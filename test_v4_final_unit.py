#!/usr/bin/env python3
"""
V4.0 Final 单元测试 - 直接测试干预计划生成器

绕过对话流程，直接测试核心修复：
1. 根据 primary_hypothesis 选择正确的策略骨架
2. 文本净化功能
3. 个性化计划生成
"""

from app.agents.intervention_planner_v4_fixed import InterventionPlannerV4Fixed

def test_escape_avoidance_plan():
    """测试逃避困难任务计划"""
    print("="*60)
    print("测试 1: 逃避困难任务计划")
    print("="*60)
    
    planner = InterventionPlannerV4Fixed()
    
    session_context = {
        "primary_hypothesis": "逃避困难任务",
        "capability_gap": "任务启动困难",
        "context": "学习时总是抗拒",
        "child_behavior": "说不要不要",
    }
    
    plan = planner.generate_plan("H1", "task_refusal", session_context)
    
    if not plan:
        print("❌ 计划生成失败")
        return False
    
    # 验收检查
    checks = []
    
    # 1. 计划名称
    phase_name = plan.get('phase_name', '')
    print(f"\n计划名称：{phase_name}")
    checks.append(("计划名称体现'启动'或'难度'", 
                   "启动" in phase_name or "难度" in phase_name or "学习" in phase_name))
    
    # 2. 核心思路
    core_idea = plan.get('four_step_plan', {}).get('core_idea', '')
    print(f"核心思路：{core_idea[:100]}...")
    checks.append(("核心思路阐述启动困难解决", 
                   "启动" in core_idea or "简单" in core_idea or "微步骤" in core_idea or "小块" in core_idea))
    
    # 3. 成功画面
    success_picture = plan.get('four_step_plan', {}).get('success_picture', '')
    print(f"成功画面：{success_picture[:80]}...")
    checks.append(("成功画面与启动/完成相关", 
                   "启动" in success_picture or "完成" in success_picture or "开始" in success_picture))
    
    # 4. 第一步行动
    first_step = plan.get('four_step_plan', {}).get('first_step', '')
    print(f"第一步行动：{first_step[:100]}...")
    checks.append(("第一步行动是 3 分钟小块", 
                   "3 分钟" in first_step or "小块" in first_step or "小步骤" in first_step))
    
    # 5. 无乱码
    plan_str = str(plan)
    has_garbage = '<pFig>' in plan_str or '%!(' in plan_str or '(MISSING)' in plan_str
    checks.append(("无乱码污染", not has_garbage))
    
    # 6. 目标正确
    goal = plan.get('goal', '')
    print(f"目标：{goal[:80]}...")
    checks.append(("目标与降低抵触情绪相关", 
                   "抵触" in goal or "启动" in goal or "成功" in goal))
    
    # 输出结果
    print("\n" + "-"*60)
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    
    for name, result in checks:
        print(f"{'✅' if result else '❌'} {name}")
    
    print(f"\n总分：{passed}/{total}")
    
    return passed >= 5

def test_prompt_dependency_plan():
    """测试提示依赖计划"""
    print("\n" + "="*60)
    print("测试 2: 提示依赖计划（做操发呆）")
    print("="*60)
    
    planner = InterventionPlannerV4Fixed()
    
    session_context = {
        "primary_hypothesis": "提示依赖",
        "capability_gap": "工作记忆中的视觉 - 动作序列保持",
        "context": "做操时有时会发呆",
        "child_behavior": "不看老师",
    }
    
    plan = planner.generate_plan("H1", "task_disengagement", session_context)
    
    if not plan:
        print("❌ 计划生成失败")
        return False
    
    # 验收检查
    checks = []
    
    # 1. 计划名称
    phase_name = plan.get('phase_name', '')
    print(f"\n计划名称：{phase_name}")
    checks.append(("计划名称包含'做操'或'密语'", 
                   "做操" in phase_name or "密语" in phase_name or "锚点" in phase_name))
    
    # 2. 核心思路
    core_idea = plan.get('four_step_plan', {}).get('core_idea', '')
    print(f"核心思路：{core_idea[:100]}...")
    checks.append(("核心思路阐述外部转内部提示", 
                   "外部" in core_idea and "内部" in core_idea))
    
    # 3. 第一步行动
    first_step = plan.get('four_step_plan', {}).get('first_step', '')
    print(f"第一步行动：{first_step[:100]}...")
    checks.append(("第一步行动是共创暗号", 
                   "暗号" in first_step or "密语" in first_step or "动作" in first_step))
    
    # 4. 无乱码
    plan_str = str(plan)
    has_garbage = '<pFig>' in plan_str or '%!(' in plan_str or '(MISSING)' in plan_str
    checks.append(("无乱码污染", not has_garbage))
    
    # 输出结果
    print("\n" + "-"*60)
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    
    for name, result in checks:
        print(f"{'✅' if result else '❌'} {name}")
    
    print(f"\n总分：{passed}/{total}")
    
    return passed >= 3

def test_text_sanitization():
    """测试文本净化功能"""
    print("\n" + "="*60)
    print("测试 3: 文本净化功能")
    print("="*60)
    
    planner = InterventionPlannerV4Fixed()
    
    test_cases = [
        ('<pFig>测试</pFig>', '测试'),
        ('%!(string=乱码)', ''),
        ('(MISSING)', ''),
        ('&amp;', '&'),
        ('多个  空格', '多个 空格'),
        ('<div>内容</div> 正常  &lt; 符号', '内容 正常 < 符号'),
    ]
    
    checks = []
    for input_text, expected_contains in test_cases:
        result = planner._sanitize_plan_text(input_text)
        # 简单检查：不包含原始标签和调试代码
        has_tags = '<' in result and '>' in result
        has_debug = '%!(' in result or '(MISSING)' in result
        is_clean = not has_tags and not has_debug
        checks.append((f"净化 '{input_text[:30]}'", is_clean))
        print(f"输入：{repr(input_text)[:50]}")
        print(f"输出：{repr(result)}")
        print(f"{'✅' if is_clean else '❌'} 无标签和调试代码\n")
    
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    
    print(f"总分：{passed}/{total}")
    
    return passed >= 5

if __name__ == "__main__":
    print("🧪 V4.0 Final 单元测试套件\n")
    
    test1 = test_escape_avoidance_plan()
    test2 = test_prompt_dependency_plan()
    test3 = test_text_sanitization()
    
    print("\n" + "="*60)
    print("总 结")
    print("="*60)
    print(f"测试 1 (逃避计划): {'✅ 通过' if test1 else '❌ 失败'}")
    print(f"测试 2 (提示依赖): {'✅ 通过' if test2 else '❌ 失败'}")
    print(f"测试 3 (文本净化): {'✅ 通过' if test3 else '❌ 失败'}")
    
    if test1 and test2 and test3:
        print("\n🎉 V4.0 Final 所有单元测试通过！")
        exit(0)
    else:
        print("\n⚠️ 部分测试未通过")
        exit(1)
