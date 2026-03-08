#!/bin/bash
# 行为记录员 - 停止服务脚本

echo "🛑 停止服务..."

# 停止后端
if [ -f "server.pid" ]; then
    PID=$(cat server.pid)
    if kill -0 $PID 2>/dev/null; then
        echo "   停止后端 (PID: $PID)..."
        kill $PID
    fi
    rm server.pid
fi
pkill -f "python3 main.py" 2>/dev/null || true

# 停止前端
if [ -f "frontend.pid" ]; then
    PID=$(cat frontend.pid)
    if kill -0 $PID 2>/dev/null; then
        echo "   停止前端 (PID: $PID)..."
        kill $PID
    fi
    rm frontend.pid
fi
pkill -f "vite" 2>/dev/null || true

sleep 2
echo "✅ 服务已停止"
