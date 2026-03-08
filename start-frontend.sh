#!/bin/bash
# 前端快速启动脚本

set -e

echo "🎨 行为记录员前端 - 快速启动"
echo "================================"

cd frontend

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 错误：未找到 Node.js"
    exit 1
fi

# 检查依赖
if [ ! -d "node_modules" ]; then
    echo "📦 安装依赖..."
    npm install
fi

# 启动开发服务器
echo "🚀 启动前端开发服务器..."
echo "访问地址：http://localhost:3000"
echo ""
npm run dev
