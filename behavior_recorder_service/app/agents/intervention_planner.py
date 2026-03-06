"""
干预规划器 V3.5
基于诊断结果，生成个性化的阶梯式干预方案
"""

import logging
from typing import Optional, Dict, Any

from app.knowledge import get_knowledge_base

logger = logging.getLogger(__name__)


class InterventionPlanner:
    """干预规划器"""

    def __init__(self):
        """初始化规划器"""
        self.knowledge_base = get_knowledge_base()
        logger.info("InterventionPlanner V3.5 初始化完成")

    def generate_plan(self, matched_hypothesis_id: str, scenario_key: str) -> Optional[Dict[str, Any]]:
        """
        基于匹配的假设生成干预计划

        Args:
            matched_hypothesis_id: 匹配的假设 ID（如 "H1"）
            scenario_key: 场景键（如 "task_disengagement"）

        Returns:
            干预计划字典，包含第一阶段详情
        """
        # 查找场景
        scenario = None
        for s in self.knowledge_base.data.get("scenarios", []):
            if s.get("scene_key") == scenario_key:
                scenario = s
                break

        if not scenario:
            logger.warning(f"未找到场景：{scenario_key}")
            return None

        # 查找假设
        hypothesis = None
        for h in scenario.get("competing_hypotheses", []):
            if h.get("id") == matched_hypothesis_id:
                hypothesis = h
                break

        if not hypothesis:
            logger.warning(f"未找到假设：{matched_hypothesis_id} in {scenario_key}")
            return None

        # 获取干预计划
        intervention_plan = hypothesis.get("intervention_plan")
        if not intervention_plan:
            logger.warning(f"假设 {matched_hypothesis_id} 无干预计划")
            return None

        # 提取第一阶段
        phase_ladder = intervention_plan.get("phase_ladder", [])
        if not phase_ladder:
            logger.warning(f"干预计划无阶段梯")
            return None

        first_phase = phase_ladder[0]

        # 解析成功标准，提取小目标
        success_criteria = first_phase.get("success_criteria", "")
        mini_goal = self._parse_mini_goal(success_criteria)

        # 构建返回结果
        plan = {
            "core_principle": intervention_plan.get("core_principle", ""),
            "current_phase": first_phase,
            "phase_name": first_phase.get("phase_name", ""),
            "goal": first_phase.get("goal", ""),
            "primary_strategy": first_phase.get("primary_strategy", ""),
            "strategy_details": first_phase.get("strategy_details", ""),
            "success_criteria": success_criteria,
            "parent_observation_task": first_phase.get("parent_observation_task", ""),
            "next_phase_preview": phase_ladder[1].get("goal", "") if len(phase_ladder) > 1 else "",
            "data_tracking_suggestion": intervention_plan.get("data_tracking_suggestion", ""),
            # V3.5 新增：小目标
            "mini_goal": mini_goal,
            "observation_tool": self._generate_observation_tool(first_phase),
        }

        logger.info(f"生成干预计划：{scenario_key} - {matched_hypothesis_id} - {first_phase.get('phase_name')}")
        return plan

    def _parse_mini_goal(self, success_criteria: str) -> str:
        """
        从成功标准中解析出小目标

        Args:
            success_criteria: 成功标准文本

        Returns:
            格式化的小目标
        """
        # 尝试提取时间框架、行为、百分比
        # 示例："连续 3 日，在自然情境的口头'密语'提示下，3 秒内独立做出正确动作的成功率 ≥ 80%。"

        time_frame = "1 周"
        behavior = "目标行为"
        percentage = "70%"

        # 简单解析逻辑
        if "连续" in success_criteria and "日" in success_criteria:
            # 提取天数
            import re
            match = re.search(r'连续 (\d+) 日', success_criteria)
            if match:
                days = int(match.group(1))
                time_frame = f"{days}天"

        if "成功率" in success_criteria:
            # 提取百分比
            match = re.search(r'(\d+)%', success_criteria)
            if match:
                percentage = f"{match.group(1)}%"

        # 提取行为描述
        if "独立" in success_criteria:
            match = re.search(r'独立 (.*?) 的', success_criteria)
            if match:
                behavior = match.group(1)
        elif "做出" in success_criteria:
            match = re.search(r'做出 (.*?) ', success_criteria)
            if match:
                behavior = match.group(1)

        return f"在{time_frame}内，实现{behavior}，成功率超过{percentage}。"

    def _generate_observation_tool(self, phase: dict) -> str:
        """
        生成观察记录小工具建议

        Args:
            phase: 阶段字典

        Returns:
            观察工具建议
        """
        # 默认建议
        tool = "在日历上画√/×：每天睡前，回想今天的目标行为，做到了画√，没做到画×。"

        # 根据观察任务定制
        obs_task = phase.get("parent_observation_task", "")
        if "记录" in obs_task:
            tool = obs_task + " 简单版：在日历上画√/×即可。"

        return tool

    def gamify_strategy_description(self, strategy_details: str, child_nickname: str = "孩子") -> str:
        """
        对策略描述进行游戏化、亲子互动式语言改写

        Args:
            strategy_details: 原始策略描述
            child_nickname: 孩子昵称

        Returns:
            游戏化后的策略描述
        """
        # V3.5 简化版：添加游戏化前缀和后缀
        gamified = f"让我们和{child_nickname}一起玩一个特别的游戏吧！\n\n"
        gamified += strategy_details
        gamified += f"\n\n记住，这个游戏的关键是：让{child_nickname}在快乐中学习，每一次成功都值得庆祝！"

        return gamified
