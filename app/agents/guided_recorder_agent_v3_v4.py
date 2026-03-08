"""
引导式记录员 V4.0 - 动态情境感知版
从"模板追问"转向"个性化鉴别"

V4.0 核心改进：
- 动态追问：基于用户已描述情境生成个性化问题
- 功能鉴别：追问直接服务于行为功能判断
- 个性化计划：干预计划完全基于上游分析动态生成
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
from app.agents.intervention_planner_v4_fixed import InterventionPlannerV4Fixed

logger = logging.getLogger(__name__)


@dataclass
class ConversationSession:
    """对话会话状态（V4.0 - 强化情境追踪）"""
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    environment: str = ""
    context: str = ""
    child_behavior: str = ""
    others_response: str = ""
    conversation_history: list = field(default_factory=list)
    is_complete: bool = False
    insight_result: Optional[dict] = None
    matched_scenario: Optional[dict] = None
    competing_hypotheses: list = field(default_factory=list)
    discriminating_answer: str = ""


class GuidedRecorderAgentV4:
    """
    引导式记录员 V4.0 - 动态情境感知版
    
    核心能力：
    1. 情境感知追问：基于已输入信息生成个性化鉴别问题
    2. 功能导向：追问直接服务于行为功能鉴别
    3. 个性化计划：干预计划完全基于分析结果动态生成
    """

    # V4.0 动态共情访谈 Prompt
    CONVERSATION_SYSTEM_PROMPT = """你是一位善于倾听的自闭症干预专家，正在与家长进行一次温和的访谈。

你的目标是帮助家长梳理一次行为观察，但不要使用任何专业术语。

请遵循以下原则：
1. **共情优先**：先认可家长的观察和感受
2. **情境感知**：追问必须结合用户已描述的具体情境，不要问通用问题
3. **功能鉴别**：追问的目的是鉴别行为功能（逃避/关注/实物/自动）
4. **自然追问**：用生活化的语言提问，不要像审问
5. **一次一问**：每次只追问最核心的一个信息

【V4.0 动态追问逻辑】
根据用户已描述的情境和行为，生成个性化的鉴别性问题：

**如果用户已描述"做操/体操/集体活动" + "发呆/走神"：**
→ 追问："在做操时，其他小朋友是都在认真做，还是也在走神？他的眼神是看起来在迷茫寻找提示，还是完全放空？"
→ 目的：鉴别提示依赖 vs 自我刺激

**如果用户已描述"学习/任务" + "抗拒/不要/不肯"：**
→ 追问："在学习时，是任务本身有难度（比如他不会做），还是他学了一会儿后才开始抗拒？抗拒时他会观察你的反应吗？"
→ 目的：鉴别逃避难度 vs 寻求关注

**如果用户已描述"嘈杂环境" + "捂耳朵/回避/发呆"：**
→ 追问："当时的环境是不是特别吵闹？他平时对噪音敏感吗？换个安静环境会好一些吗？"
→ 目的：鉴别感官过载

**如果用户已描述"要求/指令" + "不做/拖延"：**
→ 追问："这个要求对他来说是新的还是已经会的？如果是很简单的要求他也拖延，那可能是寻求关注；如果是新任务，可能是能力挑战。"

【重要】追问必须引用用户已提到的具体活动（如"做操"、"学习"、"吃饭"），不要问"在什么活动中"这种通用问题。

【完成判断】
当以下信息都清晰时，可以结束对话：
1. 环境上下文：噪音水平、其他人活动等
2. 情境：孩子当时的活动/环境
3. 孩子的表现：具体做了什么
4. 他人的回应：家长或老师的反应
5. 功能鉴别信息：足以判断行为功能

请以以下 JSON 格式输出你的回应：
{
    "empathy": "一句共情的话，认可家长的观察",
    "environment_gathered": true/false,
    "context_gathered": true/false,
    "behavior_gathered": true/false,
    "response_gathered": true/false,
    "is_complete": true/false,
    "follow_up_question": "如果需要更多信息，提出一个自然的追问（仅在 is_complete 为 false 时填写）",
    "summary": "如果信息已完整，简要复述你理解的情况（仅在 is_complete 为 true 时填写）
}"""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.sessions: dict[str, ConversationSession] = {}
        logger.info("GuidedRecorderAgentV4 初始化完成")

    def _create_session(self) -> ConversationSession:
        session_id = str(uuid.uuid4())[:8]
        session = ConversationSession(session_id=session_id)
        self.sessions[session_id] = session
        logger.info(f"创建新会话：{session_id}")
        return session

    def _get_or_create_session(self, session_id: Optional[str]) -> ConversationSession:
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        return self._create_session()

    def _evaluate_conversation(self, session: ConversationSession, user_input: str) -> dict:
        """V4.0 评估对话状态，生成情境感知追问"""
        
        history_text = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in session.conversation_history[-6:]
        ])

        # V4.0 强化：传入已收集的情境信息用于动态追问
        current_status = f"""
【当前已了解的信息】
- 环境：{session.environment or '尚未了解'}
- 情境/活动：{session.context or '尚未了解'}
- 孩子的表现：{session.child_behavior or '尚未了解'}
- 他人的回应：{session.others_response or '尚未了解'}

【家长最新输入】
{user_input}

【追问要求】
如果信息不完整，请基于上述已知情境生成一个个性化的鉴别性问题。
例如：如果已知是"做操时发呆"，追问"做操时其他小朋友在做什么？他的眼神是迷茫还是放空？"
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

            required_fields = ["empathy", "is_complete"]
            for field_name in required_fields:
                if field_name not in result:
                    result[field_name] = "谢谢你的分享" if field_name == "empathy" else False

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
    "environment": "更新后的环境上下文",
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

            if extracted.get("environment"):
                session.environment = extracted["environment"]
            if extracted.get("context"):
                session.context = extracted["context"]
            if extracted.get("child_behavior"):
                session.child_behavior = extracted["child_behavior"]
            if extracted.get("others_response"):
                session.others_response = extracted["others_response"]

        except Exception as e:
            logger.error(f"信息提取失败：{e}")

    def _generate_insight(self, session: ConversationSession) -> dict:
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

            report = self._generate_narrative_report(session, insight)
            insight["report"] = report
            return insight

        except Exception as e:
            logger.error(f"洞察生成失败：{e}")
            return {"core_insight": "孩子正在用这种方式表达他的需求。"}

    def _generate_narrative_report(self, session: ConversationSession, insight: dict) -> dict:
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
- 临床鉴别思考：{insight.get('clinical_differential', '待生成')}

请以以下 JSON 格式输出：
{{
    "observation": "第一部分：我们看到了什么（精简事实 + 认可家长）",
    "core_insight": "第二部分：核心洞察（金句，直击本质）",
    "clinical_differential": "第三部分：多角度理解（多假设考量）",
    "expert_view": "第四部分：行为模式解读（协同分析）",
    "suggestion": "第五部分：一个具体的起点（第一招）",
    "reflection": "第六部分：一个小思考（引导合作）",
    "summary": "摘要：高度精炼的核心结论与价值"
}}"""

        try:
            report = self.llm.generate_json(
                system_prompt="你是一位善于沟通的 BCBA 督导。用温暖、支持的语言生成报告。",
                user_prompt=prompt,
                temperature=0.3,
                max_tokens=1500,
            )
            return report
        except Exception as e:
            logger.error(f"报告生成失败：{e}")
            return {}

    def _generate_intervention_plan(self, session: ConversationSession, insight: dict) -> Optional[dict]:
        """V4.0 Final 生成个性化干预计划 - 使用修复版规划器"""
        planner = InterventionPlannerV4Fixed()

        expert = insight.get("expert_breakdown", {})
        scenario_key = session.matched_scenario.get("scene_key", "") if session.matched_scenario else ""
        matched_hypothesis_id = "H1"

        # V4.0 Final 核心：传递完整的结构化分析结论
        session_context = {
            "environment": session.environment,
            "context": session.context,
            "child_behavior": session.child_behavior,
            "others_response": session.others_response,
            # V4.0 Final 关键：从专家拆解中提取真实的功能假设和能力缺口
            "primary_hypothesis": expert.get("functional_hypothesis", ""),
            "capability_gap": expert.get("capability_gap", ""),
            "behavior_pattern": expert.get("behavior_pattern", ""),
        }

        logger.info(f"V4.0 Final 生成计划：primary_hypothesis={session_context['primary_hypothesis'][:50] if session_context['primary_hypothesis'] else 'None'}, capability_gap={session_context['capability_gap'][:50] if session_context['capability_gap'] else 'None'}")

        plan = planner.generate_plan(matched_hypothesis_id, scenario_key, session_context)

        return plan

    def process_input(self, session_id: Optional[str], user_input: str) -> dict:
        session = self._get_or_create_session(session_id)

        session.conversation_history.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat(),
        })

        if len(session.conversation_history) == 1 and not session.matched_scenario:
            self._match_scenario_and_load_hypotheses(session, user_input)

        evaluation = self._evaluate_conversation(session, user_input)
        empathy = evaluation.get("empathy", "谢谢你的分享")

        if evaluation.get("is_complete"):
            logger.info(f"会话 {session.session_id}: 信息完整，生成洞察")

            insight = self._generate_insight(session)
            session.insight_result = insight
            session.is_complete = True

            summary = evaluation.get("summary", "我已经了解了情况")
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
                    "intervention_plan": self._generate_intervention_plan(session, insight),
                },
            }
        else:
            question = evaluation.get("follow_up_question", "能再详细说说吗？")
            response = {
                "session_id": session.session_id,
                "status": "in_progress",
                "response_type": "follow_up",
                "message": f"{empathy}\n\n{question}",
            }

        session.conversation_history.append({
            "role": "assistant",
            "content": response["message"],
            "timestamp": datetime.now().isoformat(),
        })

        logger.info(f"会话 {session.session_id} 处理完成：status={response['status']}")
        response = self._sanitize_report_data(response)
        return response

    def _sanitize_report_data(self, obj):
        if isinstance(obj, dict):
            return {key: self._sanitize_report_data(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._sanitize_report_data(item) for item in obj]
        elif isinstance(obj, str):
            text = html.unescape(obj)
            text = re.sub(r'%!\([^)]*\)', '', text)
            text = text.replace('(MISSING)', '')
            text = re.sub(r'!?,\s*\(MISSING\)', '', text)
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            return text
        else:
            return obj

    def _match_scenario_and_load_hypotheses(self, session: ConversationSession, user_input: str) -> None:
        knowledge_base = get_knowledge_base()
        keywords = self._extract_behavior_keywords(user_input)
        matched_scenario = knowledge_base.match_scenario(keywords)

        if matched_scenario:
            session.matched_scenario = matched_scenario
            session.competing_hypotheses = knowledge_base.get_competing_hypotheses(
                matched_scenario.get("scene_key", "")
            )
            logger.info(f"场景匹配成功：{matched_scenario.get('scene_key')}")
        else:
            logger.info(f"未匹配到场景，使用通用分析流程")

    def _extract_behavior_keywords(self, text: str) -> list[str]:
        knowledge_base = get_knowledge_base()
        all_keywords = []
        for scenario in knowledge_base.data.get("scenarios", []):
            all_keywords.extend(scenario.get("keywords", []))
        all_keywords = list(set(all_keywords))
        matched = [kw for kw in all_keywords if kw in text]
        logger.info(f"提取关键词：{matched}")
        return matched

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        return self.sessions.get(session_id)

    def cleanup_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"会话 {session_id} 已清理")
            return True
        return False
