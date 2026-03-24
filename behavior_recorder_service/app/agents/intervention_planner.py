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
    """干预规划器 V4.5.21 P0 Fix - 安全校验 + 强制映射 + 输出前校验"""

    def __init__(self):
        """初始化规划器"""
        self.knowledge_base = get_knowledge_base()
        logger.info("InterventionPlanner V4.5.21 P0 Fix 初始化完成")
    
    # ========== V4.5.21 P0 核心修复 ==========
    
    def _check_safety_priority(self, session_context: Optional[dict] = None) -> bool:
        """
        V4.5.21 P0-2: 安全优先检查
        
        检查行为描述是否涉及安全风险，如果是则必须优先处理安全
        
        Returns:
            bool: True 表示涉及安全，需要启用安全优先模式
        """
        if not session_context:
            return False
        
        # 危险关键词列表（高优先级 - 低误报）
        danger_keywords_high = [
            "爬高", "危险", "利器", "冲撞", "跑到马路", "触电", "溺水", "水池",
            "从高处", "跳下", "攀爬", "窗户", "阳台", "烫",
            "尖锐", "刀子", "剪刀", "电源", "插座", "车祸", "交通"
        ]
        
        # 危险关键词（需要上下文确认 - 避免误报）
        danger_keywords_context = [
            ("火", ["玩火", "点火", "烧", "火灾", "打火机", "火柴"]),  # 排除"发火"（发脾气）
        ]
        
        child_behavior = session_context.get("child_behavior", "")
        context = session_context.get("context", "")
        context_activity = session_context.get("context", "")
        
        # 检查所有相关字段
        check_text = f"{child_behavior}{context}{context_activity}"
        
        # 第一类：高优先级关键词（直接触发）
        for keyword in danger_keywords_high:
            if keyword in check_text:
                logger.warning(
                    f"⚠️ P0-2 安全优先触发 | "
                    f"危险关键词：'{keyword}' | "
                    f"行为：{child_behavior[:50]} | "
                    f"已启用安全优先模式"
                )
                return True
        
        # 第二类：需要上下文确认的关键词
        for keyword, required_contexts in danger_keywords_context:
            if keyword in check_text:
                # 检查是否有危险上下文
                has_danger_context = any(ctx in check_text for ctx in required_contexts)
                # 检查是否有排除上下文（如"发火"表示发脾气）
                has_excluded_context = any(excl in check_text for excl in ["发火", "生气", "脾气"])
                
                if has_danger_context and not has_excluded_context:
                    logger.warning(
                        f"⚠️ P0-2 安全优先触发 | "
                        f"危险关键词：'{keyword}' + 危险上下文 | "
                        f"行为：{child_behavior[:50]} | "
                        f"已启用安全优先模式"
                    )
                    return True
        
        return False
    
    def _generate_safety_first_plan(self, session_context: Optional[dict] = None) -> Dict[str, Any]:
        """
        V4.5.21 P0-2: 安全优先干预模板
        
        核心原则：安全永远是第一原则。任何行为干预都不能以牺牲安全为代价。
        """
        context_activity = session_context.get("context", "") if session_context else ""
        activity = self._extract_activity_keyword(context_activity) if context_activity else "当前情境"
        
        return {
            "phase_name": f"针对{activity}的'安全优先'计划",
            "goal": f"确保孩子安全的前提下处理行为问题",
            "core_principle": "安全永远是第一原则。任何行为干预都不能以牺牲安全为代价。",
            "four_step_plan": {
                "core_idea": f"既然行为涉及安全风险，那么我们的首要任务是确保环境安全，然后再处理行为功能。绝不能简单'忽视'危险行为。",
                
                "our_plan": f"我们可以采用'安全三步法'：\n\n1. **立即消除危险**：检查并移除环境中的危险因素（如锁好窗户、收好利器、安装防护栏）。\n\n2. **安全前提下最小化反应**：在确保环境安全后，对问题行为保持冷静，避免过度情绪反应强化行为。\n\n3. **教授安全替代行为**：教孩子用安全的方式满足相同需求（如用蹦床替代爬高）。\n\n4. **持续监控**：定期检查安全状况，确保防护措施有效。",
                
                "success_picture": f"危险行为频率下降，且未发生安全事故。孩子能使用安全的替代行为满足需求。",
                
                "first_step": f"今天，请立即检查并消除{activity}环境中的危险因素。例如：如果孩子爬高，请安装防护栏或移除可攀爬物品；如果有利器，请锁好或放到孩子够不到的地方。"
            },
            "observation_tool": f"记录是为了确保安全。您只需：在日历上，记录每天的危险行为次数和是否有安全事故（应该为 0）。重点是确保'零事故'。",
            
            # P0-2 新增：安全警示
            "safety_warning": "⚠️ 重要：对于危险行为，绝不能简单'忽视'或'让孩子自己承担后果'。安全永远是第一位的！"
        }
    
    def _validate_diagnosis_intervention_match(self, diagnosis: str, plan: dict) -> bool:
        """
        V4.5.21 P0-3: 输出前校验
        
        校验诊断结论与干预策略是否匹配，防止"开错药"
        
        Args:
            diagnosis: 诊断/功能判断文本
            plan: 生成的干预计划字典
        
        Returns:
            bool: True 表示匹配，False 表示不匹配需要重新生成
        """
        if not diagnosis or not plan:
            return True  # 无法校验时放过
        
        # 定义不允许的诊断 - 干预组合（"开错药"模式）
        forbidden_combinations = [
            # 社交技能不足 × 行为管理模板
            ("社交技能", "忽视"),
            ("社交技能", "冷静角"),
            ("社交技能", "坐冷静"),
            ("社交", "忽视"),
            ("社交", "冷静角"),
            
            # 坚持同一性/刻板行为 × 行为管理模板
            ("坚持同一性", "忽视"),
            ("坚持同一性", "冷静角"),
            ("刻板", "忽视"),
            ("刻板", "冷静角"),
            ("仪式", "忽视"),
            
            # 注意力/执行功能 × 后果法
            ("注意力", "自然结果"),
            ("注意力", "减少任务"),
            ("注意缺陷", "忽视"),
            ("工作记忆", "忽视"),
            
            # 感觉处理 × 行为管理
            ("感觉", "忽视"),
            ("感觉", "冷静角"),
            ("过敏", "忽视"),
            
            # 情绪调节 × 纯行为管理
            ("情绪调节", "忽视"),
            ("情绪崩溃", "冷静角"),
        ]
        
        # 将计划转换为文本进行检查
        plan_text = str(plan).lower()
        
        for diagnosis_keyword, forbidden_word in forbidden_combinations:
            if diagnosis_keyword in diagnosis and forbidden_word in plan_text:
                # V4.5.21 P0-3 修复日志
                logger.warning(
                    f"⚠️ P0-3 校验失败，已降级到 fallback 计划 | "
                    f"诊断：{diagnosis[:80]} | "
                    f"禁止组合：'{diagnosis_keyword}' × '{forbidden_word}' | "
                    f"建议人工审核"
                )
                return False
        
        logger.debug(f"P0-3 校验通过：诊断'{diagnosis[:50]}'与干预匹配")
        return True
    
    def _generate_fallback_plan(self, session_context: Optional[dict] = None) -> Dict[str, Any]:
        """
        V4.5.21 P0-3: 降级干预模板（当校验失败时使用）
        
        这是一个通用的、低风险的干预模板
        注意：严禁使用"忽视"、"冷静角"等禁止词！
        """
        context_activity = session_context.get("context", "") if session_context else ""
        activity = self._extract_activity_keyword(context_activity) if context_activity else "当前活动"
        
        # V4.5.21 P0-3 修复日志
        logger.warning(
            f"⚠️ P0-3 使用 fallback 计划 | "
            f"原因：诊断 - 干预校验失败或无匹配模板 | "
            f"建议人工审核此案例"
        )
        
        return {
            "phase_name": f"针对{activity}的'观察 + 支持'计划",
            "goal": f"通过观察和适度支持，帮助孩子更好地参与{activity}",
            "core_principle": "先观察理解，再提供适度支持。",
            "four_step_plan": {
                "core_idea": f"既然我们还在了解孩子的需求，那么我们的核心思路是：先观察记录行为模式，同时提供温和的支持，逐步找到最适合孩子的干预方式。",
                "our_plan": f"1) 记录行为发生的时间、情境和后果；2) 提供适度的环境调整；3) 观察孩子的反应；4) 根据观察结果调整策略。",
                "success_picture": f"在 1 周内，通过观察记录找到行为模式，为后续精准干预提供依据。",
                "first_step": f"今天，请开始记录：在什么时间、什么情境下出现行为，之后发生了什么。"
            },
            "observation_tool": f"记录 ABC：前因（Antecedent）、行为（Behavior）、后果（Consequence）。"
        }
    
    def _generate_rigidity_plan(self, session_context: Optional[dict] = None) -> Dict[str, Any]:
        """
        V4.10.2 P2 简化版：坚持同一性/刻板行为干预模板（通用框架）
        
        定位：评估工具为主，干预建议为辅助参考
        
        核心原则：
        - 坚持同一性不是"故意作对"，而是对可预测性的需求
        - 不是"打破仪式"，而是"逐步增加灵活性"
        - 关键词：预告、渐进变化、选择权、控制感
        """
        context_activity = session_context.get("context", "") if session_context else ""
        activity = self._extract_activity_keyword(context_activity) if context_activity else "当前活动"
        
        return {
            "phase_name": f"针对{activity}的干预方向（仅供参考）",
            "goal": f"帮助孩子逐步接受小的变化，提升灵活性",
            "core_principle": "坚持同一性反映了孩子对可预测性的需求。我们通过预告增加可预测性，通过渐进变化培养灵活性。",
            "four_step_plan": {
                "core_idea": f"针对'坚持固定模式'这一困难，干预核心是：通过提前预告增加可预测性，通过微小的、可控的变化逐步培养灵活性。",
                
                "our_plan": f"**参考练习类型：认知灵活性类练习**\n\n（示例：通过预告 + 微小变化，逐步培养灵活性）\n\n建议方向：\n• 变化发生前 5-10 分钟预告，使用视觉提示卡或计时器\n• 从极小的变化开始（如换一支笔的颜色），确保孩子能接受\n• 在可接受范围内给孩子选择权，增加控制感\n• 当孩子接受变化时，给予具体的积极反馈\n\n注：具体游戏设计建议咨询专业治疗师，根据孩子的具体情况个性化定制。",
                
                "success_picture": f"孩子能接受小的变化（如换路线、换餐具）而不崩溃，成功的标志是'能接受了'。",
                
                "first_step": f"您可以如何开始尝试？例如：选择一个孩子能接受的小变化（如换一种颜色的杯子），提前 5 分钟预告，观察并记录孩子的反应。"
            },
            "observation_tool": f"记录孩子接受了哪种小变化，以及反应如何（平静/轻微不适/崩溃）。重点是记录'成功接受'的时刻。",
            
            # V4.10.2 简化：通用衔接说明
            "scene_bridge": f"针对'{activity}'中孩子的困难，干预重点通常是'认知灵活性'能力的培养。"
        }
    
    # ========== V4.5.21 P0 修复结束 ==========
    
    # ========== V4.10.1 P1 新增：场景→干预映射 ==========
    
    def _classify_scene_type(self, session_context: Optional[dict] = None) -> str:
        """
        V4.10.1 P1 新增：场景分类
        
        根据情境和行为描述，识别场景类型，用于匹配精准的干预建议
        
        场景分类：
        1. joint_play - 共同游戏/加入游戏
        2. conversation_intro - 对话/介绍/轮流
        3. rules_rigidity - 规则理解/变化
        4. body_boundary - 身体边界/触碰
        5. emotion_recognition - 情绪识别/回应
        
        Returns:
            str: 场景类型
        """
        if not session_context:
            return "joint_play"  # 默认
        
        context = session_context.get("context", "")
        behavior = session_context.get("child_behavior", "")
        check_text = f"{context}{behavior}"
        
        # 1. 对话/介绍/轮流场景
        conversation_keywords = ["介绍", "名字", "说话", "告诉", "问", "回答", "轮流", "对话", "说完", "任务化"]
        if any(kw in check_text for kw in conversation_keywords):
            logger.info(f"📍 场景分类：conversation_intro (对话/介绍)")
            return "conversation_intro"
        
        # 2. 规则理解/变化场景
        rigidity_keywords = ["路线", "顺序", "排列", "必须", "一定", "不能变", "同样", "固定", "仪式"]
        if any(kw in check_text for kw in rigidity_keywords):
            logger.info(f"📍 场景分类：rules_rigidity (规则/变化)")
            return "rules_rigidity"
        
        # 3. 身体边界/触碰场景
        boundary_keywords = ["拥抱", "碰", "推", "拉", "靠", "近", "远", "轻重", "用力", "边界"]
        if any(kw in check_text for kw in boundary_keywords):
            logger.info(f"📍 场景分类：body_boundary (身体边界)")
            return "body_boundary"
        
        # 4. 情绪识别/回应场景
        emotion_keywords = ["表情", "高兴", "生气", "哭", "笑", "脸色", "不想", "拒绝", "皱眉"]
        if any(kw in check_text for kw in emotion_keywords):
            logger.info(f"📍 场景分类：emotion_recognition (情绪识别)")
            return "emotion_recognition"
        
        # 5. 共同游戏/加入游戏场景（默认）
        play_keywords = ["玩", "游戏", "加入", "一起", "参与", "规则", "抓人", "追逐"]
        if any(kw in check_text for kw in play_keywords):
            logger.info(f"📍 场景分类：joint_play (共同游戏)")
            return "joint_play"
        
        # 默认
        logger.info(f"📍 场景分类：joint_play (默认)")
        return "joint_play"
    
    def _get_scene_intervention(self, scene_type: str, session_context: Optional[dict] = None) -> Dict[str, Any]:
        """
        V4.10.2 P2 简化版：根据场景类型生成通用干预框架（仅供参考）
        
        定位：评估工具为主，干预建议为辅助参考
        核心：提供干预方向和原则，不提供具体游戏步骤
        
        Args:
            scene_type: 场景类型
            session_context: 会话上下文
        
        Returns:
            干预计划字典（简化版）
        """
        context_activity = session_context.get("context", "") if session_context else ""
        activity = self._extract_activity_keyword(context_activity) if context_activity else "当前情境"
        capability_gap = session_context.get("capability_gap", "") if session_context else ""
        
        # 1. 对话/介绍/轮流场景
        if scene_type == "conversation_intro":
            return {
                "phase_name": f"针对{activity}的干预方向（仅供参考）",
                "goal": f"帮助孩子在对话/介绍时学会观察对方反应",
                "core_principle": "将'说完话要看对方反应'转化为可练习的具体步骤",
                "four_step_plan": {
                    "core_idea": f"针对'介绍时忽略他人反应'这一困难，干预核心是：将抽象的社交状态（'对方是否在听'）转化为具体的、可练习的动作信号。",
                    
                    "our_plan": f"**参考练习类型：社交信号监测类练习**\n\n（示例：练习'说完→看脸→等反应'的完整链条）\n\n**建议方向：**\n1. 家庭模拟对话场景，练习'说完→看脸→等反应'的完整链条\n2. 使用视觉提示卡，提醒孩子观察对方反应\n3. 在真实场景前给予简短提示（如'说完名字要做什么？'）\n\n注：具体游戏设计建议咨询专业治疗师，根据孩子的具体情况个性化定制。",
                    
                    "success_picture": f"孩子能在对话/介绍后主动观察对方反应（点头、微笑、眼神接触），而不只是'说完了'。",
                    
                    "first_step": f"您可以如何开始尝试？例如：在家模拟简单对话场景，观察孩子'说完后是否会看对方'，记录成功时刻。"
                },
                "observation_tool": f"记录孩子有几次'说完后看了对方'，以及对方的反应。重点是发现孩子的进步模式。",
                
                # V4.10.2 简化：通用衔接说明
                "scene_bridge": f"针对'{activity}'中孩子的困难，干预重点通常是'社交信号监测'能力的培养。"
            }
        
        # 2. 规则理解/变化场景
        elif scene_type == "rules_rigidity":
            return {
                "phase_name": f"针对{activity}的干预方向（仅供参考）",
                "goal": f"帮助孩子逐步接受小的变化，提升灵活性",
                "core_principle": "通过预告增加可预测性，通过微小变化培养灵活性",
                "four_step_plan": {
                    "core_idea": f"针对'坚持固定模式'这一困难，干预核心是：通过提前预告增加可预测性，通过微小的、可控的变化逐步培养灵活性。",
                    
                    "our_plan": f"**参考练习类型：认知灵活性类练习**\n\n（示例：通过预告 + 微小变化，逐步培养灵活性）\n\n**建议方向：**\n1. 变化发生前 5-10 分钟预告，使用视觉提示卡或计时器\n2. 从极小的变化开始（如换一支笔的颜色），确保孩子能接受\n3. 在可接受范围内给孩子选择权，增加控制感\n4. 当孩子接受变化时，给予具体的积极反馈\n\n注：具体游戏设计建议咨询专业治疗师。",
                    
                    "success_picture": f"孩子能接受小的变化（如换路线、换餐具）而不崩溃，成功的标志是'能接受了'。",
                    
                    "first_step": f"您可以如何开始尝试？例如：选择一个孩子能接受的小变化（如换一种颜色的杯子），提前 5 分钟预告，观察并记录孩子的反应。"
                },
                "observation_tool": f"记录孩子接受了哪种小变化，以及反应如何（平静/轻微不适/崩溃）。",
                
                "scene_bridge": f"针对'{activity}'中孩子的困难，干预重点通常是'认知灵活性'能力的培养。"
            }
        
        # 3. 身体边界/触碰场景
        elif scene_type == "body_boundary":
            return {
                "phase_name": f"针对{activity}的干预方向（仅供参考）",
                "goal": f"帮助孩子理解并尊重自己和他人的身体边界",
                "core_principle": "将抽象的'身体边界'转化为可视化的具体概念",
                "four_step_plan": {
                    "core_idea": f"针对'身体边界感不足'这一困难，干预核心是：用视觉化和体验式的方法，让孩子理解每个人都有'舒适距离'。",
                    
                    "our_plan": f"**参考练习类型：身体感知类练习**\n\n（示例：用视觉化方法展示'身体边界'，如身体泡泡图）\n\n**建议方向：**\n1. 用视觉化方法（如画图）展示每个人的'身体泡泡'\n2. 通过体验式游戏（如呼啦圈）演示'舒适距离'\n3. 角色扮演练习'轻轻抱'vs'用力抱'的区别\n4. 建立非语言提醒信号（如手势）\n\n注：具体游戏设计建议咨询专业治疗师。",
                    
                    "success_picture": f"孩子能在拥抱/靠近前停顿一下，调整力度/距离，成功的标志是'会调整了'。",
                    
                    "first_step": f"您可以如何开始尝试？例如：和孩子一起画'身体泡泡'图，用玩偶练习'轻轻抱'。"
                },
                "observation_tool": f"记录孩子调整拥抱力度/距离的次数，以及对方的反应。",
                
                "scene_bridge": f"针对'{activity}'中孩子的困难，干预重点通常是'身体感知与调节'能力的培养。"
            }
        
        # 4. 情绪识别/回应场景
        elif scene_type == "emotion_recognition":
            return {
                "phase_name": f"针对{activity}的干预方向（仅供参考）",
                "goal": f"帮助孩子识别和理解他人的情绪信号",
                "core_principle": "将情绪识别转化为可练习的'侦探游戏'",
                "four_step_plan": {
                    "core_idea": f"针对'情绪识别困难'这一困难，干预核心是：用游戏化的方式，让孩子像侦探一样寻找'情绪线索'。",
                    
                    "our_plan": f"**参考练习类型：情绪识别类练习**\n\n（示例：用游戏化方式寻找'情绪线索'，如表情卡片、猜表情游戏）\n\n**建议方向：**\n1. 制作表情卡片（高兴/生气/难过/惊讶），每天认一认\n2. 看照片/视频片段，猜测人物感受\n3. 讨论什么情况下会有什么表情\n4. 在真实情境中引导孩子注意他人情绪\n\n注：具体游戏设计建议咨询专业治疗师。",
                    
                    "success_picture": f"孩子能识别基本表情，并在真实情境中注意到他人的情绪信号。",
                    
                    "first_step": f"您可以如何开始尝试？例如：找 3-5 张不同表情的照片（家人/动画角色），和孩子玩'猜表情'游戏。"
                },
                "observation_tool": f"记录孩子正确识别他人情绪的次数和情境。",
                
                "scene_bridge": f"针对'{activity}'中孩子的困难，干预重点通常是'非语言线索解读'能力的培养。"
            }
        
        # 5. 共同游戏/加入游戏场景（默认）
        else:  # joint_play
            return {
                "phase_name": f"针对{activity}的干预方向（仅供参考）",
                "goal": f"帮助孩子判断自己是否被同伴真正接纳",
                "core_principle": "将抽象的'我们是否在一起玩'转化为具体的身体动作信号",
                "four_step_plan": {
                    "core_idea": f"针对'社交信号监测弱'这一困难，干预核心是：将抽象的社交状态转化为具体的、可练习的动作信号。",
                    
                    "our_plan": f"**参考练习类型：社交信号监测类练习**\n\n（示例：建立'开始互动'的视觉或动作信号，如击掌、对暗号）\n\n**建议方向：**\n1. 设定专属'连接信号'，作为游戏开始的标志\n2. 在家演练：游戏前完成'连接信号'\n3. 过程中可随时暂停，用信号'重启'\n4. 真实场景前给予简短提示\n\n注：具体游戏设计建议咨询专业治疗师。",
                    
                    "success_picture": f"孩子能在游戏前主动寻求'连接信号'，或在不确定时观察对方是否在回应。",
                    
                    "first_step": f"您可以如何开始尝试？例如：和孩子一起发明一个'开始信号'（如击掌 + 说'开始！'），在家游戏前练习使用。"
                },
                "observation_tool": f"记录孩子主动确认'是否在一起玩'的次数，以及对方的回应。",
                
                "scene_bridge": f"针对'{activity}'中孩子的困难，干预重点通常是'社交信号监测'能力的培养。"
            }
    
    # ========== V4.10.1 P1 修复结束 ==========

    def generate_plan(self, matched_hypothesis_id: str, scenario_key: str, session_context: Optional[dict] = None) -> Optional[Dict[str, Any]]:
        """
        V4.10.1 P1 场景化干预：根据场景类型 + 功能判断生成精准干预计划
        
        核心修复：
        1. 优先使用场景分类匹配精准干预（V4.10.1 P1）
        2. 功能判断作为辅助校验（V4.5.21 P0）

        Args:
            matched_hypothesis_id: 匹配的假设 ID（如 "H1"）
            scenario_key: 场景键（如 "task_disengagement"）
            session_context: 会话上下文（包含 functional_judgment 等关键信息）

        Returns:
            干预计划字典，包含四步结构
        """
        # V4.10.1 P1 核心：场景分类驱动的精准干预
        scene_type = self._classify_scene_type(session_context)
        capability_gap = session_context.get("capability_gap", "") if session_context else ""
        functional_judgment = session_context.get("primary_hypothesis", "") if session_context else ""
        
        logger.info(f"V4.10.1 P1 场景分类：{scene_type}, capability_gap={capability_gap[:50] if capability_gap else 'N/A'}...")
        
        # === V4.10.1 P1 核心：根据场景类型生成精准干预 ===
        # 优先使用场景→干预映射（解决"诊断正确但开错药"问题）
        plan = self._get_scene_intervention(scene_type, session_context)
        
        # V4.5.21 P0 校验：确保诊断 - 干预匹配
        if plan and self._validate_diagnosis_intervention_match(functional_judgment, plan):
            logger.info(f"✅ V4.10.1 P1：场景化干预生成成功（{scene_type}）")
            return plan
        
        # 降级方案：使用原有逻辑
        logger.info("⚠️ V4.10.1 P1：场景化干预校验失败，降级到 V4.5.21 逻辑")
        return self._generate_fallback_plan(session_context)
    
    def generate_plan_with_narrative(self, matched_hypothesis_id: str, scenario_key: str, session_context: Optional[dict] = None, narrative: Optional[dict] = None) -> Optional[Dict[str, Any]]:
        """
        V4.5.21 P0 修复：基于功能判断生成干预计划 + 安全校验 + 输出前校验
        
        核心原则：干预计划必须与功能判断严格匹配！
        诊断是"提示依赖"→干预必须是"建立视觉/动作锚点"
        诊断是"逃避难度"→干预必须是"任务分解，降低起点"
        诊断是"寻求关注"→干预必须是"关注重定向"
        
        V4.5.21 P0 新增：
        - 安全优先检查（危险行为不能简单忽视）
        - 输出前校验（防止诊断 - 干预断裂）
        """
        # V4.5.21 P0-2 核心：安全优先检查
        if self._check_safety_priority(session_context):
            logger.warning("V4.5.21 P0-2: 检测到危险行为，启用安全优先模式")
            safety_plan = self._generate_safety_first_plan(session_context)
            return safety_plan
        
        # V4.5.3 核心修复：优先使用 functional_judgment 选择模板
        functional_judgment = session_context.get("primary_hypothesis", "") if session_context else ""
        
        logger.info(f"V4.5.21 生成计划：functional_judgment={functional_judgment[:80] if functional_judgment else 'N/A'}...")
        
        # === V4.5.3 核心：根据功能判断选择干预模板（严格匹配）===
        
        # 规则 1：提示依赖 → 建立视觉/动作锚点
        if functional_judgment and "提示依赖" in functional_judgment:
            logger.info("V4.5.3: 选择提示依赖干预模板（视觉/动作锚点）")
            plan = self._generate_prompt_dependence_plan(session_context)
            # V4.5.21 P0-3: 输出前校验
            if self._validate_diagnosis_intervention_match(functional_judgment, plan):
                return plan
            else:
                return self._generate_fallback_plan(session_context)
        
        # 规则 2：逃避难度 → 任务分解，降低起点
        elif functional_judgment and ("逃避" in functional_judgment and "难度" in functional_judgment):
            logger.info("V4.5.3: 选择逃避难度干预模板（任务分解）")
            plan = self._generate_escape_difficulty_plan(session_context)
            if self._validate_diagnosis_intervention_match(functional_judgment, plan):
                return plan
            else:
                return self._generate_fallback_plan(session_context)
        
        # 规则 3（V4.5.21 P0 修复）：注意力/任务坚持 → 环境调整 + 专注支持
        # 必须在"寻求关注"之前检查，避免"注意"关键词被错误匹配
        elif functional_judgment and any(kw in functional_judgment for kw in ["注意力", "专注", "分心", "任务坚持", "走神", "持续性注意"]):
            logger.info("V4.5.21 P0: 选择注意力支持干预模板（环境调整 + 专注支持）")
            plan = self._generate_attention_support_plan(session_context, functional_judgment)
            if self._validate_diagnosis_intervention_match(functional_judgment, plan):
                return plan
            else:
                return self._generate_fallback_plan(session_context)
        
        # 规则 4：寻求关注 → 关注重定向
        # 扩展匹配：包含"寻求关注"、"吸引注意"、"互动需求"等
        # V4.5.21 P0 修复：移除"注意"关键词，避免与注意力困难混淆
        elif functional_judgment and any(kw in functional_judgment for kw in ["关注", "寻求注意", "互动"]):
            logger.info("V4.5.3: 选择寻求关注干预模板（关注重定向）")
            plan = self._generate_attention_seeking_plan(session_context)
            if self._validate_diagnosis_intervention_match(functional_judgment, plan):
                return plan
            else:
                return self._generate_fallback_plan(session_context)
        
        # 规则 4.5（V4.5.20 P0 新增）：社交技能不足 → 直接教学 + 辅助演练
        elif functional_judgment and "社交" in functional_judgment:
            logger.info("V4.5.20 P0: 选择社交技能干预模板（直接教学）")
            plan = self._generate_social_skills_plan(session_context)
            if self._validate_diagnosis_intervention_match(functional_judgment, plan):
                return plan
            else:
                return self._generate_fallback_plan(session_context)
        
        # 规则 5：感觉逃避 → 环境调整 + 脱敏
        elif functional_judgment and any(kw in functional_judgment for kw in ["感觉逃避", "感觉敏感", "逃避不适", "听觉过敏", "触觉敏感"]):
            logger.info("V4.5.3: 选择感觉逃避干预模板（环境调整）")
            plan = self._generate_sensory_escape_plan(session_context)
            if self._validate_diagnosis_intervention_match(functional_judgment, plan):
                return plan
            else:
                return self._generate_fallback_plan(session_context)
        
        # 规则 6：自我刺激/自动强化 → 替代性感官输入
        elif functional_judgment and ("自我刺激" in functional_judgment or "自动" in functional_judgment):
            logger.info("V4.5.3: 选择自我刺激干预模板（替代性感官）")
            plan = self._generate_self_stimulation_plan(session_context)
            if self._validate_diagnosis_intervention_match(functional_judgment, plan):
                return plan
            else:
                return self._generate_fallback_plan(session_context)
        
        # 规则 7：过渡困难 → 预告 + 选择权
        elif functional_judgment and "过渡" in functional_judgment:
            logger.info("V4.5.3: 选择过渡困难干预模板（预告 + 选择）")
            plan = self._generate_transition_plan(session_context)
            if self._validate_diagnosis_intervention_match(functional_judgment, plan):
                return plan
            else:
                return self._generate_fallback_plan(session_context)
        
        # 规则 8（V4.5.21 P0 新增）：坚持同一性/刻板行为 → 预告 + 渐进变化
        elif functional_judgment and any(kw in functional_judgment for kw in ["坚持同一性", "刻板", "仪式", "固定模式", "排列", "排序", "固定"]):
            logger.info("V4.5.21 P0: 选择坚持同一性干预模板（预告 + 渐进变化）")
            plan = self._generate_rigidity_plan(session_context)
            if self._validate_diagnosis_intervention_match(functional_judgment, plan):
                return plan
            else:
                return self._generate_fallback_plan(session_context)
        
        # 降级方案：使用叙事性归因辅助选择（但不覆盖功能判断）
        # V4.5.3 修复：增加感觉逃避检查，避免错配到序列支持
        if narrative:
            primary_attribution = narrative.get("primary_attribution", "")
            logger.info(f"V4.5.3: 功能判断不明确，使用叙事归因辅助：{primary_attribution[:50]}...")
            
            # 优先检查感觉逃避（避免错配到序列支持）
            if any(kw in primary_attribution for kw in ["感觉", "听觉", "触觉", "噪音", "声音", "过敏"]):
                logger.info("V4.5.3: 选择感觉逃避干预模板（叙事归因辅助）")
                plan = self._generate_sensory_escape_plan(session_context)
                if self._validate_diagnosis_intervention_match(primary_attribution, plan):
                    return plan
            
            # 检查工作记忆/序列记忆
            elif "工作记忆" in primary_attribution or "序列记忆" in primary_attribution:
                logger.info("V4.5.3: 选择序列支持干预模板（辅助）")
                plan = self._generate_sequential_support_plan(session_context, primary_attribution)
                if self._validate_diagnosis_intervention_match(primary_attribution, plan):
                    return plan
            
            # 检查注意力
            elif "注意" in primary_attribution:
                logger.info("V4.5.3: 选择注意力支持干预模板（辅助）")
                plan = self._generate_attention_support_plan(session_context, primary_attribution)
                if self._validate_diagnosis_intervention_match(primary_attribution, plan):
                    return plan
        
        # 最终降级：基于功能标签
        logger.info("V4.5.3: 降级到基于功能标签的模板")
        plan = self.generate_plan(matched_hypothesis_id, scenario_key, session_context)
        
        # V4.5.21 P0-3: 输出前校验（降级方案也要校验）
        if functional_judgment and not self._validate_diagnosis_intervention_match(functional_judgment, plan):
            logger.warning("V4.5.21 P0-3: 降级方案校验失败，使用 fallback 计划")
            return self._generate_fallback_plan(session_context)
        
        return plan

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
    
    # ========== V4.5.20 P0: 社交技能干预模板 ==========
    
    def _generate_social_skills_plan(self, session_context: Optional[dict] = None) -> Dict[str, Any]:
        """
        V4.7.0 行动种子版：社交技能不足干预模板
        
        V4.7.0 修复：干预建议不能是万金油，要提供具体可操作的游戏
        核心策略：从一个关键信号开始，搭建能力桥梁
        """
        context_activity = session_context.get("context", "") if session_context else ""
        child_behavior = session_context.get("child_behavior", "") if session_context else ""
        capability_gap = session_context.get("capability_gap", "") if session_context else ""
        
        # V4.8.0 核心：基于具体场景生成"行动种子"游戏 + 深度原理解释
        if "以为" in child_behavior or "监测" in child_behavior or "介绍" in child_behavior or "参与" in child_behavior:
            # 抓人游戏/社交监测场景（核心问题：难以判断是否真的被接纳）
            game_name = "我们开始玩了吗信号练习"
            game_steps = "1. 设定专属信号：和孩子一起发明一个代表'我们开始一起玩啦'的秘密信号（如击掌、对暗号）\n2. 家庭演练：在家玩任何游戏前，必须先完成这个'连接信号'\n3. 过程中，您可以随时喊'暂停！'，所有人定格，再次用信号'重启'游戏\n4. 真实场景提示：去游乐场前说'今天试试看，如果想和小朋友玩，能不能先和他对个暗号？'"
            why_effective = "孩子目前难以在复杂的实时互动中判断'别人是否在和我玩'。这个练习绕开了复杂的社交解读，直接给她一个明确、可执行的外在规则，作为她内部'社交监测'能力的脚手架。这是构建更复杂社交能力的第一步。"
        elif "拥抱" in child_behavior or "轻重" in child_behavior:
            # 身体边界场景
            game_name = "轻柔的手练习游戏"
            game_steps = "1. 准备道具：毛绒玩具或气球\n2. 练习轻柔：让孩子轻轻摸玩具，说'这是轻柔的手'\n3. 对比练习：先用力抱（说'太紧了'），再轻柔抱（说'刚刚好'）"
            why_effective = "通过具体道具和对比练习，帮助孩子建立身体边界感的触觉记忆"
        elif "规则" in child_behavior or "僵化" in child_behavior or "重复" in child_behavior:
            # 规则理解场景
            game_name = "规则变变变游戏"
            game_steps = "1. 设定基础规则：如'队长只能当 1 分钟'\n2. 中途变规则：突然说'现在队长要跳着走'\n3. 引导适应：问孩子'规则变了，我们该怎么办？'"
            why_effective = "在安全环境中练习规则变化，培养认知灵活性"
        elif "轮流" in child_behavior or "等待" in child_behavior or "争当" in child_behavior:
            # 轮流等待场景
            game_name = "轮流当队长游戏"
            game_steps = "1. 准备计时器：设定 2 分钟\n2. 轮流规则：计时器响了就换人当队长\n3. 引导等待：在孩子等待时说'轮到你时我会提醒你'"
            why_effective = "用可视化的计时器帮助孩子理解'轮流'的抽象概念"
        else:
            # 通用场景
            game_name = "社交技能假装游戏"
            game_steps = "1. 模拟当前场景\n2. 练习恰当的社交技能\n3. 给予积极反馈"
            why_effective = "在安全环境中练习，逐步泛化到真实场景"
        
        return {
            "phase_name": "行动起点",
            "goal": f"从一个关键信号开始，搭建能力桥梁",
            "core_principle": "将抽象的社交状态转化为可观察、可练习的具体动作信号",
            "four_step_plan": {
                "core_idea": "基于孩子的能力缺口，本周可以尝试一个极简的练习，帮助学习关键社交信号。核心思路是：将抽象的社交状态转化为具体的、可练习的动作信号。",
                
                "our_plan": f"一个可尝试的游戏：**{game_name}**\n\n{game_steps}",
                
                "success_picture": "在 1 周内，孩子能在游戏前主动使用约定的信号（如主动击掌），成功的标志是孩子开始注意到'我们是否在一起玩'这个关键信号。",
                
                "first_step": f"今天，您就可以开始第一步：{game_steps.split(chr(10))[0]}。记住，第一次玩不重要，重要的是开始！"
            },
            "observation_tool": f"记录孩子今天是否能使用约定的信号（如击掌），以及在什么情境下使用的。重点是记录'成功时刻'。",
            
            # V4.7.0 新增：原理解释
            "why_effective": why_effective,
        }
    # ========== V4.5.20 P0 结束 ==========
