#!/bin/bash
# test_trea_hook.sh - 测试 Trea 质量门禁

echo "🧪 测试 Trea 质量门禁..."

# 1. 检查依赖
echo ""
echo "📦 检查依赖..."
which ruff >/dev/null 2>&1 && echo "✅ ruff 已安装" || echo "⚠️ ruff 未安装"
which mypy >/dev/null 2>&1 && echo "✅ mypy 已安装" || echo "⚠️ mypy 未安装"

# 2. 生成测试文件
echo ""
echo "📝 创建测试文件..."
cat > test_check.py << 'PYEOF'
# 测试文件
def hello():
    print("Hello, World!")

if __name__ == "__main__":
    hello()
PYEOF

git add test_check.py 2>/dev/null || true

# 3. 运行门禁
echo ""
echo "🛡️ 运行质量门禁..."
python3 scripts/trea_hook.py

# 4. 清理
rm -f test_check.py
git reset test_check.py 2>/dev/null || true

echo ""
echo "✅ 测试完成！"
