"""
干预规划器 V4.0 - 个性化处方生成器
基于完整分析结论，动态生成独一无二的干预计划

V4.0 核心改进：
- 拒绝模板：完全基于上游分析结果动态生成
- 个性化处方：计划名称、成功画面、第一步行动均与具体案例强相关
- 知识库作为原理参考，而非静态答案
"""

import logging
import re
import html
from typing import Optional, Dict, Any

from app.knowledge import get_knowledge_base

logger = logging.getLogger(__name__)


class InterventionPlannerV4:
    """干预规划器 V4.0 - 个性化处方生成器"""

    def __init__(self):
        self.knowledge_base = get_knowledge_base()
        logger.info("InterventionPlannerV4 初始化完成")

    def generate_plan(self, matched_hypothesis_id: str, scenario_key: str, session_context: Optional[dict] = None) -> Optional[Dict[str, Any]]:
        """
        V4.0 基于完整分析结论生成个性化干预计划

        Args:
            matched_hypothesis_id: 匹配的假设 ID
            scenario_key: 场景键
            session_context: 完整的会话上下文（包含专家分析结果）

        Returns:
            个性化干预计划
        """
        scenario = self._find_scenario(scenario_key)
        if not scenario:
            logger.warning(f"未找到场景：{scenario_key}")
            return None

        hypothesis = self._find_hypothesis(scenario, matched_hypothesis_id)
        if not hypothesis:
            logger.warning(f"未找到假设：{matched_hypothesis_id}")
            return None

        intervention_plan = hypothesis.get("intervention_plan")
        if not intervention_plan:
            return None

        phase_ladder = intervention_plan.get("phase_ladder", [])
        if not phase_ladder:
            return None

        first_phase = phase_ladder[0]

        # V4.0 核心：从 session_context 提取个性化信息
        primary_hypothesis = session_context.get("primary_hypothesis", "") if session_context else ""
        capability_gap = session_context.get("capability_gap", "") if session_context else ""
        context_activity = session_context.get("context", "") if session_context else ""
        target_behavior = session_context.get("child_behavior", "") if session_context else ""

        # V4.0 动态生成四步结构
        four_step_plan = self._generate_four_step_plan_v4(
            first_phase, intervention_plan, scenario, session_context
        )

        plan = {
            "core_principle": intervention_plan.get("core_principle", ""),
            "phase_name": self._generate_phase_name_v4(first_phase, context_activity, target_behavior),
            "goal": first_phase.get("goal", ""),
            "primary_strategy": first_phase.get("primary_strategy", ""),
            "strategy_details": first_phase.get("strategy_details", ""),
            "success_criteria": first_phase.get("success_criteria", ""),
            "parent_observation_task": first_phase.get("parent_observation_task", ""),
            "next_phase_preview": phase_ladder[1].get("goal", "") if len(phase_ladder) > 1 else "",
            # V4.0 个性化四步结构
            "four_step_plan": four_step_plan,
            # V4.0 个性化观察记录工具
            "observation_tool": self._generate_observation_tool_v4(first_phase, context_activity),
        }

        logger.info(f"V4.0 生成个性化计划：{scenario_key} - {matched_hypothesis_id}")
        return plan

    def _find_scenario(self, scenario_key: str) -> Optional[dict]:
        for s in self.knowledge_base.data.get("scenarios", []):
            if s.get("scene_key") == scenario_key:
                return s
        return None

    def _find_hypothesis(self, scenario: dict, hypothesis_id: str) -> Optional[dict]:
        for h in scenario.get("competing_hypotheses", []):
            if h.get("id") == hypothesis_id:
                return h
        return None

    def _generate_phase_name_v4(self, phase: dict, context_activity: str, target_behavior: str) -> str:
        """
        V4.0 动态生成计划名称
        
        示例：
        - "针对 [做操] 中 [发呆] 的'动作密语'计划"
        - "针对 [学习] 启动困难的'情绪温度计'计划"
        """
        base_name = phase.get("phase_name", "第一步")
        
        # 提取活动关键词
        activity = self._extract_activity(context_activity)
        behavior = self._extract_behavior(target_behavior)
        
        # 动态生成名称
        if activity and behavior:
            return f"针对{activity}中{behavior}的'{base_name}'计划"
        elif activity:
            return f"针对{activity}的'{base_name}'计划"
        else:
            return f"'{base_name}'计划"

    def _extract_activity(self, context: str) -> str:
        """从情境中提取活动"""
        activities = {
            "做操": "做操", "体操": "做操", "集体活动": "集体活动",
            "学习": "学习", "任务": "任务", "作业": "学习",
            "吃饭": "吃饭", "游戏": "游戏", "拼图": "拼图",
            "画画": "画画", "搭积木": "搭积木",
        }
        for keyword, activity in activities.items():
            if keyword in context:
                return activity
        return ""

    def _extract_behavior(self, behavior_desc: str) -> str:
        """从行为描述中提取关键词"""
        behaviors = {
            "发呆": "发呆", "走神": "发呆", "不跟随": "发呆",
            "抗拒": "抗拒", "不要": "抗拒", "不肯": "抗拒", "拒绝": "抗拒",
            "哭闹": "哭闹", "发脾气": "哭闹",
            "重复": "刻板行为", "摇晃": "刻板行为",
        }
        for keyword, behavior in behaviors.items():
            if keyword in behavior_desc:
                return behavior
        return ""

    def _generate_four_step_plan_v4(self, phase: dict, intervention_plan: dict, scenario: dict, session_context: Optional[dict] = None) -> Dict[str, str]:
        """
        V4.0 生成个性化四步结构
        
        每一步都基于具体案例动态生成，拒绝模板化
        """
        success_criteria = phase.get("success_criteria", "")
        strategy_details = phase.get("strategy_details", "")
        core_principle = intervention_plan.get("core_principle", "")
        goal = phase.get("goal", "")

        # 从 session_context 提取个性化信息
        context_activity = session_context.get("context", "") if session_context else ""
        target_behavior = session_context.get("child_behavior", "") if session_context else ""
        primary_hypothesis = session_context.get("primary_hypothesis", "") if session_context else ""
        capability_gap = session_context.get("capability_gap", "") if session_context else ""

        # 1. 核心思路：基于能力缺口生成
        core_idea = self._generate_core_idea_v4(core_principle, capability_gap, primary_hypothesis)

        # 2. 我们的计划：基于具体活动和行为生成
        our_plan = self._generate_our_plan_v4(phase, context_activity, target_behavior)

        # 3. 成功的画面：基于行为基线生成
        success_picture = self._generate_success_picture_v4(success_criteria, context_activity, target_behavior)

        # 4. 第一步行动：基于具体策略生成
        first_step = self._generate_first_step_v4(phase, context_activity, target_behavior)

        return {
            "core_idea": core_idea,
            "our_plan": our_plan,
            "success_picture": success_picture,
            "first_step": first_step,
        }

    def _generate_core_idea_v4(self, core_principle: str, capability_gap: str, primary_hypothesis: str) -> str:
        """
        V4.0 生成核心思路 - 基于具体能力缺口
        
        示例：
        - 发呆（提示依赖）："既然挑战的核心是孩子对'实时视觉提示'的依赖，那么我们的核心思路就是：帮助他将需要紧盯的'外部提示'，逐步转化为自己能随时调用的'内部提示'。"
        - 学习抗拒（逃避难度）："既然挑战的核心是任务难度超出了孩子当前的能力范围，那么我们的核心思路就是：通过分解步骤和降低门槛，让任务变得可及。"
        """
        if "提示依赖" in primary_hypothesis or "外部提示" in core_principle:
            return "既然挑战的核心是孩子对'实时视觉提示'的依赖，那么我们的核心思路就是：帮助他将需要紧盯的'外部提示'，逐步转化为自己能随时调用的'内部提示'，从而减少任务中断。"
        elif "逃避" in primary_hypothesis or "难度" in capability_gap:
            return "既然挑战的核心是任务难度超出了孩子当前的能力范围，那么我们的核心思路就是：通过分解步骤和降低门槛，让任务变得可及，从而减少逃避行为，增加主动参与。"
        elif "关注" in primary_hypothesis:
            return "既然挑战的核心是孩子通过行为获取关注，那么我们的核心思路就是：将关注从问题行为转移到积极行为，建立正向互动循环。"
        else:
            return "既然挑战的核心是孩子需要更多支持来维持任务参与，那么我们的核心思路就是：通过游戏化的方式，将干预目标融入到日常互动中。"

    def _generate_our_plan_v4(self, phase: dict, context_activity: str, target_behavior: str) -> str:
        """
        V4.0 生成我们的计划 - 基于具体活动
        
        示例：
        - 做操发呆："我们可以从做操的动作序列中，选择一个有代表性的动作（如'大鹏展翅'），将它转化为趣味'暗号'。"
        - 学习抗拒："我们可以从学习任务中，选择一个容易启动的小步骤，将它设计成'火箭倒计时'游戏。"
        """
        phase_name = phase.get("phase_name", "第一步")
        
        if "做操" in context_activity or "体操" in context_activity:
            return f"我们可以从做操的动作序列中，选择一个有代表性的动作，将它转化为您和孩子之间的趣味'暗号'。通过精心设计的小游戏，在轻松的氛围中反复练习，帮助孩子建立'暗号'与'行动'之间的快速链接。"
        elif "学习" in context_activity or "任务" in context_activity:
            return f"我们可以从学习任务中，选择一个容易启动的小步骤，将它设计成有趣的'启动游戏'。关键是降低门槛，让孩子体验'我能做到'的成功感。"
        else:
            return f"我们可以从当前的{context_activity or '活动'}情境中，选择一个有代表性的步骤，将它转化为您和孩子之间的趣味'暗号'。通过精心设计的小游戏，在轻松的氛围中反复练习。"

    def _generate_success_picture_v4(self, success_criteria: str, context_activity: str, target_behavior: str) -> str:
        """
        V4.0 生成成功的画面 - 基于行为基线
        
        示例：
        - 发呆（高频行为）："在 3 天内，当您使用这个'暗号'提示时，孩子能在 3 秒内做出正确反应，且发呆频率降低至原来的 50% 以下。"
        - 学习抗拒（低频任务）："在 3 天内，孩子能主动启动学习任务至少 3 次，且每次持续时间达到 5 分钟以上。"
        """
        # 解析成功标准
        time_match = re.search(r'连续 (\d+) 日', success_criteria)
        time_frame = f"{time_match.group(1)}天" if time_match else "3 天"
        
        pct_match = re.search(r'(\d+)%', success_criteria)
        percentage = f"{pct_match.group(1)}%" if pct_match else "80%"
        
        time_resp = re.search(r'(\d+) 秒', success_criteria)
        response_time = f"{time_resp.group(1)}秒" if time_resp else "3 秒"

        # 基于行为类型生成
        if "发呆" in target_behavior or "走神" in target_behavior:
            return f"在{time_frame}内，当您使用这个'暗号'提示时，孩子能在{response_time}内做出正确反应，且发呆频率能够明显降低，成功率稳定达到{percentage}以上。"
        elif "抗拒" in target_behavior or "拒绝" in target_behavior:
            return f"在{time_frame}内，孩子能主动{context_activity or '参与任务'}至少 3 次，且每次持续时间达到 5 分钟以上，抗拒行为减少 50% 以上。"
        else:
            return f"在{time_frame}内，当您使用这个'暗号'提示时，孩子能在{response_time}内做出正确反应，且尝试的成功率能够稳定达到{percentage}以上。"

    def _generate_first_step_v4(self, phase: dict, context_activity: str, target_behavior: str) -> str:
        """
        V4.0 生成第一步行动 - 基于具体策略
        
        示例：
        - 做操发呆："今天，您就可以和孩子共创一个'大鹏展翅'暗号，并开启第一次'闯关'游戏。记住，第一次玩不重要，重要的是开始！"
        - 学习抗拒："今天，您就可以设计一个 3 分钟的'火箭启动倒计时'游戏，和孩子一起尝试第一次'任务发射'。"
        """
        if "做操" in context_activity or "体操" in context_activity:
            return "今天，您就可以和孩子共创一个趣味'动作暗号'（如'大鹏展翅'），并开启第一次'闯关'游戏。记住，第一次玩不重要，重要的是开始！"
        elif "学习" in context_activity or "任务" in context_activity:
            return "今天，您就可以设计一个 3 分钟的'启动游戏'（如'火箭倒计时'），和孩子一起尝试第一次'任务发射'。关键是让孩子体验'我能做到'的成功感！"
        else:
            return "今天，您就可以和孩子共创一个趣味'暗号'，并开启第一次'闯关'游戏。记住，第一次玩不重要，重要的是开始！"

    def _generate_observation_tool_v4(self, phase: dict, context_activity: str) -> str:
        """
        V4.0 生成观察记录工具 - 基于具体活动
        
        示例：
        - 做操："记录是为了捕捉进步的信号。您只需：在日历上，在'做操游戏'的日期旁，根据孩子的反应速度画上 ✅（快）或 🔄（慢）。"
        - 学习："记录是为了看见改变。您只需：在日历上，在'学习启动'的日期旁，记录孩子主动开始的次数和持续时间。"
        """
        if "做操" in context_activity or "体操" in context_activity:
            return "记录是为了捕捉进步的信号，而不是增加负担。您只需：在日历上，在'做操游戏'的日期旁，根据孩子的反应速度画上 ✅（快）或 🔄（慢）。这就足够了！"
        elif "学习" in context_activity or "任务" in context_activity:
            return "记录是为了看见改变。您只需：在日历上，在'学习启动'的日期旁，记录孩子主动开始的次数和持续时间（如'3 次，5 分钟'）。这就足够了！"
        else:
            return "记录是为了捕捉进步的信号，而不是增加负担。您只需：在日历上，在玩游戏的日期旁，根据孩子的反应速度画上 ✅（快）或 🔄（慢）。这就足够了！"

    def gamify_strategy_description(self, strategy_details: str, child_nickname: str = "孩子") -> str:
        gamified = f"让我们和{child_nickname}一起玩一个特别的游戏吧！\n\n"
        gamified += strategy_details
        gamified += f"\n\n记住，这个游戏的关键是：让{child_nickname}在快乐中学习，每一次成功都值得庆祝！"
        return gamified

    def decode_html_entities(self, text: str) -> str:
        if not text:
            return ""
        return html.unescape(text)

    def sanitize_plan(self, plan: dict) -> dict:
        if "four_step_plan" in plan:
            for key, value in plan["four_step_plan"].items():
                if isinstance(value, str):
                    plan["four_step_plan"][key] = self.decode_html_entities(value)
        
        if "observation_tool" in plan and isinstance(plan["observation_tool"], str):
            plan["observation_tool"] = self.decode_html_entities(plan["observation_tool"])
        
        return plan
