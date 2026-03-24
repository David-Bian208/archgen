#!/bin/bash
# 快速验证脚本 - 使用 curl

echo "============================================================"
echo "V4.10.3 API 快速验证"
echo "============================================================"

# 第 1 轮
echo -e "\n[1/5] 家长输入..."
RESP1=$(curl -s -X POST http://localhost:8000/api/v4/chat \
  -H "Content-Type: application/json" \
  -d '{"user_input": "孩子不跟小朋友玩"}')
SESSION=$(echo $RESP1 | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))")
echo "  Session: $SESSION"

# 第 2 轮
echo "[2/5] 5 岁..."
RESP2=$(curl -s -X POST http://localhost:8000/api/v4/chat \
  -H "Content-Type: application/json" \
  -d "{\"user_input\": \"5 岁\", \"session_id\": \"$SESSION\"}")
echo "  $(echo $RESP2 | python3 -c "import sys,json; print('status=' + json.load(sys.stdin).get('status',''))")"

# 第 3 轮
echo "[3/5] 女孩..."
RESP3=$(curl -s -X POST http://localhost:8000/api/v4/chat \
  -H "Content-Type: application/json" \
  -d "{\"user_input\": \"女孩\", \"session_id\": \"$SESSION\"}")
echo "  $(echo $RESP3 | python3 -c "import sys,json; print('status=' + json.load(sys.stdin).get('status',''))")"

# 第 4 轮
echo "[4/5] 在幼儿园..."
RESP4=$(curl -s -X POST http://localhost:8000/api/v4/chat \
  -H "Content-Type: application/json" \
  -d "{\"user_input\": \"在幼儿园\", \"session_id\": \"$SESSION\"}")
echo "  $(echo $RESP4 | python3 -c "import sys,json; print('status=' + json.load(sys.stdin).get('status',''))")"

# 第 5 轮
echo "[5/5] 完成评估..."
RESP5=$(curl -s -X POST http://localhost:8000/api/v4/chat \
  -H "Content-Type: application/json" \
  -d "{\"user_input\": \"完成评估\", \"session_id\": \"$SESSION\"}")

echo -e "\n============================================================"
echo $RESP5 | python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'report' in data:
    r = data['report']
    print('✅ 报告生成成功！')
    print(f\"  功能判断：{r.get('functional_judgment', 'N/A')}\")
    print(f\"  能力缺口：{r.get('capability_hypothesis', 'N/A')[:60]}...\")
else:
    print('❌ 报告未生成')
    print(f\"  status={data.get('status', 'N/A')}\")
"
echo "============================================================"
