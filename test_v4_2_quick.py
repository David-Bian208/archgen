#!/usr/bin/env python3
"""
V4.2 快速验证测试 - 验证报告结构修复
"""

import requests
import json

BASE_URL = "http://localhost:8000/api/v4"

# 快速测试对话
conversation = [
    "孩子做操时有时会发呆",
    "在教室里，其他小朋友认真做",
    "眼神迷茫，不看老师就做不好",
    "是的，需要老师提醒才继续",
    "老师会走到他身边提醒",
    "没有了",
]

session_id = None

print("=" * 80)
print("V4.2 快速验证测试")
print("=" * 80)
print()

for i, user_input in enumerate(conversation, 1):
    print(f"【第{i}轮】用户：{user_input}")
    
    response = requests.post(
        f"{BASE_URL}/chat",
        json={"session_id": session_id, "user_input": user_input},
        timeout=30
    )
    
    data = response.json()
    session_id = data.get("session_id")
    status = data.get("status")
    message = data.get("message", "")
    state = data.get("state", "N/A")
    
    print(f"AI: {message[:100]}...")
    print(f"状态：{state}, 状态：{status}")
    print()
    
    if status == "completed":
        print("=" * 80)
        print("✅ 对话完成，检查报告结构")
        print("=" * 80)
        
        report_data = data.get("data", {})
        report = report_data.get("report", {})
        
        print(f"\n📊 报告字段检查:")
        print(f"  - summary: {'✅' if report.get('summary') else '❌'}")
        print(f"  - clinical_differential: {'✅' if report.get('clinical_differential') else '❌'}")
        print(f"  - primary_hypothesis: {'✅' if report.get('primary_hypothesis') else '❌'}")
        print(f"  - supporting_evidence: {'✅' if report.get('supporting_evidence') else '❌'}")
        print(f"  - core_capability_goal: {'✅' if report.get('core_capability_goal') else '❌'}")
        print(f"  - parent_insight: {'✅' if report.get('parent_insight') else '❌'}")
        
        intervention_plan = report_data.get("intervention_plan", {})
        four_step = intervention_plan.get("four_step_plan", {}) if intervention_plan else {}
        
        print(f"\n📊 干预计划四步结构:")
        print(f"  - core_idea: {'✅' if four_step.get('core_idea') else '❌'}")
        print(f"  - our_plan: {'✅' if four_step.get('our_plan') else '❌'}")
        print(f"  - success_picture: {'✅' if four_step.get('success_picture') else '❌'}")
        print(f"  - first_step: {'✅' if four_step.get('first_step') else '❌'}")
        
        # 显示摘要内容
        if report.get("summary"):
            print(f"\n📝 摘要内容:")
            print(f"  {report['summary'][:200]}...")
        
        break

print()
print("=" * 80)
print("测试完成")
print("=" * 80)
