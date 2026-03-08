#!/bin/bash
# V3.6 功能快速验证脚本

echo "🧪 记录观察助手 V3.6 - 功能验证"
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
if [[ "$API_TITLE" == *"V3.6"* ]]; then
    echo "   ✅ API 版本：$API_TITLE"
else
    echo "   ⚠️  API 版本：$API_TITLE (期望 V3.6)"
fi

# 3. 检查前端文件
echo ""
echo "3️⃣ 检查前端关键文件..."
if [ -f "frontend/utils/filters.js" ]; then
    echo "   ✅ 全局过滤器已创建"
else
    echo "   ❌ 全局过滤器缺失"
fi

if grep -q "V3.6" frontend/App.vue; then
    echo "   ✅ 前端版本号已更新"
else
    echo "   ❌ 前端版本号未更新"
fi

if grep -q "clinical-differential" frontend/App.vue; then
    echo "   ✅ 临床鉴别思考模块已添加"
else
    echo "   ❌ 临床鉴别思考模块缺失"
fi

if grep -q "开始新的记录" frontend/App.vue; then
    echo "   ✅ 按钮文案已更新"
else
    echo "   ❌ 按钮文案未更新"
fi

# 4. 检查后端文件
echo ""
echo "4️⃣ 检查后端关键修改..."
if grep -q "clinical_differential" app/agents/insight_analyzer.py; then
    echo "   ✅ 洞察分析器已更新"
else
    echo "   ❌ 洞察分析器未更新"
fi

if grep -q "clinical_differential" app/agents/guided_recorder_agent_v3.py; then
    echo "   ✅ 引导式记录员已更新"
else
    echo "   ❌ 引导式记录员未更新"
fi

if grep -q "strategy_hint" app/agents/intervention_planner.py; then
    echo "   ✅ 干预规划器已优化"
else
    echo "   ❌ 干预规划器未优化"
fi

# 5. 测试 API 端点
echo ""
echo "5️⃣ 测试 API 端点..."
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
echo "✅ V3.6 功能验证完成！"
echo ""
echo "访问地址：http://localhost:3000"
echo "API 文档：http://localhost:8000/docs"
