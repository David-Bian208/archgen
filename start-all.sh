#!/bin/bash
# V4.5.1 完整启动脚本

echo "=========================================="
echo "🚀 行为记录助手 V4.5.1 启动"
echo "=========================================="
echo ""

# 停止旧进程
echo "🛑 停止旧进程..."
pkill -f "python3 main.py" 2>/dev/null
pkill -f "vite --port 3000" 2>/dev/null
sleep 2

# 启动后端
echo "📡 启动后端服务..."
cd /home/admin/.openclaw/workspace/behavior_recorder_service
nohup python3 main.py > server.log 2>&1 &
BACKEND_PID=$!
echo "   后端 PID: $BACKEND_PID"

# 等待后端启动
sleep 5

# 检查后端状态
if curl -s http://localhost:8000/docs | head -1 > /dev/null; then
    echo "   ✅ 后端启动成功：http://localhost:8000"
else
    echo "   ❌ 后端启动失败，请查看 server.log"
    exit 1
fi

# 启动前端
echo "🎨 启动前端服务..."
cd /home/admin/.openclaw/workspace/behavior_recorder_service/frontend
nohup npm run dev -- --port 3000 --host > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   前端 PID: $FRONTEND_PID"

# 等待前端启动
sleep 8

# 检查前端状态
if curl -s http://localhost:3000 | head -1 > /dev/null; then
    echo "   ✅ 前端启动成功：http://localhost:3000"
else
    echo "   ❌ 前端启动失败，请查看 frontend.log"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ 所有服务启动完成！"
echo "=========================================="
echo ""
echo "📊 访问地址："
echo "   前端界面：http://localhost:3000"
echo "   API 文档：http://localhost:8000/docs"
echo ""
echo "📝 日志文件："
echo "   后端日志：server.log"
echo "   前端日志：frontend.log"
echo ""
echo "🛑 停止服务："
echo "   ./stop-all.sh"
echo ""
