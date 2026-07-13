"""Storage Module - 数据库操作模块"""

import logging
import aiosqlite
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class StorageManager:
    def __init__(self, db_path: str = "data/archgen.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def init_db(self):
        """初始化数据库表"""
        async with aiosqlite.connect(str(self.db_path)) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    article_type TEXT,
                    style TEXT,
                    size TEXT,
                    input_file TEXT,
                    output_file TEXT,
                    created_at TEXT,
                    status TEXT
                )
            """)
            await db.commit()
        logger.info(f"数据库初始化完成: {self.db_path}")

    async def save_record(self, record: Dict) -> int:
        """保存生成记录"""
        async with aiosqlite.connect(str(self.db_path)) as db:
            cursor = await db.execute(
                """
                INSERT INTO records (title, article_type, style, size, input_file, output_file, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.get("title"),
                    record.get("article_type"),
                    record.get("style"),
                    record.get("size"),
                    record.get("input_file"),
                    record.get("output_file"),
                    datetime.now().isoformat(),
                    record.get("status", "completed"),
                ),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_records(self, limit: int = 50) -> List[Dict]:
        """获取历史记录"""
        async with aiosqlite.connect(str(self.db_path)) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM records ORDER BY created_at DESC LIMIT ?", (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def cleanup_old_records(self, hours: int = 24):
        """清理过期记录"""
        # TODO: 实现清理逻辑
        pass
