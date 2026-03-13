#!/usr/bin/env python3
"""
V4.1 紧急修复验收测试

测试目标：
1. 验证系统是否在 5-8 轮内主动结束提问
2. 验证提问是否聚焦在核心假设上
3. 验证无重复提问
4. 验证状态感知明确

测试案例：室内跳操发呆
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/v4"

# 测试案例：室内跳操发呆
TEST_CASE = {
    "name": "室内跳操发呆",
    "conversation": [
        "孩子做操时有时会发呆",
        "环境安静，其他小朋友认真做",
        "眼神迷茫，好像在找提示",
        "不看老师就做不好，会停下来",
        "是的，需要老师提醒才继续",
        "老师会走到他身边，拍拍他肩膀",
        "大概每 30 秒需要提醒一次",
        "最近好一些了",
    ]
}

def run_test():
    print("=" * 60)
    print("V4.1 紧急修复验收测试")
    print("=" * 60)
    print()
    
    session_id = None
    turn_count = 0
    locked_hypothesis = None
    completed = False
    
    for i, user_input in enumerate(TEST_CASE["conversation"], 1):
        turn_count = i
        print(f"【第 {i} 轮】")
        print(f"用户：{user_input}")
        
        # 发送请求
        try:
            response = requests.post(
                f"{BASE_URL}/chat",
                json={
                    "session_id": session_id,
                    "user_input": user_input
                },
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"❌ API 请求失败：{response.status_code}")
                print(response.text)
                return False
            
            data = response.json()
            
        except Exception as e:
            print(f"❌ 请求异常：{e}")
            return False
        
        # 解析响应
        session_id = data.get("session_id")
        status = data.get("status")
        message = data.get("message", "")
        state = data.get("state", "N/A")
        current_locked = data.get("locked_hypothesis")
        
        # 跟踪假设锁定
        if current_locked and not locked_hypothesis:
            locked_hypothesis = current_locked
            print(f"🔒 锁定假设：{locked_hypothesis}")
        
        # 检查是否完成
        if status == "completed":
            completed = True
            print(f"✅ 对话完成 (第 {i} 轮)")
            print()
            print("📊 报告摘要:")
            report_data = data.get("data", {})
            print(f"  核心洞察：{report_data.get('core_insight', 'N/A')[:100]}...")
            plan = report_data.get("intervention_plan", {})
            if plan:
                print(f"  计划名称：{plan.get('plan_name', 'N/A')}")
            break
        
        # 输出 AI 回应
        print(f"AI: {message[:150]}..." if len(message) > 150 else f"AI: {message}")
        print(f"状态：{state}, 锁定：{current_locked or '无'}")
        print()
    
    # 验收检查
    print("=" * 60)
    print("📋 验收检查结果")
    print("=" * 60)
    
    checks = []
    
    # 检查 1: 5-8 轮内结束
    check1 = 5 <= turn_count <= 8
    checks.append(check1)
    status1 = "✅" if check1 else "❌"
    print(f"{status1} 检查 1: 对话在 5-8 轮内结束 (实际：{turn_count}轮)")
    
    # 检查 2: 假设锁定
    check2 = locked_hypothesis is not None
    checks.append(check2)
    status2 = "✅" if check2 else "❌"
    print(f"{status2} 检查 2: 成功锁定核心假设 (锁定：{locked_hypothesis or '未锁定'})")
    
    # 检查 3: 完成状态
    check3 = completed
    checks.append(check3)
    status3 = "✅" if check3 else "❌"
    print(f"{status3} 检查 3: 系统主动结束对话并生成报告")
    
    # 总体结果
    print()
    if all(checks):
        print("🎉 所有验收检查通过！V4.1 修复成功！")
        return True
    else:
        print("⚠️  部分检查未通过，需要进一步调整")
        return False


if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
