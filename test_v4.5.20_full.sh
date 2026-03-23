#!/bin/bash
# V4.5.20 完整测试脚本

API="http://localhost:8000/api/v4/chat"
SESSION="v4520-test-$(date +%s)"

echo "=============================================="
echo "V4.5.20 完整功能测试"
echo "会话 ID: $SESSION"
echo "=============================================="
echo ""

# 测试场景：社交技能不足
echo "【测试场景】社交技能不足诊断 + 干预匹配"
echo "----------------------------------------------"
echo ""

# 轮次 1：用户提供详细场景
echo "【轮次 1】用户：4.5 岁女孩，上周在迪士尼和玩伴争抢队长，拥抱不知轻重"
RESP=$(curl -s -X POST "$API" -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION\", \"user_input\": \"4.5 岁女孩，上周在迪士尼和玩伴争抢队长，拥抱不知轻重\"}")
echo "系统阶段：$(echo $RESP | python3 -c "import sys,json; print(json.load(sys.stdin).get('state','N/A'))")"
echo "已填充字段：$(echo $RESP | python3 -c "import sys,json; print(json.load(sys.stdin).get('progress',{}).get('filled_fields',[]))")"
echo ""

# 轮次 2：用户提供后果
echo "【轮次 2】用户：我过去拉开他们，告诉他们轮流当"
RESP=$(curl -s -X POST "$API" -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION\", \"user_input\": \"我过去拉开他们，告诉他们轮流当\"}")
STATUS=$(echo $RESP | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','N/A'))")
echo "状态：$STATUS"

if [ "$STATUS" = "completed" ]; then
    echo "✅ 报告已生成！"
    echo ""
    echo "【诊断验证】"
    echo $RESP | python3 -c "
import sys,json
d=json.load(sys.stdin)
report = d.get('data',{}).get('report',{})
print(f\"功能判断：{report.get('functional_judgment','N/A')[:80]}\")
print(f\"能力缺口：{report.get('core_capability_goal','N/A')[:80]}\")
"
    echo ""
    echo "【干预验证】"
    echo $RESP | python3 -c "
import sys,json
d=json.load(sys.stdin)
plan = d.get('data',{}).get('intervention_plan',{})
phase_name = plan.get('phase_name','N/A') if plan else 'N/A'
print(f\"干预计划：{phase_name[:100]}\")
if '社交' in phase_name or '教学' in phase_name:
    print('✅ 干预匹配：社交技能教学')
else:
    print('❌ 干预不匹配')
"
else
    echo "继续追问中..."
fi

echo ""
echo "=============================================="
echo "测试完成"
echo "=============================================="
