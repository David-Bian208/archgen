#!/usr/bin/env python3
"""
V4.10.3 能力缺口分析修复测试
测试 clinical_differential 字段是否正确生成能力缺口分析
"""

import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v4/chat"

# 测试案例 4：寻求关注行为
TEST_CASE = {
    "input": "我女儿在课堂上总是突然发出奇怪的声音，老师看她时她就笑，不看她时就继续发出声音，即使被批评也停不下来。",
    "expected_function": "寻求关注",
    "expected_gaps": ["社交沟通技能", "社交信号监测", "自我调节"]
}

def test_clinical_differential():
    """测试 clinical_differential 字段是否包含完整的能力缺口分析"""
    
    print("=" * 60)
    print("V4.10.3 能力缺口分析修复测试")
    print("=" * 60)
    
    session_id = None
    
    # 发送初始消息
    print("\n📤 发送初始消息...")
    response = requests.post(BASE_URL, json={
        "user_input": TEST_CASE["input"]
    })
    
    if response.status_code != 200:
        print(f"❌ 请求失败：{response.status_code}")
        print(response.text)
        return False
    
    data = response.json()
    session_id = data.get('session_id')
    print(f"✅ 响应状态：{data.get('status')}, session_id={session_id}")
    
    # 检查是否需要继续对话
    if data.get('status') == 'in_progress':
        print("📤 继续对话...")
        # 模拟几轮对话直到报告生成
        for i in range(5):
            follow_up = data.get('message', '继续')
            print(f"  轮次 {i+1}: {follow_up[:50]}...")
            
            # 发送回复
            response = requests.post(BASE_URL, json={
                "user_input": "继续",
                "session_id": session_id
            })
            data = response.json()
            
            if data.get('status') == 'completed':
                print("✅ 报告生成完成")
                break
    
    # 检查报告
    if data.get('status') != 'completed':
        print(f"❌ 报告未生成，状态：{data.get('status')}")
        return False
    
    # 提取 clinical_differential
    report_data = data.get('data', {}).get('report', {})
    clinical_differential = report_data.get('clinical_differential', '')
    
    print("\n" + "=" * 60)
    print("📋 clinical_differential 内容:")
    print("=" * 60)
    print(clinical_differential)
    print("=" * 60)
    
    # 验证能力缺口分析
    print("\n🔍 验证能力缺口分析...")
    
    # 检查是否包含三模块结构
    has_differential = "鉴别与排除" in clinical_differential
    has_hypothesis = "核心假设" in clinical_differential
    has_gaps = "能力缺口分析" in clinical_differential
    
    print(f"  鉴别与排除：{'✅' if has_differential else '❌'}")
    print(f"  核心假设：{'✅' if has_hypothesis else '❌'}")
    print(f"  能力缺口分析：{'✅' if has_gaps else '❌'}")
    
    # 检查能力缺口数量
    gap_count = clinical_differential.count("→")
    print(f"  能力缺口数量：{gap_count} 个（期望：2-3 个）")
    
    # 检查是否包含预期的能力缺口
    expected_gaps = TEST_CASE["expected_gaps"]
    found_gaps = []
    for gap in expected_gaps:
        if gap in clinical_differential:
            found_gaps.append(gap)
    
    print(f"  预期能力缺口：{expected_gaps}")
    print(f"  找到的能力缺口：{found_gaps}")
    
    # 最终判断
    success = has_differential and has_hypothesis and has_gaps and gap_count >= 2
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 测试通过：能力缺口分析生成正确")
    else:
        print("❌ 测试失败：能力缺口分析缺失或不完整")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    try:
        test_clinical_differential()
    except Exception as e:
        print(f"❌ 测试异常：{e}")
        import traceback
        traceback.print_exc()
