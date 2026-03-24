#!/bin/bash
# V4.0 服务守护进程脚本

cd /home/admin/.openclaw/workspace/behavior_recorder_service

# 检查并杀死旧进程
pkill -9 -f "python3 main.py" 2>/dev/null
sleep 1

# 启动服务（使用 nohup 和 disown 确保不被杀死）
nohup python3 main.py > /tmp/backend_v4.log 2>&1 &
PID=$!

# 保存到文件
echo $PID > server.pid

# 等待启动
sleep 3

# 检查是否成功
if ps -p $PID > /dev/null; then
    echo "✅ V4.0 服务已启动 (PID: $PID)"
    echo "访问地址：http://localhost:8000"
    echo "API 文档：http://localhost:8000/docs"
else
    echo "❌ 启动失败，检查日志：/tmp/backend_v4.log"
    exit 1
fi
