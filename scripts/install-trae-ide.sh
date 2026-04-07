#!/bin/bash
# Trae IDE 安装脚本
# 用途：下载、安装并打开 Trae IDE

set -e

echo "🛠️  Trae IDE 安装脚本"
echo ""

# 检查系统
if [[ "$(uname)" == "Darwin" ]]; then
    echo "✅ 检测到 macOS 系统"
    ARCH=$(uname -m)
    if [[ "$ARCH" == "arm64" ]]; then
        echo "✅ Apple Silicon (M1/M2/M3)"
        DOWNLOAD_URL="https://dl.trae.cn/ide/Trae-darwin-arm64.dmg"
    else
        echo "✅ Intel Mac"
        DOWNLOAD_URL="https://dl.trae.cn/ide/Trae-darwin-x64.dmg"
    fi
else
    echo "❌ 仅支持 macOS 系统"
    exit 1
fi

echo ""
echo "📥 下载 Trae IDE..."
DOWNLOAD_DIR="/tmp"
DMG_FILE="$DOWNLOAD_DIR/Trae-IDE.dmg"

# 尝试下载
if curl -L -o "$DMG_FILE" "$DOWNLOAD_URL" 2>&1 | grep -q "HTTP/2 200"; then
    echo "✅ 下载成功：$DMG_FILE"
else
    echo "⚠️  自动下载失败"
    echo ""
    echo "请手动下载："
    echo "1. 打开浏览器访问：https://www.trae.cn/ide/download"
    echo "2. 点击 macOS 下载按钮"
    echo "3. 下载完成后，运行此脚本继续安装"
    echo ""
    exit 1
fi

echo ""
echo "💿 安装 Trae IDE..."
# 挂载 DMG
MOUNT_POINT="/Volumes/Trae"
hdiutil attach "$DMG_FILE" -mountpoint "$MOUNT_POINT" -quiet

# 复制到 Applications
cp -R "$MOUNT_POINT/Trae.app" /Applications/

# 卸载 DMG
hdiutil detach "$MOUNT_POINT" -quiet

echo "✅ 安装完成"

echo ""
echo "🚀 打开 Trae IDE..."
open /Applications/Trae.app

echo ""
echo "📂 打开项目..."
sleep 3  # 等待应用启动
open -a /Applications/Trae.app /home/admin/.openclaw/workspace/behavior_recorder_service

echo ""
echo "✅ Trae IDE 已启动并打开项目！"
echo ""
echo "下一步："
echo "1. 在 Trae 中阅读 .trae/context.md"
echo "2. 阅读 .trae/instructions.md"
echo "3. 开始编码"
echo "4. 运行 ./scripts/trae-integration.sh p0 测试"
