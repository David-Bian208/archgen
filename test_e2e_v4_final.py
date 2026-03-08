#!/usr/bin/env python3
"""
V4.0 Final 端到端验收测试 - 学习抗拒案例

验收标准：
1. ✅ 引导提问与"学习"情境相关
2. ✅ 核心能力目标与"任务启动/情绪调节"相关
3. ✅ 计划名称体现"启动"或"难度"
4. ✅ 核心思路阐述如何解决"启动困难"
5. ✅ 第一步行动是"3 分钟小块"
6. ✅ 无任何乱码
"""

import requests
import time

BASE_URL = "http://localhost:8000"

def test_learning_resistance():
    """测试案例：学习抗拒"""
    print("="*60)
    print("V4.0 Final 端到端验收测试 - 学习抗拒案例")
    print("="*60)
    
    # 第一轮：初始描述
    print("\n📝 第一轮：初始描述")
    response = requests.post(f"{BASE_URL}/api/v3/chat", json={
        "session_id": None,
        "user_input": "孩子学习时总是抗拒，说不要不要"
    })
    data = response.json()
    session_id = data['session_id']
    print(f"AI: {data['message'][:150]}...")
    
    # 验证：追问包含"学习"
    if "学习" in data['message']:
        print("✅ 追问包含具体情境（学习）")
    else:
        print("❌ 追问未包含具体情境")
    
    # 第二轮：回答难度问题
    print("\n📝 第二轮：回答难度")
    response = requests.post(f"{BASE_URL}/api/v3/chat", json={
        "session_id": session_id,
        "user_input": "任务有点难，他不会做就开始抗拒，会看我的反应"
    })
    data = response.json()
    print(f"AI: {data['message'][:150]}...")
    
    # 第三轮：完成对话
    print("\n📝 第三轮：完成对话")
    response = requests.post(f"{BASE_URL}/api/v3/chat", json={
        "session_id": session_id,
        "user_input": "我会安慰他，鼓励他继续做"
    })
    data = response.json()
    
    if data.get('status') == 'completed':
        print("✅ 对话完成")
        
        report = data.get('data', {}).get('report', {})
        plan = data.get('data', {}).get('intervention_plan', {})
        
        # 验收 1: 核心能力建设目标
        print("\n📊 验收 1: 核心能力建设目标")
        expert_view = report.get('expert_view', 'N/A')
        print(f"{expert_view[:200]}...")
        if "启动" in expert_view or "任务" in expert_view or "难度" in expert_view:
            print("✅ 与任务启动/难度相关")
        else:
            print("⚠️ 可能不够具体")
        
        # 验收 2: 计划名称
        print("\n📋 验收 2: 计划名称")
        phase_name = plan.get('phase_name', 'N/A')
        print(f"计划名称：{phase_name}")
        if "启动" in phase_name or "难度" in phase_name or "学习" in phase_name:
            print("✅ 体现'启动'或'难度'或'学习'")
        else:
            print("❌ 计划名称不够具体")
        
        # 验收 3: 核心思路
        print("\n💡 验收 3: 核心思路")
        core_idea = plan.get('four_step_plan', {}).get('core_idea', 'N/A')
        print(f"{core_idea[:150]}...")
        if "启动" in core_idea or "简单" in core_idea or "微步骤" in core_idea or "小块" in core_idea:
            print("✅ 阐述如何解决启动困难")
        else:
            print("⚠️ 可能不够具体")
        
        # 验收 4: 成功画面
        print("\n🎯 验收 4: 成功画面")
        success_picture = plan.get('four_step_plan', {}).get('success_picture', 'N/A')
        print(f"{success_picture[:100]}...")
        if "启动" in success_picture or "完成" in success_picture or "开始" in success_picture:
            print("✅ 与成功启动相关")
        else:
            print("⚠️ 可能不够具体")
        
        # 验收 5: 第一步行动
        print("\n🚀 验收 5: 第一步行动")
        first_step = plan.get('four_step_plan', {}).get('first_step', 'N/A')
        print(f"{first_step[:150]}...")
        if "3 分钟" in first_step or "小块" in first_step or "小步骤" in first_step or "简单" in first_step:
            print("✅ 是'3 分钟小块'或类似表述")
        else:
            print("⚠️ 可能不够具体")
        
        # 验收 6: 无乱码
        print("\n🧹 验收 6: 无乱码")
        plan_str = str(plan)
        if '<pFig>' in plan_str or '%!(' in plan_str or '(MISSING)' in plan_str:
            print("❌ 发现乱码")
        else:
            print("✅ 无乱码")
        
        # 总结
        print("\n" + "="*60)
        print("验收总结")
        print("="*60)
        checks = [
            ("引导提问包含'学习'", "学习" in data.get('message', '')),
            ("计划名称体现核心策略", "启动" in phase_name or "难度" in phase_name or "学习" in phase_name),
            ("核心思路阐述解决方案", "启动" in core_idea or "简单" in core_idea or "微步骤" in core_idea),
            ("第一步行动具体可执行", "3 分钟" in first_step or "小块" in first_step or "简单" in first_step),
            ("无乱码污染", '<pFig>' not in plan_str and '%!(' not in plan_str),
        ]
        
        passed = sum(1 for _, result in checks if result)
        total = len(checks)
        
        for name, result in checks:
            print(f"{'✅' if result else '❌'} {name}")
        
        print(f"\n总分：{passed}/{total}")
        
        if passed >= 4:
            print("\n🎉 V4.0 Final 验收通过！")
            return True
        else:
            print("\n⚠️ V4.0 Final 验收未完全通过，需要进一步优化")
            return False
    else:
        print("❌ 对话未完成")
        return False

if __name__ == "__main__":
    success = test_learning_resistance()
    exit(0 if success else 1)
