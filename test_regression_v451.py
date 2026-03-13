#!/usr/bin/env python3
"""
V4.5.1 紧急修复后回归测试
测试前 3 个核心案例
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v4"
OUTPUT_FILE = f"/home/admin/Desktop/回归测试结果-{datetime.now().strftime('%Y%m%d-%H%M')}.json"

# 前 3 个测试案例
TEST_CASES = [
    {
        "id": 1,
        "name": "典型提示依赖",
        "input": "孩子 5 岁，在幼儿园做操时，不看老师就不会做，一看老师就会做。",
        "answers": ["男孩", "户外操场", "老师提醒他看这里", "没有了"]
    },
    {
        "id": 2,
        "name": "逃避难度",
        "input": "我家孩子 7 岁，一写数学作业就说太难了，然后开始哭。",
        "answers": ["女孩", "在家写作业", "我给她讲道理", "就这些"]
    },
    {
        "id": 3,
        "name": "感觉逃避",
        "input": "一到超市他就捂耳朵，哭闹要出去。",
        "answers": ["5 岁", "男孩", "超市很吵", "我们离开", "没有了"]
    }
]

def run_case(case):
    """执行单个案例测试"""
    print(f"\n{'='*60}")
    print(f"案例{case['id']}: {case['name']}")
    print(f"{'='*60}")
    
    session_id = None
    conversation_log = []
    report = None
    turn_count = 0
    max_turns = 8
    
    # 第 1 轮
    print(f"\n【用户】{case['input']}")
    try:
        resp = requests.post(f"{BASE_URL}/chat", json={"user_input": case["input"]}, timeout=30)
        data = resp.json()
    except Exception as e:
        print(f"❌ 请求失败：{e}")
        return {"error": str(e)}
    
    session_id = data.get("session_id")
    ai_msg = data.get("message", "")
    print(f"【AI】{ai_msg[:100]}...")
    conversation_log.append({"role": "user", "content": case["input"]})
    conversation_log.append({"role": "ai", "content": ai_msg})
    turn_count += 1
    
    # 后续轮次
    for answer in case["answers"]:
        if data.get("status") == "completed":
            report = data.get("data")
            print(f"\n✅ 报告已生成（{turn_count}轮）")
            break
        
        if turn_count >= max_turns:
            print(f"\n⚠️ 达到轮次上限（{max_turns}轮）")
            break
        
        print(f"\n【用户】{answer}")
        try:
            resp = requests.post(f"{BASE_URL}/chat", json={
                "session_id": session_id,
                "user_input": answer
            }, timeout=30)
            data = resp.json()
        except Exception as e:
            print(f"❌ 请求失败：{e}")
            break
        
        ai_msg = data.get("message", "")
        print(f"【AI】{ai_msg[:100] if ai_msg else '空回复'}...")
        conversation_log.append({"role": "user", "content": answer})
        conversation_log.append({"role": "ai", "content": ai_msg})
        turn_count += 1
        
        if data.get("status") == "completed":
            report = data.get("data")
            print(f"\n✅ 报告已生成（{turn_count}轮）")
            break
    
    # 如果最后仍未完成但达到轮次上限，检查是否有报告
    if data.get("status") == "completed" and data.get("data"):
        report = data["data"]
    
    # 评估
    passed = report is not None and turn_count <= 6
    
    result = {
        "case_id": case["id"],
        "case_name": case["name"],
        "conversation_log": conversation_log,
        "report": report,
        "turn_count": turn_count,
        "passed": passed,
        "status": data.get("status", "unknown"),
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"\n📊 结果：轮次={turn_count}, 报告={'有' if report else '无'}, 通过={'✅' if passed else '❌'}")
    
    if report:
        print(f"   功能判断：{report.get('functional_judgment', 'N/A')}")
        print(f"   核心洞察：{report.get('core_insight', 'N/A')[:50]}...")
    
    return result

def main():
    print("="*60)
    print("🧪 V4.5.1 紧急修复后回归测试")
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*60)
    
    results = []
    for case in TEST_CASES:
        result = run_case(case)
        results.append(result)
    
    # 汇总
    total = len(results)
    passed = sum(1 for r in results if r.get("passed"))
    with_report = sum(1 for r in results if r.get("report"))
    avg_turns = sum(r.get("turn_count", 0) for r in results) / total if total > 0 else 0
    
    summary = {
        "test_info": {
            "version": "V4.5.1",
            "total_cases": total,
            "passed": passed,
            "pass_rate": f"{passed/total*100:.1f}%" if total > 0 else "N/A",
            "with_report": with_report,
            "avg_turns": f"{avg_turns:.1f}",
            "timestamp": datetime.now().isoformat()
        },
        "results": results
    }
    
    # 保存结果
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print("📊 测试汇总")
    print(f"{'='*60}")
    print(f"总数：{total} | 通过：{passed} | 通过率：{summary['test_info']['pass_rate']}")
    print(f"有报告：{with_report}/{total}")
    print(f"平均轮次：{avg_turns:.1f}")
    print(f"\n📄 详情：{OUTPUT_FILE}")
    
    return summary

if __name__ == "__main__":
    main()
