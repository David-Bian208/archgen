"""
未知表达日志器 V4.5.1

功能：
1. 记录未被识别的用户表达
2. 当同一表达出现多次时，自动告警
3. 提供定期审查和扩展关键词的机制
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class UnknownExpressionLogger:
    """未知表达日志器"""
    
    def __init__(self, log_path: str = "app/logs/unknown_expressions.json"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()
    
    def _load(self) -> dict:
        """加载日志数据"""
        if self.log_path.exists():
            with open(self.log_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"expressions": {}, "last_review": None}
    
    def _save(self) -> None:
        """保存日志数据"""
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def log_unknown(self, user_input: str, context: dict) -> None:
        """
        记录未知表达
        
        Args:
            user_input: 用户输入
            context: 上下文信息（session_id, field, timestamp 等）
        """
        # 规范化表达（去除空格、标点）
        normalized = self._normalize(user_input)
        
        if normalized not in self.data["expressions"]:
            self.data["expressions"][normalized] = {
                "original": user_input,
                "count": 0,
                "first_seen": datetime.now().isoformat(),
                "last_seen": None,
                "contexts": [],
                "suggested_category": None,
                "reviewed": False,
            }
        
        entry = self.data["expressions"][normalized]
        entry["count"] += 1
        entry["last_seen"] = datetime.now().isoformat()
        entry["contexts"].append({
            "session_id": context.get("session_id", "unknown"),
            "field": context.get("field", "unknown"),
            "timestamp": datetime.now().isoformat(),
        })
        
        # 限制上下文数量
        if len(entry["contexts"]) > 10:
            entry["contexts"] = entry["contexts"][-10:]
        
        self._save()
        
        # 如果同一表达出现 3 次以上，告警
        if entry["count"] >= 3 and not entry["reviewed"]:
            logger.warning(f"⚠️ 未知表达高频出现：{user_input} (已出现{entry['count']}次)")
    
    def _normalize(self, text: str) -> str:
        """规范化文本"""
        import re
        # 移除空格、标点
        text = re.sub(r'[\s\p{P}]+', '', text, flags=re.UNICODE)
        return text.lower()
    
    def get_frequent_unknowns(self, min_count: int = 3) -> List[dict]:
        """获取高频未知表达"""
        frequent = []
        for normalized, entry in self.data["expressions"].items():
            if entry["count"] >= min_count and not entry["reviewed"]:
                frequent.append({
                    "expression": entry["original"],
                    "count": entry["count"],
                    "first_seen": entry["first_seen"],
                    "last_seen": entry["last_seen"],
                    "contexts": entry["contexts"][-3:],  # 最近 3 次
                })
        
        # 按出现次数排序
        frequent.sort(key=lambda x: x["count"], reverse=True)
        return frequent
    
    def mark_reviewed(self, expression: str, suggested_category: str) -> None:
        """标记为已审查"""
        normalized = self._normalize(expression)
        if normalized in self.data["expressions"]:
            self.data["expressions"][normalized]["reviewed"] = True
            self.data["expressions"][normalized]["suggested_category"] = suggested_category
            self._save()
    
    def get_review_report(self) -> dict:
        """生成审查报告"""
        frequent = self.get_frequent_unknowns()
        return {
            "total_unknown_expressions": len(self.data["expressions"]),
            "frequent_unknowns": frequent,
            "last_review": self.data.get("last_review"),
            "review_needed": len(frequent) > 0,
        }


# 全局实例
_unknown_logger: Optional[UnknownExpressionLogger] = None


def get_unknown_logger() -> UnknownExpressionLogger:
    """获取全局未知表达日志器"""
    global _unknown_logger
    if _unknown_logger is None:
        _unknown_logger = UnknownExpressionLogger()
    return _unknown_logger


def log_unknown_expression(user_input: str, context: dict) -> None:
    """便捷函数：记录未知表达"""
    logger = get_unknown_logger()
    logger.log_unknown(user_input, context)


def get_unknown_report() -> dict:
    """便捷函数：获取未知表达报告"""
    logger = get_unknown_logger()
    return logger.get_review_report()
