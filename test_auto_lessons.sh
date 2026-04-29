#!/bin/bash
# test_auto_lessons.sh - 测试失败经验自动沉淀

echo "🧪 测试失败经验自动沉淀..."

# 1. 生成失败报告
echo '{"lint":{"passed":false,"output":["E001: 未使用 import"]},"type":{"passed":true},"security":{"passed":true},"tests_passed":true}' > trea_report.json
echo '{"status":"⚠️ Failed","violations":["Circular dependency: app.a -> app.b -> app.a"]}' > arch_report.json

# 2. 运行自动沉淀
echo ""
echo "🧠 运行失败经验自动沉淀..."
python .claw/auto_lessons.py

# 3. 显示生成的文件
if [ -f .claw/lessons.md ]; then
    echo ""
    echo "📄 生成的 lessons.md 内容："
    echo "================================"
    cat .claw/lessons.md
    echo "================================"
fi

if [ -f .claw/prompts/_lessons_inject.md ]; then
    echo ""
    echo "📄 生成的 _lessons_inject.md 内容："
    echo "================================"
    cat .claw/prompts/_lessons_inject.md
    echo "================================"
fi

# 4. 清理
rm -f trea_report.json arch_report.json

echo ""
echo "✅ 测试完成！"
