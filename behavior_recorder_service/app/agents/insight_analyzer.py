"""
洞察分析器 V3.0
从"行为分类"升级为"共情洞察"

核心理念：
- 不是输出标签，而是生成洞察
- 不是事实复述，而是行为理解
- 不是专业术语，而是家长能懂的"金句"
"""

import json
import logging
from typing import Optional

from app.llm.base import LLMClient

logger = logging.getLogger(__name__)


class InsightAnalyzer:
    """
    洞察分析器 V3.0
    
    三步推理链：
    1. 功能判断（内在逻辑）- 不直接输出术语
    2. 深度归因（动机与能力）- 区分"不想做"vs"做不到"
    3. 提炼核心洞察 - 给家长的"金句"
    """

    # V3.3 分析 Prompt - 提示依赖逃避模型 + 叙事型报告
    ANALYSIS_SYSTEM_PROMPT = """你是一位经验丰富的 BCBA 督导，正在将观察转化为对家长有启发的洞察。

你的任务是：
1. 进行专业的"专家拆解"（内部分析）- 精准判断功能
2. 将专业分析"翻译"成家长能懂的语言（对外沟通）- 有温度、有观点

【关键分析原则】
当行为模式表现为"有提示则执行，无提示则中断/发呆"，且任务具有明确的社会性目标时：
- 首要功能假设应从"自动强化"修正为"在提示依赖下的逃避（任务失败/认知负荷）"
- 这是特殊形式的"逃避"——逃避的是因提示中断而导致的"任务执行失败"或"认知过载"
- 能力缺口：工作记忆（记不住多步骤序列）和持续性注意（无法在提示间隙自我维持任务表征）
- 环境整合：嘈杂、拥挤等环境因素会加剧对单一、清晰视觉提示的依赖

请严格按照以下 JSON 格式输出：
{
    "expert_breakdown": {
        "behavior_pattern": "一句话命名该行为模式，如'视觉提示依赖行为'、'任务执行中断'等。",
        "functional_hypothesis": "基于上述关键原则，判断功能是否为'提示依赖下的逃避'，并说明推理链。",
        "capability_gap": "分析这可能反映了工作记忆和/或持续性注意方面的挑战。",
        "contextual_factors": "简述环境因素（如噪音、拥挤）如何加剧了对单一、清晰视觉提示的依赖。"
    },
    "core_insight_for_parent": "基于专家拆解，用一句'金句'直击本质。例如：'孩子不是不努力，而是他的动作记忆需要靠眼睛实时充电。'这句话要说进家长心坎里。",
    "strategy_principle": "针对'提示依赖'，提出'将外部提示转化为内部提示'的干预原则。",
    "reasoning_brief": "简短的专业推理（用于内部参考，50 字以内）"
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

    # V3.4 鉴别诊断分析 Prompt
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

请严格按照以下 JSON 格式输出：
{{
    "expert_breakdown": {{
        "behavior_pattern": "一句话命名该行为模式",
        "functional_hypothesis": "基于鉴别诊断，判断最可能的功能，并说明推理",
        "capability_gap": "分析这可能反映了哪方面的能力挑战",
        "contextual_factors": "简述环境因素如何影响行为",
        "differential_reasoning": "简述鉴别诊断过程：为什么 HX 可能性最高，其他假设的可能性如何"
    }},
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

    def analyze(self, environment: str, antecedent: str, behavior: str, consequence: str, competing_hypotheses: Optional[list] = None, discriminating_answer: str = "") -> dict:
        """
        执行三步推理分析（V3.4 - 加入鉴别诊断）

        Args:
            environment: 环境上下文
            antecedent: 情境（前因）
            behavior: 孩子的表现（行为）
            consequence: 当时的回应（后果）
            competing_hypotheses: 竞争性假设列表（可选）
            discriminating_answer: 用户对鉴别性问题的回答（可选）

        Returns:
            洞察分析结果
        """
        logger.info(f"开始洞察分析：环境={environment[:30] if environment else '无'}, 情境={antecedent[:30]}..., 行为={behavior[:30]}...")

        # V3.4 新增：如果有竞争性假设，使用鉴别诊断 Prompt
        if competing_hypotheses and discriminating_answer:
            user_prompt = self.ANALYSIS_WITH_DIFFERENTIAL_TEMPLATE.format(
                environment=environment or '未提及',
                antecedent=antecedent,
                behavior=behavior,
                consequence=consequence,
                hypotheses_json=json.dumps(competing_hypotheses, ensure_ascii=False, indent=2),
                discriminating_answer=discriminating_answer,
            )
        else:
            user_prompt = self.ANALYSIS_USER_PROMPT_TEMPLATE.format(
                environment=environment or '未提及',
                antecedent=antecedent,
                behavior=behavior,
                consequence=consequence,
            )

        try:
            result = self.llm.generate_json(
                system_prompt=self.ANALYSIS_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.2,
                max_tokens=800,
            )

            # 验证必需字段
            required_fields = ["functional_judgment", "core_insight", "capability_hypothesis"]
            for field in required_fields:
                if field not in result:
                    logger.warning(f"缺少字段：{field}")
                    if field == "core_insight":
                        result[field] = "孩子正在用这种方式表达他的需求。"
                    elif field == "capability_hypothesis":
                        result[field] = "相关技能还在发展中。"
                    else:
                        result[field] = "inconclusive"

            # 可选字段
            if "reasoning_brief" not in result:
                result["reasoning_brief"] = "基于 ABC 模式的综合判断"

            logger.info(f"洞察分析完成：{result['core_insight'][:50]}...")
            return result

        except Exception as e:
            logger.error(f"洞察分析失败：{e}")
            return {
                "functional_judgment": "inconclusive",
                "core_insight": "孩子正在用这种方式表达他的需求或感受。",
                "capability_hypothesis": "相关技能还在发展中，需要我们的耐心支持。",
                "reasoning_brief": f"分析过程出现异常：{str(e)}",
            }
