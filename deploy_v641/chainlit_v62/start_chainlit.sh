#!/bin/bash
# 行为观察助手 Chainlit 服务启动脚本
# 固定端口：8006

PORT=8006
PROJECT_DIR="/home/admin/.openclaw/workspace/behavior_recorder_service/chainlit_v62"

echo "🔍 检查端口 $PORT 是否被占用..."
if lsof -ti:$PORT > /dev/null 2>&1; then
    echo "⚠️  端口 $PORT 被占用，正在清理..."
    lsof -ti:$PORT | xargs kill -9 2>/dev/null
    sleep 3
fi

echo "🚀 启动 Chainlit 服务..."
cd $PROJECT_DIR
chainlit run app.py --port $PORT --headless
