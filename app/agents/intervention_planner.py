"""
干预规划器 V4.3 Hotfix - 功能判断驱动的个性化干预
核心修复：根据 functional_judgment 选择完全不同的干预模板

V4.3 核心原则：
- 提示依赖 → 建立视觉/动作锚点，将外部提示内化
- 逃避难度 → 任务分解，降低起点，高频成功体验
- 严禁混用模板！
"""

import logging
import re
import html
from typing import Optional, Dict, Any

from app.knowledge import get_knowledge_base

logger = logging.getLogger(__name__)


class InterventionPlanner:
    """干预规划器 V4.3 Hotfix - 功能判断驱动"""

    def __init__(self):
        """初始化规划器"""
        self.knowledge_base = get_knowledge_base()
        logger.info("InterventionPlanner V4.3 Hotfix 初始化完成")

    def generate_plan(self, matched_hypothesis_id: str, scenario_key: str, session_context: Optional[dict] = None) -> Optional[Dict[str, Any]]:
        """
        V4.3 Hotfix 根据功能判断生成个性化干预计划
        
        核心修复：根据 functional_judgment 选择完全不同的干预模板

        Args:
            matched_hypothesis_id: 匹配的假设 ID（如 "H1"）
            scenario_key: 场景键（如 "task_disengagement"）
            session_context: 会话上下文（包含 functional_judgment 等关键信息）

        Returns:
            干预计划字典，包含四步结构
        """
        # V4.3 Hotfix 核心：从 session_context 提取功能判断
        functional_judgment = session_context.get("primary_hypothesis", "") if session_context else ""
        capability_gap = session_context.get("capability_gap", "") if session_context else ""
        context_activity = session_context.get("context", "") if session_context else ""
        
        logger.info(f"V4.3 Hotfix 生成计划：functional_judgment={functional_judgment[:50] if functional_judgment else 'N/A'}...")
        
        # === V4.3 Hotfix 核心：根据功能判断选择完全不同的干预模板 ===
        # V4.5.3 修复：使用 AND 逻辑，确保精确匹配
        if functional_judgment and "提示依赖" in functional_judgment:
            # 提示依赖：建立视觉/动作锚点
            logger.info("V4.3 Hotfix: 选择提示依赖干预模板")
            return self._generate_prompt_dependence_plan(session_context)
        
        elif functional_judgment and "逃避" in functional_judgment and "难度" in functional_judgment:
            # 逃避难度：任务分解，降低起点（必须同时包含"逃避"和"难度"）
            logger.info("V4.3 Hotfix: 选择逃避难度干预模板（任务分解）")
            return self._generate_escape_difficulty_plan(session_context)
        
        elif functional_judgment and "关注" in functional_judgment:
            # 寻求关注：关注重定向
            logger.info("V4.3 Hotfix: 选择寻求关注干预模板")
            return self._generate_attention_seeking_plan(session_context)
        
        # 降级方案：使用知识库模板
        logger.info("V4.3 Hotfix: 使用知识库降级方案")
        return self._generate_from_knowledge_base(matched_hypothesis_id, scenario_key, session_context)
    
    def generate_plan_with_narrative(self, matched_hypothesis_id: str, scenario_key: str, session_context: Optional[dict] = None, narrative: Optional[dict] = None) -> Optional[Dict[str, Any]]:
        """
        V4.5.3 核心修复：基于功能判断生成干预计划
        
        核心原则：干预计划必须与功能判断严格匹配！
        诊断是"提示依赖"→干预必须是"建立视觉/动作锚点"
        诊断是"逃避难度"→干预必须是"任务分解，降低起点"
        诊断是"寻求关注"→干预必须是"关注重定向"
        
        V4.5.3 修复：narrative 仅用于丰富干预细节，不覆盖功能判断选择的模板
        """
        # V4.5.3 核心修复：优先使用 functional_judgment 选择模板
        functional_judgment = session_context.get("primary_hypothesis", "") if session_context else ""
        
        logger.info(f"V4.5.3 生成计划：functional_judgment={functional_judgment[:80] if functional_judgment else 'N/A'}...")
        
        # === V4.5.3 核心：根据功能判断选择干预模板（严格匹配）===
        
        # 规则 1：提示依赖 → 建立视觉/动作锚点
        if functional_judgment and "提示依赖" in functional_judgment:
            logger.info("V4.5.3: 选择提示依赖干预模板（视觉/动作锚点）")
            return self._generate_prompt_dependence_plan(session_context)
        
        # 规则 2：逃避难度 → 任务分解，降低起点
        elif functional_judgment and ("逃避" in functional_judgment and "难度" in functional_judgment):
            logger.info("V4.5.3: 选择逃避难度干预模板（任务分解）")
            return self._generate_escape_difficulty_plan(session_context)
        
        # 规则 3：寻求关注 → 关注重定向
        # 扩展匹配：包含"寻求关注"、"吸引注意"、"互动需求"等
        elif functional_judgment and any(kw in functional_judgment for kw in ["关注", "注意", "互动"]):
            logger.info("V4.5.3: 选择寻求关注干预模板（关注重定向）")
            return self._generate_attention_seeking_plan(session_context)
        
        # 规则 4：感觉逃避 → 环境调整 + 脱敏
        # 扩展匹配：包含"感觉逃避"、"感觉敏感"、"逃避不适"、"听觉过敏"等
        elif functional_judgment and any(kw in functional_judgment for kw in ["感觉逃避", "感觉敏感", "逃避不适", "听觉过敏", "触觉敏感"]):
            logger.info("V4.5.3: 选择感觉逃避干预模板（环境调整）")
            return self._generate_sensory_escape_plan(session_context)
        
        # 规则 5：自我刺激/自动强化 → 替代性感官输入
        elif functional_judgment and ("自我刺激" in functional_judgment or "自动" in functional_judgment):
            logger.info("V4.5.3: 选择自我刺激干预模板（替代性感官）")
            return self._generate_self_stimulation_plan(session_context)
        
        # 规则 6：过渡困难 → 预告 + 选择权
        elif functional_judgment and "过渡" in functional_judgment:
            logger.info("V4.5.3: 选择过渡困难干预模板（预告 + 选择）")
            return self._generate_transition_plan(session_context)
        
        # 降级方案：使用叙事性归因辅助选择（但不覆盖功能判断）
        # V4.5.3 修复：增加感觉逃避检查，避免错配到序列支持
        if narrative:
            primary_attribution = narrative.get("primary_attribution", "")
            logger.info(f"V4.5.3: 功能判断不明确，使用叙事归因辅助：{primary_attribution[:50]}...")
            
            # 优先检查感觉逃避（避免错配到序列支持）
            if any(kw in primary_attribution for kw in ["感觉", "听觉", "触觉", "噪音", "声音", "过敏"]):
                logger.info("V4.5.3: 选择感觉逃避干预模板（叙事归因辅助）")
                return self._generate_sensory_escape_plan(session_context)
            
            # 检查工作记忆/序列记忆
            elif "工作记忆" in primary_attribution or "序列记忆" in primary_attribution:
                logger.info("V4.5.3: 选择序列支持干预模板（辅助）")
                return self._generate_sequential_support_plan(session_context, primary_attribution)
            
            # 检查注意力
            elif "注意" in primary_attribution:
                logger.info("V4.5.3: 选择注意力支持干预模板（辅助）")
                return self._generate_attention_support_plan(session_context, primary_attribution)
        
        # 最终降级：基于功能标签
        logger.info("V4.5.3: 降级到基于功能标签的模板")
        return self.generate_plan(matched_hypothesis_id, scenario_key, session_context)

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

    # ========== V4.3 Hotfix 核心干预模板 ==========

    def _generate_prompt_dependence_plan(self, session_context: Optional[dict] = None) -> Dict[str, Any]:
        """
        V4.3 Hotfix 提示依赖干预模板
        
        核心策略：建立视觉/动作锚点，将外部提示内化
        严禁用于逃避难度！
        """
        context_activity = session_context.get("context", "") if session_context else ""
        child_behavior = session_context.get("child_behavior", "") if session_context else ""
        
        # 提取活动关键词
        activity = self._extract_activity_keyword(context_activity)
        
        return {
            "phase_name": f"针对{activity}的'动作锚点'计划",
            "goal": f"帮助孩子在{activity}中将外部视觉提示转化为内部提示，减少任务中断。",
            "core_principle": "通过创建'内化提示'搭建从外部依赖到内部执行的桥梁，并系统性地渐褪外部支持。",
            "four_step_plan": {
                "core_idea": f"既然挑战的核心是孩子对'实时视觉提示'的依赖，那么我们的核心思路就是：帮助他将需要紧盯的'外部提示'，逐步转化为自己能随时调用的'内部提示'，从而减少{activity}中的任务中断。",
                
                "our_plan": f"我们可以从{activity}的动作序列中，选择一个有代表性的步骤，将它转化为您和孩子之间的趣味'暗号'。通过精心设计的小游戏，在轻松的氛围中反复练习，帮助孩子建立'暗号'与'行动'之间的快速链接。",
                
                "success_picture": f"在 3 天内，当您使用这个'暗号'提示时，孩子能在 3 秒内做出正确反应，且尝试的成功率能够稳定达到 80% 以上。",
                
                "first_step": f"今天，您就可以和孩子共创一个趣味'动作暗号'（如'大鹏展翅'），并开启第一次'闯关'游戏。记住，第一次玩不重要，重要的是开始！"
            },
            "observation_tool": f"记录是为了捕捉进步的信号。您只需：在日历上，在'{activity}游戏'的日期旁，根据孩子的反应速度画上 ✅（快）或 🔄（慢）。这就足够了！",
            "strategy_details": f"1. 与孩子共同为{activity}中的一个标志性动作命名并设计夸张有趣的练习。2. 在自然情境中，当该动作出现时，使用'密语'提示。3. 孩子做出后，给予即时、夸张的积极反馈。",
            "success_criteria": f"连续 3 日，在自然情境的口头'密语'提示下，3 秒内独立做出正确动作的成功率 ≥ 80%。",
            "parent_observation_task": f"记录：日期、提示后是否成功（√/×）、反应速度（快/中/慢）。",
        }

    def _generate_escape_difficulty_plan(self, session_context: Optional[dict] = None) -> Dict[str, Any]:
        """
        V4.3 Hotfix 逃避难度干预模板
        
        核心策略：任务分解，降低起点，高频成功体验
        严禁用于提示依赖！
        """
        context_activity = session_context.get("context", "") if session_context else ""
        child_behavior = session_context.get("child_behavior", "") if session_context else ""
        
        # 提取活动关键词
        activity = self._extract_activity_keyword(context_activity)
        
        return {
            "phase_name": f"针对{activity}的'成功阶梯'计划",
            "goal": f"降低{activity}的启动抵触情绪，建立'开始就好'的成功体验。",
            "core_principle": "通过分解任务和降低起点难度，让孩子体验'我能做到'的成功感，从而减少逃避行为。",
            "four_step_plan": {
                "core_idea": f"既然挑战的核心是{activity}对孩子来说太难了，那么我们的核心思路就是：将大任务切成'微步骤'，让起点变得足够简单，简单到孩子无法拒绝，从而建立'开始就好'的成功体验。",
                
                "our_plan": f"我们可以从{activity}任务中，选择一个'最小可执行步骤'（如'只写一个字'、'只做一道题'），将它设计成一个有趣的'启动游戏'。关键是让孩子体验'我做到了'的成就感，而不是追求完美。",
                
                "success_picture": f"在 3 天内，孩子能主动开始{activity}任务至少 3 次，且每次持续时间达到 3-5 分钟以上，抵触情绪明显减少。",
                
                "first_step": f"今天，您就可以尝试将{activity}任务切成一个'3 分钟就能完成的小块'，和孩子一起玩'火箭倒计时发射'游戏。记住，完成比完美重要，开始比结果重要！"
            },
            "observation_tool": f"记录是为了看见改变。您只需：在日历上，在'{activity}启动'的日期旁，记录孩子主动开始的次数和持续时间（如'3 次，5 分钟'）。这就足够了！",
            "strategy_details": f"1. 将{activity}任务分解为最小可执行步骤。2. 使用'高概率要求序列'（先提 3 个简单要求，再提目标要求）。3. 在孩子完成每个小步骤后给予即时积极反馈。",
            "success_criteria": f"连续 3 日，每日至少有 3 次主动配合{activity}任务的行为，且每次持续时间达到 5 分钟以上。",
            "parent_observation_task": f"记录：{activity}任务名称、孩子反应（配合/拒绝）、使用的支持策略、持续时间。",
        }

    def _generate_attention_seeking_plan(self, session_context: Optional[dict] = None) -> Dict[str, Any]:
        """V4.3 Hotfix 寻求关注干预模板"""
        context_activity = session_context.get("context", "") if session_context else ""
        activity = self._extract_activity_keyword(context_activity)
        
        return {
            "phase_name": f"针对{activity}的'关注重定向'计划",
            "goal": f"将关注从{activity}中的问题行为转移到积极行为，建立正向互动循环。",
            "core_principle": "减少对问题行为的关注，增加对配合行为的积极关注，建立正向互动循环。",
            "four_step_plan": {
                "core_idea": f"既然挑战的核心是孩子通过行为获取关注，那么我们的核心思路就是：将关注从问题行为转移到配合行为，让孩子发现'做好行为'比'问题行为'能获得更多更好的关注。",
                
                "our_plan": f"当{activity}中的问题行为发生时，保持冷静、中性的态度，用最少的语言完成任务。当配合发生时，立即给予热情、具体的积极关注。",
                
                "success_picture": f"在 3 天内，配合行为频率增加 40% 以上，问题行为频率减少 30% 以上。",
                
                "first_step": f"今天，您就可以尝试'差异化关注'：当孩子配合时，立即给予热情具体的表扬；当出现问题行为时，保持冷静中性，用最少的语言处理。"
            },
            "observation_tool": f"记录是为了发现模式。您只需：在日历上，记录每天配合行为和问题行为的次数，观察它们的变化趋势。",
        }
    
    def _generate_sensory_escape_plan(self, session_context: Optional[dict] = None) -> Dict[str, Any]:
        """V4.5.3 感觉逃避干预模板"""
        context_activity = session_context.get("context", "") if session_context else ""
        activity = self._extract_activity_keyword(context_activity)
        
        return {
            "phase_name": f"针对{activity}的'感觉友好'计划",
            "goal": f"调整环境刺激，帮助孩子逐步适应{activity}中的感觉挑战。",
            "core_principle": "通过环境调整和系统脱敏，减少感觉超载，帮助孩子建立感觉耐受性。",
            "four_step_plan": {
                "core_idea": "既然挑战的核心是环境刺激超出了孩子的感觉处理能力，那么我们的核心思路就是：先调整环境减少刺激，再逐步帮助孩子建立感觉耐受性。",
                "our_plan": "我们可以从调整环境开始（如降低噪音、减少视觉干扰），同时为孩子提供感觉工具（如降噪耳塞），然后逐步延长在环境中的时间。",
                "success_picture": "在 1 周内，孩子能在调整后的环境中停留时间延长 50% 以上，抵触情绪明显减少。",
                "first_step": "今天，您就可以尝试为孩子准备降噪耳塞，并在去环境前进行预告，让孩子有心理准备。"
            },
        }
    
    def _generate_self_stimulation_plan(self, session_context: Optional[dict] = None) -> Dict[str, Any]:
        """V4.5.3 自我刺激干预模板"""
        context_activity = session_context.get("context", "") if session_context else ""
        activity = self._extract_activity_keyword(context_activity)
        
        return {
            "phase_name": f"针对{activity}的'替代性感官'计划",
            "goal": f"为孩子提供适当的替代性感官输入，减少自我刺激行为。",
            "core_principle": "通过提供功能等价的替代性感官活动，满足孩子的感官需求，同时减少不适当的自我刺激。",
            "four_step_plan": {
                "core_idea": "既然挑战的核心是孩子需要特定的感官输入，那么我们的核心思路就是：提供功能等价但更适当的替代活动，满足感官需求。",
                "our_plan": "我们可以观察孩子从自我刺激中获得什么感官输入，然后设计类似的但更适当的活动（如提供压力球替代晃手）。",
                "success_picture": "在 1 周内，自我刺激行为频率减少 40%，替代活动使用频率增加。",
                "first_step": "今天，您就可以尝试提供一个替代性感官玩具（如压力球、纹理球），在孩子开始自我刺激时温和地递给他。"
            },
        }
    
    def _generate_transition_plan(self, session_context: Optional[dict] = None) -> Dict[str, Any]:
        """V4.5.3 过渡困难干预模板"""
        context_activity = session_context.get("context", "") if session_context else ""
        activity = self._extract_activity_keyword(context_activity)
        
        return {
            "phase_name": f"针对{activity}的'预告 + 选择'计划",
            "goal": f"通过预告和提供选择权，帮助孩子顺利过渡到{activity}。",
            "core_principle": "通过提前预告和提供有限选择，增加孩子的控制感和可预测性，减少过渡抵触。",
            "four_step_plan": {
                "core_idea": "既然挑战的核心是活动转换的不可预测性，那么我们的核心思路就是：通过预告增加可预测性，通过选择权增加控制感。",
                "our_plan": "我们可以在活动转换前 5-10 分钟开始预告，使用视觉提示卡或计时器，并提供有限选择（如'先穿衣还是先刷牙'）。",
                "success_picture": "在 1 周内，活动转换时的抵触行为减少 50%，配合度明显提高。",
                "first_step": "今天，您就可以尝试使用'5 分钟预告'：在活动转换前 5 分钟告诉孩子，并使用计时器帮助他理解时间。"
            },
        }

    def _extract_activity_keyword(self, context: str) -> str:
        """从情境中提取活动关键词"""
        if not context:
            return "当前活动"
        
        activities = {
            "做操": "做操", "体操": "做操", "跳操": "做操",
            "学习": "学习", "作业": "学习", "做题": "学习",
            "吃饭": "吃饭", "游戏": "游戏",
        }
        for keyword, activity in activities.items():
            if keyword in context:
                return activity
        return "当前活动"

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
    
    # ========== V4.5.1 新增干预模板 ==========
    
    def _generate_sensory_friendly_plan(self, session_context: Optional[dict] = None, primary_attribution: str = "") -> Dict[str, Any]:
        """
        V4.5.1 感觉友好干预模板
        
        适用于：感觉处理挑战、环境超载、嘈杂环境等归因
        """
        context_activity = session_context.get("context", "") if session_context else ""
        activity = self._extract_activity_keyword(context_activity)
        
        return {
            "phase_name": f"针对{activity}的'感觉友好'计划",
            "goal": f"调整{activity}环境，减少感觉超载，提升孩子的参与舒适度。",
            "core_principle": "通过环境调整和感觉支持，降低外部干扰，让孩子能够专注于任务本身。",
            "four_step_plan": {
                "core_idea": f"既然挑战的核心是环境中的感觉刺激（如噪音、光线、触觉）超出了孩子当前的处理能力，那么我们的核心思路就是：首先调整环境，减少不必要的感觉干扰，然后提供适当的感觉支持（如降噪耳塞），帮助孩子更好地参与{activity}。",
                "our_plan": f"我们可以从{activity}的环境调整开始：1) 优化站位（远离音响、靠近老师）；2) 简化听觉输入（必要时使用降噪耳塞）；3) 提供视觉支持（清晰的视觉提示卡）。",
                "success_picture": f"在 3 天内，孩子在{activity}中的不适表现减少 50% 以上，参与度（跟随时间/总时间）达到 70% 以上。",
                "first_step": f"今天，您就可以尝试调整孩子的站位：让他站在靠近老师、远离音响的位置，观察并记录他的反应变化。"
            },
            "observation_tool": f"记录是为了发现环境因素的影响。您只需：在日历上，记录每天{activity}的环境特点（安静/嘈杂）和孩子的反应（积极/中性/消极）。",
        }
    
    def _generate_sequential_support_plan(self, session_context: Optional[dict] = None, primary_attribution: str = "") -> Dict[str, Any]:
        """
        V4.5.1 序列支持干预模板
        
        适用于：工作记忆挑战、多步骤任务、动作记忆等归因
        """
        context_activity = session_context.get("context", "") if session_context else ""
        activity = self._extract_activity_keyword(context_activity)
        
        return {
            "phase_name": f"针对{activity}的'序列支持'计划",
            "goal": f"通过视觉化和简化步骤，帮助孩子记住{activity}的动作序列。",
            "core_principle": "将多步骤任务视觉化、简化，降低工作记忆负荷，让孩子能够独立完成任务序列。",
            "four_step_plan": {
                "core_idea": f"既然挑战的核心是孩子在记住多步骤动作序列时遇到困难，那么我们的核心思路就是：将复杂的动作序列转化为可视化的、易于记忆的'步骤图'，并提供'锚点动作'作为序列的起始点，帮助孩子更轻松地跟随和记忆。",
                "our_plan": f"我们可以为{activity}创建一个简单的'动作步骤图'（3-4 个关键步骤的图片或图标），并在活动前和孩子一起复习。同时选择一个'锚点动作'作为序列的开始信号。",
                "success_picture": f"在 3 天内，孩子能在最少提示下独立完成{activity}的 80% 以上步骤，且'锚点动作'的启动时间缩短至 3 秒内。",
                "first_step": f"今天，您就可以和孩子一起制作一个简易的'{activity}步骤图'（可以用手机拍照或简单绘画），并在活动前和他一起看一遍。"
            },
            "observation_tool": f"记录是为了追踪序列记忆的进步。您只需：在日历上，记录孩子独立完成的步骤数（如'3/5 步'）和需要的提示类型（视觉/语言/身体）。",
        }
    
    def _generate_attention_support_plan(self, session_context: Optional[dict] = None, primary_attribution: str = "") -> Dict[str, Any]:
        """
        V4.5.1 注意力支持干预模板
        
        适用于：持续性注意挑战、容易分心、走神等归因
        """
        context_activity = session_context.get("context", "") if session_context else ""
        activity = self._extract_activity_keyword(context_activity)
        
        return {
            "phase_name": f"针对{activity}的'专注力支持'计划",
            "goal": f"通过分段和强化，提升孩子在{activity}中的持续性注意。",
            "core_principle": "将长任务分段，并提供即时强化，逐步延长孩子的专注时间。",
            "four_step_plan": {
                "core_idea": f"既然挑战的核心是孩子在干扰环境下难以维持持续性注意力，那么我们的核心思路就是：将{activity}分成更小的时间段（如 30 秒 -2 分钟），每段都有明确的开始和结束信号（如计时器），并在每段结束后给予即时强化，帮助孩子逐步延长专注时间。",
                "our_plan": f"我们可以使用'专注 - 休息'循环：先设定一个很短的专注时间（如 30 秒），用计时器或音乐作为信号，完成后给予即时强化（如击掌、贴纸），然后逐渐延长时间。",
                "success_picture": f"在 3 天内，孩子的专注时间从 30 秒延长至 2 分钟以上，且分心行为减少 40% 以上。",
                "first_step": f"今天，您就可以尝试'30 秒挑战'：设定一个 30 秒的计时器，和孩子一起专注{activity}，时间到了就给予热烈的庆祝，然后逐渐增加时间。"
            },
            "observation_tool": f"记录是为了看见专注力的进步。您只需：在日历上，记录孩子每次专注的时长（秒）和分心的次数。",
        }
