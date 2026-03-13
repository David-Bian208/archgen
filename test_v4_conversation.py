#!/usr/bin/env python3
"""
V4.0 多轮对话模拟测试脚本
模拟 20 轮完整对话流程
"""

import json
import requests

BASE_URL = "http://localhost:8000"
session_id = None

# 测试对话场景：孩子行为记录
test_conversation = [
    "今天在幼儿园，老师让他做手工，他觉得太难了，一开始就不想做",
    "在小组桌，和其他 3 个小朋友一起",
    "剪纸工，要剪一个圆形",
    "他说不会剪，手不听使唤，把剪刀放下了",
    "老师过来帮他剪了一下，然后他就继续做了",
    "谢谢",
]

print("=" * 70)
print("V4.0 多轮对话模拟测试")
print("=" * 70)

for i, user_input in enumerate(test_conversation, 1):
    print(f"\n【轮次 {i}】")
    print(f"用户：{user_input}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v4/chat",
            json={"session_id": session_id, "user_input": user_input},
            timeout=30
        )
        data = response.json()
        
        # 保存 session_id
        session_id = data.get("session_id", session_id)
        
        # 显示响应
        state = data.get("state", "N/A")
        message = data.get("message", "")[:200]
        status = data.get("status", "N/A")
        
        print(f"状态：{state}")
        print(f"AI: {message}...")
        print(f"完成：{status}")
        
        # 如果完成，显示报告
        if status == "completed":
            print("\n" + "=" * 70)
            print("✅ 对话完成！分析报告：")
            print("=" * 70)
            report_data = data.get("data", {})
            print(f"情境：{report_data.get('context', 'N/A')[:100]}")
            print(f"行为：{report_data.get('child_behavior', 'N/A')[:100]}")
            print(f"回应：{report_data.get('others_response', 'N/A')[:100]}")
            print(f"核心洞察：{report_data.get('core_insight', 'N/A')[:100]}")
            break
            
    except Exception as e:
        print(f"❌ 错误：{e}")
        break

print("\n" + "=" * 70)
print(f"测试完成！总会话 ID: {session_id}")
print("=" * 70)
