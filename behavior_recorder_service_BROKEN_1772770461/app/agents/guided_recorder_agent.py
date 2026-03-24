"""
引导式行为记录员 Agent V2.0
通过多轮对话引导家长完成专业的 ABC 行为记录

核心理念：
- 不是等待完美输入，而是主动创造完美输入
- 像一位有经验的督导，通过提问帮助家长补全信息
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Optional, Literal
from datetime import datetime

from app.llm.base import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class ABCSession:
    """ABC 记录会话状态"""
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    antecedent: str = ""
    behavior: str = ""
    consequence: str = ""
    conversation_history: list = field(default_factory=list)
    is_complete: bool = False
    analysis_result: Optional[dict] = None


class GuidedRecorderAgent:
    """
    引导式行为记录员 Agent V2.0
    
    通过多轮对话引导家长完成 ABC 记录：
    1. 接收用户输入
    2. 评估信息完整度
    3. 决策：提问补全 or 输出报告
    """

    # 评估与引导的系统提示词（V2.2 优化版）
    EVALUATION_SYSTEM_PROMPT = """你是一位自闭症干预方面的资深督导，正在通过对话帮助一位家长完成一次专业的行为记录（ABC 记录）。

你的目标是引导家长，逐步清晰地描述出：
- A（前因）：行为发生前的情境或事件。
- B（行为）：孩子具体做的、可观察的动作。
- C（后果）：行为发生后，家长或环境立即发生的变化。

【重要判断规则】
1. **何时完成（decision = "analyze"）**：
   - A、B、C 三者都有明确信息（即使某些字段标注为"未明确提及"，只要用户已回应就算完整）
   - 用户已经回答了所有关键问题
   - 此时应设置 missing_field = "none"，decision = "analyze"

2. **何时继续提问（decision = "question"）**：
   - A、B、C 中任一字段完全缺失或明显模糊
   - 用户对某个问题没有给出实质性回答
   - 此时应设置 missing_field 为对应字段，decision = "question"

3. **评估标准**：
   - antecedent_status = "complete"：用户提到了行为发生前的情境/事件/要求
   - behavior_status = "complete"：用户描述了孩子的具体行为
   - consequence_status = "complete"：用户描述了行为后他人的反应或环境变化

请遵循以下规则：
1. **积极共情**：先对家长的描述表示认可，如"谢谢你的描述"、"我明白了"。
2. **评估与补全**：分析当前对话历史，判断 A、B、C 三者中哪一项信息最模糊或缺失。
3. **针对性提问**：只提出当前最需要解决的那个问题。问题必须具体、封闭，易于家长回答。
4. **适时总结**：当信息逐渐完整时，可以简要复述已确认的信息，让家长确认。
5. **完成记录**：当 A、B、C 三者都明确后，不再提问，直接进入分析模式。

请以以下 JSON 格式输出你的评估和决策：
{
    "empathy": "一句简短的共情或认可的话",
    "assessment": {
        "antecedent_status": "complete | incomplete | unclear",
        "behavior_status": "complete | incomplete | unclear",
        "consequence_status": "complete | incomplete | unclear",
        "missing_field": "antecedent | behavior | consequence | none"
    },
    "decision": "question | analyze",
    "question": "如果需要补全，提出一个具体的引导性问题（仅在 decision 为 question 时填写）",
    "summary": "如果信息已完整，简要总结 ABC 三要素（仅在 decision 为 analyze 时填写）"
}"""

    def __init__(self, llm_client: LLMClient):
        """
        初始化引导式记录员 Agent

        Args:
            llm_client: LLM 客户端实例
        """
        self.llm = llm_client
        self.sessions: dict[str, ABCSession] = {}
        logger.info("GuidedRecorderAgent V2.0 初始化完成")

    def _create_session(self) -> ABCSession:
        """创建新的会话"""
        session_id = str(uuid.uuid4())[:8]
        session = ABCSession(session_id=session_id)
        self.sessions[session_id] = session
        logger.info(f"创建新会话：{session_id}")
        return session

    def _get_or_create_session(self, session_id: Optional[str]) -> ABCSession:
        """获取或创建会话"""
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        return self._create_session()

    def _evaluate_input(self, session: ABCSession, user_input: str) -> dict:
        """
        评估用户输入，判断信息完整度

        Args:
            session: 当前会话
            user_input: 用户输入

        Returns:
            评估结果字典
        """
        # 构建对话历史文本
        history_text = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in session.conversation_history[-6:]  # 最近 6 轮
        ])

        # 添加当前 ABC 状态
        abc_status = f"""
当前已收集的信息：
- 前因 (A): {session.antecedent or '未收集'}
- 行为 (B): {session.behavior or '未收集'}
- 后果 (C): {session.consequence or '未收集'}

用户最新输入：{user_input}
"""

        user_prompt = f"""{history_text}

{abc_status}

请评估当前信息完整度，并决定下一步行动。"""

        try:
            result = self.llm.generate_json(
                system_prompt=self.EVALUATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.1,
                max_tokens=800,
            )

            # 验证必需字段
            required_fields = ["empathy", "assessment", "decision"]
            for field_name in required_fields:
                if field_name not in result:
                    logger.warning(f"缺少字段：{field_name}")
                    if field_name == "decision":
                        result["decision"] = "question"
                    elif field_name == "empathy":
                        result["empathy"] = "谢谢你的描述"
                    elif field_name == "assessment":
                        result["assessment"] = {
                            "antecedent_status": "incomplete",
                            "behavior_status": "incomplete",
                            "consequence_status": "incomplete",
                            "missing_field": "antecedent",
                        }

            logger.info(f"评估完成：decision={result['decision']}, missing={result['assessment'].get('missing_field', 'none')}")
            return result

        except Exception as e:
            logger.error(f"评估失败：{e}")
            # 返回默认评估结果
            return {
                "empathy": "谢谢你的描述",
                "assessment": {
                    "antecedent_status": "incomplete",
                    "behavior_status": "incomplete",
                    "consequence_status": "incomplete",
                    "missing_field": "antecedent",
                },
                "decision": "question",
                "question": "能再详细描述一下当时的情况吗？",
            }

    def _extract_abc_from_input(self, session: ABCSession, user_input: str) -> None:
        """
        从用户输入中提取并更新 ABC 信息

        Args:
            session: 当前会话
            user_input: 用户输入
        """
        extraction_prompt = f"""从以下对话中提取或更新 ABC 信息。

当前 ABC 状态：
- 前因 (A): {session.antecedent or '未收集'}
- 行为 (B): {session.behavior or '未收集'}
- 后果 (C): {session.consequence or '未收集'}

用户输入：{user_input}

请提取新的或更新的信息，以 JSON 格式输出：
{{
    "antecedent": "更新后的前因，如果没有新信息则保持原值",
    "behavior": "更新后的行为，如果没有新信息则保持原值",
    "consequence": "更新后的后果，如果没有新信息则保持原值"
}}"""

        try:
            result = self.llm.generate_json(
                system_prompt="你是一个精准的信息提取工具，只输出 JSON，不要解释。",
                user_prompt=extraction_prompt,
                temperature=0.1,
                max_tokens=500,
            )

            # 更新会话状态
            if result.get("antecedent") and result["antecedent"] != session.antecedent:
                session.antecedent = result["antecedent"]
                logger.info(f"更新 antecedent: {session.antecedent}")

            if result.get("behavior") and result["behavior"] != session.behavior:
                session.behavior = result["behavior"]
                logger.info(f"更新 behavior: {session.behavior}")

            if result.get("consequence") and result["consequence"] != session.consequence:
                session.consequence = result["consequence"]
                logger.info(f"更新 consequence: {session.consequence}")

        except Exception as e:
            logger.error(f"提取失败：{e}")

    def _generate_question(self, assessment: dict) -> str:
        """
        根据评估结果生成引导性问题

        Args:
            assessment: 评估结果

        Returns:
            引导性问题
        """
        missing_field = assessment.get("missing_field", "antecedent")

        questions = {
            "antecedent": "在孩子出现这个行为之前，你们正在做什么？或者你正在要求他做什么？",
            "behavior": "你能更具体地描述一下孩子当时做了什么吗？比如是叫喊、躺下，还是别的什么动作？",
            "consequence": "当孩子这样做之后，你或周围的人第一时间是怎么做的？",
        }

        return questions.get(missing_field, questions["antecedent"])

    # V2.1 新增：家长友好型报告生成 Prompt
    PARENT_REPORT_SYSTEM_PROMPT = """你是一位善于与家长沟通的 BCBA 督导。你的任务是将专业的 ABC 分析结果，转化为一份充满共情、易于理解且能给予家长启发的简要报告。

请用温暖、支持的语气，避免专业术语堆砌。让家长感受到：
1. 他们的观察被重视
2. 孩子的行为可以被理解
3. 有明确的后续方向

请严格按照以下 JSON 格式输出：
{
    "empathy_opening": "一句感谢家长细致观察的开场白",
    "plain_explanation": "用比喻或生活化语言解释假设功能（2-3 句话）",
    "core_insight": "用一句话点明这对家长意味着什么",
    "reflection_question": "一个开放性问题，引导家长思考后续策略",
    "encouragement": "一句简短的鼓励话语"
}"""

    # V2.2 新增：带置信度的家长报告生成 Prompt
    PARENT_REPORT_WITH_CONFIDENCE_PROMPT = """你是一位善于与家长沟通的 BCBA 督导。你的任务是将专业的 ABC 分析结果（包含置信度），转化为一份充满共情、易于理解且能给予家长启发的简要报告。

请用温暖、支持的语气，避免专业术语堆砌。根据置信度调整语气：
- **高置信度**：可以给出较为肯定的解释和建议
- **中置信度**：使用"很可能"、"倾向于"等词语，表明是基于经验的合理推断
- **低置信度**：诚实说明信息有限，建议继续观察

请严格按照以下 JSON 格式输出：
{
    "empathy_opening": "一句感谢家长细致观察的开场白",
    "confidence_hint": "根据置信度生成一句提示，如'根据现有信息，这很可能是...'或'基于典型模式，我们倾向于认为...'",
    "plain_explanation": "用比喻或生活化语言解释假设功能（2-3 句话）",
    "core_insight": "用一句话点明这对家长意味着什么",
    "reflection_question": "一个开放性问题，引导家长思考后续策略",
    "encouragement": "一句简短的鼓励话语"
}"""

    def _analyze_complete_abc(self, session: ABCSession) -> dict:
        """
        对完整的 ABC 进行功能假设分析（V2.1 增强版）

        Args:
            session: 已完成的会话

        Returns:
            分析结果（包含家长友好型报告）
        """
        from app.agents.behavior_recorder_agent import BehaviorRecorderAgent

        recorder = BehaviorRecorderAgent(self.llm)

        try:
            # 步骤 1: 专业分析
            analysis_result = recorder.analyze(f"{session.antecedent}，{session.behavior}，{session.consequence}")

            # 步骤 2: 生成家长友好型报告（V2.1 新增）
            parent_report = self._generate_parent_friendly_report(
                session.antecedent,
                session.behavior,
                session.consequence,
                analysis_result.get("hypothesized_function", "inconclusive"),
                analysis_result.get("confidence", "medium"),
                analysis_result.get("confidence_reason", ""),
            )

            # 合并结果
            analysis_result["parent_report"] = parent_report

            return analysis_result

        except Exception as e:
            logger.error(f"分析失败：{e}")
            return {
                "hypothesized_function": "inconclusive",
                "reasoning": f"分析过程中出现错误：{str(e)}",
                "parent_report": {
                    "empathy_opening": "感谢你如此细致地观察和记录孩子的行为。",
                    "plain_explanation": "从你的描述中，我们可以看到孩子可能在用这种方式表达某种需求。",
                    "core_insight": "理解行为背后的原因，是帮助孩子的第一步。",
                    "reflection_question": "你觉得在什么情况下，这个行为会更容易出现？",
                    "encouragement": "你已经做得很好了，我们一起慢慢来。",
                },
            }

    def _generate_parent_friendly_report(self, antecedent: str, behavior: str, consequence: str, function: str, confidence: str = "medium", confidence_reason: str = "") -> dict:
        """
        生成家长友好型报告（V2.2 增强版 - 包含置信度）

        Args:
            antecedent: 前因
            behavior: 行为
            consequence: 后果
            function: 假设功能
            confidence: 置信度 (high/medium/low)
            confidence_reason: 置信度原因

        Returns:
            家长友好型报告
        """
        prompt = f"""【分析数据】
- 前因：{antecedent}
- 行为：{behavior}
- 后果：{consequence}
- 假设功能：{function}
- 置信度：{confidence}
- 置信度原因：{confidence_reason or '基于现有信息的综合判断'}

请根据以上数据，生成一份给家长的友好报告。注意根据置信度调整语气。"""

        try:
            report = self.llm.generate_json(
                system_prompt=self.PARENT_REPORT_WITH_CONFIDENCE_PROMPT,
                user_prompt=prompt,
                temperature=0.3,
                max_tokens=700,
            )

            # 验证必需字段
            required_fields = ["empathy_opening", "plain_explanation", "core_insight", "reflection_question", "encouragement"]
            for field in required_fields:
                if field not in report:
                    logger.warning(f"家长报告缺少字段：{field}")
                    report[field] = ""

            logger.info(f"家长友好型报告生成完成")
            return report

        except Exception as e:
            logger.error(f"家长报告生成失败：{e}")
            # 返回默认报告
            return {
                "empathy_opening": "感谢你如此细致地观察和记录孩子的行为。",
                "plain_explanation": f"从你的描述中，这个行为的功能可能是{self._format_function_name(function)}。",
                "core_insight": "理解行为背后的原因，是帮助孩子的第一步。",
                "reflection_question": "你觉得在什么情况下，这个行为会更容易出现？",
                "encouragement": "你已经做得很好了，我们一起慢慢来。",
            }

    def _format_function_name(self, function: str) -> str:
        """格式化功能名称为中文"""
        mapping = {
            "tangible": "获取实物（如玩具、食物）",
            "attention": "获得关注（包括批评）",
            "escape": "逃避任务或情境",
            "automatic": "自我刺激或感官调节",
            "inconclusive": "暂时无法确定，需要更多观察",
        }
        return mapping.get(function, function)

    def process_input(self, session_id: Optional[str], user_input: str) -> dict:
        """
        处理用户输入，核心方法

        Args:
            session_id: 会话 ID（可选，首次为空）
            user_input: 用户输入

        Returns:
            响应字典
        """
        # 获取或创建会话
        session = self._get_or_create_session(session_id)

        # 记录对话历史
        session.conversation_history.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat(),
        })

        # 从输入中提取 ABC 信息
        self._extract_abc_from_input(session, user_input)

        # 评估信息完整度
        evaluation = self._evaluate_input(session, user_input)

        # 根据决策生成响应
        empathy = evaluation.get("empathy", "谢谢你的描述")

        if evaluation.get("decision") == "analyze":
            # ABC 已完整，进行分析
            logger.info(f"会话 {session.session_id}: ABC 已完整，开始分析")

            # 执行分析
            analysis_result = self._analyze_complete_abc(session)
            session.analysis_result = analysis_result
            session.is_complete = True

            # 生成报告响应（V2.2 包含 confidence 字段）
            response = {
                "session_id": session.session_id,
                "status": "completed",
                "response_type": "report",
                "message": f"{empathy}\n\n{evaluation.get('summary', '信息已收集完整，以下是分析报告：')}",
                "data": {
                    "antecedent": session.antecedent,
                    "behavior": session.behavior,
                    "consequence": session.consequence,
                    "hypothesized_function": analysis_result.get("hypothesized_function", "inconclusive"),
                    "reasoning": analysis_result.get("reasoning", "无法生成推理"),
                    "confidence": analysis_result.get("confidence", "medium"),
                    "confidence_reason": analysis_result.get("confidence_reason", ""),
                    "parent_report": analysis_result.get("parent_report", None),
                },
                "progress": {
                    "antecedent_gathered": bool(session.antecedent),
                    "behavior_gathered": bool(session.behavior),
                    "consequence_gathered": bool(session.consequence),
                },
            }

            session.conversation_history.append({
                "role": "assistant",
                "content": response["message"],
                "timestamp": datetime.now().isoformat(),
            })

        else:
            # 需要继续提问
            question = evaluation.get("question") or self._generate_question(evaluation.get("assessment", {}))

            response = {
                "session_id": session.session_id,
                "status": "in_progress",
                "response_type": "question",
                "message": f"{empathy}\n\n{question}",
                "progress": {
                    "antecedent_gathered": bool(session.antecedent),
                    "behavior_gathered": bool(session.behavior),
                    "consequence_gathered": bool(session.consequence),
                },
            }

            session.conversation_history.append({
                "role": "assistant",
                "content": response["message"],
                "timestamp": datetime.now().isoformat(),
            })

        logger.info(f"会话 {session.session_id} 处理完成：status={response['status']}")
        return response

    def get_session(self, session_id: str) -> Optional[ABCSession]:
        """获取会话"""
        return self.sessions.get(session_id)

    def cleanup_session(self, session_id: str) -> bool:
        """清理会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"会话 {session_id} 已清理")
            return True
        return False
