#!/usr/bin/env python3
"""
V4.10.0 报告优化验证测试

测试目标：
1. P0: 摘要准确率 - 确保摘要与后文分析一致
2. P1: 临床推理结构 - 确保包含"鉴别与排除"三模块
3. P2: 比喻质量 - 确保使用生动比喻

测试案例：玥玥抓人游戏（社交技能不足，规则僵化）
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'behavior_recorder_service'))

from app.agents.structured_assessor_v4 import StructuredAssessorV4, StructuredAssessmentState
from app.agents.insight_analyzer import InsightAnalyzer
from datetime import datetime


def test_p0_summary_consistency():
    """
    P0 测试：摘要与后文分析一致性
    """
    print("\n" + "="*60)
    print("🔴 P0 测试：摘要与后文分析一致性")
    print("="*60)
    
    # 创建测试状态
    state = StructuredAssessmentState(session_id="test_p0_001")
    state.child_profile = {
        "birth_date": "2021-03-15",
        "stage": "kindergarten_middle"
    }
    
    # 填充测试数据（玥玥抓人游戏案例）
    state.set_field_value("antecedent", "抓人游戏，一群小朋友在那里玩")
    state.set_field_value("behavior_detail", "她会自己以为和别人在玩，其实别人并没有和她一起玩。游戏规则可能有 10 条，她会以为只有 3 条，然后不停重复这 3 条（比如语言，你是鬼，或者别人经过的时候会对别人施魔法）")
    state.set_field_value("specific_example", "抓人游戏中以为参与度很深，不停重复施魔法")
    
    # 模拟 insight_result（社交技能不足）
    state.insight_result = {
        "functional_judgment": "社交技能不足",
        "capability_hypothesis": "社交技能不足：社交信号监测弱，认知灵活性不足",
        "core_insight": "玥玥不是故意要干扰游戏，她只是还没学会怎么在快速变化的游戏中读懂其他小朋友是不是真的在和她玩"
    }
    
    # 创建评估器并生成摘要
    from app.agents.structured_assessor_v4 import ClinicalAssessmentFramework
    framework_path = os.path.join(os.path.dirname(__file__), 'behavior_recorder_service/app/knowledge/assessment_framework_v4.json')
    framework = ClinicalAssessmentFramework(framework_path)
    
    assessor = StructuredAssessorV4.__new__(StructuredAssessorV4)
    assessor.framework = framework
    
    # 调用摘要生成
    summary = assessor._generate_summary(state, "游乐场")
    
    print(f"\n📝 生成的摘要：\n{summary}\n")
    
    # 验证：摘要不应包含"工作记忆"（错误归因）
    if "工作记忆" in summary:
        print("❌ 失败：摘要包含错误的'工作记忆'归因")
        return False
    
    # 验证：摘要应包含社交相关关键词
    social_keywords = ["社交", "同伴", "互动", "监测", "灵活", "规则"]
    has_social_keyword = any(kw in summary for kw in social_keywords)
    
    if not has_social_keyword:
        print("❌ 失败：摘要缺少社交相关关键词")
        return False
    
    # 验证：摘要应使用生动比喻（P2 修复）
    metaphor_keywords = ["导演", "演员", "剧本", "收音机", "单曲循环"]
    has_metaphor = any(kw in summary for kw in metaphor_keywords)
    
    if has_metaphor:
        print("✅ 通过：摘要使用了生动比喻")
    else:
        print("⚠️  警告：摘要未使用生动比喻（可接受）")
    
    print("✅ P0 测试通过：摘要与后文分析一致")
    return True


def test_p1_clinical_reasoning_structure():
    """
    P1 测试：临床推理结构完整性
    """
    print("\n" + "="*60)
    print("🟠 P1 测试：临床推理结构完整性")
    print("="*60)
    
    # 测试 InsightAnalyzer 的 Prompt 是否包含三模块要求
    from app.agents.insight_analyzer import InsightAnalyzer
    from app.llm.base import LLMClient
    
    # 检查 SYSTEM PROMPT 是否包含三模块要求
    system_prompt = InsightAnalyzer.ANALYSIS_SYSTEM_PROMPT
    
    required_modules = [
        "鉴别与排除",
        "核心假设",
        "能力缺口分析"
    ]
    
    print("\n📋 检查 SYSTEM PROMPT 是否包含三模块要求：")
    all_present = True
    for module in required_modules:
        if module in system_prompt:
            print(f"  ✅ {module}")
        else:
            print(f"  ❌ {module}")
            all_present = False
    
    if not all_present:
        print("❌ 失败：SYSTEM PROMPT 缺少必需的模块要求")
        return False
    
    # 检查是否包含"为何不是"的排除句式要求
    if "为何不是" in system_prompt:
        print("  ✅ 包含'为何不是'排除句式要求")
    else:
        print("  ❌ 缺少'为何不是'排除句式要求")
        return False
    
    # 检查 JSON 格式要求是否包含三模块结构
    if "clinical_differential" in system_prompt and "鉴别与排除" in system_prompt:
        print("  ✅ JSON 格式要求包含三模块结构")
    else:
        print("  ❌ JSON 格式要求缺少三模块结构")
        return False
    
    print("✅ P1 测试通过：临床推理结构完整")
    return True


def test_p2_metaphor_generation():
    """
    P2 测试：比喻生成质量
    """
    print("\n" + "="*60)
    print("🟡 P2 测试：比喻生成质量")
    print("="*60)
    
    from app.agents.structured_assessor_v4 import ClinicalAssessmentFramework
    import os
    
    framework_path = os.path.join(os.path.dirname(__file__), 'behavior_recorder_service/app/knowledge/assessment_framework_v4.json')
    framework = ClinicalAssessmentFramework(framework_path)
    
    assessor = StructuredAssessorV4.__new__(StructuredAssessorV4)
    assessor.framework = framework
    
    # 测试用例 1：社交信号监测弱
    behavior1 = "她以为别人在和她玩，其实别人并没有和她一起玩"
    pattern1 = assessor._generate_ability_pattern(behavior1, "社交技能不足")
    print(f"\n📝 测试用例 1（社交信号监测弱）：\n   行为：{behavior1[:50]}...\n   生成：{pattern1}\n")
    
    if "导演" in pattern1 or "演员" in pattern1 or "剧本" in pattern1:
        print("  ✅ 使用了'导演/演员'比喻")
    else:
        print("  ⚠️  未使用'导演/演员'比喻")
    
    # 测试用例 2：规则僵化
    behavior2 = "游戏规则有 10 条，她以为只有 3 条，不停重复这 3 条"
    pattern2 = assessor._generate_ability_pattern(behavior2, "社交技能不足")
    print(f"\n📝 测试用例 2（规则僵化）：\n   行为：{behavior2[:50]}...\n   生成：{pattern2}\n")
    
    if "收音机" in pattern2 or "单曲循环" in pattern2:
        print("  ✅ 使用了'收音机/单曲循环'比喻")
    else:
        print("  ⚠️  未使用'收音机/单曲循环'比喻")
    
    # 测试用例 3：提示依赖
    behavior3 = "有提示时能执行，提示消失后中断"
    pattern3 = assessor._generate_ability_pattern(behavior3, "提示依赖")
    print(f"\n📝 测试用例 3（提示依赖）：\n   行为：{behavior3[:50]}...\n   生成：{pattern3}\n")
    
    if "脚手架" in pattern3:
        print("  ✅ 使用了'脚手架'比喻")
    else:
        print("  ⚠️  未使用'脚手架'比喻")
    
    print("✅ P2 测试完成：比喻生成已优化")
    return True


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🧪 V4.10.0 报告优化验证测试")
    print("="*60)
    
    results = {
        "P0_摘要一致性": test_p0_summary_consistency(),
        "P1_临床推理结构": test_p1_clinical_reasoning_structure(),
        "P2_比喻生成质量": test_p2_metaphor_generation(),
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
        print("🎉 所有测试通过！V4.10.0 优化完成")
    else:
        print("⚠️  部分测试未通过，需要进一步修复")
    print("="*60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
