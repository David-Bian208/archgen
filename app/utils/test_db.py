"""
测试日志数据库模块

用于记录用户测试数据、AI 输出、用户反馈
"""

import sqlite3
import json
import logging
import os
import zipfile
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
                user_id INTEGER,
                child_id INTEGER,
                started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                ended_at DATETIME,
                total_turns INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                child_profile TEXT,
                final_report TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (child_id) REFERENCES children(id)
            )
        """)
        
        # 4. 用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 5. 儿童表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS children (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                gender TEXT,
                birth_date TEXT,
                age INTEGER,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON test_logs(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON test_logs(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_session ON user_feedback(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_email ON users(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_username ON users(username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_children_user_id ON children(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON test_sessions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_child_id ON test_sessions(child_id)")
        
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
    
    def add_user(self, username: str, email: str, password_hash: str, full_name: str = "") -> int:
        """
        添加用户
        
        Args:
            username: 用户名
            email: 邮箱
            password_hash: 密码哈希
            full_name: 全名
            
        Returns:
            用户 ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, full_name)
            VALUES (?, ?, ?, ?)
        """, (username, email, password_hash, full_name))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        logger.info(f"用户已添加：id={user_id}, email={email}")
        return user_id
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """
        根据邮箱获取用户
        
        Args:
            email: 邮箱
            
        Returns:
            用户信息字典
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        
        conn.close()
        return dict(row) if row else None
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """
        根据用户名获取用户
        
        Args:
            username: 用户名
            
        Returns:
            用户信息字典
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        
        conn.close()
        return dict(row) if row else None
    
    def add_child(self, user_id: int, name: str, gender: str = "", birth_date: str = "", age: int = 0, notes: str = "") -> int:
        """
        添加儿童
        
        Args:
            user_id: 用户 ID
            name: 儿童姓名
            gender: 性别
            birth_date: 出生日期
            age: 年龄
            notes: 备注
            
        Returns:
            儿童 ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO children (user_id, name, gender, birth_date, age, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, name, gender, birth_date, age, notes))
        
        child_id = cursor.lastrowid
        conn.commit()
        conn.close()
        logger.info(f"儿童已添加：id={child_id}, name={name}")
        return child_id
    
    def get_children_by_user_id(self, user_id: int) -> List[Dict]:
        """
        获取用户的所有儿童
        
        Args:
            user_id: 用户 ID
            
        Returns:
            儿童列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM children WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        rows = cursor.fetchall()
        
        conn.close()
        return [dict(row) for row in rows]
    
    def update_session_with_user(self, session_id: str, user_id: int, child_id: int = None):
        """
        更新会话的用户和儿童信息
        
        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            child_id: 儿童 ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE test_sessions 
            SET user_id = ?, child_id = ?
            WHERE session_id = ?
        """, (user_id, child_id, session_id))
        
        conn.commit()
        conn.close()
        logger.info(f"会话已更新：session={session_id}, user_id={user_id}, child_id={child_id}")
    
    def get_sessions_by_user_id(self, user_id: int, limit: int = 100) -> List[Dict]:
        """
        获取用户的所有会话
        
        Args:
            user_id: 用户 ID
            limit: 返回数量限制
            
        Returns:
            会话列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM test_sessions 
            WHERE user_id = ? 
            ORDER BY started_at DESC
            LIMIT ?
        """, (user_id, limit))
        rows = cursor.fetchall()
        
        conn.close()
        return [dict(row) for row in rows]
    
    def search_sessions(self, user_id: int, keyword: str, limit: int = 100) -> List[Dict]:
        """
        搜索用户的会话
        
        Args:
            user_id: 用户 ID
            keyword: 搜索关键词
            limit: 返回数量限制
            
        Returns:
            匹配的会话列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM test_sessions 
            WHERE user_id = ? AND (child_profile LIKE ? OR final_report LIKE ?)
            ORDER BY started_at DESC
            LIMIT ?
        """, (user_id, f"%{keyword}%", f"%{keyword}%", limit))
        rows = cursor.fetchall()
        
        conn.close()
        return [dict(row) for row in rows]
    
    def filter_sessions(self, user_id: int, child_id: int = None, status: str = None, limit: int = 100) -> List[Dict]:
        """
        筛选用户的会话
        
        Args:
            user_id: 用户 ID
            child_id: 儿童 ID（可选）
            status: 会话状态（可选）
            limit: 返回数量限制
            
        Returns:
            筛选后的会话列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM test_sessions WHERE user_id = ?"
        params = [user_id]
        
        if child_id:
            query += " AND child_id = ?"
            params.append(child_id)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        conn.close()
        return [dict(row) for row in rows]
    
    def export_user_data(self, user_id: int, output_format: str = "csv") -> str:
        """
        导出用户数据
        
        Args:
            user_id: 用户 ID
            output_format: 输出格式（csv 或 json）
            
        Returns:
            导出文件路径
        """
        import csv
        
        # 获取用户数据
        children = self.get_children_by_user_id(user_id)
        sessions = self.get_sessions_by_user_id(user_id, limit=10000)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if output_format == "json":
            output_path = f"user_{user_id}_data_{timestamp}.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "user_id": user_id,
                    "children": children,
                    "sessions": sessions,
                    "exported_at": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        else:  # csv
            # 导出儿童数据
            children_path = f"user_{user_id}_children_{timestamp}.csv"
            if children:
                with open(children_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=children[0].keys())
                    writer.writeheader()
                    writer.writerows(children)
            
            # 导出会话数据
            sessions_path = f"user_{user_id}_sessions_{timestamp}.csv"
            if sessions:
                with open(sessions_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=sessions[0].keys())
                    writer.writeheader()
                    writer.writerows(sessions)
            
            output_path = f"user_{user_id}_data_{timestamp}.zip"
            with zipfile.ZipFile(output_path, 'w') as zf:
                if children:
                    zf.write(children_path)
                    os.remove(children_path)
                if sessions:
                    zf.write(sessions_path)
                    os.remove(sessions_path)
        
        logger.info(f"用户数据导出成功：user_id={user_id}, format={output_format}, file={output_path}")
        return output_path


# 全局数据库实例
_db: Optional[TestDatabase] = None


def get_database() -> TestDatabase:
    """获取数据库实例"""
    global _db
    if _db is None:
        _db = TestDatabase()
    return _db
