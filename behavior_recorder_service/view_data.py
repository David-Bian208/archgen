#!/usr/bin/env python3
# 行为观察伙伴 - 数据查看脚本
# 使用方法：python3 view_data.py

import sqlite3
from datetime import datetime

DB_PATH = "test_logs.db"

def print_separator(title=""):
    print("=" * 50)
    if title:
        print(title)
        print("=" * 50)

def main():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print_separator("行为观察伙伴 - 数据看板")
        print()
        
        # 1. 总体统计
        print("【总体统计】")
        cursor.execute("SELECT COUNT(DISTINCT session_id) FROM test_logs")
        print(f"总用户数：{cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM test_logs")
        print(f"总使用次数：{cursor.fetchone()[0]}")
        
        cursor.execute("SELECT AVG(response_time_ms) FROM test_logs")
        avg_time = cursor.fetchone()[0]
        if avg_time:
            print(f"平均响应时间：{avg_time/1000:.2f}秒")
        print()
        
        # 2. 今日数据
        print("【今日数据】")
        cursor.execute("SELECT COUNT(DISTINCT session_id) FROM test_logs WHERE DATE(timestamp)=DATE('now')")
        print(f"今日用户：{cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM test_logs WHERE DATE(timestamp)=DATE('now')")
        print(f"今日使用：{cursor.fetchone()[0]}次")
        print()
        
        # 3. 反馈统计
        print("【用户反馈】")
        cursor.execute("SELECT COUNT(*) FROM user_feedback")
        print(f"反馈数量：{cursor.fetchone()[0]}")
        
        cursor.execute("SELECT AVG(rating) FROM user_feedback")
        avg_rating = cursor.fetchone()[0]
        if avg_rating:
            print(f"平均评分：{avg_rating:.2f}星")
        
        cursor.execute("""
            SELECT 
              SUM(CASE WHEN accuracy='accurate' THEN 1 ELSE 0 END),
              SUM(CASE WHEN accuracy='partial' THEN 1 ELSE 0 END),
              SUM(CASE WHEN accuracy='inaccurate' THEN 1 ELSE 0 END)
            FROM user_feedback
        """)
        row = cursor.fetchone()
        if row[0] is not None:
            print(f"准确性统计：准确={row[0]}, 部分准确={row[1]}, 不准确={row[2]}")
        print()
        
        # 4. 最新反馈（5 条）
        print("【最新反馈】")
        cursor.execute("""
            SELECT rating, feedback_text, timestamp 
            FROM user_feedback 
            ORDER BY timestamp DESC 
            LIMIT 5
        """)
        rows = cursor.fetchall()
        if rows:
            for row in rows:
                print(f"⭐{row[0]}星 | {row[1][:50]}{'...' if len(row[1] or '') > 50 else ''} | {row[2]}")
        else:
            print("暂无反馈")
        print()
        
        # 5. 最新使用记录（5 条）
        print("【最新使用记录】")
        cursor.execute("""
            SELECT session_id, user_input, timestamp 
            FROM test_logs 
            ORDER BY timestamp DESC 
            LIMIT 5
        """)
        rows = cursor.fetchall()
        if rows:
            for row in rows:
                print(f"[{row[2]}] 会话{row[0][:8]}... | {row[1][:50]}{'...' if len(row[1]) > 50 else ''}")
        else:
            print("暂无使用记录")
        print()
        
        print_separator()
        print(f"数据库路径：{DB_PATH}")
        print(f"数据文件位置：$(pwd)")
        print_separator()
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 错误：{e}")
        print("提示：请确保数据库文件存在且路径正确")

if __name__ == "__main__":
    main()
