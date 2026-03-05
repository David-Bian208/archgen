"""
干预策略分析师 Agent
基于 ABC 分析和功能假设，生成个性化的干预策略计划

版本：V3.5
"""

import json
import logging
from typing import TypedDict, List
from datetime import datetime

from app.llm.base import LLMClient

logger = logging.getLogger(__name__)


class InterventionStrategy(TypedDict):
    """干预策略结果类型"""
    function: str
    antecedent_strategies: List[str]
    behavior_strategies: List[str]
    consequence_strategies: List[str]
    replacement_behavior: str
    implementation_tips: List[str]


class DisengagementTask(TypedDict):
    """任务脱离干预任务"""
    task_name: str
    anchor_behavior: str
    step_by_step_plan: List[str]
    success_criteria: str
    fallback_plan: str


class InterventionPlannerAgent:
    """
    干预策略分析师 Agent V3.5
    
    基于 ABC 分析和功能假设，生成针对性的干预策略：
    1. 前因干预：调整环境，预防问题行为
    2. 行为教学：教授替代行为
    3. 后果管理：强化适当行为，消退问题行为
    """

    # 系统提示词
    SYSTEM_PROMPT = (
        "你是一名资深的应用行为分析 (ABA) 干预策略专家。"
        "请基于提供的 ABC 分析和功能假设，生成具体、可操作的干预策略。"
        "策略必须符合循证实践，适合家长在家庭环境中实施。"
        "输出必须是严格的 JSON 格式，不要任何解释。"
    )

    # 干预策略生成提示词模板
    STRATEGY_PROMPT_TEMPLATE = """基于以下行为分析，生成完整的干预策略计划：

【行为分析】
- 前因 (A): {antecedent}
- 行为 (B): {behavior}
- 后果 (C): {consequence}
- 假设功能：{function}

【功能定义】
- escape (逃避): 为逃避/终止任务或情境
- tangible (实物): 为获得物品、食物或活动
- attention (关注): 为获得他人的注意（正负皆可）
- automatic (自我刺激): 为自我刺激或感官调节

请生成以下内容的 JSON：
{{
    "function": "{function}",
    "antecedent_strategies": [3-5 条前因干预策略],
    "behavior_strategies": [3-5 条行为教学策略],
    "consequence_strategies": [3-5 条后果管理策略],
    "replacement_behavior": "具体的替代行为描述",
    "implementation_tips": [5-8 条实施建议]
}}"""

    # 任务脱离锚点建立提示词
    DISENGAGEMENT_ANCHOR_TEMPLATE = """设计一个"任务脱离"干预的锚点建立计划：

【背景】
孩子当前功能：{function}
目标行为：{target_behavior}
当前挑战：{challenge}

【锚点建立 H1 阶段要求】
1. 选择一个高概率的锚点行为（孩子已经会做的、简单的行为）
2. 设计从锚点行为到目标行为的渐进步骤
3. 明确每个步骤的成功标准
4. 制定fallback 计划（当孩子抗拒时）

请输出 JSON：
{{
    "task_name": "任务脱离训练",
    "anchor_behavior": "锚点行为描述",
    "step_by_step_plan": ["步骤 1", "步骤 2", "步骤 3", ...],
    "success_criteria": "成功标准描述",
    "fallback_plan": "fallback 计划"
}}"""

    def __init__(self, llm_client: LLMClient):
        """
        初始化干预策略分析师 Agent

        Args:
            llm_client: LLM 客户端实例
        """
        self.llm = llm_client
        logger.info("InterventionPlanner V3.5 初始化完成")

    def generate_strategy(
        self,
        antecedent: str,
        behavior: str,
        consequence: str,
        function: str
    ) -> InterventionStrategy:
        """
        生成干预策略

        Args:
            antecedent: 前因
            behavior: 行为
            consequence: 后果
            function: 假设功能

        Returns:
            干预策略结果
        """
        logger.info(f"开始生成干预策略，功能={function}")

        user_prompt = self.STRATEGY_PROMPT_TEMPLATE.format(
            antecedent=antecedent,
            behavior=behavior,
            consequence=consequence,
            function=function
        )

        try:
            result = self.llm.generate_json(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=1500,
            )

            # 验证必需字段
            required_fields = [
                "function",
                "antecedent_strategies",
                "behavior_strategies",
                "consequence_strategies",
                "replacement_behavior",
                "implementation_tips"
            ]

            for field in required_fields:
                if field not in result:
                    logger.warning(f"缺少字段：{field}")
                    if field == "function":
                        result[field] = function
                    elif field == "replacement_behavior":
                        result[field] = "待确定"
                    else:
                        result[field] = []

            logger.info(f"干预策略生成完成")
            return result

        except Exception as e:
            logger.error(f"策略生成失败：{e}")
            # 返回基础模板
            return self._get_fallback_strategy(function)

    def _get_fallback_strategy(self, function: str) -> InterventionStrategy:
        """返回 fallback 策略模板"""
        return {
            "function": function,
            "antecedent_strategies": [
                "识别并记录行为触发因素",
                "调整环境减少触发",
                "建立可预测的日常流程"
            ],
            "behavior_strategies": [
                "教授适当的沟通方式",
                "使用视觉提示",
                "练习替代行为"
            ],
            "consequence_strategies": [
                "立即强化适当行为",
                "保持一致的后果",
                "避免意外强化问题行为"
            ],
            "replacement_behavior": "待评估后确定",
            "implementation_tips": [
                "保持耐心和一致性",
                "从小步骤开始",
                "记录进展",
                "庆祝小成功",
                "寻求专业支持"
            ]
        }

    def create_disengagement_anchor(
        self,
        function: str,
        target_behavior: str,
        challenge: str
    ) -> DisengagementTask:
        """
        创建任务脱离的锚点建立计划 (H1 阶段)

        Args:
            function: 行为功能
            target_behavior: 目标行为
            challenge: 当前挑战

        Returns:
            任务脱离计划
        """
        logger.info(f"创建任务脱离锚点计划，功能={function}")

        user_prompt = self.DISENGAGEMENT_ANCHOR_TEMPLATE.format(
            function=function,
            target_behavior=target_behavior,
            challenge=challenge
        )

        try:
            result = self.llm.generate_json(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=1000,
            )

            # 验证必需字段
            required_fields = [
                "task_name",
                "anchor_behavior",
                "step_by_step_plan",
                "success_criteria",
                "fallback_plan"
            ]

            for field in required_fields:
                if field not in result:
                    logger.warning(f"缺少字段：{field}")
                    if field == "task_name":
                        result[field] = "任务脱离训练"
                    elif field == "anchor_behavior":
                        result[field] = "待确定"
                    elif field == "step_by_step_plan":
                        result[field] = ["逐步建立锚点"]
                    elif field == "success_criteria":
                        result[field] = "孩子能够独立完成目标行为"
                    elif field == "fallback_plan":
                        result[field] = "回到上一步骤，降低要求"

            logger.info(f"任务脱离锚点计划生成完成")
            return result

        except Exception as e:
            logger.error(f"锚点计划生成失败：{e}")
            return self._get_fallback_disengagement_plan()

    def _get_fallback_disengagement_plan(self) -> DisengagementTask:
        """返回 fallback 任务脱离计划"""
        return {
            "task_name": "任务脱离训练",
            "anchor_behavior": "选择一个孩子已经掌握的高概率行为",
            "step_by_step_plan": [
                "步骤 1: 建立锚点行为的稳定性",
                "步骤 2: 在锚点行为后引入短暂的任务要求",
                "步骤 3: 逐步延长任务时间",
                "步骤 4: 增加任务难度",
                "步骤 5: 泛化到不同情境"
            ],
            "success_criteria": "孩子能够在提示下完成任务并适当脱离",
            "fallback_plan": "当孩子表现出抗拒时，回到上一步骤，降低要求，增加强化"
        }

    def analyze_and_plan(
        self,
        description: str,
        abc_result: dict
    ) -> dict:
        """
        完整分析 + 规划流程

        Args:
            description: 原始描述
            abc_result: ABC 分析结果

        Returns:
            完整的分析报告和干预计划
        """
        logger.info(f"开始完整分析 + 规划流程")

        # 生成干预策略
        strategy = self.generate_strategy(
            antecedent=abc_result.get("antecedent", ""),
            behavior=abc_result.get("behavior", ""),
            consequence=abc_result.get("consequence", ""),
            function=abc_result.get("hypothesized_function", "automatic")
        )

        # 如果是逃避功能，创建任务脱离锚点计划
        disengagement_task = None
        if abc_result.get("hypothesized_function") == "escape":
            disengagement_task = self.create_disengagement_anchor(
                function="escape",
                target_behavior=abc_result.get("behavior", ""),
                challenge=abc_result.get("antecedent", "")
            )

        # 整合结果
        result = {
            "timestamp": datetime.now().isoformat(),
            "original_description": description,
            "abc_analysis": abc_result,
            "intervention_strategy": strategy,
            "disengagement_task": disengagement_task,
            "status": "completed"
        }

        logger.info(f"完整分析 + 规划完成，status=completed")
        return result
