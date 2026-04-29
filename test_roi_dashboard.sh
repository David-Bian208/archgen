#!/bin/bash
# test_roi_dashboard.sh - 本地测试 ROI 看板生成

echo "🧪 测试 ROI 看板生成..."

# 1. 生成测试报告
echo '{"lint":{"passed":true},"type":{"passed":true},"security":{"passed":true}}' > trea_report.json
echo '{"status":"✅ Passed","circular_dependencies":[]}' > arch_report.json
echo '{"status":"✅ 安全检查通过","issues":[]}' > security_report.json

# 2. 运行看板
echo ""
echo "📊 生成 ROI 看板..."
python metrics_dashboard_lite.py

# 3. 显示生成的报表
if [ -f roi_report.md ]; then
    echo ""
    echo "📄 生成的报表内容："
    echo "================================"
    cat roi_report.md
    echo "================================"
fi

# 4. 清理
rm -f trea_report.json arch_report.json security_report.json roi_report.md

echo ""
echo "✅ 测试完成！"
