#!/bin/bash
# 技能安装脚本
# 用途：安装 FastAPI + Test Master 技能
# 用法：./install-skills.sh

set -e

echo "🛠️  OpenClaw 技能安装脚本"
echo "目标技能：fastapi, test-master"
echo ""

# 检查 clawhub 是否可用
if ! command -v clawhub &> /dev/null; then
    echo "❌ clawhub 未安装"
    exit 1
fi

echo "✅ clawhub 可用"
echo ""

# 安装 FastAPI
echo "📦 安装 FastAPI 技能..."
if clawhub install fastapi 2>&1; then
    echo "✅ FastAPI 安装成功"
else
    echo "⚠️ FastAPI 安装失败（可能限流），稍后手动重试"
fi

echo ""

# 等待
echo "⏳ 等待 5 秒..."
sleep 5

# 安装 Test Master
echo "📦 安装 Test Master 技能..."
if clawhub install test-master 2>&1; then
    echo "✅ Test Master 安装成功"
else
    echo "⚠️ Test Master 安装失败（可能限流），稍后手动重试"
fi

echo ""
echo "📋 检查已安装技能..."
clawhub list 2>&1 | head -20

echo ""
echo "✅ 安装完成！"
