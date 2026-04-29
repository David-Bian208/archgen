"""
临床推理引擎 V6.1 - LLM 驱动版
从"规则驱动评估"升级为"LLM 驱动推理"

核心变更（V6.1）：
1. 删除关键词库/模板库/策略库
2. 场景识别：LLM 分类（非关键词匹配）
3. 假设生成：LLM 动态生成（非预定义模板）
4. 证据检验：LLM 引用 + 规则验证
5. 机制解释：LLM 生成比喻（非预定义）
6. 干预策略：LLM 从机制推导（非策略库）

保留的质量底线：
- 证据必须引用用户原话
- 假设必须针对本案例
- 策略必须解释"为什么有效"
"""

import json
import logging
from typing import Optional
from dataclasses import dataclass, field
from typing import Dict, List, Any, Tuple

from app.llm.base import LLMClient

logger = logging.getLogger(__name__)


# V6.1 质量验证规则
QUALITY_VALIDATION_RULES = {
    "generic_terms": [
        "执行功能挑战",
        "社交沟通障碍",
        "感觉处理异常",
        "情绪调节困难",
        "认知灵活性不足",
    ],
    "vague_strategies": [
        "多练习",
        "耐心引导",
        "循序渐进",
        "给予支持",
        "适当帮助",
    ]
}


@dataclass
class ReasoningStep:
    """推理步骤结果"""
    step_number: int
    step_name: str
    result: Dict[str, Any]
    is_validated: bool = True
    validation_errors: List[str] = field(default_factory=list)


class ClinicalReasoningEngine:
    """
    临床推理引擎 V6.1 - LLM 驱动版
    
    核心方法：
    1. step1_scene_recognition(): LLM 场景识别
    2. step2_hypothesis_generation(): LLM 假设生成
    3. step3_evidence_examination(): 证据检验
    4. step4_mechanism_explanation(): 机制解释
    5. step5_intervention_planning(): 干预策略
    6. _validate_llm_output(): 质量底线验证
    
    ⚠️ 重要：所有 LLM 调用都是同步的（generate_json 是同步方法）
    """
    
    def __init__(self, llm_client: LLMClient):
        """初始化临床推理引擎（V6.1 LLM 驱动）"""
        self.llm = llm_client
        self.current_hypotheses: List[Dict[str, Any]] = []
        logger.info("ClinicalReasoningEngine V6.1 初始化完成（LLM 驱动）")
    
    def _reset_hypotheses(self):
        """重置当前假设（V4.5 兼容方法）"""
        self.current_hypotheses = []
        logger.debug("假设已重置")
    
    def detect_user_intent(self, user_input: str) -> Optional[str]:
        """用户意图检测（V4.5 兼容方法，V6.1 简化版）"""
        # V6.1 简化：不执行意图检测，直接返回 None
        # 由 StructuredAssessorV4 的框架驱动流程处理
        return None
    
    def update_beliefs(self, user_input: str, filled_data: Dict) -> Dict[str, float]:
        """更新假设置信度（V4.5 兼容方法，V6.1 简化版）"""
        # V6.1 简化：返回默认值
        # 实际由 LLM 动态生成假设，不需要预定义 belief 更新
        return {"tangible_access": 0.5, "attention_seeking": 0.5, "escape_difficulty": 0.5}
    
    def decide_next_question(self, filled_data: Dict) -> Dict[str, Any]:
        """决定下一个问题（V4.5 兼容方法，V6.1 简化版）"""
        # V6.1 简化：返回 None
        # 实际由 ClinicalAssessmentFramework 驱动流程
        return None
    
    def generate_narrative(self, filled_data: Dict) -> str:
        """生成叙事报告（V4.5 兼容方法，V6.1 简化版）"""
        # V6.1 简化：返回空字符串
        # 实际由 5 步临床推理引擎生成报告
        return ""
    
    def run_full_reasoning(self, user_input: str) -> Dict[str, Any]:
        """
        执行完整的 5 步临床推理流程
        
        Args:
            user_input: 用户输入的行为观察描述
            
        Returns:
            包含 5 步推理结果的字典
        """
        logger.info(f"🧠 开始 LLM 驱动临床推理：输入长度={len(user_input)}")
        
        # Step 1: 场景识别（LLM）
        step1_result = self._sync_step1_scene_recognition(user_input)
        step1 = ReasoningStep(
            step_number=1,
            step_name="场景识别",
            result=step1_result,
            is_validated=True
        )
        logger.info(f"✅ Step 1 完成：{step1_result['scene_type']}类 - {step1_result.get('scene_name', '未知')}")
        
        # Step 2: 假设生成（LLM）
        step2_result = self._sync_step2_hypothesis_generation(
            user_input,
            step1_result
        )
        logger.info(f"✅ Step 2 完成：生成{len(step2_result.get('hypotheses', []))}个假设")
        
        # Step 3: 证据检验（LLM + 规则）
        step3_result = self._sync_step3_evidence_examination(
            user_input,
            step2_result
        )
        logger.info(f"✅ Step 3 完成：检验{len(step3_result.get('evidence_examination', []))}个假设")
        
        # Step 4: 机制解释（LLM）
        step4_result = self._sync_step4_mechanism_explanation(
            user_input,
            step1_result,
            step3_result
        )
        logger.info("✅ Step 4 完成：生成机制解释")
        
        # Step 5: 干预策略（LLM）
        step5_result = self._sync_step5_intervention_planning(
            user_input,
            step4_result
        )
        logger.info(f"✅ Step 5 完成：生成{len(step5_result.get('intervention_strategies', []))}个策略")
        
        # 整合 5 步结果
        full_result = {
            **step1_result,
            **step2_result,
            **step3_result,
            **step4_result,
            **step5_result
        }
        
        # 质量底线验证
        is_valid, validation_errors = self._validate_llm_output(full_result)
        
        _ = ReasoningStep(
            step_number=2,
            step_name="假设生成 + 证据检验 + 机制解释 + 干预策略",
            result=full_result,
            is_validated=is_valid,
            validation_errors=validation_errors
        )
        
        if validation_errors:
            logger.warning(f"⚠️ 质量验证发现{len(validation_errors)}个问题：{validation_errors}")
        else:
            logger.info("✅ 5 步推理完成，质量验证通过")
        
        return {
            "step1_scene_classification": step1,
            "step2_hypothesis_generation": ReasoningStep(
                step_number=2,
                step_name="假设生成",
                result=step2_result
            ),
            "step3_evidence_examination": ReasoningStep(
                step_number=3,
                step_name="证据检验",
                result=step3_result
            ),
            "step4_mechanism_explanation": ReasoningStep(
                step_number=4,
                step_name="机制解释",
                result=step4_result
            ),
            "step5_intervention_planning": ReasoningStep(
                step_number=5,
                step_name="干预策略",
                result=step5_result
            ),
            "full_result": full_result,
            "validation_passed": is_valid,
            "validation_errors": validation_errors
        }
    
    # ========== V6.1 异步方法（SSE 支持） ==========
    
    async def step1_scene_recognition(self, user_input: str) -> Dict[str, Any]:
        """V6.1 异步版本：场景识别"""
        return self._sync_step1_scene_recognition(user_input)
    
    async def step2_hypothesis_generation(self, user_input: str, scene_result: Dict) -> Dict[str, Any]:
        """V6.1 异步版本：假设生成"""
        return self._sync_step2_hypothesis_generation(user_input, scene_result)
    
    async def step3_evidence_examination(self, user_input: str, hypothesis_result: Dict) -> Dict[str, Any]:
        """V6.1 异步版本：证据检验"""
        return self._sync_step3_evidence_examination(user_input, hypothesis_result)
    
    async def step4_mechanism_explanation(self, user_input: str, scene_result: Dict, evidence_result: Dict) -> Dict[str, Any]:
        """V6.1 异步版本：机制解释"""
        return self._sync_step4_mechanism_explanation(user_input, scene_result, evidence_result)
    
    async def step5_intervention_planning(self, user_input: str, mechanism_result: Dict) -> Dict[str, Any]:
        """V6.1 异步版本：干预策略"""
        return self._sync_step5_intervention_planning(user_input, mechanism_result)
    
    # ========== V6.1 同步方法（内部实现） ==========
    
    def _sync_step1_scene_recognition(self, user_input: str) -> Dict[str, Any]:
        """
        Step 1: LLM 场景识别
        
        使用 LLM 识别场景类型（A/B/C/D），而非关键词匹配
        
        场景分类：
        - A 类：社交互动与沟通（介绍朋友、轮流对话）
        - B 类：认知与心智理论（薯片盒子游戏、错误信念）
        - C 类：执行功能与灵活性（规则变化、过渡困难）
        - D 类：感觉处理与自我调节（听觉过敏、情绪崩溃）
        
        ⚠️ 注意：generate_json 是同步方法，不能用 await！
        """
        prompt = f"""请分析以下用户输入，识别场景类型。

场景类型选项：
- A 类 - 社交互动与沟通（介绍朋友、轮流对话、社交发起等）
- B 类 - 认知与心智理论（错误信念、视角采择、意图理解等）
- C 类 - 执行功能与灵活性（规则变化、过渡困难、计划组织等）
- D 类 - 感觉处理与自我调节（听觉过敏、情绪崩溃、自我刺激等）

用户输入：{user_input}

请以 JSON 格式输出：
{{
    "scene_type": "A/B/C/D",
    "scene_name": "场景名称",
    "core_challenge": "核心挑战定义（1 句话）",
    "recognition_basis": "识别依据（引用用户原话）"
}}
"""
        
        try:
            # ✅ 同步调用 LLM（generate_json 是同步方法）
            result = self.llm.generate_json(
                system_prompt="你是一位儿童行为临床专家。只输出 JSON，不要解释。",
                user_prompt=prompt,
                temperature=0.1,
                max_tokens=500
            )
            
            # 验证输出格式
            if not isinstance(result, dict):
                logger.error(f"场景分类返回非字典：{type(result)}")
                return self._get_fallback_scene_classification()
            
            # 验证 scene_type
            scene_type = result.get('scene_type', 'A')
            if scene_type not in ['A', 'B', 'C', 'D']:
                logger.warning(f"场景类型无效：{scene_type}，默认使用 A")
                result['scene_type'] = 'A'
            
            return result
            
        except Exception as e:
            logger.error(f"场景分类失败：{e}")
            return self._get_fallback_scene_classification()
    
    def _sync_step2_hypothesis_generation(
        self,
        user_input: str,
        scene_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Step 2: LLM 假设生成
        
        基于场景类型和用户输入，生成 2-3 个具体假设
        
        质量要求：
        1. 每个假设必须针对本案例（非通用框架）
        2. 每个假设必须包含置信度（0.3-0.9）
        3. 避免通用描述（如"执行功能挑战"）
        
        ⚠️ 注意：generate_json 是同步方法，不能用 await！
        """
        prompt = f"""你是 BCBA 督导，请基于以下场景和用户输入，生成 2-3 个具体假设。

【场景类型】
{scene_result.get('scene_type')}类 - {scene_result.get('scene_name', '未知')}
核心挑战：{scene_result.get('core_challenge', '未知')}

【用户输入】
{user_input}

【质量要求】
1. 每个假设必须针对本案例（非通用框架）
2. 每个假设必须引用用户原话作为证据
3. 为每个假设提供置信度（0.3-0.9）
4. 假设格式：{{"id": "H1", "content": "...", "confidence": 0.8, "evidence": "用户原话"}}

请以 JSON 格式输出假设列表：
{{
    "hypotheses": [
        {{"id": "H1", "content": "...", "confidence": 0.8, "evidence": "..."}},
        {{"id": "H2", "content": "...", "confidence": 0.6, "evidence": "..."}}
    ]
}}
"""
        
        try:
            # ✅ 同步调用 LLM（generate_json 是同步方法）
            hypotheses = self.llm.generate_json(
                system_prompt="你是 BCBA 督导，擅长生成具体、可检验的假设。只输出 JSON，不要解释。",
                user_prompt=prompt,
                temperature=0.3,
                max_tokens=1000
            )
            
            # 验证输出格式
            if not isinstance(hypotheses, dict):
                logger.error(f"假设生成返回非字典：{type(hypotheses)}")
                return self._get_fallback_hypotheses()
            
            return {"hypotheses": hypotheses.get("hypotheses", [])}
            
        except Exception as e:
            logger.error(f"假设生成失败：{e}")
            return self._get_fallback_hypotheses()
    
    def _sync_step3_evidence_examination(
        self,
        user_input: str,
        hypothesis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Step 3: 证据检验与排除
        
        对每个假设进行支持/反对证据分析，排除证据最弱的假设
        
        ⚠️ 注意：generate_json 是同步方法，不能用 await！
        """
        hypotheses = hypothesis_result.get("hypotheses", [])
        
        prompt = f"""你是临床推理专家，请对以下假设进行证据检验。

【用户输入】
{user_input}

【待检验假设】
{json.dumps(hypotheses, ensure_ascii=False, indent=2)}

【检验规则】
1. 支持证据必须引用用户原话
2. 反对证据可以是"无"
3. 排除证据最弱的假设
4. 决策选项：保留/排除

请以 JSON 格式输出检验结果：
{{
    "evidence_examination": [
        {{
            "hypothesis_id": "H1",
            "supporting_evidence": ["用户原话 1", "用户原话 2"],
            "contradicting_evidence": ["用户原话或无"],
            "decision": "保留/排除",
            "reason": "排除理由"
        }}
    ]
}}
"""
        
        try:
            # ✅ 同步调用 LLM（generate_json 是同步方法）
            examination = self.llm.generate_json(
                system_prompt="你是临床推理专家，擅长证据检验。只输出 JSON，不要解释。",
                user_prompt=prompt,
                temperature=0.2,
                max_tokens=1500
            )
            
            if not isinstance(examination, dict):
                logger.error(f"证据检验返回非字典：{type(examination)}")
                return {"evidence_examination": []}
            
            return {"evidence_examination": examination.get("evidence_examination", [])}
            
        except Exception as e:
            logger.error(f"证据检验失败：{e}")
            return {"evidence_examination": []}
    
    def _sync_step4_mechanism_explanation(
        self,
        user_input: str,
        scene_result: Dict[str, Any],
        evidence_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Step 4: 深度机制解释
        
        使用新颖比喻解释认知机制，避免术语堆砌
        
        ⚠️ 注意：generate_json 是同步方法，不能用 await！
        """
        prompt = f"""你是发展心理学专家，请基于以下信息生成深度机制解释。

【场景类型】
{scene_result.get('scene_type')}类 - {scene_result.get('scene_name', '未知')}

【用户输入】
{user_input}

【证据检验结果】
{json.dumps(evidence_result.get('evidence_examination', []), ensure_ascii=False, indent=2)}

【质量要求】
1. 使用新颖比喻（避免术语堆砌）
2. 链接具体认知构造
3. 包含发展视角
4. 比喻要生动、易懂

请以 JSON 格式输出：
{{
    "cognitive_mechanism": "认知机制解释",
    "metaphor": "新颖比喻",
    "developmental_perspective": "发展视角"
}}
"""
        
        try:
            # ✅ 同步调用 LLM（generate_json 是同步方法）
            mechanism = self.llm.generate_json(
                system_prompt="你是发展心理学专家，擅长用生动比喻解释认知机制。只输出 JSON，不要解释。",
                user_prompt=prompt,
                temperature=0.4,
                max_tokens=1000
            )
            
            if not isinstance(mechanism, dict):
                logger.error(f"机制解释返回非字典：{type(mechanism)}")
                return self._get_fallback_mechanism()
            
            return mechanism
            
        except Exception as e:
            logger.error(f"机制解释失败：{e}")
            return self._get_fallback_mechanism()
    
    def _sync_step5_intervention_planning(
        self,
        user_input: str,
        mechanism_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Step 5: 精准干预策略
        
        从机制直接衍生策略，解释"为什么有效"
        
        ⚠️ 注意：generate_json 是同步方法，不能用 await！
        """
        prompt = f"""你是 BCBA 督导，请基于以下机制解释生成精准干预策略。

【机制解释】
认知机制：{mechanism_result.get('cognitive_mechanism', '未知')}
比喻：{mechanism_result.get('metaphor', '未知')}
发展视角：{mechanism_result.get('developmental_perspective', '未知')}

【质量要求】
1. 策略针对机制（非维度匹配）
2. 解释"为什么有效"
3. 绑定场景要素（个性化）
4. 策略数量：2-3 个

请以 JSON 格式输出策略列表：
{{
    "intervention_strategies": [
        {{
            "name": "策略名称",
            "description": "具体做法",
            "why_effective": "为什么有效（从机制推导）",
            "based_on_mechanism": "基于的机制"
        }}
    ]
}}
"""
        
        try:
            # ✅ 同步调用 LLM（generate_json 是同步方法）
            strategies = self.llm.generate_json(
                system_prompt="你是 BCBA 督导，擅长从机制推导精准策略。只输出 JSON，不要解释。",
                user_prompt=prompt,
                temperature=0.3,
                max_tokens=1500
            )
            
            if not isinstance(strategies, dict):
                logger.error(f"干预策略返回非字典：{type(strategies)}")
                return self._get_fallback_strategies()
            
            return {"intervention_strategies": strategies.get("intervention_strategies", [])}
            
        except Exception as e:
            logger.error(f"干预策略失败：{e}")
            return self._get_fallback_strategies()
    
    def _validate_llm_output(self, output: dict) -> Tuple[bool, List[str]]:
        """
        V6.1 新增：质量底线验证
        
        验证规则：
        1. 假设必须有证据引用
        2. 机制解释必须有比喻
        3. 策略必须解释"为什么有效"
        
        Returns:
            (是否通过验证，错误列表)
        """
        errors = []
        
        # 1. 检查 Step 2：假设必须有证据引用
        for hyp in output.get("hypotheses", []):
            if not hyp.get("evidence"):
                errors.append(f"假设{hyp.get('id', '未知')}缺少证据引用")
        
        # 2. 检查 Step 4：机制解释必须有比喻
        if not output.get("metaphor"):
            errors.append("机制解释缺少比喻")
        
        # 3. 检查 Step 5：策略必须解释"为什么有效"
        for strategy in output.get("intervention_strategies", []):
            if not strategy.get("why_effective"):
                errors.append(f"策略'{strategy.get('name', '未知')}'缺少有效性解释")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def _get_fallback_scene_classification(self) -> Dict[str, Any]:
        """降级场景分类方案"""
        return {
            "scene_type": "A",
            "scene_name": "未分类场景",
            "core_challenge": "需要进一步评估",
            "recognition_basis": "场景分类失败，使用默认值"
        }
    
    def _get_fallback_hypotheses(self) -> Dict[str, Any]:
        """降级假设生成方案"""
        return {
            "hypotheses": [
                {
                    "id": "H1",
                    "content": "需要进一步评估",
                    "confidence": 0.5,
                    "evidence": "假设生成失败，使用默认值"
                }
            ]
        }
    
    def _get_fallback_mechanism(self) -> Dict[str, Any]:
        """降级机制解释方案"""
        return {
            "cognitive_mechanism": "需要进一步评估",
            "metaphor": "需要进一步评估",
            "developmental_perspective": "需要进一步评估"
        }
    
    def _get_fallback_strategies(self) -> Dict[str, Any]:
        """降级干预策略方案"""
        return {
            "intervention_strategies": [
                {
                    "name": "进一步评估",
                    "description": "收集更多信息",
                    "why_effective": "需要更多信息才能制定策略",
                    "based_on_mechanism": "未知"
                }
            ]
        }
    
    def generate_report(self, reasoning_result: Dict[str, Any]) -> str:
        """
        基于推理结果生成最终报告
        
        将 5 步推理整合为温暖的叙事性报告
        """
        full_result = reasoning_result.get('full_result', reasoning_result)
        
        # 提取关键信息
        scene_type = full_result.get('scene_type', 'A')
        scene_name = full_result.get('scene_name', '未分类场景')
        core_challenge = full_result.get('core_challenge', '需要进一步评估')
        hypotheses = full_result.get('hypotheses', [])
        mechanism = full_result
        strategies = full_result.get('intervention_strategies', [])
        
        # 生成报告
        report = f"""# 行为观察分析报告

## 场景理解
这是一个 **{scene_name}** 场景（{scene_type}类）。
核心挑战：{core_challenge}

## 我们的推理

### 可能的解释
"""
        
        # 添加假设
        for hyp in hypotheses:
            report += f"\n- **假设{hyp['id']}**: {hyp['content']}（置信度：{hyp['confidence']:.0%}）"
            if hyp.get('evidence'):
                report += f"\n  证据：\"{hyp['evidence']}\""
        
        # 添加机制解释
        report += f"""

### 深层机制
{mechanism.get('cognitive_mechanism', '需要进一步评估')}

**比喻**: {mechanism.get('metaphor', '需要进一步评估')}

**发展视角**: {mechanism.get('developmental_perspective', '需要进一步评估')}

## 建议策略

"""
        
        # 添加策略
        for i, strategy in enumerate(strategies, 1):
            report += f"""
### 策略{i}: {strategy['name']}
**具体做法**: {strategy['description']}

**为什么有效**: {strategy['why_effective']}
"""
        
        return report
    
    def get_hypothesis_status(self) -> Dict[str, Any]:
        """获取推理状态（用于调试）"""
        return {
            "engine_version": "V6.1",
            "driving_mode": "LLM-driven",
            "knowledge_base_required": False,
            "maintenance_cost": "minimal"
        }
