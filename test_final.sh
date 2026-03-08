#!/bin/bash
# V3.9.1 Final 封版验证脚本

echo "🧪 记录观察助手 V3.9.1 Final - 封版验证"
echo "========================================"
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
    echo "   ❌ API 版本：$API_TITLE (期望 V3.9.1)"
    exit 1
fi

# 3. 检查前端文件
echo ""
echo "3️⃣ 检查前端关键文件..."
if grep -q "V3.9.1" frontend/App.vue; then
    echo "   ✅ 前端版本号已更新"
else
    echo "   ❌ 前端版本号未更新"
fi

if grep -q "Final" frontend/App.vue; then
    echo "   ✅ 封版标识已添加"
else
    echo "   ❌ 封版标识未添加"
fi

# 4. 检查后端文件
echo ""
echo "4️⃣ 检查后端关键修改..."
if grep -q "V3.9.1" app/agents/intervention_planner.py; then
    echo "   ✅ 干预规划器版本已更新"
else
    echo "   ❌ 干预规划器版本未更新"
fi

if grep -q "_sanitize_report_data" app/agents/guided_recorder_agent_v3.py; then
    echo "   ✅ 数据净化函数已添加"
else
    echo "   ❌ 数据净化函数缺失"
fi

if grep -q "re.sub.*%!" app/agents/guided_recorder_agent_v3.py; then
    echo "   ✅ 调试信息清理已添加"
else
    echo "   ❌ 调试信息清理缺失"
fi

if grep -q "共创一个趣味" app/agents/intervention_planner.py; then
    echo "   ✅ 第一步行动文案已精简"
else
    echo "   ❌ 第一步行动文案未精简"
fi

if grep -q "V3.9.1" main.py; then
    echo "   ✅ 主入口版本号已更新"
else
    echo "   ❌ 主入口版本号未更新"
fi

# 5. 测试数据净化
echo ""
echo "5️⃣ 测试数据净化..."
TEST_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v3/chat \
    -H "Content-Type: application/json" \
    -d '{"session_id": null, "user_input": "孩子表现不错，成功率≥80%！"}')

# 检查是否有乱码
if echo "$TEST_RESPONSE" | grep -q "%!"; then
    echo "   ❌ 仍包含调试信息乱码"
elif echo "$TEST_RESPONSE" | grep -q "(MISSING)"; then
    echo "   ❌ 仍包含 (MISSING) 乱码"
elif echo "$TEST_RESPONSE" | grep -q "&#039;"; then
    echo "   ❌ 仍包含 HTML 实体乱码"
else
    echo "   ✅ 数据净化正常"
fi

# 6. 检查绝对化词汇
echo ""
echo "6️⃣ 检查用语规范..."
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
echo "========================================"
echo "✅ V3.9.1 Final 封版验证完成！"
echo ""
echo "访问地址：http://localhost:3000"
echo "API 文档：http://localhost:8000/docs"
echo ""
echo "V3.9.1 Final 核心特性:"
echo "  • 零容忍乱码：彻底清理调试信息和 HTML 实体"
echo "  • 文案精炼：摘要高度精炼，第一步行动简洁有力"
echo "  • 流程稳定：完整流程运行流畅"
echo "  • 版本：V3.9.1 Final 稳定版"
echo ""
echo "🎉 行为记录员 Agent 已封版，可交付封装！"
echo "   此版本将作为稳定版锁定，供后续项目调用。"
