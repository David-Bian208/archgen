"""
降级链模块 (Degradation Chain)

功能：
- 根据知识级别（L0-L4）生成不同形式的补充内容
- L0: 具体内容 + 案例/数据
- L1: 通用模式 + 缺口标注
- L2: 结构化问题（3-5 个）
- L3: 类比推导
- L4: 逻辑框架

设计原则：
- 降级不可逆（L2 不会升级到 L1）
- 最大降级次数：2 次
- L4 时用户不满意 → 直接提示手动输入

输出格式：
{
    "knowledge_level": "L0",
    "content": "补充内容",
    "questions": [],        // L2 使用
    "analogy": "",          // L3 使用
    "framework": {},        // L4 使用
    "alert_message": "",    // 降级提示
    "source_tag": "",       // 来源标签
    "reevaluate": true/false // 是否需要重新评估
}
"""

import logging
from typing import Dict, List, Optional
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config.model_config import get_model_for_scene, V4_FLASH

logger = logging.getLogger(__name__)

# ===== 事实类缺失项检测 =====
# 事实/案例/数据类缺失项：检索无结果时拒补，避免幻觉

FACT_MISSING_KEYWORDS = [
    "数据", "数字", "统计", "转化率", "增长", "下降", "百分比",
    "案例", "实践", "实践案例", "真实案例", "客户案例",
    "公司", "企业", "品牌", "产品名", "人名",
    "时间", "年份", "金额", "收入", "利润", "成本",
    "指标", "KPI", "基准", "参考值",
]

CONCEPT_MISSING_KEYWORDS = [
    "定义", "概念", "框架", "结构", "逻辑", "思路",
    "画像", "定位", "目标", "策略", "方法",
    "建议", "规划", "方向", "趋势", "洞察",
]


def is_fact_missing_item(missing_item) -> bool:
    """
    判断缺失项是否属于事实/案例/数据类

    规则：
    - 检查维度、标签、描述中是否包含事实类关键词
    - 如果包含事实类关键词，认为是事实类缺失项

    Args:
        missing_item: 缺失项详情（可以是字符串或字典）

    Returns:
        True = 事实类（需要检索结果才能生成）
        False = 概念/框架类（可用降级链生成）
    """
    if not missing_item:
        return False

    # 支持字符串和字典两种格式
    if isinstance(missing_item, str):
        text = missing_item
    else:
        text = " ".join([
            missing_item.get("dimension", ""),
            missing_item.get("label", ""),
            missing_item.get("description", ""),
            missing_item.get("name", ""),
        ])

    text_lower = text.lower()

    # 先检查概念类关键词（优先级高于事实类）
    # 如果明确是概念/框架类，即使包含"数据"等词也不视为事实类
    for keyword in CONCEPT_MISSING_KEYWORDS:
        if keyword in text:
            return False

    # 检查事实类关键词
    for keyword in FACT_MISSING_KEYWORDS:
        if keyword in text_lower:
            return True

    return False


def generate_refusal_response(topic: str) -> Dict:
    """
    生成拒补响应（事实类缺失项无检索结果时）

    Returns:
        {
            "knowledge_level": "L2",
            "content": "",
            "mode": "refuse",
            "reason": "未检索到相关资料",
            "questions": [...],  # 引导问题
            "alert_message": "...",
            "source_tag": {...}
        }
    """
    return {
        "knowledge_level": "L2",
        "content": "",
        "mode": "refuse",
        "reason": "未检索到相关资料，无法生成事实性补充内容",
        "questions": [
            {
                "question": f"关于「{topic}」，您有哪些具体的数据或案例可以补充？",
                "hint": "例如：行业报告数据、公司内部数据、客户案例等"
            },
            {
                "question": f"这个「{topic}」对您的业务有什么具体影响？",
                "hint": "例如：影响了转化率、增加了成本、带来了新机会等"
            },
            {
                "question": f"您希望读者通过「{topic}」了解什么核心信息？",
                "hint": "例如：某个方法的可行性、某个趋势的确定性等"
            }
        ],
        "alert_message": "️ 该缺失项需要事实/数据支撑，当前未检索到相关资料",
        "source_tag": {"text": " 无数据支撑（需手动补充）", "color": "red"},
        "reevaluate": False,
    }

# 降级提示文案
ALERT_MESSAGES = {
    "L0": "",  # L0 不显示提示
    "L1": "💡 基于通用模式推导，部分内容需要你补充",
    "L2": "⚠️ 这个话题 AI 知识有限，以下基于通用模式推导",
    "L3": "💡 这个话题超出 AI 知识范围，以下基于类比推导",
    "L4": "⚠️ 这个话题超出 AI 知识范围，建议你先提供相关资料",
}

# 来源标签
SOURCE_TAGS = {
    "L0": {"text": "✅ 知识充足（有案例支撑）", "color": "green"},
    "L1": {"text": "⚠️ 通用模式（需补充细节）", "color": "blue"},
    "L2": {"text": "❓ 知识有限（建议提问）", "color": "orange"},
    "L3": {"text": "🔗 类比推导（需验证）", "color": "gray"},
    "L4": {"text": "📐 逻辑框架（需填写）", "color": "gray"},
}

# 系统提示词模板
SYSTEM_PROMPTS = {
    "L0": """你是一个内容补充专家。请提供具体、有依据的补充内容。

【强制规则】
每个事实性陈述必须标注来源，使用以下格式：
  [原文] → 从用户原文/MCP摘要推导
  [检索] → 从 API 案例/知识库获取（需附来源名）
  [推断] → LLM 自身推断（无外部支撑）

示例："深度学习模型调优需要关注学习率（[检索] MCP知识库《模型调优指南》）"

【要求】
1. [推断] 内容占比不得超过 30%
2. 标注为 [检索] 但无对应检索结果的视为幻觉，禁止输出
3. 语言简洁，直接可用""",

    "L1": """你是一个内容补充专家，知道通用模式但缺少具体案例。
请提供通用模式的补充内容，并标注需要用户补充的缺口。

【强制规则】
每个事实性陈述必须标注来源：[原文]/[检索]/[推断]

【要求】
1. 提供通用模式/框架
2. 明确标注哪些部分需要用户补充具体案例
3. 使用 [📌 待补充：xxx] 格式标注缺口""",

    "L2": """你是一个引导者，AI 知识有限，但能提出好的问题。
请提出 3-5 个结构化问题，帮助用户自己思考。
要求：
1. 问题必须有引导性，帮助用户理清思路
2. 每个问题附带简短说明（为什么要问这个问题）
3. 问题由浅入深，循序渐进""",

    "L3": """你是一个类比推导者，AI 知识几乎没有。
请用类比的方式帮助用户理解这个话题。
要求：
1. 找一个用户熟悉的领域做类比
2. 解释类比的相似点和差异点
3. 明确告知这是类比推导，需要用户验证""",

    "L4": """你是一个框架提供者，AI 完全不知道这个话题。
请提供一个逻辑框架，让用户自己填写。
要求：
1. 提供 3-5 个思考维度
2. 每个维度附带简短提示（这个维度应该考虑什么）
3. 明确告知这是空框架，需要用户填写""",
}


class DegradationChain:
    """降级链处理器"""

    def __init__(self, llm_config: Dict):
        self.llm_config = llm_config

    async def generate(
        self,
        knowledge_level: str,
        topic: str,
        context: str,
        missing_item: Optional[Dict] = None,
        retrieval_results: Optional[List[Dict]] = None,
    ) -> Dict:
        """
        根据知识级别生成补充内容

        Args:
            knowledge_level: L0/L1/L2/L3/L4
            topic: 话题/维度名称
            context: 上下文（文章 + 大纲）
            missing_item: 缺失项详情
            retrieval_results: 检索结果列表（可选）

        Returns:
            补充结果字典
        """
        # 验证知识级别
        if knowledge_level not in ["L0", "L1", "L2", "L3", "L4"]:
            logger.warning(f"无效的知识级别: {knowledge_level}，默认 L1")
            knowledge_level = "L1"

        # ===== 事实类熔断拦截 =====
        # 事实/数据/案例类缺失项，L1/L3 级别强制降级，避免幻觉
        # L1 事实类 → L2（别编，去问用户）
        # L3 事实类 → L4（别类比，给空框架）
        if knowledge_level in ["L1", "L3"] and missing_item and is_fact_missing_item(missing_item):
            old_level = knowledge_level
            if knowledge_level == "L1":
                knowledge_level = "L2"
                logger.info(
                    f"事实类熔断: {topic} 原为 L1(通用推导)，"
                    f"因缺失项为事实类，降级为 L2(引导提问)"
                )
            else:  # L3
                knowledge_level = "L4"
                logger.info(
                    f"事实类熔断: {topic} 原为 L3(类比推导)，"
                    f"因缺失项为事实类，降级为 L4(空框架)"
                )

        # 构建 Prompt
        prompt = self._build_prompt(knowledge_level, topic, context, missing_item, retrieval_results)
        system_prompt = SYSTEM_PROMPTS[knowledge_level]

        # 调用 LLM
        result = await self._call_llm(system_prompt, prompt)

        # 解析结果
        supplement = self._parse_result(knowledge_level, result)

        # 添加元数据
        supplement["knowledge_level"] = knowledge_level
        supplement["alert_message"] = ALERT_MESSAGES[knowledge_level]
        supplement["source_tag"] = SOURCE_TAGS[knowledge_level]
        supplement["reevaluate"] = self._should_reevaluate(knowledge_level)

        return supplement

    def _build_prompt(
        self,
        knowledge_level: str,
        topic: str,
        context: str,
        missing_item: Optional[Dict] = None,
        retrieval_results: Optional[List[Dict]] = None,
    ) -> str:
        """构建生成 Prompt"""
        missing_info = ""
        if missing_item:
            # 支持字符串和字典两种格式
            if isinstance(missing_item, str):
                missing_info = f"""
【缺失项】
{missing_item}
"""
            else:
                missing_info = f"""
【缺失项详情】
维度：{missing_item.get('dimension', '')}
标签：{missing_item.get('label', '')}
描述：{missing_item.get('description', '')}
"""

        # 检索结果
        retrieval_info = ""
        if retrieval_results:
            retrieval_info = "\n【检索结果】\n"
            for i, r in enumerate(retrieval_results[:5], 1):  # 最多5条
                title = r.get("title", r.get("name", ""))
                snippet = r.get("snippet", r.get("content", ""))[:200]
                source = r.get("source", r.get("url", ""))
                retrieval_info += f"{i}. {title}\n   来源: {source}\n   摘要: {snippet}\n\n"
        else:
            retrieval_info = "\n【检索结果】\n无\n"

        return f"""请为以下话题生成补充内容。

【话题】
{topic}

【上下文】
{context[:3000]}
{missing_info}{retrieval_info}
请严格按照你的知识级别（{knowledge_level}）的要求生成内容。
输出 JSON 格式（不要其他内容）。"""

    def _parse_result(self, knowledge_level: str, result: Dict) -> Dict:
        """解析 LLM 返回结果"""
        content = result.get("content", "")

        # 根据知识级别解析不同格式
        if knowledge_level in ["L0", "L1"]:
            return self._parse_content_result(content)
        elif knowledge_level == "L2":
            return self._parse_questions_result(content)
        elif knowledge_level == "L3":
            return self._parse_analogy_result(content)
        else:  # L4
            return self._parse_framework_result(content)

    def _parse_content_result(self, content: str) -> Dict:
        """解析 L0/L1 结果（内容型）"""
        import json
        import re

        try:
            data = json.loads(content)
            return {
                "content": data.get("content", content),
                "evidence_quote": data.get("evidence_quote", ""),
                "gap_hint": data.get("gap_hint", ""),  # L1 专用
            }
        except json.JSONDecodeError:
            match = re.search(r'```(?:json)?\s*\n(.*?)\n```', content, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    return {
                        "content": data.get("content", content),
                        "evidence_quote": data.get("evidence_quote", ""),
                        "gap_hint": data.get("gap_hint", ""),
                    }
                except json.JSONDecodeError:
                    pass

        return {"content": content, "evidence_quote": "", "gap_hint": ""}

    def _parse_questions_result(self, content: str) -> Dict:
        """解析 L2 结果（问题型）"""
        import json
        import re

        try:
            data = json.loads(content)
            questions = data.get("questions", [])
            if isinstance(questions, list) and len(questions) > 0:
                return {"questions": questions, "content": ""}
        except json.JSONDecodeError:
            match = re.search(r'```(?:json)?\s*\n(.*?)\n```', content, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    questions = data.get("questions", [])
                    if isinstance(questions, list) and len(questions) > 0:
                        return {"questions": questions, "content": ""}
                except json.JSONDecodeError:
                    pass

        # 解析失败，从文本提取问题
        questions = self._extract_questions_from_text(content)
        return {"questions": questions, "content": content}

    def _extract_questions_from_text(self, text: str) -> List[Dict]:
        """从文本中提取问题（备用方案）"""
        import re

        questions = []
        # 匹配 "1. xxx" 或 "- xxx" 或 "Q: xxx" 格式
        patterns = [
            r'(\d+)\.\s*(.+?)(?=\d+\.|$)',
            r'[-*]\s*(.+?)(?=[-*]|$)',
            r'[？?]\s*(.+?)(?=[？?]|$)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                for i, match in enumerate(matches[:5]):  # 最多 5 个
                    if isinstance(match, tuple):
                        q_text = match[1].strip()
                    else:
                        q_text = match.strip()
                    if q_text:
                        questions.append({
                            "question": q_text,
                            "hint": "请思考这个问题并记录你的想法",
                        })
                break

        if not questions:
            questions = [{"question": text[:200], "hint": "请思考这个问题"}]

        return questions

    def _parse_analogy_result(self, content: str) -> Dict:
        """解析 L3 结果（类比型）"""
        import json
        import re

        try:
            data = json.loads(content)
            return {
                "analogy": data.get("analogy", content),
                "analogy_explanation": data.get("explanation", ""),
                "content": "",
            }
        except json.JSONDecodeError:
            match = re.search(r'```(?:json)?\s*\n(.*?)\n```', content, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    return {
                        "analogy": data.get("analogy", content),
                        "analogy_explanation": data.get("explanation", ""),
                        "content": "",
                    }
                except json.JSONDecodeError:
                    pass

        return {"analogy": content, "analogy_explanation": "", "content": ""}

    def _parse_framework_result(self, content: str) -> Dict:
        """解析 L4 结果（框架型）"""
        import json
        import re

        try:
            data = json.loads(content)
            dimensions = data.get("dimensions", [])
            if isinstance(dimensions, list) and len(dimensions) > 0:
                return {"framework": {"dimensions": dimensions}, "content": ""}
        except json.JSONDecodeError:
            match = re.search(r'```(?:json)?\s*\n(.*?)\n```', content, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    dimensions = data.get("dimensions", [])
                    if isinstance(dimensions, list) and len(dimensions) > 0:
                        return {"framework": {"dimensions": dimensions}, "content": ""}
                except json.JSONDecodeError:
                    pass

        # 解析失败，从文本提取维度
        dimensions = self._extract_dimensions_from_text(content)
        return {"framework": {"dimensions": dimensions}, "content": content}

    def _extract_dimensions_from_text(self, text: str) -> List[Dict]:
        """从文本中提取维度（备用方案）"""
        import re

        dimensions = []
        # 匹配 "维度 1: xxx" 或 "1. xxx" 格式
        pattern = r'(?:维度 [\d一二三四五]+[:：]?)\s*(.+?)(?=维度|[\d一二三四五]+\.|$)'
        matches = re.findall(pattern, text, re.DOTALL)

        if matches:
            for i, match in enumerate(matches[:5]):
                dimensions.append({
                    "name": f"维度 {i+1}",
                    "hint": match.strip()[:100],
                })
        else:
            # 通用列表匹配
            pattern = r'[-*•]\s*(.+?)(?=[-*•]|$)'
            matches = re.findall(pattern, text, re.DOTALL)
            for i, match in enumerate(matches[:5]):
                dimensions.append({
                    "name": f"维度 {i+1}",
                    "hint": match.strip()[:100],
                })

        if not dimensions:
            dimensions = [{"name": "思考维度", "hint": text[:100]}]

        return dimensions

    def _should_reevaluate(self, knowledge_level: str) -> bool:
        """
        判断是否需要重新评估

        规则：
        - L0/L1: 重新评估（因为补充了具体内容，需要验证质量）
        - L2/L3/L4: 不重新评估（因为输出的是问题/类比/框架，不需要评估质量）
        """
        return knowledge_level in ["L0", "L1"]

    async def _call_llm(self, system_prompt: str, prompt: str) -> Dict:
        """调用 LLM
        [V4] 有意保持独立 _call_llm（非 api._call_llm）：
        原因：避免循环导入（api.py 导入本模块），且降级链无需 session 思考日志
        已通过 get_model_for_scene("degradation_generate") 使用 V4-Flash
        """
        import httpx

        base_url = self.llm_config.get("base_url", "https://api.deepseek.com/v1")
        api_key = self.llm_config.get("api_key", "")
        model = get_model_for_scene("degradation_generate")
        timeout = self.llm_config.get("timeout", 60)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": 2048,
                        "temperature": 0.3,
                        "seed": 42,
                    },
                )
                response.raise_for_status()
                result = response.json()

            content = result["choices"][0]["message"]["content"].strip()
            return {"content": content, "usage": result.get("usage", {})}

        except Exception as e:
            logger.error(f"降级链 LLM 调用失败: {e}")
            return {"content": "", "usage": {}}


class DegradationManager:
    """降级管理器（处理用户不满意的降级逻辑）"""

    MAX_DEGRADATION_COUNT = 2

    def __init__(self, llm_config: Dict):
        self.chain = DegradationChain(llm_config)

    async def degrade(
        self,
        current_level: str,
        topic: str,
        context: str,
        missing_item: Optional[Dict] = None,
    ) -> Dict:
        """
        降级一级并重新生成

        Args:
            current_level: 当前知识级别
            topic: 话题
            context: 上下文
            missing_item: 缺失项

        Returns:
            降级后的补充结果
        """
        # 降级一级
        new_level = self._get_next_level(current_level)

        if new_level is None:
            # 已经是 L4，不能再降
            return {
                "knowledge_level": "L4",
                "content": "这个话题 AI 知识有限，建议你手动补充。",
                "alert_message": "⚠️ 已达降级上限，建议手动输入",
                "source_tag": SOURCE_TAGS["L4"],
                "reevaluate": False,
                "can_degrade": False,
            }

        # 生成降级内容
        result = await self.chain.generate(new_level, topic, context, missing_item)
        result["can_degrade"] = new_level != "L4"

        return result

    def _get_next_level(self, current_level: str) -> Optional[str]:
        """获取下一级（降级方向）"""
        level_order = ["L0", "L1", "L2", "L3", "L4"]
        current_index = level_order.index(current_level) if current_level in level_order else 0

        if current_index >= len(level_order) - 1:
            return None  # 已经是 L4

        return level_order[current_index + 1]


def get_degradation_chain(llm_config: Dict) -> DegradationChain:
    """获取降级链实例"""
    return DegradationChain(llm_config)


def get_degradation_manager(llm_config: Dict) -> DegradationManager:
    """获取降级管理器实例"""
    return DegradationManager(llm_config)
