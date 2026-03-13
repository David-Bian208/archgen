#!/bin/bash
# V4.2 简单验证测试

BASE_URL="http://localhost:8000/api/v4"

echo "=========================================="
echo "V4.2 简单验证测试"
echo "=========================================="

# 第 1 轮
echo "【第 1 轮】用户：孩子做操时有时会发呆"
RESP1=$(curl -s -X POST "$BASE_URL/chat" -H "Content-Type: application/json" -d '{"user_input": "孩子做操时有时会发呆"}')
SESSION=$(echo $RESP1 | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))")
echo "AI: $(echo $RESP1 | python3 -c "import sys,json; print(json.load(sys.stdin).get('message','')[:80])")..."
echo

# 第 2 轮
echo "【第 2 轮】用户：在教室里，其他小朋友认真做"
RESP2=$(curl -s -X POST "$BASE_URL/chat" -H "Content-Type: application/json" -d "{\"session_id\": \"$SESSION\", \"user_input\": \"在教室里，其他小朋友认真做\"}")
echo "AI: $(echo $RESP2 | python3 -c "import sys,json; print(json.load(sys.stdin).get('message','')[:80])")..."
echo

# 第 3 轮
echo "【第 3 轮】用户：眼神迷茫，不看老师就做不好"
RESP3=$(curl -s -X POST "$BASE_URL/chat" -H "Content-Type: application/json" -d "{\"session_id\": \"$SESSION\", \"user_input\": \"眼神迷茫，不看老师就做不好\"}")
echo "AI: $(echo $RESP3 | python3 -c "import sys,json; print(json.load(sys.stdin).get('message','')[:80])")..."
echo

# 第 4 轮
echo "【第 4 轮】用户：是的，需要老师提醒才继续"
RESP4=$(curl -s -X POST "$BASE_URL/chat" -H "Content-Type: application/json" -d "{\"session_id\": \"$SESSION\", \"user_input\": \"是的，需要老师提醒才继续\"}")
echo "AI: $(echo $RESP4 | python3 -c "import sys,json; print(json.load(sys.stdin).get('message','')[:80])")..."
echo

# 第 5 轮
echo "【第 5 轮】用户：老师会走到他身边提醒"
RESP5=$(curl -s -X POST "$BASE_URL/chat" -H "Content-Type: application/json" -d "{\"session_id\": \"$SESSION\", \"user_input\": \"老师会走到他身边提醒\"}")
echo "AI: $(echo $RESP5 | python3 -c "import sys,json; print(json.load(sys.stdin).get('message','')[:80])")..."
echo

# 第 6 轮 - 结束
echo "【第 6 轮】用户：没有了"
RESP6=$(curl -s -X POST "$BASE_URL/chat" -H "Content-Type: application/json" -d "{\"session_id\": \"$SESSION\", \"user_input\": \"没有了\"}")
STATUS=$(echo $RESP6 | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))")
echo "状态：$STATUS"
echo

if [ "$STATUS" = "completed" ]; then
    echo "=========================================="
    echo "✅ 对话完成，检查报告结构"
    echo "=========================================="
    echo "$RESP6" | python3 -c "
import sys, json
data = json.load(sys.stdin)
report_data = data.get('data', {})
report = report_data.get('report', {})

print()
print('📊 报告字段检查:')
print(f'  - summary: {\"✅\" if report.get(\"summary\") else \"❌\"}')
print(f'  - clinical_differential: {\"✅\" if report.get(\"clinical_differential\") else \"❌\"}')
print(f'  - primary_hypothesis: {\"✅\" if report.get(\"primary_hypothesis\") else \"❌\"}')
print(f'  - supporting_evidence: {\"✅\" if report.get(\"supporting_evidence\") else \"❌\"}')
print(f'  - core_capability_goal: {\"✅\" if report.get(\"core_capability_goal\") else \"❌\"}')

intervention_plan = report_data.get('intervention_plan', {})
four_step = intervention_plan.get('four_step_plan', {}) if intervention_plan else {}

print()
print('📊 干预计划四步结构:')
print(f'  - core_idea: {\"✅\" if four_step.get(\"core_idea\") else \"❌\"}')
print(f'  - our_plan: {\"✅\" if four_step.get(\"our_plan\") else \"❌\"}')
print(f'  - success_picture: {\"✅\" if four_step.get(\"success_picture\") else \"❌\"}')
print(f'  - first_step: {\"✅\" if four_step.get(\"first_step\") else \"❌\"}')

if report.get('summary'):
    print()
    print('📝 摘要内容:')
    print(f'  {report[\"summary\"][:200]}...')
"
    echo
    echo "=========================================="
    echo "测试完成"
    echo "=========================================="
else
    echo "❌ 对话未完成"
fi
