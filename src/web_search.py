"""
Web 搜索模块（DuckDuckGo，通过 ddgs 包）
用于补充环节：MCP 知识库不足时，通过 Web 搜索获取外部案例/数据

依赖：pip install ddgs
"""
import logging
from typing import List, Dict
from ddgs import DDGS

logger = logging.getLogger(__name__)


async def search_web(query: str, max_results: int = 5) -> List[Dict]:
    """
    通过 DuckDuckGo 搜索网页

    Args:
        query: 搜索关键词
        max_results: 最大返回数量

    Returns:
        List[Dict]: 搜索结果 [{"title", "url", "snippet", "source"}]
    """
    if not query or len(query.strip()) < 2:
        return []

    logger.info(f"[WebSearch] 搜索: {query}")

    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")[:300],
                    "source": "web_search",
                })
        logger.info(f"[WebSearch] 成功: {len(results)} 条结果")
        return results
    except Exception as e:
        logger.warning(f"[WebSearch] 搜索失败: {e}")
        return []


async def search_web_batch(queries: List[str], max_per_query: int = 3) -> List[Dict]:
    """
    批量搜索多个关键词

    Args:
        queries: 搜索关键词列表
        max_per_query: 每个关键词最大返回数

    Returns:
        List[Dict]: 去重后的搜索结果
    """
    all_results = []
    seen_urls = set()

    for q in queries[:3]:  # 最多3个关键词
        results = await search_web(q, max_results=max_per_query)
        for r in results:
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                all_results.append(r)

    return all_results


def format_search_results(results: List[Dict]) -> str:
    """格式化搜索结果为 LLM prompt 可用的文本"""
    if not results:
        return ""

    lines = []
    for i, r in enumerate(results, 1):
        lines.append(
            f"{i}. 【{r['title']}】\n"
            f"   来源：{r.get('url', '')}\n"
            f"   摘要：{r.get('snippet', '')}"
        )
    return "\n".join(lines)
