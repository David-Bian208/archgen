"""
引导式记录员 V3.0 - 共情访谈模式
从"系统审问"转向"专家访谈"

核心理念：
- 自然、友好的对话
- 隐藏专业术语
- 像与治疗师交谈
"""

import json
import logging
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
    """对话会话状态（V3.4 - 加入鉴别诊断）"""
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    environment: str = ""  # V3.2 新增：环境上下文
    context: str = ""  # 情境
    child_behavior: str = ""  # 孩子的表现
    others_response: str = ""  # 他人的回应
    conversation_history: list = field(default_factory=list)
    is_complete: bool = False
    insight_result: Optional[dict] = None
    # V3.4 新增：鉴别诊断相关
    matched_scenario: Optional[dict] = None  # 匹配的场景
    competing_hypotheses: list = field(default_factory=list)  # 竞争性假设
    discriminating_answer: str = ""  # 用户对鉴别性问题的回答


class GuidedRecorderAgentV3:
    """
    引导式记录员 V3.0 - 共情访谈模式
    
    通过自然对话引导家长完成观察记录：
    1. 共情回应
    2. 自然追问（隐藏 ABC 术语）
    3. 生成洞察报告
    """

    # V3.2 共情访谈 Prompt（加入环境上下文）
    CONVERSATION_SYSTEM_PROMPT = """你是一位善于倾听的自闭症干预专家，正在与家长进行一次温和的访谈。

你的目标是帮助家长梳理一次行为观察，但不要使用任何专业术语（如"前因"、"行为"、"后果"、"ABC"等）。

请遵循以下原则：
1. **共情优先**：先认可家长的观察和感受
2. **环境优先**：在首轮回应中，自然询问环境上下文（噪音、其他孩子活动等）
3. **自然追问**：用生活化的语言提问，不要像审问
4. **一次一问**：每次只追问最核心的一个信息
5. **适时总结**：信息完整时，自然复述确认

【V3.2 新话术模板】
用户首轮描述后，AI 的首轮回应必须包含环境询问：
"感谢您这么细致的观察，这非常有帮助。为了能更准确地理解当时的情况，我想了解一下当时周围的环境怎么样？比如是有点吵闹还是比较安静，其他小朋友大多在做什么呢？"

【重要】如果用户首轮输入已经包含环境信息（如"吵闹"、"安静"、"其他小朋友"等），则不需要再问环境，直接问情境。

【后续追问话术参考】
- 了解情境："孩子是在什么活动或什么情况下出现这个情况的呢？"
- 了解行为："当时你观察到孩子具体做了什么，或者没做什么，让你比较在意呢？"
- 了解回应："当孩子那样做的时候，你或周围人（比如老师）第一时间是怎么回应的呢？"

【完成判断】
当以下信息都清晰时，可以结束对话：
1. 环境上下文：噪音水平、其他人活动等
2. 情境：孩子当时的活动/环境
3. 孩子的表现：具体做了什么
4. 他人的回应：家长或老师的反应

请以以下 JSON 格式输出你的回应：
{
    "empathy": "一句共情的话，认可家长的观察",
    "environment_gathered": true/false,
    "context_gathered": true/false,
    "behavior_gathered": true/false,
    "response_gathered": true/false,
    "is_complete": true/false,
    "follow_up_question": "如果需要更多信息，提出一个自然的追问（仅在 is_complete 为 false 时填写）",
    "summary": "如果信息已完整，简要复述你理解的情况（仅在 is_complete 为 true 时填写）"
}"""

    def __init__(self, llm_client: LLMClient):
        """
        初始化引导式记录员 V3.0

        Args:
            llm_client: LLM 客户端实例
        """
        self.llm = llm_client
        self.sessions: dict[str, ConversationSession] = {}
        logger.info("GuidedRecorderAgentV3 初始化完成")

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

    def _evaluate_conversation(self, session: ConversationSession, user_input: str) -> dict:
        """
        评估对话状态，决定下一步

        Args:
            session: 当前会话
            user_input: 用户输入

        Returns:
            评估结果
        """
        # 构建对话历史
        history_text = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in session.conversation_history[-6:]
        ])

        # 当前已收集的信息
        current_status = f"""
【当前已了解的信息】
- 情境：{session.context or '尚未了解'}
- 孩子的表现：{session.child_behavior or '尚未了解'}
- 他人的回应：{session.others_response or '尚未了解'}

【家长最新输入】
{user_input}
"""

        user_prompt = f"""{history_text}

{current_status}

请评估当前对话状态，决定下一步如何回应。"""

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

            # 更新会话状态
            self._update_session_from_evaluation(session, result, user_input)

            logger.info(f"对话评估完成：is_complete={result['is_complete']}")
            return result

        except Exception as e:
            logger.error(f"对话评估失败：{e}")
            return {
                "empathy": "谢谢你的分享",
                "is_complete": False,
                "follow_up_question": "能再详细说说当时的情况吗？",
            }

    def _update_session_from_evaluation(self, session: ConversationSession, evaluation: dict, user_input: str) -> None:
        """
        根据评估结果更新会话状态（V3.2 - 加入环境信息提取）

        Args:
            session: 当前会话
            evaluation: 评估结果
            user_input: 用户输入
        """
        # 使用 LLM 提取信息（V3.2 新增 environment 字段）
        extraction_prompt = f"""从以下对话中提取或更新信息：

【当前信息】
- 环境上下文：{session.environment or '未提及'}
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

            # V3.2 新增：提取环境信息
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
        生成洞察报告（V3.4 - 加入鉴别诊断）

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

【共情翻译】
- 核心洞察（金句）：{insight.get('core_insight_for_parent', '孩子正在表达需求。')}
- 干预原则：{insight.get('strategy_principle', '待分析')}

请按照以下五个部分组织报告，将报告从"模块堆砌"变为"有观点、有温度、有步骤的叙事"：

### 关于孩子在{session.context[:20] if session.context else '该情境'}中表现的观察分析

**1. 我们看到了什么（精简事实）**
用温暖的语言精简描述事实，认可家长的观察。例如："在室内跳操时，您敏锐地发现孩子'看老师就做得好，不看就容易发呆'，这种观察非常精准。"

**2. 核心洞察：这意味着什么？（替代原"这可能意味着什么"）**
必须生成一句"金句"，直击本质。例如：
- "孩子不是不努力，而是他的'动作记忆'需要靠眼睛实时'充电'。一旦看不到老师，他的'任务图纸'就模糊了。"
- "这更像是'不知道眼睛该看哪里时，手和脚就不知道该干什么'，而不是'不想做'。"

**3. 专业视角：为什么会这样？（替代原"专业视角"）**
用家长能懂的语言解释"逃避 - 提示依赖"模型。例如：
"从专业角度看，这属于'提示依赖'。孩子需要持续看着老师来'刷新'下一步该做什么的记忆。当视线离开，不是他不想做，而是'任务指令'中断了。这常与工作记忆的发育特点有关。嘈杂的环境（音乐、其他小朋友）让他更依赖老师这个最明确的提示。"

**4. 我们可以尝试什么：一个具体的起点**
必须给出一个与"核心洞察"直接对应的、超具体的"第一招"。例如：
"基于此，我们可以尝试'预装一个动作'的策略：在跳操前，和他一起夸张地摆出第一个动作（如'开飞机'），并大声说'记住哦，第一个是开飞机！'。目的是帮他把一个外部提示（老师动作）转化为一个内部提示（自己脑子里的口诀或画面）。下次他发呆时，可以轻声提示'开飞机！'，看他能否接上。"

**5. 一个小思考（引导家长成为合作者）**
将问题从"还有哪些类似情况？"升级为更具启发性的：
"您是否发现，在那些他'不需要看就能做'的活动里（比如唱熟悉的儿歌、玩熟悉的拼图），任务步骤是不是更简单、或者他已经练习了无数遍？这或许能帮助我们找到帮他'记住动作'的钥匙。"

请以以下 JSON 格式输出：
{{
    "observation": "第一部分：我们看到了什么（精简事实 + 认可家长）",
    "core_insight": "第二部分：核心洞察（金句，直击本质）",
    "expert_view": "第三部分：专业视角（用家长能懂的语言解释提示依赖模型）",
    "suggestion": "第四部分：一个具体的起点（超具体的第一招）",
    "reflection": "第五部分：一个小思考（引导家长成为合作者）"
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
        处理用户输入（V3.4 - 加入鉴别诊断）

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

        # V3.4 新增：首次输入时匹配场景并加载竞争性假设
        if len(session.conversation_history) == 1 and not session.matched_scenario:
            self._match_scenario_and_load_hypotheses(session, user_input)

        # 评估对话状态
        evaluation = self._evaluate_conversation(session, user_input)

        # 生成响应
        empathy = evaluation.get("empathy", "谢谢你的分享")

        if evaluation.get("is_complete"):
            # 信息完整，生成洞察报告
            logger.info(f"会话 {session.session_id}: 信息完整，生成洞察")

            insight = self._generate_insight(session)
            session.insight_result = insight
            session.is_complete = True

            summary = evaluation.get("summary", "我已经了解了情况")
            
            # V3.1 新增：自然过渡语
            transition = "根据我们刚才的交流，我生成了一份简要的分析报告，希望能帮助您更好地理解孩子的行为。"

            response = {
                "session_id": session.session_id,
                "status": "completed",
                "response_type": "insight_report",
                "message": f"{empathy}\n\n{summary}\n\n{transition}",
                "data": {
                    "context": session.context,
                    "child_behavior": session.child_behavior,
                    "others_response": session.others_response,
                    "functional_judgment": insight.get("functional_judgment", "inconclusive"),
                    "core_insight": insight.get("core_insight_for_parent", ""),
                    "expert_breakdown": insight.get("expert_breakdown", {}),
                    "strategy_principle": insight.get("strategy_principle", ""),
                    "report": insight.get("report", {}),
                    # V3.5 新增：干预计划
                    "intervention_plan": self._generate_intervention_plan(session, insight),
                },
            }

        else:
            # 继续追问
            question = evaluation.get("follow_up_question", "能再详细说说吗？")

            response = {
                "session_id": session.session_id,
                "status": "in_progress",
                "response_type": "follow_up",
                "message": f"{empathy}\n\n{question}",
            }

        # 记录 AI 回应
        session.conversation_history.append({
            "role": "assistant",
            "content": response["message"],
            "timestamp": datetime.now().isoformat(),
        })

        logger.info(f"会话 {session.session_id} 处理完成：status={response['status']}")
        return response

    def _match_scenario_and_load_hypotheses(self, session: ConversationSession, user_input: str) -> None:
        """
        V3.4 新增：匹配场景并加载竞争性假设

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

    def _generate_discriminating_question(self, session: ConversationSession) -> str:
        """
        V3.4 新增：基于竞争性假设生成鉴别性问题

        Args:
            session: 当前会话

        Returns:
            鉴别性问题
        """
        if not session.competing_hypotheses:
            return "能再详细描述一下当时的情况吗？"

        knowledge_base = get_knowledge_base()
        return knowledge_base.generate_discriminating_question(session.competing_hypotheses)

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
        V3.5 新增：生成个性化干预计划

        Args:
            session: 当前会话
            insight: 洞察分析结果

        Returns:
            干预计划字典
        """
        planner = InterventionPlanner()

        # 从专家拆解中获取功能假设 ID（需要映射）
        expert = insight.get("expert_breakdown", {})
        functional_judgment = expert.get("functional_hypothesis", "")

        # 简化处理：根据场景和假设名称匹配
        # 实际应该从 insight 中读取匹配的假设 ID
        scenario_key = session.matched_scenario.get("scene_key", "") if session.matched_scenario else ""

        # 默认使用 H1（第一个假设）
        matched_hypothesis_id = "H1"

        # 如果有明确的假设 ID，使用它
        if "functional_judgment" in insight and insight["functional_judgment"]:
            # 这里需要根据实际逻辑映射到假设 ID
            # 简化处理：使用 H1
            pass

        plan = planner.generate_plan(matched_hypothesis_id, scenario_key)

        if plan:
            # 游戏化策略描述
            plan["strategy_details_gamified"] = planner.gamify_strategy_description(
                plan.get("strategy_details", ""),
                "孩子"
            )

        return plan
