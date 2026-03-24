"""
测试日志数据库模块

用于记录用户测试数据、AI 输出、用户反馈
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class TestDatabase:
    """测试数据库管理类"""
    
    def __init__(self, db_path: str = "test_logs.db"):
        """
        初始化数据库
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.init_db()
        logger.info(f"测试数据库初始化完成：{db_path}")
    
    def init_db(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. 测试日志表（自动记录每次 AI 交互）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                turn_number INTEGER DEFAULT 1,
                user_input TEXT NOT NULL,
                ai_response TEXT,
                response_time_ms INTEGER,
                stage TEXT,
                functional_judgment TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. 用户反馈表（用户主动提交）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                accuracy TEXT CHECK(accuracy IN ('accurate', 'partial', 'inaccurate')),
                feedback_text TEXT,
                improvement_suggestion TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 3. 测试会话表（汇总信息）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_sessions (
                session_id TEXT PRIMARY KEY,
                started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                ended_at DATETIME,
                total_turns INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                child_profile TEXT,
                final_report TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON test_logs(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON test_logs(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_session ON user_feedback(session_id)")
        
        conn.commit()
        conn.close()
        logger.info("数据库表结构创建完成")
    
    def add_test_log(self, session_id: str, user_input: str, ai_response: Dict, 
                     turn_number: int = 1, response_time_ms: int = 0, stage: str = ""):
        """
        添加测试日志
        
        Args:
            session_id: 会话 ID
            user_input: 用户输入
            ai_response: AI 响应（字典）
            turn_number: 对话轮次
            response_time_ms: 响应时间（毫秒）
            stage: 当前阶段
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 提取关键信息
        functional_judgment = ai_response.get("functional_judgment", "")
        ai_response_json = json.dumps(ai_response, ensure_ascii=False)
        
        cursor.execute("""
            INSERT INTO test_logs 
            (session_id, user_input, ai_response, turn_number, response_time_ms, stage, functional_judgment)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session_id, user_input, ai_response_json, turn_number, response_time_ms, stage, functional_judgment))
        
        conn.commit()
        conn.close()
        logger.info(f"测试日志已记录：session={session_id}, turn={turn_number}")
    
    def add_feedback(self, session_id: str, rating: int, accuracy: str,
                     feedback_text: str = "", improvement_suggestion: str = ""):
        """
        添加用户反馈
        
        Args:
            session_id: 会话 ID
            rating: 评分（1-5）
            accuracy: 准确性（accurate/partial/inaccurate）
            feedback_text: 反馈文本
            improvement_suggestion: 改进建议
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO user_feedback 
            (session_id, rating, accuracy, feedback_text, improvement_suggestion)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, rating, accuracy, feedback_text, improvement_suggestion))
        
        conn.commit()
        conn.close()
        logger.info(f"用户反馈已记录：session={session_id}, rating={rating}")
    
    def create_or_update_session(self, session_id: str, child_profile: Optional[Dict] = None):
        """
        创建或更新会话
        
        Args:
            session_id: 会话 ID
            child_profile: 儿童背景信息
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        child_profile_json = json.dumps(child_profile, ensure_ascii=False) if child_profile else None
        
        # 尝试插入，如果存在则更新
        cursor.execute("""
            INSERT OR REPLACE INTO test_sessions (session_id, child_profile, status)
            VALUES (?, ?, 'active')
        """, (session_id, child_profile_json))
        
        conn.commit()
        conn.close()
    
    def complete_session(self, session_id: str, final_report: Dict):
        """
        完成会话
        
        Args:
            session_id: 会话 ID
            final_report: 最终报告
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        report_json = json.dumps(final_report, ensure_ascii=False)
        
        # 更新轮次
        cursor.execute("SELECT COUNT(*) FROM test_logs WHERE session_id = ?", (session_id,))
        total_turns = cursor.fetchone()[0]
        
        cursor.execute("""
            UPDATE test_sessions 
            SET ended_at = CURRENT_TIMESTAMP,
                status = 'completed',
                total_turns = ?,
                final_report = ?
            WHERE session_id = ?
        """, (total_turns, report_json, session_id))
        
        conn.commit()
        conn.close()
        logger.info(f"会话已完成：session={session_id}, turns={total_turns}")
    
    def get_test_report(self, session_id: Optional[str] = None, 
                        limit: int = 100) -> List[Dict]:
        """
        获取测试报告
        
        Args:
            session_id: 会话 ID（可选，不传则返回所有）
            limit: 返回数量限制
            
        Returns:
            测试日志列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if session_id:
            cursor.execute("""
                SELECT * FROM test_logs 
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (session_id, limit))
        else:
            cursor.execute("""
                SELECT * FROM test_logs 
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        result = [dict(row) for row in rows]
        
        conn.close()
        return result
    
    def get_feedback_summary(self) -> Dict:
        """
        获取反馈汇总
        
        Returns:
            反馈统计信息
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 评分分布
        cursor.execute("""
            SELECT rating, COUNT(*) as count 
            FROM user_feedback 
            GROUP BY rating 
            ORDER BY rating
        """)
        rating_dist = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 准确性分布
        cursor.execute("""
            SELECT accuracy, COUNT(*) as count 
            FROM user_feedback 
            GROUP BY accuracy
        """)
        accuracy_dist = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 平均评分
        cursor.execute("""
            SELECT AVG(rating) FROM user_feedback
        """)
        avg_rating = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "rating_distribution": rating_dist,
            "accuracy_distribution": accuracy_dist,
            "average_rating": round(avg_rating, 2),
            "total_feedback": sum(rating_dist.values())
        }
    
    def export_to_csv(self, output_path: str = "test_logs_export.csv"):
        """
        导出测试日志为 CSV
        
        Args:
            output_path: 输出文件路径
        """
        import csv
        
        logs = self.get_test_report(limit=10000)
        
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            if logs:
                writer = csv.DictWriter(f, fieldnames=logs[0].keys())
                writer.writeheader()
                writer.writerows(logs)
        
        logger.info(f"测试日志已导出：{output_path}")


# 全局数据库实例
_db: Optional[TestDatabase] = None


def get_database() -> TestDatabase:
    """获取数据库实例"""
    global _db
    if _db is None:
        _db = TestDatabase()
    return _db
