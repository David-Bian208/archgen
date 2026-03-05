#!/bin/bash
# Behavior Recorder Service 快速启动脚本

set -e

echo "🧩 行为记录员服务 - 快速启动"
echo "================================"

# 检查配置文件
if [ ! -f "config.yaml" ]; then
    echo "⚠️  配置文件不存在，正在创建..."
    cp config.yaml.example config.yaml
    echo "✅ 已创建 config.yaml，请编辑该文件填入您的 API 密钥"
    echo ""
    echo "然后再次运行此脚本启动服务"
    exit 1
fi

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到 Python 3"
    exit 1
fi

# 检查依赖
echo "📦 检查依赖..."
pip3 install -q -r requirements.txt

# 启动服务
echo "🚀 启动后端服务..."
echo "API 文档：http://localhost:8000/docs"
echo ""
python3 main.py
