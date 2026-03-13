"""
结构化临床评估引导器 V4.5.10 - 对话流程修复版
在 V4.3 结构化框架基础上，新增动态假设推理层

V4.5 新增能力：
1. 动态假设追踪：基于证据更新多层级假设置信度
2. 贝叶斯信念更新：每条新证据更新所有相关假设
3. 主动鉴别提问：选择能降低不确定性的问题
4. 叙事性报告：基于推理过程生成整合性解释

V4.5.10 修复（针对案例 13 失败）：
1. 扩展后果提取关键词：新增"过去"、"看他"、"叫她"等第一人称干预动作
2. 新增第一人称模式匹配：直接捕获"我过去看他"类回答
3. 修复 field_id 变量作用域 bug（GENERATE_REPORT 分支）
4. 增加空响应防护：确保永不返回空消息

V4.5 完全保留 V4.3 数据管道，仅增强推理层
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path

from app.llm.base import LLMClient
from app.agents.insight_analyzer import InsightAnalyzer
from app.agents.intervention_planner import InterventionPlanner
from app.agents.clinical_reasoning_engine import ClinicalReasoningEngine

logger = logging.getLogger(__name__)


@dataclass
class FieldValue:
    """字段值（带置信度）"""
    value: str = ""
    confidence: float = 0.0
    source_turn: int = 0
    is_auto_inferred: bool = False  # 是否自动推断


@dataclass
class StructuredAssessmentState:
    """
    V4.3 评估会话状态
    
    核心改进：
    - workflow_stages: 明确的工作流阶段
    - filled_data: 结构化字段值存储
    - inferred_hypotheses: 动态假设置信度
    - environment_inference_rules: 环境推断规则
    """
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    
    # 工作流状态
    current_stage: str = "BACKGROUND"  # 当前阶段
    filled_data: Dict[str, FieldValue] = field(default_factory=dict)
    
    # 假设追踪
    inferred_hypotheses: Dict[str, float] = field(default_factory=lambda: {
        "prompt_dependence": 0.0,
        "escape_difficulty": 0.0,
        "attention_seeking": 0.0,
        "sensory_seeking": 0.0,
        "sensory_escape": 0.0,
    })
    
    # 对话历史
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # 元数据
    turn_count: int = 0
    is_complete: bool = False
    
    # 分析结果
    insight_result: Optional[Dict[str, Any]] = None
    intervention_plan: Optional[Dict[str, Any]] = None
    
    def get_field_value(self, field_id: str) -> Optional[str]:
        """获取字段值"""
        fv = self.filled_data.get(field_id)
        return fv.value if fv else None
    
    def set_field_value(self, field_id: str, value: str, confidence: float = 0.8, is_auto_inferred: bool = False) -> None:
        """设置字段值"""
        if field_id not in self.filled_data:
            self.filled_data[field_id] = FieldValue()
        
        fv = self.filled_data[field_id]
        fv.value = value
        fv.confidence = confidence
        fv.source_turn = self.turn_count
        fv.is_auto_inferred = is_auto_inferred
        
        logger.info(f"字段填充：{field_id} = {value[:50]}... (confidence={confidence}, inferred={is_auto_inferred})")
    
    def is_field_filled(self, field_id: str) -> bool:
        """检查字段是否已填充（V4.5.10 增强版 - 增加 DEBUG 日志）"""
        fv = self.filled_data.get(field_id)
        
        # DEBUG 日志
        if fv and fv.value:
            logger.debug(f"✅ is_field_filled({field_id}) = True (value={fv.value[:30]}...)")
        elif fv:
            logger.debug(f"❌ is_field_filled({field_id}) = False (value is empty)")
        else:
            logger.debug(f"❌ is_field_filled({field_id}) = False (field not in filled_data)")
        
        if not fv or not fv.value:
            return False
        
        # 排除无效值（但保留"无外部干预"等有效值）
        if not fv.value.strip():
            return False
        
        return True
    
    def get_stage_completion_rate(self, stage_id: str, framework: dict) -> float:
        """计算阶段完成度"""
        stage = next((s for s in framework.get("workflow_stages", []) if s["id"] == stage_id), None)
        if not stage:
            return 0.0
        
        fields = stage.get("fields", [])
        required_fields = [f for f in fields if f.get("is_required") and not f.get("is_auto_inferred")]
        
        if not required_fields:
            return 1.0
        
        filled = sum(1 for f in required_fields if self.is_field_filled(f["field_id"]))
        return filled / len(required_fields)
    
    def get_overall_completion_rate(self, framework: dict) -> float:
        """计算整体完成度"""
        all_fields = [
            f["field_id"] 
            for stage in framework.get("workflow_stages", [])
            for f in stage.get("fields", [])
            if f.get("is_required") and not f.get("is_auto_inferred")
        ]
        
        if not all_fields:
            return 0.0
        
        filled = sum(1 for fid in all_fields if self.is_field_filled(fid))
        return filled / len(all_fields)
    
    def update_hypothesis(self, hypothesis: str, confidence_boost: float) -> None:
        """更新假设置信度"""
        current = self.inferred_hypotheses.get(hypothesis, 0.0)
        new_value = min(1.0, max(-1.0, current + confidence_boost))
        self.inferred_hypotheses[hypothesis] = new_value
        logger.info(f"假设更新：{hypothesis} = {new_value:.2f} (boost={confidence_boost})")


class ClinicalAssessmentFramework:
    """临床评估框架加载与管理"""
    
    def __init__(self, framework_path: str):
        self.path = Path(framework_path)
        self.data = {}
        self.load()
        logger.info(f"ClinicalAssessmentFramework 加载完成：{len(self.data.get('workflow_stages', []))} 个阶段")
    
    def load(self) -> None:
        """加载框架文件"""
        if not self.path.exists():
            logger.error(f"框架文件不存在：{self.path}")
            return
        
        with open(self.path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
    
    def get_stage(self, stage_id: str) -> Optional[dict]:
        """获取阶段定义"""
        for stage in self.data.get("workflow_stages", []):
            if stage.get("id") == stage_id:
                return stage
        return None
    
    def get_field(self, field_id: str) -> Optional[dict]:
        """获取字段定义"""
        for stage in self.data.get("workflow_stages", []):
            for f in stage.get("fields", []):
                if f.get("field_id") == field_id:
                    return f
        return None
    
    def get_required_fields(self) -> List[str]:
        """获取所有必填字段 ID"""
        required = []
        for stage in self.data.get("workflow_stages", []):
            for f in stage.get("fields", []):
                if f.get("is_required") and not f.get("is_auto_inferred"):
                    required.append(f["field_id"])
        return required
    
    def get_completion_rules(self) -> dict:
        """获取完成规则"""
        return self.data.get("completion_rules", {})
    
    def get_hypothesis_mapping(self) -> dict:
        """获取假设映射规则"""
        return self.data.get("hypothesis_mapping", {})
    
    def get_environment_inference_rules(self) -> list:
        """获取环境推断规则"""
        rules = self.data.get("environment_inference_rules", [])
        return rules if isinstance(rules, list) else []
    
    def get_next_stage(self, current_stage_id: str) -> Optional[str]:
        """获取下一阶段 ID"""
        stages = self.data.get("workflow_stages", [])
        current_idx = next((i for i, s in enumerate(stages) if s["id"] == current_stage_id), -1)
        
        if current_idx >= 0 and current_idx < len(stages) - 1:
            return stages[current_idx + 1]["id"]
        return None


class StructuredAssessorV4:
    """
    结构化临床评估引导器 V4.5 - 临床推理引擎集成版
    
    核心方法：
    1. process(): 主处理流程
    2. _extract_into_framework(): LLM 信息提取
    3. _infer_environment(): 智能环境推断
    4. _decide_next_action(): 工作流决策（V4.3）或推理决策（V4.5）
    5. _generate_natural_question(): 自然语言问题生成
    6. _generate_report(): 触发报告生成（含叙事增强）
    
    V4.5 新增：
    - reasoning_engine: 临床推理引擎，负责假设追踪和信念更新
    """
    
    def __init__(self, llm_client: LLMClient, framework_path: str):
        self.llm = llm_client
        self.framework = ClinicalAssessmentFramework(framework_path)
        self.sessions: Dict[str, StructuredAssessmentState] = {}
        
        # V4.5 新增：临床推理引擎
        network_path = "app/knowledge/hypothesis_network.json"
        self.reasoning_engine = ClinicalReasoningEngine(llm_client, network_path)
        
        logger.info("StructuredAssessorV4 初始化完成 - V4.5 临床推理引擎集成版")
    
    def _create_session(self) -> StructuredAssessmentState:
        """创建新会话（V4.5.12 新增：重置推理引擎假设）"""
        session_id = str(uuid.uuid4())[:8]
        session = StructuredAssessmentState(session_id=session_id)
        self.sessions[session_id] = session
        
        # V4.5.12 新增：重置推理引擎的假设置信度
        self.reasoning_engine._reset_hypotheses()
        
        # 初始化必填字段
        for field_id in self.framework.get_required_fields():
            session.filled_data[field_id] = FieldValue()
        
        logger.info(f"创建新会话：{session_id} (假设置信度已重置)")
        return session
    
    def _get_or_create_session(self, session_id: Optional[str]) -> StructuredAssessmentState:
        """获取或创建会话"""
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        return self._create_session()
    
    def _extract_into_framework(self, state: StructuredAssessmentState, user_input: str) -> Dict[str, str]:
        """
        V4.3 核心：从用户输入中提取信息，填充到框架字段
        
        提取策略：
        1. 优先提取当前阶段的必填字段
        2. 如果用户输入包含多阶段信息，全部提取
        3. 使用明确的字段定义，避免歧义
        """
        # 构建字段定义列表（按阶段组织）
        field_definitions = []
        for stage in self.framework.data.get("workflow_stages", []):
            stage_name = stage.get("name", "")
            fields_str = "\n".join([
                f"  - {f['field_id']}: {f.get('prompt_question', '')} ({f.get('short_name', '')})"
                for f in stage.get("fields", [])
                if not f.get("is_auto_inferred")
            ])
            field_definitions.append(f"【{stage_name}】\n{fields_str}")
        
        all_fields_text = "\n\n".join(field_definitions)
        
        # 构建已填充字段信息
        filled_info = []
        for field_id, fv in state.filled_data.items():
            if fv.value:
                filled_info.append(f"- {field_id}: {fv.value[:50]}")
        filled_text = "\n".join(filled_info) if filled_info else "（暂无）"
        
        # 确定当前最需要填充的字段
        required_fields = self.framework.get_required_fields()
        missing_required = [f for f in required_fields if not state.is_field_filled(f)]
        priority_hint = f"当前最需要填充的字段：{', '.join(missing_required)}" if missing_required else "所有必填字段已填充"
        
        extraction_prompt = f"""从用户输入中提取信息，填充到临床评估框架字段中。

【评估框架字段定义】
{all_fields_text}

【已填充字段】
{filled_text}

【优先级提示】
{priority_hint}

【用户输入】
{user_input}

【提取规则】
1. **优先提取必填字段**：child_age, antecedent, behavior_detail, immediate_consequence
2. 只提取明确提到的信息，不要推断
3. 值要简洁，保留核心信息
4. 以 JSON 格式输出：{{"field_id": "提取的值", ...}}

【字段说明】
- child_age：孩子年龄（如"5 岁"、"幼儿园大班"）
- antecedent：何时、何地、何事（如"在教室里做操"）
- behavior_detail：孩子具体做了什么/没做什么（如"发呆"、"不看老师"）
- immediate_consequence：他人如何回应（如"老师提醒他"、"没人管他"、"被忽略"）
  **关键识别规则**：
  - "不管"、"不干预"、"忽略"、"没人理"、"随他去"、"没人管"、"不怎么管" → 提取为 "无外部干预"
  - "观察者"、"影子"、"记录" → 提取为 "无干预（观察者角色）"
- pattern_with_prompt：有提示能否做好（如"需要提醒才继续"）
- escape_difficulty_clue：任务难度感受（如"太难了"、"不会"）

【示例】
用户说："5 岁，在幼儿园做操时发呆"
输出：{{"child_age": "5 岁", "antecedent": "在幼儿园做操", "behavior_detail": "发呆"}}

用户说："老师提醒他才会继续"
输出：{{"immediate_consequence": "老师提醒", "pattern_with_prompt": "提醒才会继续"}}

用户说："老师在大多数情况下是不管的"
输出：{{"immediate_consequence": "无外部干预"}}

用户说："我本人是一个行为记录观察。就像影子一样，尽量不干预"
输出：{{"immediate_consequence": "无干预（观察者角色）"}}

用户说："基本上没人管她"
输出：{{"immediate_consequence": "无外部干预"}}

注意：
- 如果用户输入不包含任何字段信息，返回空字典 {{}}
- 如果用户是在回答某个问题，重点提取对应字段
- **当检测到"不管"、"不干预"、"忽略"、"没人管"等词时，必须将 immediate_consequence 标记为"无外部干预"，这视为已填充！**
"""
        
        try:
            result = self.llm.generate_json(
                system_prompt="只输出 JSON，不要解释。如果没有可提取的信息，返回空字典{}。",
                user_prompt=extraction_prompt,
                temperature=0.1,
                max_tokens=400,
            ) or {}
            
            # V4.5 Hotfix: 规则匹配后处理 - 确保"不管"、"没人管"等被正确识别
            result = self._post_process_extraction(result, user_input)
            
            # 更新假设置信度
            self._update_hypothesis_tracker(state, user_input, result)
            
            return result
            
        except Exception as e:
            logger.warning(f"LLM 提取失败：{e}")
            # 降级：直接规则匹配
            return self._post_process_extraction({}, user_input)
    
    def _rule_based_extraction(self, user_input: str) -> dict:
        """
        V4.5.18 修复版：基于规则的字段提取 + 矛盾证据识别 + "不知道"处理
        
        确保简单回答（如"5 岁"、"男孩"）能被正确提取
        识别矛盾证据（如"其实都会做"推翻提示依赖假设）
        处理"不知道"等无法回答的情况
        """
        import re
        extracted = {}
        user_input = user_input.strip()
        
        # === V4.5.18 新增："不知道"处理 ===
        # 用户回答"不知道"是有效信息，应记录为"观察者未注意"
        unknown_keywords = ["不知道", "不清楚", "没注意", "忘了", "说不清", "不确定", "没看到"]
        if user_input in unknown_keywords or user_input.startswith("不知道"):
            # 根据上下文，填充为"观察者未注意"
            logger.info(f"规则提取：用户回答'不知道'，记录为有效信息")
        
        # === 年龄提取 ===
        age_patterns = [
            r"(\d+)[岁个]",  # "5 岁"、"5 个"
            r"(\d+) 岁半",  # "5 岁半"
            r"幼儿园 [小中大] 班",  # "幼儿园小班"
            r"[小中大]班",  # "小班"
            r"(\d+) 年级",  # "1 年级"
        ]
        for pattern in age_patterns:
            match = re.search(pattern, user_input)
            if match:
                extracted["child_age"] = match.group(0)
                logger.info(f"规则提取：child_age = {match.group(0)}")
                break
        
        # V4.5.7 增强：单独处理纯数字回答（如"7 岁"）
        if not extracted.get("child_age") and re.match(r"^\d+[岁个]?$", user_input.strip()):
            extracted["child_age"] = user_input.strip()
            logger.info(f"规则提取（纯数字）：child_age = {user_input.strip()}")
        
        # === 性别提取 ===
        if any(kw in user_input for kw in ["男孩", "男宝", "儿子", "他"]):
            extracted["child_gender"] = "男孩"
            logger.info(f"规则提取：child_gender = 男孩")
        elif any(kw in user_input for kw in ["女孩", "女宝", "女儿", "她"]):
            extracted["child_gender"] = "女孩"
            logger.info(f"规则提取：child_gender = 女孩")
        
        # === 环境提取 ===
        if any(kw in user_input for kw in ["幼儿园", "学校", "教室", "老师"]):
            extracted["inferred_setting"] = "幼儿园" if "幼儿园" in user_input else "学校"
            logger.info(f"规则提取：inferred_setting = {extracted['inferred_setting']}")
        elif any(kw in user_input for kw in ["家", "家里", "客厅", "卧室"]):
            extracted["inferred_setting"] = "家庭"
            logger.info(f"规则提取：inferred_setting = 家庭")
        elif "超市" in user_input:
            extracted["inferred_setting"] = "超市"
            logger.info(f"规则提取：inferred_setting = 超市")
        
        # === 后果提取（无干预） ===
        no_intervention_keywords = [
            "不管", "不干预", "忽略", "没人理", "随他去", "没人管", 
            "不怎么管", "很少管", "基本不管", "观察者", "影子", "记录",
            "尽量不干预", "没有人管", "没人管她", "没有特别处理"
        ]
        if any(kw in user_input for kw in no_intervention_keywords):
            extracted["immediate_consequence"] = "无外部干预"
            logger.info(f"规则提取：immediate_consequence = 无外部干预")
        
        # === 后果提取（有干预）V4.5.10 增强 ===
        # V4.5.10 新增：扩展关键词，覆盖"我过去看他"等常见表达
        consequence_keywords = [
            "提醒", "说", "批评", "安慰", "给", "离开", "催", "哄", "告诉", "打断",
            "过去", "看他", "看她", "走过去", "跑过去", "叫他", "喊他", "喊她",
            "回应", "理他", "理她", "帮他", "帮他做", "辅助", "示范", "拉着", "抱着",
            "制止", "阻止", "表扬", "鼓励", "点头", "微笑", "看他一眼", "看了一眼"
        ]
        if any(kw in user_input for kw in consequence_keywords):
            if "immediate_consequence" not in extracted:  # 不覆盖无干预
                # 提取整句作为后果
                extracted["immediate_consequence"] = user_input[:30]
                logger.info(f"规则提取：immediate_consequence = {user_input[:30]}...")
        
        # === V4.5.10 新增：第一人称干预动作直接提取 ===
        # 匹配模式："我..." + 动作词 → 视为有干预
        first_person_patterns = [
            r"^我 [过去走跑].*",  # "我过去看他"、"我走过去"
            r"^我 [叫喊提醒].*",  # "我叫他"、"我提醒他"
            r"^我 [帮辅示].*",  # "我帮他"、"我辅助"
            r"^我 [制阻].*",  # "我制止"、"我阻止"
        ]
        import re
        for pattern in first_person_patterns:
            if re.match(pattern, user_input):
                if "immediate_consequence" not in extracted:
                    extracted["immediate_consequence"] = user_input[:30]
                    logger.info(f"规则提取（第一人称）：immediate_consequence = {user_input[:30]}...")
                break
        
        # === V4.5.18 新增："不知道"处理 ===
        # 用户回答"不知道"是有效信息，应记录为"观察者未注意"
        if user_input in ["不知道", "不清楚", "没注意", "忘了", "说不清", "不确定"]:
            if "immediate_consequence" not in extracted:
                extracted["immediate_consequence"] = "观察者未注意/无法确定"
                logger.info(f"规则提取：immediate_consequence = 观察者未注意")
        
        # === V4.5.7 增强：矛盾证据识别 + 置信度调整 ===
        # 关键线索："其实都会做"、"不需要帮助就能完成" → 排除提示依赖，指向寻求关注
        attention_seeking_keywords = ["其实都会", "都会做", "不需要帮助", "自己能做", "能做好", "已经会", "自己能"]
        if any(kw in user_input for kw in attention_seeking_keywords):
            extracted["attention_seeking_clue"] = user_input
            extracted["_override_prompt_dependence"] = True  # 强制覆盖提示依赖假设（内部标志，不作为字段存储）
            logger.info(f"矛盾证据识别：attention_seeking_clue = {user_input}（强制排除提示依赖）")
        
        # === V4.5.14 新增：逃避难度线索提取 ===
        # 关键线索："太难了"、"有点难"、"不会做" → 指向逃避难度
        escape_difficulty_keywords = ["太难了", "太难", "有点难", "不会做", "做不到", "好难"]
        if any(kw in user_input for kw in escape_difficulty_keywords):
            extracted["escape_difficulty_clue"] = user_input
            logger.info(f"规则提取：escape_difficulty_clue = {user_input}")
        
        return extracted
    
    def _post_process_extraction(self, result: dict, user_input: str) -> dict:
        """
        V4.5.9 三层防御机制：语义识别后处理（修复覆盖 bug）
        
        Layer 1: 精确匹配（硬编码关键词）→ 快速识别常见表达
        Layer 2: 正则模式匹配 → 识别相似表达
        Layer 3: LLM 兜底 → 处理未知表达
        
        确保各种"无干预"表达都被正确识别
        V4.5.9 修复：不覆盖已提取的有效信息
        """
        # === Layer 1: 精确匹配 ===
        no_intervention_keywords = [
            "不管", "不干预", "忽略", "没人理", "随他去", "没人管", 
            "不怎么管", "很少管", "基本不管", "观察者", "影子", "记录",
            "不干预学校的情况", "尽量不干预", "没有人管", "没人管她"
        ]
        
        if any(kw in user_input for kw in no_intervention_keywords):
            if not result.get("immediate_consequence"):
                result["immediate_consequence"] = "无外部干预"
                logger.info(f"Layer1 精确匹配：检测到无干预关键词，强制填充 immediate_consequence")
                return result
        
        # === Layer 2: 正则模式匹配 ===
        import re
        semantic_patterns = [
            (r".*不.*管.*", "包含'不'和'管'的表达"),
            (r".*观察者.*", "观察者角色"),
            (r".*影子.*", "影子式观察"),
            (r".*记录.*", "只做记录不干预"),
            (r".*除非.*夸张.*", "只在极端情况下干预"),
            (r".*大多数.*不.*", "大部分时间不干预"),
            (r".*尽量.*不干预.*", "尽量不干预"),
        ]
        
        for pattern, explanation in semantic_patterns:
            if re.match(pattern, user_input):
                if not result.get("immediate_consequence"):
                    result["immediate_consequence"] = "无外部干预"
                    logger.info(f"Layer2 模式匹配：{explanation}，强制填充 immediate_consequence")
                    return result
        
        # === Layer 3: LLM 兜底识别 ===
        # 如果前两层都没匹配，但用户输入较长（可能是复杂表达），调用 LLM 识别
        if len(user_input) > 10 and not result.get("immediate_consequence"):
            llm_result = self._classify_intervention_type(user_input)
            if llm_result and isinstance(llm_result, str):
                result["immediate_consequence"] = llm_result
                logger.info(f"Layer3 LLM 识别：{llm_result}")
            elif llm_result and isinstance(llm_result, dict):
                result.update(llm_result)
                logger.info(f"Layer3 LLM 识别：{llm_result}")
        
        # 未匹配到任何模式
        if not result.get("immediate_consequence"):
            logger.info(f"未识别干预类型：{user_input[:50]}...")
        
        return result
    
    def _classify_intervention_type(self, user_input: str) -> Optional[str]:
        """
        Layer 3: 使用 LLM 识别干预类型（兜底方案）
        
        使用少样本学习，提高识别准确率
        """
        classification_prompt = f"""判断以下用户描述属于哪种干预类型：

【用户描述】
{user_input}

【干预类型定义】
1. 无外部干预：成人选择不介入、旁观、让孩子自己处理
   示例："老师不管"、"我是观察者"、"尽量不干预"、"让孩子自己解决"
   
2. 有外部干预：成人主动介入、提醒、帮助
   示例："老师提醒他"、"我走过去帮助"、"给予指导"
   
3. 同伴反应：其他孩子的反应
   示例："小朋友笑他"、"同学告诉老师"

【判断规则】
- 如果描述中包含"不管"、"不干预"、"观察者"、"影子"、"记录"等词 → 无外部干预
- 如果描述中包含"提醒"、"帮助"、"介入"等词 → 有外部干预
- 如果主要描述其他孩子的反应 → 同伴反应

请只输出以下三个值之一：
- 无外部干预
- 有外部干预
- 同伴反应

如果无法判断，输出：需要澄清
"""
        
        try:
            # 使用已初始化的 self.llm (OpenAIClient 实例)
            result = self.llm.generate(
                system_prompt="只输出四个值之一：无外部干预、有外部干预、同伴反应、需要澄清",
                user_prompt=classification_prompt,
                temperature=0.1,
                max_tokens=20,
            )
            
            response = result.strip() if result else ""
            
            if response in ["无外部干预", "有外部干预", "同伴反应"]:
                return response
            else:
                return None
                
        except Exception as e:
            logger.warning(f"LLM 分类失败：{e}")
            return None
    
    def _update_hypothesis_tracker(self, state: StructuredAssessmentState, user_input: str, extracted: dict) -> None:
        """
        根据用户输入更新假设置信度
        
        基于框架中的 hypothesis_mapping 规则
        """
        mapping = self.framework.get_hypothesis_mapping()
        
        for rule_name, rule in mapping.items():
            trigger_patterns = rule.get("trigger_patterns", [])
            hypothesis = rule.get("hypothesis")
            confidence_boost = rule.get("confidence_boost", 0.1)
            
            # 检查是否触发（支持多模式匹配）
            triggered = any(pattern in user_input for pattern in trigger_patterns)
            
            if triggered and hypothesis:
                state.update_hypothesis(hypothesis, confidence_boost)
    
    def _infer_environment(self, state: StructuredAssessmentState) -> Optional[str]:
        """
        V4.3 智能环境推断（P1 修复版）
        
        基于年龄和 antecedent 描述自动推断环境
        修复逻辑：优先识别家庭环境，避免"在家写作业"被误判为学校
        """
        age_str = state.get_field_value("child_age") or ""
        antecedent = state.get_field_value("antecedent") or ""
        
        # 提取年龄数字
        age = None
        if "岁" in age_str:
            try:
                age = int(''.join(filter(str.isdigit, age_str)))
            except:
                pass
        
        # === V4.3 P1 修复：优先识别家庭环境（强信号）===
        home_keywords = ["家", "家里", "在家", "客厅", "卧室", "书房", "饭桌", "餐桌"]
        if any(kw in antecedent for kw in home_keywords):
            logger.info(f"环境推断：家庭 (检测到家庭关键词：{antecedent[:50]}...)")
            return "家庭"
        
        # === 规则 2：结合活动推断（作业/学习/练琴等）===
        study_activities = ["做作业", "作业", "学习", "练琴", "写作业", "功课"]
        if any(kw in antecedent for kw in study_activities):
            # 如果没有明确的学校线索，优先推断为家庭
            school_keywords = ["学校", "教室", "幼儿园", "老师", "课堂", "上课"]
            if not any(kw in antecedent for kw in school_keywords):
                logger.info(f"环境推断：家庭 (学习活动且无学校线索：{antecedent[:50]}...)")
                return "家庭"
        
        # === 规则 3：原幼儿园/学校推断逻辑 ===
        # 应用环境推断规则（从框架文件加载）
        rules = self.framework.get_environment_inference_rules()
        
        # V4.5.14 修复：确保 rules 是列表
        if not isinstance(rules, list):
            logger.warning(f"⚠️ environment_inference_rules 类型错误：{type(rules)}，使用空列表")
            rules = []
        
        for rule in rules:
            conditions = rule.get("conditions", {})
            env_name = rule.get("environment")
            
            # 跳过家庭规则（已在上文处理）
            if env_name == "家庭":
                continue
            
            # 检查年龄范围
            age_range = conditions.get("age_range")
            if age_range and age:
                if not (age_range[0] <= age <= age_range[1]):
                    continue
            
            # 检查关键词
            keywords = conditions.get("antecedent_keywords", [])
            if keywords and antecedent:
                if any(kw in antecedent for kw in keywords):
                    logger.info(f"环境推断：{env_name} (age={age}, antecedent={antecedent[:30]}...)")
                    return env_name
        
        # 默认返回
        logger.info(f"环境推断：未明确 (antecedent={antecedent[:30]}...)")
        return None
    
    def _decide_next_action(self, state: StructuredAssessmentState) -> Dict[str, Any]:
        """
        V4.5.10 系统性重构版 - 增加已问字段跟踪
        
        决策逻辑：
        1. 检查强制结束条件（轮数限制）
        2. 检查必填字段完成度
        3. 检查早期退出条件
        4. 跟踪已问字段，避免重复提问
        5. 选择下一个要问的字段
        """
        rules = self.framework.get_completion_rules()
        required_fields = rules.get("required_fields_for_analysis", [])
        max_turns = rules.get("max_turns", 8)
        
        # === V4.5.10 新增：已问字段跟踪 ===
        asked_fields = {}  # field_id -> count
        for msg in state.conversation_history:
            if msg.get("role") == "ai" and "field=" in str(msg.get("text", "")):
                import re
                match = re.search(r'field=(\w+)', msg.get("text", ""))
                if match:
                    field_id = match.group(1)
                    asked_fields[field_id] = asked_fields.get(field_id, 0) + 1
        
        logger.info(f"📊 已问字段统计：{asked_fields}")
        
        # === 规则 1: 强制结束条件（轮数限制）===
        if state.turn_count >= max_turns:
            logger.info(f"触发强制结束：turn_count={state.turn_count} >= {max_turns}")
            return {"type": "GENERATE_REPORT"}
        
        # === V4.5.10 新增：重复提问检测 ===
        for field_id, count in asked_fields.items():
            if count >= 2:
                logger.warning(f"⚠️ 字段{field_id}已问过{count}次，检查是否填充失败")
                if not state.is_field_filled(field_id):
                    logger.error(f"❌ 字段{field_id}问过{count}次仍未填充，强制结束")
                    return {"type": "GENERATE_REPORT"}
        
        # === 规则 2: 必填字段完成度 ===
        missing_required = [f for f in required_fields if not state.is_field_filled(f)]
        if not missing_required:
            logger.info(f"必填字段已完成：{len(required_fields)}/{len(required_fields)}")
            return {"type": "GENERATE_REPORT"}
        
        # === 规则 3: 早期退出条件 ===
        for condition in rules.get("early_exit_conditions", []):
            cond_field = condition.get("condition", {}).get("field")
            cond_values = condition.get("condition", {}).get("value_contains", [])
            required_filled = condition.get("condition", {}).get("required_fields_filled", [])
            
            if cond_field:
                field_value = state.get_field_value(cond_field)
                if field_value and any(v in field_value for v in cond_values):
                    all_filled = all(state.is_field_filled(f) for f in required_filled)
                    if all_filled:
                        logger.info(f"触发早期退出：{condition.get('name')}")
                        return {"type": "GENERATE_REPORT"}
        
        # === 规则 4: 按工作流阶段选择下一个字段 ===
        # 4a. 先完成当前阶段的必填字段
        current_stage = self.framework.get_stage(state.current_stage)
        if current_stage:
            skipped_due_to_asked = 0
            for f in current_stage.get("fields", []):
                field_id = f["field_id"]
                # 跳过已填充和自动推断字段
                if state.is_field_filled(field_id) or f.get("is_auto_inferred"):
                    continue
                # V4.5.10 新增：跳过已问过 2 次以上的字段
                if asked_fields.get(field_id, 0) >= 2:
                    logger.warning(f"⚠️ 字段{field_id}已问过 2 次，跳过")
                    skipped_due_to_asked += 1
                    continue
                # 检查触发条件
                trigger = f.get("trigger_condition")
                if trigger:
                    trigger_field = trigger.get("field")
                    trigger_contains = trigger.get("contains", [])
                    tf_value = state.get_field_value(trigger_field)
                    if tf_value and any(kw in tf_value for kw in trigger_contains):
                        logger.info(f"选择触发字段：{field_id}")
                        return {"type": "ASK_FIELD", "field_id": field_id}
                    # 触发条件不满足，跳过
                    continue
                else:
                    logger.info(f"选择当前阶段字段：{field_id}")
                    return {"type": "ASK_FIELD", "field_id": field_id}
            
            # V4.5.10 新增：如果所有字段都已问过 2 次，强制结束
            if skipped_due_to_asked > 0:
                logger.warning(f"⚠️ 所有字段都已问过 2 次，强制生成报告")
                return {"type": "GENERATE_REPORT"}
        
        # 4b. 当前阶段完成，进入下一阶段
        next_stage = self.framework.get_next_stage(state.current_stage)
        if next_stage:
            state.current_stage = next_stage
            logger.info(f"进入下一阶段：{state.current_stage}")
            return self._decide_next_action(state)
        
        # === 默认：信息已足够 ===
        logger.info("无更多字段可问，生成报告")
        return {"type": "GENERATE_REPORT"}
    
    def _generate_natural_question(self, state: StructuredAssessmentState, field_id: str) -> str:
        """
        将框架字段转化为自然语言问题
        
        策略：
        - 使用字段定义的 prompt_question 作为基础
        - 根据对话轮次调整语气（首轮完整，后续简洁）
        - 结合上下文，使问题更自然
        """
        field_def = self.framework.get_field(field_id)
        if not field_def:
            return "能再详细描述一下吗？"
        
        question = field_def.get("prompt_question", "")
        hint = field_def.get("hint", "")
        short_name = field_def.get("short_name", "")
        
        # 根据阶段调整语气
        stage_name = state.current_stage
        stage = self.framework.get_stage(stage_name)
        stage_desc = stage.get("description", "") if stage else ""
        
        if state.turn_count <= 1:
            # 首轮：完整问题 + 阶段说明
            prefix = f"【{stage_name}】" if stage_name else ""
            return f"{prefix} {question} {hint if hint else ''}".strip()
        else:
            # 后续轮次：简洁直接
            return f"{question} {hint if hint else ''}".strip()
    
    def _generate_report(self, state: StructuredAssessmentState) -> Dict[str, Any]:
        """
        触发报告生成
        
        调用现有的 InsightAnalyzer 和 InterventionPlanner
        """
        logger.info(f"触发报告生成：session={state.session_id}")
        
        try:
            # 从填充数据中提取 ABC
            antecedent = state.get_field_value("antecedent") or ""
            behavior = state.get_field_value("behavior_detail") or ""
            consequence = state.get_field_value("immediate_consequence") or ""
            environment = state.get_field_value("inferred_setting") or self._infer_environment(state) or ""
            child_age = state.get_field_value("child_age") or ""
            
            # 1. 生成洞察（V4.5.13 新增：个性化报告风格）
            analyzer = InsightAnalyzer(self.llm)
            insight = analyzer.analyze(
                environment=environment,
                antecedent=antecedent,
                behavior=behavior,
                consequence=consequence,
                conversation_history=state.conversation_history,  # V4.5.13 新增
                report_style=None,  # 自动检测
            )
            
            # 2. V4.5.1 核心修复：生成叙事性报告并传递给干预计划
            filled_data_dict = {k: v.value for k, v in state.filled_data.items() if v.value}
            narrative = self.reasoning_engine.generate_narrative(filled_data_dict)
            
            # 3. 生成干预计划 - V4.5.1 核心修复：基于叙事性归因选择计划
            planner = InterventionPlanner()
            
            # 根据假设置信度选择场景和假设
            hypotheses = state.inferred_hypotheses
            top_hypothesis = max(hypotheses.items(), key=lambda x: x[1], default=("prompt_dependence", 0))
            
            # 选择场景
            if top_hypothesis[0] == "escape_difficulty" or "难" in behavior or "太难" in behavior:
                scenario_key = "task_refusal"  # 逃避难度场景
                hypothesis_id = "H1"  # 逃避任务难度
            else:
                scenario_key = "task_disengagement"  # 提示依赖场景
                hypothesis_id = "H1"  # 提示依赖
            
            # V4.5.1 核心：传递叙事性分析给干预计划生成器
            session_context = {
                "environment": environment,
                "context": antecedent,
                "child_behavior": behavior,
                "others_response": consequence,
                "child_age": child_age,
                # V4.3 核心：传递功能判断和能力缺口
                "primary_hypothesis": insight.get("functional_judgment", ""),
                "capability_gap": insight.get("capability_hypothesis", ""),
                # V4.5.1 新增：传递叙事性归因
                "narrative_analysis": narrative,
            }
            
            logger.info(f"V4.5.1 生成干预计划：scenario={scenario_key}, hypothesis={hypothesis_id}, narrative={narrative.get('primary_attribution', 'N/A')[:50] if narrative else 'N/A'}...")
            plan = planner.generate_plan_with_narrative(hypothesis_id, scenario_key, session_context, narrative)
            
            # 3. 保存结果
            state.insight_result = insight
            state.intervention_plan = plan
            state.is_complete = True
            
            logger.info(f"报告生成完成：session={state.session_id}")
            
            return self._build_complete_response(state)
            
        except Exception as e:
            logger.error(f"报告生成失败：{e}")
            state.is_complete = True
            return self._build_error_response(state, str(e))
    
    def _build_complete_response(self, state: StructuredAssessmentState) -> Dict[str, Any]:
        """构建完成响应（V4.5 集成叙事性报告）"""
        insight = state.insight_result or {}
        intervention_plan = state.intervention_plan or {}
        expert_breakdown = insight.get("expert_breakdown", {})
        
        # 环境推断
        inferred_env = state.get_field_value("inferred_setting") or self._infer_environment(state) or "未明确"
        
        # V4.3 核心修复：确保 functional_judgment 等关键字段存在
        functional_judgment = insight.get("functional_judgment", "")
        if not functional_judgment and expert_breakdown.get("functional_hypothesis"):
            functional_judgment = expert_breakdown["functional_hypothesis"]
        
        # V4.5 新增：生成叙事性报告
        filled_data_dict = {k: v.value for k, v in state.filled_data.items() if v.value}
        narrative = self.reasoning_engine.generate_narrative(filled_data_dict)
        
        # 构建前端期望的 report 结构（V4.5 增强）
        report = {
            "summary": self._generate_summary(state, inferred_env),
            "context": state.get_field_value("antecedent") or "",
            "child_behavior": state.get_field_value("behavior_detail") or "",
            "others_response": state.get_field_value("immediate_consequence") or "",
            "environment": inferred_env,
            "child_age": state.get_field_value("child_age") or "",
            "functional_judgment": functional_judgment,  # V4.3 核心字段
            "core_insight": insight.get("core_insight", insight.get("core_insight_for_parent", "您敏锐地观察到了孩子的行为模式。")),
            "parent_insight": insight.get("core_insight_for_parent", "您敏锐地观察到了孩子的行为模式。"),
            "expert_view": expert_breakdown.get("functional_hypothesis", functional_judgment or "基于您的详细描述，我们正在分析行为背后的可能原因。"),
            "primary_hypothesis": expert_breakdown.get("behavior_pattern", "提示依赖行为"),
            "supporting_evidence": self._generate_supporting_evidence(state),
            "core_capability_goal": expert_breakdown.get("capability_gap", insight.get("capability_hypothesis", "提升在无实时外部提示下维持任务的能力。")),
            "clinical_differential": insight.get("clinical_differential", "基于观察到的行为模式，我们考虑了多种可能性。"),
            "reflection": insight.get("reasoning_brief", "每个行为都是孩子与我们沟通的方式。"),
            "empowerment_question": "在接下来一周，请留意孩子在哪件他热爱的事情上展现出惊人的专注力？",
            # V4.5 新增：叙事性报告
            "narrative_analysis": narrative,
        }
        
        return {
            "session_id": state.session_id,
            "status": "completed",
            "response_type": "insight_report",
            "message": "感谢您详细的分享。信息已收集完整，现在我将为您生成分析报告。",
            "data": {
                "context": report["context"],
                "child_behavior": report["child_behavior"],
                "others_response": report["others_response"],
                "core_insight": insight.get("core_insight_for_parent", ""),
                "expert_breakdown": expert_breakdown,
                "report": report,
                "intervention_plan": intervention_plan,
            },
            "progress": {
                "completion_rate": state.get_overall_completion_rate(self.framework.data),
                "current_stage": state.current_stage,
                "filled_fields": list(state.filled_data.keys()),
                "total_turns": state.turn_count,
                "inferred_environment": inferred_env,
            },
        }
    
    def _build_error_response(self, state: StructuredAssessmentState, error: str) -> Dict[str, Any]:
        """构建错误响应（降级方案）"""
        return {
            "session_id": state.session_id,
            "status": "completed",
            "response_type": "insight_report",
            "message": "感谢您的分享。我已经有了基本了解，现在为您生成简要分析。",
            "data": {
                "context": state.get_field_value("antecedent") or "",
                "child_behavior": state.get_field_value("behavior_detail") or "",
                "others_response": state.get_field_value("immediate_consequence") or "",
                "core_insight": "孩子正在用这种方式表达他的需求。",
                "expert_breakdown": {},
                "report": {
                    "summary": "基于我们的对话，我了解到一些关于孩子行为的信息。",
                    "context": state.get_field_value("antecedent") or "",
                    "child_behavior": state.get_field_value("behavior_detail") or "",
                    "others_response": state.get_field_value("immediate_consequence") or "",
                    "parent_insight": "感谢您的详细描述。",
                    "expert_view": "需要进一步观察分析。",
                    "primary_hypothesis": "待确定",
                    "supporting_evidence": "基于您的描述。",
                    "core_capability_goal": "相关技能还在发展中。",
                    "clinical_differential": "需要更多信息进行鉴别。",
                    "reflection": "感谢您的耐心分享。",
                    "empowerment_question": "请继续观察孩子的行为模式。",
                },
                "intervention_plan": {},
            },
        }
    
    def _decide_next_action_with_reasoning(self, state: StructuredAssessmentState, reasoning_action: Optional[dict] = None) -> Dict[str, Any]:
        """
        V4.5.1 核心修复：带推理的工作流决策
        
        当推理引擎无明确指令时，按优先级收集缺失信息：
        1. 必填字段（CORE_ABC 优先）
        2. 鉴别线索字段
        3. 背景信息字段
        """
        rules = self.framework.get_completion_rules()
        required_fields = rules.get("required_fields_for_analysis", [])
        max_turns = rules.get("max_turns", 8)
        
        # 规则 1: 强制结束（轮数限制）
        if state.turn_count >= max_turns:
            logger.info(f"触发强制结束：turn_count={state.turn_count} >= {max_turns}")
            return {"type": "GENERATE_REPORT", "source": "max_turns"}
        
        # 规则 2: 必填字段完成度检查
        missing_required = [f for f in required_fields if not state.is_field_filled(f)]
        if not missing_required:
            logger.info(f"必填字段已完成：{len(required_fields)}/{len(required_fields)}")
            return {"type": "GENERATE_REPORT", "source": "required_fields_complete"}
        
        # 规则 3: 早期退出条件（强证据）
        for condition in rules.get("early_exit_conditions", []):
            cond_field = condition.get("condition", {}).get("field")
            cond_values = condition.get("condition", {}).get("value_contains", [])
            required_filled = condition.get("condition", {}).get("required_fields_filled", [])
            
            field_value = state.get_field_value(cond_field)
            if field_value and any(v in field_value for v in cond_values):
                if all(state.is_field_filled(f) for f in required_filled):
                    logger.info(f"触发早期退出：{condition.get('name')}")
                    return {"type": "GENERATE_REPORT", "source": f"early_exit_{condition.get('name')}"}
        
        # 规则 4: 按工作流阶段选择下一个必填字段
        current_stage = self.framework.get_stage(state.current_stage)
        if current_stage:
            # 优先问当前阶段的必填字段
            for f in current_stage.get("fields", []):
                field_id = f["field_id"]
                if not state.is_field_filled(field_id) and not f.get("is_auto_inferred"):
                    # 检查触发条件
                    trigger = f.get("trigger_condition")
                    if trigger:
                        trigger_field = trigger.get("field")
                        trigger_contains = trigger.get("contains", [])
                        tf_value = state.get_field_value(trigger_field)
                        if tf_value and any(kw in tf_value for kw in trigger_contains):
                            logger.info(f"选择触发字段：{field_id}")
                            return {"type": "ASK_FIELD", "field_id": field_id, "source": "workflow_trigger"}
                        continue
                    else:
                        logger.info(f"选择当前阶段字段：{field_id}")
                        return {"type": "ASK_FIELD", "field_id": field_id, "source": "workflow_current_stage"}
        
        # 规则 5: 进入下一阶段
        next_stage = self.framework.get_next_stage(state.current_stage)
        if next_stage:
            state.current_stage = next_stage
            logger.info(f"进入下一阶段：{state.current_stage}")
            return self._decide_next_action_with_reasoning(state)
        
        # 规则 6: 默认结束
        logger.info("无更多字段可问，生成报告")
        return {"type": "GENERATE_REPORT", "source": "default"}
    
    def _generate_natural_question(self, state: StructuredAssessmentState, field_id: str, probing_hypothesis: Optional[str] = None) -> str:
        """
        V4.5.1 核心修复：将假设验证意图融入提问
        
        当问题是推理引擎为验证特定假设而提出时，提问方式应更精准、更具引导性。
        """
        field_def = self.framework.get_field(field_id)
        if not field_def:
            return "能再详细描述一下吗？"
        
        base_question = field_def.get("prompt_question", "")
        hint = field_def.get("hint", "")
        
        # 如果是推理引擎驱动的提问，优化问题表述
        if probing_hypothesis:
            # 从假设网络知识库中，获取此假设的"验证意图描述"
            hyp_info = self.reasoning_engine.network.get_hypothesis(probing_hypothesis)
            if hyp_info and hyp_info.evidence_rules:
                # 构建融合验证意图的专业提问
                verification_intent = self._get_verification_intent(probing_hypothesis, field_id)
                if verification_intent:
                    # 示例输出："为了帮助我们厘清孩子发呆是否与感觉环境有关，当时室内环境是安静还是有点嘈杂？"
                    if state.turn_count <= 1:
                        prefix = f"【{state.current_stage}】"
                        return f"{prefix} 为了帮助我们厘清{verification_intent}，{base_question} {hint if hint else ''}".strip()
                    else:
                        return f"为了帮助我们厘清{verification_intent}，{base_question} {hint if hint else ''}".strip()
        
        # 普通提问保持不变
        if state.turn_count <= 1:
            prefix = f"【{state.current_stage}】"
            return f"{prefix} {base_question} {hint if hint else ''}".strip()
        else:
            return f"{base_question} {hint if hint else ''}".strip()
    
    def _get_verification_intent(self, hypothesis_id: str, field_id: str) -> str:
        """
        获取假设验证意图描述
        
        根据假设 ID 和字段 ID，返回验证意图的中文描述
        """
        intent_map = {
            "H_WORKING_MEMORY": {
                "pattern_with_prompt": "孩子的表现是否依赖于实时视觉提示",
                "antecedent": "任务是否涉及多步骤序列",
            },
            "H_ESCAPE_DIFFICULTY": {
                "escape_difficulty_clue": "任务难度是否超出孩子当前能力",
                "behavior_detail": "行为是否表现为抗拒或逃避",
            },
            "H_SENSORY_OVERLOAD": {
                "sensory_reactions": "环境是否存在感觉超载因素",
                "antecedent": "环境是否嘈杂或拥挤",
            },
            "H_ESCAPE_SENSORY": {
                "sensory_reactions": "孩子是否有感觉敏感表现",
                "antecedent": "环境是否有不适的感觉刺激",
            },
        }
        
        hyp_intents = intent_map.get(hypothesis_id, {})
        return hyp_intents.get(field_id, "行为背后的原因")
    
    def _generate_summary(self, state: StructuredAssessmentState, inferred_env: str) -> str:
        """生成综合摘要（V4.3 增强版）"""
        parts = []
        
        child_age = state.get_field_value("child_age") or ""
        antecedent = state.get_field_value("antecedent") or ""
        behavior = state.get_field_value("behavior_detail") or ""
        consequence = state.get_field_value("immediate_consequence") or ""
        
        # 年龄 + 环境
        if child_age and inferred_env != "未明确":
            parts.append(f"{child_age}孩子在{inferred_env}环境中")
        elif child_age:
            parts.append(f"{child_age}孩子")
        elif inferred_env != "未明确":
            parts.append(f"在{inferred_env}环境中")
        
        # 情境
        if antecedent:
            parts.append(f"当{antecedent}时")
        
        # 行为
        if behavior:
            parts.append(f"观察到孩子{behavior}")
        
        # 后果
        if consequence:
            parts.append(f"而周围人的回应是{consequence}")
        
        # 假设信息
        top_hypothesis = max(state.inferred_hypotheses.items(), key=lambda x: x[1], default=(None, 0))
        if top_hypothesis[0] and top_hypothesis[1] > 0.3:
            hyp_names = {
                "prompt_dependence": "提示依赖",
                "escape_difficulty": "逃避难度",
                "attention_seeking": "寻求关注",
            }
            hyp_name = hyp_names.get(top_hypothesis[0], top_hypothesis[0])
            parts.append(f"初步判断可能与{hyp_name}有关")
        
        if not parts:
            return "基于我们的对话，我对情况有了基本了解。"
        
        return "。".join(parts) + "。"
    
    def _generate_supporting_evidence(self, state: StructuredAssessmentState) -> str:
        """生成支持证据描述"""
        evidence_parts = []
        
        # 检查提示依赖证据
        pattern_field = state.get_field_value("pattern_with_prompt")
        if pattern_field and ("能" in pattern_field or "会" in pattern_field or "需要" in pattern_field):
            evidence_parts.append("孩子表现出'有提示则执行，无提示则中断'的模式")
        
        # 检查逃避难度证据
        escape_field = state.get_field_value("escape_difficulty_clue")
        if escape_field and ("难" in escape_field or "不会" in escape_field or "吃力" in escape_field):
            evidence_parts.append("任务难度超出当前能力范围")
        
        # 检查对话轮数
        if state.turn_count >= 3:
            evidence_parts.append(f"通过{state.turn_count}轮深入对话确认了关键细节")
        
        if not evidence_parts:
            return "基于您的详细描述和行为模式分析。"
        
        return "；".join(evidence_parts) + "。"
    
    def process(self, session_id: Optional[str], user_input: str) -> Dict[str, Any]:
        """
        V4.3 主处理流程
        
        1. 加载/创建会话
        2. 记录用户输入
        3. LLM 提取信息到框架字段
        4. 智能环境推断
        5. 更新假设置信度
        6. 工作流决策下一步
        7. 生成问题或触发报告
        """
        # 1. 加载状态
        state = self._get_or_create_session(session_id)
        state.turn_count += 1
        
        # 2. 记录对话
        state.conversation_history.append({
            "role": "user", 
            "text": user_input, 
            "turn": state.turn_count
        })
        
        logger.info(f"V4.3 处理输入：session={state.session_id}, turn={state.turn_count}, stage={state.current_stage}")
        
        # V4.5.12 新增：意图检测（前 2 轮对话）
        if state.turn_count <= 2:
            logger.info(f"🔍 第{state.turn_count}轮对话，执行意图检测：{user_input[:50]}...")
            detected_intent = self.reasoning_engine.detect_user_intent(user_input)
            if detected_intent:
                logger.info(f"✅ 意图检测：{detected_intent}")
                # V4.5.15 修复：将意图检测结果同步到 state.inferred_hypotheses
                hyp_id_map = {
                    "H_TANGIBLE": "tangible_access",
                    "H_ATTENTION": "attention_seeking",
                    "H_ESCAPE_SENSORY": "sensory_escape",
                    "H_ESCAPE_DIFFICULTY": "escape_difficulty",
                    "prompt_dependence": "prompt_dependence",
                    "escape_difficulty": "escape_difficulty",
                }
                mapped_id = hyp_id_map.get(detected_intent, detected_intent)
                # 将检测到的假设置信度设为 0.9（最高优先级）
                for hyp_key in state.inferred_hypotheses:
                    if hyp_key == mapped_id or hyp_key == detected_intent:
                        state.inferred_hypotheses[hyp_key] = 0.9
                    else:
                        state.inferred_hypotheses[hyp_key] = max(0.1, state.inferred_hypotheses[hyp_key] * 0.3)
                logger.info(f"🔒 锁定假设：{mapped_id} (confidence=0.9)")
            else:
                logger.info(f"⚠️ 未检测到明确意图")
        
        # V4.5.13 P1-04 新增：情感识别与回应
        emotion_response = self._detect_and_respond_emotion(user_input, state.turn_count)
        if emotion_response:
            logger.info(f"💙 情感回应：{emotion_response[:50]}...")
        
        # 3. LLM 提取信息
        extracted = self._extract_into_framework(state, user_input)
        
        # V4.5.3 修复：规则匹配 fallback，确保简单回答也能提取
        rule_extracted = self._rule_based_extraction(user_input)
        for field_id, value in rule_extracted.items():
            if field_id not in extracted:  # LLM 未提取到的字段用规则补充
                extracted[field_id] = value
        
        # V4.5.18 新增：ABC 信息收集 fallback
        # 如果用户输入模糊（如"眼神关注有问题"），缺少 A 或 B，需要主动询问
        if state.turn_count == 1 and not extracted.get("antecedent"):
            # 首轮对话且缺少前因，记录用户输入为行为描述
            extracted["behavior_detail"] = user_input
            logger.info(f"V4.5.18 fallback: 首轮输入记录为 behavior_detail")
        
        # 填充字段（跳过内部标志，如 _override_prompt_dependence）
        for field_id, value in extracted.items():
            if field_id.startswith("_"):
                continue  # 跳过内部标志
            state.set_field_value(field_id, value)
            logger.info(f"✅ 字段确认：{field_id} = {value[:30]}...")
        
        # 4. 智能环境推断（如果 antecedent 已填充）
        if state.get_field_value("antecedent") and not state.get_field_value("inferred_setting"):
            inferred_env = self._infer_environment(state)
            if inferred_env:
                state.set_field_value("inferred_setting", inferred_env, confidence=0.7, is_auto_inferred=True)
        
        # 5. V4.5.7 增强：临床推理引擎更新信念 + 矛盾证据处理
        filled_data_dict = {k: v.value for k, v in state.filled_data.items() if v.value}
        hypothesis_confidences = self.reasoning_engine.update_beliefs(user_input, filled_data_dict)
        
        # V4.5.12 修复：确保 hypothesis_confidences 是字典
        if not isinstance(hypothesis_confidences, dict):
            logger.warning(f"⚠️ hypothesis_confidences 类型错误：{type(hypothesis_confidences)}，使用默认值")
            hypothesis_confidences = {}
        
        # V4.5.15 修复：保护意图锁定的假设不被 update_beliefs 覆盖
        locked_hypothesis = None
        locked_confidence = 0.0
        for hyp_id, conf in state.inferred_hypotheses.items():
            if conf >= 0.9:
                locked_hypothesis = hyp_id
                locked_confidence = conf
                break
        
        # V4.5.15 新增：假设 ID 反向映射（用于匹配 update_beliefs 返回的 ID）
        reverse_hyp_map = {
            "tangible_access": "H_TANGIBLE",
            "attention_seeking": "H_ATTENTION",
            "sensory_escape": "H_ESCAPE_SENSORY",
            "escape_difficulty": "H_ESCAPE_DIFFICULTY",
            "prompt_dependence": "H_PROMPT_DEPENDENCE",
        }
        
        # V4.5.7 P0 修复：矛盾证据强制调整假设置信度
        # V4.5.14 修复：确保 rule_extracted 是字典
        if isinstance(rule_extracted, dict) and rule_extracted.get("_override_prompt_dependence"):
            logger.info("🔴 矛盾证据检测：强制调整假设置信度")
            # 降低提示依赖置信度
            state.inferred_hypotheses["prompt_dependence"] = 0.2
            # 提升寻求关注置信度
            state.inferred_hypotheses["attention_seeking"] = 0.8
            logger.info(f"调整后的假设：prompt_dependence=0.2, attention_seeking=0.8")
        else:
            # 正常更新（V4.5.15 修复：保护意图锁定的假设）
            if isinstance(hypothesis_confidences, dict):
                for hyp_id, confidence in hypothesis_confidences.items():
                    # 保护意图锁定的假设（置信度>=0.9）不被覆盖
                    # 检查直接匹配或反向映射匹配
                    should_protect = False
                    if locked_hypothesis:
                        if hyp_id == locked_hypothesis:
                            should_protect = True
                        elif reverse_hyp_map.get(locked_hypothesis) == hyp_id:
                            should_protect = True
                        elif reverse_hyp_map.get(hyp_id) == locked_hypothesis:
                            should_protect = True
                    
                    if should_protect:
                        logger.info(f"🔒 保护锁定假设：{locked_hypothesis}/{hyp_id} 保持{locked_confidence:.1f}，忽略 update_beliefs 返回的{confidence:.2f}")
                        continue
                    state.inferred_hypotheses[hyp_id] = confidence
            else:
                logger.warning(f"⚠️ hypothesis_confidences 类型错误：{type(hypothesis_confidences)}，跳过更新")
        
        # 6. V4.5.10 系统性重构：临床推理引擎驱动决策（增加已问字段跟踪）
        # === 第 1 优先级：推理引擎的主动鉴别提问 ===
        # V4.5.10 新增：计算已问字段
        asked_fields = {}
        import re
        for msg in state.conversation_history:
            if msg.get("role") == "ai":
                # Try to get field_id from the message first
                field_id = msg.get("field_id")
                if not field_id:
                    # Fallback: extract from message text
                    msg_text = msg.get("text", "")
                    if "field=" in str(msg_text):
                        match = re.search(r'field=(\w+)', str(msg_text))
                        if match:
                            field_id = match.group(1)
                if field_id:
                    asked_fields[field_id] = asked_fields.get(field_id, 0) + 1
        
        logger.info(f"📊 已问字段统计：{asked_fields}")
        
        # V4.5.11 新增：传递 conversation_history 供推理引擎使用
        reasoning_action = self.reasoning_engine.decide_next_question(
            filled_data_dict, 
            state.current_stage, 
            asked_fields,
            state.conversation_history,
        )
        
        # V4.5.14 修复：确保 reasoning_action 是字典
        if not isinstance(reasoning_action, dict):
            logger.error(f"⚠️ reasoning_action 类型错误：{type(reasoning_action)}，降级到工作流")
            action = self._decide_next_action_with_reasoning(state, None)
        elif reasoning_action.get("type") == "ASK_FIELD":
            # 推理引擎明确要求问某个问题，以验证某个假设
            target_field = reasoning_action.get("field_id")
            probing_hyp = reasoning_action.get("probing_hypothesis")
            if target_field:
                logger.info(f"🔍 推理引擎驱动提问：为验证假设 [{probing_hyp}]，询问字段 [{target_field}]")
                action = {
                    "type": "ASK_FIELD",
                    "field_id": target_field,
                    "probing_hypothesis": probing_hyp,
                    "source": "reasoning_engine",
                }
            else:
                # 推理引擎没有明确字段，降级到工作流
                action = self._decide_next_action_with_reasoning(state, reasoning_action)
        elif reasoning_action.get("type") == "GENERATE_REPORT":
            # 推理引擎判定假设已收敛
            logger.info(f"✅ 推理引擎判定假设已收敛，触发报告生成")
            action = {"type": "GENERATE_REPORT", "source": "reasoning_engine_converged"}
        else:
            # 降级到 V4.3 工作流收集缺失的必填字段
            action = self._decide_next_action_with_reasoning(state, reasoning_action)
        
        # V4.5.14 修复：确保 action 是字典
        if not isinstance(action, dict):
            logger.error(f"⚠️ action 类型错误：{type(action)}，使用默认值")
            action = {"type": "GENERATE_REPORT", "source": "error_fallback"}
        
        if action["type"] == "GENERATE_REPORT":
            # 生成报告
            response = self._generate_report(state)
            state.conversation_history.append({
                "role": "ai", 
                "text": response["message"], 
                "turn": state.turn_count,
                "field_id": "REPORT"  # V4.5.10 修复：报告生成不需要 field_id
            })
            self.sessions[state.session_id] = state
            return response
        
        elif action["type"] == "ASK_FIELD":
            # 生成问题
            field_id = action.get("field_id")
            probing_hypothesis = action.get("probing_hypothesis")
            
            if not field_id:
                # fallback：问必填字段
                required = self.framework.get_required_fields()
                field_id = next((f for f in required if not state.is_field_filled(f)), "antecedent")
            
            # V4.5.1 核心修复：传入 probing_hypothesis，让问题更精准
            question = self._generate_natural_question(state, field_id, probing_hypothesis)
            
            # 构建进度信息
            progress = {
                "current_stage": state.current_stage,
                "stage_completion": state.get_stage_completion_rate(state.current_stage, self.framework.data),
                "overall_completion": state.get_overall_completion_rate(self.framework.data),
                "filled_fields": [f for f, fv in state.filled_data.items() if fv.value],
                "next_field": field_id,
            }
            
            # V4.5.13 P1-04 新增：如果有情感回应，前置到问题前面
            if emotion_response:
                message = f"{emotion_response}\n\n{question}"
            else:
                message = question
            
            response = {
                "session_id": state.session_id,
                "status": "in_progress",
                "response_type": "follow_up",
                "message": message,
                "state": state.current_stage,
                "locked_hypothesis": max(state.inferred_hypotheses.items(), key=lambda x: x[1], default=(None, 0))[0],
                "progress": progress,
            }
            
            state.conversation_history.append({
                "role": "ai", 
                "text": message, 
                "turn": state.turn_count,
                "field_id": field_id  # V4.5.10 新增：记录所问字段
            })
            self.sessions[state.session_id] = state
            
            logger.info(f"V4.3 提问：field={field_id}, stage={state.current_stage}, question={question[:50]}...")
            return response
        
        # 默认响应（V4.5.10 防护：确保不返回空消息）
        response = {
            "session_id": state.session_id,
            "status": "in_progress",
            "response_type": "follow_up",
            "message": "能再详细描述一下吗？",
        }
        
        # V4.5.10 最终防护：如果 message 为空，使用默认问题
        if not response.get("message") or not response["message"].strip():
            # 尝试问一个必填字段
            required = self.framework.get_required_fields()
            missing = [f for f in required if not state.is_field_filled(f)]
            if missing:
                field_id = missing[0]
                response["message"] = self._generate_natural_question(state, field_id)
                response["field_id"] = field_id
                logger.warning(f"⚠️ 检测到空响应，使用默认问题：{field_id}")
            else:
                response["message"] = "能再详细描述一下吗？"
                logger.warning("⚠️ 检测到空响应，使用通用追问")
        
        return response
    
    # ========== V4.5.13 P1-04: 情感识别与回应 ==========
    EMOTION_PATTERNS = {
        "焦虑": {
            "keywords": ["担心", "着急", "不知道怎么办", "很困扰", "害怕", "焦虑", "急死了", "愁"],
            "response": "我理解您的担心。很多家长都遇到过类似情况，这是很正常的感受。我们会一起分析孩子的行为，找到适合的方法。",
        },
        "困惑": {
            "keywords": ["为什么", "怎么回事", "不明白", "不懂", "什么原因", "为啥", "搞不懂"],
            "response": "这个问题很好。让我帮您分析一下可能的原因。孩子的行为背后通常有特定的功能，我们一起梳理一下。",
        },
        "挫败": {
            "keywords": ["没用", "总是", "没办法", "试过了", "不行", "不管用", "没效果", "放弃了"],
            "response": "听起来您已经尝试了很多方法，这确实很不容易。您已经为孩子付出了很多努力，我们一起看看有没有新的角度和方法。",
        },
        "无助": {
            "keywords": ["不知道", "怎么办", "无助", "绝望", "太难了", "撑不住"],
            "response": "我能感受到您现在的压力。照顾有特殊需求的孩子确实很挑战，但您不是一个人在战斗。我们会一步步来，找到可行的方案。",
        },
    }
    
    def _detect_and_respond_emotion(self, user_input: str, turn_count: int) -> Optional[str]:
        """
        V4.5.13 P1-04 新增：检测情绪并生成回应
        
        Args:
            user_input: 用户输入
            turn_count: 对话轮次
            
        Returns:
            情感回应文本，如果没有检测到情绪则返回 None
        """
        # 只在首轮或关键节点回应，避免打断流程
        if turn_count > 1 and turn_count % 3 != 0:
            return None
        
        for emotion, data in self.EMOTION_PATTERNS.items():
            if any(kw in user_input for kw in data["keywords"]):
                logger.info(f"💙 检测到情绪：{emotion}")
                return data["response"]
        
        return None
    # ========== P1-04 结束 ==========
    
    def get_session(self, session_id: str) -> Optional[StructuredAssessmentState]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    def cleanup_session(self, session_id: str) -> bool:
        """清理会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"会话 {session_id} 已清理")
            return True
        return False
