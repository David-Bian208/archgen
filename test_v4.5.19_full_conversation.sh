#!/bin/bash
# V4.5.19 完整对话测试脚本
# 模拟真实用户场景，测试模糊回答检测与共情回应

API_URL="http://localhost:8000/api/v4/chat"
SESSION_ID="test-v4519-$(date +%s)"

echo "============================================================"
echo "V4.5.19 完整对话测试"
echo "会话 ID: $SESSION_ID"
echo "============================================================"
echo ""

# 第 1 轮：用户使用模糊标签
echo "【第 1 轮】用户：孩子社交互动中缺少深度关注"
echo "----------------------------------------------------------"
RESPONSE=$(curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\", \"user_input\": \"孩子社交互动中缺少深度关注\"}")

echo "系统回应：$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('message','N/A')[:200])")"
echo "回应类型：$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('response_type','N/A'))")"
echo "当前阶段：$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('state','N/A'))")"
echo "模糊类型：$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('vague_type','N/A'))")"
echo ""

# 第 2 轮：用户说"不知道"
echo "【第 2 轮】用户：不知道怎么回答你，要根据实际情况"
echo "----------------------------------------------------------"
RESPONSE=$(curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\", \"user_input\": \"不知道怎么回答你，要根据实际情况\"}")

echo "系统回应：$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('message','N/A')[:200])")"
echo "回应类型：$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('response_type','N/A'))")"
echo "模糊类型：$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('vague_type','N/A'))")"
echo ""

# 第 3 轮：用户说"看情况"
echo "【第 3 轮】用户：要看具体事情"
echo "----------------------------------------------------------"
RESPONSE=$(curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\", \"user_input\": \"要看具体事情\"}")

echo "系统回应：$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('message','N/A')[:200])")"
echo "回应类型：$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('response_type','N/A'))")"
echo "模糊类型：$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('vague_type','N/A'))")"
echo ""

# 第 4 轮：用户给出具体例子
echo "【第 4 轮】用户：比如今天早上在幼儿园做操时，叫他排队他不理"
echo "----------------------------------------------------------"
RESPONSE=$(curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\", \"user_input\": \"比如今天早上在幼儿园做操时，叫他排队他不理\"}")

echo "系统回应：$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('message','N/A')[:200])")"
echo "回应类型：$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('response_type','N/A'))")"
echo "当前阶段：$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('state','N/A'))")"
echo ""

# 第 5 轮：用户提供年龄
echo "【第 5 轮】用户：5 岁，男孩"
echo "----------------------------------------------------------"
RESPONSE=$(curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\", \"user_input\": \"5 岁，男孩\"}")

echo "系统回应：$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('message','N/A')[:200])")"
echo "回应类型：$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('response_type','N/A'))")"
echo "当前阶段：$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('state','N/A'))")"
echo ""

# 第 6 轮：用户提供后果
echo "【第 6 轮】用户：老师提醒他才会继续"
echo "----------------------------------------------------------"
RESPONSE=$(curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\", \"user_input\": \"老师提醒他才会继续\"}")

echo "系统回应：$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('message','N/A')[:200])")"
echo "回应类型：$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('response_type','N/A'))")"
echo "当前阶段：$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('state','N/A'))")"
echo ""

echo "============================================================"
echo "测试完成！"
echo "============================================================"
echo ""
echo "查看会话状态："
curl -s "http://localhost:8000/api/v4/session/$SESSION_ID" | python3 -m json.tool
