#!/bin/bash
# 行为观察伙伴 - 数据查看脚本
# 使用方法：./view_data.sh

DB_PATH="test_logs.db"

echo "======================================"
echo "行为观察伙伴 - 数据看板"
echo "======================================"
echo ""

# 1. 总体统计
echo "【总体统计】"
sqlite3 $DB_PATH "
SELECT 
  '总用户数：' || COUNT(DISTINCT session_id)
FROM test_logs;
"
sqlite3 $DB_PATH "
SELECT 
  '总使用次数：' || COUNT(*)
FROM test_logs;
"
sqlite3 $DB_PATH "
SELECT 
  '平均响应时间：' || ROUND(AVG(response_time_ms)/1000, 2) || '秒'
FROM test_logs;
"
echo ""

# 2. 今日数据
echo "【今日数据】"
sqlite3 $DB_PATH "
SELECT 
  '今日用户：' || COUNT(DISTINCT session_id)
FROM test_logs 
WHERE DATE(timestamp)=DATE('now');
"
sqlite3 $DB_PATH "
SELECT 
  '今日使用：' || COUNT(*) || '次'
FROM test_logs 
WHERE DATE(timestamp)=DATE('now');
"
echo ""

# 3. 反馈统计
echo "【用户反馈】"
sqlite3 $DB_PATH "
SELECT 
  '反馈数量：' || COUNT(*)
FROM user_feedback;
"
sqlite3 $DB_PATH "
SELECT 
  '平均评分：' || ROUND(AVG(rating), 2) || '星'
FROM user_feedback;
"
sqlite3 $DB_PATH "
SELECT 
  '准确性统计：' || 
  '准确=' || SUM(CASE WHEN accuracy='accurate' THEN 1 ELSE 0 END) || 
  ', 部分准确=' || SUM(CASE WHEN accuracy='partial' THEN 1 ELSE 0 END) || 
  ', 不准确=' || SUM(CASE WHEN accuracy='inaccurate' THEN 1 ELSE 0 END)
FROM user_feedback;
"
echo ""

# 4. 最新反馈（5 条）
echo "【最新反馈】"
sqlite3 -header -column $DB_PATH "
SELECT 
  rating as 评分，
  feedback_text as 反馈，
  substr(timestamp, 1, 16) as 时间
FROM user_feedback 
ORDER BY timestamp DESC 
LIMIT 5;
"
echo ""

# 5. 最新使用记录（5 条）
echo "【最新使用记录】"
sqlite3 -header -column $DB_PATH "
SELECT 
  substr(session_id, 1, 8) as 会话 ID,
  substr(user_input, 1, 30) || '...' as 输入，
  substr(timestamp, 1, 16) as 时间
FROM test_logs 
ORDER BY timestamp DESC 
LIMIT 5;
"
echo ""

echo "======================================"
echo "数据库路径：$DB_PATH"
echo "数据文件位置：$(pwd)"
echo "======================================"
