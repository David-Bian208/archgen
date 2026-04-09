#!/usr/bin/env python3
"""行为分析 Agent 测试脚本"""

import json
import sys
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 添加 behavior-analysis 到路径
BEHAVIOR_ANALYSIS_ROOT = Path(__file__).parent
sys.path.insert(0, str(BEHAVIOR_ANALYSIS_ROOT))

from agent import BehaviorAnalysisAgent


def test_case_1():
    """测试用例 1：二级错误信念（薯片盒子游戏）"""
    print("=" * 60)
    print("测试用例 1：二级错误信念（薯片盒子游戏）")
    print("=" * 60)

    agent = BehaviorAnalysisAgent()

    abc_records = [
        {
            "antecedent": "妈妈和 OK 玩薯片盒子游戏，OK 看到妈妈把糖果换成薯片",
            "behavior": "OK 能说出盒子里是薯片，但当被问'爸爸会看到什么'时，OK 说'糖'",
            "consequence": "妈妈继续引导，但 OK 不太理解为什么爸爸会说是糖",
        }
    ]

    result = agent.analyze(abc_records)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 验证要点
    assert result.get("success") == True, "分析失败"
    assert "developmental_profile" in result, "缺少发展剖面"
    assert "attribution_statement" in result, "缺少归因陈述"

    print("\n✅ 测试用例 1 通过")
    return result


def test_case_2():
    """测试用例 2：逃避行为（任务延迟响应）"""
    print("\n" + "=" * 60)
    print("测试用例 2：逃避行为（任务延迟响应）")
    print("=" * 60)

    agent = BehaviorAnalysisAgent()

    abc_records = [
        {
            "antecedent": "妈妈让 OK 收拾玩具",
            "behavior": "OK 说'妈妈收'，然后继续玩",
            "consequence": "妈妈妥协了，帮 OK 收拾",
        }
    ]

    result = agent.analyze(abc_records)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 验证要点
    assert result.get("success") == True, "分析失败"
    assert "developmental_profile" in result, "缺少发展剖面"

    print("\n✅ 测试用例 2 通过")
    return result


def test_case_3():
    """测试用例 3：寻求关注（打断对话）"""
    print("\n" + "=" * 60)
    print("测试用例 3：寻求关注（打断对话）")
    print("=" * 60)

    agent = BehaviorAnalysisAgent()

    abc_records = [
        {
            "antecedent": "妈妈和爸爸聊天，OK 在旁边玩",
            "behavior": "OK 突然大声尖叫，打断对话",
            "consequence": "爸爸妈妈看向 OK，询问怎么了",
        }
    ]

    result = agent.analyze(abc_records)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 验证要点
    assert result.get("success") == True, "分析失败"
    assert "developmental_profile" in result, "缺少发展剖面"

    print("\n✅ 测试用例 3 通过")
    return result


def main():
    """运行所有测试"""
    print("行为分析 Agent 测试开始\n")

    try:
        test_case_1()
        test_case_2()
        test_case_3()

        print("\n" + "=" * 60)
        print("✅ 所有测试通过（3/3）")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
