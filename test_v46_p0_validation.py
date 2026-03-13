#!/usr/bin/env python3
"""
V4.6.0-P0 阶段验证测试集
测试 6 个新增假设的关键词匹配
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v4"

# 6 个新增假设的验证案例
TEST_CASES = [
    {
        "hypothesis": "H_WORKING_MEMORY",
        "input": "孩子记不住多步骤指令，丢了前一步就接不上",
        "expected": "H_WORKING_MEMORY"
    },
    {
        "hypothesis": "H_SENSORY_OVERLOAD",
        "input": "环境太复杂，信息太多处理不过来，人多就崩溃",
        "expected": "H_SENSORY_OVERLOAD"
    },
    {
        "hypothesis": "H_SUSTAINED_ATTENTION",
        "input": "容易分心，注意力短暂，无法坚持完成任务",
        "expected": "H_SUSTAINED_ATTENTION"
    },
    {
        "hypothesis": "H_VISUAL_PROCESSING",
        "input": "视觉提示无效，看不懂图片，看图困难",
        "expected": "H_VISUAL_PROCESSING"
    },
    {
        "hypothesis": "H_AUDITORY_PROCESSING",
        "input": "听觉提示无效，听不懂指令，听而不闻",
        "expected": "H_AUDITORY_PROCESSING"
    },
    {
        "hypothesis": "H_MOTOR_PLANNING",
        "input": "动作慢，模仿困难，知道但做不出",
        "expected": "H_MOTOR_PLANNING"
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
    print("V4.6.0-P0 阶段验证测试集 - 6 个新增假设关键词匹配")
    print("=" * 80)
    print()
    
    results = []
    
    for i, case in enumerate(TEST_CASES, 1):
        print(f"[{i}/6] 测试：{case['hypothesis']}")
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
        print("✅ P0 阶段验证通过！")
    else:
        print("❌ P0 阶段验证未通过，需要调整关键词")
    
    # 保存详细报告
    report = f"""# V4.6.0-P0 阶段验证报告

**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**测试版本**: V4.6.0-P0  
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
    
    report_path = f"/home/admin/Desktop/V4.6.0-P0 验证报告_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n详细报告已保存：{report_path}")

if __name__ == "__main__":
    main()
