#!/usr/bin/env python3
"""简化 3 案例测试 - 验证修复效果"""

import requests
import time
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
CHAT_ENDPOINT = f"{BASE_URL}/api/v4/chat"
TIMEOUT = 180

TEST_CASES = [
    {
        "id": 1,
        "scene": "joint_play",
        "parent_input": "我女儿跟小朋友玩的时候，总以为自己跟别人在玩，其实人家没带她玩。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": ["社交信号监测", "监测"]
    },
    {
        "id": 2,
        "scene": "rules_rigidity",
        "parent_input": "我儿子每天回家必须走同一条路，有一次换了条路走，他就崩溃大哭。",
        "expected_hypothesis": "坚持同一性",
        "expected_capability_gap": ["认知灵活性", "灵活性"]
    },
    {
        "id": 3,
        "scene": "body_boundary",
        "parent_input": "我女儿抱小朋友的时候特别用力，把人家的肋骨都勒疼了。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": ["身体边界", "身体感知"]
    }
]

def get_smart_reply(message):
    msg = message.lower()
    if any(k in msg for k in ['几岁', '年龄']): return '5 岁'
    if any(k in msg for k in ['男孩', '女孩']): return '女孩'
    if any(k in msg for k in ['地方', '幼儿园', '哪里']): return '在幼儿园'
    if any(k in msg for k in ['活动', '时候', '情境']): return '做操的时候'
    if any(k in msg for k in ['回应', '处理']): return '老师提醒'
    if any(k in msg for k in ['多久', '持续', '时间']): return '半年了'
    return '完成评估'

def run_test(case):
    session = requests.Session()
    session_id = None
    
    print(f"\n{'='*60}")
    print(f"测试 #{case['id']} ({case['scene']})")
    print(f"{'='*60}")
    
    # 第 1 轮
    user_input = case["parent_input"]
    print(f"[1] 输入：{user_input[:40]}...")
    resp = session.post(CHAT_ENDPOINT, json={'user_input': user_input}, timeout=TIMEOUT)
    if resp.status_code != 200:
        print(f"  ❌ 失败：{resp.status_code}")
        return False
    data = resp.json()
    session_id = data.get('session_id')
    print(f"  → status={data.get('status')}")
    
    # 后续轮次
    for turn in range(2, 10):
        if data.get('status') == 'completed' and 'report' in data:
            break
        
        user_input = get_smart_reply(data.get('message', ''))
        print(f"[{turn}] 回答：{user_input}")
        resp = session.post(CHAT_ENDPOINT, 
            json={'user_input': user_input, 'session_id': session_id}, timeout=TIMEOUT)
        if resp.status_code != 200:
            print(f"  ❌ 失败：{resp.status_code}")
            return False
        data = resp.json()
        print(f"  → status={data.get('status')}")
    
    # 检查结果
    if 'report' in data:
        report = data['report']
        func_judgment = report.get('functional_judgment', '')
        cap_gap = report.get('capability_hypothesis', '')
        
        hypothesis_match = case['expected_hypothesis'] in func_judgment
        capability_match = any(k in cap_gap for k in case['expected_capability_gap'])
        passed = hypothesis_match and capability_match
        
        print(f"\n  功能判断：{func_judgment[:50]}...")
        print(f"  能力缺口：{cap_gap[:50]}...")
        print(f"  假设匹配：{'✅' if hypothesis_match else '❌'}")
        print(f"  能力匹配：{'✅' if capability_match else '❌'}")
        print(f"  结果：{'✅ 通过' if passed else '❌ 失败'}")
        return passed
    else:
        print(f"\n  ❌ 报告未生成")
        return False

def main():
    print("="*60)
    print("V4.10.3 简化 3 案例测试")
    print("="*60)
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    for case in TEST_CASES:
        result = run_test(case)
        results.append(result)
        time.sleep(1)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n{'='*60}")
    print(f"测试结果：{passed}/{total} 通过 ({passed/total*100:.1f}%)")
    print(f"{'='*60}")
    
    # 保存结果
    with open('/home/admin/Desktop/V4.10.3_3 案例简化测试结果.json', 'w') as f:
        json.dump({'passed': passed, 'total': total, 'rate': passed/total*100}, f)
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
