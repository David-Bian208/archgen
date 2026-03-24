#!/bin/bash
# 行为记录员 V3.6 - 守护进程启动脚本
# 使用 nohup + disown 确保进程独立运行

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 启动记录观察助手 V4.1 - 严格出口 + 假设锁定"
echo "================================"

# 停止旧进程
echo "📋 清理旧进程..."
pkill -f "python3 main.py" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
sleep 2

# 启动后端
echo "🔧 启动后端服务..."
nohup python3 main.py > server.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > server.pid
disown $BACKEND_PID
echo "   后端 PID: $BACKEND_PID"

# 等待后端启动
sleep 3

# 检查后端
if kill -0 $BACKEND_PID 2>/dev/null; then
    echo "   ✅ 后端启动成功"
else
    echo "   ❌ 后端启动失败，查看 server.log"
    exit 1
fi

# 启动前端
echo "🎨 启动前端服务..."
cd frontend
nohup npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../frontend.pid
disown $FRONTEND_PID
echo "   前端 PID: $FRONTEND_PID"

# 等待前端启动
sleep 3

# 检查前端
if kill -0 $FRONTEND_PID 2>/dev/null; then
    echo "   ✅ 前端启动成功"
else
    echo "   ❌ 前端启动失败，查看 frontend.log"
    exit 1
fi

echo ""
echo "================================"
echo "✅ 服务启动完成！"
echo ""
echo "访问地址：http://localhost:3000"
echo "API 文档：http://localhost:8000/docs"
echo ""
echo "查看日志:"
echo "  后端：tail -f server.log"
echo "  前端：tail -f frontend.log"
echo ""
echo "停止服务：./stop.sh"
