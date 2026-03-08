"""
干预规划器 V3.8
基于诊断结果，生成个性化的四步干预方案

V3.8 核心改进：
- 四步结构：通用方法论阐述（避免具体案例名词）
- HTML 实体解码（彻底修复乱码）
- 更具鼓励性的观察记录工具表述
"""

import logging
import re
import html
from typing import Optional, Dict, Any

from app.knowledge import get_knowledge_base

logger = logging.getLogger(__name__)


class InterventionPlanner:
    """干预规划器 V3.9.2 - 智能动态临床访谈配套"""

    def __init__(self):
        """初始化规划器"""
        self.knowledge_base = get_knowledge_base()
        logger.info("InterventionPlanner V3.9.2 初始化完成")

    def generate_plan(self, matched_hypothesis_id: str, scenario_key: str, session_context: Optional[dict] = None) -> Optional[Dict[str, Any]]:
        """
        V3.7 基于匹配的假设生成四步干预计划

        Args:
            matched_hypothesis_id: 匹配的假设 ID（如 "H1"）
            scenario_key: 场景键（如 "task_disengagement"）
            session_context: 会话上下文（包含环境、行为等信息，用于个性化生成）

        Returns:
            干预计划字典，包含四步结构
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

        # V3.7 生成四步结构
        four_step_plan = self._generate_four_step_plan(first_phase, intervention_plan, scenario, session_context)

        # 构建返回结果
        plan = {
            "core_principle": intervention_plan.get("core_principle", ""),
            "current_phase": first_phase,
            "phase_name": first_phase.get("phase_name", ""),
            "goal": first_phase.get("goal", ""),
            "primary_strategy": first_phase.get("primary_strategy", ""),
            "strategy_details": first_phase.get("strategy_details", ""),
            "success_criteria": first_phase.get("success_criteria", ""),
            "parent_observation_task": first_phase.get("parent_observation_task", ""),
            "next_phase_preview": phase_ladder[1].get("goal", "") if len(phase_ladder) > 1 else "",
            "data_tracking_suggestion": intervention_plan.get("data_tracking_suggestion", ""),
            # V3.7 四步结构
            "four_step_plan": four_step_plan,
            # V3.7 观察记录工具
            "observation_tool": self._generate_observation_tool_v37(first_phase),
        }

        logger.info(f"V3.7 生成干预计划：{scenario_key} - {matched_hypothesis_id}")
        return plan

    def _generate_four_step_plan(self, phase: dict, intervention_plan: dict, scenario: dict, session_context: Optional[dict] = None) -> Dict[str, str]:
        """
        V3.7 生成四步结构计划

        Args:
            phase: 第一阶段详情
            intervention_plan: 完整干预计划
            scenario: 场景信息
            session_context: 会话上下文

        Returns:
            四步结构字典
        """
        # 提取关键信息
        success_criteria = phase.get("success_criteria", "")
        strategy_details = phase.get("strategy_details", "")
        core_principle = intervention_plan.get("core_principle", "")
        goal = phase.get("goal", "")

        # 解析成功标准
        parsed_success = self._parse_success_criteria(success_criteria)

        # 提取策略关键词（如"密语"、"动作暗号"等）
        strategy_keyword = self._extract_strategy_keyword(strategy_details, session_context)

        # 1. 核心思路
        core_idea = self._generate_core_idea(core_principle, scenario, strategy_keyword)

        # 2. 我们的计划
        our_plan = self._generate_our_plan(phase, strategy_keyword, session_context)

        # 3. 成功的画面
        success_picture = self._generate_success_picture(parsed_success, strategy_keyword)

        # 4. 第一步行动与观察
        first_step = self._generate_first_step(phase, strategy_keyword, session_context)

        return {
            "core_idea": core_idea,
            "our_plan": our_plan,
            "success_picture": success_picture,
            "first_step": first_step,
        }

    def _generate_core_idea(self, core_principle: str, scenario: dict, strategy_keyword: str) -> str:
        """
        V3.9 生成核心思路（强化理性逻辑链）
        
        用 1-2 句话说明：针对 [已识别的主要挑战]，我们的核心策略是通过 [具体的转换/构建方法]，来实现 [目标状态]
        """
        # V3.9 理性逻辑链：挑战 → 策略 → 目标
        if "提示依赖" in core_principle or "外部提示" in core_principle:
            return "既然挑战的核心是孩子对'实时视觉提示'的依赖，那么我们的核心思路就是：帮助他将需要紧盯的'外部提示'，逐步转化为自己能随时调用的'内部提示'，从而减少任务中断。"
        elif "逃避" in core_principle:
            return "既然挑战的核心是任务难度超出了孩子当前的能力范围，那么我们的核心思路就是：通过分解步骤和降低门槛，让任务变得可及，从而减少逃避行为，增加主动参与。"
        else:
            return "既然挑战的核心是孩子需要更多支持来维持任务参与，那么我们的核心思路就是：通过游戏化的方式，将干预目标融入到日常互动中，帮助孩子在自然情境中学习和成长。"

    def _generate_our_plan(self, phase: dict, strategy_keyword: str, session_context: Optional[dict] = None) -> str:
        """
        V3.9 生成我们的计划（通用方法论描述 + 温和提示）
        
        避免具体案例名词，专注于方法本身的阐述，加入温和提示
        """
        phase_name = phase.get("phase_name", "第一步")

        # V3.9 通用方法论表述 + 温和提示
        return "我们可以从当前的任务情境中，选择一个有代表性的步骤，将它转化为您和孩子之间的趣味'暗号'。通过精心设计的小游戏，在轻松的氛围中反复练习，帮助孩子建立'暗号'与'行动'之间的快速链接。您可以根据孩子的反应灵活调整游戏节奏。"

    def _generate_success_picture(self, parsed_success: dict, strategy_keyword: str) -> str:
        """
        V3.8 生成成功的画面（通用可衡量目标）
        
        避免具体案例名词，专注于通用成功标准
        """
        time_frame = parsed_success.get("time_frame", "3 天")
        percentage = parsed_success.get("percentage", "80%")
        response_time = parsed_success.get("response_time", "3 秒")

        # V3.8 通用表述
        return f"在{time_frame}内，当您使用这个'暗号'提示时，孩子能在{response_time}内做出正确反应，且尝试的成功率能够稳定达到{percentage}以上。"

    def _generate_first_step(self, phase: dict, strategy_keyword: str, session_context: Optional[dict] = None) -> str:
        """
        V3.9 Final 生成第一步行动（简洁有力 + 温和提示）
        
        简洁直接的表述
        """
        # V3.9 Final 简洁表述
        return "今天，您就可以和孩子共创一个趣味'暗号'，并开启第一次'闯关'游戏。记住，第一次玩不重要，重要的是开始！"

    def _extract_strategy_keyword(self, strategy_details: str, session_context: Optional[dict] = None) -> str:
        """从策略描述中提取关键词（如"密语"、"动作暗号"等）"""
        # 尝试提取引号内的关键词
        match = re.search(r"'([^']+)'", strategy_details)
        if match:
            keyword = match.group(1)
            if len(keyword) <= 10:  # 短词更适合作为关键词
                return keyword

        # 尝试从会话上下文提取
        if session_context and session_context.get("child_behavior"):
            behavior = session_context["child_behavior"]
            if "发呆" in behavior:
                return "动作密语"
            elif "提示" in behavior:
                return "密语提示"

        return "动作密语"  # 默认关键词

    def _extract_activity(self, strategy_details: str) -> str:
        """从策略描述中提取活动名称"""
        activities = ["体操", "跳操", "游戏", "拼图", "儿歌", "画画", "搭积木"]
        for activity in activities:
            if activity in strategy_details:
                return activity
        return "日常活动"

    def _parse_success_criteria(self, success_criteria: str) -> dict:
        """
        解析成功标准

        Args:
            success_criteria: 成功标准文本

        Returns:
            解析后的字典
        """
        result = {
            "time_frame": "3 天",
            "behavior": "目标动作",
            "percentage": "80%",
            "response_time": "3 秒",
        }

        # 提取时间框架
        time_match = re.search(r'连续 (\d+) 日', success_criteria)
        if time_match:
            result["time_frame"] = f"{time_match.group(1)}天"

        # 提取百分比
        pct_match = re.search(r'(\d+)%', success_criteria)
        if pct_match:
            result["percentage"] = f"{pct_match.group(1)}%"

        # 提取响应时间
        time_match = re.search(r'(\d+) 秒', success_criteria)
        if time_match:
            result["response_time"] = f"{time_match.group(1)}秒"

        # 提取行为
        if "独立" in success_criteria:
            behavior_match = re.search(r'独立 (.*?) 的', success_criteria)
            if behavior_match:
                result["behavior"] = behavior_match.group(1)
        elif "做出" in success_criteria:
            behavior_match = re.search(r'做出 (.*?) ', success_criteria)
            if behavior_match:
                result["behavior"] = behavior_match.group(1)

        return result

    def _generate_observation_tool_v38(self, phase: dict) -> str:
        """
        V3.8 生成观察记录工具（强调目的，减轻负担）

        Args:
            phase: 阶段字典

        Returns:
            观察工具建议
        """
        return "记录是为了捕捉进步的信号，而不是增加负担。您只需：在日历上，在玩游戏的日期旁，根据孩子的反应速度画上 ✅（快）或 🔄（慢）。这就足够了！"

    def _generate_observation_tool_v37(self, phase: dict) -> str:
        """兼容 V3.7 方法"""
        return self._generate_observation_tool_v38(phase)

    def gamify_strategy_description(self, strategy_details: str, child_nickname: str = "孩子") -> str:
        """
        对策略描述进行游戏化、亲子互动式语言改写

        Args:
            strategy_details: 原始策略描述
            child_nickname: 孩子昵称

        Returns:
            游戏化后的策略描述
        """
        gamified = f"让我们和{child_nickname}一起玩一个特别的游戏吧！\n\n"
        gamified += strategy_details
        gamified += f"\n\n记住，这个游戏的关键是：让{child_nickname}在快乐中学习，每一次成功都值得庆祝！"

        return gamified

    def decode_html_entities(self, text: str) -> str:
        """
        V3.8 HTML 实体解码 - 修复乱码
        
        使用 html.unescape() 将 HTML 实体转换回原始字符
        
        Args:
            text: 包含 HTML 实体的文本
            
        Returns:
            解码后的文本
        """
        if not text:
            return ""
        
        # 使用 Python 标准库进行 HTML 实体解码
        return html.unescape(text)

    def sanitize_plan(self, plan: dict) -> dict:
        """
        V3.8 对计划字典中的所有文本字段进行 HTML 实体解码
        
        Args:
            plan: 计划字典
            
        Returns:
            解码后的计划字典
        """
        if "four_step_plan" in plan:
            for key, value in plan["four_step_plan"].items():
                if isinstance(value, str):
                    plan["four_step_plan"][key] = self.decode_html_entities(value)
        
        if "observation_tool" in plan and isinstance(plan["observation_tool"], str):
            plan["observation_tool"] = self.decode_html_entities(plan["observation_tool"])
        
        return plan
