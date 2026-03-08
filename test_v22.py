#!/usr/bin/env python3
"""V2.2 功能测试脚本"""

import requests

BASE_URL = "http://localhost:8000"

def test_complete_analysis():
    """测试完整分析（包含置信度）"""
    print("=" * 60)
    print("测试：完整行为分析（包含置信度）")
    print("=" * 60)
    
    # 第一轮
    response1 = requests.post(f"{BASE_URL}/api/v2/record", json={
        "user_input": "不给他手机，他打自己头，我马上把手机给他了"
    })
    data1 = response1.json()
    print(f"\n第一轮状态：{data1['status']}")
    session_id = data1['session_id']
    
    # 第二轮
    response2 = requests.post(f"{BASE_URL}/api/v2/record", json={
        "session_id": session_id,
        "user_input": "当时我正在工作"
    })
    data2 = response2.json()
    print(f"第二轮状态：{data2['status']}")
    
    if data2['status'] == 'completed':
        result = data2.get('data', {})
        print(f"\n功能假设：{result.get('hypothesized_function')}")
        print(f"置信度：{result.get('confidence')}")
        print(f"推理：{result.get('reasoning', '')[:60]}...")
        print(f"\n家长报告开场：{result.get('parent_report', {}).get('empathy_opening', '')[:40]}...")
        print(f"置信度提示：{result.get('parent_report', {}).get('confidence_hint', '')[:40]}...")
    else:
        print("未完成，继续提问...")
        print(f"问题：{data2.get('message', '')[:100]}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_complete_analysis()
