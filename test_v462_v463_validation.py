#!/usr/bin/env python3
"""
V4.6.2-V4.6.3 阶段验证测试集
测试 ADHD 和情绪管理新增关键词匹配
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v4"

# ADHD 和情绪管理验证案例
TEST_CASES = [
    # ADHD 相关 (10 词)
    {
        "hypothesis": "H_WORKING_MEMORY",
        "input": "孩子左耳进右耳出，说啥忘啥，记性特别差",
        "expected": "H_WORKING_MEMORY"
    },
    {
        "hypothesis": "H_SUSTAINED_ATTENTION",
        "input": "坐不住，老是走神，注意力不集中，做事三分钟热度",
        "expected": "H_SUSTAINED_ATTENTION"
    },
    {
        "hypothesis": "impulse_control",
        "input": "冲动，控制不住自己，行动先于思考",
        "expected": "impulse_control"
    },
    
    # 情绪管理相关 (12 词)
    {
        "hypothesis": "emotional_regulation",
        "input": "脾气大，易怒，暴躁，情绪化",
        "expected": "emotional_regulation"
    },
    {
        "hypothesis": "emotional_regulation",
        "input": "玻璃心，输不起，容易沮丧",
        "expected": "emotional_regulation"
    },
    {
        "hypothesis": "emotional_regulation",
        "input": "叛逆，对着干，不听管教，情绪波动大",
        "expected": "emotional_regulation"
    },
]

def test_case(case):
    """测试单个案例"""
    try:
        response = requests.post(f"{BASE_URL}/chat", json={"user_input": case["input"]}, timeout=30)
        data = response.json()
        
        locked_hyp = data.get("locked_hypothesis", "unknown")
        
        # 判断是否正确
        is_correct = (locked_hyp == case["expected"])
        
        return {
            "hypothesis": case["hypothesis"],
            "input": case["input"][:50] + "...",
            "expected": case["expected"],
            "predicted": locked_hyp,
            "correct": is_correct,
            "response": data.get("message", "")[:100]
        }
    except Exception as e:
        return {
            "hypothesis": case["hypothesis"],
            "expected": case["expected"],
            "predicted": "error",
            "correct": False,
            "error": str(e)
        }

def main():
    print("=" * 80)
    print("V4.6.2-V4.6.3 阶段验证测试集 - ADHD 和情绪管理关键词匹配")
    print("=" * 80)
    print()
    
    results = []
    
    for i, case in enumerate(TEST_CASES, 1):
        print(f"[{i}/{len(TEST_CASES)}] 测试：{case['hypothesis']}")
        print(f"  输入：{case['input']}")
        result = test_case(case)
        results.append(result)
        
        status = "✅" if result["correct"] else "❌"
        print(f"  {status} 期望：{result['expected']} | 预测：{result['predicted']}")
        print()
    
    # 统计结果
    total_correct = sum(1 for r in results if r["correct"])
    total_accuracy = total_correct / len(results) * 100
    
    print("=" * 80)
    print(f"测试结果：{total_accuracy:.1f}% ({total_correct}/{len(results)})")
    print("=" * 80)
    
    if total_accuracy >= 83:  # 5/6 通过
        print("✅ V4.6.2-V4.6.3 阶段验证通过！")
    else:
        print("❌ V4.6.2-V4.6.3 阶段验证未通过，需要调整关键词")
    
    # 保存详细报告
    report = f"""# V4.6.2-V4.6.3 验证报告

**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**测试版本**: V4.6.3  
**测试案例数**: {len(TEST_CASES)}

## 执行摘要

| 指标 | 结果 |
|------|------|
| **总准确率** | **{total_accuracy:.1f}%** ({total_correct}/{len(results)}) |
| **通过标准** | ≥83% (5/6) |
| **测试状态** | {"✅ 通过" if total_accuracy >= 83 else "❌ 未通过"} |

## 详细测试结果

| # | 假设 | 期望 | 预测 | 状态 |
|---|------|------|------|------|
"""
    
    for i, r in enumerate(results, 1):
        status = "✅" if r["correct"] else "❌"
        report += f"| {i} | {r['hypothesis']} | {r['expected']} | {r['predicted']} | {status} |\n"
    
    report += f"""
## 测试输入详情

"""
    
    for i, (case, r) in enumerate(zip(TEST_CASES, results), 1):
        report += f"""### {i}. {case['hypothesis']}

**输入**: {case['input']}

**期望**: {r['expected']}  
**预测**: {r['predicted']}  
**状态**: {"✅ 正确" if r['correct'] else "❌ 错误"}

**AI 回应**: {r.get('response', r.get('error', 'N/A'))}

---

"""
    
    report_path = f"/home/admin/Desktop/V4.6.2-V4.6.3 验证报告_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n详细报告已保存：{report_path}")

if __name__ == "__main__":
    main()
