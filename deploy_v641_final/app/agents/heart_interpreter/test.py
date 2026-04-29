#!/usr/bin/env python3
"""心伴解读 Agent 测试"""

import sys
import os
from pathlib import Path

# 添加项目根目录和当前目录
PROJECT_ROOT = '/home/admin/.openclaw/workspace/behavior_recorder_service'
CURRENT_DIR = str(Path(__file__).parent)

sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, CURRENT_DIR)

try:
    from app.llm.openai_client import OpenAIClient
    from agent import HeartInterpreterAgent
except ImportError as e:
    print(f"❌ 无法导入模块：{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


def test_case_1():
    """测试用例 1：薯片盒子游戏"""
    print("=" * 60)
    print("测试用例 1：薯片盒子游戏（观点采择）")
    print("=" * 60)
    
    input_data = {
        "child_name": "OK",
        "child_age": "5 岁",
        "strengths": ["能记住盒子里实际是糖果", "能陈述自己知识"],
        "current_focus": ["心理理论发展", "观点采择能力"],
        "challenges": ["难以推断他人视角"],
        "attribution": "心理理论发展节奏的个体差异，颞顶联合区网络负荷过重。",
        "hypotheses_ranking": [
            {"id": "H1", "rank": 1, "confidence": 0.85, "description": "心理理论延迟（观点采择困难）"},
        ],
        "identified_problems": ["无法推断他人视角", "固着于初始状态"],
        "parent_concerns": ["孩子不理解换位思考"],
    }
    
    # 创建 Agent（需要 LLM 客户端）
    try:
        client = OpenAIClient(
            api_key=os.getenv("LLM_API_KEY", ""),
            base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
            model=os.getenv("LLM_MODEL", "deepseek-chat"),
        )
        agent = HeartInterpreterAgent(client)
        result = agent.interpret(input_data)
        print(result.full_text)
        print("=" * 60)
        print("✅ 测试通过")
        return True
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_case_2_fallback():
    """测试用例 2：降级处理"""
    print("=" * 60)
    print("测试用例 2：降级处理（LLM 失败）")
    print("=" * 60)
    
    input_data = {
        "child_name": "测试",
        "child_age": "未明确",
        "strengths": [],
        "current_focus": [],
        "challenges": [],
        "attribution": "",
        "hypotheses_ranking": [],
        "identified_problems": [],
        "parent_concerns": [],
    }
    
    # 模拟 LLM 失败
    class MockLLMClient:
        def generate(self, **kwargs):
            raise Exception("LLM 调用失败")
    
    agent = HeartInterpreterAgent(MockLLMClient())
    result = agent.interpret(input_data)
    print(result.full_text)
    print("=" * 60)
    print("✅ 降级处理成功")
    return True


def main():
    """运行所有测试"""
    print("🧪 心伴解读 Agent 测试\n")
    
    # 检查环境变量
    if not os.getenv("LLM_API_KEY"):
        print("⚠️ 警告：LLM_API_KEY 未设置")
        print("请设置环境变量后重试:")
        print("  export LLM_API_KEY='your_api_key'")
        print("  export LLM_BASE_URL='https://api.deepseek.com'")
        print("  export LLM_MODEL='deepseek-chat'")
        print("=" * 60)
        return 1
    
    results = []
    results.append(("用例 1：薯片盒子游戏", test_case_1()))
    results.append(("用例 2：降级处理", test_case_2_fallback()))
    
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
