#!/bin/bash
# V4.3 MVP 验收测试

BASE_URL="http://localhost:8000/api/v4/v43"

echo "=========================================="
echo "V4.3 结构化评估引导器 - MVP 验收测试"
echo "=========================================="
echo

# 测试案例：室内跳操发呆
conversation=(
    "孩子做操时有时会发呆"
    "在教室里，其他小朋友认真做"
    "眼神迷茫，不看老师就做不好"
    "是的，需要老师提醒才继续"
    "老师会走到他身边提醒"
    "没有了"
)

session_id=""
turn=0

for input in "${conversation[@]}"; do
    turn=$((turn + 1))
    echo "【第$turn 轮】用户：$input"
    
    if [ -n "$session_id" ]; then
        resp=$(curl -s -X POST "$BASE_URL/chat" -H "Content-Type: application/json" -d "{\"session_id\": \"$session_id\", \"user_input\": \"$input\"}")
    else
        resp=$(curl -s -X POST "$BASE_URL/chat" -H "Content-Type: application/json" -d "{\"user_input\": \"$input\"}")
    fi
    
    session_id=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))")
    status=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))")
    message=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('message','')[:80])")
    progress=$(echo "$resp" | python3 -c "import sys,json; p=json.load(sys.stdin).get('progress',{}); print(f\"完成度:{p.get('completion_rate',0):.0%} 已填:{len(p.get('filled_fields',[]))}字段\")")
    
    echo "AI: $message..."
    echo "进度：$progress"
    echo
    
    if [ "$status" = "completed" ]; then
        echo "=========================================="
        echo "✅ 对话完成，检查报告结构"
        echo "=========================================="
        
        echo "$resp" | python3 -c "
import sys, json
data = json.load(sys.stdin)
report_data = data.get('data', {})
report = report_data.get('report', {})
progress = data.get('progress', {})

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

print()
print('📊 V4.3 进度信息:')
print(f'  - 总轮数：{progress.get(\"total_turns\", \"N/A\")}')
print(f'  - 完成度：{progress.get(\"completion_rate\", 0):.0%}')
print(f'  - 已填字段：{len(progress.get(\"filled_fields\", []))}')

if report.get('summary'):
    print()
    print('📝 摘要内容:')
    print(f'  {report[\"summary\"][:200]}...')
"
        echo
        echo "=========================================="
        echo "验收检查"
        echo "=========================================="
        
        # 检查轮数
        total_turns=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('progress',{}).get('total_turns',99))")
        if [ "$total_turns" -le 5 ]; then
            echo "✅ 提问次数：$total_turns 轮 (≤5 轮)"
        else
            echo "❌ 提问次数：$total_turns 轮 (>5 轮)"
        fi
        
        # 检查报告完整性
        has_all_fields=$(echo "$resp" | python3 -c "
import sys, json
data = json.load(sys.stdin)
report = data.get('data', {}).get('report', {})
required = ['summary', 'clinical_differential', 'primary_hypothesis', 'supporting_evidence', 'core_capability_goal']
missing = [f for f in required if not report.get(f)]
print('✅' if not missing else '❌')
")
        echo "✅ 报告完整性：$has_all_fields"
        
        echo
        echo "=========================================="
        echo "V4.3 MVP 测试完成"
        echo "=========================================="
        break
    fi
done
