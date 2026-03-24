"""
行为记录员 Agent V1.1
实现自闭症行为 ABC 分析与功能假设的两步工作流（优化版）

优化内容：
- 更严谨的 Prompt 设计
- 引入推理链（Chain-of-Thought）
- 增强错误处理
- 输出包含推理过程
"""

import json
import logging
import re
from typing import TypedDict, Optional

from app.llm.base import LLMClient

logger = logging.getLogger(__name__)


class ABCAnalysisResult(TypedDict):
    """ABC 分析结果类型（V2.2）"""

    antecedent: str
    behavior: str
    consequence: str
    hypothesized_function: str
    reasoning: str
    confidence: str  # high | medium | low
    confidence_reason: str


class BehaviorRecorderAgent:
    """
    行为记录员 Agent V1.1

    实现两步工作流程：
    1. 结构化提取：从自然语言描述中提取 ABC 三要素
    2. 功能假设：基于 ABC 分析，遵循标准决策流程判断行为功能
    """

    # ========== 步骤一：结构化提取（优化版）==========
    STEP1_SYSTEM_PROMPT = (
        "你是一名严谨的儿童行为观察记录员。你的任务是从描述中提取精确的信息。"
        "请确保输出纯净的文本，不包含任何 markdown、代码或额外格式。"
    )

    STEP1_USER_PROMPT_TEMPLATE = """请分析以下关于儿童行为的描述：

"{description}"

请严格按照以下 JSON 格式输出，且仅输出此 JSON 对象：
{{
    "antecedent": "行为发生前，孩子所处的具体情境、被给予的指令或活动。如果描述中未明确提及，则填入'未明确提及'。",
    "behavior": "孩子表现出的具体、可观察的动作或非动作（例如：跑开、哭闹、发呆、沉默）。请用简洁的短语描述。",
    "consequence": "行为发生后，他人（如老师、家长）的直接反应，或环境/任务的直接变化。如果描述中未明确提及，则填入'未明确提及'。"
}}"""

    # ========== 步骤二：功能假设（V2.2 临床推理增强版）==========
    STEP2_SYSTEM_PROMPT = (
        "你是一名经验丰富的应用行为分析（BCBA）专家。"
        "你的任务是根据行为 ABC 数据，遵循临床推理逻辑，做出最合理的功能假设。"
        "你需要敢于判断，同时诚实标注置信度。"
        "请逐步思考。"
    )

    STEP2_USER_PROMPT_TEMPLATE = """你正在分析一个行为案例。请严格遵循以下临床推理步骤：

【已知信息】
- 前因 (A): `{antecedent}`
- 行为 (B): `{behavior}`
- 后果 (C): `{consequence}`

【临床推理步骤】
1. **检查实物获取（tangible）**：行为是否为了获得某个具体物品、食物或活动？后果是否为"获得了该物"？如果是，功能是 **tangible**，置信度：**高**。
2. **检查关注获取（attention）**：行为是否为了获得他人的注意（包括安慰、责备、对话）？后果是否为"他人给予了社交性反应"？如果是，功能是 **attention**，置信度：**高**。
3. **检查逃避（escape）**：
   - 若前因包含"要求"、"任务"、"复杂情境"，且后果为"任务/要求被取消、延迟或减轻"，功能是 **escape**，置信度：**高**。
   - 若前因为明确任务要求，但后果模糊（如"无反应"、"继续活动"），且行为为脱离任务（如走神、拒绝、发呆），**推断**功能为 **escape**，置信度：**中**，原因：任务情境下的脱离行为通常具有逃避功能。
4. **检查自动强化（automatic）**：
   - 若行为是重复的、刻板的（如摇晃、看手、喃喃自语），且前因后果均模糊，**推断**功能为 **automatic**，置信度：**中**，原因：刻板行为通常与感官调节相关。
5. **无法确定（inconclusive）**：仅在 ABC 信息极度匮乏或相互矛盾时使用，置信度：**低**。

【判断原则】
- **敢于判断**：基于临床经验和典型模式，做出合理推断，不要过度依赖"无法确定"。
- **诚实标注**：清晰标注置信度（高/中/低），让家长了解判断的确定性。
- **解释原因**：说明是哪个推理步骤最关键，以及为什么给出这个置信度。

【你的输出】
请以以下 JSON 格式输出你的最终结论和简要推理：
{{
    "hypothesized_function": "tangible | attention | escape | automatic | inconclusive",
    "reasoning": "一句话解释，说明是哪个推理步骤最关键。",
    "confidence": "high | medium | low",
    "confidence_reason": "解释为什么给出这个置信度，例如：'后果明确符合实物获取模式'或'后果模糊但前因为任务要求，基于临床经验推断'"
}}"""

    # 功能关键词到标准值的映射
    FUNCTION_MAPPING = {
        "escape": "escape",
        "逃避": "escape",
        "tangible": "tangible",
        "实物": "tangible",
        "物品": "tangible",
        "attention": "attention",
        "关注": "attention",
        "注意": "attention",
        "automatic": "automatic",
        "自动": "automatic",
        "自我刺激": "automatic",
        "感官": "automatic",
        "inconclusive": "inconclusive",
        "无法确定": "inconclusive",
    }

    def __init__(self, llm_client: LLMClient):
        """
        初始化行为记录员 Agent

        Args:
            llm_client: LLM 客户端实例
        """
        self.llm = llm_client
        logger.info("BehaviorRecorderAgent V1.1 初始化完成")

    def _extract_abc(self, description: str) -> dict:
        """
        步骤一：从描述中提取 ABC 三要素（优化版）

        Args:
            description: 家长的自然语言描述

        Returns:
            包含 antecedent, behavior, consequence 的字典

        Raises:
            ValueError: 当 LLM 返回无法解析的响应时
        """
        logger.info(f"步骤一：开始提取 ABC，输入长度={len(description)}")

        user_prompt = self.STEP1_USER_PROMPT_TEMPLATE.format(
            description=description
        )

        try:
            # 使用 generate_json 获取结构化响应
            result = self.llm.generate_json(
                system_prompt=self.STEP1_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.1,
                max_tokens=500,
            )

            # 验证必需字段
            required_fields = ["antecedent", "behavior", "consequence"]
            for field in required_fields:
                if field not in result:
                    logger.warning(f"缺少字段：{field}，使用默认值")
                    result[field] = "未明确提及"
                elif not result[field] or result[field].strip() == "":
                    result[field] = "未明确提及"

            logger.info(f"步骤一完成：{result}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"步骤一 JSON 解析失败：{e}")
            raise ValueError(f"ABC 提取失败：LLM 返回了无效的 JSON 格式")
        except Exception as e:
            logger.error(f"步骤一提取失败：{e}")
            raise ValueError(f"ABC 提取失败：{str(e)}")

    def _hypothesize_function(
        self, antecedent: str, behavior: str, consequence: str
    ) -> dict:
        """
        步骤二：基于 ABC 分析假设行为功能（优化版 - 引入推理链）

        Args:
            antecedent: 前因
            behavior: 行为
            consequence: 后果

        Returns:
            包含 hypothesized_function 和 reasoning 的字典

        Raises:
            ValueError: 当 LLM 返回无法解析的响应时
        """
        logger.info("步骤二：开始功能假设分析（推理链模式）")

        user_prompt = self.STEP2_USER_PROMPT_TEMPLATE.format(
            antecedent=antecedent,
            behavior=behavior,
            consequence=consequence,
        )

        try:
            # 使用 generate_json 获取结构化响应
            result = self.llm.generate_json(
                system_prompt=self.STEP2_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.1,
                max_tokens=800,
            )

            # 验证必需字段
            if "hypothesized_function" not in result:
                logger.warning("缺少 hypothesized_function 字段")
                result["hypothesized_function"] = "inconclusive"

            if "reasoning" not in result:
                logger.warning("缺少 reasoning 字段，生成默认推理")
                result["reasoning"] = "基于 ABC 数据进行的综合判断"

            # V2.2 新增：验证置信度字段
            if "confidence" not in result:
                logger.warning("缺少 confidence 字段，使用默认值")
                result["confidence"] = "medium"

            if "confidence_reason" not in result:
                logger.warning("缺少 confidence_reason 字段，生成默认值")
                result["confidence_reason"] = "基于现有信息的综合判断"

            # 规范化功能值
            raw_function = result["hypothesized_function"].lower()
            normalized_function = self.FUNCTION_MAPPING.get(
                raw_function, "inconclusive"
            )
            result["hypothesized_function"] = normalized_function

            logger.info(f"步骤二完成：功能={normalized_function}, 置信度={result['confidence']}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"步骤二 JSON 解析失败：{e}")
            raise ValueError(f"功能假设失败：LLM 返回了无效的 JSON 格式")
        except Exception as e:
            logger.error(f"步骤二分析失败：{e}")
            raise ValueError(f"功能假设失败：{str(e)}")

    def analyze(self, description: str) -> ABCAnalysisResult:
        """
        完整分析流程：执行两步工作流（优化版）

        Args:
            description: 家长的自然语言描述

        Returns:
            完整的 ABC 分析结果（包含推理过程）

        Raises:
            ValueError: 当分析过程中出现错误时
        """
        logger.info(f"开始分析，输入：{description[:100]}...")

        # 验证输入
        if not description or not description.strip():
            raise ValueError("描述不能为空")

        try:
            # 步骤一：提取 ABC
            abc_result = self._extract_abc(description)

            # 步骤二：功能假设（包含推理链）
            function_result = self._hypothesize_function(
                abc_result.get("antecedent", "未明确提及"),
                abc_result.get("behavior", "未明确提及"),
                abc_result.get("consequence", "未明确提及"),
            )

            # 整合结果
            final_result = ABCAnalysisResult(
                antecedent=abc_result.get("antecedent", "未明确提及"),
                behavior=abc_result.get("behavior", "未明确提及"),
                consequence=abc_result.get("consequence", "未明确提及"),
                hypothesized_function=function_result.get("hypothesized_function", "inconclusive"),
                reasoning=function_result.get("reasoning", "无法生成推理过程"),
            )

            logger.info(f"分析完成：功能={final_result['hypothesized_function']}")
            return final_result

        except ValueError as e:
            logger.error(f"分析失败：{e}")
            raise
        except Exception as e:
            logger.error(f"未知错误：{e}")
            raise ValueError(f"分析过程中发生错误：{str(e)}")
