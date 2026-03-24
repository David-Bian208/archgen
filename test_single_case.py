#!/usr/bin/env python3
"""单案例测试 - 验证修复是否有效"""

import requests
import time

BASE_URL = "http://localhost:8000"
CHAT_ENDPOINT = f"{BASE_URL}/api/v4/chat"
TIMEOUT = 120  # 增加超时时间

def test_single_case():
    session = requests.Session()
    session_id = None
    
    print("="*60)
    print("单案例测试：共同游戏场景")
    print("="*60)
    
    # 第 1 轮：家长输入
    print("\n第 1 轮：家长输入")
    resp = session.post(CHAT_ENDPOINT, json={
        'user_input': '我女儿跟小朋友玩的时候，总以为自己跟别人在玩，其实人家没带她玩。',
        'session_id': session_id
    }, timeout=TIMEOUT)
    
    if resp.status_code != 200:
        print(f"❌ 第 1 轮失败：{resp.status_code} - {resp.text}")
        return False
    
    data = resp.json()
    session_id = data.get('session_id')
    print(f"  Status: {data.get('status')}")
    print(f"  Session: {session_id}")
    
    # 第 2 轮：年龄
    print("\n第 2 轮：年龄")
    resp = session.post(CHAT_ENDPOINT, json={
        'user_input': '5 岁',
        'session_id': session_id
    }, timeout=TIMEOUT)
    
    if resp.status_code != 200:
        print(f"❌ 第 2 轮失败：{resp.status_code}")
        return False
    
    data = resp.json()
    print(f"  Status: {data.get('status')}")
    
    # 第 3 轮：地点
    print("\n第 3 轮：地点")
    resp = session.post(CHAT_ENDPOINT, json={
        'user_input': '在幼儿园',
        'session_id': session_id
    }, timeout=TIMEOUT)
    
    if resp.status_code != 200:
        print(f"❌ 第 3 轮失败：{resp.status_code}")
        return False
    
    data = resp.json()
    print(f"  Status: {data.get('status')}")
    
    # 第 4-8 轮：继续对话直到报告生成
    max_turns = 8
    for turn in range(4, max_turns + 1):
        if data.get('status') == 'completed' and 'report' in data:
            break
        
        # 根据系统消息智能回答
        message = data.get('message', '')
        if '活动' in message or '地方' in message or '情境' in message:
            user_input = '做操的时候'
        elif '回应' in message or '怎么处理' in message:
            user_input = '老师提醒他'
        elif '多久' in message or '时间' in message or '持续' in message:
            user_input = '半年了'
        elif '评估' in message or '报告' in message or '完成' in message:
            user_input = '完成评估'
        else:
            user_input = '是的'
        
        print(f"\n第{turn}轮：{user_input}")
        resp = session.post(CHAT_ENDPOINT, json={
            'user_input': user_input,
            'session_id': session_id
        }, timeout=TIMEOUT)
        
        if resp.status_code != 200:
            print(f"❌ 第{turn}轮失败：{resp.status_code}")
            return False
        
        data = resp.json()
        print(f"  Status: {data.get('status')}")
    
    # 检查报告
    if 'report' in data:
        report = data['report']
        print("\n" + "="*60)
        print("✅ 报告生成成功！")
        print("="*60)
        print(f"功能判断：{report.get('functional_judgment', 'N/A')}")
        print(f"能力缺口：{report.get('capability_hypothesis', 'N/A')[:100]}...")
        print(f"摘要：{report.get('summary', 'N/A')[:100]}...")
        return True
    else:
        print("\n❌ 报告未生成")
        print(f"Status: {data.get('status')}")
        print(f"Response keys: {list(data.keys())}")
        return False

if __name__ == "__main__":
    success = test_single_case()
    print("\n" + "="*60)
    print(f"测试结果：{'✅ 通过' if success else '❌ 失败'}")
    print("="*60)
    exit(0 if success else 1)
