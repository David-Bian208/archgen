"""
干预规划器 V4.5.21 P0 Fix + V4.11 规则注册表集成
核心修复：根据 functional_judgment 选择完全不同的干预模板

V4.3 核心原则：
- 提示依赖 → 建立视觉/动作锚点，将外部提示内化
- 逃避难度 → 任务分解，降低起点，高频成功体验
- 严禁混用模板！

V4.11 新增：
- 临床规则注册表集成（可测试、可审计）
- 规则匹配辅助诊断
"""

import logging
import re
import html
from typing import Optional, Dict, Any, List

from app.knowledge import get_knowledge_base
from app.knowledge.clinical_rules_registry import get_clinical_rules_registry, RuleMatch

logger = logging.getLogger(__name__)


# ========== V6.0 P0: 能力缺口同义词库 ==========

# 能力缺口到干预游戏的映射
INTERVENTION_MAP = {
    "社交信号监测": "社交信号侦探游戏",
    "观点采择": "视角游戏：妈妈会看到什么",
    "工作记忆": "视觉提示卡游戏",
    "认知灵活性": "规则变变变游戏",
    "情绪识别": "情绪小侦探游戏",
    "共同调控": "我们开始玩了吗信号练习",
}

# 6 种能力缺口的同义词库（每类≥5 个同义词，覆盖自然语言描述）
CAPABILITY_SYNONYMS = {
    "社交信号监测": [
        # 标准术语
        "社交信号", "监测", "观察反应", "眼神接触",
        # 自然语言描述
        "眼神", "表情", "看不懂", "读不懂", "不会观察",
        "没注意到", "不看人", "忽略反应", "没眼色", "看不懂眼神",
        "不会看脸色", "不注意别人", "忽略别人"
    ],
    "观点采择": [
        # 标准术语
        "观点采择", "换位思考", "视角转换", "心理理论",
        # 自然语言描述
        "自我中心", "别人应该懂", "无法理解他人", "总觉得",
        "以为别人知道", "站别人角度", "理解别人想法", "不理解别人",
        "别人应该懂他", "不理解他人", "无法站在别人角度"
    ],
    "工作记忆": [
        # 标准术语
        "工作记忆", "记不住", "忘记步骤", "多步骤",
        # 自然语言描述
        "容易忘", "记性差", "需要反复提醒", "转头就忘",
        "记不住指令", "步骤乱了", "丢三落四", "记不住任务",
        "忘了老师说的", "多步骤记不住", "需要提醒"
    ],
    "认知灵活性": [
        # 标准术语
        "认知灵活性", "灵活性", "变化", "转换",
        # 自然语言描述
        "崩溃", "不接受", "固执", "必须一样",
        "不能变", "路线变了", "顺序变了", "刻板", "不接受变化",
        "必须走同样的路线", "变了就崩溃", "不能改变"
    ],
    "情绪识别": [
        # 标准术语
        "情绪识别", "表情", "面部表情", "情绪",
        # 自然语言描述
        "看不出", "分不清", "高兴生气", "什么表情",
        "不知道情绪", "读不懂脸色", "看不出高兴还是生气", "分不清表情",
        "不知道别人什么情绪", "看不懂表情"
    ],
    "共同调控": [
        # 标准术语
        "共同调控", "同步", "节奏匹配", "互动",
        # 自然语言描述
        "何时加入", "轮流", "一起玩的信号", "不知道怎么加入",
        "不会轮流", "插不进去", "没眼力见", "不会加入游戏",
        "不知道什么时候加入", "不会一起玩", "无法加入"
    ],
}

# ========== V6.0 P0 结束 ==========


class InterventionPlanner:
    """干预规划器 V4.11 - 规则注册表集成版"""

    def __init__(self):
        """初始化规划器"""
        self.knowledge_base = get_knowledge_base()
        self.rules_registry = get_clinical_rules_registry()
        logger.info("InterventionPlanner V4.11 初始化完成（规则注册表已加载）")
    
    # ========== V4.5.21 P0 核心修复 ==========
    
    def _analyze_with_rules(self, session_context: Optional[dict] = None) -> List[RuleMatch]:
        """
        V4.11 新增：使用临床规则注册表进行分析
        
        将行为描述和情境输入规则注册表，获取匹配的规则
        
        Args:
            session_context: 会话上下文
            
        Returns:
            List[RuleMatch]: 匹配的规则列表，按置信度排序
        """
        if not session_context:
            return []
        
        # 构建待分析文本
        child_behavior = session_context.get("child_behavior", "")
        context = session_context.get("context", "")
        antecedent = session_context.get("antecedent", "")
        consequence = session_context.get("consequence", "")
        
        analysis_text = f"{antecedent} {child_behavior} {context} {consequence}"
        
        # 使用规则注册表评估
        matches = self.rules_registry.evaluate(analysis_text)
        
        logger.info(f"规则分析：{len(matches)} 条匹配 | 文本：{analysis_text[:80]}...")
        return matches
    
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
            "strategy_details": f"1. **立即消除危险**：检查并移除环境中的危险因素（如锁好窗户、收好利器、安装防护栏）。\n2. **安全前提下最小化反应**：在确保环境安全后，对问题行为保持冷静，避免过度情绪反应强化行为。\n3. **教授安全替代行为**：教孩子用安全的方式满足相同需求（如用蹦床替代爬高）。\n4. **持续监控**：定期检查安全状况，确保防护措施有效。",
            "strategy_details_gamified": f"🦸 **安全小卫士**游戏\n\n**游戏设定：** 我们是'安全特工队'，保护孩子远离危险！\n\n**任务 1：危险大搜查**\n- 和孩子一起检查环境中的危险因素\n- 像侦探一样找出'危险物品'\n- 把它们放到'安全保险箱'（锁好或收好）\n\n**任务 2：安全替代**\n- 如果孩子喜欢爬高→准备蹦床或攀爬架\n- 如果孩子喜欢玩火→准备安全打火机玩具\n- 告诉孩子：'这个更安全、更好玩！'\n\n**任务 3：安全监控**\n- 每天检查一次环境安全\n- 确保所有防护措施有效\n- 零事故=任务成功！\n\n💡 记住：安全永远是第一位的！",
            "success_criteria": f"在 1 周内，危险行为频率下降 50% 以上，且未发生安全事故。",
            "parent_observation_task": f"记录每天的危险行为次数和是否有安全事故（应该为 0）。重点是确保'零事故'。",
            "why_effective": "这个干预有效的原因：通过消除环境危险因素，从源头降低安全风险。安全替代行为满足相同需求，减少危险行为冲动。持续监控确保防护措施有效，实现零事故目标。",
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
            "strategy_details": f"1) 记录行为发生的时间、情境和后果；2) 提供适度的环境调整；3) 观察孩子的反应；4) 根据观察结果调整策略。",
            "strategy_details_gamified": f"让我们和宝贝一起玩一个'行为侦探'游戏吧！\n\n1. **侦探任务**：记录行为发生的时间、情境和后果\n2. **环境调整**：像整理房间一样调整环境\n3. **观察反应**：看看孩子有什么变化\n4. **灵活调整**：根据观察结果调整策略\n\n记住，每一次观察都是一次有趣的发现！",
            "success_criteria": f"在 1 周内，通过观察记录找到行为模式，为后续精准干预提供依据。",
            "parent_observation_task": f"记录 ABC：前因（Antecedent）、行为（Behavior）、后果（Consequence）。每天花 2 分钟记录即可。",
            "why_effective": "这个干预有效的原因：通过观察记录找到行为模式，为精准干预提供依据。先理解再支持，避免盲目干预。行为学层面实现功能性评估，为后续干预奠定基础。",
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
            "strategy_details": f"1. **预告**：变化发生前 5-10 分钟告知孩子\n2. **微小变化**：从极小的变化开始（如换一支笔的颜色）\n3. **选择权**：在可接受范围内给孩子选择\n4. **积极反馈**：当孩子接受变化时给予具体表扬",
            "strategy_details_gamified": f"让我们和孩子一起玩'变化大冒险'游戏吧！\n\n1. **预告魔法**：提前 5-10 分钟用计时器或提示卡告诉孩子'马上要变化啦'\n2. **微小挑战**：从超级小的变化开始（如换一支笔的颜色），像闯关一样\n3. **选择权力**：给孩子两个选择'你想先换颜色还是先换位置？'\n4. **成功庆祝**：孩子接受变化时，热烈庆祝'你做到了！'\n\n记住，每一次小变化都是一次大冒险！",
            "success_criteria": f"在 1 周内，孩子能接受 3 次以上小的变化（如换路线、换餐具）而不崩溃。",
            "parent_observation_task": f"记录孩子接受了哪种小变化，以及反应如何（平静/轻微不适/崩溃）。重点是记录'成功接受'的时刻。",
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
    
    # ========== V6.0 Harness Engineering 新增方法 ==========
    
    def _extract_capability_keywords(self, capability_gap: str) -> list[str]:
        """
        V6.0 Harness Engineering：从能力缺口描述中提取关键词
        
        Args:
            capability_gap: 能力缺口描述
            
        Returns:
            关键词列表
        """
        if not capability_gap:
            return []
        
        # 常见能力关键词
        capability_keywords = {
            "观点采择": ["观点采择", "换位思考", "视角转换", "心理理论"],
            "工作记忆": ["工作记忆", "记不住", "忘记步骤", "多步骤"],
            "认知灵活性": ["认知灵活性", "灵活性", "变化", "转换"],
            "社交信号监测": ["社交信号", "监测", "观察反应", "眼神接触"],
            "情绪识别": ["情绪识别", "表情", "面部表情", "情绪"],
            "执行功能": ["执行功能", "计划", "组织", "抑制控制"],
            "共同调控": ["共同调控", "同步", "节奏匹配", "互动"],
            "沟通圈": ["沟通圈", "互动回合", "轮流", "对话"],
        }
        
        keywords = []
        for category, category_keywords in capability_keywords.items():
            for kw in category_keywords:
                if kw in capability_gap:
                    keywords.append(kw)
        
        logger.info(f"提取能力关键词：{keywords}")
        return keywords
    
    def _query_knowledge_base(self, capability_keywords: list[str], functional_judgment: str) -> Optional[Dict[str, Any]]:
        """
        V6.0 Harness Engineering：查询知识库获取标准化干预
        
        知识库匹配逻辑：
        1. 根据能力关键词匹配干预类型
        2. 根据功能判断调整干预重点
        3. 返回标准化干预模板
        
        Args:
            capability_keywords: 能力关键词列表
            functional_judgment: 功能判断
            
        Returns:
            标准化干预模板，未匹配则返回 None
        """
        if not capability_keywords:
            return None
        
        # 知识库干预模板（V6.0 新增）
        knowledge_interventions = {
            "观点采择": {
                "goal": "帮助孩子学会从他人视角看问题",
                "core_principle": "通过具体的视觉提示和角色扮演，让孩子体验'不同位置看到不同内容'",
                "four_step_plan": {
                    "core_idea": "观点采择能力是社交认知的核心。我们通过'视觉化'和'身体化'的练习，帮助孩子理解'你看到的≠我看到的'。",
                    "our_plan": "**推荐练习：视角游戏**\n\n1. 薯片盒游戏：把薯片盒洗干净，在里面放糖果。让孩子站在一个位置，家长站在另一个位置，问'妈妈会看到什么？'\n2. 逐步升级：从简单物品（杯子）到复杂场景（图画书）\n3. 录像回放：录下孩子的表现，和孩子一起看，暂停问'这时候妈妈看到了什么？'\n4. 真实场景：在游乐场、幼儿园等自然情境中练习",
                    "success_picture": "孩子能在换位思考任务中正确推断他人看到的内容，而不只是'我知道是糖'。",
                    "first_step": "今天就可以开始：找一个透明盒子，放一个孩子熟悉的物品，和孩子玩'妈妈会看到什么'的游戏。"
                },
                "observation_tool": "记录孩子有几次能正确推断他人视角，以及在什么情境下成功的。重点是发现'成功时刻'的模式。"
            },
            "工作记忆": {
                "goal": "帮助孩子记住多步骤任务的执行序列",
                "core_principle": "将抽象的任务序列转化为具体的视觉提示",
                "four_step_plan": {
                    "core_idea": "工作记忆短板不是'不认真'，而是'记不住多步骤'。我们用视觉提示卡替代'口头提醒'，减少认知负荷。",
                    "our_plan": "**推荐工具：视觉提示卡**\n\n1. 制作步骤卡：把任务分解为 3-5 个步骤，每个步骤画一张图\n2. 按顺序排列：用魔术贴或磁贴按顺序排列\n3. 执行时指卡：不口头提醒，只指下一张卡\n4. 逐步撤退：从全提示→部分提示→独立",
                    "success_picture": "孩子能在视觉提示下独立完成多步骤任务，而不需要成人反复口头提醒。",
                    "first_step": "选择一个孩子每天都会做的任务（如洗手、整理书包），制作 3-5 步的视觉提示卡。"
                },
                "observation_tool": "记录孩子在视觉提示下独立完成的步骤数，以及需要提示的次数。"
            },
            "认知灵活性": {
                "goal": "帮助孩子逐步接受小的变化",
                "core_principle": "通过预告增加可预测性，通过微小变化培养灵活性",
                "four_step_plan": {
                    "core_idea": "认知灵活性不是'不固执'，而是'能切换'。我们通过'预告 + 小变化'的组合，逐步提升孩子的适应能力。",
                    "our_plan": "**推荐练习：规则变变变**\n\n1. 提前预告：变化前 5-10 分钟告知\n2. 微小变化：从极小的变化开始（换一支笔的颜色）\n3. 提供选择权：在可接受范围内给孩子选择\n4. 成功强化：接受变化时给予具体反馈",
                    "success_picture": "孩子能接受小的变化而不崩溃，成功的标志是'能接受了'。",
                    "first_step": "选择一个孩子能接受的小变化（如换一种颜色的杯子），提前 5 分钟预告，观察并记录反应。"
                },
                "observation_tool": "记录孩子接受了哪种小变化，以及反应如何（平静/轻微不适/崩溃）。"
            },
            "社交信号监测": {
                "goal": "帮助孩子学会观察他人的社交信号",
                "core_principle": "将抽象的'社交状态'转化为具体的'可监测信号'",
                "four_step_plan": {
                    "core_idea": "社交信号监测弱不是'不理人'，而是'读不懂信号'。我们用'慢动作回放'和'暂停提问'，帮助孩子学会监测。",
                    "our_plan": "**推荐练习：社交信号侦探**\n\n1. 看动画片时暂停，问'他现在感觉如何？你怎么知道的？'\n2. 制作表情卡片，练习识别高兴/生气/难过/惊讶\n3. 真实场景：在游乐场观察其他小朋友的表情，猜测他们的感受\n4. 录像回放：录下互动场景，和孩子一起分析'这时候他是什么意思'",
                    "success_picture": "孩子能在互动中主动观察对方的表情、眼神、肢体动作，并适当回应。",
                    "first_step": "今晚看动画片时，尝试暂停 3 次，问孩子'他现在感觉如何？'"
                },
                "observation_tool": "记录孩子有几次主动观察对方反应，以及在什么情境下成功的。"
            },
        }
        
        # 匹配最相关的能力领域
        best_match = None
        best_score = 0
        
        for capability, intervention in knowledge_interventions.items():
            score = sum(1 for kw in capability_keywords if kw in capability)
            if score > best_score:
                best_score = score
                best_match = intervention
        
        if best_match and best_score > 0:
            logger.info(f"知识库匹配成功：{best_match['goal'][:50]}... (匹配度：{best_score})")
            return best_match
        
        logger.info(f"知识库未匹配，关键词：{capability_keywords}")
        return None
    
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
                "strategy_details": f"1. 家庭模拟对话场景，练习'说完→看脸→等反应'的完整链条\n2. 使用视觉提示卡，提醒孩子观察对方反应\n3. 在真实场景前给予简短提示",
                "strategy_details_gamified": f"让我们和孩子一起玩'说完看脸'游戏吧！\n\n1. **家庭剧场**：模拟对话场景，练习'说完→看脸→等反应'\n2. **视觉提示卡**：制作'眼睛看'提示卡，说完后提醒孩子\n3. **真实挑战**：去真实场景前，简短提示'说完名字要做什么？'\n\n记住，每一次眼神接触都是进步！",
                "success_criteria": f"在 1 周内，孩子能在对话/介绍后主动观察对方反应至少 3 次。",
                "parent_observation_task": f"记录孩子有几次'说完后看了对方'，以及对方的反应。重点是发现孩子的进步模式。",
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
                "strategy_details": f"1. 变化发生前 5-10 分钟预告，使用视觉提示卡或计时器\n2. 从极小的变化开始（如换一支笔的颜色）\n3. 在可接受范围内给孩子选择权\n4. 当孩子接受变化时，给予具体的积极反馈",
                "strategy_details_gamified": f"让我们和孩子一起玩'变化大冒险'游戏吧！\n\n1. **预告魔法**：提前 5-10 分钟用计时器告诉孩子'马上要变化啦'\n2. **微小挑战**：从超级小的变化开始（如换笔的颜色），像闯关一样\n3. **选择权力**：给孩子两个选择'你想先换颜色还是先换位置？'\n4. **成功庆祝**：孩子接受变化时，热烈庆祝'你做到了！'\n\n记住，每一次小变化都是一次大冒险！",
                "success_criteria": f"在 1 周内，孩子能接受 3 次以上小的变化而不崩溃。",
                "parent_observation_task": f"记录孩子接受了哪种小变化，以及反应如何（平静/轻微不适/崩溃）。",
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
                "strategy_details": f"1. 用视觉化方法（如画图）展示每个人的'身体泡泡'\n2. 通过体验式游戏（如呼啦圈）演示'舒适距离'\n3. 角色扮演练习'轻轻抱'vs'用力抱'的区别\n4. 建立非语言提醒信号（如手势）",
                "strategy_details_gamified": f"让我们和孩子一起玩'身体泡泡'游戏吧！\n\n1. **画泡泡**：和孩子一起画每个人的'身体泡泡'，解释这是舒适距离\n2. **呼啦圈体验**：用呼啦圈演示'舒适距离'，让孩子感受\n3. **玩偶练习**：用玩偶练习'轻轻抱'vs'用力抱'的区别\n4. **秘密手势**：建立非语言提醒信号（如手势）\n\n记住，尊重身体边界是重要的社交技能！",
                "success_criteria": f"在 1 周内，孩子能在拥抱/靠近前停顿调整至少 3 次。",
                "parent_observation_task": f"记录孩子调整拥抱力度/距离的次数，以及对方的反应。",
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
                "strategy_details": f"1. 制作表情卡片（高兴/生气/难过/惊讶），每天认一认\n2. 看照片/视频片段，猜测人物感受\n3. 讨论什么情况下会有什么表情\n4. 在真实情境中引导孩子注意他人情绪",
                "strategy_details_gamified": f"让我们和孩子一起玩'情绪小侦探'游戏吧！\n\n1. **表情卡片**：制作高兴/生气/难过/惊讶卡片，每天玩'认一认'\n2. **照片猜谜**：看照片/视频片段，暂停问'他现在感觉如何？'\n3. **情境讨论**：讨论什么情况下会有什么表情\n4. **真实挑战**：在真实情境中引导孩子注意他人情绪\n\n记住，每一次正确识别都是进步！",
                "success_criteria": f"在 1 周内，孩子能正确识别至少 5 种基本表情。",
                "parent_observation_task": f"记录孩子正确识别他人情绪的次数和情境。",
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
                "strategy_details": f"1. 设定专属'连接信号'，作为游戏开始的标志\n2. 在家演练：游戏前完成'连接信号'\n3. 过程中可随时暂停，用信号'重启'\n4. 真实场景前给予简短提示",
                "strategy_details_gamified": f"让我们和孩子一起玩'连接信号'游戏吧！\n\n1. **发明信号**：和孩子一起发明专属'开始信号'（如击掌 + 说'开始！'）\n2. **家庭演练**：在家玩任何游戏前，必须先完成这个'连接信号'\n3. **暂停重启**：游戏过程中可随时喊'暂停！'，用信号'重启'\n4. **真实挑战**：去游乐场前提示'今天试试看，能不能和小朋友对暗号？'\n\n记住，每一次主动寻求信号都是进步！",
                "success_criteria": f"在 1 周内，孩子能在游戏前主动使用约定的连接信号至少 3 次。",
                "parent_observation_task": f"记录孩子主动确认'是否在一起玩'的次数，以及对方的回应。",
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
        V6.0 Harness Engineering：三段式干预生成逻辑
        
        核心逻辑：
        1. 知识库匹配（能回答的）→ 标准化干预
        2. 场景映射（不能回答的提示）→ 场景化干预
        3. 大模型推理（知识库没有的）→ 通用框架
        
        Args:
            matched_hypothesis_id: 匹配的假设 ID
            scenario_key: 场景键
            session_context: 会话上下文

        Returns:
            干预计划字典
        """
        # === 阶段 1：知识库匹配（能回答的）===
        capability_gap = session_context.get("capability_gap", "") if session_context else ""
        functional_judgment = session_context.get("primary_hypothesis", "") if session_context else ""
        
        logger.info(f"V6.0 Harness Engineering：开始三段式干预生成")
        
        # 尝试从知识库获取标准化干预
        if capability_gap and functional_judgment:
            # 提取能力缺口关键词
            capability_keywords = self._extract_capability_keywords(capability_gap)
            
            # 查询知识库
            knowledge_intervention = self._query_knowledge_base(capability_keywords, functional_judgment)
            
            if knowledge_intervention:
                logger.info(f"✅ 阶段 1：知识库匹配成功，返回标准化干预")
                return knowledge_intervention
        
        # === 阶段 2：场景映射（不能回答的提示）===
        scene_type = self._classify_scene_type(session_context)
        logger.info(f"阶段 2：场景分类={scene_type}")
        
        scene_intervention = self._get_scene_intervention(scene_type, session_context)
        
        if scene_intervention and self._validate_diagnosis_intervention_match(functional_judgment, scene_intervention):
            logger.info(f"✅ 阶段 2：场景映射成功，返回场景化干预")
            return scene_intervention
        
        # === 阶段 3：大模型推理（知识库没有的）===
        logger.info(f"⚠️ 阶段 3：知识库和场景映射都未匹配，使用通用框架")
        return self._generate_fallback_plan(session_context)
    
    def generate_plan_with_narrative(self, matched_hypothesis_id: str, scenario_key: str, session_context: Optional[dict] = None, narrative: Optional[dict] = None) -> Optional[Dict[str, Any]]:
        """
        V4.5.21 P0 修复 + V4.11 规则注册表集成
        
        核心原则：干预计划必须与功能判断严格匹配！
        诊断是"提示依赖"→干预必须是"建立视觉/动作锚点"
        诊断是"逃避难度"→干预必须是"任务分解，降低起点"
        诊断是"寻求关注"→干预必须是"关注重定向"
        
        V4.5.21 P0 新增：
        - 安全优先检查（危险行为不能简单忽视）
        - 输出前校验（防止诊断 - 干预断裂）
        
        V4.11 新增：
        - 规则注册表分析（辅助诊断）
        - 规则匹配日志
        """
        # V4.11 新增：规则注册表分析
        rule_matches = self._analyze_with_rules(session_context)
        if rule_matches:
            logger.info(f"V4.11 规则分析：Top 匹配 = {[(m.rule.name, m.confidence) for m in rule_matches[:3]]}")
        
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
            "strategy_details": f"1. 与孩子共同为{activity}中的一个标志性动作命名并设计夸张有趣的练习。2. 在自然情境中，当该动作出现时，使用'密语'提示。3. 孩子做出后，给予即时、夸张的积极反馈。",
            "strategy_details_gamified": f"🎯 **锚点大冒险**游戏\n\n**游戏设定：** 我们是'锚点特工队'，每个动作都有一个专属锚点信号！\n\n**任务 1：发明锚点**\n- 和孩子一起设计专属锚点动作（如：摸耳朵=开始做操）\n- 给锚点起个酷酷的名字（如'启动密码'）\n\n**任务 2：锚点练习**\n- 在家玩'锚点反应'游戏：你说锚点，孩子做动作\n- 计时挑战：看谁反应最快！\n\n**任务 3：真实挑战**\n- 去幼儿园前提示：'今天试试用锚点密码，看能不能跟上做操？'\n- 回来后庆祝：'今天用锚点密码跟上了几次？'\n\n💡 记住：锚点越酷，孩子越爱玩！",
            "success_criteria": f"连续 3 日，在自然情境的口头'密语'提示下，3 秒内独立做出正确动作的成功率 ≥ 80%。",
            "parent_observation_task": f"记录：日期、提示后是否成功（√/×）、反应速度（快/中/慢）。",
            "why_effective": "这个干预有效的原因：通过建立锚点信号到动作的条件反射，将外部提示内化为自动化反应。游戏化设计提升参与动机，减少抗拒感。脑科学层面建立神经通路，行为学层面实现刺激控制。",
            "four_step_plan": {
                "core_idea": f"既然挑战的核心是孩子对'实时视觉提示'的依赖，那么我们的核心思路就是：帮助他将需要紧盯的'外部提示'，逐步转化为自己能随时调用的'内部提示'，从而减少{activity}中的任务中断。",
                
                "our_plan": f"我们可以从{activity}的动作序列中，选择一个有代表性的步骤，将它转化为您和孩子之间的趣味'暗号'。通过精心设计的小游戏，在轻松的氛围中反复练习，帮助孩子建立'暗号'与'行动'之间的快速链接。",
                
                "success_picture": f"在 3 天内，当您使用这个'暗号'提示时，孩子能在 3 秒内做出正确反应，且尝试的成功率能够稳定达到 80% 以上。",
                
                "first_step": f"今天，您就可以和孩子共创一个趣味'动作暗号'（如'大鹏展翅'），并开启第一次'闯关'游戏。记住，第一次玩不重要，重要的是开始！"
            },
            "observation_tool": f"记录是为了捕捉进步的信号。您只需：在日历上，在'{activity}游戏'的日期旁，根据孩子的反应速度画上 ✅（快）或 🔄（慢）。这就足够了！",
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
            "strategy_details": f"1. 将{activity}任务分解为最小可执行步骤。2. 使用'高概率要求序列'（先提 3 个简单要求，再提目标要求）。3. 在孩子完成每个小步骤后给予即时积极反馈。",
            "strategy_details_gamified": f"🎮 **成功阶梯挑战**游戏\n\n**游戏设定：** 我们一起建造'成功金字塔'！\n\n**关卡 1：迷你启动**\n- 把任务切成'3 分钟小块'（如'只写一个字'）\n- 玩'火箭倒计时发射'：3-2-1，发射！\n\n**关卡 2：连胜挑战**\n- 完成 1 个小块得 1 颗星\n- 集齐 3 颗星召唤'成功巨龙'！\n\n**关卡 3：时间延长**\n- 从 3 分钟升级到 5 分钟\n- 每延长 1 分钟都是大胜利！\n\n💡 记住：完成比完美重要，开始比结果重要！",
            "success_criteria": f"连续 3 日，每日至少有 3 次主动配合{activity}任务的行为，且每次持续时间达到 5 分钟以上。",
            "parent_observation_task": f"记录：{activity}任务名称、孩子反应（配合/拒绝）、使用的支持策略、持续时间。",
            "why_effective": "这个干预有效的原因：通过任务分解降低认知负荷，让孩子体验我能做到的成功感。高频成功体验激活大脑奖励系统，逐步建立开始等于快乐的神经链接，减少逃避行为.",
            "four_step_plan": {
                "core_idea": f"既然挑战的核心是{activity}对孩子来说太难了，那么我们的核心思路就是：将大任务切成'微步骤'，让起点变得足够简单，简单到孩子无法拒绝，从而建立'开始就好'的成功体验。",
                
                "our_plan": f"我们可以从{activity}任务中，选择一个'最小可执行步骤'（如'只写一个字'、'只做一道题'），将它设计成一个有趣的'启动游戏'。关键是让孩子体验'我做到了'的成就感，而不是追求完美。",
                
                "success_picture": f"在 3 天内，孩子能主动开始{activity}任务至少 3 次，且每次持续时间达到 3-5 分钟以上，抵触情绪明显减少。",
                
                "first_step": f"今天，您就可以尝试将{activity}任务切成一个'3 分钟就能完成的小块'，和孩子一起玩'火箭倒计时发射'游戏。记住，完成比完美重要，开始比结果重要！"
            },
            "observation_tool": f"记录是为了看见改变。您只需：在日历上，在'{activity}启动'的日期旁，记录孩子主动开始的次数和持续时间（如'3 次，5 分钟'）。这就足够了！",
        }

    def _generate_attention_seeking_plan(self, session_context: Optional[dict] = None) -> Dict[str, Any]:
        """V4.3 Hotfix 寻求关注干预模板"""
        context_activity = session_context.get("context", "") if session_context else ""
        activity = self._extract_activity_keyword(context_activity)
        
        return {
            "phase_name": f"针对{activity}的'关注重定向'计划",
            "goal": f"将关注从{activity}中的问题行为转移到积极行为，建立正向互动循环。",
            "core_principle": "减少对问题行为的关注，增加对配合行为的积极关注，建立正向互动循环。",
            "strategy_details": f"当{activity}中的问题行为发生时，保持冷静、中性的态度，用最少的语言完成任务。当配合发生时，立即给予热情、具体的积极关注。",
            "strategy_details_gamified": f"🕵️ **关注侦探**游戏\n\n**游戏设定：** 我们是'关注侦探'，专门寻找'好行为线索'！\n\n**任务 1：发现线索**\n- 当孩子配合时，立即说'我发现了！'\n- 具体描述：'你刚才主动收拾玩具，太棒了！'\n\n**任务 2：线索奖励**\n- 每个'好行为线索'得 1 枚侦探徽章\n- 集齐 5 枚徽章晋升'超级侦探'\n\n**任务 3：问题行为冷处理**\n- 问题行为发生时，保持'侦探冷静脸'\n- 用最少的语言处理，不给予情绪关注\n\n💡 记住：好行为=热烈关注，问题行为=冷静处理！",
            "success_criteria": f"在 3 天内，配合行为频率增加 40% 以上，问题行为频率减少 30% 以上。",
            "parent_observation_task": f"记录是为了发现模式。您只需：在日历上，记录每天配合行为和问题行为的次数，观察它们的变化趋势。",
            "why_effective": "这个干预有效的原因：通过差异化关注，让孩子发现好行为比问题行为能获得更多更好的关注。行为学层面实现关注重定向，脑科学层面重塑奖励系统。",
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
            "strategy_details": "我们可以从调整环境开始（如降低噪音、减少视觉干扰），同时为孩子提供感觉工具（如降噪耳塞），然后逐步延长在环境中的时间。",
            "strategy_details_gamified": f"🌈 **感觉探险家**游戏\n\n**游戏设定：** 我们是'感觉探险家'，去陌生环境探险！\n\n**装备 1：感觉工具包**\n- 降噪耳塞（对付嘈杂声音）\n- 太阳镜（对付强光）\n- 安抚玩具（感觉不安时使用）\n\n**任务 2：时间挑战**\n- 第 1 天：在环境中待 5 分钟\n- 第 2 天：延长到 10 分钟\n- 第 3 天：挑战 15 分钟！\n\n**任务 3：成功庆祝**\n- 每完成一个时间挑战，获得'感觉勇士'徽章\n- 集齐 3 枚徽章晋升'感觉探险家'！\n\n💡 记住：慢慢来，每一次尝试都是勇气！",
            "success_criteria": "在 1 周内，孩子能在调整后的环境中停留时间延长 50% 以上，抵触情绪明显减少。",
            "parent_observation_task": "记录是为了看见环境因素的影响。您只需：在日历上，记录每天{activity}的环境特点（安静/嘈杂）和孩子的反应（积极/中性/消极）。",
            "why_effective": "这个干预有效的原因：通过环境调整减少感觉超载，让孩子在可承受的范围内逐步建立感觉耐受性。系统脱敏原理降低焦虑，感觉工具提供安全感.",
            "four_step_plan": {
                "core_idea": "既然挑战的核心是环境刺激超出了孩子的感觉处理能力，那么我们的核心思路就是：先调整环境减少刺激，再逐步帮助孩子建立感觉耐受性。",
                "our_plan": "我们可以从调整环境开始（如降低噪音、减少视觉干扰），同时为孩子提供感觉工具（如降噪耳塞），然后逐步延长在环境中的时间。",
                "success_picture": "在 1 周内，孩子能在调整后的环境中停留时间延长 50% 以上，抵触情绪明显减少。",
                "first_step": "今天，您就可以尝试为孩子准备降噪耳塞，并在去环境前进行预告，让孩子有心理准备。"
            },
            "observation_tool": f"记录是为了看见环境因素的影响。您只需：在日历上，记录每天{activity}的环境特点（安静/嘈杂）和孩子的反应（积极/中性/消极）。",
        }
    
    def _generate_self_stimulation_plan(self, session_context: Optional[dict] = None) -> Dict[str, Any]:
        """V4.5.3 自我刺激干预模板"""
        context_activity = session_context.get("context", "") if session_context else ""
        activity = self._extract_activity_keyword(context_activity)
        
        return {
            "phase_name": f"针对{activity}的'替代性感官'计划",
            "goal": f"为孩子提供适当的替代性感官输入，减少自我刺激行为。",
            "core_principle": "通过提供功能等价的替代性感官活动，满足孩子的感官需求，同时减少不适当的自我刺激。",
            "strategy_details": "我们可以观察孩子从自我刺激中获得什么感官输入，然后设计类似的但更适当的活动（如提供压力球替代晃手）。",
            "strategy_details_gamified": f"🎾 **替代玩具总动员**游戏\n\n**游戏设定：** 我们是'玩具特工队'，找到最酷的替代玩具！\n\n**任务 1：侦探观察**\n- 观察孩子晃手时，手在做什么动作？\n- 是喜欢'晃动感'还是'视觉刺激'？\n\n**任务 2：玩具匹配**\n- 如果喜欢晃动感→提供压力球、握力器\n- 如果喜欢视觉刺激→提供万花筒、发光陀螺\n- 如果喜欢触觉刺激→提供纹理球、安抚巾\n\n**任务 3：温柔替换**\n- 孩子开始晃手时，温和地递上替代玩具\n- 不说'不要晃手'，而说'试试这个超酷的玩具！'\n\n💡 记住：不是'制止'，而是'提供更好的选择'！",
            "success_criteria": "在 1 周内，自我刺激行为频率减少 40%，替代活动使用频率增加。",
            "parent_observation_task": "记录是为了找到最适合的替代玩具。您只需：在日历上，记录每天自我刺激次数和替代玩具使用次数。",
            "why_effective": "这个干预有效的原因：通过提供功能等价的替代活动，满足孩子的感官需求。不是强行制止，而是提供更好的选择，降低抗拒感，逐步建立新的感官习惯.",
            "four_step_plan": {
                "core_idea": "既然挑战的核心是孩子需要特定的感官输入，那么我们的核心思路就是：提供功能等价但更适当的替代活动，满足感官需求。",
                "our_plan": "我们可以观察孩子从自我刺激中获得什么感官输入，然后设计类似的但更适当的活动（如提供压力球替代晃手）。",
                "success_picture": "在 1 周内，自我刺激行为频率减少 40%，替代活动使用频率增加。",
                "first_step": "今天，您就可以尝试提供一个替代性感官玩具（如压力球、纹理球），在孩子开始自我刺激时温和地递给他。"
            },
            "observation_tool": "记录是为了找到最适合的替代玩具。您只需：在日历上，记录每天自我刺激次数和替代玩具使用次数。",
        }
    
    def _generate_transition_plan(self, session_context: Optional[dict] = None) -> Dict[str, Any]:
        """V4.5.3 过渡困难干预模板"""
        context_activity = session_context.get("context", "") if session_context else ""
        activity = self._extract_activity_keyword(context_activity)
        
        return {
            "phase_name": f"针对{activity}的'预告 + 选择'计划",
            "goal": f"通过预告和提供选择权，帮助孩子顺利过渡到{activity}。",
            "core_principle": "通过提前预告和提供有限选择，增加孩子的控制感和可预测性，减少过渡抵触。",
            "strategy_details": "我们可以在活动转换前 5-10 分钟开始预告，使用视觉提示卡或计时器，并提供有限选择（如'先穿衣还是先刷牙'）。",
            "strategy_details_gamified": f"⏰ **过渡小能手**游戏\n\n**游戏设定：** 我们是'时间魔法师'，学会预测变化！\n\n**魔法 1:5 分钟预告**\n- 使用计时器或提示卡：'还有 5 分钟就要变化啦！'\n- 让孩子有心理准备，不是突然打断\n\n**魔法 2：选择权力**\n- 提供两个选择：'你想先穿衣还是先刷牙？'\n- 增加控制感，减少抵触情绪\n\n**魔法 3：过渡仪式**\n- 创建一个'结束仪式'（如说'拜拜，游戏时间！'）\n- 帮助孩子从当前活动切换到下一个活动\n\n💡 记住：预告=尊重，选择=控制感！",
            "success_criteria": "在 1 周内，活动转换时的抵触行为减少 50%，配合度明显提高。",
            "parent_observation_task": "记录是为了看见预告和选择的效果。您只需：在日历上，记录每天活动转换时孩子的反应（配合/轻微抵触/强烈抵触）。",
            "why_effective": "这个干预有效的原因：通过预告增加可预测性，降低突然变化带来的焦虑；通过提供选择权增加控制感，减少抵触情绪。孩子从被动接受变为主动参与。",
            "four_step_plan": {
                "core_idea": "既然挑战的核心是活动转换的不可预测性，那么我们的核心思路就是：通过预告增加可预测性，通过选择权增加控制感。",
                "our_plan": "我们可以在活动转换前 5-10 分钟开始预告，使用视觉提示卡或计时器，并提供有限选择（如'先穿衣还是先刷牙'）。",
                "success_picture": "在 1 周内，活动转换时的抵触行为减少 50%，配合度明显提高。",
                "first_step": "今天，您就可以尝试使用'5 分钟预告'：在活动转换前 5 分钟告诉孩子，并使用计时器帮助他理解时间。"
            },
            "observation_tool": "记录是为了看见预告和选择的效果。您只需：在日历上，记录每天活动转换时孩子的反应（配合/轻微抵触/强烈抵触）。",
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
            "strategy_details": f"我们可以为{activity}创建一个简单的'动作步骤图'（3-4 个关键步骤的图片或图标），并在活动前和孩子一起复习。同时选择一个'锚点动作'作为序列的起始点。",
            "strategy_details_gamified": f"🗺️ **序列大闯关**游戏\n\n**游戏设定：** 我们是'闯关小能手'，按照地图完成任务！\n\n**道具 1：动作步骤图**\n- 用手机拍照或绘画制作步骤图\n- 3-4 个关键步骤（如：1. 伸手 2. 握紧 3. 拉起）\n- 贴在孩子能看到的地方\n\n**道具 2：锚点动作**\n- 选择一个标志性动作作为'开始信号'\n- 如'准备 - 开始！'的手势\n- 孩子看到这个信号就开始行动\n\n**闯关挑战：**\n- 第 1 关：看着步骤图完成\n- 第 2 关：不看图完成 50%\n- 第 3 关：独立 100% 完成！\n\n💡 记住：视觉化=降低难度，锚点=启动信号！",
            "success_criteria": f"在 3 天内，孩子能在最少提示下独立完成{activity}的 80% 以上步骤，且'锚点动作'的启动时间缩短至 3 秒内。",
            "parent_observation_task": f"记录是为了追踪序列记忆的进步。您只需：在日历上，记录孩子独立完成的步骤数（如'3/5 步'）和需要的提示类型（视觉/语言/身体）。",
            "why_effective": "这个干预有效的原因：通过视觉化步骤图降低工作记忆负荷，让孩子不需要记住所有步骤。锚点动作作为启动信号，建立信号到行动的自动化链接.",
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
            "strategy_details": f"我们可以使用'专注 - 休息'循环：先设定一个很短的专注时间（如 30 秒），用计时器或音乐作为信号，完成后给予即时强化（如击掌、贴纸），然后逐渐延长时间。",
            "strategy_details_gamified": f"⏱️ **专注力挑战**游戏\n\n**游戏设定：** 我们是'时间勇士'，挑战专注力极限！\n\n**关卡 1:30 秒挑战**\n- 设定 30 秒计时器\n- 和孩子一起专注{activity}\n- 时间到了就热烈庆祝'耶！我们做到了！'\n\n**关卡 2：连胜挑战**\n- 连续完成 3 次 30 秒挑战\n- 获得'专注勇士'徽章\n\n**关卡 3：时间升级**\n- 从 30 秒升级到 1 分钟\n- 再升级到 2 分钟！\n- 每延长 10 秒都是大胜利！\n\n💡 记住：短时间 + 高频庆祝 = 专注力提升！",
            "success_criteria": f"在 3 天内，孩子的专注时间从 30 秒延长至 2 分钟以上，且分心行为减少 40% 以上。",
            "parent_observation_task": f"记录是为了看见专注力的进步。您只需：在日历上，记录孩子每次专注的时长（秒）和分心的次数。",
            "why_effective": "这个干预有效的原因：通过短时间专注 + 即时强化，激活大脑奖励系统。逐步延长时间建立我能专注的自我效能感，降低分心冲动。行为学层面实现正向强化循环.",
            "four_step_plan": {
                "core_idea": f"既然挑战的核心是孩子在干扰环境下难以维持持续性注意力，那么我们的核心思路就是：将{activity}分成更小的时间段（如 30 秒 -2 分钟），每段都有明确的开始和结束信号（如计时器），并在每段结束后给予即时强化，帮助孩子逐步延长专注时间。",
                "our_plan": f"我们可以使用'专注 - 休息'循环：先设定一个很短的专注时间（如 30 秒），用计时器或音乐作为信号，完成后给予即时强化（如击掌、贴纸），然后逐渐延长时间。",
                "success_picture": f"在 3 天内，孩子的专注时间从 30 秒延长至 2 分钟以上，且分心行为减少 40% 以上。",
                "first_step": f"今天，您就可以尝试'30 秒挑战'：设定一个 30 秒的计时器，和孩子一起专注{activity}，时间到了就给予热烈的庆祝，然后逐渐增加时间。"
            },
            "observation_tool": f"记录是为了看见专注力的进步。您只需：在日历上，记录孩子每次专注的时长（秒）和分心的次数。",
        }
    
    # ========== V4.5.20 P0: 社交技能干预模板 ==========
    
    def _match_capability_keywords(self, capability_gap: str) -> Optional[str]:
        """
        V6.0 P0 新增：关键词扩展匹配
        
        使用同义词库匹配能力缺口，支持自然语言描述
        
        Args:
            capability_gap: 能力缺口描述（支持自然语言）
            
        Returns:
            干预游戏名称，如果无匹配则返回 None
        """
        for capability, synonyms in CAPABILITY_SYNONYMS.items():
            if any(syn in capability_gap for syn in synonyms):
                return INTERVENTION_MAP[capability]
        return None
    
    def _match_social_scene(self, child_behavior: str) -> tuple[str, str, str]:
        """
        V6.0 新增：场景匹配辅助方法（降级用）
        
        当 capability_gap 不明确时，基于 child_behavior 进行场景匹配
        
        Args:
            child_behavior: 孩子行为描述
            
        Returns:
            (game_name, game_steps, why_effective) 元组
        """
        # 身体边界
        if "拥抱" in child_behavior or "轻重" in child_behavior:
            game_name = "轻柔的手练习游戏"
            game_steps = "1. 准备道具：毛绒玩具或气球\n2. 练习轻柔：让孩子轻轻摸玩具，说'这是轻柔的手'\n3. 对比练习：先用力抱（说'太紧了'），再轻柔抱（说'刚刚好'）"
            why_effective = "通过具体道具和对比练习，帮助孩子建立身体边界感的触觉记忆"
        
        # 规则理解
        elif "规则" in child_behavior or "僵化" in child_behavior or "重复" in child_behavior:
            game_name = "规则变变变游戏"
            game_steps = "1. 设定基础规则：如'队长只能当 1 分钟'\n2. 中途变规则：突然说'现在队长要跳着走'\n3. 引导适应：问孩子'规则变了，我们该怎么办？'"
            why_effective = "在安全环境中练习规则变化，培养认知灵活性"
        
        # 介绍/任务化
        elif "介绍" in child_behavior or "任务化" in child_behavior:
            game_name = "说完看脸游戏"
            game_steps = "1. 家庭模拟对话场景\n2. 练习'说完→看脸→等反应'的完整链条\n3. 制作'眼睛看'提示卡，说完后提醒孩子\n4. 真实场景前给予简短提示'说完名字要做什么？'"
            why_effective = "将'说完话要看对方反应'转化为可练习的具体步骤，培养社交信号监测能力"
        
        # 轮流等待
        elif "轮流" in child_behavior or "等待" in child_behavior or "争当" in child_behavior:
            game_name = "轮流当队长游戏"
            game_steps = "1. 准备计时器：设定 2 分钟\n2. 轮流规则：计时器响了就换人当队长\n3. 引导等待：在孩子等待时说'轮到你时我会提醒你'"
            why_effective = "用可视化的计时器帮助孩子理解'轮流'的抽象概念"
        
        else:
            # 通用场景
            game_name = "社交技能假装游戏"
            game_steps = "1. 模拟当前场景\n2. 练习恰当的社交技能\n3. 给予积极反馈"
            why_effective = "在安全环境中练习，逐步泛化到真实场景"
        
        return game_name, game_steps, why_effective
    
    def _generate_social_skills_plan(self, session_context: Optional[dict] = None) -> Dict[str, Any]:
        """
        V6.0 P0 关键词扩展版：社交技能不足干预模板
        
        V6.0 P0 修复：使用同义词库匹配，支持自然语言描述
        
        匹配顺序：
        1. 关键词扩展匹配（P0）- 使用同义词库
        2. 降级到场景匹配（当前）
        3. LLM 推理（P1，预留接口）- TODO
        """
        context_activity = session_context.get("context", "") if session_context else ""
        child_behavior = session_context.get("child_behavior", "") if session_context else ""
        capability_gap = session_context.get("capability_gap", "") if session_context else ""
        
        # V6.0 P0 核心：优先使用同义词库匹配
        game_name = ""
        game_steps = ""
        why_effective = ""
        
        if capability_gap:
            # 1. 关键词扩展匹配（P0）
            result = self._match_capability_keywords(capability_gap)
            if result:
                game_name = result
                # 根据游戏名称设置详细步骤和原理解释
                game_details = self._get_game_details(game_name, capability_gap)
                game_steps = game_details["steps"]
                why_effective = game_details["why"]
            else:
                # 2. 降级到场景匹配
                game_name, game_steps, why_effective = self._match_social_scene(child_behavior)
        else:
            # 没有 capability_gap，直接降级到场景匹配
            game_name, game_steps, why_effective = self._match_social_scene(child_behavior)
        
        # 3. LLM 推理（P1，预留接口）
        # TODO: 如果关键词匹配和场景匹配都失败，使用 LLM 推理生成干预
        
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
            "strategy_details_gamified": f"一个可尝试的游戏：**{game_name}**\n\n{game_steps}",
            "success_criteria": "在 1 周内，孩子能在游戏前主动使用约定的信号（如主动击掌）",
            "parent_observation_task": f"记录孩子今天是否能使用约定的信号（如击掌），以及在什么情境下使用的。重点是记录'成功时刻'。",
            
            # V6.0 P0 新增：原理解释
            "why_effective": why_effective,
        }
    
    def _get_game_details(self, game_name: str, capability_gap: str) -> Dict[str, str]:
        """
        V6.0 P0 新增：获取游戏详细信息
        
        Args:
            game_name: 游戏名称
            capability_gap: 能力缺口描述
            
        Returns:
            {"steps": str, "why": str} 字典
        """
        details = {
            "社交信号侦探游戏": {
                "steps": "1. 看动画片时暂停，问'他现在感觉如何？你怎么知道的？'\n2. 制作表情卡片，练习识别高兴/生气/难过/惊讶\n3. 真实场景：在游乐场观察其他小朋友的表情，猜测他们的感受\n4. 录像回放：录下互动场景，和孩子一起分析'这时候他是什么意思'",
                "why": f"孩子目前的挑战是'{capability_gap}'。这个练习通过'慢动作回放'和'暂停提问'，帮助孩子学会监测社交信号（表情、眼神、肢体动作）。就像学外语先学单词，社交信号监测是社交能力的基础词汇。"
            },
            "视角游戏：妈妈会看到什么": {
                "steps": "1. 薯片盒游戏：把薯片盒洗干净，在里面放糖果。让孩子站在一个位置，家长站在另一个位置，问'妈妈会看到什么？'\n2. 逐步升级：从简单物品（杯子）到复杂场景（图画书）\n3. 录像回放：录下孩子的表现，和孩子一起看，暂停问'这时候妈妈看到了什么？'\n4. 真实场景：在游乐场、幼儿园等自然情境中练习",
                "why": f"孩子目前的挑战是'{capability_gap}'。这个练习通过具体的视觉提示和角色扮演，让孩子体验'不同位置看到不同内容'。观点采择不是'自私'，而是'还没学会换位思考'。通过反复练习，帮助孩子建立心理理论能力。"
            },
            "视觉提示卡游戏": {
                "steps": "1. 制作步骤卡：把任务分解为 3-5 个步骤，每个步骤画一张图\n2. 按顺序排列：用魔术贴或磁贴按顺序排列\n3. 执行时指卡：不口头提醒，只指下一张卡\n4. 逐步撤退：从全提示→部分提示→独立",
                "why": f"孩子目前的挑战是'{capability_gap}'。工作记忆短板不是'不认真'，而是'记不住多步骤'。我们用视觉提示卡替代'口头提醒'，减少认知负荷，帮助孩子独立完成任务序列。"
            },
            "规则变变变游戏": {
                "steps": "1. 提前预告：变化前 5-10 分钟告知\n2. 微小变化：从极小的变化开始（换一支笔的颜色）\n3. 提供选择权：在可接受范围内给孩子选择\n4. 成功强化：接受变化时给予具体反馈",
                "why": f"孩子目前的挑战是'{capability_gap}'。认知灵活性不是'不固执'，而是'能切换'。我们通过'预告 + 小变化'的组合，逐步提升孩子的适应能力，培养认知灵活性。"
            },
            "情绪小侦探游戏": {
                "steps": "1. 制作表情卡片（高兴/生气/难过/惊讶），每天认一认\n2. 看照片/视频片段，猜测人物感受\n3. 讨论什么情况下会有什么表情\n4. 在真实情境中引导孩子注意他人情绪",
                "why": f"孩子目前的挑战是'{capability_gap}'。情绪识别不是'不理人'，而是'读不懂表情'。我们用'侦探游戏'的方式，让孩子像侦探一样寻找'情绪线索'（表情、眼神、肢体），培养情绪识别能力。"
            },
            "我们开始玩了吗信号练习": {
                "steps": "1. 设定专属信号：和孩子一起发明一个代表'我们开始一起玩啦'的秘密信号（如击掌、对暗号）\n2. 家庭演练：在家玩任何游戏前，必须先完成这个'连接信号'\n3. 过程中，您可以随时喊'暂停！'，所有人定格，再次用信号'重启'游戏\n4. 真实场景提示：去游乐场前说'今天试试看，如果想和小朋友玩，能不能先和他对个暗号？'",
                "why": f"孩子目前的挑战是'{capability_gap}'。这个练习绕开了复杂的社交解读，直接给孩子一个明确、可执行的外在规则，作为她内部'社交监测'能力的脚手架。这是构建更复杂社交能力的第一步。"
            }
        }
        
        return details.get(game_name, {
            "steps": "1. 模拟当前场景\n2. 练习恰当的社交技能\n3. 给予积极反馈",
            "why": "在安全环境中练习，逐步泛化到真实场景"
        })
    # ========== V4.5.20 P0 结束 ==========
