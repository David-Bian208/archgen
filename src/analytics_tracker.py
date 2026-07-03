"""
埋点追踪模块 (Analytics Tracker)

功能：
- 采集补充事件数据
- 存储到 SQLite 数据库
- 提供查询接口用于数据看板

数据表：
- supplement_events: 补充事件记录
- supplement_sessions: 会话级汇总
"""

import logging
import aiosqlite
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# 数据库路径
DB_PATH = Path(__file__).parent.parent / "data" / "analytics.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class AnalyticsTracker:
    """埋点追踪器"""

    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def init_db(self):
        """初始化数据库表"""
        async with aiosqlite.connect(str(self.db_path)) as db:
            # 补充事件表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS supplement_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,  -- supplement_start, supplement_complete, degrade, confirm, cancel
                    timestamp TEXT NOT NULL,
                    
                    -- 补充上下文
                    topic TEXT,
                    knowledge_level TEXT,  -- L0/L1/L2/L3/L4
                    assessment_confidence TEXT,  -- high/medium/low
                    assessment_cached BOOLEAN,
                    
                    -- 补充结果
                    content_length INTEGER,
                    has_evidence BOOLEAN,
                    has_gap_hint BOOLEAN,
                    questions_count INTEGER,
                    reevaluate BOOLEAN,
                    can_degrade BOOLEAN,
                    
                    -- 用户行为
                    user_action TEXT,  -- confirm, edit, degrade, cancel
                    degradation_count INTEGER DEFAULT 0,
                    
                    -- 元数据
                    metadata TEXT  -- JSON 字符串
                )
            """)
            
            # 会话级汇总表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS supplement_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL UNIQUE,
                    total_supplements INTEGER DEFAULT 0,
                    l0_count INTEGER DEFAULT 0,
                    l1_count INTEGER DEFAULT 0,
                    l2_count INTEGER DEFAULT 0,
                    l3_count INTEGER DEFAULT 0,
                    l4_count INTEGER DEFAULT 0,
                    total_degradations INTEGER DEFAULT 0,
                    confirm_rate REAL DEFAULT 0.0,
                    avg_content_length REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # 索引
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_session ON supplement_events(session_id)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_timestamp ON supplement_events(timestamp)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_knowledge_level ON supplement_events(knowledge_level)
            """)
            
            await db.commit()
        
        logger.info(f"埋点数据库初始化完成: {self.db_path}")

    async def record_event(self, event: Dict):
        """
        记录补充事件
        
        Args:
            event: 事件数据
            {
                "session_id": "xxx",
                "event_type": "supplement_complete",
                "topic": "话题",
                "knowledge_level": "L0",
                "assessment_confidence": "high",
                "assessment_cached": false,
                "content_length": 500,
                "has_evidence": true,
                "has_gap_hint": false,
                "questions_count": 0,
                "reevaluate": true,
                "can_degrade": true,
                "user_action": null,
                "degradation_count": 0,
                "metadata": {}
            }
        """
        timestamp = event.get("timestamp", datetime.now().isoformat())
        metadata = json.dumps(event.get("metadata", {}), ensure_ascii=False)
        
        async with aiosqlite.connect(str(self.db_path)) as db:
            await db.execute("""
                INSERT INTO supplement_events (
                    session_id, event_type, timestamp,
                    topic, knowledge_level, assessment_confidence, assessment_cached,
                    content_length, has_evidence, has_gap_hint,
                    questions_count, reevaluate, can_degrade,
                    user_action, degradation_count, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.get("session_id", ""),
                event.get("event_type", ""),
                timestamp,
                event.get("topic", ""),
                event.get("knowledge_level", ""),
                event.get("assessment_confidence", ""),
                1 if event.get("assessment_cached", False) else 0,
                event.get("content_length", 0),
                1 if event.get("has_evidence", False) else 0,
                1 if event.get("has_gap_hint", False) else 0,
                event.get("questions_count", 0),
                1 if event.get("reevaluate", False) else 0,
                1 if event.get("can_degrade", False) else 0,
                event.get("user_action", ""),
                event.get("degradation_count", 0),
                metadata,
            ))
            await db.commit()
        
        # 更新会话汇总
        await self._update_session_summary(event.get("session_id", ""))

    async def _update_session_summary(self, session_id: str):
        """更新会话级汇总"""
        if not session_id:
            return
        
        async with aiosqlite.connect(str(self.db_path)) as db:
            db.row_factory = aiosqlite.Row
            
            # 查询会话所有事件
            async with db.execute(
                "SELECT * FROM supplement_events WHERE session_id = ? ORDER BY timestamp",
                (session_id,)
            ) as cursor:
                events = await cursor.fetchall()
            
            if not events:
                return
            
            # 计算汇总数据
            total_supplements = len(events)
            level_counts = {"L0": 0, "L1": 0, "L2": 0, "L3": 0, "L4": 0}
            total_degradations = 0
            confirm_count = 0
            total_content_length = 0
            
            for event in events:
                event_dict = dict(event)
                kl = event_dict.get("knowledge_level", "")
                if kl in level_counts:
                    level_counts[kl] += 1
                
                if event_dict.get("user_action") == "degrade":
                    total_degradations += 1
                elif event_dict.get("user_action") == "confirm":
                    confirm_count += 1
                
                total_content_length += event_dict.get("content_length", 0)
            
            confirm_rate = confirm_count / total_supplements if total_supplements > 0 else 0.0
            avg_content_length = total_content_length / total_supplements if total_supplements > 0 else 0.0
            
            now = datetime.now().isoformat()
            
            # 插入或更新汇总
            await db.execute("""
                INSERT INTO supplement_sessions (
                    session_id, total_supplements,
                    l0_count, l1_count, l2_count, l3_count, l4_count,
                    total_degradations, confirm_rate, avg_content_length,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    total_supplements = excluded.total_supplements,
                    l0_count = excluded.l0_count,
                    l1_count = excluded.l1_count,
                    l2_count = excluded.l2_count,
                    l3_count = excluded.l3_count,
                    l4_count = excluded.l4_count,
                    total_degradations = excluded.total_degradations,
                    confirm_rate = excluded.confirm_rate,
                    avg_content_length = excluded.avg_content_length,
                    updated_at = excluded.updated_at
            """, (
                session_id, total_supplements,
                level_counts["L0"], level_counts["L1"], level_counts["L2"],
                level_counts["L3"], level_counts["L4"],
                total_degradations, confirm_rate, avg_content_length,
                now, now,
            ))
            
            await db.commit()

    async def get_events(self, session_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """获取事件列表"""
        async with aiosqlite.connect(str(self.db_path)) as db:
            db.row_factory = aiosqlite.Row
            
            if session_id:
                query = "SELECT * FROM supplement_events WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?"
                params = (session_id, limit)
            else:
                query = "SELECT * FROM supplement_events ORDER BY timestamp DESC LIMIT ?"
                params = (limit,)
            
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_session_summary(self, session_id: str) -> Optional[Dict]:
        """获取会话汇总"""
        async with aiosqlite.connect(str(self.db_path)) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM supplement_sessions WHERE session_id = ?",
                (session_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_analytics_overview(self, days: int = 7) -> Dict:
        """
        获取分析概览
        
        Returns:
            {
                "total_events": 1000,
                "total_sessions": 50,
                "level_distribution": {"L0": 100, "L1": 200, ...},
                "avg_confirm_rate": 0.85,
                "avg_degradation_count": 0.5,
                "cache_hit_rate": 0.3,
                "reevaluate_rate": 0.6
            }
        """
        from datetime import timedelta
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        async with aiosqlite.connect(str(self.db_path)) as db:
            db.row_factory = aiosqlite.Row
            
            # 总事件数
            async with db.execute(
                "SELECT COUNT(*) as cnt FROM supplement_events WHERE timestamp > ?",
                (cutoff,)
            ) as cursor:
                row = await cursor.fetchone()
                total_events = row["cnt"] if row else 0
            
            # 总会话数
            async with db.execute(
                "SELECT COUNT(*) as cnt FROM supplement_sessions WHERE updated_at > ?",
                (cutoff,)
            ) as cursor:
                row = await cursor.fetchone()
                total_sessions = row["cnt"] if row else 0
            
            # 知识级别分布
            level_distribution = {}
            for level in ["L0", "L1", "L2", "L3", "L4"]:
                async with db.execute(
                    "SELECT COUNT(*) as cnt FROM supplement_events WHERE knowledge_level = ? AND timestamp > ?",
                    (level, cutoff)
                ) as cursor:
                    row = await cursor.fetchone()
                    level_distribution[level] = row["cnt"] if row else 0
            
            # 平均确认率
            async with db.execute(
                "SELECT AVG(confirm_rate) as avg_rate FROM supplement_sessions WHERE updated_at > ?",
                (cutoff,)
            ) as cursor:
                row = await cursor.fetchone()
                avg_confirm_rate = row["avg_rate"] if row and row["avg_rate"] else 0.0
            
            # 平均降级次数
            async with db.execute(
                "SELECT AVG(total_degradations) as avg_deg FROM supplement_sessions WHERE updated_at > ?",
                (cutoff,)
            ) as cursor:
                row = await cursor.fetchone()
                avg_degradation_count = row["avg_deg"] if row and row["avg_deg"] else 0.0
            
            # 缓存命中率
            async with db.execute(
                "SELECT COUNT(*) as cached FROM supplement_events WHERE assessment_cached = 1 AND timestamp > ?",
                (cutoff,)
            ) as cursor:
                row = await cursor.fetchone()
                cached_count = row["cached"] if row else 0
            cache_hit_rate = cached_count / total_events if total_events > 0 else 0.0
            
            # 重新评估率
            async with db.execute(
                "SELECT COUNT(*) as reeval FROM supplement_events WHERE reevaluate = 1 AND timestamp > ?",
                (cutoff,)
            ) as cursor:
                row = await cursor.fetchone()
                reeval_count = row["reeval"] if row else 0
            reevaluate_rate = reeval_count / total_events if total_events > 0 else 0.0
            
            return {
                "total_events": total_events,
                "total_sessions": total_sessions,
                "level_distribution": level_distribution,
                "avg_confirm_rate": round(avg_confirm_rate, 2),
                "avg_degradation_count": round(avg_degradation_count, 2),
                "cache_hit_rate": round(cache_hit_rate, 2),
                "reevaluate_rate": round(reevaluate_rate, 2),
            }


def get_analytics_tracker() -> AnalyticsTracker:
    """获取埋点追踪器实例"""
    return AnalyticsTracker()
