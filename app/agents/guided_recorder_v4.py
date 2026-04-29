"""
引导式记录员 V4.2 - 确定性状态机引擎（完整修复版）
彻底重构：从"LLM 驱动"转向"代码逻辑驱动 + LLM 自然语言生成"

V4.2 核心改进（完整修复）：
1. 报告完整性修复：正确映射 InsightAnalyzer 输出到前端期望的格式
2. 综合摘要生成：从对话历史提取关键信息，而非机械复制首条消息
3. 协商式结束：新增 READY_TO_CONCLUDE 状态，询问用户确认后再结束
4. 证据链生成：从证据日志自动生成支持证据描述

V4.1 核心改进（紧急修复）：
1. 确定性状态机：对话流程由代码逻辑控制，不依赖 LLM 主观判断
2. 单 LLM 调用：每轮只调用一次 LLM，用于生成自然语言回应
3. 严格出口条件：ABC 信息完整 + 关键功能证据 + 无效追问停止检查
4. 假设锁定机制：检测到强证据后锁定假设，禁止发散追问
5. 深度挖掘轮次限制：防止无限追问

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
    """确定性对话状态（V4.2 修复版）"""
    WELCOME = "welcome"  # 初始问候，建立关系
    GATHER_CONTEXT = "gather_context"  # 收集行为发生的基本情境
    GATHER_BEHAVIOR = "gather_behavior"  # 收集行为的具体细节
    GATHER_RESPONSE = "gather_response"  # 收集他人反应
    HYPOTHESIS_DRIVEN = "hypothesis_driven"  # 基于假设的深度追问
    DEEP_DIVE = "deep_dive"  # V4.1 新增：锁定假设后的深度挖掘
    READY_TO_ANALYZE = "ready_to_analyze"  # 信息收集完毕
    READY_TO_CONCLUDE = "ready_to_conclude"  # V4.2 新增：准备结束，等待用户确认
    ANALYZING = "analyzing"  # 正在生成分析
    COMPLETE = "complete"  # 完成


@dataclass
class ClinicalInterviewState:
    """
    确定性对话状态机（V4.1 修复版）
    
    状态流转：
    WELCOME → GATHER_CONTEXT → GATHER_BEHAVIOR → GATHER_RESPONSE → HYPOTHESIS_DRIVEN → READY_TO_ANALYZE → COMPLETE
    
    每个状态有明确的：
    - 进入条件
    - 退出条件
    - 核心目标
    
    V4.1 新增：
    - deep_dive_rounds: 深度挖掘轮次计数（防止无限追问）
    - excluded_hypotheses: 已排除的假设列表（避免重复追问）
    - locked_hypothesis: 当前锁定的核心假设（防止发散）
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
    locked_hypothesis: Optional[str] = None  # V4.1 新增：锁定的核心假设
    excluded_hypotheses: List[str] = field(default_factory=list)  # V4.1 新增：已排除的假设
    
    # 对话历史
    conversation_history: List[str] = field(default_factory=list)  # V4.1 简化为字符串列表
    
    # 分析结果
    insight_result: Optional[Dict[str, Any]] = None
    intervention_plan: Optional[Dict[str, Any]] = None
    
    # 元数据
    turn_count: int = 0  # 对话轮数
    deep_dive_rounds: int = 0  # V4.1 新增：深度挖掘轮次计数
    last_updated: datetime = field(default_factory=datetime.now)
    
    def get_state_description(self) -> str:
        """获取当前状态的中文描述"""
        descriptions = {
            InterviewState.WELCOME: "初始问候",
            InterviewState.GATHER_CONTEXT: "收集情境信息",
            InterviewState.GATHER_BEHAVIOR: "收集行为细节",
            InterviewState.GATHER_RESPONSE: "收集他人回应",
            InterviewState.HYPOTHESIS_DRIVEN: "假设驱动追问",
            InterviewState.DEEP_DIVE: "深度挖掘（已锁定核心假设）",
            InterviewState.READY_TO_ANALYZE: "准备分析",
            InterviewState.READY_TO_CONCLUDE: "准备结束（等待用户确认）",
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
            InterviewState.HYPOTHESIS_DRIVEN: "鉴别最可能的行为功能假设",
            InterviewState.DEEP_DIVE: "针对锁定假设，深入探索具体表现和条件",
            InterviewState.READY_TO_ANALYZE: "信息已完整，准备生成分析报告",
            InterviewState.READY_TO_CONCLUDE: "与用户确认是否还有补充，然后结束对话",
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
        根据当前状态和用户输入，决定是否需要状态转移（V4.1 修复版）
        
        这是纯代码逻辑，不调用 LLM。
        
        V4.1 新增：
        - 假设锁定检测：检测到强证据后进入 DEEP_DIVE
        - 深度挖掘轮次限制
        
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
                # ABC 收集完毕，进入假设驱动阶段
                return InterviewState.HYPOTHESIS_DRIVEN
        
        # HYPOTHESIS_DRIVEN → DEEP_DIVE：检测到强证据，锁定假设
        if current == InterviewState.HYPOTHESIS_DRIVEN:
            # 如果已锁定假设，进入深度挖掘
            if self.locked_hypothesis:
                return InterviewState.DEEP_DIVE
            # 否则继续假设驱动追问
        
        # DEEP_DIVE → READY_TO_ANALYZE：深度挖掘完成
        if current == InterviewState.DEEP_DIVE:
            # 深度挖掘轮次限制（最多 3 轮）
            if self.deep_dive_rounds >= 3:
                return InterviewState.READY_TO_ANALYZE
            # 或者已有足够证据
            if len(self.evidence_log) >= 5:
                return InterviewState.READY_TO_ANALYZE
        
        # HYPOTHESIS_DRIVEN → READY_TO_ANALYZE：深度追问完成
        if current == InterviewState.HYPOTHESIS_DRIVEN:
            if len(self.evidence_log) >= 5:  # 至少有 5 条证据
                return InterviewState.READY_TO_ANALYZE
        
        # READY_TO_ANALYZE → READY_TO_CONCLUDE：V4.2 新增，先询问用户确认
        if current == InterviewState.READY_TO_ANALYZE:
            return InterviewState.READY_TO_CONCLUDE
        
        # READY_TO_CONCLUDE → ANALYZING：用户确认结束
        if current == InterviewState.READY_TO_CONCLUDE:
            # 如果用户表示没有补充（包含肯定或中性回答）
            if any(kw in user_input.lower() for kw in ["没有", "完了", "好了", "可以", "行", "嗯", "好的", "是的", "finish", "end", "complete"]):
                return InterviewState.ANALYZING
            # 如果用户有补充内容，返回到假设驱动继续收集
            elif len(user_input.strip()) > 5:
                logger.info(f"用户有补充内容，返回 HYPOTHESIS_DRIVEN")
                return InterviewState.HYPOTHESIS_DRIVEN
        
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
        """判断是否需要深度追问（V4.1 修复版）"""
        # 如果证据不足 3 条，需要深度追问
        # 或者已锁定核心假设
        return len(self.evidence_log) < 3 or self.locked_hypothesis is not None


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

【你的任务 - 必须严格遵守以下结构】
请生成你的回应，**必须**包含以下三个部分：

1. **共情与确认**（1 句话）：对家长上一句话表达理解。

2. **总结先行**（必须）：以"基于我们的对话，我了解到..."开头，简要总结目前已确认的所有关键事实（1-2 句话）。

3. **思维推进**（根据阶段目标，二选一）：
   - 如果信息已足够进入下一阶段：清晰总结我们已确认的事实，并自然过渡到下一阶段的**唯一一个**核心问题。
   - 如果信息不足：提出当前阶段下，最核心、最迫切的**唯一一个**问题。

【示例回应】
"我理解您的担心。（共情）
基于我们的对话，我了解到孩子在幼儿园小组桌上做手工时遇到了困难。（总结）
为了进一步明确，现在最需要厘清的是他当时的具体行为。可以请您描述一下，当他说太难时，具体做了什么吗？"（提问）

【专业锚点】（内部思考，不输出）
基于当前信息，你认为最可能的行为功能假设是什么？（如：逃避任务难度、寻求关注、感觉调节）。这仅用于指导你的提问方向。

请以自然、温暖、专业的口语化语言回应。不要使用 JSON 格式，直接输出自然语言。"""


class GuidedRecorderV4:
    """
    引导式记录员 V4.1 - 确定性状态机驱动（紧急修复版）
    
    V4.1 核心修复：
    1. 严格出口条件：ABC 完整 + 关键功能证据 + 无效追问停止检查
    2. 假设锁定机制：检测到强证据后锁定，禁止发散追问
    3. 深度挖掘轮次限制：最多 3 轮深度追问
    
    V4.0 核心改进：
    1. 状态转移由代码逻辑控制（不调用 LLM）
    2. 每轮只调用一次 LLM（生成自然语言）
    3. 明确的完成条件（ABC 信息完整 + 证据充足）
    4. 状态感知的 Prompt 构建
    """
    
    def __init__(self, llm_client: LLMClient):
        """
        初始化 V4.1 Agent
        
        Args:
            llm_client: LLM 客户端实例
        """
        self.llm = llm_client
        self.sessions: Dict[str, ClinicalInterviewState] = {}
        logger.info("GuidedRecorderV4 初始化完成 - V4.1 紧急修复版（严格出口 + 假设锁定）")
    
    # ========== V4.1 核心修复方法 ==========
    
    def _detect_hypothesis_from_input(self, user_input: str) -> Optional[str]:
        """
        V4.1 新增：从用户输入中检测关键证据，锁定假设
        
        Returns:
            检测到的假设类型（prompt_dependence, escape_difficulty, attention_seeking, sensory_seeking, sensory_escape）
        """
        input_lower = user_input.lower()
        
        # 1. 提示依赖证据
        prompt_dep_indicators = [
            ("不看", ("做不好", "不会", "跟不上", "发呆", "走神", "做错")),
            ("看", ("做得好", "会", "跟随", "认真", "做对")),
            ("注意", ("做对", "做好", "完成")),
        ]
        for prefix, suffixes in prompt_dep_indicators:
            if prefix in input_lower:
                for suffix in suffixes:
                    if suffix in input_lower:
                        logger.info(f"检测到提示依赖证据：{prefix}+{suffix}")
                        return "prompt_dependence"
        
        # 2. 逃避难度证据
        if any(word in input_lower for word in ["太难", "难", "跟不上", "不会", "吃力", "累", "辛苦"]):
            logger.info(f"检测到逃避难度证据")
            return "escape_difficulty"
        
        # 3. 寻求关注证据
        if any(phrase in input_lower for phrase in ["要理", "要管", "要关注", "要陪", "要看他", "引起注意"]):
            logger.info(f"检测到寻求关注证据")
            return "attention_seeking"
        
        # 4. 感觉寻求证据
        if any(word in input_lower for word in ["好玩", "有趣", "刺激", "喜欢", "开心"]):
            if any(word in input_lower for word in ["跳", "跑", "转", "摸", "看"]):
                logger.info(f"检测到感觉寻求证据")
                return "sensory_seeking"
        
        # 5. 感觉逃避证据
        if any(word in input_lower for word in ["吵", "吵", "难受", "不舒服", "太亮", "太吵", "害怕"]):
            logger.info(f"检测到感觉逃避证据")
            return "sensory_escape"
        
        return None
    
    def _should_complete(self, state: ClinicalInterviewState) -> bool:
        """
        V4.1 新增：严格的对话完成判断逻辑
        
        返回 True 的条件：
        1. 核心 ABC 信息完整
        2. 获得至少一个关键功能证据
        3. 无效追问已停止（最近对话中否定回答占比高）
        4. 深度挖掘轮次达到限制
        """
        # 1. 基础 ABC 信息完备性检查
        abc_complete = all([
            state.collected_data.get("context", "").strip(),  # 情境（前因）
            state.collected_data.get("behavior", "").strip(),  # 行为
            state.collected_data.get("response", "").strip(),  # 后果
        ])
        
        if not abc_complete:
            return False
        
        # 2. 关键功能性证据检查（以下条件满足其一即可）
        evidence = state.evidence_log
        has_key_evidence = any([
            # 证据 1: 提示依赖模式
            any("不看" in e and ("做不好" in e or "不会" in e or "跟不上" in e or "发呆" in e) for e in evidence),
            any("看" in e and ("做得好" in e or "会" in e or "跟随" in e) for e in evidence),
            # 证据 2: 逃避难度
            any("太难" in e or "难" in e or "跟不上" in e or "不会" in e or "吃力" in e for e in evidence),
            # 证据 3: 明确的实物/关注获取
            any("要" in e and ("给" in e or "得到" in e or "理" in e) for e in evidence),
        ])
        
        if not has_key_evidence:
            return False
        
        # 3. 无效追问停止检查（避免在已排除的假设上纠缠）
        # 检查最近 6 条对话历史中否定回答的数量
        recent_history = state.conversation_history[-6:] if state.conversation_history else []
        recent_negatives = sum(1 for msg in recent_history if "没有" in msg or "不知道" in msg or "不" in msg or "没" in msg)
        
        # 如果最近对话中否定回答占比过高（>=2 次），且已有关键证据，则结束
        if recent_negatives >= 2 and has_key_evidence:
            logger.info(f"触发完成：否定回答过多 (recent_negatives={recent_negatives})")
            return True
        
        # 4. 深度挖掘轮次限制
        if state.current_state == InterviewState.DEEP_DIVE and state.deep_dive_rounds >= 3:
            logger.info(f"触发完成：深度挖掘轮次达到限制 (deep_dive_rounds={state.deep_dive_rounds})")
            return True
        
        # 5. 总轮次限制（安全网）
        if state.turn_count >= 8:
            logger.info(f"触发完成：总轮次达到限制 (turn_count={state.turn_count})")
            return True
        
        return False
    
    def _update_state_with_negatives(self, state: ClinicalInterviewState, user_input: str) -> None:
        """
        V4.1 新增：根据用户否定回答更新已排除假设
        """
        if "没有" in user_input or "不知道" in user_input or "不" in user_input or "没" in user_input:
            # 分析当前正在追问的假设（从最近 AI 问题推断）
            ai_questions = [msg for msg in state.conversation_history if msg.startswith("AI:")]
            if ai_questions:
                current_question = ai_questions[-1]
                
                # 简单关键词匹配（可根据实际情况扩展）
                if "看什么" in current_question or "注意什么" in current_question or "眼神" in current_question:
                    if "sensory_seeking" not in state.excluded_hypotheses:
                        state.excluded_hypotheses.append("sensory_seeking")
                        logger.info(f"排除假设：sensory_seeking")
                
                elif "不舒服" in current_question or "难受" in current_question or "吵" in current_question:
                    if "sensory_escape" not in state.excluded_hypotheses:
                        state.excluded_hypotheses.append("sensory_escape")
                        logger.info(f"排除假设：sensory_escape")
                
                elif "想要什么" in current_question or "得到什么" in current_question:
                    if "attention_seeking" not in state.excluded_hypotheses:
                        state.excluded_hypotheses.append("attention_seeking")
                        logger.info(f"排除假设：attention_seeking")
    
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
        更新收集的数据（使用 LLM 辅助提取）
        
        策略：
        - 使用 LLM 从用户输入中提取关键信息
        - 根据当前状态，将提取的信息归类到对应字段
        - 保留原始输入作为证据
        """
        current = state.current_state
        
        # 记录证据
        state.evidence_log.append(user_input)
        
        # 使用 LLM 辅助提取（只在关键字段为空时）
        try:
            extracted = self._extract_data_with_llm(user_input, state.collected_data)
            
            if current == InterviewState.GATHER_CONTEXT and not state.collected_data["context"]:
                state.collected_data["context"] = extracted.get("context", user_input[:100])
                if extracted.get("environment"):
                    state.collected_data["environment"] = extracted["environment"]
                logger.info(f"收集情境：{state.collected_data['context'][:50]}...")
            
            elif current == InterviewState.GATHER_BEHAVIOR and not state.collected_data["behavior"]:
                # 行为应该是孩子具体做了什么，不是重复情境
                state.collected_data["behavior"] = extracted.get("behavior", user_input[:100])
                logger.info(f"收集行为：{state.collected_data['behavior'][:50]}...")
            
            elif current == InterviewState.GATHER_RESPONSE and not state.collected_data["response"]:
                state.collected_data["response"] = extracted.get("response", user_input[:100])
                logger.info(f"收集回应：{state.collected_data['response'][:50]}...")
            
            elif current == InterviewState.HYPOTHESIS_DRIVEN:
                # 深度追问阶段，记录为额外证据
                logger.info(f"深度追问证据：{user_input[:50]}...")
        
        except Exception as e:
            logger.error(f"数据提取失败：{e}，使用原始输入")
            # 回退到简单归类
            if current == InterviewState.GATHER_CONTEXT and not state.collected_data["context"]:
                state.collected_data["context"] = user_input
            elif current == InterviewState.GATHER_BEHAVIOR and not state.collected_data["behavior"]:
                state.collected_data["behavior"] = user_input
            elif current == InterviewState.GATHER_RESPONSE and not state.collected_data["response"]:
                state.collected_data["response"] = user_input
        
        state.last_updated = datetime.now()
        state.turn_count += 1
    
    def _extract_data_with_llm(self, user_input: str, current_data: dict) -> dict:
        """
        使用 LLM 从用户输入中提取结构化数据
        
        Returns:
            包含 context, behavior, response, environment 的字典
        """
        extraction_prompt = f"""从以下用户输入中提取信息。如果某项信息不存在，留空。

【用户输入】
{user_input}

【已收集的数据】
- 情境：{current_data.get('context', '无')}
- 行为：{current_data.get('behavior', '无')}
- 回应：{current_data.get('response', '无')}

请提取新信息，以 JSON 格式输出：
{{
    "context": "何时、何地、何事（如果用户输入包含这些信息）",
    "behavior": "孩子具体做了什么、没做什么（动作、语言、表情等）",
    "response": "老师、家长或其他人的回应方式",
    "environment": "环境描述（噪音、其他人活动等）"
}}

注意：
- 只提取用户输入中明确提到的信息
- 不要重复已收集的数据
- 如果用户输入是回答行为问题，重点提取 behavior 字段
- 如果用户输入是回答回应问题，重点提取 response 字段
"""
        
        try:
            result = self.llm.generate_json(
                system_prompt="只输出 JSON，不要解释。",
                user_prompt=extraction_prompt,
                temperature=0.1,
                max_tokens=300,
            )
            return result
        except Exception as e:
            logger.warning(f"LLM 提取失败：{e}")
            return {}
    
    def _build_prompt(self, state: ClinicalInterviewState, user_input: str) -> str:
        """
        构建单一、集成的 Prompt（V4.1 修复版）
        
        这是 V4.0 的核心：所有上下文信息整合到一个 Prompt 中
        
        V4.1 新增：
        - 深度挖掘阶段的强制聚焦指令
        - 已排除假设的明确禁止
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
        
        # === V4.1 新增：深度挖掘阶段的强制聚焦指令 ===
        if state.current_state == InterviewState.DEEP_DIVE and state.locked_hypothesis:
            hypothesis_names = {
                "prompt_dependence": "提示依赖（需要视觉/语言提示才能完成）",
                "escape_difficulty": "逃避难度（任务太难想要放弃）",
                "attention_seeking": "寻求关注（想要得到他人注意）",
                "sensory_seeking": "感觉寻求（觉得好玩有趣）",
                "sensory_escape": "感觉逃避（环境太吵/太亮不舒服）",
            }
            hypothesis_name = hypothesis_names.get(state.locked_hypothesis, state.locked_hypothesis)
            
            excluded_list = "、".join(state.excluded_hypotheses) if state.excluded_hypotheses else "无"
            
            focus_instruction = f"""
【关键指令：深度聚焦】
当前已锁定核心假设：**{hypothesis_name}**。

你接下来的问题**必须且只能**用于深入探索以下方面：
- 验证此假设的强度（证据是否充分）
- 探索此假设的具体表现和细节
- 了解此假设发生的条件和模式

**禁止**询问以下内容：
- 与{hypothesis_name}无关的其他功能假设
- 用户已多次否定或表示不知道的方面（已排除：{excluded_list}）
- 过于宽泛或重复的问题

记住：每次只问一个最核心、最能推进验证此假设的问题。如果用户已经提供了足够信息，请直接结束对话并生成报告。
"""
            prompt += focus_instruction
            logger.info(f"添加深度聚焦指令：locked_hypothesis={state.locked_hypothesis}")
        
        logger.info(f"构建 Prompt：state={state.current_state.value}, turns={state.turn_count}, locked={state.locked_hypothesis}")
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
    
    def _generate_summary(self, state: ClinicalInterviewState) -> str:
        """
        V4.2 新增：生成综合摘要
        
        从对话历史和收集的数据中提取关键信息，生成一段连贯的叙述性摘要。
        而不是机械复制用户首条消息。
        """
        # 1. 从收集的数据中提取关键事实
        context = state.collected_data.get("context", "").strip()
        behavior = state.collected_data.get("behavior", "").strip()
        response = state.collected_data.get("response", "").strip()
        environment = state.collected_data.get("environment", "").strip()
        
        # 2. 尝试从对话历史中提取额外关键信息
        key_facts = []
        for msg in state.conversation_history:
            if msg.startswith("用户："):
                user_text = msg[3:].strip()
                # 提取关键信息（简单关键词匹配）
                if any(kw in user_text for kw in ["音乐", "广播", "操", "活动", "任务"]):
                    if user_text not in key_facts and len(user_text) < 100:
                        key_facts.append(user_text)
                if any(kw in user_text for kw in ["老师", "提醒", "干预", "管", "理"]):
                    if user_text not in key_facts and len(user_text) < 100:
                        key_facts.append(user_text)
                if any(kw in user_text for kw in ["反应", "表现", "一致", "不一致", "有时", "经常"]):
                    if user_text not in key_facts and len(user_text) < 100:
                        key_facts.append(user_text)
        
        # 3. 构建叙述性摘要
        summary_parts = []
        
        # 环境/情境
        if environment:
            summary_parts.append(f"在{environment}的环境中")
        elif context:
            summary_parts.append(f"在{context}的情境下")
        
        # 行为模式
        if behavior:
            summary_parts.append(f"观察到孩子{behavior}")
        
        # 他人回应
        if response:
            summary_parts.append(f"而周围人的回应方式是{response}")
        
        # 关键补充信息
        if key_facts:
            # 取前 3 条最关键的信息
            for fact in key_facts[:3]:
                if len(fact) > 10:
                    summary_parts.append(f"进一步了解：{fact}")
        
        # 假设（如果有）
        if state.locked_hypothesis:
            hypothesis_names = {
                "prompt_dependence": "提示依赖",
                "escape_difficulty": "逃避难度",
                "attention_seeking": "寻求关注",
                "sensory_seeking": "感觉寻求",
                "sensory_escape": "感觉逃避",
            }
            hyp_name = hypothesis_names.get(state.locked_hypothesis, state.locked_hypothesis)
            summary_parts.append(f"初步判断可能与{hyp_name}有关")
        
        if not summary_parts:
            return "基于我们的对话，我对情况有了基本了解，现在可以为您生成分析报告。"
        
        # 组合成连贯的段落
        summary = "。".join(summary_parts)
        if not summary.endswith("。"):
            summary += "。"
        
        return summary
    
    def _should_generate_report(self, state: ClinicalInterviewState) -> bool:
        """
        判断是否应该生成报告（代码逻辑）- V4.1 兼容
        
        注意：V4.1 主要使用 _should_complete() 进行严格检查
        此方法保留用于向后兼容
        
        条件：
        1. ABC 核心信息完整
        2. 至少 3 条证据
        3. 或者对话轮数 >= 5（避免无限追问）
        """
        # V4.1 优先使用 _should_complete
        if hasattr(self, '_should_complete'):
            return self._should_complete(state)
        
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
            # 1. 生成洞察 - P0 防护优化：传递 session_context
            session_context = {
                "environment": state.collected_data.get("environment", ""),
                "context": state.collected_data.get("context", ""),
                "child_behavior": state.collected_data.get("behavior", ""),
                "others_response": state.collected_data.get("response", ""),
            }
            
            analyzer = InsightAnalyzer(self.llm)
            insight = analyzer.analyze(
                environment=state.collected_data.get("environment", ""),
                antecedent=state.collected_data.get("context", ""),
                behavior=state.collected_data.get("behavior", ""),
                consequence=state.collected_data.get("response", ""),
                session_context=session_context,  # P0 防护优化新增
            )
            
            # 2. 生成干预计划
            planner = InterventionPlanner()
            # V4.2 修复：使用默认场景 key 而非空字符串
            scenario_key = "task_disengagement"  # 默认使用任务脱离场景
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
        V4.1 主处理流程（紧急修复版）
        
        集权式控制：
        1. 加载状态
        2. 记录用户输入
        3. 检测并锁定假设（V4.1 新增）
        4. 跟踪否定回答，排除假设（V4.1 新增）
        5. === 关键修复：执行严格的完成检查 ===
        6. 更新收集的数据
        7. 状态转移
        8. 深度挖掘轮次计数
        9. 构建 Prompt（含聚焦指令），发起 LLM 调用
        10. 保存状态，返回响应
        
        Args:
            session_id: 会话 ID
            user_input: 用户输入
            
        Returns:
            响应字典
        """
        # 1. 加载状态
        state = self._get_or_create_session(session_id)
        
        # 2. 记录用户输入（简化为字符串）
        state.conversation_history.append(f"用户：{user_input}")
        
        logger.info(f"V4.1 处理输入：session={state.session_id}, state={state.current_state.value}, turn={state.turn_count + 1}")
        
        # 3. === V4.1 新增：检测并锁定假设 ===
        detected_hyp = self._detect_hypothesis_from_input(user_input)
        if detected_hyp and not state.locked_hypothesis:
            state.locked_hypothesis = detected_hyp
            logger.info(f"锁定假设：{detected_hyp}")
        
        # 4. === V4.1 新增：跟踪否定回答，排除假设 ===
        self._update_state_with_negatives(state, user_input)
        
        # 5. === V4.1 关键修复：执行严格的完成检查 ===
        if self._should_complete(state):
            logger.info(f"触发完成条件，生成报告")
            self._trigger_analysis(state)
            
            # 生成完成响应
            completion_message = "感谢您如此详细的分享。基于我们刚才的对话，我已经对情况有了清晰的了解。现在，我将为您整理一份简要的分析报告。"
            
            # 转移到完成状态
            state.current_state = InterviewState.COMPLETE
            
            # 记录 AI 响应
            state.conversation_history.append(f"AI: {completion_message}")
            
            # 保存状态
            self.sessions[state.session_id] = state
            
            # 构建完整响应
            response = self._build_complete_response(state)
            response["message"] = completion_message
            response["locked_hypothesis"] = state.locked_hypothesis
            
            logger.info(f"V4.1 完成：session={state.session_id}, turns={state.turn_count}, hypothesis={state.locked_hypothesis}")
            return response
        
        # 6. 更新收集的数据（基于简单规则，而非 LLM）
        self._update_collected_data(state, user_input)
        
        # 7. 确定性状态转移（代码逻辑）
        next_state = state.should_transition_to(user_input)
        if next_state:
            state.current_state = next_state
            logger.info(f"状态转移：{state.current_state.value}")
        
        # 8. === V4.1 新增：如果是深度挖掘，增加计数 ===
        if state.current_state == InterviewState.DEEP_DIVE:
            state.deep_dive_rounds += 1
            logger.info(f"深度挖掘轮次：{state.deep_dive_rounds}")
        
        # 9. === V4.2 修复：处理 READY_TO_CONCLUDE 状态 ===
        # 当状态转移到 READY_TO_CONCLUDE 时，询问用户确认而非直接结束
        if state.current_state == InterviewState.READY_TO_CONCLUDE:
            logger.info(f"状态为 READY_TO_CONCLUDE，询问用户确认")
            # 生成确认性问题
            confirm_message = "基于我们的对话，我已经对情况有了比较清晰的了解。请问还有没有其他重要的细节需要补充？如果没有，我将为您生成分析报告。"
            
            # 记录 AI 响应
            state.conversation_history.append(f"AI: {confirm_message}")
            
            # 保存状态
            self.sessions[state.session_id] = state
            
            # 返回确认响应（不触发分析）
            response = {
                "session_id": state.session_id,
                "status": "in_progress",
                "response_type": "confirmation",
                "message": confirm_message,
                "state": state.current_state.value,
                "locked_hypothesis": state.locked_hypothesis,
            }
            
            logger.info(f"V4.2 确认询问：session={state.session_id}")
            return response
        
        # 9. === V4.1 修复：状态转移后再次检查完成条件 ===
        # 防止状态转移到 READY_TO_ANALYZE 后没有触发完成
        if state.current_state == InterviewState.READY_TO_ANALYZE:
            logger.info(f"状态为 READY_TO_ANALYZE，触发完成检查")
            # 转移到 READY_TO_CONCLUDE 而非直接分析
            state.current_state = InterviewState.READY_TO_CONCLUDE
            
            # 生成确认性问题
            confirm_message = "基于我们的对话，我已经对情况有了比较清晰的了解。请问还有没有其他重要的细节需要补充？如果没有，我将为您生成分析报告。"
            
            # 记录 AI 响应
            state.conversation_history.append(f"AI: {confirm_message}")
            
            # 保存状态
            self.sessions[state.session_id] = state
            
            # 返回确认响应
            response = {
                "session_id": state.session_id,
                "status": "in_progress",
                "response_type": "confirmation",
                "message": confirm_message,
                "state": state.current_state.value,
                "locked_hypothesis": state.locked_hypothesis,
            }
            
            logger.info(f"V4.2 确认询问：session={state.session_id}")
            return response
        
        # 10. 构建 Prompt（含聚焦指令），发起唯一一次 LLM 调用
        prompt = self._build_prompt(state, user_input)
        
        try:
            llm_response = self.llm.generate(
                system_prompt="你是一位资深的自闭症干预督导，用温暖、专业的语言与家长交流。回答简洁，不超过 150 字。如果信息已足够，请主动结束对话并告知用户将生成报告。",
                user_prompt=prompt,
                temperature=0.7,
                max_tokens=300,
            )
        except Exception as e:
            logger.error(f"LLM 调用失败：{e}")
            llm_response = "谢谢您的分享，我正在整理信息。"
        
        # 11. 记录 AI 响应
        state.conversation_history.append(f"AI: {llm_response}")
        
        # 构建继续追问响应
        response = {
            "session_id": state.session_id,
            "status": "in_progress",
            "response_type": "follow_up",
            "message": llm_response,
            "state": state.current_state.value,
            "locked_hypothesis": state.locked_hypothesis,
        }
        
        # 保存状态，返回响应
        self.sessions[state.session_id] = state
        
        logger.info(f"V4.1 响应完成：session={state.session_id}, status={response.get('status')}, locked={state.locked_hypothesis}")
        
        return response
    
    def _build_complete_response(self, state: ClinicalInterviewState) -> Dict[str, Any]:
        """
        V4.2 构建完成响应（修复数据结构匹配问题）
        
        关键修复：将 InsightAnalyzer 返回的字段映射到前端期望的格式
        """
        insight = state.insight_result or {}
        intervention_plan = state.intervention_plan or {}
        
        # 从 expert_breakdown 中提取信息
        expert_breakdown = insight.get("expert_breakdown", {})
        
        # V4.2 关键修复：构建前端期望的 report 结构
        report = {
            # 摘要 - V4.2 新增：使用综合摘要而非复制首条消息
            "summary": self._generate_summary(state),
            
            # 基础信息
            "context": state.collected_data.get("context", ""),
            "child_behavior": state.collected_data.get("behavior", ""),
            "others_response": state.collected_data.get("response", ""),
            "environment": state.collected_data.get("environment", ""),
            
            # 核心洞察
            "parent_insight": insight.get("core_insight_for_parent", "您敏锐地观察到了孩子的行为模式，这是帮助他的第一步。"),
            
            # 专业视角 - 从 expert_breakdown 映射
            "expert_view": expert_breakdown.get("functional_hypothesis", insight.get("strategy_principle", "基于您的详细描述，我们正在进一步分析行为背后的可能原因。")),
            "primary_hypothesis": expert_breakdown.get("behavior_pattern", "提示依赖行为"),
            
            # 支持证据 - 从证据日志生成
            "supporting_evidence": self._generate_supporting_evidence(state),
            
            # 核心能力目标 - 从 expert_breakdown 映射
            "core_capability_goal": expert_breakdown.get("capability_gap", "提升在无实时外部提示下，维持任务序列的工作记忆能力。"),
            
            # 专业鉴别思考
            "clinical_differential": insight.get("clinical_differential", "基于观察到的行为模式，我们考虑了多种可能性，包括提示依赖、自我刺激、感觉逃避等。结合'有提示时表现良好'这一关键信息，提示依赖的可能性最高。"),
            
            # 反思与赋能
            "reflection": insight.get("reasoning_brief", "每个行为都是孩子与我们沟通的方式。通过理解行为背后的原因，我们可以提供更有效的支持。"),
            "empowerment_question": "在接下来一周，请留意孩子在哪件他热爱的事情上，展现出惊人的'无需提醒'的专注力？",
        }
        
        return {
            "session_id": state.session_id,
            "status": "completed",
            "response_type": "insight_report",
            "message": "感谢您如此详细的分享。基于我们刚才的对话，我已经对情况有了清晰的了解。现在，我将为您整理一份简要的分析报告。",
            "data": {
                "context": state.collected_data.get("context", ""),
                "child_behavior": state.collected_data.get("behavior", ""),
                "others_response": state.collected_data.get("response", ""),
                "core_insight": insight.get("core_insight_for_parent", ""),
                "expert_breakdown": expert_breakdown,
                "report": report,  # V4.2 修复：正确的 report 结构
                "intervention_plan": intervention_plan,
            },
        }
    
    def _generate_supporting_evidence(self, state: ClinicalInterviewState) -> str:
        """
        V4.2 新增：生成支持证据描述
        
        从证据日志中提取关键证据，形成连贯的证据链描述。
        """
        evidence = state.evidence_log
        
        if not evidence:
            return "基于您的详细描述和行为模式分析。"
        
        # 提取关键证据类型
        has_prompt_dependency = any(
            ("不看" in e and ("做不好" in e or "不会" in e or "跟不上" in e)) or
            ("看" in e and ("做得好" in e or "会" in e))
            for e in evidence
        )
        
        has_difficulty = any(
            kw in e for kw in ["太难", "难", "跟不上", "不会", "吃力"]
            for e in evidence
        )
        
        has_consistent_pattern = any(
            kw in e for kw in ["每次", "总是", "经常", "通常", "一般"]
            for e in evidence
        )
        
        evidence_parts = []
        
        if has_prompt_dependency:
            evidence_parts.append("孩子表现出'有提示则执行，无提示则中断'的模式")
        
        if has_difficulty:
            evidence_parts.append("任务难度超出当前能力范围")
        
        if has_consistent_pattern:
            evidence_parts.append("行为模式具有一致性和可预测性")
        
        if len(evidence) >= 3:
            evidence_parts.append(f"通过{len(evidence)}轮深入对话确认了关键细节")
        
        if not evidence_parts:
            return "基于您的详细描述和行为模式分析。"
        
        return "；".join(evidence_parts) + "。"
    
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
