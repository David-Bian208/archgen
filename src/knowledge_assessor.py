"""
知识评估模块 (Knowledge Assessor)

功能：
- 评估 AI 对特定话题的知识覆盖度（L0-L4）
- 返回评估结果 + 置信度 + 理由
- 支持缓存机制（避免重复评估）

设计原则：
- AI 自评：宁可降级，不要升级
- 缓存策略：L0 缓存 24h，L1 缓存 12h，L2/L3/L4 不缓存
- 对前端透明：集成到 supplement 接口内部

知识级别定义：
- L0: 知识充足（有具体案例/数据支撑）
- L1: 知识部分（知道通用模式，但缺少具体案例）
- L2: 知识稀疏（只能提出结构化问题）
- L3: 知识几乎没有（只能用类比推导）
- L4: 知识空白（只能提供逻辑框架）
"""

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 缓存目录
CACHE_DIR = Path(__file__).parent.parent / "data" / "assessment_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 缓存 TTL（秒）
CACHE_TTL = {
    "L0": 24 * 3600,    # 24 小时
    "L1": 12 * 3600,    # 12 小时
    "L2": 0,            # 不缓存
    "L3": 0,            # 不缓存
    "L4": 0,            # 不缓存
}

# 系统提示词（固定）
SYSTEM_PROMPT = """你是一个知识评估专家。请严格评估 AI 对该话题的知识覆盖度。

核心规则：
1. 必须输出 JSON 格式，不要包含其他内容
2. 知识级别必须是 L0/L1/L2/L3/L4 中的一个
3. 如果不确定，宁可降级，不要升级
4. 置信度必须是 high/medium/low 中的一个

知识级别定义：
- L0: 知识充足（能直接补充具体内容，且有具体案例/数据支撑）
- L1: 知识部分（能直接补充具体内容，但缺少具体案例/数据）
- L2: 知识稀疏（不能直接补充内容，但能提出结构化问题帮助用户）
- L3: 知识几乎没有（不能提出问题，但能用类比或框架帮助用户）
- L4: 知识空白（完全无法提供任何帮助）

输出格式：
{
  "knowledge_level": "L0",
  "reason": "评估理由",
  "confidence": "high"
}"""


class KnowledgeAssessor:
    """知识评估器"""

    def __init__(self, llm_config: Dict, cache_enabled: bool = True):
        self.llm_config = llm_config
        self.cache_enabled = cache_enabled

    def _build_cache_key(self, topic: str, context: str) -> str:
        """生成缓存 key"""
        content = f"{topic}:{context}"
        return hashlib.md5(content.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """获取缓存文件路径"""
        return CACHE_DIR / f"{cache_key}.json"

    def _load_cache(self, cache_key: str) -> Optional[Dict]:
        """加载缓存"""
        if not self.cache_enabled:
            return None

        cache_path = self._get_cache_path(cache_key)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)

            # 检查是否过期
            now = time.time()
            ttl = CACHE_TTL.get(cached.get("knowledge_level", "L1"), 12 * 3600)
            if now - cached.get("timestamp", 0) > ttl:
                cache_path.unlink()
                return None

            logger.info(f"使用缓存的评估结果: {cache_key[:8]}...")
            return cached

        except Exception as e:
            logger.warning(f"加载缓存失败: {e}")
            return None

    def _save_cache(self, cache_key: str, result: Dict):
        """保存缓存"""
        if not self.cache_enabled:
            return

        cache_path = self._get_cache_path(cache_key)
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存缓存失败: {e}")

    def clear_cache(self, cache_key: Optional[str] = None):
        """清除缓存"""
        if cache_key:
            cache_path = self._get_cache_path(cache_key)
            if cache_path.exists():
                cache_path.unlink()
        else:
            for cache_path in CACHE_DIR.glob("*.json"):
                cache_path.unlink()
            logger.info("已清除所有评估缓存")

    async def assess(
        self,
        topic: str,
        context: str,
        missing_items: Optional[List[Dict]] = None,
    ) -> Dict:
        """
        评估知识级别

        Args:
            topic: 话题/维度名称
            context: 上下文（文章 + 大纲）
            missing_items: 缺失项列表（可选）

        Returns:
            {
                "knowledge_level": "L0",
                "reason": "评估理由",
                "confidence": "high",
                "cached": true/false
            }
        """
        # 检查缓存
        cache_key = self._build_cache_key(topic, context)
        cached = self._load_cache(cache_key)
        if cached:
            cached["cached"] = True
            return cached

        # 构建评估 Prompt
        prompt = self._build_assessment_prompt(topic, context, missing_items)

        # 调用 LLM
        result = await self._call_llm(prompt)

        # 解析结果
        assessment = self._parse_result(result)

        # 保存到缓存
        assessment["timestamp"] = time.time()
        self._save_cache(cache_key, assessment)

        assessment["cached"] = False
        return assessment

    def _build_assessment_prompt(
        self,
        topic: str,
        context: str,
        missing_items: Optional[List[Dict]] = None,
    ) -> str:
        """构建评估 Prompt"""
        missing_items_str = ""
        if missing_items:
            missing_items_str = "\n\n【缺失项列表】\n"
            for item in missing_items:
                # 支持字符串和字典两种格式
                if isinstance(item, str):
                    missing_items_str += f"- {item}\n"
                else:
                    missing_items_str += f"- {item.get('dimension', '')}: {item.get('label', '')}\n"

        return f"""请评估 AI 对以下话题的知识覆盖度。

【话题】
{topic}

【上下文】
{context[:3000]}
{missing_items_str}

请严格根据以下判断流程评估：

【第一步：判断缺失项类型】
- 事实/数据/案例类（如：获客成本、转化率、具体案例、用户数、行业数据等）
  → 走「事实类判断流程」
- 概念/框架/方法类（如：定义、策略、画像、方法论、建议等）
  → 走「概念类判断流程」

【事实类判断流程】（⚠️ 关键：宁可降级，绝不编造）
1. 我有确切的数据/案例/资料支撑这个缺失项吗？
   - 有（能给出具体数字、真实案例、可验证来源） → L0
   - 没有（只知道大概、行业常识、但给不出具体数据） → 直接 L2
     理由：事实类数据不能靠推导，没有确切资料就去问用户

【概念类判断流程】
1. 我能直接补充具体内容吗？
   - 能 → 继续问：我补充的内容有具体案例/数据支撑吗？
     - 有 → L0
     - 没有 → L1（通用模式推导，但缺口需要用户补充细节）
   - 不能 → 继续问：我能提出结构化问题帮助用户吗？
     - 能 → L2
   - 不能 → 继续问：我能用类比或框架帮助用户吗？
     - 能 → L3
     - 不能 → L4

输出 JSON（不要其他内容）：
{{
  "knowledge_level": "L0/L1/L2/L3/L4",
  "reason": "评估理由（50 字以内）",
  "confidence": "high/medium/low"
}}"""

    def _parse_result(self, result: Dict) -> Dict:
        """解析 LLM 返回结果"""
        content = result.get("content", "")

        # 尝试提取 JSON
        try:
            # 尝试直接解析
            assessment = json.loads(content)
        except json.JSONDecodeError:
            # 尝试从 markdown 代码块中提取
            import re
            match = re.search(r'```(?:json)?\s*\n(.*?)\n```', content, re.DOTALL)
            if match:
                try:
                    assessment = json.loads(match.group(1))
                except json.JSONDecodeError:
                    assessment = {}
            else:
                assessment = {}

        # 验证必填字段
        knowledge_level = assessment.get("knowledge_level", "L1")
        if knowledge_level not in ["L0", "L1", "L2", "L3", "L4"]:
            logger.warning(f"知识级别无效: {knowledge_level}，默认 L1")
            knowledge_level = "L1"

        return {
            "knowledge_level": knowledge_level,
            "reason": assessment.get("reason", ""),
            "confidence": assessment.get("confidence", "medium"),
        }

    async def _call_llm(self, prompt: str) -> Dict:
        """调用 LLM"""
        import httpx

        base_url = self.llm_config.get("base_url", "https://api.deepseek.com/v1")
        api_key = self.llm_config.get("api_key", "")
        model = self.llm_config.get("model", "deepseek-chat")
        timeout = self.llm_config.get("timeout", 30)  # 评估超时较短

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": 256,
                        "temperature": 0.1,  # 低温度，保证一致性
                        "seed": 42,
                    },
                )
                response.raise_for_status()
                result = response.json()

            content = result["choices"][0]["message"]["content"].strip()
            return {"content": content, "usage": result.get("usage", {})}

        except Exception as e:
            logger.error(f"知识评估 LLM 调用失败: {e}")
            # 降级到 L1（保守策略）
            return {
                "content": '{"knowledge_level": "L1", "reason": "LLM 调用失败，保守降级", "confidence": "low"}',
                "usage": {},
            }


def get_knowledge_assessor(llm_config: Dict, cache_enabled: bool = True) -> KnowledgeAssessor:
    """获取知识评估器实例"""
    return KnowledgeAssessor(llm_config, cache_enabled)
