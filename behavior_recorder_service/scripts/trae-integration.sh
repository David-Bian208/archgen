#!/bin/bash
# Trae IDE 集成脚本
# 用途：同步项目配置、运行测试、生成报告

set -e

WORKSPACE="/home/admin/.openclaw/workspace/behavior_recorder_service"
TRAE_DIR="$WORKSPACE/.trae"

echo "🛠️  Trae IDE 集成脚本"
echo "工作目录：$WORKSPACE"
echo ""

# 同步项目上下文到 Trae 配置
sync_context() {
    echo "📋 同步项目上下文..."
    cp "$WORKSPACE/AGENTS.md" "$TRAE_DIR/agents-latest.md"
    cp "$WORKSPACE/PRD.md" "$TRAE_DIR/prd-latest.md"
    cp "$WORKSPACE/TECH_DESIGN.md" "$TRAE_DIR/tech-design-latest.md"
    echo "✅ 同步完成"
}

# 运行 P0 测试
run_p0_tests() {
    echo "🧪 运行 P0 测试..."
    cd "$WORKSPACE"
    source venv/bin/activate 2>/dev/null || true
    pytest tests/test_p0_regression.py -v
    echo "✅ P0 测试完成"
}

# 运行全量测试
run_all_tests() {
    echo "🧪 运行全量测试..."
    cd "$WORKSPACE"
    source venv/bin/activate 2>/dev/null || true
    pytest tests/ -v --cov=app --cov-report=html
    echo "✅ 全量测试完成"
    echo "📊 覆盖率报告：file://$WORKSPACE/htmlcov/index.html"
}

# 生成测试报告
generate_report() {
    echo "📊 生成测试报告..."
    python3 scripts/generate_test_report.py 2>/dev/null || echo "⚠️ 报告脚本不存在"
    echo "✅ 报告完成"
}

# 检查服务状态
check_status() {
    echo "💓 检查服务状态..."
    curl -s http://localhost:8000/health && echo "✅ 后端正常" || echo "❌ 后端异常"
    curl -s http://localhost:3000 && echo "✅ 前端正常" || echo "❌ 前端异常"
}

# 安全扫描
security_scan() {
    echo "🛡️  执行安全扫描..."
    "$WORKSPACE/../scripts/security-scan.sh"
    echo "✅ 安全扫描完成"
}

# 显示帮助
show_help() {
    echo "用法：./trae-integration.sh [命令]"
    echo ""
    echo "命令:"
    echo "  sync        同步项目上下文到 Trae 配置"
    echo "  p0          运行 P0 测试"
    echo "  test        运行全量测试"
    echo "  report      生成测试报告"
    echo "  status      检查服务状态"
    echo "  security    执行安全扫描"
    echo "  all         执行所有操作"
    echo "  help        显示帮助"
}

# 主逻辑
case "${1:-help}" in
    sync)
        sync_context
        ;;
    p0)
        run_p0_tests
        ;;
    test)
        run_all_tests
        ;;
    report)
        generate_report
        ;;
    status)
        check_status
        ;;
    security)
        security_scan
        ;;
    all)
        sync_context
        run_p0_tests
        check_status
        ;;
    help|*)
        show_help
        ;;
esac

echo ""
echo "✅ 完成！"
