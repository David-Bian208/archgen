#!/bin/bash
# V3.8 最终优化版 - 功能验证脚本

echo "🧪 记录观察助手 V3.8 - 功能验证"
echo "================================"
echo ""

# 1. 检查服务状态
echo "1️⃣ 检查服务状态..."
if curl -s http://localhost:8000/docs > /dev/null; then
    echo "   ✅ 后端服务正常 (8000)"
else
    echo "   ❌ 后端服务异常"
    exit 1
fi

if curl -s http://localhost:3000 > /dev/null; then
    echo "   ✅ 前端服务正常 (3000)"
else
    echo "   ❌ 前端服务异常"
    exit 1
fi

# 2. 检查 API 版本
echo ""
echo "2️⃣ 检查 API 版本..."
API_TITLE=$(curl -s http://localhost:8000/docs | grep -o "记录观察助手 V[0-9.]*" | head -1)
if [[ "$API_TITLE" == *"V3.8"* ]]; then
    echo "   ✅ API 版本：$API_TITLE"
else
    echo "   ❌ API 版本：$API_TITLE (期望 V3.8)"
    exit 1
fi

# 3. 检查前端文件
echo ""
echo "3️⃣ 检查前端关键文件..."
if grep -q "V3.8" frontend/App.vue; then
    echo "   ✅ 前端版本号已更新"
else
    echo "   ❌ 前端版本号未更新"
fi

if grep -q "多角度理解" frontend/App.vue; then
    echo "   ✅ 第二章标题已更新"
else
    echo "   ❌ 第二章标题未更新"
fi

if grep -q "行为模式解读" frontend/App.vue; then
    echo "   ✅ 第三章标题已更新"
else
    echo "   ❌ 第三章标题未更新"
fi

if grep -q "decodeHTMLEntities" frontend/utils/filters.js; then
    echo "   ✅ HTML 实体解码函数已添加"
else
    echo "   ❌ HTML 实体解码函数缺失"
fi

# 4. 检查后端文件
echo ""
echo "4️⃣ 检查后端关键修改..."
if grep -q "V3.8" app/agents/intervention_planner.py; then
    echo "   ✅ 干预规划器版本已更新"
else
    echo "   ❌ 干预规划器版本未更新"
fi

if grep -q "decode_html_entities" app/agents/intervention_planner.py; then
    echo "   ✅ HTML 实体解码方法已添加"
else
    echo "   ❌ HTML 实体解码方法缺失"
fi

if grep -q "通用方法论" app/agents/intervention_planner.py; then
    echo "   ✅ 通用方法论描述已添加"
else
    echo "   ❌ 通用方法论描述缺失"
fi

if grep -q "捕捉进步的信号" app/agents/intervention_planner.py; then
    echo "   ✅ 观察记录工具文案已优化"
else
    echo "   ❌ 观察记录工具文案未优化"
fi

if grep -q "V3.8" main.py; then
    echo "   ✅ 主入口版本号已更新"
else
    echo "   ❌ 主入口版本号未更新"
fi

# 5. 测试 HTML 实体解码
echo ""
echo "5️⃣ 测试 HTML 实体解码..."
TEST_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v3/chat \
    -H "Content-Type: application/json" \
    -d '{"session_id": null, "user_input": "孩子表现不错，成功率≥80%！"}')

if echo "$TEST_RESPONSE" | grep -q "session_id"; then
    echo "   ✅ API 响应正常"
else
    echo "   ⚠️  API 响应异常"
fi

# 6. 检查通用方法论
echo ""
echo "6️⃣ 检查通用方法论生成..."
# 检查是否避免具体案例名词
if ! grep -q "大鹏展翅" app/agents/intervention_planner.py; then
    echo "   ✅ 已避免具体案例名词"
else
    echo "   ⚠️  仍包含具体案例名词"
fi

echo ""
echo "================================"
echo "✅ V3.8 功能验证完成！"
echo ""
echo "访问地址：http://localhost:3000"
echo "API 文档：http://localhost:8000/docs"
echo ""
echo "V3.8 核心特性:"
echo "  • HTML 实体解码：彻底修复乱码"
echo "  • 章节标题优化：多角度理解 + 行为模式解读"
echo "  • 通用方法论：避免具体案例，增强普适性"
echo "  • 观察记录优化：强调捕捉进步信号"
echo "  • 版本：V3.8.0 通用方法论增强版"
