#!/bin/bash
# 行为观察助手 Chainlit 服务启动脚本
# 阿里云固定端口：3000 (可通过环境变量 PORT 覆盖)
# 原因：阿里云安全组/防火墙只开放3000端口，本地测试可使用8005
# 部署优化：默认监听 0.0.0.0 以支持云服务器外网访问

PORT=${PORT:-3000}
HOST=${HOST:-0.0.0.0}
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
