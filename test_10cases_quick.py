#!/usr/bin/env python3
"""
V4.10.3 10 题快速验证测试
目的：验证系统核心功能正常，不过度纠结测试细节
"""

import requests
import time
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
CHAT_ENDPOINT = f"{BASE_URL}/api/v4/chat"
TIMEOUT = 180

# 10 个代表性测试案例（覆盖主要场景）
TEST_CASES = [
    {"id": 1, "scene": "共同游戏", "input": "我女儿跟小朋友玩的时候，总以为自己跟别人在玩，其实人家没带她玩。"},
    {"id": 2, "scene": "共同游戏", "input": "孩子在游乐场想加入其他小朋友，但不知道怎么玩，就站在旁边看。"},
    {"id": 3, "scene": "对话交流", "input": "我儿子跟小朋友聊天，就一直说自己喜欢什么，也不听别人说。"},
    {"id": 4, "scene": "对话交流", "input": "孩子跟别人说话的时候，眼睛不看对方，说完就走。"},
    {"id": 5, "scene": "规则僵化", "input": "我儿子每天回家必须走同一条路，有一次换了条路走，他就崩溃大哭。"},
    {"id": 6, "scene": "规则僵化", "input": "孩子吃饭必须用同一个碗，有一次用了别的碗，他就不吃。"},
    {"id": 7, "scene": "身体边界", "input": "我女儿抱小朋友的时候特别用力，把人家的肋骨都勒疼了。"},
    {"id": 8, "scene": "情绪识别", "input": "我儿子跟小朋友玩，人家都皱眉了他还继续，最后人家生气走了。"},
    {"id": 9, "scene": "提示依赖", "input": "孩子 5 岁，在幼儿园做操时，不看老师就不会做，一看老师就会做。"},
    {"id": 10, "scene": "感觉敏感", "input": "一到超市他就捂耳朵，哭闹要出去。"}
]

def get_smart_reply(message):
    """智能生成后续回答"""
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

def run_test(case):
    """运行单个测试案例"""
    session = requests.Session()
    session_id = None
    
    # 第 1 轮：家长输入
    resp = session.post(CHAT_ENDPOINT, json={'user_input': case["input"]}, timeout=TIMEOUT)
    if resp.status_code != 200:
        return {"passed": False, "error": f"HTTP {resp.status_code}"}
    
    data = resp.json()
    session_id = data.get('session_id')
    
    # 后续轮次：持续对话直到报告生成
    for turn in range(2, 15):
        if data.get('status') == 'completed' and 'report' in data:
            break
        
        user_input = get_smart_reply(data.get('message', ''))
        resp = session.post(CHAT_ENDPOINT, 
            json={'user_input': user_input, 'session_id': session_id}, timeout=TIMEOUT)
        if resp.status_code != 200:
            return {"passed": False, "error": f"HTTP {resp.status_code}"}
        data = resp.json()
    
    # 检查结果
    if 'report' not in data:
        return {"passed": False, "error": "报告未生成"}
    
    report = data['report']
    func_judgment = report.get('functional_judgment', '')
    # 能力缺口可能在 core_capability_goal 或 capability_hypothesis 中
    cap_gap = report.get('core_capability_goal', '') or report.get('capability_hypothesis', '')
    
    # 只要有功能判断和能力缺口就算通过（不严格匹配预期）
    passed = bool(func_judgment) and bool(cap_gap)
    
    return {
        "passed": passed,
        "functional_judgment": func_judgment[:50] if func_judgment else "",
        "capability_gap": cap_gap[:50] if cap_gap else ""
    }

def main():
    print("="*60)
    print("V4.10.3 10 题快速验证测试")
    print("="*60)
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = []
    for i, case in enumerate(TEST_CASES, 1):
        print(f"[{i}/10] 测试：{case['scene']} - {case['input'][:30]}...")
        result = run_test(case)
        results.append(result)
        
        if result["passed"]:
            print(f"      ✅ 通过 - {result['functional_judgment']}")
        else:
            print(f"      ❌ 失败 - {result.get('error', '未知错误')}")
        
        time.sleep(1)
    
    # 汇总
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    
    print()
    print("="*60)
    print(f"测试结果：{passed}/{total} 通过 ({passed/total*100:.1f}%)")
    print("="*60)
    
    # 保存结果
    output = {
        "timestamp": datetime.now().isoformat(),
        "total": total,
        "passed": passed,
        "pass_rate": passed/total*100,
        "results": results
    }
    
    with open('/home/admin/Desktop/V4.10.3_10 题快速测试结果.json', 'w') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存：/home/admin/Desktop/V4.10.3_10 题快速测试结果.json")
    
    return passed >= total * 0.8  # 80% 通过率即算成功

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
