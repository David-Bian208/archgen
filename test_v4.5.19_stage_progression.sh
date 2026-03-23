#!/bin/bash
# V4.5.19 最终测试 - 验证阶段推进逻辑

API_URL="http://localhost:8000/api/v4/chat"
SESSION="test-$(date +%s)"

echo "========================================"
echo "V4.5.19 阶段推进逻辑测试"
echo "会话 ID: $SESSION"
echo "========================================"
echo ""

# 轮次 1
echo "【轮次 1】用户：孩子社交互动有问题"
RESP=$(curl -s -X POST "$API_URL" -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION\", \"user_input\": \"孩子社交互动有问题\"}")
echo "系统：$(echo $RESP | python3 -c "import sys,json; print(json.load(sys.stdin)['message'][:100])")"
echo "阶段：$(echo $RESP | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])")"
echo ""

# 轮次 2
echo "【轮次 2】用户：叫他不理人"
RESP=$(curl -s -X POST "$API_URL" -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION\", \"user_input\": \"叫他不理人\"}")
echo "系统：$(echo $RESP | python3 -c "import sys,json; print(json.load(sys.stdin)['message'][:100])")"
echo "阶段：$(echo $RESP | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])")"
echo "已填充：$(echo $RESP | python3 -c "import sys,json; print(json.load(sys.stdin)['progress']['filled_fields'])")"
echo ""

# 轮次 3
echo "【轮次 3】用户：今天早上在幼儿园做操时"
RESP=$(curl -s -X POST "$API_URL" -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION\", \"user_input\": \"今天早上在幼儿园做操时\"}")
echo "系统：$(echo $RESP | python3 -c "import sys,json; print(json.load(sys.stdin)['message'][:100])")"
echo "阶段：$(echo $RESP | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])")"
echo "已填充：$(echo $RESP | python3 -c "import sys,json; print(json.load(sys.stdin)['progress']['filled_fields'])")"
echo ""

# 轮次 4
echo "【轮次 4】用户：5 岁男孩"
RESP=$(curl -s -X POST "$API_URL" -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION\", \"user_input\": \"5 岁男孩\"}")
echo "系统：$(echo $RESP | python3 -c "import sys,json; print(json.load(sys.stdin)['message'][:100])")"
echo "阶段：$(echo $RESP | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])")"
echo ""

echo "========================================"
echo "测试完成"
echo "========================================"
