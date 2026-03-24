#!/usr/bin/env python3
"""单案例完整测试 - 持续对话直到报告生成"""

import requests
import time

BASE_URL = "http://localhost:8000"
CHAT_ENDPOINT = f"{BASE_URL}/api/v4/chat"
TIMEOUT = 180

def get_smart_reply(message):
    msg = message.lower()
    if any(k in msg for k in ['几岁', '年龄', '多大']): return '5 岁'
    if any(k in msg for k in ['男孩', '女孩', '性别']): return '女孩'
    if any(k in msg for k in ['地方', '幼儿园', '哪里', '环境']): return '在幼儿园'
    if any(k in msg for k in ['活动', '时候', '情境', '正在']): return '做操的时候'
    if any(k in msg for k in ['表现', '行为', '具体', '怎么']): return '叫他不理，自己玩自己的'
    if any(k in msg for k in ['回应', '处理', '后果', '反应']): return '老师提醒'
    if any(k in msg for k in ['多久', '持续', '时间', '开始']): return '半年了'
    if any(k in msg for k in ['评估', '报告', '完成', '结束']): return '完成评估'
    return '是的'

def run_test():
    session = requests.Session()
    session_id = None
    
    print("="*70)
    print("V4.10.3 单案例完整测试")
    print("="*70)
    
    user_input = '我女儿跟小朋友玩的时候，总以为自己跟别人在玩，其实人家没带她玩。'
    print(f"\n[1] 家长输入：{user_input[:40]}...")
    
    resp = session.post(CHAT_ENDPOINT, json={'user_input': user_input}, timeout=TIMEOUT)
    if resp.status_code != 200:
        print(f"❌ 失败：{resp.status_code}")
        return False
    data = resp.json()
    session_id = data.get('session_id')
    print(f"    → status={data.get('status')}, session={session_id}")
    
    # 持续对话直到报告生成
    for turn in range(2, 20):
        status = data.get('status', '')
        
        # 检查是否完成
        if status == 'completed' and 'report' in data:
            print(f"\n✅ 第{turn-1}轮后报告生成完成！")
            break
        
        # 智能回答
        message = data.get('message', '')
        user_input = get_smart_reply(message)
        print(f"[{turn}] 系统：{message[:40]}...")
        print(f"    回答：{user_input}")
        
        resp = session.post(CHAT_ENDPOINT, 
            json={'user_input': user_input, 'session_id': session_id}, timeout=TIMEOUT)
        
        if resp.status_code != 200:
            print(f"❌ 第{turn}轮失败：{resp.status_code}")
            return False
        
        data = resp.json()
        print(f"    → status={data.get('status')}")
        time.sleep(0.5)
    
    # 最终检查
    print("\n" + "="*70)
    if 'report' in data:
        report = data['report']
        print("✅ 报告生成成功！")
        print("="*70)
        print(f"功能判断：{report.get('functional_judgment', 'N/A')}")
        print(f"能力缺口：{report.get('capability_hypothesis', 'N/A')[:80]}...")
        print(f"摘要：{report.get('summary', 'N/A')[:80]}...")
        print(f"总轮次：{turn-1}")
        return True
    else:
        print(f"❌ 报告未生成（达到最大轮次 20）")
        print(f"最终状态：{data.get('status')}")
        return False

if __name__ == "__main__":
    success = run_test()
    print("\n" + "="*70)
    print(f"测试结果：{'✅ 通过' if success else '❌ 失败'}")
    print("="*70)
    exit(0 if success else 1)
