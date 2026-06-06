"""
AI-Pulse API 客户端模块

功能：
- 获取最新案例（fetch_latest_cases）
- 获取行业数据（fetch_industry_data）
- 获取日报（fetch_daily_report）

API 端点（v1.6 公开 API）：
- 基础 URL: http://8.130.148.166:8887
- /api/public/items - 获取内容列表（无鉴权）
- /api/public/daily - 获取最新日报（无鉴权）
- /api/public/daily/{date} - 获取指定日期日报
- /api/public/dailies - 获取日报列表
"""

import logging
import httpx
from typing import List, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AIPulseClient:
    """AI-Pulse API 客户端"""

    def __init__(self, base_url: str = "http://8.130.148.166:8887", timeout: int = 10):
        self.base_url = base_url
        self.timeout = timeout

    async def fetch_latest_cases(
        self, keywords: List[str], days: int = 7, take: int = 10
    ) -> List[Dict]:
        """
        获取最新案例

        Args:
            keywords: 关键词列表
            days: 时间范围（天）
            take: 返回数量

        Returns:
            List[Dict]: 案例列表
        """
        # 构建查询参数
        q = " ".join(keywords) if keywords else ""
        time_filter = "week" if days <= 7 else "month" if days <= 30 else "all"
        
        url = f"{self.base_url}/api/public/items"
        params = {
            "q": q,
            "time_filter": time_filter,
            "take": take,
        }
        
        logger.info(f"请求 AI-Pulse API: {url}, params={params}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                # 解析返回数据
                if data.get("code") == 0:
                    items = data.get("items", [])
                    logger.info(f"成功获取 {len(items)} 条案例")
                    return [
                        {
                            "id": str(item.get("id", "")),
                            "title": item.get("title", ""),
                            "summary": item.get("summary", ""),
                            "source": item.get("source", ""),
                            "published_at": item.get("publish_date", ""),
                            "score": item.get("final_score", 0),
                            "category": item.get("category", ""),
                            "url": item.get("url", ""),
                            "tags": item.get("tags", []) or [],
                        }
                        for item in items
                    ]
                else:
                    logger.warning(f"API 返回错误：{data.get('msg', 'unknown error')}")
                    return []
        except httpx.HTTPError as e:
            logger.error(f"HTTP 请求失败：{e}")
            return []
        except Exception as e:
            logger.error(f"获取案例失败：{e}")
            return []

    async def fetch_industry_data(
        self, category: str, days: int = 30, take: int = 20
    ) -> List[Dict]:
        """
        获取行业数据

        Args:
            category: 行业分类
            days: 时间范围（天）
            take: 返回数量

        Returns:
            List[Dict]: 行业数据列表
        """
        url = f"{self.base_url}/api/public/items"
        params = {
            "category": category,
            "time_filter": "month" if days <= 30 else "all",
            "take": take,
        }
        
        logger.info(f"请求 AI-Pulse API: {url}, params={params}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if data.get("code") == 0:
                    items = data.get("items", [])
                    logger.info(f"成功获取 {len(items)} 条行业数据")
                    return [
                        {
                            "id": str(item.get("id", "")),
                            "title": item.get("title", ""),
                            "summary": item.get("summary", ""),
                            "source": item.get("source", ""),
                            "published_at": item.get("publish_date", ""),
                            "score": item.get("final_score", 0),
                            "category": item.get("category", ""),
                            "url": item.get("url", ""),
                            "tags": item.get("tags", []) or [],
                        }
                        for item in items
                    ]
                else:
                    logger.warning(f"API 返回错误：{data.get('msg', 'unknown error')}")
                    return []
        except httpx.HTTPError as e:
            logger.error(f"HTTP 请求失败：{e}")
            return []
        except Exception as e:
            logger.error(f"获取行业数据失败：{e}")
            return []

    async def fetch_daily_report(self, date: Optional[str] = None) -> Dict:
        """
        获取日报

        Args:
            date: 日期（YYYY-MM-DD），None 表示今日

        Returns:
            Dict: 日报内容
        """
        if date is None:
            # 获取最新日报
            url = f"{self.base_url}/api/public/daily"
        else:
            # 获取指定日期日报
            url = f"{self.base_url}/api/public/daily/{date}"
        
        logger.info(f"请求 AI-Pulse API: {url}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                
                if data.get("code") == 0:
                    logger.info(f"成功获取日报：{data.get('date', 'unknown')}")
                    return data
                else:
                    logger.warning(f"API 返回错误：{data.get('msg', 'unknown error')}")
                    return {}
        except httpx.HTTPError as e:
            logger.error(f"HTTP 请求失败：{e}")
            return {}
        except Exception as e:
            logger.error(f"获取日报失败：{e}")
            return {}


def get_ai_pulse_client(config: Optional[Dict] = None) -> AIPulseClient:
    """
    获取 AI-Pulse 客户端实例

    Args:
        config: 配置字典，包含 base_url 和 timeout

    Returns:
        AIPulseClient 实例
    """
    if config is None:
        config = {}
    base_url = config.get("base_url", "http://8.130.148.166:8887")
    timeout = config.get("timeout", 10)
    return AIPulseClient(base_url=base_url, timeout=timeout)
