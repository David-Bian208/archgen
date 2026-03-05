"""
行为记录员 Agent
实现自闭症行为 ABC 分析与功能假设的两步工作流
"""

import json
import logging
from typing import TypedDict

from app.llm.base import LLMClient

logger = logging.getLogger(__name__)


class ABCAnalysisResult(TypedDict):
    """ABC 分析结果类型"""

    antecedent: str
    behavior: str
    consequence: str
    hypothesized_function: str


class BehaviorRecorderAgent:
    """
    行为记录员 Agent

    实现两步工作流程：
    1. 结构化提取：从自然语言描述中提取 ABC 三要素
    2. 功能假设：基于 ABC 分析判断行为功能
    """

    # 步骤一：结构化提取的提示词
    STEP1_SYSTEM_PROMPT = (
        "你是一个精准的信息提取工具，请严格按照用户要求输出 JSON，不要任何解释。"
    )

    STEP1_USER_PROMPT_TEMPLATE = """从以下关于孩子的描述中，严格提取：
1. 前因 (A)：直接导致行为发生的事件或情境。
2. 行为 (B)：孩子具体、可观察的动作。
3. 后果 (C)：行为发生后，家长或他人立即做的事。
描述：{description}
请输出 JSON：{{"antecedent": "...", "behavior": "...", "consequence": "..."}}"""

    # 步骤二：功能假设的提示词
    STEP2_SYSTEM_PROMPT = (
        "你是一名应用行为分析（ABA）专家，请从四个标准功能中做出最严谨的选择。"
    )

    STEP2_USER_PROMPT_TEMPLATE = """基于以下行为 ABC 分析，判断其最可能的功能：
- 前因：{antecedent}
- 行为：{behavior}
- 后果：{consequence}
选项定义：
- escape: 为逃避/终止任务或情境。
- tangible: 为获得物品、食物或活动。
- attention: 为获得他人的注意（正负皆可）。
- automatic: 为自我刺激或感官调节。
你只需输出一个功能关键词，格式为：功能：xxx"""

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
    }

    def __init__(self, llm_client: LLMClient):
        """
        初始化行为记录员 Agent

        Args:
            llm_client: LLM 客户端实例
        """
        self.llm = llm_client
        logger.info("BehaviorRecorderAgent 初始化完成")

    def _extract_abc(self, description: str) -> dict:
        """
        步骤一：从描述中提取 ABC 三要素

        Args:
            description: 家长的自然语言描述

        Returns:
            包含 antecedent, behavior, consequence 的字典
        """
        logger.info(f"步骤一：开始提取 ABC，输入长度={len(description)}")

        user_prompt = self.STEP1_USER_PROMPT_TEMPLATE.format(
            description=description
        )

        try:
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
                    logger.warning(f"缺少字段：{field}")
                    result[field] = ""

            logger.info(f"步骤一完成：{result}")
            return result

        except Exception as e:
            logger.error(f"步骤一提取失败：{e}")
            # 返回空结果，让调用者决定如何处理
            return {
                "antecedent": "",
                "behavior": "",
                "consequence": "",
            }

    def _hypothesize_function(
        self, antecedent: str, behavior: str, consequence: str
    ) -> str:
        """
        步骤二：基于 ABC 分析假设行为功能

        Args:
            antecedent: 前因
            behavior: 行为
            consequence: 后果

        Returns:
            假设的功能关键词 (escape/tangible/attention/automatic)
        """
        logger.info("步骤二：开始功能假设分析")

        user_prompt = self.STEP2_USER_PROMPT_TEMPLATE.format(
            antecedent=antecedent,
            behavior=behavior,
            consequence=consequence,
        )

        try:
            # 获取 LLM 的原始响应
            raw_response = self.llm.generate(
                system_prompt=self.STEP2_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.1,
                max_tokens=100,
            )

            logger.info(f"步骤二原始响应：{raw_response}")

            # 解析响应，提取功能关键词
            function_keyword = self._parse_function_response(raw_response)

            # 映射到标准值
            normalized_function = self.FUNCTION_MAPPING.get(
                function_keyword.lower(), "automatic"
            )

            logger.info(f"步骤二完成：功能={normalized_function}")
            return normalized_function

        except Exception as e:
            logger.error(f"步骤二分析失败：{e}")
            # 默认返回 automatic
            return "automatic"

    def _parse_function_response(self, response: str) -> str:
        """
        解析功能假设的响应

        Args:
            response: LLM 的原始响应

        Returns:
            提取的功能关键词
        """
        response = response.strip()

        # 尝试匹配 "功能：xxx" 格式
        if "功能:" in response or "功能：" in response:
            parts = response.replace("功能：", "功能:").split("功能:")
            if len(parts) > 1:
                return parts[1].strip()

        # 尝试直接匹配关键词
        keywords = [
            "escape",
            "tangible",
            "attention",
            "automatic",
            "逃避",
            "实物",
            "物品",
            "关注",
            "注意",
            "自动",
            "自我刺激",
            "感官",
        ]

        for keyword in keywords:
            if keyword in response.lower():
                return keyword

        # 如果都无法匹配，返回第一个非空词
        words = response.split()
        if words:
            return words[0]

        return "automatic"

    def analyze(self, description: str) -> ABCAnalysisResult:
        """
        完整分析流程：执行两步工作流

        Args:
            description: 家长的自然语言描述

        Returns:
            完整的 ABC 分析结果
        """
        logger.info(f"开始分析，输入：{description[:100]}...")

        # 步骤一：提取 ABC
        abc_result = self._extract_abc(description)

        # 步骤二：功能假设
        function = self._hypothesize_function(
            abc_result.get("antecedent", ""),
            abc_result.get("behavior", ""),
            abc_result.get("consequence", ""),
        )

        # 整合结果
        final_result = ABCAnalysisResult(
            antecedent=abc_result.get("antecedent", ""),
            behavior=abc_result.get("behavior", ""),
            consequence=abc_result.get("consequence", ""),
            hypothesized_function=function,
        )

        logger.info(f"分析完成：{final_result}")
        return final_result
