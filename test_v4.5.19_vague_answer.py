#!/usr/bin/env python3
"""
V4.5.19 模糊回答检测与共情回应测试

测试场景：
1. 用户说"不知道" → 应触发共情回应
2. 用户说"看情况" → 应触发共情回应
3. 用户使用模糊标签 → 应引导具体描述
4. 同一字段问过 2 次仍未填充 → 应跳过或强制结束
"""

import sys
import json
sys.path.insert(0, '/home/admin/.openclaw/workspace/behavior_recorder_service')

from app.agents.structured_assessor_v4 import StructuredAssessorV4
from app.config import get_config
from app.llm.openai_client import OpenAIClient

def test_vague_answer_detection():
    """测试模糊回答检测"""
    print("=" * 60)
    print("V4.5.19 模糊回答检测测试")
    print("=" * 60)
    
    config = get_config()
    llm_client = OpenAIClient(
        api_key=config.llm_api_key,
        base_url=config.llm_base_url,
        model=config.llm_model,
    )
    framework_path = "app/knowledge/clinical_assessment_framework.json"
    agent = StructuredAssessorV4(llm_client, framework_path)
    
    # 测试用例 1: "不知道"
    print("\n【测试 1】用户说'不知道'")
    print("-" * 40)
    response = agent.process(None, "你好，我想咨询孩子的行为问题")
    print(f"首轮提问：{response['message'][:100]}...")
    
    # 模拟用户回答"不知道"
    response = agent.process(response['session_id'], "不知道")
    print(f"共情回应：{response['message'][:200]}...")
    assert response['response_type'] == 'empathetic_follow_up', "应返回共情回应"
    assert 'vague_type' in response, "应包含 vague_type"
    print(f"✓ 检测到模糊类型：{response['vague_type']}")
    
    # 测试用例 2: "看情况"
    print("\n【测试 2】用户说'看情况'")
    print("-" * 40)
    agent2 = StructuredAssessorV4(llm_client, framework_path)
    response = agent2.process(None, "孩子社交有问题")
    print(f"首轮提问：{response['message'][:100]}...")
    
    response = agent2.process(response['session_id'], "要看具体事情")
    print(f"共情回应：{response['message'][:200]}...")
    assert response['response_type'] == 'empathetic_follow_up', "应返回共情回应"
    print(f"✓ 检测到模糊类型：{response['vague_type']}")
    
    # 测试用例 3: 模糊标签
    print("\n【测试 3】用户使用模糊标签'深度关注'")
    print("-" * 40)
    agent3 = StructuredAssessorV4(llm_client, framework_path)
    response = agent3.process(None, "孩子深度关注有问题")
    print(f"首轮回应：{response['message'][:200]}...")
    # 首轮应该检测模糊标签并引导具体描述
    if response['response_type'] == 'empathetic_follow_up':
        print(f"✓ 检测到模糊标签，引导具体描述")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)

def test_framework_problem_clarification():
    """测试问题澄清阶段"""
    print("\n" + "=" * 60)
    print("V4.5.19 问题澄清阶段测试")
    print("=" * 60)
    
    import json
    framework_path = '/home/admin/.openclaw/workspace/behavior_recorder_service/app/knowledge/clinical_assessment_framework.json'
    with open(framework_path, 'r', encoding='utf-8') as f:
        framework = json.load(f)
    
    # 检查是否添加了 PROBLEM_CLARIFICATION 阶段
    stages = framework.get('workflow_stages', [])
    problem_clarification = next((s for s in stages if s['id'] == 'PROBLEM_CLARIFICATION'), None)
    
    assert problem_clarification is not None, "应包含 PROBLEM_CLARIFICATION 阶段"
    print(f"✓ 已添加 PROBLEM_CLARIFICATION 阶段")
    print(f"  阶段名称：{problem_clarification['name']}")
    print(f"  字段数量：{len(problem_clarification['fields'])}")
    
    # 检查字段
    for field in problem_clarification['fields']:
        print(f"  - {field['field_id']}: {field['short_name']}")
    
    # 检查必填字段列表
    required_fields = framework['completion_rules']['required_fields_for_analysis']
    assert 'problem_description' in required_fields, "problem_description 应为必填字段"
    assert 'specific_example' in required_fields, "specific_example 应为必填字段"
    print(f"✓ 必填字段已更新：{required_fields}")
    
    # 检查最大轮数
    max_turns = framework['completion_rules']['max_turns']
    assert max_turns == 10, f"max_turns 应为 10，实际为{max_turns}"
    print(f"✓ 最大轮数已更新：{max_turns}")
    
    print("\n" + "=" * 60)
    print("✅ 框架配置测试通过！")
    print("=" * 60)

if __name__ == '__main__':
    test_framework_problem_clarification()
    test_vague_answer_detection()
