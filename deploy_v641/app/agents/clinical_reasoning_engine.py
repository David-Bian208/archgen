"""
临床推理引擎 V4.6.0 - 知识配置工程化版
从"规则驱动评估"升级为"假设驱动推理"

核心能力：
1. 动态假设生成：基于证据并行生成多层级假设
2. 贝叶斯信念更新：每条新证据更新所有相关假设的置信度
3. 主动鉴别提问：选择能最大程度降低不确定性的问题
4. 叙事性报告生成：基于推理过程构建整合性解释

V4.6.0 新增（P1 知识配置工程化）：
1. INTENT_MAPPING 迁移到 JSON 文件 (app/knowledge/intent_keywords.json)
2. 支持正则表达式匹配
3. 知识与代码解耦，便于领域专家维护

V4.5.12 已实现：
1. 首句意图检测：关键词→假设直接映射
2. 矛盾证据识别："都会做"等直接排除提示依赖
3. 首问准确率目标：>90%
"""

import json
import logging
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

from app.llm.base import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class Hypothesis:
    """单个假设的置信度状态"""
    id: str
    name: str
    description: str
    prior_probability: float = 0.5
    current_confidence: float = 0.5
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)
    evidence_rules: Dict[str, List[str]] = field(default_factory=dict)
    
    def update_confidence(self, new_confidence: float) -> None:
        """更新置信度（限制在 0-1 范围）"""
        self.current_confidence = min(1.0, max(0.0, new_confidence))
    
    def add_evidence(self, evidence: Dict[str, Any]) -> None:
        """添加证据"""
        self.evidence.append(evidence)


class HypothesisNetwork:
    """假设网络加载与管理"""
    
    def __init__(self, network_path: str):
        self.path = Path(network_path)
        self.data = {}
        self.hypotheses: Dict[str, Hypothesis] = {}
        self.load()
        logger.info(f"HypothesisNetwork 加载完成：{len(self.hypotheses)} 个假设")
    
    def load(self) -> None:
        """加载假设网络"""
        if not self.path.exists():
            logger.error(f"假设网络文件不存在：{self.path}")
            return
        
        with open(self.path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        
        # 构建假设对象
        for layer_key, layer_data in self.data.get("hypothesis_layers", {}).items():
            for hyp in layer_data.get("hypotheses", []):
                self.hypotheses[hyp["id"]] = Hypothesis(
                    id=hyp["id"],
                    name=hyp["name"],
                    description=hyp.get("description", ""),
                    prior_probability=hyp.get("prior_probability", 0.5),
                    current_confidence=hyp.get("prior_probability", 0.5),
                    parent=hyp.get("parent"),
                    children=hyp.get("children", []),
                    evidence_rules=hyp.get("evidence_rules", {}),
                )
    
    def get_hypothesis(self, hyp_id: str) -> Optional[Hypothesis]:
        """获取假设对象"""
        return self.hypotheses.get(hyp_id)
    
    def get_discriminating_questions(self) -> dict:
        """获取鉴别性问题"""
        return self.data.get("discriminating_questions", {})
    
    def get_convergence_rules(self) -> dict:
        """获取收敛规则"""
        return self.data.get("convergence_rules", {})


class ClinicalReasoningEngine:
    """
    临床推理引擎 V4.5
    
    核心方法：
    1. update_beliefs(): 根据新证据更新所有假设的置信度
    2. decide_next_question(): 选择能最大程度降低不确定性的问题
    3. generate_narrative(): 基于推理过程生成整合性报告
    """
    
    # ========== V4.5.12 P1-02: 用户意图识别映射表 ==========
    def __init__(self, llm_client: LLMClient, network_path: str):
        self.llm = llm_client
        self.network = HypothesisNetwork(network_path)
        self.intent_detected_hypotheses = set()  # V4.5.12 新增：跟踪意图检测的假设
        self.intent_mapping = self._load_intent_mapping()  # V4.6.0: 从 JSON 加载
        self._reset_hypotheses()  # V4.5.12 新增：重置所有假设到先验概率
        logger.info("ClinicalReasoningEngine V4.6.0 初始化完成（知识配置工程化）")
    
    def _load_intent_mapping(self) -> dict:
        """V4.6.0 新增：从 JSON 文件加载意图映射表"""
        intent_file = Path(__file__).parent.parent / "knowledge" / "intent_keywords.json"
        
        try:
            with open(intent_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 将 JSON 格式转换为字典：keyword -> hypothesis_id
            mapping = {}
            for hyp_id, keywords in data.get("intent_mapping", {}).items():
                for keyword in keywords:
                    mapping[keyword] = hyp_id
            
            logger.info(f"✅ 意图映射表加载成功：{len(mapping)} 个关键词，来自 {intent_file}")
            return mapping
        
        except Exception as e:
            logger.error(f"❌ 意图映射表加载失败：{e}")
            logger.warning("⚠️ 使用空映射表，意图识别将失效")
            return {}
    def _reset_hypotheses(self):
        """V4.5.12 新增：重置所有假设到先验概率（避免 H_WORKING_MEMORY 默认 1.0）"""
        for hyp in self.network.hypotheses.values():
            hyp.current_confidence = hyp.prior_probability
        self.intent_detected_hypotheses = set()  # 清空意图检测记录
        logger.info("🔄 假设置信度已重置为先验概率")
    
    def detect_user_intent(self, user_input: str) -> Optional[str]:
        """
        V4.6.0 修复：检测用户首句意图，直接提升相关假设置信度
        
        支持两种匹配模式：
        1. 精确关键词匹配（如"太难了"）
        2. 正则表达式匹配（如"不看.*就不会"）
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            检测到的假设 ID，如果没有匹配则返回 None
        """
        intent_mapping = self.intent_mapping  # V4.6.0: 使用实例变量
        
        logger.info(f"🔍 意图检测：输入='{user_input[:50]}...', 映射表大小={len(intent_mapping)}")
        
        detected_hyps = []
        matched_keywords = []
        
        for keyword, hyp_id in intent_mapping.items():
            matched = False
            # 正则表达式匹配（包含.*的模式）
            if ".*" in keyword:
                if re.search(keyword, user_input):
                    matched = True
                    matched_keywords.append((keyword, hyp_id))
            # 精确关键词匹配
            elif keyword in user_input:
                matched = True
                matched_keywords.append((keyword, hyp_id))
            
            if matched:
                hyp = self.network.get_hypothesis(hyp_id)
                if hyp:
                    old_conf = hyp.current_confidence
                    hyp.update_confidence(0.9)
                    self.intent_detected_hypotheses.add(hyp_id)
                    logger.info(f"🎯 意图识别：'{keyword}' → {hyp_id} (confidence: {old_conf:.2f} → 0.9)")
                    detected_hyps.append(hyp_id)
                    
                    # 矛盾证据处理
                    if keyword in ["都会做", "不需要帮助", "自己能做", "其实都会", "能做好", "已经会"]:
                        prompt_dep = self.network.get_hypothesis("prompt_dependence")
                        if prompt_dep:
                            prompt_dep.update_confidence(0.1)
                            logger.info(f"🔴 矛盾证据：'{keyword}' → prompt_dependence 置信度降至 0.1")
        
        if matched_keywords:
            logger.info(f"✅ 匹配到关键词：{matched_keywords}")
        else:
            logger.info(f"⚠️ 未匹配到关键词")
        
        return detected_hyps[0] if detected_hyps else None
    
    def _find_related_hypotheses(self, assertion: dict) -> List[str]:
        """找到受这个证据影响的所有假设"""
        hyp_id = assertion.get("hypothesis", "")
        related = [hyp_id]
        
        # 添加父假设和子假设
        hyp = self.network.get_hypothesis(hyp_id)
        if hyp:
            if hyp.parent:
                related.append(hyp.parent)
            related.extend(hyp.children)
        
        return list(set(related))
        self.intent_detected_hypotheses = set()  # 清空意图检测记录
        logger.info("🔄 假设置信度已重置为先验概率")
    
    def detect_user_intent(self, user_input: str) -> Optional[str]:
        """
        V4.6.0 修复：检测用户首句意图，直接提升相关假设置信度
        
        支持两种匹配模式：
        1. 精确关键词匹配（如"太难了"）
        2. 正则表达式匹配（如"不看.*就不会"）
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            检测到的假设 ID，如果没有匹配则返回 None
        """
        intent_mapping = self.intent_mapping  # V4.6.0: 使用实例变量
        
        logger.info(f"🔍 意图检测：输入='{user_input[:50]}...', 映射表大小={len(intent_mapping)}")
        
        detected_hyps = []
        matched_keywords = []
        
        for keyword, hyp_id in intent_mapping.items():
            matched = False
            # 正则表达式匹配（包含.*的模式）
            if ".*" in keyword:
                if re.search(keyword, user_input):
                    matched = True
                    matched_keywords.append((keyword, hyp_id))
            # 精确关键词匹配
            elif keyword in user_input:
                matched = True
                matched_keywords.append((keyword, hyp_id))
            
            if matched:
                hyp = self.network.get_hypothesis(hyp_id)
                if hyp:
                    old_conf = hyp.current_confidence
                    hyp.update_confidence(0.9)
                    self.intent_detected_hypotheses.add(hyp_id)
                    logger.info(f"🎯 意图识别：'{keyword}' → {hyp_id} (confidence: {old_conf:.2f} → 0.9)")
                    detected_hyps.append(hyp_id)
                    
                    # 矛盾证据处理：降低提示依赖
                    if keyword in ["都会做", "不需要帮助", "自己能做", "其实都会", "能做好", "已经会"]:
                        prompt_dep = self.network.get_hypothesis("prompt_dependence")
                        if prompt_dep:
                            prompt_dep.update_confidence(0.1)
                            logger.info(f"🔴 矛盾证据：'{keyword}' → prompt_dependence 置信度降至 0.1")
                    
                    # 提示依赖检测时，同时抑制 H_WORKING_MEMORY（避免覆盖）
                    if hyp_id == "prompt_dependence":
                        working_mem = self.network.get_hypothesis("H_WORKING_MEMORY")
                        if working_mem:
                            working_mem.update_confidence(0.1)
                            logger.info(f"🔴 提示依赖检测：H_WORKING_MEMORY 置信度降至 0.1")
                    
                    # 实物获取检测时，抑制提示依赖和工作记忆
                    if hyp_id == "tangible_access":
                        prompt_dep = self.network.get_hypothesis("prompt_dependence")
                        if prompt_dep:
                            prompt_dep.update_confidence(0.1)
                            logger.info(f"🔴 实物获取检测：prompt_dependence 置信度降至 0.1")
                        working_mem = self.network.get_hypothesis("H_WORKING_MEMORY")
                        if working_mem:
                            working_mem.update_confidence(0.1)
                            logger.info(f"🔴 实物获取检测：H_WORKING_MEMORY 置信度降至 0.1")
                    
                    # 寻求关注检测时，抑制工作记忆
                    if hyp_id == "attention_seeking":
                        working_mem = self.network.get_hypothesis("H_WORKING_MEMORY")
                        if working_mem:
                            working_mem.update_confidence(0.1)
                            logger.info(f"🔴 寻求关注检测：H_WORKING_MEMORY 置信度降至 0.1")
        
        if matched_keywords:
            logger.info(f"✅ 匹配到关键词：{matched_keywords}")
        else:
            logger.info(f"⚠️ 未匹配到关键词")
        
        return detected_hyps[0] if detected_hyps else None
    
    def update_beliefs(self, user_input: str, filled_data: dict) -> Dict[str, float]:
        """
        核心：根据新证据，更新所有相关假设的置信度
        
        贝叶斯更新逻辑：
        P(H|E) = P(E|H) * P(H) / P(E)
        
        简化实现：
        - 支持证据：confidence += strength * (1 - confidence)
        - 反对证据：confidence -= strength * confidence
        """
        # 1. 从用户输入和已填数据中提取"证据断言"
        evidence_assertions = self._extract_evidence_assertions(user_input, filled_data)
        
        # 2. 对每个证据，更新相关假设（V4.5.12 修复：增加类型检查）
        for assertion in evidence_assertions:
            # V4.5.12 修复：确保 assertion 是字典
            if not isinstance(assertion, dict):
                logger.warning(f"⚠️ 证据断言类型错误：{type(assertion)}，跳过")
                continue
            
            affected_hypotheses = self._find_related_hypotheses(assertion)
            
            for hyp_id in affected_hypotheses:
                hyp = self.network.get_hypothesis(hyp_id)
                if not hyp:
                    continue
                
                # V4.5.12 修复：保护意图检测的高置信度假设（>=0.9）
                if hyp.current_confidence >= 0.9 and assertion.get("type") == "supporting":
                    logger.info(f"🛡️ 保护意图检测结果：{hyp_id} 置信度={hyp.current_confidence:.2f}，跳过支持证据更新")
                    continue
                
                # V4.5.18 修复：当有意图检测时，抑制所有非意图假设的置信度提升
                if self.intent_detected_hypotheses and hyp_id not in self.intent_detected_hypotheses:
                    if assertion.get("type") == "supporting":
                        # 非意图假设的支持证据，一律抑制（无论当前置信度）
                        logger.info(f"🚫 抑制非意图假设：{hyp_id} 置信度={hyp.current_confidence:.2f}，跳过支持证据更新")
                        continue
                
                # V4.5.18 新增：置信度限制在 [0.0, 1.0]
                old_confidence = hyp.current_confidence
                
                # 3. 计算证据强度
                strength = self._calculate_evidence_strength(assertion, hyp)
                
                # 4. 贝叶斯更新
                old_confidence = hyp.current_confidence
                assertion_type = assertion.get("type", "unknown")
                if assertion_type == "supporting":
                    # 支持证据：向 1.0 靠近
                    new_confidence = old_confidence + strength * (1 - old_confidence)
                else:
                    # 反对证据：向 0.0 靠近
                    new_confidence = old_confidence - strength * old_confidence
                
                # V4.5.15 修复：限制置信度在 [0.0, 1.0] 范围内
                new_confidence = max(0.0, min(1.0, new_confidence))
                
                hyp.update_confidence(new_confidence)
                hyp.add_evidence(assertion)
                
                logger.info(f"假设更新：{hyp_id} {old_confidence:.2f} → {new_confidence:.2f} ({assertion_type}, strength={strength:.2f})")
        
        # 返回所有假设的当前置信度
        return {hyp_id: hyp.current_confidence for hyp_id, hyp in self.network.hypotheses.items()}
    
    def _extract_evidence_assertions(self, user_input: str, filled_data: dict) -> List[Dict[str, Any]]:
        """
        从用户输入中提取证据断言
        
        使用 LLM 识别用户输入中包含的证据类型
        """
        extraction_prompt = f"""从用户输入和已填数据中，提取能支持或反对临床假设的证据断言。

【用户输入】
{user_input}

【已填数据】
{json.dumps(filled_data, ensure_ascii=False, indent=2)}

【证据类型说明】
- supporting: 支持某个假设的证据
- contradicting: 反对某个假设的证据

【可能的证据模式】
- "有提示则执行，无提示则中断" → 支持 H_WORKING_MEMORY
- "说太难了"、"不会做" → 支持 H_ESCAPE_DIFFICULTY
- "捂耳朵"、"环境嘈杂" → 支持 H_ESCAPE_SENSORY
- "安静环境也发生" → 反对 H_ESCAPE_SENSORY
- "无需提示也能完成" → 反对 H_WORKING_MEMORY

请以 JSON 数组格式输出证据断言：
[
    {{"type": "supporting", "hypothesis": "H_WORKING_MEMORY", "evidence_text": "有提示则执行，无提示则中断", "strength": 0.8}},
    {{"type": "contradicting", "hypothesis": "H_ESCAPE_SENSORY", "evidence_text": "安静环境也发生", "strength": 0.6}}
]

如果没有可提取的证据，返回空数组 []。
"""
        
        try:
            result = self.llm.generate_json(
                system_prompt="只输出 JSON 数组，不要解释。",
                user_prompt=extraction_prompt,
                temperature=0.1,
                max_tokens=500,
            )
            
            return result if isinstance(result, list) else []
            
        except Exception as e:
            logger.warning(f"证据提取失败：{e}")
            return []
    
    def _find_related_hypotheses(self, assertion: dict) -> List[str]:
        """找到受这个证据影响的所有假设"""
        hyp_id = assertion.get("hypothesis", "")
        related = [hyp_id]
        
        # 添加父假设和子假设
        hyp = self.network.get_hypothesis(hyp_id)
        if hyp:
            if hyp.parent:
                related.append(hyp.parent)
            related.extend(hyp.children)
        
        return list(set(related))
    
    def _calculate_evidence_strength(self, assertion: dict, hypothesis: Hypothesis) -> float:
        """
        计算证据强度 (0-1)
        
        考虑因素：
        1. 证据与假设规则匹配度
        2. 证据来源可靠性
        3. 当前置信度（高置信度假设需要更强证据才能改变）
        """
        # 基础强度（来自 LLM 提取）
        base_strength = assertion.get("strength", 0.5)
        
        # 检查证据是否在假设的规则中
        evidence_text = assertion.get("evidence_text", "")
        rule_type = "supporting" if assertion["type"] == "supporting" else "contradicting"
        
        if rule_type in hypothesis.evidence_rules:
            rules = hypothesis.evidence_rules[rule_type]
            if any(rule in evidence_text for rule in rules):
                # 证据匹配规则，强度 +0.2
                base_strength = min(1.0, base_strength + 0.2)
        
        # 当前置信度调节（高置信度假设更难改变）
        confidence_factor = 1.0 - (hypothesis.current_confidence - 0.5) * 0.5
        
        return base_strength * confidence_factor
    
    def decide_next_question(self, filled_data: dict, current_stage: str, asked_fields: dict = None, conversation_history: list = None) -> Dict[str, Any]:
        """
        决定下一个问题（V4.5.11 假设驱动动态提问版）
        
        核心逻辑：
        1. 检测用户输入是否强烈指向某一假设 → 直接追问该假设的关键问题
        2. 否则：选择能最大程度降低"最不确定关键假设"的不确定性的问题
        3. 强制尊重 asked_fields，避免重复提问
        4. 安全出口：循环超过 3 轮且有足够基础信息时，强制生成报告
        
        V4.5.11 新增：
        - 假设驱动的动态提问策略
        - 安全出口机制
        - 强制尊重已问字段（1 次警告，2 次跳过）
        """
        if asked_fields is None:
            asked_fields = {}
        if conversation_history is None:
            conversation_history = []
        
        logger.info(f"🔍 decide_next_question: asked_fields={asked_fields}, filled_data={list(filled_data.keys())}")
        
        # === V4.5.12 新增：意图检测（优先于其他逻辑）===
        # 如果是首轮对话（filled_data 为空或很少），检测用户意图
        if len(filled_data) <= 1 and conversation_history:
            # 获取用户首句输入
            first_user_input = None
            for msg in conversation_history:
                if msg.get("role") == "user":
                    first_user_input = msg.get("text", "")
                    break
            
            if first_user_input:
                detected_intent = self.detect_user_intent(first_user_input)
                if detected_intent:
                    logger.info(f"✅ 首轮意图检测：{detected_intent}")
        
        # === V4.5.11 新增：安全出口检查 ===
        # 基础字段：antecedent, behavior_detail, immediate_consequence, child_age
        basic_fields = ["antecedent", "behavior_detail", "immediate_consequence", "child_age"]
        basic_filled = sum(1 for f in basic_fields if filled_data.get(f))
        
        # 计算最大重复提问次数
        max_asked_count = max(asked_fields.values()) if asked_fields else 0
        
        # 安全出口：基础字段已填充 3 个以上 + 某问题问过 2 次以上 → 强制结束
        if basic_filled >= 3 and max_asked_count >= 2:
            logger.warning(f"⚠️ 安全出口触发：基础字段={basic_filled}/4, 最大重复={max_asked_count}，强制生成报告")
            return {"type": "GENERATE_REPORT", "reason": "safety_exit"}
        
        # === V4.5.12 增强：意图检测优先 ===
        # 优先选择意图检测的假设（不管置信度，因为可能被 LLM 覆盖）
        if self.intent_detected_hypotheses:
            # 从意图检测的假设中选择置信度最高的
            intent_hyps_with_conf = [
                (hid, self.network.hypotheses[hid].current_confidence)
                for hid in self.intent_detected_hypotheses
                if self.network.hypotheses.get(hid)
            ]
            if intent_hyps_with_conf:
                intent_hyp_id, intent_conf = max(intent_hyps_with_conf, key=lambda x: x[1])
                logger.info(f"🎯 意图检测优先：{intent_hyp_id} (confidence={intent_conf:.2f}, intent_detected={True})")
                
                specific_question = self._find_hypothesis_specific_question(intent_hyp_id, filled_data, asked_fields)
                if specific_question:
                    logger.info(f"意图驱动提问：{intent_hyp_id} → {specific_question}")
                    return {
                        "type": "ASK_FIELD",
                        "field_id": specific_question,
                        "probing_hypothesis": intent_hyp_id,
                        "reasoning": f"意图检测{intent_hyp_id}的特异性鉴别问题",
                        "source": "intent_driven",
                    }
        
        # === V4.5.12 P1-01: 多假设并行追踪 ===
        # 收集所有置信度在 0.3-0.9 之间的不确定假设
        uncertain_hypotheses = [
            (hid, h.current_confidence)
            for hid, h in self.network.hypotheses.items()
            if 0.3 <= h.current_confidence < 0.9
        ]
        
        if len(uncertain_hypotheses) >= 2:
            # 有 2 个以上不确定假设，选择 top 2-3 个
            uncertain_hypotheses.sort(key=lambda x: x[1], reverse=True)
            top_hypotheses = uncertain_hypotheses[:3]
            top_hyp_ids = [hid for hid, _ in top_hypotheses]
            
            logger.info(f"🔀 多假设并行追踪：{top_hyp_ids} (confidences={[f'{c:.2f}' for _, c in top_hypotheses]})")
            
            # 尝试找到能同时区分多个假设的问题
            discriminating_questions = self.network.get_discriminating_questions()
            for q_key, q_data in discriminating_questions.items():
                # 检查这个问题是否涉及多个 top 假设
                q_hyps = q_key.replace("_vs_", " ").replace("_", " ").split()
                matching_hyps = [h for h in top_hyp_ids if h in q_key or any(h in part for part in q_key.split("_vs_"))]
                
                if len(matching_hyps) >= 1:
                    field_mapping = q_data.get("field_mapping")
                    if field_mapping and field_mapping not in filled_data and asked_fields.get(field_mapping, 0) < 2:
                        logger.info(f"🎯 多假设鉴别问题：{field_mapping} (区分 {matching_hyps})")
                        return {
                            "type": "ASK_FIELD",
                            "field_id": field_mapping,
                            "probing_hypothesis": matching_hyps[0],
                            "reasoning": f"区分{matching_hyps}的鉴别问题",
                            "source": "multi_hypothesis",
                        }
            
            # 如果没有多假设问题，选择置信度最高的假设的特异性问题
            best_hyp_id, best_conf = top_hypotheses[0]
            logger.info(f"🎯 降级到单假设：{best_hyp_id} (confidence={best_conf:.2f})")
        
        # === V4.5.11 新增：假设驱动的动态提问 ===
        # 检测是否有假设置信度 > 0.8（强烈指向）
        strong_hypotheses = [(hid, h.current_confidence) for hid, h in self.network.hypotheses.items() if h.current_confidence > 0.8]
        
        if strong_hypotheses:
            # 有强烈指向的假设，直接追问该假设的关键鉴别问题
            strong_hyp_id, strong_conf = max(strong_hypotheses, key=lambda x: x[1])
            logger.info(f"🎯 检测到强假设：{strong_hyp_id} (confidence={strong_conf:.2f})，切换到假设驱动提问")
            
            # 获取该假设的特异性问题
            specific_question = self._find_hypothesis_specific_question(strong_hyp_id, filled_data, asked_fields)
            if specific_question:
                logger.info(f"假设驱动提问：{strong_hyp_id} → {specific_question}")
                return {
                    "type": "ASK_FIELD",
                    "field_id": specific_question,
                    "probing_hypothesis": strong_hyp_id,
                    "reasoning": f"强假设{strong_hyp_id}的特异性鉴别问题",
                    "source": "hypothesis_driven",
                }
        
        # === 标准流程：鉴别性问题 ===
        # 1. 找出当前置信度在 0.3-0.7 之间的关键假设（最不确定）
        key_hypotheses = []
        for hyp_id, hyp in self.network.hypotheses.items():
            if 0.3 < hyp.current_confidence < 0.7:
                if self._is_hypothesis_relevant(hyp_id, filled_data):
                    key_hypotheses.append((hyp_id, hyp.current_confidence))
        
        # 2. 为每个不确定假设，找到最佳鉴别问题
        discriminating_questions = self.network.get_discriminating_questions()
        candidate_questions = []
        
        for hyp_id, confidence in key_hypotheses:
            best_question = self._find_best_discriminating_question(hyp_id, discriminating_questions, filled_data, asked_fields)
            if best_question:
                # V4.5.18 修复：只允许问 1 次，避免重复提问
                asked_count = asked_fields.get(best_question, 0)
                if asked_count >= 1:
                    logger.warning(f"⚠️ 字段{best_question}已问过{asked_count}次，强制跳过")
                    continue
                
                # 计算信息增益
                uncertainty = 1.0 - abs(confidence - 0.5) * 2
                candidate_questions.append((hyp_id, best_question, uncertainty, asked_count))
        
        # 3. 选择信息增益最大的问题（优先选择未问过的）
        if candidate_questions:
            # 排序：先按 asked_count 升序（未问过的优先），再按 uncertainty 降序
            candidate_questions.sort(key=lambda x: (x[3], -x[2]))
            next_hyp, next_field_id, _, _ = candidate_questions[0]
            
            logger.info(f"选择鉴别问题：{next_hyp} → {next_field_id}")
            return {
                "type": "ASK_FIELD",
                "field_id": next_field_id,
                "probing_hypothesis": next_hyp,
                "reasoning": f"为了区分{next_hyp}与其他竞争假设",
            }
        
        # 4. 无可用鉴别问题 → 强制结束
        if key_hypotheses:
            logger.warning("⚠️ 所有鉴别问题都已问过或无可用候选，强制结束")
            return {"type": "GENERATE_REPORT", "reason": "no_more_questions"}
        
        # 5. 假设已收敛
        if self._hypotheses_converged():
            logger.info("假设已收敛，可以生成报告")
            return {"type": "GENERATE_REPORT"}
        
        # 6. 降级到工作流
        logger.info("降级到 V4.3 工作流")
        return {"type": "FALLBACK_TO_WORKFLOW"}
    
    def _is_hypothesis_relevant(self, hyp_id: str, filled_data: dict) -> bool:
        """判断假设是否与当前已填数据相关"""
        # 简化实现：如果已有相关字段填充，则认为相关
        hyp = self.network.get_hypothesis(hyp_id)
        if not hyp:
            return False
        
        # 检查证据规则中的关键词是否出现在已填数据中
        all_text = " ".join(str(v) for v in filled_data.values())
        
        for rule_type in ["supporting", "contradicting"]:
            if rule_type in hyp.evidence_rules:
                if any(kw in all_text for kw in hyp.evidence_rules[rule_type]):
                    return True
        
        return True  # 默认认为相关
    
    def _find_best_discriminating_question(self, hyp_id: str, questions: dict, filled_data: dict, asked_fields: dict = None) -> Optional[str]:
        """为假设找到最佳鉴别问题（V4.5.18 修复版 - 只允许问 1 次）"""
        if asked_fields is None:
            asked_fields = {}
        
        # 查找包含这个假设的鉴别问题
        for q_key, q_data in questions.items():
            if hyp_id in q_key:
                field_mapping = q_data.get("field_mapping")
                # 检查这个字段是否已填充
                if field_mapping and field_mapping in filled_data and filled_data[field_mapping]:
                    continue  # 已填充，跳过
                # V4.5.18 修复：检查这个字段是否已问过 1 次
                if asked_fields.get(field_mapping, 0) >= 1:
                    logger.debug(f"字段{field_mapping}已问过{asked_fields.get(field_mapping)}次，跳过")
                    continue
                return field_mapping
        
        return None
    
    def _find_hypothesis_specific_question(self, hyp_id: str, filled_data: dict, asked_fields: dict = None) -> Optional[str]:
        """
        V4.5.11 新增：为强假设找到特异性鉴别问题
        
        策略：
        1. 优先选择 primary_hypothesis 完全匹配的问题
        2. 其次选择假设 ID 在问题名中的问题
        3. 跳过已填充或已问过 2 次的字段
        """
        if asked_fields is None:
            asked_fields = {}
        
        # 获取鉴别性问题定义
        discriminating_questions = self.network.get_discriminating_questions()
        
        # 第一轮：查找 primary_hypothesis 完全匹配的问题
        for q_key, q_data in discriminating_questions.items():
            if q_data.get("primary_hypothesis") == hyp_id:
                field_mapping = q_data.get("field_mapping")
                
                if not field_mapping:
                    continue
                
                # 跳过已填充的字段
                if field_mapping in filled_data and filled_data[field_mapping]:
                    continue
                
                # V4.5.18 修复：跳过已问过 1 次的字段
                if asked_fields.get(field_mapping, 0) >= 1:
                    logger.debug(f"特异性问题{field_mapping}已问过{asked_fields.get(field_mapping)}次，跳过")
                    continue
                
                # 找到 primary_hypothesis 匹配的字段
                logger.info(f"找到{hyp_id}的特异性问题（primary 匹配）：{field_mapping}")
                return field_mapping
        
        # 第二轮：查找假设 ID 在问题名中的问题
        for q_key, q_data in discriminating_questions.items():
            if hyp_id in q_key:
                field_mapping = q_data.get("field_mapping")
                
                if not field_mapping:
                    continue
                
                # 跳过已填充的字段
                if field_mapping in filled_data and filled_data[field_mapping]:
                    continue
                
                # V4.5.18 修复：跳过已问过 1 次的字段
                if asked_fields.get(field_mapping, 0) >= 1:
                    logger.debug(f"特异性问题{field_mapping}已问过{asked_fields.get(field_mapping)}次，跳过")
                    continue
                
                # 找到名称匹配的字段
                logger.info(f"找到{hyp_id}的特异性问题（名称匹配）：{field_mapping}")
                return field_mapping
        
        # 如果没有特异性问题，返回 None
        logger.warning(f"未找到{hyp_id}的特异性问题，返回 None")
        return None
    
    def _hypotheses_converged(self) -> bool:
        """检查所有关键假设是否已收敛"""
        rules = self.network.get_convergence_rules()
        high_threshold = rules.get("high_confidence_threshold", 0.75)
        low_threshold = rules.get("low_confidence_threshold", 0.25)
        
        for hyp in self.network.hypotheses.values():
            # 如果有假设的置信度在阈值之间，且证据不足，则未收敛
            if low_threshold < hyp.current_confidence < high_threshold:
                if len(hyp.evidence) < rules.get("evidence_minimum", 3):
                    return False
        
        return True
    
    def generate_narrative(self, filled_data: dict) -> Dict[str, str]:
        """
        生成基于推理过程的叙事性报告
        
        核心：不是模块拼接，而是有因果逻辑的整合性解释
        """
        # 1. 获取收敛的假设
        rules = self.network.get_convergence_rules()
        high_threshold = rules.get("high_confidence_threshold", 0.75)
        
        high_confidence_hyps = [
            (hyp_id, hyp) 
            for hyp_id, hyp in self.network.hypotheses.items()
            if hyp.current_confidence >= high_threshold
        ]
        
        # 2. 使用 LLM 生成整合性叙事
        narrative_prompt = self._build_narrative_prompt(high_confidence_hyps, filled_data)
        
        try:
            result = self.llm.generate_json(
                system_prompt="你是一位善于沟通的 BCBA 督导。用温暖、支持但有专业深度的语言生成报告。",
                user_prompt=narrative_prompt,
                temperature=0.3,
                max_tokens=1000,
            )
            
            return result
            
        except Exception as e:
            logger.error(f"叙事生成失败：{e}")
            return self._get_fallback_narrative(high_confidence_hyps)
    
    def _build_narrative_prompt(self, high_confidence_hyps: List[Tuple[str, Hypothesis]], filled_data: dict) -> str:
        """构建叙事生成 Prompt"""
        # 整理假设信息
        hyp_summary = "\n".join([
            f"- {hyp.name}: 置信度={hyp.current_confidence:.2f}, 证据={len(hyp.evidence)}条"
            for _, hyp in high_confidence_hyps
        ])
        
        # 整理证据
        evidence_summary = []
        for _, hyp in high_confidence_hyps:
            for ev in hyp.evidence:
                evidence_summary.append(f"- {hyp.name}: {ev.get('evidence_text', '')} ({ev.get('type', '')})")
        
        return f"""基于以下临床推理结果，生成一份整合性的行为分析报告。

【高置信度假设】
{hyp_summary}

【支持证据】
{chr(10).join(evidence_summary)}

【已填数据】
{json.dumps(filled_data, ensure_ascii=False, indent=2)}

【报告要求】
请按照以下结构组织报告，确保各部分之间有因果逻辑连接：

1. **观察到的模式**：简要描述行为表现的关键特征
2. **最可能的解释**：基于高置信度假设，给出整合性归因（不是简单罗列）
3. **需考虑的深层因素**：指出可能的能力缺口（工作记忆/注意/感觉处理等）
4. **我们的判断依据**：说明为什么支持这个判断，排除了哪些其他可能性

请以 JSON 格式输出：
{{
    "observed_pattern": "观察到的行为模式描述",
    "primary_attribution": "最可能的整合性归因",
    "capability_gaps": "深层能力缺口分析",
    "reasoning_basis": "判断依据和排除逻辑",
    "narrative_summary": "整合以上所有内容的连贯叙事（200-300 字）"
}}
"""
    
    def _get_fallback_narrative(self, high_confidence_hyps: List[Tuple[str, Hypothesis]]) -> Dict[str, str]:
        """降级叙事方案"""
        if not high_confidence_hyps:
            return {
                "observed_pattern": "观察到的行为模式需要进一步评估",
                "primary_attribution": "需要更多信息进行判断",
                "capability_gaps": "待评估",
                "reasoning_basis": "证据不足",
                "narrative_summary": "基于目前的观察，我们需要收集更多信息来理解孩子的行为模式。",
            }
        
        top_hyp = high_confidence_hyps[0][1]
        return {
            "observed_pattern": f"观察到{top_hyp.name}相关的行为模式",
            "primary_attribution": top_hyp.description,
            "capability_gaps": "需要进一步评估",
            "reasoning_basis": f"基于{len(top_hyp.evidence)}条证据的支持",
            "narrative_summary": f"分析指向{top_hyp.name}。这反映了孩子在相关能力方面可能需要额外支持。",
        }
    
    def get_hypothesis_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有假设的当前状态（用于调试和可视化）"""
        return {
            hyp_id: {
                "name": hyp.name,
                "confidence": hyp.current_confidence,
                "evidence_count": len(hyp.evidence),
                "evidence": hyp.evidence,
            }
            for hyp_id, hyp in self.network.hypotheses.items()
        }
    
    def confidence_label(self, confidence: float) -> str:
        """根据置信度返回标签"""
        if confidence >= 0.8:
            return "很可能"
        elif confidence >= 0.6:
            return "较可能"
        elif confidence >= 0.4:
            return "有可能"
        else:
            return "可能性较低"
    
    async def step1_scene_recognition(self, user_input: str) -> Dict[str, Any]:
        """Step 1: 场景识别"""
        detected_intent = self.detect_user_intent(user_input)
        
        scene_type_map = {
            "H_TANGIBLE": "A 类（实物获取）",
            "H_ATTENTION": "A 类（寻求关注）",
            "H_ESCAPE_DIFFICULTY": "B 类（逃避难度）",
            "H_ESCAPE_SENSORY": "B 类（感觉逃避）",
            "H_WORKING_MEMORY": "B 类（认知与心智理论）",
            "prompt_dependence": "C 类（提示依赖）",
            "sensory_seeking": "D 类（感官寻求）",
            "H_VISUAL_DISCRIMINATION": "E 类（视觉辨别）",
        }
        
        challenge_map = {
            "H_TANGIBLE": "延迟满足与情绪调节",
            "H_ATTENTION": "适当寻求关注的技能",
            "H_ESCAPE_DIFFICULTY": "任务坚持与挫折耐受",
            "H_ESCAPE_SENSORY": "感觉统合与适应",
            "H_WORKING_MEMORY": "错误信念推理与认知灵活性",
            "prompt_dependence": "独立执行功能",
            "sensory_seeking": "感觉需求适当表达",
            "H_VISUAL_DISCRIMINATION": "视觉辨别与方向认知",
        }
        
        scene_name_map = {
            "H_TANGIBLE": "想要但得不到",
            "H_ATTENTION": "被看见的渴望",
            "H_ESCAPE_DIFFICULTY": "太难了我不想做",
            "H_ESCAPE_SENSORY": "太吵了我受不了",
            "H_WORKING_MEMORY": "我记不住步骤",
            "prompt_dependence": "看着才会做",
            "sensory_seeking": "我要更多感觉",
            "H_VISUAL_DISCRIMINATION": "方向搞反了",
        }
        
        scene_type = scene_type_map.get(detected_intent, "待确定") if detected_intent else "待确定"
        core_challenge = challenge_map.get(detected_intent, "待评估") if detected_intent else "待评估"
        scene_name = scene_name_map.get(detected_intent, "未知场景") if detected_intent else "未知场景"
        
        return {
            "scene_type": scene_type,
            "scene_name": scene_name,
            "core_challenge": core_challenge,
            "detected_intent": detected_intent,
            "antecedent": user_input,
            "behavior": "",
            "consequence": "",
        }
    
    async def step2_hypothesis_generation(self, user_input: str, step1_result: Dict) -> Dict[str, Any]:
        """Step 2: 假设生成"""
        hypotheses = []
        
        top_hyps = sorted(
            self.network.hypotheses.items(),
            key=lambda x: x[1].current_confidence,
            reverse=True
        )[:3]
        
        for hyp_id, hyp in top_hyps:
            label = self.confidence_label(hyp.current_confidence)
            hypotheses.append({
                "id": hyp_id,
                "content": hyp.description,
                "confidence": hyp.current_confidence,
                "label": label,
                "reason": f"基于当前证据，置信度{int(hyp.current_confidence * 100)}%",
            })
        
        return {"hypotheses": hypotheses}
    
    async def step4_mechanism_explanation(self, user_input: str, step1_result: Dict, step3_result: Dict) -> Dict[str, Any]:
        """Step 4: 机制解释"""
        detected_intent = step1_result.get("detected_intent", "")
        
        metaphor_map = {
            "H_WORKING_MEMORY": "这就像一个电脑内存不足的孩子，同时处理多件事情时会卡顿",
            "H_ESCAPE_DIFFICULTY": "这就像一个面对高台阶的孩子，不是不想上，是不知如何迈步",
            "H_ATTENTION": "这就像一个渴望观众鼓掌的表演者，用各种方式吸引目光",
            "H_TANGIBLE": "这就像一个看到糖果就忍不住的孩子，即时满足战胜了等待能力",
            "prompt_dependence": "这就像一个需要拐杖学步的孩子，外部支持成了内在能力的一部分",
            "H_VISUAL_DISCRIMINATION": "这就像一个看镜子写字的孩子，不是不会写，是视觉信号被翻转了",
        }
        
        developmental_map = {
            "H_WORKING_MEMORY": "工作记忆能力在儿童期持续发展，前额叶皮层到25岁才完全成熟。当前的困难反映了执行功能发展中的正常变异。",
            "H_ESCAPE_DIFFICULTY": "挫折耐受能力随年龄和经验逐步建立。孩子需要成功的体验来积累'我能行'的信念。",
            "H_ATTENTION": "寻求关注是人类的自然需求，关键是如何以适当的方式满足。孩子正在学习'怎样被看见'。",
            "H_TANGIBLE": "延迟满足能力是自我调节的核心，4-6岁是发展关键期，适当的等待练习会促进这一能力。",
            "prompt_dependence": "独立性是一个逐步褪去外部支持的过程，像学步车一样，最终目标是让孩子自己走。",
            "H_VISUAL_DISCRIMINATION": "视觉辨别能力在4-7岁仍在发展中，方向混淆是常见现象。多数孩子随年龄增长会自然改善，但适当的练习可以加速这一过程。",
        }
        
        cognitive_mechanism_map = {
            "H_WORKING_MEMORY": "可能涉及工作记忆容量（维持和操作信息）、认知灵活性（任务切换）或抑制控制（过滤干扰）的薄弱环节。",
            "H_ESCAPE_DIFFICULTY": "可能涉及挫折耐受阈值、情绪调节策略或任务价值评估的困难。",
            "H_ATTENTION": "可能涉及社会参照需求、自我价值感建立或互动模式学习的需要。",
            "H_TANGIBLE": "可能涉及冲动控制、延迟满足能力或情绪调节策略的发展中状态。",
            "prompt_dependence": "可能涉及视觉编码依赖、内部言语发展不足或执行功能外部化的需要。",
            "H_VISUAL_DISCRIMINATION": "可能涉及视觉工作记忆（维持方向信息）、视觉注意（选择性关注关键特征）或视觉-空间处理（心理旋转、空间定位）的薄弱环节。",
        }
        
        metaphor = metaphor_map.get(detected_intent, "每个行为都是孩子独特的沟通语言")
        developmental = developmental_map.get(detected_intent, "每个孩子的发展节奏不同，需要耐心和适当支持")
        cognitive = cognitive_mechanism_map.get(detected_intent, "需要进一步评估")
        
        return {
            "cognitive_mechanism": cognitive,
            "metaphor": metaphor,
            "developmental_perspective": developmental,
        }
    
    async def step5_intervention_planning(self, user_input: str, step4_result: Dict) -> Dict[str, Any]:
        """Step 5: 干预策略"""
        detected_intent = self.detect_user_intent(user_input)
        
        strategy_map = {
            "H_WORKING_MEMORY": [
                {"name": "分步提示法", "description": "将复杂任务分解为小步骤，每次只给一个指令。完成一步后再给下一步，逐步减少提示。", "why_effective": "降低工作记忆负荷，让孩子的认知资源集中在当前步骤上，避免信息过载导致的'交通堵塞'。"},
                {"name": "视觉步骤图", "description": "用图片或图标展示任务步骤，让孩子可以随时'查看进度'。完成后标记已完成的步骤。", "why_effective": "将内部工作记忆转化为外部视觉支持，孩子不需要'记住'所有步骤，只需'看到'下一步。"},
                {"name": "游戏化练习", "description": "通过'记指令'游戏（如'去房间拿3样东西'）逐步增加任务复杂度，在有趣的情境中锻炼工作记忆。", "why_effective": "游戏情境降低焦虑，动机提升有助于认知资源投入，在不知不觉中锻炼了工作记忆。"},
            ],
            "H_ESCAPE_DIFFICULTY": [
                {"name": "难度梯度法", "description": "将任务分解为由易到难的梯度，让孩子从'肯定能做到'的水平开始，逐步提升难度。", "why_effective": "建立成功体验和自信心，避免'太难了'的挫折感，让挑战始终在'跳一跳够得着'的范围。"},
                {"name": "情绪标识法", "description": "教孩子用颜色或表情标识当前困难程度（绿=轻松，黄=有点难，红=太难），帮助成人及时调整。", "why_effective": "赋予孩子表达困难的工具，避免用行为（哭闹、逃避）来沟通需求。"},
            ],
            "H_ATTENTION": [
                {"name": "关注时间表", "description": "设立固定的'专属关注时间'（如每天15分钟一对一），让孩子知道'妈妈一定会看我'。", "why_effective": "用可预测的关注满足需求，减少'随时随地求关注'的行为。"},
                {"name": "积极行为强化", "description": "在孩子安静独立活动时给予关注（'我看到你自己玩得好认真'），而非只在捣乱时关注。", "why_effective": "重新定义'被关注'的条件，强化适当行为而非问题行为。"},
            ],
            "H_TANGIBLE": [
                {"name": "等待训练", "description": "使用计时器（'等针走到3就可以'），逐步延长等待时间，从10秒到1分钟到5分钟。", "why_effective": "将抽象的'等待'转化为可视化的过程，帮助孩子理解'延迟'不等于'得不到'。"},
                {"name": "替代活动法", "description": "在等待期间提供替代活动（'等的时候我们可以先玩这个'），转移注意力。", "why_effective": "降低等待的焦虑感，同时培养孩子的注意力转移能力。"},
            ],
            "prompt_dependence": [
                {"name": "提示褪去法", "description": "从全提示（手把手）→ 部分提示（指一下）→ 眼神提示 → 无提示，逐步减少。", "why_effective": "像拆脚手架一样逐步移除外部支持，让内部能力有机会独立运作。"},
                {"name": "自我对话训练", "description": "教孩子用'自言自语'的方式指导自己（'第一步做什么？哦，先拿笔'）。", "why_effective": "将外部提示转化为内部语言，是独立性发展的关键桥梁。"},
            ],
            "H_VISUAL_DISCRIMINATION": [
                {"name": "多感官标记法", "description": "用颜色、触觉等外部线索标记方向。如在左手腕戴红色手环（红色=左），右手腕戴蓝色手环。数字6和9用不同贴纸标记。", "why_effective": "通过多感官线索提供外部支架，绕过内部视觉处理的薄弱环节，让方向辨别变成'认颜色'而不是'辨方向'，降低认知负荷。"},
                {"name": "镜像对比练习", "description": "将易混淆的符号（6/9、b/d、左/右箭头）并排对比，用不同颜色标注差异点。每天练习5分钟，让孩子指出'哪里不一样'。", "why_effective": "强化视觉系统对方向差异的敏感度，帮助大脑建立稳定的'方向锚点'，逐步内化方向辨别能力。"},
                {"name": "身体体验法", "description": "用身体动作体验方向概念。如'左手摸左耳，右手摸右耳'游戏；在地上画左右线，听指令站位置；用身体摆出6和9的形状。", "why_effective": "将抽象的视觉方向转化为具体的身体记忆，通过运动觉辅助视觉处理，建立多重编码通道。"},
            ],
        }
        
        strategies = strategy_map.get(detected_intent, [
            {"name": "继续观察，收集更多信息", "description": "记录行为发生的频率、场景和前后变化", "why_effective": "更多信息有助于更准确的判断"}
        ])
        
        return {"intervention_strategies": strategies}
    
    def generate_report(self, full_result: Dict) -> str:
        """生成完整报告"""
        step1 = full_result.get("step1", {})
        step2 = full_result.get("step2", {})
        step4 = full_result.get("step4", {})
        step5 = full_result.get("step5", {})
        
        report = "# 📊 行为观察分析报告\n\n"
        
        # 场景理解
        report += "## 🎯 场景理解\n\n"
        report += f"这是一个 **{step1.get('scene_type', '待确定')}** 场景。\n\n"
        report += f"**核心挑战：** {step1.get('core_challenge', '待评估')}\n\n"
        
        # ABC 行为分析
        report += "## 📋 ABC 行为分析\n\n"
        report += "| 要素 | 描述 |\n|------|------|\n"
        report += f"| A 前因 | {step1.get('antecedent', '未提供')} |\n"
        report += f"| B 行为 | {step1.get('behavior', '未提供')} |\n"
        report += f"| C 后果 | {step1.get('consequence', '未提供')} |\n\n"
        
        # 我们的推理
        report += "## 🧠 我们的推理\n\n"
        report += "### 行为假设\n\n"
        hypotheses = step2.get("hypotheses", [])
        for i, h in enumerate(hypotheses, 1):
            report += f"{i}. **{h.get('label', '')}** - {h.get('content', '')}\n\n"
            report += f"   > 证据：{h.get('reason', '无')}\n\n"
        
        # 深层机制
        report += "### 深层机制\n\n"
        report += f"{step4.get('cognitive_mechanism', '需要进一步评估')}\n\n"
        report += f"**比喻：** {step4.get('metaphor', '')}\n\n"
        report += f"**发展视角：** {step4.get('developmental_perspective', '')}\n\n"
        
        # 安全提示
        report += "---\n\n"
        report += "### ⚠️ 安全提示\n\n"
        report += "在尝试以下策略前，请确认孩子的基本需求已满足：\n\n"
        report += "- 睡眠充足（未过度疲劳）\n"
        report += "- 饮食正常（未饥饿或过饱）\n"
        report += "- 身体健康（无生病、疼痛等不适）\n"
        report += "- 如孩子当前情绪极度不稳定，请先安抚情绪，再实施干预。\n\n"
        report += "所有干预都建立在安全的情感连接之上。如任何策略导致孩子更抗拒或您更焦虑，请暂停，优先修复关系。\n\n"
        
        # 建议策略
        report += "## 💡 建议策略\n\n"
        strategies = step5.get("intervention_strategies", [])
        for i, s in enumerate(strategies, 1):
            report += f"### 策略{i}: {s.get('name', '')}\n\n"
            report += f"**具体做法：** {s.get('description', '')}\n\n"
            report += f"**为什么有效：** {s.get('why_effective', '')}\n\n"
        
        # 个性化提醒
        report += "> 💡 **个性化适配提醒：** 以上策略为通用建议。实施前请评估您孩子的能力水平：\n\n"
        report += "> - 如孩子还不能理解情绪词汇，请先从非语言策略（如环境调整）开始\n"
        report += "> - 如孩子对特定策略表现出抗拒，请暂停并尝试其他方式\n"
        report += "> - 干预效果因个体差异而异，建议循序渐进，每次只尝试 1-2 种策略\n\n"
        
        # 结尾
        report += "---\n\n"
        report += "> 📋 **本次分析结束**。如需进一步评估，请描述新的行为观察内容。\n"
        report += "> 每次提问将开启一次独立的行为诊断分析。\n\n"
        report += "> ⚠️ **免责声明**：本分析基于单次行为观察，仅供参考。行为分析需要多次观察才能发现规律，建议您记录未来 2-3 次类似情况，并注意：\n"
        report += "> - 是否总是在特定场景发生？\n"
        report += "> - 孩子是否有先兆行为（如捂耳朵、烦躁）？\n"
        report += "> - 您的处理方式对行为有什么影响？\n\n"
        report += "> **AI 分析不能替代专业评估。如需正式诊断请咨询专业人士。**\n"
        
        return report
