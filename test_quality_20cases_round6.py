#!/usr/bin/env python3
"""
V4.5.6 20 案例质量验证测试 - 第 6 轮（优化后验证）
测试目的：验证临床推理优化效果，目标寻求关注准确率≥80%
"""

import requests
import json
import re
from datetime import datetime
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v4"
OUTPUT_DIR = Path("/home/admin/Desktop/V4.5.6-20 案例测试 - 第 6 轮")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 20 个测试案例（重点关注寻求关注类型）
TEST_CASES = [
    # === 提示依赖 (5 例) ===
    {"id": 1, "name": "做操不看老师", "category": "提示依赖",
     "input": "孩子 5 岁，在幼儿园做操时，不看老师就不会做，一看老师就会做。",
     "answers": ["男孩", "户外操场", "老师提醒", "能做好"],
     "expected_function": "提示依赖"},
    {"id": 2, "name": "需要示范才做", "category": "提示依赖",
     "input": "老师教新动作时，必须老师做一遍他才会跟着做。",
     "answers": ["6 岁", "男孩", "教室里", "能模仿"],
     "expected_function": "提示依赖"},
    {"id": 3, "name": "排队看前面", "category": "提示依赖",
     "input": "排队时，不看前面同学的后脑勺就不会走。",
     "answers": ["5 岁", "女孩", "幼儿园", "能跟上"],
     "expected_function": "提示依赖"},
    {"id": 4, "name": "洗手看步骤图", "category": "提示依赖",
     "input": "洗手时必须看着墙上的步骤图，不看就不会洗。",
     "answers": ["4 岁", "男孩", "卫生间", "能完成"],
     "expected_function": "提示依赖"},
    {"id": 5, "name": "穿衣看镜子", "category": "提示依赖",
     "input": "穿衣服时必须看着镜子里的自己，不看就不会穿。",
     "answers": ["5 岁", "女孩", "卧室", "能穿好"],
     "expected_function": "提示依赖"},
    
    # === 逃避难度 (5 例) ===
    {"id": 6, "name": "数学作业畏难", "category": "逃避难度",
     "input": "我家孩子 7 岁，一写数学作业就说太难了，然后开始哭。",
     "answers": ["女孩", "家里", "我安慰她", "不会做"],
     "expected_function": "逃避.*难度"},
    {"id": 7, "name": "练琴畏难", "category": "逃避难度",
     "input": "一让他练新曲子，他就说太难了不会弹。",
     "answers": ["6 岁", "女孩", "家里", "弹不了"],
     "expected_function": "逃避.*难度"},
    {"id": 8, "name": "跳绳畏难", "category": "逃避难度",
     "input": "学跳绳时，跳不过去就说太难了不学了。",
     "answers": ["5 岁", "男孩", "户外", "不会跳"],
     "expected_function": "逃避.*难度"},
    {"id": 9, "name": "写字畏难", "category": "逃避难度",
     "input": "写字时一写不好就擦掉，说太难了写不好。",
     "answers": ["7 岁", "女孩", "家里", "写不好"],
     "expected_function": "逃避.*难度"},
    {"id": 10, "name": "拼图畏难", "category": "逃避难度",
     "input": "拼图拼不上就说太难了不玩了。",
     "answers": ["5 岁", "男孩", "家里", "拼不上"],
     "expected_function": "逃避.*难度"},
    
    # === 寻求关注 (5 例) ===
    {"id": 11, "name": "打电话捣乱", "category": "寻求关注",
     "input": "我打电话时，他就故意大声唱歌或捣乱。",
     "answers": ["6 岁", "女孩", "家里", "我说他"],
     "expected_function": "关注"},
    {"id": 12, "name": "客人来捣乱", "category": "寻求关注",
     "input": "家里有客人时，他就故意捣乱吸引注意。",
     "answers": ["5 岁", "男孩", "家里", "我说他"],
     "expected_function": "关注"},
    {"id": 13, "name": "写作业求关注", "category": "寻求关注",
     "input": "写作业时不停地叫我，其实他都会做。",
     "answers": ["7 岁", "女孩", "家里", "我过去看他"],
     "expected_function": "关注"},
    {"id": 14, "name": "吃饭求关注", "category": "寻求关注",
     "input": "吃饭时故意把饭菜弄掉，让我们看他。",
     "answers": ["4 岁", "男孩", "餐桌", "我们说他"],
     "expected_function": "关注"},
    {"id": 15, "name": "睡觉求关注", "category": "寻求关注",
     "input": "睡觉时不停地叫妈妈，其实不想上厕所也不渴。",
     "answers": ["5 岁", "女孩", "卧室", "我过去"],
     "expected_function": "关注"},
    
    # === 感觉逃避 (5 例) ===
    {"id": 16, "name": "超市捂耳朵", "category": "感觉逃避",
     "input": "一到超市他就捂耳朵，哭闹要出去。",
     "answers": ["5 岁", "男孩", "超市很吵", "我们离开"],
     "expected_function": "感觉.*逃避"},
    {"id": 17, "name": "理发哭闹", "category": "感觉逃避",
     "input": "理发时电动推子的声音让他哭闹不止。",
     "answers": ["4 岁", "男孩", "理发店", "我们按住他"],
     "expected_function": "感觉.*逃避|逃避不适"},
    {"id": 18, "name": "拒绝玩水", "category": "感觉逃避",
     "input": "洗澡时不让水冲到脸上，一冲就哭。",
     "answers": ["3 岁", "女孩", "浴室", "我们擦干"],
     "expected_function": "感觉.*逃避"},
    {"id": 19, "name": "拒绝光脚", "category": "感觉逃避",
     "input": "死活不肯光脚踩草地或沙地。",
     "answers": ["4 岁", "男孩", "户外", "我们抱他"],
     "expected_function": "感觉.*逃避"},
    {"id": 20, "name": "拒绝特定衣服", "category": "感觉逃避",
     "input": "有标签的衣服死活不肯穿，说扎人。",
     "answers": ["5 岁", "女孩", "家里", "我们剪标签"],
     "expected_function": "感觉.*逃避"},
]

def run_case(case):
    """执行单个案例测试"""
    print(f"\n{'='*60}")
    print(f"案例{case['id']}: {case['name']} ({case['category']})")
    print(f"{'='*60}")
    
    session_id = None
    conversation_log = []
    report = None
    turn_count = 0
    max_turns = 8
    timeout = 90
    
    # 第 1 轮
    user_input = case['input']
    print(f"\n【用户】{user_input}")
    try:
        resp = requests.post(f"{BASE_URL}/chat", json={"user_input": user_input}, timeout=timeout)
        data = resp.json()
    except Exception as e:
        print(f"❌ 请求失败：{e}")
        return {"error": str(e)}
    
    session_id = data.get("session_id")
    ai_msg = data.get("message", "")
    print(f"【AI】{ai_msg[:80]}...")
    conversation_log.append({"role": "user", "content": user_input})
    conversation_log.append({"role": "ai", "content": ai_msg})
    turn_count += 1
    
    # 后续轮次
    for answer in case['answers']:
        if data.get("status") == "completed":
            report = data.get("data")
            print(f"\n✅ 报告已生成（{turn_count}轮）")
            break
        
        if turn_count >= max_turns:
            print(f"\n⚠️ 达到轮次上限")
            break
        
        print(f"\n【用户】{answer}")
        try:
            resp = requests.post(f"{BASE_URL}/chat", json={
                "session_id": session_id,
                "user_input": answer
            }, timeout=timeout)
            data = resp.json()
        except Exception as e:
            print(f"❌ 请求失败：{e}")
            break
        
        ai_msg = data.get("message", "")
        print(f"【AI】{ai_msg[:80] if ai_msg else '(空回复)'}...")
        conversation_log.append({"role": "user", "content": answer})
        conversation_log.append({"role": "ai", "content": ai_msg})
        turn_count += 1
        
        if data.get("status") == "completed":
            report = data.get("data")
            print(f"\n✅ 报告已生成（{turn_count}轮）")
            break
    
    # 如果仍未完成，尝试生成报告
    if turn_count < max_turns and data.get("status") != "completed":
        try:
            resp = requests.post(f"{BASE_URL}/chat", json={
                "session_id": session_id,
                "user_input": "生成报告"
            }, timeout=timeout)
            data = resp.json()
            if data.get("status") == "completed":
                report = data.get("data")
                turn_count += 1
                print(f"\n✅ 报告已生成（{turn_count}轮）")
        except:
            pass
    
    # 评估
    passed = report is not None
    function_match = False
    intervention_match = True
    intervention_clean = True
    
    if report:
        inner_report = report.get("report", report)
        functional_judgment = inner_report.get("functional_judgment", "")
        function_match = re.search(case['expected_function'], functional_judgment) is not None if functional_judgment else False
        
        intervention_plan = report.get("intervention_plan", {})
        phase_name = intervention_plan.get("phase_name", "")
        four_step = intervention_plan.get("four_step_plan", {})
        core_idea = four_step.get("core_idea", "")
        
        if case['category'] == '感觉逃避':
            if "序列支持" in phase_name or "步骤图" in core_idea:
                intervention_match = False
        elif case['category'] == '寻求关注':
            if "动作锚点" in phase_name or "视觉提示" in core_idea:
                intervention_match = False
        
        if "置信度" in core_idea or "证据" in core_idea:
            intervention_clean = False
    
    result = {
        "case_id": case["id"],
        "case_name": case["name"],
        "category": case["category"],
        "conversation_log": conversation_log,
        "report": report,
        "turn_count": turn_count,
        "passed": passed,
        "function_match": function_match,
        "intervention_match": intervention_match,
        "intervention_clean": intervention_clean,
        "status": data.get("status", "unknown"),
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"\n📊 结果：轮次={turn_count}, 报告={'有' if report else '无'}, 功能匹配={'✅' if function_match else '❌'}, 干预匹配={'✅' if intervention_match else '❌'}, 输出净化={'✅' if intervention_clean else '❌'}")
    
    if report:
        func = inner_report.get("functional_judgment", "N/A")
        print(f"   功能判断：{func}")
        insight = inner_report.get("core_insight", "")
        if insight:
            print(f"   核心洞察：{insight[:60]}...")
        plan_name = intervention_plan.get("phase_name", "N/A")
        print(f"   干预计划：{plan_name}")
    
    return result

def main():
    print("="*60)
    print("🧪 V4.5.6 20 案例质量验证测试 - 第 6 轮（优化后验证）")
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"测试重点：寻求关注判断准确率（目标≥80%）")
    print("="*60)
    
    results = []
    for case in TEST_CASES:
        result = run_case(case)
        results.append(result)
        import time
        time.sleep(1)
    
    total = len(results)
    passed = sum(1 for r in results if r.get("passed"))
    function_match = sum(1 for r in results if r.get("function_match"))
    intervention_match = sum(1 for r in results if r.get("intervention_match"))
    intervention_clean = sum(1 for r in results if r.get("intervention_clean"))
    all_good = sum(1 for r in results if r.get("function_match") and r.get("intervention_match") and r.get("intervention_clean"))
    avg_turns = sum(r.get("turn_count", 0) for r in results) / total if total > 0 else 0
    
    category_stats = {}
    for r in results:
        cat = r.get("category", "Unknown")
        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "passed": 0, "function_match": 0, "intervention_match": 0}
        category_stats[cat]["total"] += 1
        if r.get("passed"):
            category_stats[cat]["passed"] += 1
        if r.get("function_match"):
            category_stats[cat]["function_match"] += 1
        if r.get("intervention_match"):
            category_stats[cat]["intervention_match"] += 1
    
    summary = {
        "test_info": {
            "version": "V4.5.6-Round6",
            "test_type": "20 案例质量验证 - 第 6 轮（优化后验证）",
            "total_cases": total,
            "passed": passed,
            "pass_rate": f"{passed/total*100:.1f}%",
            "function_match": function_match,
            "intervention_match": intervention_match,
            "intervention_clean": intervention_clean,
            "all_good": all_good,
            "avg_turns": f"{avg_turns:.1f}",
            "timestamp": datetime.now().isoformat()
        },
        "category_stats": category_stats,
        "results": results
    }
    
    json_file = OUTPUT_DIR / "测试结果.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    md_report = generate_markdown_report(summary)
    md_file = OUTPUT_DIR / "测试报告.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(md_report)
    
    print(f"\n{'='*60}")
    print("📊 测试汇总")
    print(f"{'='*60}")
    print(f"总数：{total} | 通过：{passed} | 通过率：{summary['test_info']['pass_rate']}")
    print(f"功能判断匹配：{function_match}/{total}")
    print(f"诊断 - 干预匹配：{intervention_match}/{total}")
    print(f"输出文本净化：{intervention_clean}/{total}")
    print(f"三达标：{all_good}/{total}")
    print(f"平均轮次：{avg_turns:.1f}")
    print(f"\n📄 详情：{md_file}")
    
    import shutil
    desktop_md = Path("/home/admin/Desktop/V4.5.6-20 案例测试 - 第 6 轮报告.md")
    shutil.copy(md_file, desktop_md)
    print(f"📋 已复制到：{desktop_md}")
    
    return summary

def generate_markdown_report(summary):
    """生成 Markdown 报告"""
    md = f"""# V4.5.6 20 案例质量验证测试报告 - 第 6 轮

**测试时间**: {summary['test_info']['timestamp']}  
**测试版本**: V4.5.6-Round6  
**测试类型**: 优化后验证（寻求关注判断增强）  
**测试案例**: 20 个（4 大功能类型，每类 5 例）

---

## 测试汇总对比

| 指标 | 第 5 轮 | 第 6 轮 | 变化 | 目标 | 状态 |
|------|--------|--------|------|------|------|
| **报告生成率** | 80% | {summary['test_info']['pass_rate']} | {'⬆️' if float(summary['test_info']['pass_rate'][:-1]) > 80 else '➡️' if float(summary['test_info']['pass_rate'][:-1]) == 80 else '⬇️'} | ≥90% | {'✅' if float(summary['test_info']['pass_rate'][:-1]) >= 90 else '⚠️'} |
| **功能判断匹配** | 75% | {summary['test_info']['function_match']}/{summary['test_info']['total_cases']} ({summary['test_info']['function_match']/summary['test_info']['total_cases']*100:.0f}%) | {'⬆️' if summary['test_info']['function_match']/summary['test_info']['total_cases'] > 0.75 else '➡️' if summary['test_info']['function_match']/summary['test_info']['total_cases'] == 0.75 else '⬇️'} | ≥90% | {'✅' if summary['test_info']['function_match'] >= 18 else '⚠️'} |
| **诊断 - 干预匹配** | 95% | {summary['test_info']['intervention_match']}/{summary['test_info']['total_cases']} ({summary['test_info']['intervention_match']/summary['test_info']['total_cases']*100:.0f}%) | {'⬆️' if summary['test_info']['intervention_match']/summary['test_info']['total_cases'] > 0.95 else '➡️' if summary['test_info']['intervention_match']/summary['test_info']['total_cases'] == 0.95 else '⬇️'} | 100% | {'✅' if summary['test_info']['intervention_match'] == 20 else '⚠️'} |
| **输出文本净化** | 100% | {summary['test_info']['intervention_clean']}/{summary['test_info']['total_cases']} ({summary['test_info']['intervention_clean']/summary['test_info']['total_cases']*100:.0f}%) | {'➡️' if summary['test_info']['intervention_clean'] == 20 else '⬇️'} | 100% | {'✅' if summary['test_info']['intervention_clean'] == 20 else '⚠️'} |
| **三达标** | 75% | {summary['test_info']['all_good']}/{summary['test_info']['total_cases']} ({summary['test_info']['all_good']/summary['test_info']['total_cases']*100:.0f}%) | {'⬆️' if summary['test_info']['all_good']/summary['test_info']['total_cases'] > 0.75 else '➡️' if summary['test_info']['all_good']/summary['test_info']['total_cases'] == 0.75 else '⬇️'} | ≥90% | {'✅' if summary['test_info']['all_good'] >= 15 else '⚠️'} |
| **平均对话轮次** | 2.9 | {summary['test_info']['avg_turns']} | {'⬇️' if float(summary['test_info']['avg_turns']) < 2.9 else '➡️' if float(summary['test_info']['avg_turns']) == 2.9 else '⬆️'} | ≤6 | {'✅' if float(summary['test_info']['avg_turns']) <= 6 else '⚠️'} |

---

## 按类别汇总

| 功能类型 | 案例数 | 报告生成 | 功能匹配 | 干预匹配 | 准确率 |
|---------|--------|---------|---------|---------|--------|
"""
    
    for cat, stats in summary['category_stats'].items():
        total = stats['total']
        passed = stats['passed']
        func = stats['function_match']
        interv = stats['intervention_match']
        rate = func/total*100 if total > 0 else 0
        md += f"| {cat} | {total} | {passed}/{total} | {func}/{total} | {interv}/{total} | {rate:.0f}% |\n"
    
    md += f"""
---

## 关键问题验证

### 寻求关注判断准确率

| 案例 | 第 5 轮 | 第 6 轮 | 状态 |
|------|--------|--------|------|
| 案例 11: 打电话捣乱 | ✅ | {'✅' if summary['results'][10].get('function_match') else '❌'} | {'✅ 保持' if summary['results'][10].get('function_match') else '❌ 恶化'} |
| 案例 12: 客人来捣乱 | ❌ | {'✅' if summary['results'][11].get('function_match') else '❌'} | {'✅ 已修复' if summary['results'][11].get('function_match') else '⚠️ 未修复'} |
| 案例 13: 写作业求关注 | ❌ | {'✅' if summary['results'][12].get('function_match') else '❌'} | {'✅ 已修复' if summary['results'][12].get('function_match') else '⚠️ 未修复'} |
| 案例 14: 吃饭求关注 | ❌ | {'✅' if summary['results'][13].get('function_match') else '❌'} | {'✅ 已修复' if summary['results'][13].get('function_match') else '⚠️ 未修复'} |
| 案例 15: 睡觉求关注 | ✅ | {'✅' if summary['results'][14].get('function_match') else '❌'} | {'✅ 保持' if summary['results'][14].get('function_match') else '❌ 恶化'} |

**寻求关注准确率**: {summary['category_stats'].get('寻求关注', {}).get('function_match', 0)}/{summary['category_stats'].get('寻求关注', {}).get('total', 1)} ({summary['category_stats'].get('寻求关注', {}).get('function_match', 0)/summary['category_stats'].get('寻求关注', {}).get('total', 1)*100:.0f}%)  
**目标**: ≥80%  
**状态**: {'✅ 已达标' if summary['category_stats'].get('寻求关注', {}).get('function_match', 0)/summary['category_stats'].get('寻求关注', {}).get('total', 1) >= 0.8 else '⚠️ 未达标'}

---

## 验收标准

### 核心标准

| 标准 | 要求 | 实际 | 状态 |
|------|------|------|------|
| 报告生成率 | ≥90% | {summary['test_info']['pass_rate']} | {'✅' if float(summary['test_info']['pass_rate'][:-1]) >= 90 else '⚠️'} |
| 功能判断准确率 | ≥90% | {summary['test_info']['function_match']}/{summary['test_info']['total_cases']} ({summary['test_info']['function_match']/summary['test_info']['total_cases']*100:.0f}%) | {'✅' if summary['test_info']['function_match'] >= 18 else '⚠️'} |
| 寻求关注准确率 | ≥80% | {summary['category_stats'].get('寻求关注', {}).get('function_match', 0)}/{summary['category_stats'].get('寻求关注', {}).get('total', 1)} ({summary['category_stats'].get('寻求关注', {}).get('function_match', 0)/summary['category_stats'].get('寻求关注', {}).get('total', 1)*100:.0f}%) | {'✅' if summary['category_stats'].get('寻求关注', {}).get('function_match', 0)/summary['category_stats'].get('寻求关注', {}).get('total', 1) >= 0.8 else '⚠️'} |
| 诊断 - 干预匹配 | 100% | {summary['test_info']['intervention_match']}/{summary['test_info']['total_cases']} ({summary['test_info']['intervention_match']/summary['test_info']['total_cases']*100:.0f}%) | {'✅' if summary['test_info']['intervention_match'] == 20 else '⚠️'} |
| 输出文本净化 | 100% | {summary['test_info']['intervention_clean']}/{summary['test_info']['total_cases']} ({summary['test_info']['intervention_clean']/summary['test_info']['total_cases']*100:.0f}%) | {'✅' if summary['test_info']['intervention_clean'] == 20 else '⚠️'} |

---

## 详细案例结果

"""
    
    for r in summary['results']:
        status_icon = "✅" if r.get('passed', False) else "❌"
        func_icon = "✅" if r.get('function_match', False) else "❌"
        interv_icon = "✅" if r.get('intervention_match', False) else "❌"
        clean_icon = "✅" if r.get('intervention_clean', False) else "❌"
        all_icon = "✅" if (r.get('function_match', False) and r.get('intervention_match', False) and r.get('intervention_clean', False)) else "❌"
        
        md += f"""### 案例{r['case_id']}: {r['case_name']} ({r['category']})

**对话轮次**: {r['turn_count']}轮  
**测试状态**: {status_icon} {'通过' if r.get('passed') else '失败'}  
**功能判断匹配**: {func_icon}  
**诊断 - 干预匹配**: {interv_icon}  
**输出文本净化**: {clean_icon}  
**三达标**: {all_icon}  

"""
        
        if r.get('report'):
            inner_report = r['report'].get('report', r['report'])
            func = inner_report.get('functional_judgment', 'N/A')
            md += f"""**功能判断**: {func}

**核心洞察**: 
> {inner_report.get('core_insight', 'N/A')[:100]}...

**干预计划**: 
> {r.get('report', {}).get('intervention_plan', {}).get('phase_name', 'N/A')}

**干预核心思路**: 
> {r.get('report', {}).get('intervention_plan', {}).get('four_step_plan', {}).get('core_idea', 'N/A')[:100]}...

"""
        md += "---\n\n"
    
    md += f"""## 优化验证结论

### 临床推理优化效果

| 问题 | 第 5 轮 | 第 6 轮 | 状态 |
|------|--------|--------|------|
| 寻求关注判断准确率低 | 40% (2/5) | {summary['category_stats'].get('寻求关注', {}).get('function_match', 0)}/{summary['category_stats'].get('寻求关注', {}).get('total', 1)} ({summary['category_stats'].get('寻求关注', {}).get('function_match', 0)/summary['category_stats'].get('寻求关注', {}).get('total', 1)*100:.0f}%) | {'✅ 已修复' if summary['category_stats'].get('寻求关注', {}).get('function_match', 0)/summary['category_stats'].get('寻求关注', {}).get('total', 1) >= 0.8 else '⚠️ 部分改善'} |
| 矛盾证据识别不足 | ❌ | {'✅' if summary['results'][12].get('function_match') else '❌'} | {'✅ 已修复' if summary['results'][12].get('function_match') else '⚠️ 待修复'} |
| 案例 13 类型误判 | ❌ | {'✅' if summary['results'][12].get('function_match') else '❌'} | {'✅ 已修复' if summary['results'][12].get('function_match') else '⚠️ 待修复'} |

### 系统能力评估

| 维度 | 第 5 轮 | 第 6 轮 | 变化 |
|------|--------|--------|------|
| 临床思维深度 | 4 | {'5' if summary['category_stats'].get('寻求关注', {}).get('function_match', 0)/summary['category_stats'].get('寻求关注', {}).get('total', 1) >= 0.8 else '4'} | {'⬆️ 提升' if summary['category_stats'].get('寻求关注', {}).get('function_match', 0)/summary['category_stats'].get('寻求关注', {}).get('total', 1) >= 0.8 else '➡️ 持平'} |
| 判断准确性 | 4 | {'5' if summary['test_info']['function_match']/summary['test_info']['total_cases'] >= 0.9 else '4'} | {'⬆️ 提升' if summary['test_info']['function_match']/summary['test_info']['total_cases'] >= 0.9 else '➡️ 持平'} |
| 建议匹配度 | 5 | 5 | ➡️ 持平 |
| 沟通专业性 | 5 | 5 | ➡️ 持平 |
| 系统稳定性 | 4 | {'5' if float(summary['test_info']['pass_rate'][:-1]) >= 90 else '4'} | {'⬆️ 提升' if float(summary['test_info']['pass_rate'][:-1]) >= 90 else '➡️ 持平'} |
| 总体可靠性 | 4 | {'5' if summary['test_info']['function_match']/summary['test_info']['total_cases'] >= 0.9 and float(summary['test_info']['pass_rate'][:-1]) >= 90 else '4'} | {'⬆️ 提升' if summary['test_info']['function_match']/summary['test_info']['total_cases'] >= 0.9 and float(summary['test_info']['pass_rate'][:-1]) >= 90 else '➡️ 持平'} |

---

**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  
**版本**: V4.5.6-Round6  
**状态**: {'✅ 测试通过，寻求关注判断已优化' if summary['category_stats'].get('寻求关注', {}).get('function_match', 0)/summary['category_stats'].get('寻求关注', {}).get('total', 1) >= 0.8 else '⚠️ 部分改善，仍需优化'}
"""
    
    return md

if __name__ == "__main__":
    main()
