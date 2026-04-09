#!/usr/bin/env python3
"""ABC 场景提取 Skill 测试"""

import json
import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from skill import extract_abc_scene


def test_case_1():
    """测试用例 1：薯片盒子游戏"""
    text = "老师好，OK 玩薯片盒子游戏，打开盒子问她'妈妈会看到什么'，她说'糖'"
    print("=" * 60)
    print("测试用例 1：薯片盒子游戏")
    print("=" * 60)
    print(f"输入：{text}\n")
    
    result = extract_abc_scene(text)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 验证
    assert result["antecedent"] != "未明确", "前因提取失败"
    assert result["behavior"] != "未明确", "行为提取失败"
    assert "糖" in result["behavior"], "行为内容错误"
    
    print("✅ 测试通过\n")
    return True


def test_case_2():
    """测试用例 2：等待提示"""
    text = "小明 5 岁，遇到困难就说'我不会'，等着大人教"
    print("=" * 60)
    print("测试用例 2：等待提示")
    print("=" * 60)
    print(f"输入：{text}\n")
    
    result = extract_abc_scene(text)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 验证
    assert "5" in result["child_age"] and "岁" in result["child_age"], "年龄提取失败"
    assert "小明" in result["child_name"], "姓名提取失败"
    
    print("✅ 测试通过\n")
    return True


def test_case_3():
    """测试用例 3：寻求关注"""
    text = "玥玥 4 岁 3 个月，老师看她时就故意发出奇怪声音"
    print("=" * 60)
    print("测试用例 3：寻求关注")
    print("=" * 60)
    print(f"输入：{text}\n")
    
    result = extract_abc_scene(text)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 验证
    assert "4" in result["child_age"] and "岁" in result["child_age"], "年龄提取失败"
    assert "玥玥" in result["child_name"], "姓名提取失败"
    
    print("✅ 测试通过\n")
    return True


def main():
    """运行所有测试"""
    print("🧪 ABC 场景提取 Skill 测试\n")
    
    results = []
    results.append(("用例 1：薯片盒子游戏", test_case_1()))
    results.append(("用例 2：等待提示", test_case_2()))
    results.append(("用例 3：寻求关注", test_case_3()))
    
    print("=" * 60)
    print("📊 测试汇总")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print("=" * 60)
    print(f"总计：{passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过")
        return 0
    else:
        print(f"⚠️ {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit(main())
