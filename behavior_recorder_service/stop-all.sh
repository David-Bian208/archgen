#!/bin/bash
# 停止所有服务

echo "🛑 停止所有服务..."
pkill -f "python3 main.py" 2>/dev/null
pkill -f "vite --port 3000" 2>/dev/null
sleep 2
echo "✅ 所有服务已停止"
