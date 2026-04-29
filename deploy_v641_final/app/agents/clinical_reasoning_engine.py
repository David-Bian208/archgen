"""
临床推理引擎 V6.2 - LLM 驱动优化版
从 V6.1 优化而来，专注于效率提升

版本历史：
V6.1 - 2026-04-22: 首次 LLM 驱动版（5 次 LLM 调用）
V6.2 - 2026-04-22: 效率优化版（4 次 LLM 调用，合并 Step 2+3）

备份文件：app/agents/backups/clinical_reasoning_engine_v6.1_backup.py

核心变更（V6.2）：
1. 合并假设生成与证据检验（Step 2+3 → 1 次 LLM 调用）
2. 前端仍展示 5 步进度（用户体验不变）
3. 响应时间从 ~150 秒优化到 ~120 秒

核心变更（V6.1）：
1. 删除关键词库/模板库/策略库
2. 场景识别：LLM 分类（非关键词匹配）
3. 假设生成：LLM 动态生成（非预定义模板）
4. 证据检验：LLM 引用 + 规则验证
5. 机制解释：LLM 生成比喻（非预定义）
6. 干预策略：LLM 从机制推导（非策略库）

保留的质量底线：
- 证据必须引用用户原话
- 假设必须针对本案例
- 策略必须解释"为什么有效"
"""

import json
import logging
from typing import Optional
from dataclasses import dataclass, field
from typing import Dict, List, Any, Tuple

from app.llm.base import LLMClient

logger = logging.getLogger(__name__)


# V6.1 质量验证规则
QUALITY_VALIDATION_RULES = {
    "generic_terms": [
        "执行功能挑战",
        "社交沟通障碍",
        "感觉处理异常",
        "情绪调节困难",
        "认知灵活性不足",
    ],
    "vague_strategies": [
        "多练习",
        "耐心引导",
        "循序渐进",
        "给予支持",
        "适当帮助",
    ]
}


@dataclass
class ReasoningStep:
    """推理步骤结果"""
    step_number: int
    step_name: str
    result: Dict[str, Any]
    is_validated: bool = True
    validation_errors: List[str] = field(default_factory=list)


class ClinicalReasoningEngine:
    """
    临床推理引擎 V6.2 - LLM 驱动优化版
    
    核心方法：
    1. step1_scene_recognition(): LLM 场景识别
    2. step2_hypothesis_generation(): LLM 假设生成（V6.2: 与证据检验合并）
    3. step3_evidence_examination(): 证据检验（V6.2: 前端展示，实际已合并）
    4. step4_mechanism_explanation(): 机制解释
    5. step5_intervention_planning(): 干预策略
    6. _validate_llm_output(): 质量底线验证
    
    ⚠️ V6.2 优化：Step 2+3 合并为 1 次 LLM 调用（前端仍展示 2 步）
    ⚠️ 重要：所有 LLM 调用都是同步的（generate_json 是同步方法）
    """
    
    VERSION = "V6.3.1"
    
    def __init__(self, llm_client: LLMClient):
        """初始化临床推理引擎（V6.2 LLM 驱动优化）"""
        self.llm = llm_client
        self.current_hypotheses: List[Dict[str, Any]] = []
        logger.info(f"ClinicalReasoningEngine {self.VERSION} 初始化完成（ABC 引导 + 语义判断）")
    
    def _reset_hypotheses(self):
        """重置当前假设（V4.5 兼容方法）"""
        self.current_hypotheses = []
        logger.debug("假设已重置")
    
    def detect_user_intent(self, user_input: str) -> Optional[str]:
        """用户意图检测（V4.5 兼容方法，V6.1 简化版）"""
        # V6.1 简化：不执行意图检测，直接返回 None
        # 由 StructuredAssessorV4 的框架驱动流程处理
        return None
    
    def update_beliefs(self, user_input: str, filled_data: Dict) -> Dict[str, float]:
        """更新假设置信度（V4.5 兼容方法，V6.1 简化版）"""
        # V6.1 简化：返回默认值
        # 实际由 LLM 动态生成假设，不需要预定义 belief 更新
        return {"tangible_access": 0.5, "attention_seeking": 0.5, "escape_difficulty": 0.5}
    
    def decide_next_question(self, filled_data: Dict) -> Dict[str, Any]:
        """决定下一个问题（V4.5 兼容方法，V6.1 简化版）"""
        # V6.1 简化：返回 None
        # 实际由 ClinicalAssessmentFramework 驱动流程
        return None
    
    def generate_narrative(self, filled_data: Dict) -> str:
        """生成叙事报告（V4.5 兼容方法，V6.1 简化版）"""
        # V6.1 简化：返回空字符串
        # 实际由 5 步临床推理引擎生成报告
        return ""
    
    def run_full_reasoning(self, user_input: str) -> Dict[str, Any]:
        """
        执行完整的 5 步临床推理流程
        
        V6.2 优化：Step 2+3 合并为 1 次 LLM 调用（总调用从 5 次降为 4 次）
        前端仍展示 5 步进度（用户体验不变）
        
        Args:
            user_input: 用户输入的行为观察描述
            
        Returns:
            包含 5 步推理结果的字典
        """
        logger.info(f"🧠 开始 LLM 驱动临床推理 V6.2：输入长度={len(user_input)}，预期 4 次 LLM 调用")
        
        # Step 1: 场景识别（LLM，调用 1）
        step1_result = self._sync_step1_scene_recognition(user_input)
        step1 = ReasoningStep(
            step_number=1,
            step_name="场景识别",
            result=step1_result,
            is_validated=True
        )
        logger.info(f"✅ Step 1 完成：{step1_result['scene_type']}类 - {step1_result.get('scene_name', '未知')}")
        
        # V6.2 优化：Step 2+3 合并为 1 次 LLM 调用（调用 2）
        step2_result = self._sync_step2_hypothesis_generation(
            user_input,
            step1_result
        )
        hypotheses = step2_result.get("hypotheses", [])
        logger.info(f"✅ Step 2+3 完成（V6.2 合并调用）：生成{len(hypotheses)}个假设，已含证据检验")
        
        # V6.2 兼容：为前端展示 Step 3，从合并结果中提取证据检验数据
        step3_result = self._get_evidence_from_hypotheses(hypotheses)
        logger.info(f"✅ Step 3 数据提取完成：检验{len(step3_result.get('evidence_examination', []))}个假设")
        
        # Step 4: 机制解释（LLM，调用 3）
        step4_result = self._sync_step4_mechanism_explanation(
            user_input,
            step1_result,
            step3_result
        )
        logger.info("✅ Step 4 完成：生成机制解释")
        
        # Step 5: 干预策略（LLM，调用 4）
        step5_result = self._sync_step5_intervention_planning(
            user_input,
            step4_result
        )
        logger.info(f"✅ Step 5 完成：生成{len(step5_result.get('intervention_strategies', []))}个策略")
        
        # 整合 5 步结果
        full_result = {
            **step1_result,
            **step2_result,
            **step3_result,
            **step4_result,
            **step5_result
        }
        
        # 质量底线验证
        is_valid, validation_errors = self._validate_llm_output(full_result)
        
        _ = ReasoningStep(
            step_number=2,
            step_name="假设生成 + 证据检验 + 机制解释 + 干预策略",
            result=full_result,
            is_validated=is_valid,
            validation_errors=validation_errors
        )
        
        if validation_errors:
            logger.warning(f"⚠️ 质量验证发现{len(validation_errors)}个问题：{validation_errors}")
        else:
            logger.info("✅ 5 步推理完成，质量验证通过")
        
        return {
            "step1_scene_classification": step1,
            "step2_hypothesis_generation": ReasoningStep(
                step_number=2,
                step_name="假设生成",
                result=step2_result
            ),
            "step3_evidence_examination": ReasoningStep(
                step_number=3,
                step_name="证据检验",
                result=step3_result
            ),
            "step4_mechanism_explanation": ReasoningStep(
                step_number=4,
                step_name="机制解释",
                result=step4_result
            ),
            "step5_intervention_planning": ReasoningStep(
                step_number=5,
                step_name="干预策略",
                result=step5_result
            ),
            "full_result": full_result,
            "validation_passed": is_valid,
            "validation_errors": validation_errors
        }
    
    # ========== V6.1 异步方法（SSE 支持） ==========
    
    async def step1_scene_recognition(self, user_input: str) -> Dict[str, Any]:
        """V6.1 异步版本：场景识别"""
        return self._sync_step1_scene_recognition(user_input)
    
    async def step2_hypothesis_generation(self, user_input: str, scene_result: Dict) -> Dict[str, Any]:
        """V6.1 异步版本：假设生成"""
        return self._sync_step2_hypothesis_generation(user_input, scene_result)
    
    async def step3_evidence_examination(self, user_input: str, hypothesis_result: Dict) -> Dict[str, Any]:
        """V6.1 异步版本：证据检验"""
        return self._sync_step3_evidence_examination(user_input, hypothesis_result)
    
    async def step4_mechanism_explanation(self, user_input: str, scene_result: Dict, evidence_result: Dict) -> Dict[str, Any]:
        """V6.1 异步版本：机制解释"""
        return self._sync_step4_mechanism_explanation(user_input, scene_result, evidence_result)
    
    async def step5_intervention_planning(self, user_input: str, mechanism_result: Dict) -> Dict[str, Any]:
        """V6.1 异步版本：干预策略"""
        return self._sync_step5_intervention_planning(user_input, mechanism_result)
    
    # ========== 输入验证 ==========
    
    # V6.3 语义判断关键词列表（放在类级别，避免重复定义）
    BEHAVIOR_KEYWORDS = [
        # 情绪爆发型
        "哭", "叫", "打", "踢", "躺", "坐", "跑", "拒绝", "要求", "抢", "推", "咬",
        "发呆", "不看", "不理", "躺在地上", "大声哭", "尖叫", "不理人", "不回应",
        "不说话", "不爱说话", "哭闹", "发脾气", "情绪崩溃", "自我刺激", "重复行为", "转圈",
        "拍手", "摇晃", "撞头", "打人", "咬人", "推人", "抢东西",
        "做操", "听", "玩", "写", "画", "吃", "睡", "大哭", "大叫", "乱跑",
        # 认知错误型（新增）
        "看错", "搞反", "混淆", "弄错", "颠倒", "说反", "听反", "认错", "弄混", "分不清", "搞混",
        "说错", "做错", "写错", "读错", "记错", "理解错", "会错意", "搞错", "弄颠倒",
    ]
    
    SCENE_KEYWORDS = [
        "超市", "幼儿园", "学校", "家里", "客厅", "卧室", "车上", "餐厅", "公园", "排队",
        "教室", "做操", "吃饭", "睡觉", "玩游戏", "写作业", "练琴", "看电视", "商场",
        "上课", "做题", "考试", "学习", "读书", "写字", "画画", "手工", "活动",
        "在", "时", "时候", "地方", "场景", "情况", "环境", "活动",
        "上", "下", "里", "外", "旁边", "附近",
    ]
    
    GREETING_KEYWORDS = ["你好", "hi", "hello", "嗨", "在吗", "在不在", "您好", "hey"]
    
    MEANINGLESS_KEYWORDS = ["继续", "好的", "谢谢", "明白", "了解", "收到", "ok", "yes", "no", "嗯", "啊", "哦", "好", "行", "可以"]
    
    VAGUE_PATTERNS = [
        "一直有情绪", "经常发脾气", "总是哭", "不听话", "有问题",
        "最近不好", "表现不好", "有问题吗", "正常吗", "怎么办",
        "怎么样", "怎么了", "好不好", "可以吗", "最近一直",
        "一直这样", "总是这样",
    ]
    
    @staticmethod
    def analyze_input_quality(user_input: str) -> Dict[str, Any]:
        """
        V6.3 语义判断版输入质量分析
        
        用关键词检测判断输入信息完整性，替代 30 字阈值。
        方法放在引擎中，Chainlit 只负责展示。
        
        返回格式：
        {
            "valid": True/False,
            "quality": "complete" | "partial" | "vague",
            "reason": "拒绝原因（仅 valid=False 时）",
            "suggestion": "引导建议（仅 valid=False 时）"
        }
        """
        text = user_input.strip()
        
        # === 基础过滤 ===
        if len(text) < 5:
            return {
                "valid": False,
                "quality": "vague",
                "reason": "输入内容过短，请描述具体的行为表现",
                "suggestion": "请描述您观察到的孩子行为，例如：孩子在超市里突然大哭、无法安静等待"
            }
        
        if text.lower() in ClinicalReasoningEngine.GREETING_KEYWORDS:
            return {
                "valid": False,
                "quality": "vague",
                "reason": "这是问候语，不是行为描述",
                "suggestion": "请描述您观察到的孩子行为，我会为您进行专业分析"
            }
        
        if text.lower() in ClinicalReasoningEngine.MEANINGLESS_KEYWORDS:
            return {
                "valid": False,
                "quality": "vague",
                "reason": "这是一个简单回复，不是行为描述",
                "suggestion": "请描述您观察到的孩子行为，我会为您进行专业分析"
            }
        
        # === 关键词检测 ===
        has_behavior = any(kw in text for kw in ClinicalReasoningEngine.BEHAVIOR_KEYWORDS)
        has_scene = any(kw in text for kw in ClinicalReasoningEngine.SCENE_KEYWORDS)
        
        # === 语义判断逻辑 ===
        if has_behavior and has_scene:
            # 有行为动词 + 有场景词 = 完整，直接推理
            return {
                "valid": True,
                "quality": "complete",
                "reason": None,
                "suggestion": None
            }
        
        elif has_behavior or has_scene:
            # 有行为动词 或 有场景词（缺一个）= 部分，引导补充
            return {
                "valid": True,
                "quality": "partial",
                "reason": None,
                "suggestion": "建议补充更多细节以获得更精准的分析"
            }
        
        else:
            # 只有情绪词 或 无具体描述 = 模糊，触发 ABC 教育
            # V6.4 新增：LLM 兜底判断
            llm_result = ClinicalReasoningEngine._llm_fallback_check(user_input)
            if llm_result.get("has_concrete_description"):
                # LLM 认为有具体描述 → 升级为 complete
                return {
                    "valid": True,
                    "quality": "complete",
                    "reason": None,
                    "suggestion": None
                }
            else:
                # LLM 确认模糊 → 触发 ABC 教育
                return {
                    "valid": False,
                    "quality": "vague",
                    "reason": "您的描述比较笼统，缺乏具体场景和行为细节",
                    "suggestion": "请描述孩子最近一次让您担心的具体行为场景，包括：在哪里？发生了什么？孩子具体做了什么？"
                }
    
    @staticmethod
    def validate_input(user_input: str) -> Dict[str, Any]:
        """
        V6.3 保留向后兼容的验证方法
        
        内部调用 analyze_input_quality() 保持统一判断逻辑。
        保留此方法是为了避免破坏现有调用点。
        """
        result = ClinicalReasoningEngine.analyze_input_quality(user_input)
        
        # 兼容旧格式：valid 字段和 suggestion 字段
        if not result.get("valid", True):
            return {
                "valid": False,
                "reason": result.get("reason", ""),
                "suggestion": result.get("suggestion", "")
            }
        return {"valid": True}
    
    # ========== V6.1 同步方法（内部实现） ==========
    
    def _sync_step1_scene_recognition(self, user_input: str) -> Dict[str, Any]:
        """
        Step 1: LLM 场景识别
        
        使用 LLM 识别场景类型（A/B/C/D），而非关键词匹配
        
        场景分类：
        - A 类：社交互动与沟通（介绍朋友、轮流对话）
        - B 类：认知与心智理论（薯片盒子游戏、错误信念）
        - C 类：执行功能与灵活性（规则变化、过渡困难）
        - D 类：感觉处理与自我调节（听觉过敏、情绪崩溃）
        
        ⚠️ 注意：generate_json 是同步方法，不能用 await！
        """
        prompt = f"""请分析以下用户输入，识别场景类型并提取 ABC 行为分析要素。

场景类型选项：
- A 类 - 社交互动与沟通（介绍朋友、轮流对话、社交发起等）
- B 类 - 认知与心智理论（[错误信念]、[视角采择]、[意图理解]等）
- C 类 - 执行功能与灵活性（规则变化、过渡困难、计划组织等）
- D 类 - 感觉处理与自我调节（听觉过敏、情绪崩溃、自我刺激等）

用户输入：{user_input}

【ABC 行为分析提取要求】
从用户输入中提取以下信息（如果没有明确描述，填"未提及"）：
- **A (Antecedent 前因)**: 行为发生前的事件或情境
- **B (Behavior 行为)**: 孩子表现出的具体行为
- **C (Consequence 后果)**: 行为发生后产生的结果或反应

【重要要求】
1. 所有关键术语必须用 [] 标注（如 [错误信念]、[视角采择]、[前额叶皮层]）
2. 识别依据必须引用用户原话
3. ABC 提取要忠于用户描述，不要臆测

请以 JSON 格式输出：
{{
    "scene_type": "A/B/C/D",
    "scene_name": "场景名称",
    "core_challenge": "核心挑战定义（1 句话）",
    "recognition_basis": "识别依据（引用用户原话）",
    "abc_analysis": {{
        "antecedent": "前因描述",
        "behavior": "行为描述",
        "consequence": "后果描述"
    }}
}}
"""
        
        try:
            # ✅ 同步调用 LLM（generate_json 是同步方法）
            result = self.llm.generate_json(
                system_prompt="你是一位儿童行为临床专家。只输出 JSON，不要解释。",
                user_prompt=prompt,
                temperature=0.1,
                max_tokens=500
            )
            
            # 验证输出格式
            if not isinstance(result, dict):
                logger.error(f"场景分类返回非字典：{type(result)}")
                return self._get_fallback_scene_classification()
            
            # 验证 scene_type
            scene_type = result.get('scene_type', 'A')
            if scene_type not in ['A', 'B', 'C', 'D']:
                logger.warning(f"场景类型无效：{scene_type}，默认使用 A")
                result['scene_type'] = 'A'
            
            return result
            
        except Exception as e:
            logger.error(f"场景分类失败：{e}")
            return self._get_fallback_scene_classification()
    
    def _sync_step2_hypothesis_generation(
        self,
        user_input: str,
        scene_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        V6.2 优化：假设生成 + 证据检验（合并为 1 次 LLM 调用）
        
        基于场景类型和用户输入，生成 2-3 个具体假设，并对每个假设进行证据检验。
        
        质量要求：
        1. 假设必须提供专业解释（不是只引用原话）
        2. 假设必须聚焦认知过程的具体缺陷
        3. 每个假设必须包含置信度（0.3-0.9）
        4. 证据精简引用用户原话
        5. 所有关键术语必须用 [] 标注
        
        ⚠️ V6.2 优化：合并 Step 2+3，从 2 次调用降为 1 次
        ⚠️ 注意：generate_json 是同步方法，不能用 await！
        """
        prompt = f"""你是 BCBA 督导，请基于以下场景和用户输入，生成 2-3 个具体假设，并对每个假设进行证据检验。

【场景类型】
{scene_result.get('scene_type')}类 - {scene_result.get('scene_name', '未知')}
核心挑战：{scene_result.get('core_challenge', '未知')}

【用户输入】
{user_input}

【任务要求】
1. 生成 2-3 个假设（每个必须针对本案例，非通用框架）
2. 每个假设必须包含：
   - **专业解释**：从认知心理学/行为分析角度，解释具体是哪个认知环节出现问题
   - **证据**：精简引用用户原话（1 句话以内）
   - **置信度**（0.3-0.9）
   - **决策**（保留/排除）
3. 所有关键术语必须用 [] 标注（如 [错误信念]、[视角采择]、[抑制控制]）

【假设示例】
好假设："儿童在 [抑制控制] 方面存在困难，无法抑制自己已知的信息（糖果），导致 [投射偏差]"
差假设："儿童理解他人视角有困难"（太笼统，没有专业解释）

【输出格式】
{{
    "hypotheses": [
        {{
            "id": "H1",
            "content": "专业解释：从认知角度说明具体是哪个环节出问题",
            "confidence": 0.8,
            "supporting_evidence": ["精简引用用户原话"],
            "contradicting_evidence": ["无"],
            "decision": "保留",
            "reason": ""
        }}
    ]
}}
"""
        
        try:
            # ✅ 同步调用 LLM（1 次调用完成假设生成 + 证据检验）
            combined = self.llm.generate_json(
                system_prompt="你是 BCBA 督导，擅长生成具体、专业的认知假设。只输出 JSON，不要解释。",
                user_prompt=prompt,
                temperature=0.3,
                max_tokens=1500
            )
            
            # 验证输出格式
            if not isinstance(combined, dict):
                logger.error(f"假设生成+证据检验返回非字典：{type(combined)}")
                return self._get_fallback_hypotheses()
            
            hypotheses = combined.get("hypotheses", [])
            
            # 验证每个假设的字段
            for h in hypotheses:
                if "content" not in h:
                    h["content"] = "需要进一步评估"
                if "confidence" not in h:
                    h["confidence"] = 0.5
                if "supporting_evidence" not in h:
                    h["supporting_evidence"] = []
                if "contradicting_evidence" not in h:
                    h["contradicting_evidence"] = ["无"]
                if "decision" not in h:
                    h["decision"] = "保留"
                if "reason" not in h:
                    h["reason"] = ""
            
            return {
                "hypotheses": hypotheses,
                "_v62_combined": True  # 标记：V6.2 合并输出
            }
            
        except Exception as e:
            logger.error(f"假设生成+证据检验失败：{e}")
            return self._get_fallback_hypotheses()
    
    # V6.2 兼容方法：为了保持 API 接口不变，提供单独的方法提取数据
    def _get_evidence_from_hypotheses(self, hypotheses: List[Dict]) -> Dict[str, Any]:
        """从合并的假设数据中提取证据检验结果（用于前端展示 Step 3）"""
        evidence_examination = []
        for h in hypotheses:
            evidence_examination.append({
                "hypothesis_id": h.get("id", "未知"),
                "supporting_evidence": h.get("supporting_evidence", []),
                "contradicting_evidence": h.get("contradicting_evidence", ["无"]),
                "decision": h.get("decision", "保留"),
                "reason": h.get("reason", "")
            })
        return {"evidence_examination": evidence_examination}
    
    def _sync_step3_evidence_examination(
        self,
        user_input: str,
        hypothesis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Step 3: 证据检验与排除
        
        对每个假设进行支持/反对证据分析，排除证据最弱的假设
        
        ⚠️ 注意：generate_json 是同步方法，不能用 await！
        """
        hypotheses = hypothesis_result.get("hypotheses", [])
        
        prompt = f"""你是临床推理专家，请对以下假设进行证据检验。

【用户输入】
{user_input}

【待检验假设】
{json.dumps(hypotheses, ensure_ascii=False, indent=2)}

【检验规则】
1. 支持证据必须引用用户原话
2. 反对证据可以是"无"
3. 排除证据最弱的假设
4. 决策选项：保留/排除

请以 JSON 格式输出检验结果：
{{
    "evidence_examination": [
        {{
            "hypothesis_id": "H1",
            "supporting_evidence": ["用户原话 1", "用户原话 2"],
            "contradicting_evidence": ["用户原话或无"],
            "decision": "保留/排除",
            "reason": "排除理由"
        }}
    ]
}}
"""
        
        try:
            # ✅ 同步调用 LLM（generate_json 是同步方法）
            examination = self.llm.generate_json(
                system_prompt="你是临床推理专家，擅长证据检验。只输出 JSON，不要解释。",
                user_prompt=prompt,
                temperature=0.2,
                max_tokens=1500
            )
            
            if not isinstance(examination, dict):
                logger.error(f"证据检验返回非字典：{type(examination)}")
                return {"evidence_examination": []}
            
            return {"evidence_examination": examination.get("evidence_examination", [])}
            
        except Exception as e:
            logger.error(f"证据检验失败：{e}")
            return {"evidence_examination": []}
    
    def _sync_step4_mechanism_explanation(
        self,
        user_input: str,
        scene_result: Dict[str, Any],
        evidence_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Step 4: 深度机制解释
        
        使用新颖比喻解释认知机制，避免术语堆砌
        
        ⚠️ 注意：generate_json 是同步方法，不能用 await！
        """
        prompt = f"""你是发展心理学专家，请基于以下信息生成深度机制解释。

【场景类型】
{scene_result.get('scene_type')}类 - {scene_result.get('scene_name', '未知')}

【用户输入】
{user_input}

【证据检验结果】
{json.dumps(evidence_result.get('evidence_examination', []), ensure_ascii=False, indent=2)}

【质量要求】
1. 使用新颖比喻（避免术语堆砌），比喻要生动、易懂
2. 链接具体认知构造（如 [执行功能]、[抑制控制]、[心智理论]）
3. 包含发展视角（当前阶段 + 未来预期）
4. 所有关键术语必须用 [] 标注（如 [错误信念]、[前额叶皮层]、[工作记忆]、[抑制控制]、[执行功能]）

请以 JSON 格式输出：
{{
    "cognitive_mechanism": "认知机制解释",
    "metaphor": "新颖比喻",
    "developmental_perspective": "发展视角"
}}
"""
        
        try:
            # ✅ 同步调用 LLM（generate_json 是同步方法）
            mechanism = self.llm.generate_json(
                system_prompt="你是发展心理学专家，擅长用生动比喻解释认知机制。只输出 JSON，不要解释。",
                user_prompt=prompt,
                temperature=0.4,
                max_tokens=1000
            )
            
            if not isinstance(mechanism, dict):
                logger.error(f"机制解释返回非字典：{type(mechanism)}")
                return self._get_fallback_mechanism()
            
            return mechanism
            
        except Exception as e:
            logger.error(f"机制解释失败：{e}")
            return self._get_fallback_mechanism()
    
    def _sync_step5_intervention_planning(
        self,
        user_input: str,
        mechanism_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Step 5: 精准干预策略
        
        从机制直接衍生策略，解释"为什么有效"
        
        ⚠️ 注意：generate_json 是同步方法，不能用 await！
        """
        prompt = f"""你是 BCBA 督导，请基于以下机制解释生成精准干预策略。

【机制解释】
认知机制：{mechanism_result.get('cognitive_mechanism', '未知')}
比喻：{mechanism_result.get('metaphor', '未知')}
发展视角：{mechanism_result.get('developmental_perspective', '未知')}

【质量要求】
1. 策略针对机制（非维度匹配）
2. 解释"为什么有效"
3. 绑定场景要素（个性化）
4. 策略数量：2-3 个

请以 JSON 格式输出策略列表：
{{
    "intervention_strategies": [
        {{
            "name": "策略名称",
            "description": "具体做法",
            "why_effective": "为什么有效（从机制推导）",
            "based_on_mechanism": "基于的机制"
        }}
    ]
}}
"""
        
        try:
            # ✅ 同步调用 LLM（generate_json 是同步方法）
            strategies = self.llm.generate_json(
                system_prompt="你是 BCBA 督导，擅长从机制推导精准策略。只输出 JSON，不要解释。",
                user_prompt=prompt,
                temperature=0.3,
                max_tokens=1500
            )
            
            if not isinstance(strategies, dict):
                logger.error(f"干预策略返回非字典：{type(strategies)}")
                return self._get_fallback_strategies()
            
            return {"intervention_strategies": strategies.get("intervention_strategies", [])}
            
        except Exception as e:
            logger.error(f"干预策略失败：{e}")
            return self._get_fallback_strategies()
    
    def _validate_llm_output(self, output: dict) -> Tuple[bool, List[str]]:
        """
        质量底线验证
        
        验证规则：
        1. 假设必须有证据引用（V6.2: 检查 supporting_evidence 或 evidence）
        2. 机制解释必须有比喻
        3. 策略必须解释"为什么有效"
        
        Returns:
            (是否通过验证，错误列表)
        """
        errors = []
        
        # 1. 检查 Step 2：假设必须有证据引用
        for hyp in output.get("hypotheses", []):
            # V6.2 兼容：同时检查 evidence 和 supporting_evidence
            has_evidence = (
                hyp.get("evidence") or 
                hyp.get("supporting_evidence") or
                (isinstance(hyp.get("supporting_evidence"), list) and len(hyp.get("supporting_evidence", [])) > 0)
            )
            if not has_evidence:
                errors.append(f"假设{hyp.get('id', '未知')}缺少证据引用")
        
        # 2. 检查 Step 4：机制解释必须有比喻
        if not output.get("metaphor"):
            errors.append("机制解释缺少比喻")
        
        # 3. 检查 Step 5：策略必须解释"为什么有效"
        for strategy in output.get("intervention_strategies", []):
            if not strategy.get("why_effective"):
                errors.append(f"策略'{strategy.get('name', '未知')}'缺少有效性解释")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def _get_fallback_scene_classification(self) -> Dict[str, Any]:
        """降级场景分类方案"""
        return {
            "scene_type": "A",
            "scene_name": "未分类场景",
            "core_challenge": "需要进一步评估",
            "recognition_basis": "场景分类失败，使用默认值",
            "abc_analysis": {
                "antecedent": "未提及",
                "behavior": "未提及",
                "consequence": "未提及"
            }
        }
    
    def _get_fallback_hypotheses(self) -> Dict[str, Any]:
        """降级假设生成方案（V6.2 兼容格式）"""
        return {
            "hypotheses": [
                {
                    "id": "H1",
                    "content": "需要进一步评估",
                    "confidence": 0.5,
                    "supporting_evidence": [],
                    "contradicting_evidence": ["无"],
                    "decision": "保留",
                    "reason": "假设生成失败，使用默认值"
                }
            ],
            "_v62_combined": True
        }
    
    def _get_fallback_evidence_examination(self) -> Dict[str, Any]:
        """降级证据检验方案（V6.2 不再需要，保留兼容）"""
        return {
            "evidence_examination": [
                {
                    "hypothesis_id": "H1",
                    "supporting_evidence": ["需要进一步评估"],
                    "contradicting_evidence": ["无"],
                    "decision": "保留",
                    "reason": "证据检验失败，使用默认值"
                }
            ]
        }
    
    def _get_fallback_mechanism(self) -> Dict[str, Any]:
        """降级机制解释方案"""
        return {
            "cognitive_mechanism": "需要进一步评估",
            "metaphor": "需要进一步评估",
            "developmental_perspective": "需要进一步评估"
        }
    
    def _get_fallback_strategies(self) -> Dict[str, Any]:
        """降级干预策略方案"""
        return {
            "intervention_strategies": [
                {
                    "name": "进一步评估",
                    "description": "收集更多信息",
                    "why_effective": "需要更多信息才能制定策略",
                    "based_on_mechanism": "未知"
                }
            ]
        }
    
    @staticmethod
    def confidence_label(confidence: float) -> str:
        """V6.3.1 将数值置信度转换为定性描述"""
        if confidence >= 0.7:
            return "较可能"
        elif confidence >= 0.5:
            return "有可能"
        else:
            return "需更多观察"

    def generate_report(self, reasoning_result: Dict[str, Any], show_ending: bool = True) -> str:
        """
        基于推理结果生成最终报告
        
        将 5 步推理整合为温暖的叙事性报告
        
        Args:
            reasoning_result: 推理结果（包含 step1-5）
            show_ending: 是否在报告末尾显示会话结束语
        """
        full_result = reasoning_result.get('full_result', reasoning_result)
        
        step1 = full_result.get('step1', full_result)
        step2 = full_result.get('step2', full_result)
        step4 = full_result.get('step4', full_result)
        step5 = full_result.get('step5', full_result)
        
        scene_type = step1.get('scene_type', 'A')
        scene_name = step1.get('scene_name', '未分类场景')
        core_challenge = step1.get('core_challenge', '需要进一步评估')
        hypotheses = step2.get('hypotheses', [])
        strategies = step5.get('intervention_strategies', [])
        abc = step1.get('abc_analysis', {})
        
        antecedent = abc.get('antecedent', '未提及')
        behavior = abc.get('behavior', '未提及')
        consequence = abc.get('consequence', '未提及')
        
        report = f"""# 行为观察分析报告

## 场景理解
这是一个 **{scene_name}** 场景。
核心挑战：{core_challenge}

## ABC 行为分析

| 要素 | 描述 |
|------|------|
| **A 前因** | {antecedent} |
| **B 行为** | {behavior} |
| **C 后果** | {consequence} |

## 我们的推理

### 行为假设
"""
        
        for i, hyp in enumerate(hypotheses, 1):
            conf = hyp.get('confidence', 0)
            label = ClinicalReasoningEngine.confidence_label(conf)
            content = hyp.get('content', '').replace('专业解释：', '')
            report += f"\n{i}. {content}（{label}）"
            if hyp.get('supporting_evidence'):
                evidence_list = hyp['supporting_evidence']
                if isinstance(evidence_list, list) and evidence_list:
                    report += f"\n  证据：\"{evidence_list[0]}\""
        
        report += f"""

### 深层机制
{step4.get('cognitive_mechanism', '需要进一步评估')}

**比喻**: {step4.get('metaphor', '需要进一步评估')}

**发展视角**: {step4.get('developmental_perspective', '需要进一步评估')}

## 安全提示

> 在尝试以下策略前，请确认孩子的基本需求已满足：
> - 睡眠充足（未过度疲劳）
> - 饮食正常（未饥饿或过饱）
> - 身体健康（无生病、疼痛等不适）
>
> 如孩子当前情绪极度不稳定，请先安抚情绪，再实施干预。
> **所有干预都建立在安全的情感连接之上。如任何策略导致孩子更抗拒或您更焦虑，请暂停，优先修复关系。**

## 建议策略

"""
        
        for i, strategy in enumerate(strategies, 1):
            report += f"""
### 策略{i}: {strategy['name']}
**具体做法**: {strategy['description']}

**为什么有效**: {strategy.get('why_effective', strategy.get('effectiveness_explanation', '基于机制推导'))}
"""
        
        if strategies:
            report += """
> 💡 **个性化适配提醒**：以上策略为通用建议。实施前请评估您孩子的能力水平：
> - 如孩子还不能理解情绪词汇，请先从非语言策略（如环境调整）开始
> - 如孩子对特定策略表现出抗拒，请暂停并尝试其他方式
> - 干预效果因个体差异而异，建议循序渐进，每次只尝试 1-2 种策略

"""
        
        if show_ending:
            report += """
---

> 📋 **本次分析结束**。如需进一步评估，请描述新的行为观察内容。
> 每次提问将开启一次独立的行为诊断分析。

> ⚠️ **免责声明**：本分析基于单次行为观察，仅供参考。行为分析需要多次观察才能发现规律，建议您记录未来 2-3 次类似情况，并注意：
> - 是否总是在特定场景发生？
> - 孩子是否有先兆行为（如捂耳朵、烦躁）？
> - 您的处理方式对行为有什么影响？
>
> **AI 分析不能替代专业评估。如需正式诊断请咨询专业人士。**
"""
        
        return report
    
    def get_hypothesis_status(self) -> Dict[str, Any]:
        """获取推理状态（用于调试）"""
        return {
            "engine_version": "V6.1",
            "driving_mode": "LLM-driven",
            "knowledge_base_required": False,
            "maintenance_cost": "minimal"
        }
