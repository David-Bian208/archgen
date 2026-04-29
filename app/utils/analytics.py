"""
使用统计模块
用于收集匿名用户行为统计数据
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class Analytics:
    """使用统计类"""

    def __init__(self, log_file: str = "analytics.log"):
        """
        初始化统计模块

        Args:
            log_file: 日志文件路径
        """
        self.log_file = Path(log_file)
        self._ensure_log_file()

    def _ensure_log_file(self):
        """确保日志文件存在"""
        if not self.log_file.parent.exists():
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_file.exists():
            self.log_file.write_text("[]")

    def track_usage(self, event_type: str, data: Optional[Dict[str, Any]] = None):
        """
        记录使用统计

        Args:
            event_type: 事件类型
            data: 附加数据
        """
        try:
            # 读取现有日志
            with open(self.log_file, "r", encoding="utf-8") as f:
                logs = json.load(f)

            # 创建新日志条目
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "data": data or {}
            }

            # 添加新条目
            logs.append(log_entry)

            # 限制日志大小（只保留最近 1000 条）
            if len(logs) > 1000:
                logs = logs[-1000:]

            # 写回日志文件
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)

            logger.info(f"使用统计记录：{event_type}")
        except Exception as e:
            logger.error(f"记录使用统计失败：{e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计数据

        Returns:
            统计数据
        """
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                logs = json.load(f)

            # 统计事件类型
            event_counts = {}
            for log in logs:
                event_type = log.get("event_type")
                if event_type:
                    event_counts[event_type] = event_counts.get(event_type, 0) + 1

            return {
                "total_events": len(logs),
                "event_counts": event_counts,
                "last_event": logs[-1] if logs else None
            }
        except Exception as e:
            logger.error(f"获取统计数据失败：{e}")
            return {"error": str(e)}


# 全局统计实例
_analytics: Optional[Analytics] = None


def get_analytics() -> Analytics:
    """获取全局统计实例"""
    global _analytics
    if _analytics is None:
        _analytics = Analytics()
    return _analytics


def track_usage(event_type: str, data: Optional[Dict[str, Any]] = None):
    """记录使用统计的便捷函数"""
    analytics = get_analytics()
    analytics.track_usage(event_type, data)


def get_stats() -> Dict[str, Any]:
    """获取统计数据的便捷函数"""
    analytics = get_analytics()
    return analytics.get_stats()