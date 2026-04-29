"""
洞察分析器 V3.0 - V4.5.13 个性化报告版
从"行为分类"升级为"共情洞察"

核心理念：
- 不是输出标签，而是生成洞察
- 不是事实复述，而是行为理解
- 不是专业术语，而是家长能懂的"金句"

V4.5.13 新增：
- 家长用语风格检测（专业 vs 日常）
- 个性化报告语言调整
- 详细版/简洁版选项
"""

import json
import logging
import re
from typing import Optional

from app.llm.base import LLMClient

logger = logging.getLogger(__name__)


# ========== V4.5.13 P1-03: 家长用语风格检测 ==========
class ParentStyleDetector:
    """家长用语风格检测器"""
    
    # 专业术语关键词
    PROFESSIONAL_TERMS = [
        "前因", "后果", "强化", "消退", "ABC", "功能分析",
        "行为功能", "逃避", "寻求关注", "感觉统合", "感统",
        "刻板行为", "自我刺激", "提示", "辅助", "泛化",
        "工作记忆", "执行功能", "注意力缺陷", "感统失调"
    ]
    
    # 日常用语关键词
    CASUAL_TERMS = [
        "之前", "然后", "之后", "奖励", "不理", "什么时候",
        "老是", "总是", "就是", "好像", "感觉", "觉得",
        "孩子他", "我家", "老师他", "不知道咋办"
    ]
    
    @classmethod
    def detect_style(cls, conversation_history: list) -> str:
        """
        检测家长用语风格
        
        Args:
            conversation_history: 对话历史
            
        Returns:
            "professional" (专业) 或 "casual" (日常)
        """
        all_text = " ".join([
            msg.get("text", "") 
            for msg in conversation_history 
            if msg.get("role") == "user"
        ])
        
        prof_count = sum(1 for term in cls.PROFESSIONAL_TERMS if term in all_text)
        casual_count = sum(1 for term in cls.CASUAL_TERMS if term in all_text)
        
        # 句子长度和复杂度
        sentences = [s.strip() for s in re.split(r'[。！？!?]', all_text) if s.strip()]
        avg_sentence_length = sum(len(s) for s in sentences) / len(sentences) if sentences else 0
        
        style = "professional" if prof_count > casual_count else "casual"
        
        # 长句子 + 专业术语 → 更可能是专业人士
        if avg_sentence_length > 30 and prof_count >= 2:
            style = "professional"
        
        logger.info(f"📊 家长用语风格检测：{style} (专业术语={prof_count}, 日常用语={casual_count}, 平均句长={avg_sentence_length:.1f})")
        return style
    
    @classmethod
    def get_style_prompt_suffix(cls, style: str) -> str:
        """
        根据风格返回 Prompt 后缀
        
        Args:
            style: 用语风格 ("professional" 或 "casual")
            
        Returns:
            Prompt 后缀
        """
        if style == "professional":
            return """
【语言风格要求】
- 使用专业术语（如"前因"、"后果"、"强化"、"功能分析"）
- 保持专业严谨，但要有温度
- 可以适当使用专业概念解释
- 长度：详细版（150-200 字）"""
        else:
            return """
【语言风格要求】
- 使用日常语言，避免专业术语
- 用"之前/然后/之后"代替"前因/后果"
- 用"奖励"代替"强化"，用"不理"代替"消退"
- 多用比喻和金句，说进家长心坎里
- 长度：简洁版（80-120 字）"""


class InsightAnalyzer:
    """
    洞察分析器 V3.0
    
    三步推理链：
    1. 功能判断（内在逻辑）- 不直接输出术语
    2. 深度归因（动机与能力）- 区分"不想做"vs"做不到"
    3. 提炼核心洞察 - 给家长的"金句"
    """
    # V4.11.2 深度性能优化：精简提示词（减少 70% token）
    ANALYSIS_SYSTEM_PROMPT = """BCBA 督导，将观察转化为家长能懂的洞察。

任务：
1. 功能判断
2. 核心洞察（金句）
3. 能力假设
4. 临床鉴别（3 模块）
5. 干预原则

关键规则：
- 有"都会做"→排除提示依赖
- 同伴互动→社交技能不足
- 证据不足→"需要进一步观察"

鉴别结构：
1. 鉴别与排除（排除 2+ 假设）
2. 核心假设（术语命名）
3. 能力缺口（现象→归因）

输出 JSON：
{{
  "functional_judgment": "...",
  "core_insight": "...",
  "capability_hypothesis": "...",
  "clinical_differential": "1. **鉴别与排除**：...",
  "intervention_principle": "..."
}}

语言：短句、"我们"视角、"还没学会"
"""

    # V4.11.2 深度性能优化：精简用户提示词（减少 67% token）
    ANALYSIS_USER_PROMPT_TEMPLATE = """观察：
- 环境：{environment}
- 情境：{antecedent}
- 行为：{behavior}
- 后果：{consequence}

生成洞察报告（功能判断、核心洞察、能力假设、临床鉴别、干预原则）。

要求：结合细节、家长能懂、短句。
"""

    # V3.6 鉴别诊断分析 Prompt - 临床深度增强版
    ANALYSIS_WITH_DIFFERENTIAL_TEMPLATE = """请基于以下观察信息和竞争性假设，进行鉴别诊断分析：

【观察信息】
- 环境：{environment}
- 情境：{antecedent}
- 孩子的表现：{behavior}
- 当时的回应：{consequence}
- 用户补充的鉴别细节：{discriminating_answer}

【竞争性假设】
{hypotheses_json}

【你的分析任务】
请参考提供的专业假设，根据所有信息评估每种假设的可能性：
1. 逐一评估每个假设的支持证据和不支持证据
2. 给出一个综合性的、有层次的分析：哪个假设可能性最高，为什么
3. 同时考虑其他假设是否可能部分存在
4. 基于最可能的假设，给出核心洞察和干预原则
5. 生成临床鉴别思考：说明鉴别诊断过程

请严格按照以下 JSON 格式输出：
{{
    "expert_breakdown": {{
        "behavior_pattern": "一句话命名该行为模式",
        "functional_hypothesis": "基于鉴别诊断，判断最可能的功能，并说明推理",
        "capability_gap": "分析这可能反映了哪方面的能力挑战",
        "contextual_factors": "简述环境因素如何影响行为",
        "differential_reasoning": "简述鉴别诊断过程：为什么 HX 可能性最高，其他假设的可能性如何"
    }},
    "clinical_differential": "针对观察到的行为，说明临床上通常考虑的几种可能性（参考竞争性假设），然后结合当前观察信息（如用户的鉴别细节）说明为什么某种可能性最高。100-200 字。",
    "core_insight_for_parent": "基于专家拆解，用一句'金句'直击本质，说进家长心坎里",
    "strategy_principle": "针对最可能的假设，提出具体的干预原则",
    "reasoning_brief": "简短的专业推理（50 字以内）"
}}"""

    def __init__(self, llm_client: LLMClient):
        """
        初始化洞察分析器

        Args:
            llm_client: LLM 客户端实例
        """
        self.llm = llm_client
        # V4.11.2 性能优化：添加 LLM 缓存
        from app.llm.llm_cache import get_llm_cache
        self.cache = get_llm_cache()
        logger.info("InsightAnalyzer V3.0 初始化完成（带缓存）")

    def analyze(self, environment: str, antecedent: str, behavior: str, consequence: str, competing_hypotheses: Optional[list] = None, discriminating_answer: str = "", conversation_history: Optional[list] = None, report_style: Optional[str] = None) -> dict:
        """
        执行三步推理分析（V4.5.13 - 个性化报告版）

        Args:
            environment: 环境上下文
            antecedent: 情境（前因）
            behavior: 孩子的表现（行为）
            consequence: 当时的回应（后果）
            competing_hypotheses: 竞争性假设列表（可选）
            discriminating_answer: 用户对鉴别性问题的回答（可选）
            conversation_history: 对话历史（用于检测家长用语风格）
            report_style: 报告风格 ("professional"/"casual"，不传则自动检测)

        Returns:
            洞察分析结果
        """
        logger.info(f"开始洞察分析：环境={environment[:30] if environment else '无'}, 情境={antecedent[:30]}..., 行为={behavior[:30]}...")
        
        # V4.5.13 新增：检测家长用语风格
        if report_style is None and conversation_history:
            report_style = ParentStyleDetector.detect_style(conversation_history)
        elif report_style is None:
            report_style = "casual"  # 默认日常风格
        
        style_suffix = ParentStyleDetector.get_style_prompt_suffix(report_style)
        logger.info(f"📝 报告风格：{report_style}")

        # V3.4 新增：如果有竞争性假设，使用鉴别诊断 Prompt
        if competing_hypotheses and discriminating_answer:
            user_prompt = self.ANALYSIS_WITH_DIFFERENTIAL_TEMPLATE.format(
                environment=environment or '未提及',
                antecedent=antecedent,
                behavior=behavior,
                consequence=consequence,
                hypotheses_json=json.dumps(competing_hypotheses, ensure_ascii=False, indent=2),
                discriminating_answer=discriminating_answer,
            ) + style_suffix
        else:
            user_prompt = self.ANALYSIS_USER_PROMPT_TEMPLATE.format(
                environment=environment or '未提及',
                antecedent=antecedent,
                behavior=behavior,
                consequence=consequence,
            ) + style_suffix

        try:
            # V4.11.2 性能优化：先尝试从缓存获取
            cache_key_system = self.ANALYSIS_SYSTEM_PROMPT
            cache_key_user = user_prompt
            cached_response = self.cache.get(cache_key_system, cache_key_user)
            
            if cached_response:
                logger.info("✅ 缓存命中")
                import json
                result = json.loads(cached_response)
            else:
                # 缓存未命中，调用 LLM
                logger.info("⏳ 调用 LLM...")
                result = self.llm.generate_json(
                    system_prompt=self.ANALYSIS_SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    temperature=0.1,  # V4.11.2 深度优化：更低温度，更确定性
                    max_tokens=500,  # V4.11.2 深度优化：减少 37%
                )
                
                # 写入缓存（10 分钟 TTL）
                import json as json_module
                self.cache.set(
                    cache_key_system,
                    cache_key_user,
                    json_module.dumps(result, ensure_ascii=False),
                    ttl_seconds=600  # 10 分钟
                )
                logger.info("💾 已写入缓存")

            # V4.3 核心修复：确保所有必需字段存在，进行数据转换和兼容
            result = self._ensure_v43_compatibility(result)
            
            # V4.10.3 新增：强制转换能力缺口分析的有序列表为无序列表
            logger.info(f"V4.10.3 修复前 clinical_differential: {result.get('clinical_differential', '')}")
            result = self._fix_capability_gap_format(result)
            logger.info(f"V4.10.3 修复后 clinical_differential: {result.get('clinical_differential', '')}")

            # V5.0 新增：发展性视角映射（功能→能力）
            result = self._add_developmental_perspective(result)

            logger.info(f"洞察分析完成：{result['core_insight'][:50]}...")
            return result

        except Exception as e:
            logger.error(f"洞察分析失败：{e}")
            return self._get_fallback_result(str(e))
    
    def _fix_capability_gap_format(self, result: dict) -> dict:
        """
        V4.10.3 新增：强制修复 clinical_differential 的编号层级
        
        问题：
        1. LLM 经常忽略 Prompt 要求，三个主标题都用"1."
        2. 能力缺口分析的子列表用 1. 2. 3. 而不是 •
        3. 标题可能没有加粗标记（如"1. 鉴别与排除："而非"1. **鉴别与排除**："）
        
        解决：后处理强制修复编号层级，兼容有无加粗两种情况
        
        期望格式：
        1. **鉴别与排除**：
           • 为何不是...
        
        2. **核心假设**：...
        
        3. **能力缺口分析**：
           • **缺口 1**：...
           • **缺口 2**：...
        
        Args:
            result: LLM 返回的分析结果
            
        Returns:
            修复后的结果
        """
        clinical_diff = result.get("clinical_differential", "")
        if not clinical_diff:
            return result
        
        import re
        
        # ========== 修复 1: 主标题编号 ==========
        # 匹配模式：行首 + 数字 + "."或"、" + 空格 + 可选的 ** + 标题文本 + 可选的 **
        # 替换为正确的 1. 2. 3. 编号
        
        # 找到三个主标题的位置
        titles = ["鉴别与排除", "核心假设", "能力缺口分析"]
        lines = clinical_diff.split('\n')
        fixed_lines = []
        title_index = 0
        
        for line in lines:
            fixed_line = line
            # 检查是否是主标题行（行首有数字编号 + 标题，兼容有无加粗）
            # 正则：行首 + 数字 + .或、 + 可选空格 + 可选** + 捕获标题文本 + 可选** + 可选冒号
            title_match = re.match(r'^(\d+)[.、]\s*\*?([^*:]+)\*?\s*:?\s*$', line.strip())
            if title_match:
                # 检查是否是我们期望的三个标题之一
                title_text = title_match.group(2).strip()
                if title_text in titles and title_index < len(titles):
                    # 用正确的编号替换
                    correct_num = title_index + 1
                    # 保持原有格式（有无加粗都保留）
                    fixed_line = re.sub(r'^\d+[.、]', f'{correct_num}.', line)
                    title_index += 1
            
            fixed_lines.append(fixed_line)
        
        clinical_diff = '\n'.join(fixed_lines)
        
        # ========== 修复 2: 能力缺口分析的子列表 ==========
        # 找到"能力缺口分析"部分，将其中的有序列表转换为无序列表
        if "能力缺口分析" in clinical_diff:
            parts = clinical_diff.split("能力缺口分析")
            if len(parts) >= 2:
                prefix = parts[0] + "能力缺口分析"
                suffix = parts[1]
                
                # 只替换能力缺口分析内部的有序列表（有缩进 + 可选加粗）
                # 匹配：换行 + 空格 + 数字 + 点 + 空格 + 可选** + 内容 + 可选**
                suffix_fixed = re.sub(r'\n\s+(\d+)[.、]\s*\*?([^\n]+?)\*?\s*$', r'\n   • \2', suffix, flags=re.MULTILINE)
                
                clinical_diff = prefix + suffix_fixed
        
        result["clinical_differential"] = clinical_diff
        
        logger.info("V4.10.3 clinical_differential 编号层级修复完成")
        return result
    
    def _ensure_v43_compatibility(self, result: dict) -> dict:
        """
        V4.3 核心修复：确保返回字段与 V4.3 报告模板完全兼容
        
        数据转换逻辑：
        1. 确保 functional_judgment, core_insight, capability_hypothesis 存在
        2. 兼容旧字段名（expert_breakdown → functional_judgment 等）
        3. 填充缺失字段的默认值
        """
        # 1. 确保核心字段存在
        if "functional_judgment" not in result:
            # 尝试从 expert_breakdown 推断
            expert = result.get("expert_breakdown", {})
            result["functional_judgment"] = expert.get("functional_hypothesis", "提示依赖下的逃避")
        
        if "core_insight" not in result:
            # 尝试从 core_insight_for_parent 复制
            result["core_insight"] = result.get("core_insight_for_parent", "孩子正在用这种方式表达他的需求。")
        
        if "capability_hypothesis" not in result:
            # 尝试从 expert_breakdown 复制
            expert = result.get("expert_breakdown", {})
            result["capability_hypothesis"] = expert.get("capability_gap", "工作记忆和持续性注意方面的挑战。")
        
        # 2. 确保 clinical_differential 存在
        if "clinical_differential" not in result:
            result["clinical_differential"] = "基于观察到的行为模式，我们考虑了多种可能性，结合关键信息判断最可能的功能假设。"
        
        # 3. 确保 intervention_principle 存在
        if "intervention_principle" not in result:
            result["intervention_principle"] = result.get("strategy_principle", "将外部提示转化为内部提示")
        
        # 4. 确保 expert_breakdown 存在（向后兼容）
        if "expert_breakdown" not in result:
            result["expert_breakdown"] = {
                "behavior_pattern": "待分析行为模式",
                "functional_hypothesis": result.get("functional_judgment", ""),
                "capability_gap": result.get("capability_hypothesis", ""),
                "contextual_factors": "环境因素影响待评估"
            }
        
        # 5. 确保 core_insight_for_parent 与 core_insight 一致（向后兼容）
        if "core_insight_for_parent" not in result:
            result["core_insight_for_parent"] = result["core_insight"]
        
        # 6. 确保 strategy_principle 与 intervention_principle 一致（向后兼容）
        if "strategy_principle" not in result:
            result["strategy_principle"] = result["intervention_principle"]
        
        # 7. 确保 reasoning_brief 存在
        if "reasoning_brief" not in result:
            result["reasoning_brief"] = "基于 ABC 模式和临床经验的综合判断"
        
        logger.info(f"V4.3 字段兼容性检查完成：functional_judgment={result.get('functional_judgment', 'N/A')[:30]}...")
        return result
    
    def _add_developmental_perspective(self, result: dict) -> dict:
        """
        V5.0 新增：发展性视角映射（功能→能力）
        
        基于功能判断，映射到可能的发展能力领域
        
        Args:
            result: 洞察分析结果
        
        Returns:
            增加 developmental_perspective 字段的结果
        """
        from app.knowledge import map_function_to_capabilities
        
        functional_judgment = result.get("functional_judgment", "")
        
        # 从功能判断提取假设 ID
        # 例如："逃避难度" → "H_ESCAPE_DIFFICULTY"
        #      "提示依赖" → "H_PROMPT_DEPENDENCE"
        #      "寻求关注" → "H_ATTENTION"
        #      "社交技能不足" → "H_SOCIAL_SKILLS"
        #      "自动强化" → "H_AUTOMATIC"
        
        function_to_id = {
            "逃避难度": "H_ESCAPE_DIFFICULTY",
            "逃避": "H_ESCAPE",
            "提示依赖": "H_PROMPT_DEPENDENCE",
            "寻求关注": "H_ATTENTION",
            "关注": "H_ATTENTION",
            "社交技能不足": "H_SOCIAL_SKILLS",
            "社交": "H_SOCIAL_SKILLS",
            "自动强化": "H_AUTOMATIC",
            "自我刺激": "H_AUTOMATIC",
            "感觉超载": "H_SENSORY_OVERLOAD",
            "感觉逃避": "H_ESCAPE_SENSORY",
            "感觉敏感": "H_ESCAPE_SENSORY",
        }
        
        # 匹配假设 ID
        hypothesis_id = None
        for func_name, hyp_id in function_to_id.items():
            if func_name in functional_judgment:
                hypothesis_id = hyp_id
                break
        
        if not hypothesis_id:
            logger.warning(f"未能从功能判断 '{functional_judgment}' 中提取假设 ID")
            result["developmental_perspective"] = {
                "capability_areas": [],
                "note": "未能匹配到对应的能力领域映射"
            }
            return result
        
        # 映射到能力领域
        capability_areas = map_function_to_capabilities(hypothesis_id)
        
        if not capability_areas:
            logger.warning(f"未找到假设 {hypothesis_id} 的能力映射")
            result["developmental_perspective"] = {
                "capability_areas": [],
                "note": f"暂未建立 {hypothesis_id} 的能力领域映射"
            }
            return result
        
        # 构建发展性视角输出（最多 3 个，避免信息过载）
        developmental_perspective = {
            "capability_areas": [
                {
                    "area": area.get("area"),
                    "sub_areas": area.get("sub_areas", []),
                    "confidence": area.get("confidence", 0),
                    "evidence": [],  # 从行为描述中提取（后续优化）
                    "assessment_implications": area.get("assessment_tools", []),
                    "family_verification": area.get("family_verification", ""),
                    "developmental_milestone": area.get("developmental_milestone", "")
                }
                for area in capability_areas[:3]
            ]
        }
        
        result["developmental_perspective"] = developmental_perspective
        logger.info(f"V5.0 发展性视角映射完成：{len(developmental_perspective['capability_areas'])} 个能力领域")
        
        return result
    
    def _get_fallback_result(self, error: str) -> dict:
        """
        V4.3 降级方案：当分析失败时返回完整的兼容结构
        """
        return {
            "functional_judgment": "inconclusive",
            "core_insight": "孩子正在用这种方式表达他的需求或感受。",
            "capability_hypothesis": "相关技能还在发展中，需要我们的耐心支持。",
            "clinical_differential": "由于信息有限，无法进行详细的鉴别诊断。建议继续观察并收集更多信息。",
            "intervention_principle": "提供温和、一致的支持，观察孩子的反应模式。",
            "expert_breakdown": {
                "behavior_pattern": "待分析行为模式",
                "functional_hypothesis": "需要更多信息进行判断",
                "capability_gap": "相关技能还在发展中",
                "contextual_factors": "环境因素影响待评估"
            },
            "core_insight_for_parent": "孩子正在用这种方式表达他的需求或感受。",
            "strategy_principle": "提供温和、一致的支持，观察孩子的反应模式。",
            "reasoning_brief": f"分析过程出现异常：{error}",
        }
