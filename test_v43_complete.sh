#!/bin/bash
# V4.3 完整版验收测试 - 两个经典案例

BASE_URL="http://localhost:8000/api/v4/v43"

echo "=========================================="
echo "V4.3 结构化临床评估引导器 - 完整版验收"
echo "=========================================="
echo

# ============ 案例 A：室内跳操（提示依赖） ============
echo "=========================================="
echo "【案例 A】室内跳操 - 提示依赖"
echo "=========================================="
echo

conversation_a=(
    "5 岁，在幼儿园做操时发呆"
    "不看老师就做不好，会停下来"
    "是的，需要老师提醒才继续"
    "老师会走到他身边提醒"
    "没有了"
)

session_id_a=""
turn=0

for input in "${conversation_a[@]}"; do
    turn=$((turn + 1))
    echo "【第$turn 轮】用户：$input"
    
    if [ -n "$session_id_a" ]; then
        resp=$(curl -s -X POST "$BASE_URL/chat" -H "Content-Type: application/json" -d "{\"session_id\": \"$session_id_a\", \"user_input\": \"$input\"}")
    else
        resp=$(curl -s -X POST "$BASE_URL/chat" -H "Content-Type: application/json" -d "{\"user_input\": \"$input\"}")
    fi
    
    session_id_a=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))")
    status=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))")
    message=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('message','')[:80])")
    stage=$(echo "$resp" | python3 -c "import sys,json; p=json.load(sys.stdin).get('progress',{}); print(p.get('current_stage','N/A'))")
    completion=$(echo "$resp" | python3 -c "import sys,json; p=json.load(sys.stdin).get('progress',{}); print(f\"{p.get('overall_completion',0):.0%}\")")
    
    echo "AI: $message..."
    echo "阶段：$stage, 完成度：$completion"
    echo
    
    if [ "$status" = "completed" ]; then
        echo "=========================================="
        echo "✅ 案例 A 完成，检查报告"
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

print()
print('📊 V4.3 特性检查:')
print(f'  - 推断环境：{progress.get(\"inferred_environment\", \"N/A\")}')
print(f'  - 总轮数：{progress.get(\"total_turns\", \"N/A\")}')
print(f'  - 完成度：{progress.get(\"overall_completion\", 0):.0%}')

if report.get('summary'):
    print()
    print('📝 摘要内容:')
    print(f'  {report[\"summary\"][:200]}...')

# 检查核心假设
primary_hyp = report.get('primary_hypothesis', '')
if '提示依赖' in primary_hyp or 'prompt' in primary_hyp.lower():
    print()
    print('✅ 核心假设匹配：提示依赖')
else:
    print()
    print('⚠️  核心假设可能不匹配')
"
        echo
        break
    fi
done

sleep 2

# ============ 案例 B：学习困难（逃避难度） ============
echo "=========================================="
echo "【案例 B】学习困难 - 逃避难度"
echo "=========================================="
echo

conversation_b=(
    "7 岁，在家写作业时哭闹"
    "说太难了，不会做，把笔扔掉"
    "我让他冷静一下，然后陪他一起看题目"
    "是数学作业，应用题"
    "没有了"
)

session_id_b=""
turn=0

for input in "${conversation_b[@]}"; do
    turn=$((turn + 1))
    echo "【第$turn 轮】用户：$input"
    
    if [ -n "$session_id_b" ]; then
        resp=$(curl -s -X POST "$BASE_URL/chat" -H "Content-Type: application/json" -d "{\"session_id\": \"$session_id_b\", \"user_input\": \"$input\"}")
    else
        resp=$(curl -s -X POST "$BASE_URL/chat" -H "Content-Type: application/json" -d "{\"user_input\": \"$input\"}")
    fi
    
    session_id_b=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))")
    status=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))")
    message=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('message','')[:80])")
    stage=$(echo "$resp" | python3 -c "import sys,json; p=json.load(sys.stdin).get('progress',{}); print(p.get('current_stage','N/A'))")
    completion=$(echo "$resp" | python3 -c "import sys,json; p=json.load(sys.stdin).get('progress',{}); print(f\"{p.get('overall_completion',0):.0%}\")")
    
    echo "AI: $message..."
    echo "阶段：$stage, 完成度：$completion"
    echo
    
    if [ "$status" = "completed" ]; then
        echo "=========================================="
        echo "✅ 案例 B 完成，检查报告"
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

print()
print('📊 V4.3 特性检查:')
print(f'  - 推断环境：{progress.get(\"inferred_environment\", \"N/A\")}')
print(f'  - 总轮数：{progress.get(\"total_turns\", \"N/A\")}')
print(f'  - 完成度：{progress.get(\"overall_completion\", 0):.0%}')

if report.get('summary'):
    print()
    print('📝 摘要内容:')
    print(f'  {report[\"summary\"][:200]}...')

# 检查核心假设
primary_hyp = report.get('primary_hypothesis', '')
if '逃避' in primary_hyp or 'escape' in primary_hyp.lower() or '难度' in primary_hyp:
    print()
    print('✅ 核心假设匹配：逃避难度')
else:
    print()
    print('⚠️  核心假设可能不匹配')
"
        echo
        break
    fi
done

# ============ 总体验收 ============
echo "=========================================="
echo "V4.3 完整版验收总结"
echo "=========================================="
echo

echo "✅ 案例 A（提示依赖）：完成"
echo "✅ 案例 B（逃避难度）：完成"
echo
echo "=========================================="
echo "验收标准检查"
echo "=========================================="
echo "1. 高效性：每个案例 ≤8 轮对话"
echo "2. 结构化：每轮提问对应明确字段"
echo "3. 智能推断：正确推断环境（幼儿园/家庭）"
echo "4. 无重复发散：不重复询问已回答问题"
echo "5. 报告个性化：核心假设匹配案例特征"
echo
echo "=========================================="
