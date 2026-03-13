"""
洞察分析器 V3.0 - V4.5.13 个性化报告版
从"行为分类"升级为"共情洞察"

核心理念：
- 不是输出标签，而是生成洞察
- 不是事实复述，而是行为理解
- 不是专业术语，而是家长能懂的"金句"

V4.5.13 新增：
- 家长用语风格检测（专业 vs 日常）
- 个性化报告语言调整
- 详细版/简洁版选项
"""

import json
import logging
import re
from typing import Optional, Dict, Any

from app.llm.base import LLMClient

logger = logging.getLogger(__name__)


# ========== V4.5.13 P1-03: 家长用语风格检测 ==========
class ParentStyleDetector:
    """家长用语风格检测器"""
    
    # 专业术语关键词
    PROFESSIONAL_TERMS = [
        "前因", "后果", "强化", "消退", "ABC", "功能分析",
        "行为功能", "逃避", "寻求关注", "感觉统合", "感统",
        "刻板行为", "自我刺激", "提示", "辅助", "泛化",
        "工作记忆", "执行功能", "注意力缺陷", "感统失调"
    ]
    
    # 日常用语关键词
    CASUAL_TERMS = [
        "之前", "然后", "之后", "奖励", "不理", "什么时候",
        "老是", "总是", "就是", "好像", "感觉", "觉得",
        "孩子他", "我家", "老师他", "不知道咋办"
    ]
    
    @classmethod
    def detect_style(cls, conversation_history: list) -> str:
        """
        检测家长用语风格
        
        Args:
            conversation_history: 对话历史
            
        Returns:
            "professional" (专业) 或 "casual" (日常)
        """
        all_text = " ".join([
            msg.get("text", "") 
            for msg in conversation_history 
            if msg.get("role") == "user"
        ])
        
        prof_count = sum(1 for term in cls.PROFESSIONAL_TERMS if term in all_text)
        casual_count = sum(1 for term in cls.CASUAL_TERMS if term in all_text)
        
        # 句子长度和复杂度
        sentences = [s.strip() for s in re.split(r'[。！？!?]', all_text) if s.strip()]
        avg_sentence_length = sum(len(s) for s in sentences) / len(sentences) if sentences else 0
        
        style = "professional" if prof_count > casual_count else "casual"
        
        # 长句子 + 专业术语 → 更可能是专业人士
        if avg_sentence_length > 30 and prof_count >= 2:
            style = "professional"
        
        logger.info(f"📊 家长用语风格检测：{style} (专业术语={prof_count}, 日常用语={casual_count}, 平均句长={avg_sentence_length:.1f})")
        return style
    
    @classmethod
    def get_style_prompt_suffix(cls, style: str) -> str:
        """
        根据风格返回 Prompt 后缀
        
        Args:
            style: 用语风格 ("professional" 或 "casual")
            
        Returns:
            Prompt 后缀
        """
        if style == "professional":
            return """
【语言风格要求】
- 使用专业术语（如"前因"、"后果"、"强化"、"功能分析"）
- 保持专业严谨，但要有温度
- 可以适当使用专业概念解释
- 长度：详细版（150-200 字）"""
        else:
            return """
【语言风格要求】
- 使用日常语言，避免专业术语
- 用"之前/然后/之后"代替"前因/后果"
- 用"奖励"代替"强化"，用"不理"代替"消退"
- 多用比喻和金句，说进家长心坎里
- 长度：简洁版（80-120 字）"""


class InsightAnalyzer:
    """
    洞察分析器 V3.0
    
    三步推理链：
    1. 功能判断（内在逻辑）- 不直接输出术语
    2. 深度归因（动机与能力）- 区分"不想做"vs"做不到"
    3. 提炼核心洞察 - 给家长的"金句"
    """

    # V4.5.7 分析 Prompt - 矛盾证据优先处理版
    ANALYSIS_SYSTEM_PROMPT = """你是一位经验丰富的 BCBA 督导，正在将观察转化为对家长有启发的洞察。

你的任务是：
1. 进行专业的"专家拆解"（内部分析）- 精准判断功能
2. 将专业分析"翻译"成家长能懂的语言（对外沟通）- 有温度、有观点
3. 展现临床鉴别思考过程 - 说明为什么排除其他可能性

【P0 关键规则 - 矛盾证据优先处理】
当用户描述中出现以下"能力完备"关键词时，必须优先处理：
- 关键词："都会做"、"已经会"、"自己能"、"不需要帮助"、"能做好"
- 处理规则：
  1. 立即降低"提示依赖"假设置信度至 30% 以下
  2. 立即提升"寻求关注"或"获得社会性确认"假设置信度至 70% 以上
  3. 在鉴别诊断中明确说明："由于孩子具备完成任务的能力，'叫家长'行为的主要功能更可能是获取关注而非获取提示"

【关键分析原则 - 寻求关注鉴别】
当行为模式满足以下特征时，应判断为"寻求关注"而非"提示依赖"：
- 孩子在成人注意力分散时（打电话、招待客人）故意制造问题行为
- 关键线索："其实都会做"、"不需要帮助就能完成" → 排除提示依赖（P0 规则）
- 行为目的：获取成人注意力，而非获取任务执行提示
- 能力缺口：恰当的社交沟通技能（如何用适当方式获取关注）
- 鉴别性问题："他叫您的时候，主要是需要您帮助解题，还是只是想让您看看他？"

【关键分析原则 - 提示依赖鉴别】
当行为模式表现为"有提示则执行，无提示则中断/发呆"，且任务具有明确的社会性目标时：
- 首要功能假设应从"自动强化"修正为"在提示依赖下的逃避（任务失败/认知负荷）"
- 这是特殊形式的"逃避"——逃避的是因提示中断而导致的"任务执行失败"或"认知过载"
- 能力缺口：工作记忆（记不住多步骤序列）和持续性注意（无法在提示间隙自我维持任务表征）
- 环境整合：嘈杂、拥挤等环境因素会加剧对单一、清晰视觉提示的依赖

【临床鉴别思考要求】
在生成报告时，需要简要说明鉴别诊断过程：针对观察到的行为，临床上通常会考虑几种可能性（如提示依赖、寻求关注、自我刺激、感觉逃避等），然后说明为什么结合当前信息判断某种可能性最高。

【V4.3 字段兼容性要求】
请严格按照以下 JSON 格式输出，确保所有字段都存在：
{
    "functional_judgment": "首要功能判断，如'提示依赖下的逃避'、'逃避难度任务'、'寻求关注'等",
    "core_insight": "用一句'金句'直击本质，说进家长心坎里。例如：'孩子不是不专心，而是他的动作记忆像手机需要实时充电。'",
    "capability_hypothesis": "这可能反映了哪方面的能力挑战，如'工作记忆和持续性注意方面的挑战'",
    "clinical_differential": "针对观察到的行为，说明临床上通常考虑的几种可能性，然后结合当前信息说明为什么某种可能性最高。100-200 字。",
    "intervention_principle": "针对最可能的假设，提出具体的干预原则，如'将外部提示转化为内部提示'",
    "expert_breakdown": {
        "behavior_pattern": "一句话命名该行为模式",
        "functional_hypothesis": "功能假设详细说明",
        "capability_gap": "能力缺口分析",
        "contextual_factors": "环境因素如何影响行为"
    },
    "core_insight_for_parent": "与 core_insight 相同的核心洞察",
    "strategy_principle": "与 intervention_principle 相同的干预原则",
    "reasoning_brief": "简短的专业推理（50 字以内）"
}"""

    ANALYSIS_USER_PROMPT_TEMPLATE = """请基于以下观察信息，进行专家拆解与共情翻译：

【观察信息】
- 环境：{environment}
- 情境：{antecedent}
- 孩子的表现：{behavior}
- 当时的回应：{consequence}

【你的分析任务】
1. **专家拆解（专业视角）**：
   - 识别模式：这是"有提示则执行，无提示则中断"的提示依赖行为吗？
   - 功能判断：如果是，主要功能是"提示依赖下的逃避"而非"自动强化"
   - 能力缺口：工作记忆和/或持续性注意的挑战
   - 环境因素：环境如何加剧了对视觉提示的依赖

2. **共情翻译（家长视角）**：
   - 核心洞察：用"金句"直击本质，说进家长心坎里
   - 干预原则："将外部提示转化为内部提示"

请输出 JSON 格式的分析结果。"""

    # V3.6 鉴别诊断分析 Prompt - 临床深度增强版
    ANALYSIS_WITH_DIFFERENTIAL_TEMPLATE = """请基于以下观察信息和竞争性假设，进行鉴别诊断分析：

【观察信息】
- 环境：{environment}
- 情境：{antecedent}
- 孩子的表现：{behavior}
- 当时的回应：{consequence}
- 用户补充的鉴别细节：{discriminating_answer}

【竞争性假设】
{hypotheses_json}

【你的分析任务】
请参考提供的专业假设，根据所有信息评估每种假设的可能性：
1. 逐一评估每个假设的支持证据和不支持证据
2. 给出一个综合性的、有层次的分析：哪个假设可能性最高，为什么
3. 同时考虑其他假设是否可能部分存在
4. 基于最可能的假设，给出核心洞察和干预原则
5. 生成临床鉴别思考：说明鉴别诊断过程

请严格按照以下 JSON 格式输出：
{{
    "expert_breakdown": {{
        "behavior_pattern": "一句话命名该行为模式",
        "functional_hypothesis": "基于鉴别诊断，判断最可能的功能，并说明推理",
        "capability_gap": "分析这可能反映了哪方面的能力挑战",
        "contextual_factors": "简述环境因素如何影响行为",
        "differential_reasoning": "简述鉴别诊断过程：为什么 HX 可能性最高，其他假设的可能性如何"
    }},
    "clinical_differential": "针对观察到的行为，说明临床上通常考虑的几种可能性（参考竞争性假设），然后结合当前观察信息（如用户的鉴别细节）说明为什么某种可能性最高。100-200 字。",
    "core_insight_for_parent": "基于专家拆解，用一句'金句'直击本质，说进家长心坎里",
    "strategy_principle": "针对最可能的假设，提出具体的干预原则",
    "reasoning_brief": "简短的专业推理（50 字以内）"
}}"""

    def __init__(self, llm_client: LLMClient):
        """
        初始化洞察分析器

        Args:
            llm_client: LLM 客户端实例
        """
        self.llm = llm_client
        logger.info("InsightAnalyzer V3.0 初始化完成")

    def analyze(self, environment: str, antecedent: str, behavior: str, consequence: str, competing_hypotheses: Optional[list] = None, discriminating_answer: str = "", conversation_history: Optional[list] = None, report_style: Optional[str] = None) -> dict:
        """
        执行三步推理分析（V4.5.13 - 个性化报告版）

        Args:
            environment: 环境上下文
            antecedent: 情境（前因）
            behavior: 孩子的表现（行为）
            consequence: 当时的回应（后果）
            competing_hypotheses: 竞争性假设列表（可选）
            discriminating_answer: 用户对鉴别性问题的回答（可选）
            conversation_history: 对话历史（用于检测家长用语风格）
            report_style: 报告风格 ("professional"/"casual"，不传则自动检测)

        Returns:
            洞察分析结果
        """
        logger.info(f"开始洞察分析：环境={environment[:30] if environment else '无'}, 情境={antecedent[:30]}..., 行为={behavior[:30]}...")
        
        # V4.5.13 新增：检测家长用语风格
        if report_style is None and conversation_history:
            report_style = ParentStyleDetector.detect_style(conversation_history)
        elif report_style is None:
            report_style = "casual"  # 默认日常风格
        
        style_suffix = ParentStyleDetector.get_style_prompt_suffix(report_style)
        logger.info(f"📝 报告风格：{report_style}")

        # V3.4 新增：如果有竞争性假设，使用鉴别诊断 Prompt
        if competing_hypotheses and discriminating_answer:
            user_prompt = self.ANALYSIS_WITH_DIFFERENTIAL_TEMPLATE.format(
                environment=environment or '未提及',
                antecedent=antecedent,
                behavior=behavior,
                consequence=consequence,
                hypotheses_json=json.dumps(competing_hypotheses, ensure_ascii=False, indent=2),
                discriminating_answer=discriminating_answer,
            ) + style_suffix
        else:
            user_prompt = self.ANALYSIS_USER_PROMPT_TEMPLATE.format(
                environment=environment or '未提及',
                antecedent=antecedent,
                behavior=behavior,
                consequence=consequence,
            ) + style_suffix

        try:
            result = self.llm.generate_json(
                system_prompt=self.ANALYSIS_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.2,
                max_tokens=800,
            )

            # V4.3 核心修复：确保所有必需字段存在，进行数据转换和兼容
            result = self._ensure_v43_compatibility(result)

            logger.info(f"洞察分析完成：{result['core_insight'][:50]}...")
            return result

        except Exception as e:
            logger.error(f"洞察分析失败：{e}")
            return self._get_fallback_result(str(e))
    
    def _ensure_v43_compatibility(self, result: dict) -> dict:
        """
        V4.3 核心修复：确保返回字段与 V4.3 报告模板完全兼容
        
        数据转换逻辑：
        1. 确保 functional_judgment, core_insight, capability_hypothesis 存在
        2. 兼容旧字段名（expert_breakdown → functional_judgment 等）
        3. 填充缺失字段的默认值
        """
        # 1. 确保核心字段存在
        if "functional_judgment" not in result:
            # 尝试从 expert_breakdown 推断
            expert = result.get("expert_breakdown", {})
            result["functional_judgment"] = expert.get("functional_hypothesis", "提示依赖下的逃避")
        
        if "core_insight" not in result:
            # 尝试从 core_insight_for_parent 复制
            result["core_insight"] = result.get("core_insight_for_parent", "孩子正在用这种方式表达他的需求。")
        
        if "capability_hypothesis" not in result:
            # 尝试从 expert_breakdown 复制
            expert = result.get("expert_breakdown", {})
            result["capability_hypothesis"] = expert.get("capability_gap", "工作记忆和持续性注意方面的挑战。")
        
        # 2. 确保 clinical_differential 存在
        if "clinical_differential" not in result:
            result["clinical_differential"] = "基于观察到的行为模式，我们考虑了多种可能性，结合关键信息判断最可能的功能假设。"
        
        # 3. 确保 intervention_principle 存在
        if "intervention_principle" not in result:
            result["intervention_principle"] = result.get("strategy_principle", "将外部提示转化为内部提示")
        
        # 4. 确保 expert_breakdown 存在（向后兼容）
        if "expert_breakdown" not in result:
            result["expert_breakdown"] = {
                "behavior_pattern": "待分析行为模式",
                "functional_hypothesis": result.get("functional_judgment", ""),
                "capability_gap": result.get("capability_hypothesis", ""),
                "contextual_factors": "环境因素影响待评估"
            }
        
        # 5. 确保 core_insight_for_parent 与 core_insight 一致（向后兼容）
        if "core_insight_for_parent" not in result:
            result["core_insight_for_parent"] = result["core_insight"]
        
        # 6. 确保 strategy_principle 与 intervention_principle 一致（向后兼容）
        if "strategy_principle" not in result:
            result["strategy_principle"] = result["intervention_principle"]
        
        # 7. 确保 reasoning_brief 存在
        if "reasoning_brief" not in result:
            result["reasoning_brief"] = "基于 ABC 模式和临床经验的综合判断"
        
        logger.info(f"V4.3 字段兼容性检查完成：functional_judgment={result.get('functional_judgment', 'N/A')[:30]}...")
        return result
    
    def _get_fallback_result(self, error: str) -> dict:
        """
        V4.3 降级方案：当分析失败时返回完整的兼容结构
        """
        return {
            "functional_judgment": "inconclusive",
            "core_insight": "孩子正在用这种方式表达他的需求或感受。",
            "capability_hypothesis": "相关技能还在发展中，需要我们的耐心支持。",
            "clinical_differential": "由于信息有限，无法进行详细的鉴别诊断。建议继续观察并收集更多信息。",
            "intervention_principle": "提供温和、一致的支持，观察孩子的反应模式。",
            "expert_breakdown": {
                "behavior_pattern": "待分析行为模式",
                "functional_hypothesis": "需要更多信息进行判断",
                "capability_gap": "相关技能还在发展中",
                "contextual_factors": "环境因素影响待评估"
            },
            "core_insight_for_parent": "孩子正在用这种方式表达他的需求或感受。",
            "strategy_principle": "提供温和、一致的支持，观察孩子的反应模式。",
            "reasoning_brief": f"分析过程出现异常：{error}",
        }
