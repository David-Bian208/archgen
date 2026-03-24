"""
行为记录员 Agent + 干预策略分析师 Agent 单元测试
"""

import pytest
from unittest.mock import Mock, MagicMock

from app.agents.behavior_recorder_agent import BehaviorRecorderAgent
from app.agents.intervention_planner import InterventionPlannerAgent


class MockLLMClient:
    """模拟 LLM 客户端用于测试"""

    def __init__(self, mock_abc_result=None, mock_function="tangible"):
        self.mock_abc_result = mock_abc_result or {
            "antecedent": "测试前因",
            "behavior": "测试行为",
            "consequence": "测试后果",
        }
        self.mock_function = mock_function

    def generate_json(self, system_prompt, user_prompt, temperature=0.1, max_tokens=500):
        return self.mock_abc_result

    def generate(self, system_prompt, user_prompt, temperature=0.1, max_tokens=100):
        return f"功能：{self.mock_function}"


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
        mock_function="tangible",
    )
    agent = BehaviorRecorderAgent(mock_llm)
    
    description = "不给他手机，他就打自己头，我赶紧把手机给他了。"
    result = agent.analyze(description)
    
    assert result["antecedent"] == "不给他手机"
    assert result["behavior"] == "打自己头"
    assert result["consequence"] == "把手机给他"
    assert result["hypothesized_function"] == "tangible"


def test_analyze_escape_function():
    """测试逃避功能的识别"""
    mock_llm = MockLLMClient(
        mock_abc_result={
            "antecedent": "要求他写作业",
            "behavior": "哭闹并逃跑",
            "consequence": "妈妈让他先去玩",
        },
        mock_function="escape",
    )
    agent = BehaviorRecorderAgent(mock_llm)
    
    description = "要求他写作业，他就哭闹并逃跑，妈妈只好让他先去玩。"
    result = agent.analyze(description)
    
    assert result["hypothesized_function"] == "escape"


def test_analyze_attention_function():
    """测试关注功能的识别"""
    mock_llm = MockLLMClient(
        mock_abc_result={
            "antecedent": "妈妈在打电话",
            "behavior": "大声尖叫",
            "consequence": "妈妈停止通话看他",
        },
        mock_function="attention",
    )
    agent = BehaviorRecorderAgent(mock_llm)
    
    description = "妈妈在打电话时，他突然大声尖叫，妈妈只好停止通话看他。"
    result = agent.analyze(description)
    
    assert result["hypothesized_function"] == "attention"


def test_analyze_automatic_function():
    """测试自我刺激功能的识别"""
    mock_llm = MockLLMClient(
        mock_abc_result={
            "antecedent": "独自坐在角落",
            "behavior": "反复摇晃身体",
            "consequence": "无人干预",
        },
        mock_function="automatic",
    )
    agent = BehaviorRecorderAgent(mock_llm)
    
    description = "他独自坐在角落时，会反复摇晃身体，看起来自我刺激。"
    result = agent.analyze(description)
    
    assert result["hypothesized_function"] == "automatic"


def test_parse_function_response():
    """测试功能响应解析"""
    mock_llm = MockLLMClient()
    agent = BehaviorRecorderAgent(mock_llm)
    
    # 测试标准格式
    assert agent._parse_function_response("功能：escape") == "escape"
    assert agent._parse_function_response("功能：tangible") == "tangible"
    
    # 测试关键词匹配
    assert agent._parse_function_response("我认为是 escape 功能") == "escape"
    assert agent._parse_function_response("应该是 attention") == "attention"
    
    # 测试中文关键词
    assert agent._parse_function_response("功能：逃避") == "逃避"
    assert agent._parse_function_response("为了获得关注") == "关注"


def test_empty_description():
    """测试空描述处理"""
    mock_llm = MockLLMClient(
        mock_abc_result={
            "antecedent": "",
            "behavior": "",
            "consequence": "",
        },
        mock_function="automatic",
    )
    agent = BehaviorRecorderAgent(mock_llm)
    
    result = agent.analyze("")
    
    assert result["antecedent"] == ""
    assert result["behavior"] == ""
    assert result["consequence"] == ""
    # 即使 ABC 为空，也应返回默认功能
    assert result["hypothesized_function"] in ["escape", "tangible", "attention", "automatic"]


# ============== 干预策略分析师 Agent 测试 ==============


class MockLLMClientForPlanner:
    """模拟 LLM 客户端用于干预策略测试"""

    def __init__(self, mock_strategy=None, mock_disengagement=None):
        self.mock_strategy = mock_strategy or {
            "function": "tangible",
            "antecedent_strategies": ["策略 1", "策略 2", "策略 3"],
            "behavior_strategies": ["策略 1", "策略 2", "策略 3"],
            "consequence_strategies": ["策略 1", "策略 2", "策略 3"],
            "replacement_behavior": "使用适当方式请求物品",
            "implementation_tips": ["提示 1", "提示 2", "提示 3", "提示 4", "提示 5"],
        }
        self.mock_disengagement = mock_disengagement or {
            "task_name": "任务脱离训练",
            "anchor_behavior": "坐下",
            "step_by_step_plan": ["步骤 1", "步骤 2", "步骤 3"],
            "success_criteria": "成功标准",
            "fallback_plan": "fallback 计划",
        }

    def generate_json(self, system_prompt, user_prompt, temperature=0.3, max_tokens=1500):
        # 根据提示词内容判断返回策略还是任务脱离计划
        if "锚点建立" in user_prompt or "Disengagement" in user_prompt:
            return self.mock_disengagement
        return self.mock_strategy

    def generate(self, system_prompt, user_prompt, temperature=0.1, max_tokens=100):
        return f"功能：tangible"


def test_planner_initialization():
    """测试干预策略分析师 Agent 初始化"""
    mock_llm = MockLLMClientForPlanner()
    agent = InterventionPlannerAgent(mock_llm)
    
    assert agent.llm == mock_llm
    assert agent is not None


def test_generate_strategy_tangible():
    """测试实物功能的干预策略生成"""
    mock_llm = MockLLMClientForPlanner(
        mock_strategy={
            "function": "tangible",
            "antecedent_strategies": [
                "提前告知物品使用规则",
                "提供视觉提示卡",
                "设置计时器明确时间"
            ],
            "behavior_strategies": [
                "教授'我想要'的手势或语言",
                "练习等待技能",
                "使用替代沟通方式"
            ],
            "consequence_strategies": [
                "立即强化适当请求",
                "问题行为时不给予物品",
                "使用'先...然后...'结构"
            ],
            "replacement_behavior": "用语言或手势适当请求物品",
            "implementation_tips": [
                "保持一致性",
                "从小要求开始",
                "使用高频强化",
                "记录行为数据",
                "逐步延长等待时间"
            ],
        }
    )
    agent = InterventionPlannerAgent(mock_llm)
    
    result = agent.generate_strategy(
        antecedent="不给他手机",
        behavior="打自己头",
        consequence="把手机给他",
        function="tangible"
    )
    
    assert result["function"] == "tangible"
    assert len(result["antecedent_strategies"]) >= 3
    assert len(result["behavior_strategies"]) >= 3
    assert len(result["consequence_strategies"]) >= 3
    assert result["replacement_behavior"] != ""
    assert len(result["implementation_tips"]) >= 5


def test_generate_strategy_escape():
    """测试逃避功能的干预策略生成"""
    mock_llm = MockLLMClientForPlanner(
        mock_strategy={
            "function": "escape",
            "antecedent_strategies": [
                "任务分解为小步骤",
                "提供选择权",
                "使用视觉日程表"
            ],
            "behavior_strategies": [
                "教授'休息'的请求方式",
                "练习坚持技能",
                "使用'先...然后...'结构"
            ],
            "consequence_strategies": [
                "完成小步骤后允许短暂休息",
                "问题行为时不终止任务",
                "使用代币强化系统"
            ],
            "replacement_behavior": "用适当方式请求休息",
            "implementation_tips": [
                "从低要求开始",
                "逐步增加任务难度",
                "高频强化适当行为",
                "保持任务趣味性",
                "记录成功数据"
            ],
        }
    )
    agent = InterventionPlannerAgent(mock_llm)
    
    result = agent.generate_strategy(
        antecedent="要求写作业",
        behavior="哭闹逃跑",
        consequence="妈妈让他去玩",
        function="escape"
    )
    
    assert result["function"] == "escape"
    assert len(result["antecedent_strategies"]) >= 3


def test_create_disengagement_anchor():
    """测试任务脱离锚点计划创建"""
    mock_llm = MockLLMClientForPlanner(
        mock_disengagement={
            "task_name": "任务脱离训练",
            "anchor_behavior": "安静坐下 5 秒",
            "step_by_step_plan": [
                "步骤 1: 建立坐下锚点（无任务要求）",
                "步骤 2: 坐下后呈现 1 秒任务",
                "步骤 3: 坐下后呈现 5 秒任务",
                "步骤 4: 坐下后完成简单任务",
                "步骤 5: 泛化到不同任务类型"
            ],
            "success_criteria": "孩子能够在提示下完成任务并保持适当脱离",
            "fallback_plan": "当孩子抗拒时，回到上一步骤，降低任务要求，增加强化频率",
        }
    )
    agent = InterventionPlannerAgent(mock_llm)
    
    result = agent.create_disengagement_anchor(
        function="escape",
        target_behavior="哭闹逃跑",
        challenge="要求写作业时"
    )
    
    assert result["task_name"] == "任务脱离训练"
    assert result["anchor_behavior"] != ""
    assert len(result["step_by_step_plan"]) >= 3
    assert result["success_criteria"] != ""
    assert result["fallback_plan"] != ""


def test_analyze_and_plan_complete():
    """测试完整分析 + 规划流程"""
    mock_llm = MockLLMClientForPlanner()
    agent = InterventionPlannerAgent(mock_llm)
    
    abc_result = {
        "antecedent": "不给他手机",
        "behavior": "打自己头",
        "consequence": "把手机给他",
        "hypothesized_function": "tangible",
    }
    
    result = agent.analyze_and_plan(
        description="不给他手机，他就打自己头，我赶紧把手机给他了。",
        abc_result=abc_result
    )
    
    assert result["status"] == "completed"
    assert result["abc_analysis"] == abc_result
    assert "intervention_strategy" in result
    assert result["intervention_strategy"]["function"] == "tangible"
    # tangible 功能不应有 disengagement_task
    assert result["disengagement_task"] is None


def test_analyze_and_plan_with_disengagement():
    """测试逃避功能的完整分析 + 规划（包含任务脱离计划）"""
    mock_llm = MockLLMClientForPlanner()
    agent = InterventionPlannerAgent(mock_llm)
    
    abc_result = {
        "antecedent": "要求写作业",
        "behavior": "哭闹逃跑",
        "consequence": "妈妈让他去玩",
        "hypothesized_function": "escape",
    }
    
    result = agent.analyze_and_plan(
        description="要求他写作业，他就哭闹逃跑，妈妈只好让他先去玩。",
        abc_result=abc_result
    )
    
    assert result["status"] == "completed"
    assert result["abc_analysis"]["hypothesized_function"] == "escape"
    # escape 功能应该有 disengagement_task
    assert result["disengagement_task"] is not None
    assert result["disengagement_task"]["task_name"] == "任务脱离训练"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
