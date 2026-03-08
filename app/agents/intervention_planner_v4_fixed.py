"""
干预规划器 V4.0 Final - 外科手术式修复版
根治三大问题：1) 数据流断裂 2) 计划模板化 3) 乱码污染

修复原则：
- 严格依据 primary_hypothesis 和 capability_gap 生成计划
- 强力净化所有输出文本
- 拒绝通用模板，实现真正的诊断 - 处方闭环
"""

import logging
import re
import html
from typing import Optional, Dict, Any

from app.knowledge import get_knowledge_base

logger = logging.getLogger(__name__)


class InterventionPlannerV4Fixed:
    """干预规划器 V4.0 Final - 外科手术式修复版"""

    def __init__(self):
        self.knowledge_base = get_knowledge_base()
        logger.info("InterventionPlannerV4Fixed 初始化完成")

    def _sanitize_plan_text(self, text: str) -> str:
        """
        V4.0 Final 强力文本净化 - 根治所有乱码
        
        清理顺序：
        1. 移除所有类 XML/HTML 标签
        2. 移除调试代码（%!(...)、(MISSING) 等）
        3. 解码 HTML 实体
        4. 清理多余空白字符
        """
        if not text:
            return ""
        
        # 1. 移除所有类 XML/HTML 标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 2. 移除调试代码
        text = re.sub(r'%!\([^)]*\)', '', text)
        text = text.replace('(MISSING)', '')
        text = re.sub(r'!?,\s*\(MISSING\)', '', text)
        
        # 3. 解码 HTML 实体
        text = html.unescape(text)
        
        # 4. 清理多余空白字符
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text

    def generate_plan(self, matched_hypothesis_id: str, scenario_key: str, session_context: Optional[dict] = None) -> Optional[Dict[str, Any]]:
        """
        V4.0 Final 基于完整分析结论生成个性化干预计划
        
        核心逻辑：
        - 根据 primary_hypothesis 选择正确的策略骨架
        - 根据 capability_gap 定制具体目标
        - 所有输出文本经过强力净化
        """
        # 从 session_context 提取关键诊断信息
        if not session_context:
            logger.error("session_context 为空，无法生成个性化计划")
            return None
        
        primary_hypothesis = session_context.get("primary_hypothesis", "")
        capability_gap = session_context.get("capability_gap", "")
        context_activity = session_context.get("context", "")
        target_behavior = session_context.get("child_behavior", "")
        
        logger.info(f"V4.0 Final 生成计划：假设={primary_hypothesis}, 缺口={capability_gap}, 活动={context_activity}")
        
        # V4.0 Final 核心：根据 primary_hypothesis 选择策略骨架
        if "逃避" in primary_hypothesis or "逃避困难" in primary_hypothesis:
            plan = self._generate_escape_avoidance_plan(context_activity, target_behavior, capability_gap)
        elif "提示依赖" in primary_hypothesis:
            plan = self._generate_prompt_dependency_plan(context_activity, target_behavior, capability_gap)
        elif "关注" in primary_hypothesis or "寻求关注" in primary_hypothesis:
            plan = self._generate_attention_seeking_plan(context_activity, target_behavior, capability_gap)
        elif "感官" in primary_hypothesis or "自我刺激" in primary_hypothesis:
            plan = self._generate_sensory_plan(context_activity, target_behavior, capability_gap)
        else:
            # 默认使用知识库中的通用计划
            plan = self._generate_from_knowledge_base(matched_hypothesis_id, scenario_key, session_context)
        
        # V4.0 Final 核心：所有文本字段必须经过净化
        if plan:
            plan = self._sanitize_all_text_fields(plan)
            logger.info(f"V4.0 Final 计划生成完成：{plan.get('phase_name', 'Unknown')}")
        
        return plan

    def _generate_escape_avoidance_plan(self, context_activity: str, target_behavior: str, capability_gap: str) -> Dict[str, Any]:
        """
        针对"逃避困难任务"的干预计划
        
        核心策略：降低感知难度，建立启动成功体验
        """
        # 提取活动类型
        activity = self._extract_activity(context_activity)
        
        # 动态生成计划名称
        if "学习" in activity or "任务" in activity:
            phase_name = "启动引擎游戏"
        else:
            phase_name = "难度斜坡计划"
        
        return {
            "phase_name": f"针对{activity}的'{phase_name}'",
            "goal": self._sanitize_plan_text(f"降低{activity}的启动抵触情绪，建立'开始就好'的成功体验。"),
            "core_principle": "通过分解任务和降低起点难度，让孩子体验'我能做到'的成功感，从而减少逃避行为。",
            "four_step_plan": {
                "core_idea": self._sanitize_plan_text(f"既然挑战的核心是{capability_gap or '任务启动困难'}，那么我们的核心思路就是：将大任务切成'微步骤'，让起点变得足够简单，简单到孩子无法拒绝，从而建立'开始就好'的成功体验。"),
                
                "our_plan": self._sanitize_plan_text(f"我们可以从{activity}任务中，选择一个'最小可执行步骤'（如'只写一个字'、'只读一页'），将它设计成一个有趣的'启动游戏'。关键是让孩子体验'我做到了'的成就感，而不是追求完美。"),
                
                "success_picture": self._sanitize_plan_text(f"在 3 天内，孩子能主动开始{activity}任务至少 3 次，且每次持续时间达到 3-5 分钟以上，抵触情绪明显减少。"),
                
                "first_step": self._sanitize_plan_text(f"今天，您就可以尝试将{activity}任务切成一个'3 分钟就能完成的小块'，和孩子一起玩'火箭倒计时发射'游戏。记住，完成比完美重要，开始比结果重要！")
            },
            "observation_tool": self._sanitize_plan_text(f"记录是为了看见改变。您只需：在日历上，在'{activity}启动'的日期旁，记录孩子主动开始的次数和持续时间（如'3 次，5 分钟'）。这就足够了！"),
            "strategy_details": self._sanitize_plan_text(f"1. 将{activity}任务分解为最小可执行步骤。2. 使用'高概率要求序列'（先提 3 个简单要求，再提目标要求）。3. 在孩子完成每个小步骤后给予即时积极反馈。"),
            "success_criteria": self._sanitize_plan_text(f"连续 3 日，每日至少有 3 次主动配合{activity}任务的行为，且每次持续时间达到 5 分钟以上。"),
            "parent_observation_task": self._sanitize_plan_text(f"记录：{activity}任务名称、孩子反应（配合/拒绝）、使用的支持策略、持续时间。"),
        }

    def _generate_prompt_dependency_plan(self, context_activity: str, target_behavior: str, capability_gap: str) -> Dict[str, Any]:
        """
        针对"提示依赖"的干预计划
        
        核心策略：将外部提示转化为内部提示
        """
        activity = self._extract_activity(context_activity)
        
        if "做操" in activity or "体操" in activity:
            phase_name = "动作密语计划"
            first_step = "今天，您就可以和孩子共创一个趣味'动作暗号'（如'大鹏展翅'），并开启第一次'闯关'游戏。"
        else:
            phase_name = "内化提示计划"
            first_step = "今天，您就可以和孩子共创一个趣味'暗号'，并开启第一次'闯关'游戏。"
        
        return {
            "phase_name": f"针对{activity}中{target_behavior or '中断'}的'{phase_name}'",
            "goal": self._sanitize_plan_text(f"帮助{activity}中的外部提示逐步转化为孩子的内部提示，减少任务中断。"),
            "core_principle": "通过创建'内化提示'搭建从外部依赖到内部执行的桥梁，并系统性地渐褪外部支持。",
            "four_step_plan": {
                "core_idea": self._sanitize_plan_text(f"既然挑战的核心是{capability_gap or '对外部提示的依赖'}，那么我们的核心思路就是：帮助他将需要紧盯的'外部提示'，逐步转化为自己能随时调用的'内部提示'，从而减少任务中断。"),
                
                "our_plan": self._sanitize_plan_text(f"我们可以从{activity}的任务序列中，选择一个有代表性的步骤，将它转化为您和孩子之间的趣味'暗号'。通过精心设计的小游戏，在轻松的氛围中反复练习，帮助孩子建立'暗号'与'行动'之间的快速链接。"),
                
                "success_picture": self._sanitize_plan_text(f"在 3 天内，当您使用这个'暗号'提示时，孩子能在 3 秒内做出正确反应，且尝试的成功率能够稳定达到 80% 以上。"),
                
                "first_step": self._sanitize_plan_text(first_step + "记住，第一次玩不重要，重要的是开始！")
            },
            "observation_tool": self._sanitize_plan_text(f"记录是为了捕捉进步的信号。您只需：在日历上，在'{activity}游戏'的日期旁，根据孩子的反应速度画上 ✅（快）或 🔄（慢）。这就足够了！"),
            "strategy_details": self._sanitize_plan_text(f"1. 与孩子共同为任务中的一个标志性动作命名并设计夸张有趣的练习。2. 在自然情境中，当该动作出现时，使用'密语'提示。3. 孩子做出后，给予即时、夸张的积极反馈。"),
            "success_criteria": self._sanitize_plan_text(f"连续 3 日，在自然情境的口头'密语'提示下，3 秒内独立做出正确动作的成功率 ≥ 80%。"),
            "parent_observation_task": self._sanitize_plan_text(f"记录：日期、提示后是否成功（√/×）、反应速度（快/中/慢）。"),
        }

    def _generate_attention_seeking_plan(self, context_activity: str, target_behavior: str, capability_gap: str) -> Dict[str, Any]:
        """针对"寻求关注"的干预计划"""
        activity = self._extract_activity(context_activity)
        
        return {
            "phase_name": f"针对{activity}的'关注重定向计划'",
            "goal": self._sanitize_plan_text(f"将关注从{target_behavior or '问题行为'}转移到积极行为，建立正向互动循环。"),
            "core_principle": "减少对问题行为的关注，增加对配合行为的积极关注，建立正向互动循环。",
            "four_step_plan": {
                "core_idea": self._sanitize_plan_text(f"既然挑战的核心是{capability_gap or '通过行为获取关注'}，那么我们的核心思路就是：将关注从问题行为转移到配合行为，让孩子发现'做好行为'比'问题行为'能获得更多更好的关注。"),
                
                "our_plan": self._sanitize_plan_text(f"当{target_behavior or '问题行为'}发生时，保持冷静、中性的态度，用最少的语言完成任务。当配合发生时，立即给予热情、具体的积极关注。"),
                
                "success_picture": self._sanitize_plan_text(f"在 3 天内，配合行为频率增加 40% 以上，问题行为频率减少 30% 以上。"),
                
                "first_step": self._sanitize_plan_text(f"今天，您就可以尝试'差异化关注'：当孩子配合时，立即给予热情具体的表扬；当出现问题行为时，保持冷静中性，用最少的语言处理。")
            },
            "observation_tool": self._sanitize_plan_text(f"记录是为了发现模式。您只需：在日历上，记录每天配合行为和问题行为的次数，观察它们的变化趋势。"),
        }

    def _generate_sensory_plan(self, context_activity: str, target_behavior: str, capability_gap: str) -> Dict[str, Any]:
        """针对"感官/自我刺激"的干预计划"""
        activity = self._extract_activity(context_activity)
        
        return {
            "phase_name": f"针对{activity}的'感觉调节计划'",
            "goal": self._sanitize_plan_text(f"在{activity}前提供适当的感官输入，降低自我刺激需求。"),
            "core_principle": "先接纳感官需求，再将任务与特殊兴趣结合，逐步提高任务吸引力。",
            "four_step_plan": {
                "core_idea": self._sanitize_plan_text(f"既然挑战的核心是{capability_gap or '感官调节需求'}，那么我们的核心思路就是：在任务前提供适当的感官输入，降低自我刺激需求，再将任务内容与孩子的特殊兴趣建立联系。"),
                
                "our_plan": self._sanitize_plan_text(f"识别孩子偏好的感官类型（视觉、听觉、触觉等），在{activity}前 5 分钟提供相应的感官活动。同时将任务动作与兴趣元素结合。"),
                
                "success_picture": self._sanitize_plan_text(f"在 3 天内，{activity}中的自我刺激行为减少 50% 以上，参与度（跟随时间/总时间）达到 70% 以上。"),
                
                "first_step": self._sanitize_plan_text(f"今天，您就可以在{activity}前 5 分钟，给孩子提供他喜欢的感官活动（如挤压球、听轻音乐），观察并记录哪种感官输入最有效。")
            },
            "observation_tool": self._sanitize_plan_text(f"记录是为了找到规律。您只需：记录感觉活动类型、持续时间、{activity}中自我刺激行为次数。"),
        }

    def _generate_from_knowledge_base(self, matched_hypothesis_id: str, scenario_key: str, session_context: dict) -> Optional[Dict[str, Any]]:
        """从知识库生成计划（备用方案）"""
        scenario = None
        for s in self.knowledge_base.data.get("scenarios", []):
            if s.get("scene_key") == scenario_key:
                scenario = s
                break
        
        if not scenario:
            return None
        
        hypothesis = None
        for h in scenario.get("competing_hypotheses", []):
            if h.get("id") == matched_hypothesis_id:
                hypothesis = h
                break
        
        if not hypothesis:
            return None
        
        intervention_plan = hypothesis.get("intervention_plan")
        if not intervention_plan:
            return None
        
        phase_ladder = intervention_plan.get("phase_ladder", [])
        if not phase_ladder:
            return None
        
        first_phase = phase_ladder[0]
        context_activity = session_context.get("context", "")
        
        return {
            "phase_name": first_phase.get("phase_name", "第一步"),
            "goal": self._sanitize_plan_text(first_phase.get("goal", "")),
            "core_principle": self._sanitize_plan_text(intervention_plan.get("core_principle", "")),
            "four_step_plan": {
                "core_idea": self._sanitize_plan_text(self._generate_core_idea_from_principle(intervention_plan.get("core_principle", ""))),
                "our_plan": self._sanitize_plan_text(first_phase.get("strategy_details", "")),
                "success_picture": self._sanitize_plan_text(first_phase.get("success_criteria", "")),
                "first_step": self._sanitize_plan_text(f"今天，您就可以开始尝试{first_phase.get('primary_strategy', '第一步策略')}。"),
            },
            "observation_tool": self._sanitize_plan_text(first_phase.get("parent_observation_task", "")),
            "strategy_details": self._sanitize_plan_text(first_phase.get("strategy_details", "")),
            "success_criteria": self._sanitize_plan_text(first_phase.get("success_criteria", "")),
            "parent_observation_task": self._sanitize_plan_text(first_phase.get("parent_observation_task", "")),
        }

    def _generate_core_idea_from_principle(self, core_principle: str) -> str:
        """从核心原则生成核心思路"""
        if "提示依赖" in core_principle or "外部提示" in core_principle:
            return "既然挑战的核心是孩子对'实时视觉提示'的依赖，那么我们的核心思路就是：帮助他将需要紧盯的'外部提示'，逐步转化为自己能随时调用的'内部提示'。"
        elif "逃避" in core_principle:
            return "既然挑战的核心是任务难度超出了孩子当前的能力范围，那么我们的核心思路就是：通过分解步骤和降低门槛，让任务变得可及。"
        else:
            return "既然挑战的核心是孩子需要更多支持来维持任务参与，那么我们的核心思路就是：通过游戏化的方式，将干预目标融入到日常互动中。"

    def _extract_activity(self, context: str) -> str:
        """从情境中提取活动"""
        activities = {
            "做操": "做操", "体操": "做操", "集体活动": "集体活动",
            "学习": "学习", "任务": "学习", "作业": "学习",
            "吃饭": "吃饭", "游戏": "游戏", "拼图": "拼图",
            "画画": "画画", "搭积木": "搭积木",
        }
        for keyword, activity in activities.items():
            if keyword in context:
                return activity
        return "当前活动"

    def _sanitize_all_text_fields(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """递归净化字典中的所有文本字段"""
        if isinstance(plan, dict):
            return {key: self._sanitize_all_text_fields(value) for key, value in plan.items()}
        elif isinstance(plan, list):
            return [self._sanitize_all_text_fields(item) for item in plan]
        elif isinstance(plan, str):
            return self._sanitize_plan_text(plan)
        else:
            return plan
