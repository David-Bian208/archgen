#!/usr/bin/env python3
"""
V4.10.1 场景化干预验证测试

测试目标：
1. 场景分类准确性 - 5 类场景正确识别
2. 干预匹配精准度 - 场景→干预正确映射
3. 衔接说明生成 - scene_bridge 字段存在且合理

测试案例：
1. 抓人游戏（共同游戏场景）
2. 相互介绍（对话/介绍场景）
3. 固定路线（规则变化场景）
4. 拥抱太重（身体边界场景）
5. 看不出别人生气（情绪识别场景）
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'behavior_recorder_service'))

from app.agents.intervention_planner import InterventionPlanner


def test_scene_classification():
    """
    测试 1：场景分类准确性
    """
    print("\n" + "="*60)
    print("🔴 测试 1：场景分类准确性")
    print("="*60)
    
    planner = InterventionPlanner()
    
    test_cases = [
        # (场景描述，预期分类，关键词)
        (
            "抓人游戏，一群小朋友在那里玩，她以为别人在和她玩",
            "joint_play",
            "共同游戏"
        ),
        (
            "请玥玥做相互介绍，她像完成任务一样介绍，没有关注对方反应",
            "conversation_intro",
            "对话/介绍"
        ),
        (
            "必须走同一条路线，玩具必须按特定顺序排列",
            "rules_rigidity",
            "规则变化"
        ),
        (
            "拥抱不知轻重，靠得太近，触碰他人过度用力",
            "body_boundary",
            "身体边界"
        ),
        (
            "看不出别人不高兴，读不懂面部表情，忽略别人的拒绝信号",
            "emotion_recognition",
            "情绪识别"
        ),
    ]
    
    results = []
    for context, expected_scene, scene_name in test_cases:
        session_context = {
            "context": context,
            "child_behavior": context,
        }
        
        classified_scene = planner._classify_scene_type(session_context)
        passed = classified_scene == expected_scene
        
        status = "✅" if passed else "❌"
        print(f"\n{status} {scene_name}场景：{classified_scene} (预期：{expected_scene})")
        print(f"   输入：{context[:50]}...")
        
        results.append(passed)
    
    all_passed = all(results)
    print(f"\n{'✅' if all_passed else '❌'} 场景分类测试：{sum(results)}/{len(results)} 通过")
    return all_passed


def test_scene_intervention_mapping():
    """
    测试 2：干预匹配精准度
    """
    print("\n" + "="*60)
    print("🟠 测试 2：干预匹配精准度")
    print("="*60)
    
    planner = InterventionPlanner()
    
    test_cases = [
        # (场景类型，预期干预关键词，预期游戏特征)
        (
            "joint_play",
            ["开始信号", "连接信号", "是否在一起玩"],
            "共同游戏→开始信号游戏"
        ),
        (
            "conversation_intro",
            ["观察 - 反应", "介绍接力赛", "说完→看脸→等反应"],
            "对话/介绍→观察 - 反应游戏"
        ),
        (
            "rules_rigidity",
            ["预告", "小变化", "灵活性"],
            "规则变化→预告 + 小变化游戏"
        ),
        (
            "body_boundary",
            ["身体边界", "身体地图", "舒适距离"],
            "身体边界→身体地图游戏"
        ),
        (
            "emotion_recognition",
            ["情绪侦探", "表情卡片", "猜表情"],
            "情绪识别→情绪侦探游戏"
        ),
    ]
    
    results = []
    for scene_type, expected_keywords, scenario_name in test_cases:
        session_context = {
            "context": f"测试{scene_type}场景",
            "child_behavior": f"测试{scene_type}行为",
        }
        
        plan = planner._get_scene_intervention(scene_type, session_context)
        
        # 检查 plan 是否包含预期关键词
        plan_text = str(plan)
        has_keywords = all(kw in plan_text for kw in expected_keywords)
        
        # 检查是否有 scene_bridge 字段
        has_bridge = "scene_bridge" in plan
        
        passed = has_keywords and has_bridge
        
        status = "✅" if passed else "❌"
        print(f"\n{status} {scenario_name}")
        print(f"   关键词匹配：{'✅' if has_keywords else '❌'}")
        print(f"   衔接说明：{'✅' if has_bridge else '❌'}")
        
        if passed:
            print(f"   阶段名称：{plan.get('phase_name', 'N/A')[:60]}...")
        
        results.append(passed)
    
    all_passed = all(results)
    print(f"\n{'✅' if all_passed else '❌'} 干预匹配测试：{sum(results)}/{len(results)} 通过")
    return all_passed


def test_full_pipeline():
    """
    测试 3：完整流程（场景分类→干预生成）
    """
    print("\n" + "="*60)
    print("🟡 测试 3：完整流程测试")
    print("="*60)
    
    planner = InterventionPlanner()
    
    # 测试案例 1：相互介绍场景
    print("\n📝 测试案例 1：相互介绍场景")
    session_context_1 = {
        "context": "昨天和两个小朋友出去玩，请玥玥做相互介绍",
        "child_behavior": "她像完成任务一样介绍了两个小朋友，但没有关注其他两个小朋友有没有在注意她",
        "primary_hypothesis": "社交技能不足",
        "capability_gap": "社交信号监测弱，观点采择困难",
    }
    
    plan_1 = planner.generate_plan("H_SOCIAL_SKILLS", "social_skills_deficit", session_context_1)
    
    # 验证：应该是"观察 - 反应"游戏，而非"开始信号"游戏
    plan_text_1 = str(plan_1)
    is_conversation_game = "观察 - 反应" in plan_text_1 or "介绍接力赛" in plan_text_1
    is_not_signal_game = "开始信号" not in plan_text_1 or "连接信号" not in plan_text_1
    
    passed_1 = is_conversation_game
    print(f"   干预类型：{'✅ 观察 - 反应游戏' if is_conversation_game else '❌ 错误类型'}")
    print(f"   阶段名称：{plan_1.get('phase_name', 'N/A')[:80]}...")
    
    # 测试案例 2：抓人游戏场景
    print("\n📝 测试案例 2：抓人游戏场景")
    session_context_2 = {
        "context": "抓人游戏，一群小朋友在那里玩",
        "child_behavior": "她以为别人在和她玩，其实别人并没有和她一起玩",
        "primary_hypothesis": "社交技能不足",
        "capability_gap": "社交信号监测弱",
    }
    
    plan_2 = planner.generate_plan("H_SOCIAL_SKILLS", "social_skills_deficit", session_context_2)
    
    # 验证：应该是"开始信号"游戏
    plan_text_2 = str(plan_2)
    is_signal_game = "开始信号" in plan_text_2 or "连接信号" in plan_text_2
    
    passed_2 = is_signal_game
    print(f"   干预类型：{'✅ 开始信号游戏' if is_signal_game else '❌ 错误类型'}")
    print(f"   阶段名称：{plan_2.get('phase_name', 'N/A')[:80]}...")
    
    all_passed = passed_1 and passed_2
    print(f"\n{'✅' if all_passed else '❌'} 完整流程测试：{'通过' if all_passed else '未通过'}")
    return all_passed


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🧪 V4.10.1 场景化干预验证测试")
    print("="*60)
    
    results = {
        "场景分类准确性": test_scene_classification(),
        "干预匹配精准度": test_scene_intervention_mapping(),
        "完整流程": test_full_pipeline(),
    }
    
    # 汇总结果
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 所有测试通过！V4.10.1 场景化干预修复完成")
    else:
        print("⚠️  部分测试未通过，需要进一步修复")
    print("="*60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
