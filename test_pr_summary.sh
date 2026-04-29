#!/bin/bash
# test_pr_summary.sh - 本地测试 PR 摘要生成

echo "🧪 测试 PR 摘要生成..."

# 1. 生成测试报告
echo '{"lint":{"passed":true},"type":{"passed":true},"security":{"passed":true},"status":"✅ Passed"}' > trea_report.json
echo '{"status":"✅ Passed","circular_dependencies":[]}' > arch_report.json
echo '{"status":"✅ 安全检查通过","issues":[]}' > security_report.json

# 2. 设置 API Key（如果未设置）
if [ -z "$DASHSCOPE_API_KEY" ]; then
    echo "⚠️ DASHSCOPE_API_KEY 未设置，使用测试模式"
    export DASHSCOPE_API_KEY="sk-test"
fi

# 3. 运行脚本
echo ""
echo "📝 生成 PR 摘要..."
python generate_pr_summary.py

# 4. 清理
rm -f trea_report.json arch_report.json security_report.json pr_summary.md

echo ""
echo "✅ 测试完成！"
