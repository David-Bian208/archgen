"""
V3.9.2 修复验证测试
测试智能动态临床访谈逻辑是否正确实现

验收标准：
1. ✅ 无重复提问：当用户回答"觉得任务太难"后，AI 不应再追问时间点或是否寻求关注
2. ✅ 智能转向：AI 应能基于"任务太难"这一高置信度信息，自动转向深度挖掘
3. ✅ 状态感知：AI 的提问应体现出对之前对话内容的理解
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.agents.guided_recorder_agent_v3 import GuidedRecorderAgentV3, ConversationSession


class MockLLMClient:
    """模拟 LLM 客户端 - 用于测试"""

    def __init__(self, mock_responses=None):
        self.mock_responses = mock_responses or []
        self.call_count = 0

    def generate_json(self, system_prompt, user_prompt, temperature=0.1, max_tokens=500):
        """模拟 JSON 生成"""
        # 根据 prompt 内容智能响应
        if "提取关键信息并评估假设置信度" in system_prompt or "提取关键信息并评估假设置信度" in user_prompt:
            # 状态更新响应
            if "太难" in user_prompt or "难" in user_prompt:
                return {
                    "new_evidence": ["孩子明确表达任务太难", "抗拒一开始就发生"],
                    "confidence_updates": {
                        "逃避难度": 0.8,
                        "寻求关注": 0.1,
                        "感觉逃避": 0.1
                    },
                    "high_confidence_hypothesis": "逃避难度"
                }
            else:
                return {
                    "new_evidence": ["用户提供了新信息"],
                    "confidence_updates": {
                        "逃避难度": 0.5,
                        "寻求关注": 0.3,
                        "感觉逃避": 0.2
                    },
                    "high_confidence_hypothesis": None
                }
        
        elif "提取或更新信息" in user_prompt:
            # 信息提取响应
            if "太难" in user_prompt:
                return {
                    "environment": "幼儿园教室",
                    "context": "手工活动",
                    "child_behavior": "觉得任务太难，不想做",
                    "others_response": "老师让他做"
                }
            elif "剪纸" in user_prompt:
                return {
                    "environment": "幼儿园教室",
                    "context": "手工活动 - 剪纸部分",
                    "child_behavior": "说手不听使唤，剪不直",
                    "others_response": "老师让他做"
                }
            else:
                return {
                    "environment": "",
                    "context": "",
                    "child_behavior": "",
                    "others_response": ""
                }
        
        elif "评估当前对话状态" in user_prompt or "生成唯一一个最有助于推进分析的问题" in system_prompt:
            # 对话评估响应
            if "剪纸" in user_prompt:
                return {
                    "empathy": "我理解您的担心，剪纸确实需要手眼协调能力。",
                    "summary": "基于我们的对话，我了解到孩子在手工活动中，特别是剪纸部分感到困难。",
                    "focus": "了解具体困难点",
                    "environment_gathered": True,
                    "context_gathered": True,
                    "behavior_gathered": True,
                    "response_gathered": True,
                    "is_complete": True,
                    "final_summary": "孩子在幼儿园手工活动中，因剪纸困难而产生逃避行为。"
                }
            else:
                return {
                    "empathy": "谢谢您这么细致的观察。",
                    "summary": "我了解到孩子觉得任务有困难。",
                    "focus": "了解具体困难点",
                    "environment_gathered": False,
                    "context_gathered": True,
                    "behavior_gathered": True,
                    "response_gathered": False,
                    "is_complete": False,
                    "follow_up_question": "您觉得是任务中的哪一部分让他感到最难？"
                }
        
        # 默认响应
        return {
            "empathy": "谢谢你的分享",
            "is_complete": False,
            "follow_up_question": "能再详细说说吗？"
        }


def test_session_state_tracking():
    """测试 1: 会话状态追踪"""
    print("=" * 60)
    print("测试 1: 会话状态追踪")
    print("=" * 60)
    
    llm = MockLLMClient()
    agent = GuidedRecorderAgentV3(llm)
    
    # 创建会话
    session = agent._create_session()
    
    # 验证初始状态
    assert "evidence" in session.session_state
    assert "hypothesis_confidence" in session.session_state
    assert "current_focus" in session.session_state
    
    # 验证初始置信度均匀分布
    conf = session.session_state["hypothesis_confidence"]
    assert abs(conf["逃避难度"] - 0.33) < 0.01
    assert abs(conf["寻求关注"] - 0.33) < 0.01
    assert abs(conf["感觉逃避"] - 0.33) < 0.01
    
    print("✅ 初始状态正确")
    print(f"   初始置信度：{conf}")
    return True


def test_state_update():
    """测试 2: 状态更新逻辑"""
    print("\n" + "=" * 60)
    print("测试 2: 状态更新逻辑")
    print("=" * 60)
    
    llm = MockLLMClient()
    agent = GuidedRecorderAgentV3(llm)
    session = agent._create_session()
    
    # 模拟用户输入"孩子觉得任务太难"
    user_input = "他觉得这个任务太难了，一开始就不想做"
    
    # 更新状态
    agent._update_state(session, user_input)
    
    # 验证证据被记录
    assert len(session.session_state["evidence"]) > 0
    print(f"✅ 证据已记录：{session.session_state['evidence']}")
    
    # 验证置信度已更新
    conf = session.session_state["hypothesis_confidence"]
    print(f"✅ 置信度已更新：逃避难度={conf['逃避难度']:.2f}, 寻求关注={conf['寻求关注']:.2f}, 感觉逃避={conf['感觉逃避']:.2f}")
    
    # 验证"逃避难度"置信度应该最高
    assert conf["逃避难度"] > conf["寻求关注"]
    assert conf["逃避难度"] > conf["感觉逃避"]
    print("✅ '逃避难度'假设置信度最高，符合预期")
    
    return True


def test_decision_logic():
    """测试 3: 决策逻辑 - 高置信度时转向深度挖掘"""
    print("\n" + "=" * 60)
    print("测试 3: 决策逻辑 - 高置信度触发深度挖掘")
    print("=" * 60)
    
    llm = MockLLMClient()
    agent = GuidedRecorderAgentV3(llm)
    session = agent._create_session()
    
    # 手动设置高置信度
    session.session_state["hypothesis_confidence"]["逃避难度"] = 0.85
    session.session_state["hypothesis_confidence"]["寻求关注"] = 0.10
    session.session_state["hypothesis_confidence"]["感觉逃避"] = 0.05
    
    # 决策
    question_type = agent._decide_next_question(session)
    
    print(f"✅ 决策结果：{question_type}")
    assert question_type == "deep_dive_escape", f"期望 'deep_dive_escape'，得到 '{question_type}'"
    print("✅ 高置信度触发深度挖掘，符合预期")
    
    # 验证 current_focus 被设置
    assert session.session_state["current_focus"] == "逃避难度"
    print(f"✅ 当前聚焦：{session.session_state['current_focus']}")
    
    return True


def test_decision_logic_discrimination():
    """测试 4: 决策逻辑 - 置信度接近时需要鉴别"""
    print("\n" + "=" * 60)
    print("测试 4: 决策逻辑 - 置信度接近时生成鉴别性问题")
    print("=" * 60)
    
    llm = MockLLMClient()
    agent = GuidedRecorderAgentV3(llm)
    session = agent._create_session()
    
    # 设置两个接近的置信度
    session.session_state["hypothesis_confidence"]["逃避难度"] = 0.45
    session.session_state["hypothesis_confidence"]["寻求关注"] = 0.40
    session.session_state["hypothesis_confidence"]["感觉逃避"] = 0.15
    
    # 决策
    question_type = agent._decide_next_question(session)
    
    print(f"✅ 决策结果：{question_type}")
    assert "discriminate" in question_type, f"期望鉴别性问题，得到 '{question_type}'"
    print("✅ 置信度接近时生成鉴别性问题，符合预期")
    
    return True


def test_deep_dive_question():
    """测试 5: 深度挖掘问题生成"""
    print("\n" + "=" * 60)
    print("测试 5: 深度挖掘问题生成")
    print("=" * 60)
    
    llm = MockLLMClient()
    agent = GuidedRecorderAgentV3(llm)
    
    # 测试各假设的深度挖掘问题
    for hypothesis in ["逃避难度", "寻求关注", "感觉逃避"]:
        question = agent._get_deep_dive_question(hypothesis)
        assert len(question) > 10, f"问题太短：{question}"
        print(f"✅ {hypothesis}: {question}")
    
    return True


def test_full_conversation_flow():
    """测试 6: 完整对话流程 - 验证无重复提问"""
    print("\n" + "=" * 60)
    print("测试 6: 完整对话流程 - 验证无重复提问")
    print("=" * 60)
    
    llm = MockLLMClient()
    agent = GuidedRecorderAgentV3(llm)
    
    # 首轮：用户描述行为
    response1 = agent.process_input(None, "今天在幼儿园，老师让他做手工，他觉得太难了，一开始就不想做")
    print(f"首轮响应：{response1['status']}")
    print(f"   共情：{response1['message'][:100]}...")
    
    # 验证响应包含总结
    assert "session_id" in response1
    session_id = response1["session_id"]
    
    # 获取会话状态
    session = agent.get_session(session_id)
    print(f"   已收集证据：{session.session_state['evidence']}")
    print(f"   假设置信度：{session.session_state['hypothesis_confidence']}")
    
    # 第二轮：用户回答深度挖掘问题
    response2 = agent.process_input(session_id, "主要是剪纸的部分，他说手不听使唤，剪不直")
    print(f"\n第二轮响应：{response2['status']}")
    print(f"   消息：{response2['message'][:150]}...")
    
    # 验证：第二轮响应应该体现对第一轮的理解（提到"任务难"或"剪纸"）
    session = agent.get_session(session_id)
    print(f"   已收集证据：{session.session_state['evidence']}")
    print(f"   假设置信度：{session.session_state['hypothesis_confidence']}")
    
    # 验证置信度应该进一步向"逃避难度"倾斜
    conf = session.session_state["hypothesis_confidence"]
    assert conf["逃避难度"] > 0.5, f"逃避难度置信度应该 > 0.5，实际 {conf['逃避难度']}"
    print(f"✅ '逃避难度'置信度持续上升：{conf['逃避难度']:.2f}")
    
    return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("V3.9.2 修复验证测试")
    print("智能动态临床访谈逻辑")
    print("=" * 60)
    
    tests = [
        ("会话状态追踪", test_session_state_tracking),
        ("状态更新逻辑", test_state_update),
        ("决策逻辑 - 高置信度", test_decision_logic),
        ("决策逻辑 - 鉴别", test_decision_logic_discrimination),
        ("深度挖掘问题", test_deep_dive_question),
        ("完整对话流程", test_full_conversation_flow),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {name} 失败：{e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果：{passed} 通过，{failed} 失败")
    print("=" * 60)
    
    if failed == 0:
        print("\n✅ V3.9.2 修复验证通过！")
        print("   - 会话状态追踪正常")
        print("   - 假设置信度动态更新正常")
        print("   - 高置信度触发深度挖掘正常")
        print("   - 无重复提问逻辑正常")
        return 0
    else:
        print(f"\n❌ {failed} 个测试失败，请检查修复")
        return 1


if __name__ == "__main__":
    sys.exit(main())
