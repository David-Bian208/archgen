"""
引导式记录员 V4.0 - 确定性状态机引擎
彻底重构：从"LLM 驱动"转向"代码逻辑驱动 + LLM 自然语言生成"

V4.0 核心原则：
1. 确定性状态机：对话流程由代码逻辑控制，不依赖 LLM 主观判断
2. 单 LLM 调用：每轮只调用一次 LLM，用于生成自然语言回应
3. 明确出口条件：信息收集完毕自动进入分析阶段
4. 状态感知：AI 回应体现当前对话阶段和目标

这是"行为记录员"重生为真正智能体的关键一步。
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from app.llm.base import LLMClient
from app.knowledge import get_knowledge_base
from app.agents.insight_analyzer import InsightAnalyzer
from app.agents.intervention_planner import InterventionPlanner

logger = logging.getLogger(__name__)


class InterviewState(Enum):
    """确定性对话状态"""
    WELCOME = "welcome"  # 初始问候，建立关系
    GATHER_CONTEXT = "gather_context"  # 收集行为发生的基本情境
    GATHER_BEHAVIOR = "gather_behavior"  # 收集行为的具体细节
    GATHER_RESPONSE = "gather_response"  # 收集他人反应
    HYPOTHESIS_DRIVEN = "hypothesis_driven"  # 基于假设的深度追问
    READY_TO_ANALYZE = "ready_to_analyze"  # 信息收集完毕
    ANALYZING = "analyzing"  # 正在生成分析
    COMPLETE = "complete"  # 完成


@dataclass
class ClinicalInterviewState:
    """
    确定性对话状态机
    
    状态流转：
    WELCOME → GATHER_CONTEXT → GATHER_BEHAVIOR → GATHER_RESPONSE → HYPOTHESIS_DRIVEN → READY_TO_ANALYZE → COMPLETE
    
    每个状态有明确的：
    - 进入条件
    - 退出条件
    - 核心目标
    """
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    current_state: InterviewState = InterviewState.WELCOME
    
    # 收集的数据
    collected_data: Dict[str, str] = field(default_factory=lambda: {
        "context": "",      # 何时、何地、何事
        "behavior": "",     # 具体做了什么
        "response": "",     # 他人如何回应
        "environment": "",  # 环境上下文（噪音、其他人等）
    })
    
    # 假设管理
    active_hypotheses: List[Dict[str, Any]] = field(default_factory=list)
    primary_hypothesis: Optional[str] = None  # 最可能的假设
    evidence_log: List[str] = field(default_factory=list)  # 证据链
    
    # 对话历史
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    
    # 分析结果
    insight_result: Optional[Dict[str, Any]] = None
    intervention_plan: Optional[Dict[str, Any]] = None
    
    # 元数据
    turn_count: int = 0  # 对话轮数
    last_updated: datetime = field(default_factory=datetime.now)
    
    def get_state_description(self) -> str:
        """获取当前状态的中文描述"""
        descriptions = {
            InterviewState.WELCOME: "初始问候",
            InterviewState.GATHER_CONTEXT: "收集情境信息",
            InterviewState.GATHER_BEHAVIOR: "收集行为细节",
            InterviewState.GATHER_RESPONSE: "收集他人回应",
            InterviewState.HYPOTHESIS_DRIVEN: "深度追问",
            InterviewState.READY_TO_ANALYZE: "准备分析",
            InterviewState.ANALYZING: "生成分析中",
            InterviewState.COMPLETE: "已完成",
        }
        return descriptions.get(self.current_state, "未知状态")
    
    def get_state_goal(self) -> str:
        """获取当前状态的核心目标"""
        goals = {
            InterviewState.WELCOME: "建立信任关系，邀请家长描述行为",
            InterviewState.GATHER_CONTEXT: "了解行为发生的时间、地点、环境",
            InterviewState.GATHER_BEHAVIOR: "了解孩子具体做了什么、没做什么",
            InterviewState.GATHER_RESPONSE: "了解家长或老师当时的回应方式",
            InterviewState.HYPOTHESIS_DRIVEN: "针对最可能的假设，追问关键细节",
            InterviewState.READY_TO_ANALYZE: "信息已完整，准备生成分析报告",
            InterviewState.ANALYZING: "正在整理分析",
            InterviewState.COMPLETE: "对话已完成",
        }
        return goals.get(self.current_state, "未知目标")
    
    def is_data_complete(self) -> bool:
        """检查核心数据是否完整"""
        return all([
            self.collected_data.get("context", "").strip(),
            self.collected_data.get("behavior", "").strip(),
            self.collected_data.get("response", "").strip(),
        ])
    
    def should_transition_to(self, user_input: str) -> Optional[InterviewState]:
        """
        根据当前状态和用户输入，决定是否需要状态转移
        
        这是纯代码逻辑，不调用 LLM。
        
        Returns:
            下一个状态（如果需要转移），否则 None
        """
        current = self.current_state
        
        # WELCOME → GATHER_CONTEXT：用户已描述行为
        if current == InterviewState.WELCOME and len(user_input.strip()) > 10:
            # 提取用户输入中的关键信息
            self._extract_initial_info(user_input)
            return InterviewState.GATHER_CONTEXT
        
        # GATHER_CONTEXT → GATHER_BEHAVIOR：情境已收集
        if current == InterviewState.GATHER_CONTEXT:
            if self.collected_data.get("context", "").strip():
                return InterviewState.GATHER_BEHAVIOR
            # 用户输入包含情境信息
            if any(kw in user_input for kw in ["时", "时候", "地方", "地点", "环境", "在"]):
                return InterviewState.GATHER_BEHAVIOR
        
        # GATHER_BEHAVIOR → GATHER_RESPONSE：行为已收集
        if current == InterviewState.GATHER_BEHAVIOR:
            if self.collected_data.get("behavior", "").strip():
                return InterviewState.GATHER_RESPONSE
            # 用户输入包含行为描述
            if any(kw in user_input for kw in ["做", "说", "表现", "行为", "动作"]):
                return InterviewState.GATHER_RESPONSE
        
        # GATHER_RESPONSE → HYPOTHESIS_DRIVEN：回应已收集
        if current == InterviewState.GATHER_RESPONSE:
            if self.collected_data.get("response", "").strip():
                # 检查是否需要深度追问
                if self._should_deep_dive():
                    return InterviewState.HYPOTHESIS_DRIVEN
                else:
                    return InterviewState.READY_TO_ANALYZE
        
        # HYPOTHESIS_DRIVEN → READY_TO_ANALYZE：深度追问完成
        if current == InterviewState.HYPOTHESIS_DRIVEN:
            if len(self.evidence_log) >= 3:  # 至少有 3 条证据
                return InterviewState.READY_TO_ANALYZE
        
        # READY_TO_ANALYZE → ANALYZING
        if current == InterviewState.READY_TO_ANALYZE:
            return InterviewState.ANALYZING
        
        # ANALYZING → COMPLETE
        if current == InterviewState.ANALYZING:
            return InterviewState.COMPLETE
        
        return None
    
    def _extract_initial_info(self, user_input: str) -> None:
        """从初始输入中提取信息"""
        # 简单关键词提取（后续可用 LLM 增强）
        if any(kw in user_input for kw in ["时", "时候", "在"]):
            self.collected_data["context"] = user_input[:100]
        
        if any(kw in user_input for kw in ["做", "行为", "表现"]):
            self.collected_data["behavior"] = user_input[:100]
        
        self.evidence_log.append(f"初始输入：{user_input[:50]}...")
    
    def _should_deep_dive(self) -> bool:
        """判断是否需要深度追问"""
        # 如果证据不足 3 条，需要深度追问
        return len(self.evidence_log) < 3


# V4.0 单一、集成的提示词模板
SINGLE_TURN_PROMPT_TEMPLATE = """你是一位资深的自闭症干预督导，正在温和地引导家长完成一次行为记录。

【你的角色与目标】
- 角色：共情的倾听者、思维的引导者
- 当前对话阶段：{current_state_description}
- 阶段核心目标：{current_goal}

【截至目前我们了解到】
{collected_data_summary}

【家长刚刚说】
"{latest_user_input}"

【你的任务】
请生成你的回应，必须包含：
1. **共情与确认**（1 句话）：对家长上一句话表达理解。
2. **思维推进**（根据阶段目标，二选一）：
   - 如果信息已足够进入下一阶段：清晰总结我们已确认的事实，并自然过渡到下一阶段的**唯一一个**核心问题。
   - 如果信息不足：提出当前阶段下，最核心、最迫切的**唯一一个**问题。
3. **专业锚点**（内部思考，不输出）：基于当前信息，你认为最可能的行为功能假设是什么？（如：逃避任务难度、寻求关注、感觉调节）。这仅用于指导你的提问方向。

请以自然、温暖、专业的口语化语言回应。不要使用 JSON 格式，直接输出自然语言。"""


class GuidedRecorderV4:
    """
    引导式记录员 V4.0 - 确定性状态机驱动
    
    核心改进：
    1. 状态转移由代码逻辑控制（不调用 LLM）
    2. 每轮只调用一次 LLM（生成自然语言）
    3. 明确的完成条件（ABC 信息完整 + 证据充足）
    4. 状态感知的 Prompt 构建
    """
    
    def __init__(self, llm_client: LLMClient):
        """
        初始化 V4.0 Agent
        
        Args:
            llm_client: LLM 客户端实例
        """
        self.llm = llm_client
        self.sessions: Dict[str, ClinicalInterviewState] = {}
        logger.info("GuidedRecorderV4 初始化完成 - 确定性状态机引擎")
    
    def _create_session(self) -> ClinicalInterviewState:
        """创建新会话"""
        session_id = str(uuid.uuid4())[:8]
        session = ClinicalInterviewState(session_id=session_id)
        self.sessions[session_id] = session
        logger.info(f"创建新会话：{session_id}")
        return session
    
    def _get_or_create_session(self, session_id: Optional[str]) -> ClinicalInterviewState:
        """获取或创建会话"""
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        return self._create_session()
    
    def _update_collected_data(self, state: ClinicalInterviewState, user_input: str) -> None:
        """
        更新收集的数据（基于简单规则，而非 LLM）
        
        策略：
        - 根据当前状态，将用户输入归类到对应字段
        - 保留原始输入作为证据
        """
        current = state.current_state
        
        # 记录证据
        state.evidence_log.append(user_input)
        
        # 根据状态归类数据
        if current == InterviewState.GATHER_CONTEXT and not state.collected_data["context"]:
            state.collected_data["context"] = user_input
            logger.info(f"收集情境：{user_input[:50]}...")
        
        elif current == InterviewState.GATHER_BEHAVIOR and not state.collected_data["behavior"]:
            state.collected_data["behavior"] = user_input
            logger.info(f"收集行为：{user_input[:50]}...")
        
        elif current == InterviewState.GATHER_RESPONSE and not state.collected_data["response"]:
            state.collected_data["response"] = user_input
            logger.info(f"收集回应：{user_input[:50]}...")
        
        elif current == InterviewState.HYPOTHESIS_DRIVEN:
            # 深度追问阶段，记录为额外证据
            logger.info(f"深度追问证据：{user_input[:50]}...")
        
        state.last_updated = datetime.now()
        state.turn_count += 1
    
    def _build_prompt(self, state: ClinicalInterviewState, user_input: str) -> str:
        """
        构建单一、集成的 Prompt
        
        这是 V4.0 的核心：所有上下文信息整合到一个 Prompt 中
        """
        # 构建已收集数据的摘要
        collected_summary = self._build_collected_summary(state)
        
        # 填充模板
        prompt = SINGLE_TURN_PROMPT_TEMPLATE.format(
            current_state_description=state.get_state_description(),
            current_goal=state.get_state_goal(),
            collected_data_summary=collected_summary,
            latest_user_input=user_input,
        )
        
        logger.info(f"构建 Prompt：state={state.current_state.value}, turns={state.turn_count}")
        return prompt
    
    def _build_collected_summary(self, state: ClinicalInterviewState) -> str:
        """构建已收集数据的摘要"""
        lines = []
        
        if state.collected_data.get("environment"):
            lines.append(f"- 环境：{state.collected_data['environment']}")
        
        if state.collected_data.get("context"):
            lines.append(f"- 情境：{state.collected_data['context']}")
        
        if state.collected_data.get("behavior"):
            lines.append(f"- 孩子的表现：{state.collected_data['behavior']}")
        
        if state.collected_data.get("response"):
            lines.append(f"- 他人的回应：{state.collected_data['response']}")
        
        if state.primary_hypothesis:
            lines.append(f"- 初步假设：{state.primary_hypothesis}")
        
        if not lines:
            return "（尚未收集到具体信息，这是第一轮对话）"
        
        return "\n".join(lines)
    
    def _should_generate_report(self, state: ClinicalInterviewState) -> bool:
        """
        判断是否应该生成报告（代码逻辑）
        
        条件：
        1. ABC 核心信息完整
        2. 至少 3 条证据
        3. 或者对话轮数 >= 5（避免无限追问）
        """
        abc_complete = state.is_data_complete()
        enough_evidence = len(state.evidence_log) >= 3
        max_turns = state.turn_count >= 5
        
        should_generate = abc_complete and (enough_evidence or max_turns)
        
        if should_generate:
            logger.info(f"触发报告生成：abc_complete={abc_complete}, evidence={len(state.evidence_log)}, turns={state.turn_count}")
        
        return should_generate
    
    def _trigger_analysis(self, state: ClinicalInterviewState) -> None:
        """
        触发分析流程
        
        调用 InsightAnalyzer 和 InterventionPlanner 生成完整报告
        """
        logger.info(f"触发分析流程：session={state.session_id}")
        
        try:
            # 1. 生成洞察
            analyzer = InsightAnalyzer(self.llm)
            insight = analyzer.analyze(
                environment=state.collected_data.get("environment", ""),
                antecedent=state.collected_data.get("context", ""),
                behavior=state.collected_data.get("behavior", ""),
                consequence=state.collected_data.get("response", ""),
            )
            
            # 2. 生成干预计划
            planner = InterventionPlanner()
            scenario_key = ""  # V4.0 暂不依赖场景匹配
            session_context = {
                "environment": state.collected_data.get("environment", ""),
                "context": state.collected_data.get("context", ""),
                "child_behavior": state.collected_data.get("behavior", ""),
                "others_response": state.collected_data.get("response", ""),
            }
            plan = planner.generate_plan("H1", scenario_key, session_context)
            
            # 3. 保存结果
            state.insight_result = insight
            state.intervention_plan = plan
            
            logger.info(f"分析完成：session={state.session_id}")
            
        except Exception as e:
            logger.error(f"分析失败：{e}")
            state.insight_result = {
                "core_insight_for_parent": "孩子正在用这种方式表达他的需求。",
                "report": {
                    "observation": "我们观察到了一些值得关注的行为。",
                    "insight": "孩子可能在用行为表达某种需求。",
                    "suggestion": "可以尝试更多积极的回应方式。",
                }
            }
    
    def process(self, session_id: Optional[str], user_input: str) -> Dict[str, Any]:
        """
        V4.0 主处理流程
        
        集权式控制：
        1. 加载状态
        2. 更新收集的数据（基于简单规则）
        3. 确定性状态转移（代码逻辑）
        4. 构建 Prompt，发起唯一一次 LLM 调用
        5. 判断是否完成（代码逻辑）
        6. 保存状态，返回响应
        
        Args:
            session_id: 会话 ID
            user_input: 用户输入
            
        Returns:
            响应字典
        """
        # 1. 加载状态
        state = self._get_or_create_session(session_id)
        
        # 记录用户输入
        state.conversation_history.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat(),
        })
        
        logger.info(f"V4.0 处理输入：session={state.session_id}, state={state.current_state.value}, turn={state.turn_count + 1}")
        
        # 2. 更新收集的数据（基于简单规则，而非 LLM）
        self._update_collected_data(state, user_input)
        
        # 3. 确定性状态转移（代码逻辑）
        next_state = state.should_transition_to(user_input)
        if next_state:
            state.current_state = next_state
            logger.info(f"状态转移：{state.current_state.value}")
        
        # 4. 构建 Prompt，发起唯一一次 LLM 调用
        prompt = self._build_prompt(state, user_input)
        
        try:
            llm_response = self.llm.generate(
                system_prompt="你是一位资深的自闭症干预督导，用温暖、专业的语言与家长交流。",
                user_prompt=prompt,
                temperature=0.7,
                max_tokens=500,
            )
        except Exception as e:
            logger.error(f"LLM 调用失败：{e}")
            llm_response = "谢谢您的分享，我正在整理信息。"
        
        # 5. 判断是否完成（代码逻辑）
        if self._should_generate_report(state) and state.current_state != InterviewState.ANALYZING:
            state.current_state = InterviewState.ANALYZING
            self._trigger_analysis(state)
            
            # 生成完成响应
            llm_response = "感谢您的分享，我已经有了清晰的了解。现在我将为您整理一份分析报告。"
            
            # 转移到完成状态
            state.current_state = InterviewState.COMPLETE
            
            # 构建完整响应
            response = self._build_complete_response(state)
        
        else:
            # 构建继续追问响应
            response = {
                "session_id": state.session_id,
                "status": "in_progress",
                "response_type": "follow_up",
                "message": llm_response,
                "state": state.current_state.value,
            }
        
        # 6. 保存状态，返回响应
        state.conversation_history.append({
            "role": "assistant",
            "content": response.get("message", llm_response),
            "timestamp": datetime.now().isoformat(),
        })
        
        self.sessions[state.session_id] = state
        
        logger.info(f"V4.0 响应完成：session={state.session_id}, status={response.get('status')}")
        
        return response
    
    def _build_complete_response(self, state: ClinicalInterviewState) -> Dict[str, Any]:
        """构建完成响应"""
        insight = state.insight_result or {}
        
        return {
            "session_id": state.session_id,
            "status": "completed",
            "response_type": "insight_report",
            "message": "感谢您的分享，我已经有了清晰的了解。现在我将为您整理一份分析报告。",
            "data": {
                "context": state.collected_data.get("context", ""),
                "child_behavior": state.collected_data.get("behavior", ""),
                "others_response": state.collected_data.get("response", ""),
                "core_insight": insight.get("core_insight_for_parent", ""),
                "expert_breakdown": insight.get("expert_breakdown", {}),
                "report": insight.get("report", {}),
                "intervention_plan": state.intervention_plan,
            },
        }
    
    def get_session(self, session_id: str) -> Optional[ClinicalInterviewState]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    def cleanup_session(self, session_id: str) -> bool:
        """清理会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"会话 {session_id} 已清理")
            return True
        return False
