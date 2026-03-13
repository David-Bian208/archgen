#!/usr/bin/env python3
"""
V4.5.3 干预计划逻辑自洽性验证测试
测试目的：验证功能判断与干预计划是否严格匹配
"""

import requests
import json
from datetime import datetime
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v4"
OUTPUT_DIR = Path("/home/admin/Desktop/V4.5.3-干预计划逻辑验证")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 4 个关键案例（覆盖主要功能类型）
TEST_CASES = [
    {
        "id": 1,
        "name": "提示依赖",
        "input": "孩子 5 岁，在幼儿园做操时，不看老师就不会做，一看老师就会做。",
        "expected_function": "提示依赖",
        "expected_intervention": "动作锚点|视觉提示|内化提示",
    },
    {
        "id": 2,
        "name": "逃避难度",
        "input": "我家孩子 7 岁，一写数学作业就说太难了，然后开始哭。",
        "expected_function": "逃避.*难度",
        "expected_intervention": "任务分解 | 降低起点 | 成功体验 | 阶梯",
    },
    {
        "id": 3,
        "name": "寻求关注",
        "input": "我打电话时，他就故意大声唱歌或捣乱。",
        "expected_function": "关注",
        "expected_intervention": "关注重定向 | 差异化关注 | 积极关注",
    },
    {
        "id": 4,
        "name": "感觉逃避",
        "input": "一到超市他就捂耳朵，哭闹要出去。",
        "expected_function": "感觉.*逃避",
        "expected_intervention": "感觉友好 | 环境调整 | 脱敏 | 降噪",
    },
]

import re

def test_case(case):
    """测试单个案例"""
    print(f"\n{'='*60}")
    print(f"案例{case['id']}: {case['name']}")
    print(f"{'='*60}")
    
    # 发送请求
    print(f"\n【用户】{case['input']}")
    try:
        resp = requests.post(f"{BASE_URL}/chat", json={"user_input": case["input"]}, timeout=60)
        data = resp.json()
    except Exception as e:
        print(f"❌ 请求失败：{e}")
        return {"error": str(e)}
    
    # 检查状态
    if data.get("status") != "completed":
        print(f"❌ 状态错误：{data.get('status')}")
        return {"error": "未完成"}
    
    # 提取功能判断
    report_data = data.get("data", {})
    report = report_data.get("report", {})
    functional_judgment = report.get("functional_judgment", "")
    core_insight = report.get("core_insight", "")
    
    print(f"\n📊 功能判断：{functional_judgment}")
    print(f"💡 核心洞察：{core_insight[:80]}...")
    
    # 提取干预计划
    intervention_plan = report_data.get("intervention_plan", {})
    four_step = intervention_plan.get("four_step_plan", {})
    core_idea = four_step.get("core_idea", "")
    our_plan = four_step.get("our_plan", "")
    
    print(f"\n🎯 干预核心思路：{core_idea[:100]}...")
    print(f"📋 干预计划：{our_plan[:100]}...")
    
    # 验证功能判断
    function_match = re.search(case['expected_function'], functional_judgment) is not None
    
    # 验证干预计划
    intervention_match = any(re.search(kw, core_idea + our_plan) for kw in case['expected_intervention'].split('|'))
    
    # 评估
    passed = function_match and intervention_match
    
    result = {
        "case_id": case["id"],
        "case_name": case["name"],
        "functional_judgment": functional_judgment,
        "core_insight": core_insight,
        "intervention_core_idea": core_idea,
        "intervention_plan": our_plan,
        "function_match": function_match,
        "intervention_match": intervention_match,
        "passed": passed,
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"\n{'='*60}")
    print(f"📊 验证结果")
    print(f"{'='*60}")
    print(f"功能判断匹配：{'✅' if function_match else '❌'}")
    print(f"干预计划匹配：{'✅' if intervention_match else '❌'}")
    print(f"逻辑自洽：{'✅ PASS' if passed else '❌ FAIL'}")
    
    return result

def main():
    print("="*60)
    print("🧪 V4.5.3 干预计划逻辑自洽性验证")
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*60)
    
    results = []
    for case in TEST_CASES:
        result = test_case(case)
        results.append(result)
    
    # 汇总
    total = len(results)
    passed = sum(1 for r in results if r.get("passed"))
    function_match = sum(1 for r in results if r.get("function_match"))
    intervention_match = sum(1 for r in results if r.get("intervention_match"))
    
    summary = {
        "test_info": {
            "version": "V4.5.3-LogicFixed",
            "test_type": "干预计划逻辑自洽性验证",
            "total_cases": total,
            "passed": passed,
            "pass_rate": f"{passed/total*100:.1f}%",
            "function_match": function_match,
            "intervention_match": intervention_match,
            "timestamp": datetime.now().isoformat()
        },
        "results": results
    }
    
    # 保存 JSON
    json_file = OUTPUT_DIR / "测试结果.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    # 生成 Markdown 报告
    md_report = generate_markdown_report(summary)
    md_file = OUTPUT_DIR / "测试报告.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(md_report)
    
    # 打印汇总
    print(f"\n{'='*60}")
    print("📊 测试汇总")
    print(f"{'='*60}")
    print(f"总数：{total} | 通过：{passed} | 通过率：{summary['test_info']['pass_rate']}")
    print(f"功能判断匹配：{function_match}/{total}")
    print(f"干预计划匹配：{intervention_match}/{total}")
    print(f"\n📄 详情：{md_file}")
    
    # 复制到桌面
    import shutil
    desktop_md = Path("/home/admin/Desktop/V4.5.3-干预计划逻辑自洽性验证报告.md")
    shutil.copy(md_file, desktop_md)
    print(f"📋 已复制到：{desktop_md}")
    
    return summary

def generate_markdown_report(summary):
    """生成 Markdown 报告"""
    md = f"""# V4.5.3 干预计划逻辑自洽性验证报告

**测试时间**: {summary['test_info']['timestamp']}  
**测试版本**: V4.5.3-LogicFixed  
**测试类型**: 干预计划逻辑自洽性验证  
**测试目的**: 验证功能判断与干预计划是否严格匹配

---

## 测试汇总

| 指标 | 结果 | 目标 | 状态 |
|------|------|------|------|
| **测试案例数** | {summary['test_info']['total_cases']} | 4 | ✅ |
| **通过数** | {summary['test_info']['passed']} | 4 | {'✅' if summary['test_info']['passed'] == 4 else '❌'} |
| **通过率** | {summary['test_info']['pass_rate']} | 100% | {'✅' if summary['test_info']['passed'] == 4 else '❌'} |
| **功能判断匹配** | {summary['test_info']['function_match']}/{summary['test_info']['total_cases']} | 4/4 | {'✅' if summary['test_info']['function_match'] == 4 else '❌'} |
| **干预计划匹配** | {summary['test_info']['intervention_match']}/{summary['test_info']['total_cases']} | 4/4 | {'✅' if summary['test_info']['intervention_match'] == 4 else '❌'} |

**验收标准**: 功能判断与干预计划必须严格匹配（100%）

---

## 案例详情

"""
    
    for r in summary['results']:
        status_icon = "✅" if r['passed'] else "❌"
        md += f"""### 案例{r['case_id']}: {r['case_name']}

**功能判断**: {r['functional_judgment']}  
**功能判断匹配**: {'✅' if r['function_match'] else '❌'}

**核心洞察**: 
> {r['core_insight']}

**干预核心思路**: 
> {r['intervention_core_idea']}

**干预计划**: 
> {r['intervention_plan']}

**干预计划匹配**: {'✅' if r['intervention_match'] else '❌'}

**逻辑自洽**: {status_icon} {'通过' if r['passed'] else '失败'}

---

"""
    
    md += f"""## 修复验证结论

### 修复内容

1. **优先使用 functional_judgment 选择干预模板**
   - 提示依赖 → 动作锚点/视觉提示
   - 逃避难度 → 任务分解/降低起点
   - 寻求关注 → 关注重定向
   - 感觉逃避 → 环境调整/脱敏

2. **narrative 仅用于丰富干预细节，不覆盖功能判断**

3. **添加缺失的干预模板方法**
   - `_generate_sensory_escape_plan()` - 感觉逃避
   - `_generate_self_stimulation_plan()` - 自我刺激
   - `_generate_transition_plan()` - 过渡困难

### 验证结果

| 问题 | 修复前 | 修复后 | 状态 |
|------|--------|--------|------|
| 诊断 - 干预断裂 | 4/4 案例 | 0/4 | {'✅ 已修复' if summary['test_info']['passed'] == 4 else '⚠️ 部分修复'} |
| 功能判断匹配 | - | {summary['test_info']['function_match']}/{summary['test_info']['total_cases']} | {'✅' if summary['test_info']['function_match'] == 4 else '❌'} |
| 干预计划匹配 | - | {summary['test_info']['intervention_match']}/{summary['test_info']['total_cases']} | {'✅' if summary['test_info']['intervention_match'] == 4 else '❌'} |

---

**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  
**版本**: V4.5.3-LogicFixed  
**状态**: {'✅ 修复完成，逻辑自洽' if summary['test_info']['passed'] == 4 else '❌ 仍需修复'}
"""
    
    return md

if __name__ == "__main__":
    main()
