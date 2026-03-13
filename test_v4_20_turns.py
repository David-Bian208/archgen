#!/usr/bin/env python3
"""
V4.0 20 轮完整对话模拟测试
测试场景：复杂行为案例，包含多轮追问和深度挖掘
"""

import json
import requests
import time

BASE_URL = "http://localhost:8000"
session_id = None

# 20 轮测试对话 - 模拟真实复杂案例
test_conversation = [
    "今天在幼儿园，老师让他做手工，他觉得太难了，一开始就不想做",
    "在小组桌，和其他 3 个小朋友一起",
    "剪纸工，要剪一个圆形",
    "他说不会剪，手不听使唤，把剪刀放下了",
    "老师过来帮他剪了一下，然后他就继续做了",
    "大概持续了 2 分钟左右",
    "其他小朋友在看他",
    "有点着急，但没有哭",
    "老师轻声鼓励他",
    "之后就完成了",
    "在家里也会这样",
    "遇到难的就放弃",
    "我们会帮他",
    "他喜欢画画",
    "画画时很专注",
    "不需要帮助",
    "谢谢",
    "再见",
    "好的",
    "拜拜",
]

print("=" * 80)
print("V4.0 20 轮完整对话模拟测试")
print("=" * 80)

start_time = time.time()
completed = False

for i, user_input in enumerate(test_conversation, 1):
    print(f"\n【轮次 {i}/20】")
    print(f"用户：{user_input}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v4/chat",
            json={"session_id": session_id, "user_input": user_input},
            timeout=60
        )
        data = response.json()
        
        # 保存 session_id
        session_id = data.get("session_id", session_id)
        
        # 显示响应
        state = data.get("state", "N/A")
        message = data.get("message", "")[:250]
        status = data.get("status", "N/A")
        
        print(f"状态：{state}")
        print(f"AI: {message}...")
        print(f"完成：{status}")
        
        # 如果完成，显示报告
        if status == "completed" and not completed:
            completed = True
            print("\n" + "=" * 80)
            print("✅ 对话完成！分析报告：")
            print("=" * 80)
            report_data = data.get("data", {})
            print(f"情境：{report_data.get('context', 'N/A')[:150]}")
            print(f"行为：{report_data.get('child_behavior', 'N/A')[:150]}")
            print(f"回应：{report_data.get('others_response', 'N/A')[:150]}")
            print(f"核心洞察：{report_data.get('core_insight', 'N/A')[:150]}")
            print(f"专家拆解：{json.dumps(report_data.get('expert_breakdown', {}), ensure_ascii=False)[:200]}")
            
            # 继续测试后续轮次（应该保持完成状态）
            print("\n" + "=" * 80)
            print("继续测试后续轮次（应保持完成状态）...")
            print("=" * 80)
            
    except Exception as e:
        print(f"❌ 错误：{e}")
        break

end_time = time.time()
total_time = end_time - start_time

print("\n" + "=" * 80)
print(f"测试完成！")
print(f"总会话 ID: {session_id}")
print(f"总轮数：{len(test_conversation)}")
print(f"总耗时：{total_time:.2f}秒")
print(f"平均耗时：{total_time/len(test_conversation):.2f}秒/轮")
print(f"完成轮次：{i}")
print("=" * 80)

# 获取最终会话状态
try:
    status_response = requests.get(f"{BASE_URL}/api/v4/session/{session_id}", timeout=10)
    session_status = status_response.json()
    print("\n最终会话状态：")
    print(json.dumps(session_status, ensure_ascii=False, indent=2))
except Exception as e:
    print(f"无法获取会话状态：{e}")
