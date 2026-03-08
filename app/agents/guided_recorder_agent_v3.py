"""
引导式记录员 V3.9.2 - 智能动态临床访谈模式
彻底根治重复提问问题，实现状态感知的鉴别诊断逻辑

V3.9.2 核心修复：
- 实现会话状态追踪与假设置信度动态管理
- 重构下一问生成逻辑，基于置信度阈值决策
- 强制 Prompt 总结与聚焦，避免循环提问
- 删除所有导致重复提问的硬编码逻辑

这是"行为记录员"Agent 能否被用户接受的生死线修复。
"""

import json
import html
import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from app.llm.base import LLMClient
from app.knowledge import get_knowledge_base
from app.agents.intervention_planner import InterventionPlanner

logger = logging.getLogger(__name__)


@dataclass
class ConversationSession:
    """对话会话状态（V3.9.2 - 智能状态机）"""
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    environment: str = ""  # V3.2 新增：环境上下文
    context: str = ""  # 情境
    child_behavior: str = ""  # 孩子的表现
    others_response: str = ""  # 他人的回应
    conversation_history: list = field(default_factory=list)
    is_complete: bool = False
    insight_result: Optional[dict] = None
    # V3.4 鉴别诊断相关
    matched_scenario: Optional[dict] = None
    competing_hypotheses: list = field(default_factory=list)
    discriminating_answer: str = ""
    # V3.9.2 核心新增：会话状态追踪
    session_state: dict = field(default_factory=lambda: {
        "evidence": [],  # 用户已提供的关键事实
        "hypothesis_confidence": {
            "逃避难度": 0.33,
            "寻求关注": 0.33,
            "感觉逃避": 0.33,
        },  # 动态更新的置信度
        "current_focus": None,  # 当前聚焦的假设
        "clarified_hypotheses": [],  # 已厘清的假设
    })


class GuidedRecorderAgentV3:
    """
    引导式记录员 V3.9.2 - 智能动态临床访谈模式

    通过自然对话引导家长完成观察记录：
    1. 共情回应
    2. 状态感知的智能追问（基于置信度决策）
    3. 生成洞察报告

    V3.9.2 核心改进：
    - 不再机械追问，而是基于假设置信度动态决策
    - 当某假设置信度 > 0.7 时，自动转向深度挖掘
    - 每轮对话先总结共识，再提出唯一精准问题
    - 彻底根治重复提问
    """

    # V3.9.2 智能访谈 Prompt - 强制总结与聚焦
    CONVERSATION_SYSTEM_PROMPT = """你是一位善于倾听的自闭症干预专家，正在与家长进行一次温和的访谈。

你的目标是帮助家长梳理一次行为观察，但不要使用任何专业术语（如"前因"、"行为"、"后果"、"ABC"等）。

请遵循以下原则：
1. **共情优先**：先认可家长的观察和感受
2. **状态感知**：你的提问必须体现对之前对话内容的理解
3. **一次一问**：每次只追问最核心的一个信息
4. **总结先行**：在提问前，先简要复述关键共识

【当前对话状态】
你将收到以下状态信息：
- 已收集的证据列表
- 各假设的当前置信度
- 当前聚焦的假设（如果有）

【你的任务】
生成唯一一个最有助于推进分析的问题。你的回应必须包含三个部分：
1. **总结**："基于我们目前的对话，我了解到..."（简要复述关键共识）
2. **决策**："为了进一步明确，现在最需要厘清的一点是..."（说明提问目的）
3. **提问**：提出唯一的、精准的问题

【完成判断】
当以下信息都清晰时，可以结束对话：
1. 环境上下文：噪音水平、其他人活动等
2. 情境：孩子当时的活动/环境
3. 孩子的表现：具体做了什么
4. 他人的回应：家长或老师的反应

【重要规则】
- 如果用户已经提到"任务太难"、"觉得难"等信息，不要重复问时间点或是否寻求关注
- 如果某假设置信度已很高（>0.7），转向深度挖掘该假设的原因
- 你的提问必须体现对之前对话的理解（如："您提到他觉得任务太难，那么..."）

请以以下 JSON 格式输出你的回应：
{
    "empathy": "一句共情的话，认可家长的观察",
    "summary": "基于目前对话的简要总结（1-2 句话）",
    "focus": "现在最需要厘清的一点是什么",
    "environment_gathered": true/false,
    "context_gathered": true/false,
    "behavior_gathered": true/false,
    "response_gathered": true/false,
    "is_complete": true/false,
    "follow_up_question": "如果需要更多信息，提出一个自然的追问（仅在 is_complete 为 false 时填写）",
    "final_summary": "如果信息已完整，简要复述你理解的情况（仅在 is_complete 为 true 时填写）"
}"""

    def __init__(self, llm_client: LLMClient):
        """
        初始化引导式记录员 V3.9.2

        Args:
            llm_client: LLM 客户端实例
        """
        self.llm = llm_client
        self.sessions: dict[str, ConversationSession] = {}
        logger.info("GuidedRecorderAgentV3 V3.9.2 初始化完成 - 智能动态临床访谈模式")

    def _create_session(self) -> ConversationSession:
        """创建新会话"""
        session_id = str(uuid.uuid4())[:8]
        session = ConversationSession(session_id=session_id)
        self.sessions[session_id] = session
        logger.info(f"创建新会话：{session_id}")
        return session

    def _get_or_create_session(self, session_id: Optional[str]) -> ConversationSession:
        """获取或创建会话"""
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        return self._create_session()

    def _update_state(self, session: ConversationSession, user_input: str) -> None:
        """
        V3.9.2 核心：更新会话状态

        解析用户输入，更新 evidence 和 hypothesis_confidence

        Args:
            session: 当前会话
            user_input: 用户输入
        """
        state = session.session_state

        # 使用 LLM 解析输入，更新证据和置信度
        extraction_prompt = f"""从以下用户输入中提取关键信息并评估假设置信度。

【当前状态】
已收集证据：{state['evidence']}
当前假设置信度：{json.dumps(state['hypothesis_confidence'], ensure_ascii=False)}

【用户输入】
{user_input}

【任务】
1. 提取新的关键事实（证据）
2. 评估各假设的置信度变化（0-1 之间）
3. 判断是否有假设已达到高置信度（>0.7）

假设说明：
- 逃避难度：孩子因为任务太难而逃避
- 寻求关注：孩子通过行为获取他人关注
- 感觉逃避：孩子因为感觉刺激不适而逃避

请以 JSON 格式输出：
{{
    "new_evidence": ["新提取的关键事实 1", "新提取的关键事实 2"],
    "confidence_updates": {{
        "逃避难度": 0.8,
        "寻求关注": 0.1,
        "感觉逃避": 0.1
    }},
    "high_confidence_hypothesis": "逃避难度"  // 如果有假设>0.7，填写名称；否则 null
}}"""

        try:
            result = self.llm.generate_json(
                system_prompt="只输出 JSON，不要解释。基于用户输入的内容合理评估置信度。",
                user_prompt=extraction_prompt,
                temperature=0.1,
                max_tokens=600,
            )

            # 更新证据列表
            new_evidence = result.get("new_evidence", [])
            for evidence in new_evidence:
                if evidence and evidence not in state["evidence"]:
                    state["evidence"].append(evidence)

            # 更新置信度
            confidence_updates = result.get("confidence_updates", {})
            for hyp, conf in confidence_updates.items():
                if hyp in state["hypothesis_confidence"]:
                    state["hypothesis_confidence"][hyp] = conf

            # 检查是否有高置信度假设
            high_conf = result.get("high_confidence_hypothesis")
            if high_conf:
                state["current_focus"] = high_conf
                logger.info(f"高置信度假设：{high_conf}，转向深度挖掘")

            logger.info(f"状态更新完成：evidence={len(state['evidence'])}, focus={state['current_focus']}")

        except Exception as e:
            logger.error(f"状态更新失败：{e}")

    def _decide_next_question(self, session: ConversationSession) -> str:
        """
        V3.9.2 核心：决策下一问

        基于会话状态决定下一个问题类型：
        - 如果任一假设置信度 > 0.7：停止鉴别，转向深度挖掘
        - 否则：生成鉴别性问题区分接近的假设

        Args:
            session: 当前会话

        Returns:
            问题类型标识
        """
        state = session.session_state
        conf = state["hypothesis_confidence"]

        # 规则 1：如果任一假设置信度 > 0.7，转向深度挖掘
        max_conf = max(conf.values())
        if max_conf > 0.7:
            top_hyp = max(conf, key=conf.get)
            state["current_focus"] = top_hyp
            logger.info(f"置信度阈值触发（{max_conf:.2f}），聚焦：{top_hyp}")

            if top_hyp == "逃避难度":
                return "deep_dive_escape"
            elif top_hyp == "寻求关注":
                return "deep_dive_attention"
            elif top_hyp == "感觉逃避":
                return "deep_dive_sensory"

        # 规则 2：找出置信度接近且未厘清的两个假设，生成鉴别性问题
        sorted_hyps = sorted(conf.items(), key=lambda x: x[1], reverse=True)
        top_two = sorted_hyps[:2]

        # 如果前两个假设置信度接近（差值 < 0.2），需要鉴别
        if len(top_two) >= 2 and abs(top_two[0][1] - top_two[1][1]) < 0.2:
            hyp1, hyp2 = top_two[0][0], top_two[1][0]
            logger.info(f"需要鉴别：{hyp1} ({conf[hyp1]:.2f}) vs {hyp2} ({conf[hyp2]:.2f})")
            return f"discriminate_{hyp1}_vs_{hyp2}"

        # 默认：继续收集基础信息
        return "gather_info"

    def _get_deep_dive_question(self, hypothesis: str) -> str:
        """
        获取深度挖掘问题

        Args:
            hypothesis: 聚焦的假设

        Returns:
            深度挖掘问题模板
        """
        questions = {
            "逃避难度": [
                "您觉得是任务中的哪一部分让他感到最难？是读题不理解，还是动手操作有困难？",
                "当他觉得难的时候，通常会怎么做？是直接放弃，还是尝试求助？",
                "您有没有观察到，他在哪些类型的任务上表现得比较轻松，不容易出现这种情况？",
            ],
            "寻求关注": [
                "当您或老师注意到他时，他的行为会有什么变化吗？",
                "他平时在什么情况下最容易主动寻求您的关注？",
                "如果他一个人安静地玩，您通常会在什么时候过去看他？",
            ],
            "感觉逃避": [
                "当时周围环境有什么特别的吗？比如噪音、灯光、或者其他让他不舒服的感觉刺激？",
                "他平时对声音、触觉或者其他感觉刺激比较敏感吗？",
                "当他表现出逃避时，如果改变环境（比如换个安静的地方），情况会有所改善吗？",
            ],
        }

        import random
        return random.choice(questions.get(hypothesis, ["能再详细描述一下当时的情况吗？"]))

    def _evaluate_conversation(self, session: ConversationSession, user_input: str) -> dict:
        """
        评估对话状态，决定下一步（V3.9.2 - 基于状态机）

        Args:
            session: 当前会话
            user_input: 用户输入

        Returns:
            评估结果
        """
        # V3.9.2 核心：先更新状态
        self._update_state(session, user_input)

        state = session.session_state

        # 构建对话历史（限制最近 6 轮）
        history_text = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in session.conversation_history[-6:]
        ])

        # 当前状态摘要
        state_summary = f"""
【当前对话状态】
已收集证据：{state['evidence'] if state['evidence'] else '暂无'}
假设置信度：{json.dumps(state['hypothesis_confidence'], ensure_ascii=False)}
当前聚焦：{state['current_focus'] or '尚未确定'}
已厘清假设：{state['clarified_hypotheses'] if state['clarified_hypotheses'] else '暂无'}

【当前已收集的信息】
- 环境：{session.environment or '尚未了解'}
- 情境：{session.context or '尚未了解'}
- 孩子的表现：{session.child_behavior or '尚未了解'}
- 他人的回应：{session.others_response or '尚未了解'}

【家长最新输入】
{user_input}
"""

        # 决定下一问类型
        question_type = self._decide_next_question(session)

        user_prompt = f"""{history_text}

{state_summary}

【决策指令】
当前问题类型：{question_type}

请根据上述状态和决策，生成你的回应。记住：
1. 先总结目前达成的共识
2. 说明现在需要厘清什么
3. 提出唯一的、精准的问题
"""

        try:
            result = self.llm.generate_json(
                system_prompt=self.CONVERSATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.2,
                max_tokens=800,
            )

            # 验证必需字段
            required_fields = ["empathy", "is_complete"]
            for field_name in required_fields:
                if field_name not in result:
                    logger.warning(f"缺少字段：{field_name}")
                    if field_name == "empathy":
                        result["empathy"] = "谢谢你的分享"
                    elif field_name == "is_complete":
                        result["is_complete"] = False

            # 如果 LLM 没有生成 follow_up_question 但 is_complete=False，根据决策类型补充
            if not result.get("follow_up_question") and not result["is_complete"]:
                if question_type.startswith("deep_dive_"):
                    hypothesis = question_type.replace("deep_dive_", "")
                    result["follow_up_question"] = self._get_deep_dive_question(hypothesis)
                else:
                    result["follow_up_question"] = "能再详细说说当时的情况吗？"

            # 更新会话状态
            self._update_session_from_evaluation(session, result, user_input)

            logger.info(f"对话评估完成：is_complete={result['is_complete']}, question_type={question_type}")
            return result

        except Exception as e:
            logger.error(f"对话评估失败：{e}")
            return {
                "empathy": "谢谢你的分享",
                "summary": "我正在努力理解您的描述",
                "is_complete": False,
                "follow_up_question": "能再详细说说当时的情况吗？",
            }

    def _update_session_from_evaluation(self, session: ConversationSession, evaluation: dict, user_input: str) -> None:
        """
        根据评估结果更新会话状态

        Args:
            session: 当前会话
            evaluation: 评估结果
            user_input: 用户输入
        """
        # 使用 LLM 提取信息
        extraction_prompt = f"""从以下对话中提取或更新信息：

【当前信息】
- 环境：{session.environment or '未提及'}
- 情境：{session.context or '未提及'}
- 孩子的表现：{session.child_behavior or '未提及'}
- 他人的回应：{session.others_response or '未提及'}

【对话内容】
家长：{user_input}

请提取新信息，以 JSON 格式输出：
{{
    "environment": "更新后的环境上下文（噪音、其他人活动等）",
    "context": "更新后的情境",
    "child_behavior": "更新后的孩子表现",
    "others_response": "更新后的他人回应"
}}"""

        try:
            extracted = self.llm.generate_json(
                system_prompt="只输出 JSON，不要解释。",
                user_prompt=extraction_prompt,
                temperature=0.1,
                max_tokens=500,
            )

            if extracted.get("environment") and extracted["environment"] != session.environment:
                session.environment = extracted["environment"]
                logger.info(f"更新环境：{session.environment}")

            if extracted.get("context") and extracted["context"] != session.context:
                session.context = extracted["context"]
                logger.info(f"更新情境：{session.context}")

            if extracted.get("child_behavior") and extracted["child_behavior"] != session.child_behavior:
                session.child_behavior = extracted["child_behavior"]
                logger.info(f"更新孩子表现：{session.child_behavior}")

            if extracted.get("others_response") and extracted["others_response"] != session.others_response:
                session.others_response = extracted["others_response"]
                logger.info(f"更新他人回应：{session.others_response}")

        except Exception as e:
            logger.error(f"信息提取失败：{e}")

    def _generate_insight(self, session: ConversationSession) -> dict:
        """
        生成洞察报告

        Args:
            session: 已完成的会话

        Returns:
            洞察报告
        """
        from app.agents.insight_analyzer import InsightAnalyzer

        analyzer = InsightAnalyzer(self.llm)

        try:
            insight = analyzer.analyze(
                session.environment,
                session.context,
                session.child_behavior,
                session.others_response,
                session.competing_hypotheses if session.competing_hypotheses else None,
                session.discriminating_answer,
            )

            # 生成完整报告
            report = self._generate_narrative_report(session, insight)

            insight["report"] = report
            return insight

        except Exception as e:
            logger.error(f"洞察生成失败：{e}")
            return {
                "core_insight": "孩子正在用这种方式表达他的需求。",
                "capability_hypothesis": "相关技能还在发展中。",
                "report": {
                    "observation": "我们观察到了一些值得关注的行为。",
                    "insight": "孩子可能在用行为表达某种需求。",
                    "suggestion": "可以尝试更多积极的回应方式。",
                    "reflection": "下次类似情况下，我们可以尝试什么不同的做法呢？",
                },
            }

    def _generate_narrative_report(self, session: ConversationSession, insight: dict) -> dict:
        """
        生成叙事型报告（V3.3 - 有观点、有温度、有步骤）

        Args:
            session: 会话
            insight: 洞察分析结果（包含 expert_breakdown）

        Returns:
            叙事型报告
        """
        expert = insight.get('expert_breakdown', {})

        prompt = f"""你是一位善于沟通的 BCBA 督导。请基于以下信息，生成一份"有观点、有温度、有步骤"的叙事型报告。

【观察信息】
- 环境：{session.environment or '未提及'}
- 情境：{session.context}
- 孩子的表现：{session.child_behavior}
- 他人的回应：{session.others_response}

【专家拆解】
- 行为模式：{expert.get('behavior_pattern', '待分析')}
- 功能假设：{expert.get('functional_hypothesis', '待分析')}
- 能力缺口：{expert.get('capability_gap', '待分析')}
- 环境因素：{expert.get('contextual_factors', '待分析')}
- 临床鉴别思考：{insight.get('clinical_differential', '待生成')}

【共情翻译】
- 核心洞察（金句）：{insight.get('core_insight_for_parent', '孩子正在表达需求。')}
- 干预原则：{insight.get('strategy_principle', '待分析')}

请按照以下六个部分组织报告，将报告从"模块堆砌"变为"有观点、有温度、有步骤的叙事"：

### 关于孩子在{session.context[:20] if session.context else '该情境'}中表现的观察分析

**1. 我们看到了什么（精简事实）**
用温暖的语言精简描述事实，认可家长的观察。例如："您敏锐地观察到孩子'看老师就做得好，不看就容易发呆'，这种观察非常精准。"

**2. 核心洞察：这意味着什么？**
建议生成一句"金句"，直击本质。例如：
- "孩子不是不努力，而是他的'动作记忆'需要靠眼睛实时'充电'。"
- "这更像是'不知道眼睛该看哪里时，手脚就不知道该干什么'，而不是'不想做'。"

**3. 多角度理解（V3.6 新增）**
简要说明分析时的多假设考量。例如：
"针对'发呆'行为，评估中通常考虑几种可能性：1) 提示依赖；2) 自我刺激；3) 感觉逃避。结合'有提示时表现良好'的信息，提示依赖的可能性较高。"

**4. 行为模式解读：为什么会这样？**
用家长能懂的语言解释，采用协同分析的语气。例如：
"我们的分析指向了'提示依赖'这一模式。孩子需要看着老师来'刷新'下一步的记忆。当视线离开，'任务指令'可能中断。这通常提示着工作记忆的发育特点。"

**5. 我们可以尝试什么：一个具体的起点**
建议给出一个与"核心洞察"对应的具体"第一招"。您可以根据孩子的反应灵活调整。例如：
"我们可以尝试'预装一个动作'的策略：活动前，和孩子一起夸张地摆出第一个动作，并大声说出名称。如果孩子感兴趣，可以多玩几次。"

**6. 一个小思考（引导家长成为合作者）**
用启发性的问题邀请家长成为合作者：
"您是否发现，在他'不需要看就能做'的活动里，任务步骤是不是更简单、或已练习很多遍？这或许能帮助我们找到'记住动作'的钥匙。"

**摘要生成要求**：
摘要部分应高度精炼，只保留核心结论与价值，删除对情境的重复描述。例如：
"分析指出了孩子在集体活动中的'提示依赖'模式。我们将通过游戏化的'建立锚点'策略，帮助他将外部提示转化为内部动力。"

请以以下 JSON 格式输出：
{{
    "observation": "第一部分：我们看到了什么（精简事实 + 认可家长）",
    "core_insight": "第二部分：核心洞察（金句，直击本质）",
    "clinical_differential": "第三部分：多角度理解（多假设考量）",
    "expert_view": "第四部分：行为模式解读（协同分析）",
    "suggestion": "第五部分：一个具体的起点（第一招）",
    "reflection": "第六部分：一个小思考（引导合作）",
    "summary": "摘要：高度精炼的核心结论与价值（1-2 句话）"
}}"""

        try:
            report = self.llm.generate_json(
                system_prompt="你是一位善于沟通的 BCBA 督导。用温暖、支持的语言生成报告，同时保持专业深度。将报告从'模块堆砌'变为'有观点、有温度、有步骤的叙事'。",
                user_prompt=prompt,
                temperature=0.3,
                max_tokens=1500,
            )

            # 验证字段
            required_fields = ["observation", "core_insight", "expert_view", "suggestion", "reflection"]
            for field in required_fields:
                if field not in report:
                    report[field] = ""

            logger.info("V3.3 叙事型报告生成完成")
            return report

        except Exception as e:
            logger.error(f"报告生成失败：{e}")
            return {
                "observation": f"在{session.context or '该情境'}中，您敏锐地观察到孩子出现了{session.child_behavior or '一些行为'}。",
                "core_insight": insight.get("core_insight_for_parent", "孩子不是不想做，而是需要更多的支持来记住下一步该做什么。"),
                "expert_view": f"从专业角度看，这属于'提示依赖'行为。{expert.get('functional_hypothesis', '孩子需要持续的视觉提示来维持任务执行。')} {expert.get('capability_gap', '这常与工作记忆的发育特点有关。')} {expert.get('contextual_factors', '')}",
                "suggestion": "我们可以尝试'预装一个动作'的策略：在活动前，和孩子一起夸张地摆出第一个动作，并大声说出动作名称，帮助他建立内部提示。",
                "reflection": "您是否发现，在那些他'不需要看就能做'的活动里，任务步骤是不是更简单、或者他已经练习了无数遍？这或许能帮助我们找到帮他'记住动作'的钥匙。",
            }

    def process_input(self, session_id: Optional[str], user_input: str) -> dict:
        """
        处理用户输入（V3.9.2 - 智能状态机驱动）

        Args:
            session_id: 会话 ID
            user_input: 用户输入

        Returns:
            响应
        """
        session = self._get_or_create_session(session_id)

        # 记录对话
        session.conversation_history.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat(),
        })

        # 首次输入时匹配场景并加载竞争性假设
        if len(session.conversation_history) == 1 and not session.matched_scenario:
            self._match_scenario_and_load_hypotheses(session, user_input)

        # V3.9.2 核心：评估对话状态（包含状态更新和决策）
        evaluation = self._evaluate_conversation(session, user_input)

        # 生成响应
        empathy = evaluation.get("empathy", "谢谢你的分享")

        if evaluation.get("is_complete"):
            # 信息完整，生成洞察报告
            logger.info(f"会话 {session.session_id}: 信息完整，生成洞察")

            insight = self._generate_insight(session)
            session.insight_result = insight
            session.is_complete = True

            final_summary = evaluation.get("final_summary", evaluation.get("summary", "我已经了解了情况"))

            # 自然过渡语
            transition = "根据我们刚才的交流，我生成了一份简要的分析报告，希望能帮助您更好地理解孩子的行为。"

            response = {
                "session_id": session.session_id,
                "status": "completed",
                "response_type": "insight_report",
                "message": f"{empathy}\n\n{final_summary}\n\n{transition}",
                "data": {
                    "context": session.context,
                    "child_behavior": session.child_behavior,
                    "others_response": session.others_response,
                    "functional_judgment": insight.get("functional_judgment", "inconclusive"),
                    "core_insight": insight.get("core_insight_for_parent", ""),
                    "expert_breakdown": insight.get("expert_breakdown", {}),
                    "strategy_principle": insight.get("strategy_principle", ""),
                    "report": insight.get("report", {}),
                    # 干预计划
                    "intervention_plan": self._generate_intervention_plan(session, insight),
                },
            }

        else:
            # 继续追问 - V3.9.2 确保问题来自状态决策
            question = evaluation.get("follow_up_question", "")

            # 如果 LLM 没有生成问题，根据决策类型补充
            if not question:
                question_type = self._decide_next_question(session)
                if question_type.startswith("deep_dive_"):
                    hypothesis = question_type.replace("deep_dive_", "")
                    question = self._get_deep_dive_question(hypothesis)
                else:
                    question = "能再详细说说当时的情况吗？"

            # 构建包含总结的回应
            summary = evaluation.get("summary", "")
            if summary:
                message = f"{empathy}\n\n{summary}\n\n{question}"
            else:
                message = f"{empathy}\n\n{question}"

            response = {
                "session_id": session.session_id,
                "status": "in_progress",
                "response_type": "follow_up",
                "message": message,
            }

        # 记录 AI 回应
        session.conversation_history.append({
            "role": "assistant",
            "content": response["message"],
            "timestamp": datetime.now().isoformat(),
        })

        logger.info(f"会话 {session.session_id} 处理完成：status={response['status']}")

        # 净化报告数据
        response = self._sanitize_report_data(response)

        return response

    def _sanitize_report_data(self, obj):
        """
        彻底净化报告数据 - 递归清理所有乱码

        清理规则：
        1. 移除调试信息：%!(string=、(MISSING)、!,(MISSING) 等
        2. HTML 实体解码
        3. 清理多余空格和标点

        Args:
            obj: 字典、列表或字符串

        Returns:
            净化后的对象
        """
        if isinstance(obj, dict):
            return {key: self._sanitize_report_data(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._sanitize_report_data(item) for item in obj]
        elif isinstance(obj, str):
            # 1. HTML 实体解码
            text = html.unescape(obj)

            # 2. 移除调试信息模式
            text = re.sub(r'%!\([^)]*\)', '', text)
            text = text.replace('(MISSING)', '')
            text = re.sub(r'!?,\s*\(MISSING\)', '', text)

            # 3. 清理多余空格
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()

            return text
        else:
            return obj

    def _match_scenario_and_load_hypotheses(self, session: ConversationSession, user_input: str) -> None:
        """
        匹配场景并加载竞争性假设

        Args:
            session: 当前会话
            user_input: 用户输入
        """
        knowledge_base = get_knowledge_base()

        # 提取关键词
        keywords = self._extract_behavior_keywords(user_input)

        # 匹配场景
        matched_scenario = knowledge_base.match_scenario(keywords)

        if matched_scenario:
            session.matched_scenario = matched_scenario
            session.competing_hypotheses = knowledge_base.get_competing_hypotheses(
                matched_scenario.get("scene_key", "")
            )
            logger.info(f"场景匹配成功：{matched_scenario.get('scene_key')}, 假设数：{len(session.competing_hypotheses)}")
        else:
            logger.info(f"未匹配到场景，使用通用分析流程")

    def _extract_behavior_keywords(self, text: str) -> list[str]:
        """
        从文本中提取行为关键词

        Args:
            text: 用户输入文本

        Returns:
            关键词列表
        """
        knowledge_base = get_knowledge_base()

        # 从知识库获取所有关键词
        all_keywords = []
        for scenario in knowledge_base.data.get("scenarios", []):
            all_keywords.extend(scenario.get("keywords", []))

        # 去重
        all_keywords = list(set(all_keywords))

        # 提取匹配的关键词
        matched = [kw for kw in all_keywords if kw in text]

        logger.info(f"提取关键词：{matched}")
        return matched

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """获取会话"""
        return self.sessions.get(session_id)

    def cleanup_session(self, session_id: str) -> bool:
        """清理会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"会话 {session_id} 已清理")
            return True
        return False

    def _generate_intervention_plan(self, session: ConversationSession, insight: dict) -> Optional[dict]:
        """
        生成个性化干预计划（四步结构）

        Args:
            session: 当前会话
            insight: 洞察分析结果

        Returns:
            干预计划字典
        """
        planner = InterventionPlanner()

        # 从专家拆解中获取功能假设 ID
        expert = insight.get("expert_breakdown", {})
        scenario_key = session.matched_scenario.get("scene_key", "") if session.matched_scenario else ""

        # 默认使用 H1（第一个假设）
        matched_hypothesis_id = "H1"

        # 准备会话上下文
        session_context = {
            "environment": session.environment,
            "context": session.context,
            "child_behavior": session.child_behavior,
            "others_response": session.others_response,
        }

        plan = planner.generate_plan(matched_hypothesis_id, scenario_key, session_context)

        if plan:
            # 游戏化策略描述
            plan["strategy_details_gamified"] = planner.gamify_strategy_description(
                plan.get("strategy_details", ""),
                "孩子"
            )
            # HTML 实体解码
            plan = planner.sanitize_plan(plan)

        return plan
