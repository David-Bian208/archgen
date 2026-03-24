"""
行为记录员 Agent V1.1 单元测试
测试优化后的核心逻辑
"""

import pytest
from unittest.mock import Mock

from app.agents.behavior_recorder_agent import BehaviorRecorderAgent


class MockLLMClient:
    """模拟 LLM 客户端用于测试"""

    def __init__(self, mock_abc_result=None, mock_function_result=None):
        self.mock_abc_result = mock_abc_result or {
            "antecedent": "测试前因",
            "behavior": "测试行为",
            "consequence": "测试后果",
        }
        self.mock_function_result = mock_function_result or {
            "hypothesized_function": "tangible",
            "reasoning": "测试推理",
        }

    def generate_json(self, system_prompt, user_prompt, temperature=0.1, max_tokens=500):
        # 根据提示词内容判断是步骤一还是步骤二
        if "推理步骤" in user_prompt or "hypothesized_function" in user_prompt:
            return self.mock_function_result
        return self.mock_abc_result


def test_agent_initialization():
    """测试 Agent 初始化"""
    mock_llm = MockLLMClient()
    agent = BehaviorRecorderAgent(mock_llm)
    
    assert agent.llm == mock_llm
    assert agent is not None


def test_analyze_basic():
    """测试基本分析流程"""
    mock_llm = MockLLMClient(
        mock_abc_result={
            "antecedent": "不给他手机",
            "behavior": "打自己头",
            "consequence": "把手机给他",
        },
        mock_function_result={
            "hypothesized_function": "tangible",
            "reasoning": "行为后获得了想要的物品，符合实物获取特征",
        },
    )
    agent = BehaviorRecorderAgent(mock_llm)
    
    description = "不给他手机，他就打自己头，我赶紧把手机给他了。"
    result = agent.analyze(description)
    
    assert result["antecedent"] == "不给他手机"
    assert result["behavior"] == "打自己头"
    assert result["consequence"] == "把手机给他"
    assert result["hypothesized_function"] == "tangible"
    assert "reasoning" in result
    assert len(result["reasoning"]) > 0


def test_analyze_escape_function():
    """测试逃避功能的识别"""
    mock_llm = MockLLMClient(
        mock_abc_result={
            "antecedent": "要求他写作业",
            "behavior": "哭闹并逃跑",
            "consequence": "妈妈让他先去玩",
        },
        mock_function_result={
            "hypothesized_function": "escape",
            "reasoning": "前因为任务要求，后果为任务中断，符合逃避特征",
        },
    )
    agent = BehaviorRecorderAgent(mock_llm)
    
    description = "要求他写作业，他就哭闹并逃跑，妈妈只好让他先去玩。"
    result = agent.analyze(description)
    
    assert result["hypothesized_function"] == "escape"
    assert "逃避" in result["reasoning"] or "任务" in result["reasoning"]


def test_analyze_attention_function():
    """测试关注功能的识别"""
    mock_llm = MockLLMClient(
        mock_abc_result={
            "antecedent": "妈妈在打电话",
            "behavior": "大声尖叫",
            "consequence": "妈妈停止通话看他",
        },
        mock_function_result={
            "hypothesized_function": "attention",
            "reasoning": "行为获得了他人注意，符合关注获取特征",
        },
    )
    agent = BehaviorRecorderAgent(mock_llm)
    
    description = "妈妈在打电话时，他突然大声尖叫，妈妈只好停止通话看他。"
    result = agent.analyze(description)
    
    assert result["hypothesized_function"] == "attention"
    assert "注意" in result["reasoning"] or "关注" in result["reasoning"]


def test_analyze_automatic_function():
    """测试自我刺激功能的识别"""
    mock_llm = MockLLMClient(
        mock_abc_result={
            "antecedent": "独自坐在角落",
            "behavior": "反复摇晃身体",
            "consequence": "未明确提及",
        },
        mock_function_result={
            "hypothesized_function": "automatic",
            "reasoning": "行为是重复刻板的，与社交环境无关，符合自动强化特征",
        },
    )
    agent = BehaviorRecorderAgent(mock_llm)
    
    description = "他独自坐在角落时，会反复摇晃身体，看起来自我刺激。"
    result = agent.analyze(description)
    
    assert result["hypothesized_function"] == "automatic"


def test_analyze_inconclusive():
    """测试信息不足时的 inconclusive 判断"""
    mock_llm = MockLLMClient(
        mock_abc_result={
            "antecedent": "未明确提及",
            "behavior": "有些异常",
            "consequence": "未明确提及",
        },
        mock_function_result={
            "hypothesized_function": "inconclusive",
            "reasoning": "信息不足，无法做出明确判断",
        },
    )
    agent = BehaviorRecorderAgent(mock_llm)
    
    description = "他今天表现有些异常。"
    result = agent.analyze(description)
    
    assert result["hypothesized_function"] == "inconclusive"


def test_empty_description_error():
    """测试空描述抛出错误"""
    mock_llm = MockLLMClient()
    agent = BehaviorRecorderAgent(mock_llm)
    
    with pytest.raises(ValueError, match="描述不能为空"):
        agent.analyze("")
    
    with pytest.raises(ValueError, match="描述不能为空"):
        agent.analyze("   ")


def test_missing_fields_handling():
    """测试缺失字段的默认处理"""
    mock_llm = MockLLMClient(
        mock_abc_result={
            "antecedent": "测试",
            # 缺少 behavior 和 consequence
        },
        mock_function_result={
            "hypothesized_function": "tangible",
            "reasoning": "测试推理",
        },
    )
    agent = BehaviorRecorderAgent(mock_llm)
    
    result = agent.analyze("测试描述")
    
    # 缺失字段应被填充为默认值
    assert result["antecedent"] == "测试"
    assert result["behavior"] == "未明确提及"
    assert result["consequence"] == "未明确提及"


# ========== V1.1 新增测试案例 ==========

def test_v11_case_foggy_social_escape():
    """V1.1 测试案例：模糊后果的社交逃避"""
    mock_llm = MockLLMClient(
        mock_abc_result={
            "antecedent": "在教室排队跳操时",
            "behavior": "眼睛不跟随老师，站着发呆",
            "consequence": "未明确提及",
        },
        mock_function_result={
            "hypothesized_function": "escape",
            "reasoning": "前因为集体活动要求，行为表现为不参与，符合逃避特征",
        },
    )
    agent = BehaviorRecorderAgent(mock_llm)
    
    description = "在教室排队跳操时，他眼睛不跟随老师，站着发呆。"
    result = agent.analyze(description)
    
    # 这个案例可能是 escape 或 inconclusive，取决于专业判断
    assert result["hypothesized_function"] in ["escape", "inconclusive", "automatic"]
    assert "reasoning" in result
    assert len(result["reasoning"]) > 10


def test_v11_case_tangible():
    """V1.1 测试案例：明显的实物获取"""
    mock_llm = MockLLMClient(
        mock_abc_result={
            "antecedent": "想要手机我没给",
            "behavior": "打自己头",
            "consequence": "我马上把手机给他了",
        },
        mock_function_result={
            "hypothesized_function": "tangible",
            "reasoning": "行为后获得了想要的物品，符合实物获取特征",
        },
    )
    agent = BehaviorRecorderAgent(mock_llm)
    
    description = "想要手机我没给，他就打自己头，我马上把手机给他了。"
    result = agent.analyze(description)
    
    assert result["hypothesized_function"] == "tangible"
    assert "实物" in result["reasoning"] or "物品" in result["reasoning"]


def test_v11_case_attention():
    """V1.1 测试案例：获得关注（即使是负面的）"""
    mock_llm = MockLLMClient(
        mock_abc_result={
            "antecedent": "我在工作时",
            "behavior": "他不停跑来拍我笔记本",
            "consequence": "我每次都说'别吵'",
        },
        mock_function_result={
            "hypothesized_function": "attention",
            "reasoning": "行为获得了他人反应（即使是负面），符合关注获取特征",
        },
    )
    agent = BehaviorRecorderAgent(mock_llm)
    
    description = "我在工作时，他不停跑来拍我笔记本，我每次都说'别吵'。"
    result = agent.analyze(description)
    
    assert result["hypothesized_function"] == "attention"
    assert "注意" in result["reasoning"] or "关注" in result["reasoning"] or "反应" in result["reasoning"]


def test_v11_reasoning_field_present():
    """V1.1 测试：确保所有分析都包含 reasoning 字段"""
    test_cases = [
        "不给他手机，他就打自己头，我赶紧把手机给他了。",
        "要求他写作业，他就哭闹并逃跑，妈妈只好让他先去玩。",
        "妈妈在打电话时，他突然大声尖叫，妈妈只好停止通话看他。",
        "他独自坐在角落时，会反复摇晃身体。",
    ]
    
    for description in test_cases:
        mock_llm = MockLLMClient(
            mock_function_result={
                "hypothesized_function": "tangible",
                "reasoning": f"针对'{description[:20]}...'的推理",
            },
        )
        agent = BehaviorRecorderAgent(mock_llm)
        result = agent.analyze(description)
        
        assert "reasoning" in result, f"测试案例缺少 reasoning 字段：{description}"
        assert isinstance(result["reasoning"], str), "reasoning 应该是字符串"
        assert len(result["reasoning"]) > 0, "reasoning 不应该为空"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
