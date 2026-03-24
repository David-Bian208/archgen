#!/bin/bash
# 自闭症AI助教项目解码脚本 (Linux/Mac)
# 使用方法：将autism_assistant.base64放在同一目录，运行 ./decode.sh

echo "🔧 自闭症AI助教项目解码工具"
echo "================================"

# 检查base64文件
if [ ! -f "autism_assistant.base64" ]; then
    echo "❌ 缺少 autism_assistant.base64 文件"
    echo "📝 请确保 autism_assistant.base64 与本脚本在同一目录"
    exit 1
fi

echo "✅ 找到 autism_assistant.base64 文件"
echo "📦 解码Base64数据..."

# 解码base64为tar.gz
if base64 --decode autism_assistant.base64 > autism_assistant.tar.gz 2>/dev/null; then
    echo "✅ Base64解码完成"
else
    echo "❌ Base64解码失败"
    echo "⚠️  尝试使用其他base64解码方式..."
    if cat autism_assistant.base64 | base64 -d > autism_assistant.tar.gz 2>/dev/null; then
        echo "✅ 备用解码方式成功"
    else
        echo "❌ 解码失败，请检查base64文件完整性"
        exit 1
    fi
fi

echo "📂 解压项目文件..."
if tar -xzf autism_assistant.tar.gz; then
    echo "✅ 项目解压完成"
    echo "📁 项目目录: autism_assistant/"
    echo ""
    echo "🚀 接下来操作："
    echo "1. cd autism_assistant"
    echo "2. 查看 README.md 了解项目详情"
    echo "3. 运行启动脚本:"
    echo "   - Linux/Mac: ./start.sh"
    echo "   - Windows: 双击 start.bat"
else
    echo "❌ 解压失败，文件可能损坏"
    exit 1
fi

# 清理临时文件（可选）
echo ""
read -p "是否删除临时压缩文件? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm autism_assistant.tar.gz
    echo "✅ 已删除临时文件"
fi

echo ""
echo "🎉 解码完成！"