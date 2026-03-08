#!/usr/bin/env python3
"""
V4.0 架构修复验证测试

测试两个经典案例，验证：
1. 引导提问明显不同，且与已描述情境紧密相关
2. 核心能力建设目标表述不同，精准反映各自主要挑战
3. 干预计划在策略、目标和具体行动上均有显著差异
"""

import json
from app.llm.openai_client import OpenAIClient
from app.config import get_config
from app.agents.guided_recorder_agent_v3_v4 import GuidedRecorderAgentV4
from app.agents.intervention_planner_v4 import InterventionPlannerV4

def test_case_1():
    """测试案例 1：做操发呆"""
    print("\n" + "="*60)
    print("测试案例 1: 做操发呆")
    print("="*60)
    
    config = get_config()
    llm_client = OpenAIClient(
        api_key=config.llm_api_key,
        base_url=config.llm_base_url,
        model=config.llm_model,
    )
    
    agent = GuidedRecorderAgentV4(llm_client)
    
    # 首轮输入
    response1 = agent.process_input(None, "孩子做操时有时会发呆，不看老师。")
    print("\n📝 首轮回应:")
    print(response1['message'])
    
    # 检查追问是否包含"做操"情境
    if "做操" in response1['message'] or "体操" in response1['message']:
        print("✅ 追问包含具体情境（做操）")
    else:
        print("❌ 追问未包含具体情境")
    
    # 第二轮：回答环境问题
    response2 = agent.process_input(response1['session_id'], "环境有点吵闹，其他小朋友都在认真做。")
    print("\n📝 第二轮回应:")
    print(response2['message'])
    
    # 检查追问是否针对"发呆"进行功能鉴别
    if "眼神" in response2['message'] or "迷茫" in response2['message'] or "放空" in response2['message']:
        print("✅ 追问针对发呆进行功能鉴别（眼神状态）")
    else:
        print("❌ 追问未针对功能鉴别")
    
    # 第三轮：完成对话
    response3 = agent.process_input(response2['session_id'], "眼神看起来有点迷茫，好像在找提示。")
    
    if response3['status'] == 'completed':
        print("\n✅ 对话完成")
        data = response3.get('data', {})
        
        # 检查核心能力建设目标
        report = data.get('report', {})
        expert_breakdown = data.get('expert_breakdown', {})
        
        print("\n📊 核心能力建设目标:")
        print(report.get('expert_view', 'N/A')[:200])
        
        # 检查干预计划
        plan = data.get('intervention_plan', {})
        if plan:
            print("\n📋 干预计划:")
            print(f"  计划名称：{plan.get('phase_name', 'N/A')}")
            
            four_step = plan.get('four_step_plan', {})
            print(f"  核心思路：{four_step.get('core_idea', 'N/A')[:100]}...")
            print(f"  成功的画面：{four_step.get('success_picture', 'N/A')[:100]}...")
            print(f"  第一步行动：{four_step.get('first_step', 'N/A')[:100]}...")
            
            # 验证个性化
            if "做操" in plan.get('phase_name', '') or "做操" in four_step.get('first_step', ''):
                print("\n✅ 计划包含具体活动（做操）")
            else:
                print("\n❌ 计划未包含具体活动")
        else:
            print("\n❌ 未生成干预计划")
    else:
        print("\n❌ 对话未完成")
    
    return response3

def test_case_2():
    """测试案例 2：学习抗拒"""
    print("\n" + "="*60)
    print("测试案例 2: 学习抗拒")
    print("="*60)
    
    config = get_config()
    llm_client = OpenAIClient(
        api_key=config.llm_api_key,
        base_url=config.llm_base_url,
        model=config.llm_model,
    )
    
    agent = GuidedRecorderAgentV4(llm_client)
    
    # 首轮输入
    response1 = agent.process_input(None, "孩子学习时总是抗拒，说不要不要。")
    print("\n📝 首轮回应:")
    print(response1['message'])
    
    # 检查追问是否包含"学习"情境
    if "学习" in response1['message'] or "任务" in response1['message']:
        print("✅ 追问包含具体情境（学习）")
    else:
        print("❌ 追问未包含具体情境")
    
    # 第二轮：回答难度问题
    response2 = agent.process_input(response1['session_id'], "任务有点难，他不会做就开始抗拒。")
    print("\n📝 第二轮回应:")
    print(response2['message'])
    
    # 检查追问是否针对功能鉴别
    if "难度" in response2['message'] or "观察" in response2['message'] or "反应" in response2['message']:
        print("✅ 追问针对功能鉴别（难度/关注）")
    else:
        print("❌ 追问未针对功能鉴别")
    
    # 第三轮：完成对话
    response3 = agent.process_input(response2['session_id'], "他抗拒时会看我的反应，如果我批评他就不做了。")
    
    if response3['status'] == 'completed':
        print("\n✅ 对话完成")
        data = response3.get('data', {})
        
        # 检查核心能力建设目标
        report = data.get('report', {})
        
        print("\n📊 核心能力建设目标:")
        print(report.get('expert_view', 'N/A')[:200])
        
        # 检查干预计划
        plan = data.get('intervention_plan', {})
        if plan:
            print("\n📋 干预计划:")
            print(f"  计划名称：{plan.get('phase_name', 'N/A')}")
            
            four_step = plan.get('four_step_plan', {})
            print(f"  核心思路：{four_step.get('core_idea', 'N/A')[:100]}...")
            print(f"  成功的画面：{four_step.get('success_picture', 'N/A')[:100]}...")
            print(f"  第一步行动：{four_step.get('first_step', 'N/A')[:100]}...")
            
            # 验证个性化
            if "学习" in plan.get('phase_name', '') or "学习" in four_step.get('first_step', ''):
                print("\n✅ 计划包含具体活动（学习）")
            else:
                print("\n❌ 计划未包含具体活动")
        else:
            print("\n❌ 未生成干预计划")
    else:
        print("\n❌ 对话未完成")
    
    return response3

def compare_results(case1, case2):
    """比较两个案例的差异"""
    print("\n" + "="*60)
    print("对比分析")
    print("="*60)
    
    # 比较引导提问
    print("\n1️⃣ 引导提问对比:")
    print(f"   案例 1 首轮：{case1['message'][:100]}...")
    print(f"   案例 2 首轮：{case2['message'][:100]}...")
    
    if "做操" in case1['message'] and "学习" in case2['message']:
        print("   ✅ 两个案例的追问明显不同，与情境相关")
    else:
        print("   ❌ 追问差异化不足")
    
    # 比较干预计划
    plan1 = case1.get('data', {}).get('intervention_plan', {})
    plan2 = case2.get('data', {}).get('intervention_plan', {})
    
    print("\n2️⃣ 干预计划对比:")
    print(f"   案例 1 计划名称：{plan1.get('phase_name', 'N/A')}")
    print(f"   案例 2 计划名称：{plan2.get('phase_name', 'N/A')}")
    
    if plan1.get('phase_name') != plan2.get('phase_name'):
        print("   ✅ 计划名称不同")
    else:
        print("   ❌ 计划名称相同")
    
    four_step1 = plan1.get('four_step_plan', {})
    four_step2 = plan2.get('four_step_plan', {})
    
    print(f"\n   案例 1 核心思路：{four_step1.get('core_idea', 'N/A')[:80]}...")
    print(f"   案例 2 核心思路：{four_step2.get('core_idea', 'N/A')[:80]}...")
    
    if four_step1.get('core_idea') != four_step2.get('core_idea'):
        print("   ✅ 核心思路不同")
    else:
        print("   ❌ 核心思路相同")
    
    print(f"\n   案例 1 第一步：{four_step1.get('first_step', 'N/A')[:80]}...")
    print(f"   案例 2 第一步：{four_step2.get('first_step', 'N/A')[:80]}...")
    
    if four_step1.get('first_step') != four_step2.get('first_step'):
        print("   ✅ 第一步行动不同")
    else:
        print("   ❌ 第一步行动相同")

if __name__ == "__main__":
    print("🧪 V4.0 架构修复验证测试")
    print("="*60)
    
    case1_result = test_case_1()
    case2_result = test_case_2()
    
    compare_results(case1_result, case2_result)
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
