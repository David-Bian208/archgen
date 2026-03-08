#!/bin/bash
# V3.7 最终优化版 - 功能验证脚本

echo "🧪 记录观察助手 V3.7 - 功能验证"
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
if [[ "$API_TITLE" == *"V3.7"* ]]; then
    echo "   ✅ API 版本：$API_TITLE"
else
    echo "   ❌ API 版本：$API_TITLE (期望 V3.7)"
    exit 1
fi

# 3. 检查前端文件
echo ""
echo "3️⃣ 检查前端关键文件..."
if [ -f "frontend/utils/filters.js" ]; then
    echo "   ✅ 全局过滤器已创建"
else
    echo "   ❌ 全局过滤器缺失"
fi

if grep -q "V3.7" frontend/App.vue; then
    echo "   ✅ 前端版本号已更新"
else
    echo "   ❌ 前端版本号未更新"
fi

if grep -q "four-step-container" frontend/App.vue; then
    echo "   ✅ 四步结构 UI 已添加"
else
    echo "   ❌ 四步结构 UI 缺失"
fi

if grep -q "成功时刻" frontend/App.vue; then
    echo "   ✅ 成功时刻记录卡已更新"
else
    echo "   ❌ 成功时刻记录卡未更新"
fi

# 4. 检查后端文件
echo ""
echo "4️⃣ 检查后端关键修改..."
if grep -q "four_step_plan" app/agents/intervention_planner.py; then
    echo "   ✅ 四步结构生成逻辑已添加"
else
    echo "   ❌ 四步结构生成逻辑缺失"
fi

if grep -q "sanitize_text" app/agents/intervention_planner.py; then
    echo "   ✅ 文本安全处理已添加"
else
    echo "   ❌ 文本安全处理缺失"
fi

if grep -q "four_step_plan" app/agents/guided_recorder_agent_v3.py; then
    echo "   ✅ 引导式记录员已更新"
else
    echo "   ❌ 引导式记录员未更新"
fi

if grep -q "V3.7" main.py; then
    echo "   ✅ 主入口版本号已更新"
else
    echo "   ❌ 主入口版本号未更新"
fi

# 5. 测试特殊字符处理
echo ""
echo "5️⃣ 测试特殊字符处理..."
TEST_TEXT="成功率≥80%，表现不错！"
ENCODED=$(echo -n "$TEST_TEXT" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))")
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v3/chat \
    -H "Content-Type: application/json" \
    -d "{\"session_id\": null, \"user_input\": $ENCODED}")

if echo "$RESPONSE" | grep -q "session_id"; then
    echo "   ✅ 特殊字符输入处理正常"
else
    echo "   ⚠️  特殊字符输入处理异常"
fi

# 6. 测试 API 端点
echo ""
echo "6️⃣ 测试 API 端点..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v3/chat \
    -H "Content-Type: application/json" \
    -d '{"session_id": null, "user_input": "孩子做操时有时会发呆"}')

if echo "$RESPONSE" | grep -q "session_id"; then
    echo "   ✅ /api/v3/chat 端点正常"
else
    echo "   ⚠️  /api/v3/chat 端点响应异常"
fi

echo ""
echo "================================"
echo "✅ V3.7 功能验证完成！"
echo ""
echo "访问地址：http://localhost:3000"
echo "API 文档：http://localhost:8000/docs"
echo ""
echo "V3.7 核心特性:"
echo "  • 四步结构：核心思路 → 计划 → 成功画面 → 第一步"
echo "  • 成功时刻记录卡：更具鼓励性的观察工具"
echo "  • 文本安全：双重处理，无乱码"
echo "  • 版本：V3.7.0 最终优化版"
