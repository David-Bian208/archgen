#!/usr/bin/env python3
"""
自动对话测试脚本 - 智能回答直到报告生成
"""

import requests
import time
import re

BASE_URL = "http://localhost:8000"
CHAT_ENDPOINT = f"{BASE_URL}/api/v4/chat"
TIMEOUT = 180
MAX_TURNS = 15

def get_smart_reply(message: str, turn: int) -> str:
    """根据系统消息智能生成回答"""
    msg = message.lower()
    
    # 年龄相关
    if any(k in msg for k in ['几岁', '年龄', '多大', '出生']):
        return '5 岁'
    
    # 性别相关
    if any(k in msg for k in ['男孩', '女孩', '性别', '男生', '女生']):
        return '女孩'
    
    # 地点/环境相关
    if any(k in msg for k in ['地方', '哪里', '幼儿园', '学校', '环境', '场景']):
        return '在幼儿园'
    
    # 活动/情境相关
    if any(k in msg for k in ['活动', '情境', '时候', '正在', '发生']):
        return '做操的时候'
    
    # 行为细节相关
    if any(k in msg for k in ['具体', '表现', '行为', '怎么做', '什么样子']):
        return '叫他不理，自己玩自己的'
    
    # 回应/后果相关
    if any(k in msg for k in ['回应', '处理', '后果', '反应', '怎么办']):
        return '老师提醒他'
    
    # 时间/持续时间相关
    if any(k in msg for k in ['多久', '时间', '持续', '开始', '多久了']):
        return '半年了'
    
    # 评估/报告相关
    if any(k in msg for k in ['评估', '报告', '完成', '结束', '分析']):
        return '完成评估'
    
    # 默认回答
    return '是的'

def run_auto_test():
    """运行自动对话测试"""
    session = requests.Session()
    session_id = None
    
    print("="*70)
    print("V4.10.3 自动对话测试 - 智能回答直到报告生成")
    print("="*70)
    
    # 第 1 轮：家长输入
    user_input = '我女儿跟小朋友玩的时候，总以为自己跟别人在玩，其实人家没带她玩。'
    print(f"\n[第 1 轮] 家长输入：{user_input[:40]}...")
    
    resp = session.post(CHAT_ENDPOINT, json={'user_input': user_input}, timeout=TIMEOUT)
    if resp.status_code != 200:
        print(f"❌ 第 1 轮失败：{resp.status_code}")
        return False
    
    data = resp.json()
    session_id = data.get('session_id')
    print(f"  → status={data.get('status')}, session={session_id}")
    
    # 后续轮次：智能对话
    for turn in range(2, MAX_TURNS + 1):
        status = data.get('status', '')
        
        # 检查是否完成
        if status == 'completed' and 'report' in data:
            print(f"\n✅ 第{turn-1}轮后报告生成完成！")
            break
        
        # 获取系统消息
        message = data.get('message', '')
        
        # 智能生成回答
        user_input = get_smart_reply(message, turn)
        print(f"[第{turn}轮] 系统：{message[:50]}...")
        print(f"         回答：{user_input}")
        
        # 发送回答
        resp = session.post(CHAT_ENDPOINT, 
            json={'user_input': user_input, 'session_id': session_id}, 
            timeout=TIMEOUT)
        
        if resp.status_code != 200:
            print(f"❌ 第{turn}轮失败：{resp.status_code}")
            return False
        
        data = resp.json()
        print(f"  → status={data.get('status')}")
        
        # 短暂间隔
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
        print(f"❌ 报告未生成（达到最大轮次{MAX_TURNS}）")
        print(f"最终状态：{data.get('status')}")
        print(f"可用字段：{list(data.keys())}")
        return False

if __name__ == "__main__":
    success = run_auto_test()
    print("\n" + "="*70)
    print(f"测试结果：{'✅ 通过' if success else '❌ 失败'}")
    print("="*70)
    exit(0 if success else 1)
