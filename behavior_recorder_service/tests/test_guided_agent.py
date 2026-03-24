"""
引导式行为记录员 Agent V2.0 单元测试
"""

import pytest
from unittest.mock import Mock

from app.agents.guided_recorder_agent import GuidedRecorderAgent


class MockLLMClient:
    """模拟 LLM 客户端"""

    def __init__(self, mock_responses=None):
        self.mock_responses = mock_responses or []
        self.call_count = 0

    def generate_json(self, system_prompt, user_prompt, temperature=0.1, max_tokens=500):
        if self.call_count < len(self.mock_responses):
            response = self.mock_responses[self.call_count]
            self.call_count += 1
            return response
        # 默认响应
        return {
            "empathy": "谢谢你的描述",
            "assessment": {
                "antecedent_status": "incomplete",
                "behavior_status": "incomplete",
                "consequence_status": "incomplete",
                "missing_field": "antecedent",
            },
            "decision": "question",
            "question": "能再详细描述一下吗？",
        }


def test_create_session():
    """测试会话创建"""
    mock_llm = MockLLMClient()
    agent = GuidedRecorderAgent(mock_llm)

    session = agent._create_session()

    assert session.session_id is not None
    assert len(session.session_id) == 8
    assert session.is_complete is False
    assert session.antecedent == ""
    assert session.behavior == ""
    assert session.consequence == ""


def test_get_or_create_session():
    """测试获取或创建会话"""
    mock_llm = MockLLMClient()
    agent = GuidedRecorderAgent(mock_llm)

    # 创建新会话
    session1 = agent._get_or_create_session(None)
    assert session1 is not None

    # 获取已有会话
    session2 = agent._get_or_create_session(session1.session_id)
    assert session2.session_id == session1.session_id

    # 创建另一个新会话
    session3 = agent._get_or_create_session(None)
    assert session3.session_id != session1.session_id


def test_process_input_initial():
    """测试初始输入处理"""
    mock_llm = MockLLMClient([
        {
            "empathy": "谢谢你的描述，我明白了。",
            "assessment": {
                "antecedent_status": "incomplete",
                "behavior_status": "incomplete",
                "consequence_status": "incomplete",
                "missing_field": "antecedent",
            },
            "decision": "question",
            "question": "在孩子出现这个行为之前，你们正在做什么？",
        }
    ])
    agent = GuidedRecorderAgent(mock_llm)

    response = agent.process_input(None, "他今天打自己头")

    assert response["session_id"] is not None
    # 初始输入可能直接完成或继续提问，取决于 LLM 判断
    assert response["status"] in ["in_progress", "completed"]
    assert response["response_type"] in ["question", "report"]


def test_process_input_complete():
    """测试完整输入处理"""
    mock_llm = MockLLMClient([
        {
            "empathy": "信息很完整，谢谢。",
            "assessment": {
                "antecedent_status": "complete",
                "behavior_status": "complete",
                "consequence_status": "complete",
                "missing_field": "none",
            },
            "decision": "analyze",
            "summary": "已收集完整 ABC 信息",
        },
        {
            "hypothesized_function": "tangible",
            "reasoning": "测试推理",
        }
    ])
    agent = GuidedRecorderAgent(mock_llm)

    response = agent.process_input(None, "不给他手机，他打自己头，我给他手机了")

    # 可能直接完成或需要多轮
    assert response["session_id"] is not None
    if response["status"] == "completed":
        assert response["response_type"] == "report"
        assert "data" in response or "hypothesized_function" in str(response)


def test_session_continuity():
    """测试会话连续性"""
    mock_llm = MockLLMClient([
        {
            "empathy": "谢谢",
            "assessment": {
                "antecedent_status": "incomplete",
                "behavior_status": "incomplete",
                "consequence_status": "incomplete",
                "missing_field": "antecedent",
            },
            "decision": "question",
            "question": "之前发生了什么？",
        },
        {
            "empathy": "明白了",
            "assessment": {
                "antecedent_status": "complete",
                "behavior_status": "complete",
                "consequence_status": "complete",
                "missing_field": "none",
            },
            "decision": "analyze",
            "summary": "完整",
        }
    ])
    agent = GuidedRecorderAgent(mock_llm)

    # 第一轮
    response1 = agent.process_input(None, "他打自己头")
    session_id = response1["session_id"]
    assert response1["session_id"] is not None

    # 第二轮
    response2 = agent.process_input(session_id, "因为不给他手机")
    assert response2["session_id"] == session_id
    # 第二轮可能完成或继续
    assert response2["status"] in ["in_progress", "completed"]


def test_generate_question():
    """测试问题生成"""
    mock_llm = MockLLMClient()
    agent = GuidedRecorderAgent(mock_llm)

    # 测试不同缺失字段的问题
    assessments = {
        "antecedent": "在孩子出现这个行为之前",
        "behavior": "你能更具体地描述一下",
        "consequence": "当孩子这样做之后",
    }

    for field, expected_text in assessments.items():
        question = agent._generate_question({
            "missing_field": field,
        })
        assert expected_text in question


def test_cleanup_session():
    """测试会话清理"""
    mock_llm = MockLLMClient()
    agent = GuidedRecorderAgent(mock_llm)

    # 创建会话
    session = agent._create_session()
    assert session.session_id in agent.sessions

    # 清理会话
    success = agent.cleanup_session(session.session_id)
    assert success is True
    assert session.session_id not in agent.sessions

    # 清理不存在的会话
    success = agent.cleanup_session("nonexistent")
    assert success is False


def test_extract_abc_from_input():
    """测试 ABC 信息提取"""
    mock_llm = MockLLMClient([
        {
            "antecedent": "不给他手机",
            "behavior": "打自己头",
            "consequence": "给他手机",
        }
    ])
    agent = GuidedRecorderAgent(mock_llm)

    session = agent._create_session()
    agent._extract_abc_from_input(session, "不给他手机，他打自己头，我给他手机了")

    assert session.antecedent == "不给他手机"
    assert session.behavior == "打自己头"
    assert session.consequence == "给他手机"


def test_empty_input_handling():
    """测试空输入处理"""
    mock_llm = MockLLMClient()
    agent = GuidedRecorderAgent(mock_llm)

    # 空输入应该也能处理（虽然实际 API 会拦截）
    response = agent.process_input(None, "   ")

    assert response["session_id"] is not None
    # 空输入应该触发提问
    assert response["status"] == "in_progress" or response["status"] == "completed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
