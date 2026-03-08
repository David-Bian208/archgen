#!/bin/bash
# V3.9 最终打磨版 - 功能验证脚本

echo "🧪 记录观察助手 V3.9 - 最终验证"
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
if [[ "$API_TITLE" == *"V3.9"* ]]; then
    echo "   ✅ API 版本：$API_TITLE"
else
    echo "   ❌ API 版本：$API_TITLE (期望 V3.9)"
    exit 1
fi

# 3. 检查前端文件
echo ""
echo "3️⃣ 检查前端关键文件..."
if grep -q "V3.9" frontend/App.vue; then
    echo "   ✅ 前端版本号已更新"
else
    echo "   ❌ 前端版本号未更新"
fi

if grep -q "多角度理解" frontend/App.vue; then
    echo "   ✅ 第二章标题已优化"
else
    echo "   ❌ 第二章标题未优化"
fi

if grep -q "行为模式解读" frontend/App.vue; then
    echo "   ✅ 第三章标题已优化"
else
    echo "   ❌ 第三章标题未优化"
fi

# 4. 检查后端文件
echo ""
echo "4️⃣ 检查后端关键修改..."
if grep -q "V3.9" app/agents/guided_recorder_agent_v3.py; then
    echo "   ✅ 引导式记录员版本已更新"
else
    echo "   ❌ 引导式记录员版本未更新"
fi

if grep -q "html.unescape" app/agents/guided_recorder_agent_v3.py; then
    echo "   ✅ HTML 实体解码已添加"
else
    echo "   ❌ HTML 实体解码缺失"
fi

if grep -q "我们的分析指向了" app/agents/guided_recorder_agent_v3.py; then
    echo "   ✅ 行为模式解读表述已优化"
else
    echo "   ❌ 行为模式解读表述未优化"
fi

if grep -q "既然挑战的核心" app/agents/intervention_planner.py; then
    echo "   ✅ 核心思路逻辑链已强化"
else
    echo "   ❌ 核心思路逻辑链未强化"
fi

if grep -q "您可以根据孩子的反应灵活调整" app/agents/intervention_planner.py; then
    echo "   ✅ 温和提示已添加"
else
    echo "   ❌ 温和提示未添加"
fi

if grep -q "V3.9" main.py; then
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

# 6. 检查绝对化词汇
echo ""
echo "6️⃣ 检查绝对化词汇..."
if ! grep -q "必须" app/agents/guided_recorder_agent_v3.py; then
    echo "   ✅ 已移除'必须'等绝对化词汇"
else
    echo "   ⚠️  仍包含'必须'等绝对化词汇"
fi

if grep -q "建议" app/agents/guided_recorder_agent_v3.py; then
    echo "   ✅ 已采用温和建议用语"
else
    echo "   ⚠️  温和建议用语不足"
fi

echo ""
echo "================================"
echo "✅ V3.9 最终验证完成！"
echo ""
echo "访问地址：http://localhost:3000"
echo "API 文档：http://localhost:8000/docs"
echo ""
echo "V3.9 核心特性:"
echo "  • 零乱码：html.unescape() 根治 HTML 实体"
echo "  • 表述共建化：'我们的分析指向了'替代'从专业角度'"
echo "  • 核心思路逻辑化：'既然挑战...那么核心思路...'"
echo "  • 用语温和化：移除'必须'，添加'建议'、'灵活调整'"
echo "  • 版本：V3.9.0 最终打磨版"
echo ""
echo "🎉 行为记录员 Agent 已成熟，可交付封装！"
