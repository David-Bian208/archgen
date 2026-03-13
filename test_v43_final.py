#!/usr/bin/env python3
"""
V4.3 最终验收测试 - 两个核心案例

测试案例 A：跳操 - 提示依赖
测试案例 B：学习 - 逃避难度
"""

import requests
import json

BASE_URL = "http://localhost:8000/api/v4/chat"

def run_test_case(name, conversation, expected_env, expected_hypothesis_keywords):
    """运行单个测试案例"""
    print("=" * 80)
    print(f"【{name}】")
    print("=" * 80)
    print()
    
    session_id = None
    messages = []
    
    for i, user_input in enumerate(conversation, 1):
        print(f"【第{i}轮】用户：{user_input}")
        
        resp = requests.post(
            BASE_URL,
            json={"session_id": session_id, "user_input": user_input},
            timeout=30
        )
        
        data = resp.json()
        session_id = data.get("session_id")
        message = data.get("message", "")
        status = data.get("status")
        progress = data.get("progress", {})
        
        messages.append({"role": "user", "content": user_input})
        messages.append({"role": "ai", "content": message})
        
        print(f"AI: {message[:100]}...")
        print(f"状态：{status}, 环境推断：{progress.get('inferred_environment', 'N/A')}, 轮数：{progress.get('total_turns', 'N/A')}")
        print()
        
        if status == "completed":
            print("=" * 80)
            print("✅ 对话完成，验证结果")
            print("=" * 80)
            
            report_data = data.get("data", {})
            report = report_data.get("report", {})
            intervention_plan = report_data.get("intervention_plan", {})
            
            # 验证点 1：环境推断
            inferred_env = progress.get("inferred_environment", "N/A")
            env_pass = inferred_env == expected_env
            print(f"\n1. 环境推断：{inferred_env}")
            print(f"   期望：{expected_env} → {'✅ 通过' if env_pass else '❌ 失败'}")
            
            # 验证点 2：功能判断
            functional_judgment = report.get("functional_judgment", "")
            hypothesis_pass = any(kw in functional_judgment for kw in expected_hypothesis_keywords)
            print(f"\n2. 功能判断：{functional_judgment[:80]}...")
            print(f"   期望包含：{expected_hypothesis_keywords} → {'✅ 通过' if hypothesis_pass else '❌ 失败'}")
            
            # 验证点 3：干预计划（根据假设类型检查不同关键词）
            phase_name = intervention_plan.get("phase_name", "") if intervention_plan else ""
            four_step = intervention_plan.get("four_step_plan", {}) if intervention_plan else {}
            core_idea = four_step.get("core_idea", "") if four_step else ""
            
            # 根据功能判断选择期望的关键词
            if "逃避" in functional_judgment or "难度" in functional_judgment:
                # 逃避难度：期望"分解"、"降低"、"起点"、"匹配"、"成功"
                plan_keywords = ["分解", "降低", "起点", "匹配", "成功", "难度", "微步骤", "简单"]
            else:
                # 提示依赖：期望"锚点"、"暗号"、"内化"、"提示"、"外部"、"内部"、"充电宝"
                plan_keywords = ["锚点", "暗号", "内化", "提示", "建立", "外部", "内部", "充电宝"]
            
            plan_pass = any(kw in phase_name or kw in core_idea for kw in plan_keywords)
            print(f"\n3. 干预计划：{phase_name}")
            print(f"   核心思路：{core_idea[:80]}...")
            print(f"   期望包含策略关键词 {plan_keywords} → {'✅ 通过' if plan_pass else '❌ 失败'}")
            
            # 验证点 4：轮数
            total_turns = progress.get("total_turns", 99)
            turns_pass = total_turns <= 5
            print(f"\n4. 对话轮数：{total_turns}")
            print(f"   期望：≤5 轮 → {'✅ 通过' if turns_pass else '❌ 失败'}")
            
            # 输出完整报告
            print("\n" + "=" * 80)
            print("📄 完整报告摘要")
            print("=" * 80)
            print(f"摘要：{report.get('summary', 'N/A')[:200]}...")
            print(f"核心洞察：{report.get('core_insight', 'N/A')[:150]}...")
            print(f"临床鉴别：{report.get('clinical_differential', 'N/A')[:150]}...")
            
            # 返回测试结果
            all_pass = env_pass and hypothesis_pass and plan_pass and turns_pass
            return {
                "name": name,
                "passed": all_pass,
                "messages": messages,
                "report": report,
                "intervention_plan": intervention_plan,
                "progress": progress,
            }
    
    return None

# 测试案例 A：跳操 - 提示依赖
test_a = run_test_case(
    "测试案例 A：跳操 - 提示依赖",
    [
        "孩子 5 岁，今天在幼儿园室内跳操时，看老师就会做，不看老师就容易发呆。",
        "环境安静，其他小朋友认真做",
        "老师会走到他身边提醒",
        "没有了",
    ],
    expected_env="幼儿园",
    expected_hypothesis_keywords=["提示依赖", "逃避"]
)

print("\n\n")

# 测试案例 B：学习 - 逃避难度
test_b = run_test_case(
    "测试案例 B：学习 - 逃避难度",
    [
        "孩子 7 岁，晚上在家做数学作业时，一直说太难了，哭闹着不肯做。",
        "是应用题，他不会做",
        "我让他冷静一下，然后陪他一起看题目",
        "没有了",
    ],
    expected_env="家庭",
    expected_hypothesis_keywords=["逃避", "难度", "太难"]
)

# 总结
print("\n" + "=" * 80)
print("📊 验收总结")
print("=" * 80)
print(f"案例 A（跳操 - 提示依赖）：{'✅ 通过' if test_a and test_a['passed'] else '❌ 失败'}")
print(f"案例 B（学习 - 逃避难度）：{'✅ 通过' if test_b and test_b['passed'] else '❌ 失败'}")
print()

if test_a and test_b and test_a['passed'] and test_b['passed']:
    print("🎉 所有验收测试通过！V4.3 稳定版交付成功！")
else:
    print("⚠️  部分测试未通过，需要进一步修复")
