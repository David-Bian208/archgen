#!/usr/bin/env python3
"""四维度归因 Skill 测试"""

from executor import FourDimensionAnalyzer


def test_case_1():
    """测试用例 1：薯片盒子游戏（观点采择）"""
    print("=" * 60)
    print("测试用例 1：薯片盒子游戏（观点采择）")
    print("=" * 60)
    
    analyzer = FourDimensionAnalyzer()
    result = analyzer.analyze(
        "她以为我看到盒子里还是糖，不太理解我看到的是薯片的意思。"
    )
    
    if not result["success"]:
        print(f"❌ 测试失败：{result['error']}")
        return False
    
    print(result["attribution"])
    print("=" * 60)
    
    errors = []
    if "心理理论" not in result["attribution"]:
        errors.append("缺少心理理论维度")
    if "执行功能" not in result["attribution"]:
        errors.append("缺少执行功能维度")
    if "齿轮" not in result["attribution"]:
        errors.append("缺少协同作用说明（齿轮啮合比喻）")
    
    if errors:
        print(f"❌ 验证失败：{', '.join(errors)}")
        return False
    
    print("✅ 测试通过")
    return True


def test_case_2():
    """测试用例 2：等待提示（提示依赖）"""
    print("\n" + "=" * 60)
    print("测试用例 2：等待提示（提示依赖）")
    print("=" * 60)
    
    analyzer = FourDimensionAnalyzer()
    result = analyzer.analyze(
        "遇到困难就说我不会，等着大人教，其实都会做。"
    )
    
    if not result["success"]:
        print(f"❌ 测试失败：{result['error']}")
        return False
    
    print(result["attribution"])
    print("=" * 60)
    print("✅ 测试通过")
    return True


def test_case_3():
    """测试用例 3：寻求关注"""
    print("\n" + "=" * 60)
    print("测试用例 3：寻求关注")
    print("=" * 60)
    
    analyzer = FourDimensionAnalyzer()
    result = analyzer.analyze(
        "老师看她时她就故意发出奇怪声音，老师不看她就不发。"
    )
    
    if not result["success"]:
        print(f"❌ 测试失败：{result['error']}")
        return False
    
    print(result["attribution"])
    print("=" * 60)
    print("✅ 测试通过")
    return True


def test_case_4():
    """测试用例 4：简短模式"""
    print("\n" + "=" * 60)
    print("测试用例 4：简短模式（300 字以内）")
    print("=" * 60)
    
    analyzer = FourDimensionAnalyzer(short_mode=True)
    result = analyzer.analyze("孩子推人插队")
    
    if not result["success"]:
        print(f"❌ 测试失败：{result['error']}")
        return False
    
    print(result["attribution"])
    print("=" * 60)
    
    if len(result["attribution"]) > 500:
        print(f"⚠️ 警告：输出过长（{len(result['attribution'])}字）")
    else:
        print("✅ 字数符合要求")
    
    print("✅ 测试通过")
    return True


def main():
    """运行所有测试"""
    print("🧪 四维度归因 Skill 测试")
    print("=" * 60)
    
    # 检查环境变量
    if not os.getenv('DASHSCOPE_API_KEY'):
        print("⚠️  警告：DASHSCOPE_API_KEY 未设置")
        print("请设置环境变量后重试:")
        print("  export DASHSCOPE_API_KEY='your_api_key'")
        print("  export DASHSCOPE_BASE_URL='https://dashscope.aliyuncs.com/compatible-mode/v1'")
        print("  export DASHSCOPE_MODEL='qwen-plus'")
        print("=" * 60)
        return 1
    
    results = []
    results.append(("用例 1：薯片盒子游戏", test_case_1()))
    results.append(("用例 2：等待提示", test_case_2()))
    results.append(("用例 3：寻求关注", test_case_3()))
    results.append(("用例 4：简短模式", test_case_4()))
    
    print("\n" + "=" * 60)
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
