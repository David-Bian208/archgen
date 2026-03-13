#!/usr/bin/env python3
"""
V4.5.3 10 案例质量验证测试
测试目的：验证系统回答质量和报告生成能力
超时设置：60 秒（充足时间等待 LLM 响应）
"""

import requests
import json
from datetime import datetime
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v4"
OUTPUT_DIR = Path("/home/admin/Desktop/10 案例质量测试")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 10 个测试案例（简化回答策略）
TEST_CASES = [
    {
        "id": 1, "name": "典型提示依赖",
        "input": "孩子 5 岁，在幼儿园做操时，不看老师就不会做，一看老师就会做。",
        "expected_function": "提示依赖"
    },
    {
        "id": 2, "name": "逃避难度",
        "input": "我家孩子 7 岁，一写数学作业就说太难了，然后开始哭。",
        "expected_function": "逃避难度"
    },
    {
        "id": 3, "name": "感觉逃避",
        "input": "一到超市他就捂耳朵，哭闹要出去。",
        "expected_function": "感觉逃避"
    },
    {
        "id": 4, "name": "寻求关注",
        "input": "我打电话时，他就故意大声唱歌或捣乱。",
        "expected_function": "寻求关注"
    },
    {
        "id": 5, "name": "自我刺激",
        "input": "他总是不停地晃手，盯着手看，叫名字没反应。",
        "expected_function": "自我刺激/自动强化"
    },
    {
        "id": 6, "name": "拒绝穿衣",
        "input": "早上不肯穿衣服，挑衣服。",
        "expected_function": "过渡困难/逃避"
    },
    {
        "id": 7, "name": "不会轮流",
        "input": "游戏时不会等，总是抢着来。",
        "expected_function": "社交技能缺陷"
    },
    {
        "id": 8, "name": "眼神回避",
        "input": "说话时不看人，低头或看别处。",
        "expected_function": "社交注意缺陷"
    },
    {
        "id": 9, "name": "完美主义",
        "input": "写字擦来擦去，纸都破了。",
        "expected_function": "焦虑/僵化思维"
    },
    {
        "id": 10, "name": "挑食",
        "input": "只吃白色食物，米饭、面条、馒头。",
        "expected_function": "感觉敏感"
    },
]

def run_case(case):
    """执行单个案例测试"""
    print(f"\n{'='*60}")
    print(f"案例{case['id']}: {case['name']}")
    print(f"预期功能：{case['expected_function']}")
    print(f"{'='*60}")
    
    session_id = None
    conversation_log = []
    report = None
    turn_count = 0
    max_turns = 10  # 增加轮次上限
    timeout = 60  # 60 秒超时
    
    # 第 1 轮
    user_input = case['input']
    print(f"\n【用户】{user_input}")
    try:
        resp = requests.post(f"{BASE_URL}/chat", json={"user_input": user_input}, timeout=timeout)
        data = resp.json()
    except Exception as e:
        print(f"❌ 请求失败：{e}")
        return {"error": str(e), "case_id": case['id']}
    
    session_id = data.get("session_id")
    ai_msg = data.get("message", "")
    print(f"【AI】{ai_msg[:100]}...")
    conversation_log.append({"role": "user", "content": user_input})
    conversation_log.append({"role": "ai", "content": ai_msg})
    turn_count += 1
    
    # 智能回答策略
    answers_pool = [
        "男孩", "女孩",  # 性别
        "5 岁", "6 岁", "7 岁",  # 年龄
        "幼儿园", "家里", "学校", "超市",  # 环境
        "老师提醒", "我安慰他", "我们离开了", "我给他了",  # 后果
        "没有了", "就这些",  # 结束
    ]
    
    answer_idx = 0
    
    # 后续轮次
    while turn_count < max_turns:
        if data.get("status") == "completed":
            report = data.get("data")
            print(f"\n✅ 报告已生成（{turn_count}轮）")
            break
        
        # 选择回答
        if answer_idx < len(answers_pool):
            user_input = answers_pool[answer_idx]
            answer_idx += 1
        else:
            user_input = "没有了"
        
        print(f"\n【用户】{user_input}")
        try:
            resp = requests.post(f"{BASE_URL}/chat", json={
                "session_id": session_id,
                "user_input": user_input
            }, timeout=timeout)
            data = resp.json()
        except Exception as e:
            print(f"❌ 请求失败：{e}")
            break
        
        ai_msg = data.get("message", "")
        print(f"【AI】{ai_msg[:100] if ai_msg else '(空回复)'}...")
        conversation_log.append({"role": "user", "content": user_input})
        conversation_log.append({"role": "ai", "content": ai_msg})
        turn_count += 1
        
        if data.get("status") == "completed":
            report = data.get("data")
            print(f"\n✅ 报告已生成（{turn_count}轮）")
            break
    
    # 如果达到轮次上限仍未完成，检查是否有报告
    if turn_count >= max_turns and not report:
        print(f"\n⚠️ 达到轮次上限（{max_turns}轮），尝试获取报告...")
        # 再试一轮
        try:
            resp = requests.post(f"{BASE_URL}/chat", json={
                "session_id": session_id,
                "user_input": "生成报告"
            }, timeout=timeout)
            data = resp.json()
            if data.get("status") == "completed":
                report = data.get("data")
                turn_count += 1
                print(f"✅ 报告已生成（{turn_count}轮）")
        except:
            pass
    
    # 评估
    passed = report is not None
    function_match = False
    if report and report.get("functional_judgment"):
        func = report["functional_judgment"]
        # 简单匹配预期功能
        expected = case['expected_function']
        if expected in func or func in expected:
            function_match = True
    
    result = {
        "case_id": case["id"],
        "case_name": case["name"],
        "expected_function": case["expected_function"],
        "conversation_log": conversation_log,
        "report": report,
        "turn_count": turn_count,
        "passed": passed,
        "function_match": function_match,
        "status": data.get("status", "unknown"),
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"\n📊 结果：轮次={turn_count}, 报告={'有' if report else '无'}, 通过={'✅' if passed else '❌'}")
    
    if report:
        func = report.get("functional_judgment", "N/A")
        print(f"   功能判断：{func}")
        insight = report.get("core_insight", "")
        if insight:
            print(f"   核心洞察：{insight[:60]}...")
    
    return result

def main():
    print("="*60)
    print("🧪 V4.5.3 10 案例质量验证测试")
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"超时设置：60 秒")
    print(f"最大轮次：10 轮")
    print("="*60)
    
    results = []
    for case in TEST_CASES:
        result = run_case(case)
        results.append(result)
        # 案例间等待 1 秒
        import time
        time.sleep(1)
    
    # 汇总
    total = len(results)
    passed = sum(1 for r in results if r.get("passed"))
    with_report = sum(1 for r in results if r.get("report"))
    func_match = sum(1 for r in results if r.get("function_match"))
    avg_turns = sum(r.get("turn_count", 0) for r in results) / total if total > 0 else 0
    
    # 详细汇总
    summary = {
        "test_info": {
            "version": "V4.5.3",
            "test_type": "质量验证",
            "total_cases": total,
            "passed": passed,
            "pass_rate": f"{passed/total*100:.1f}%" if total > 0 else "N/A",
            "with_report": with_report,
            "function_match": func_match,
            "avg_turns": f"{avg_turns:.1f}",
            "timestamp": datetime.now().isoformat()
        },
        "results": results
    }
    
    # 保存汇总
    summary_file = OUTPUT_DIR / "汇总报告.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    # 生成 Markdown 报告
    md_report = generate_markdown_report(summary)
    md_file = OUTPUT_DIR / "汇总报告.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(md_report)
    
    # 打印汇总
    print(f"\n{'='*60}")
    print("📊 测试汇总")
    print(f"{'='*60}")
    print(f"总数：{total} | 通过：{passed} | 通过率：{summary['test_info']['pass_rate']}")
    print(f"有报告：{with_report}/{total}")
    print(f"功能匹配：{func_match}/{total}")
    print(f"平均轮次：{avg_turns:.1f}")
    print(f"\n📄 详情：{md_file}")
    
    # 复制到桌面
    import shutil
    desktop_md = Path("/home/admin/Desktop/10 案例质量测试报告.md")
    shutil.copy(md_file, desktop_md)
    print(f"📋 已复制到：{desktop_md}")
    
    return summary

def generate_markdown_report(summary):
    """生成 Markdown 格式报告"""
    md = f"""# V4.5.3 十案例质量验证测试报告

**测试时间**: {summary['test_info']['timestamp']}  
**测试版本**: V4.5.3  
**测试类型**: 质量验证（非压力测试）  
**超时设置**: 60 秒  
**最大轮次**: 10 轮

---

## 测试汇总

| 指标 | 结果 | 说明 |
|------|------|------|
| **测试案例数** | {summary['test_info']['total_cases']} | 10 个标准化案例 |
| **通过数** | {summary['test_info']['passed']} | 生成报告即为通过 |
| **通过率** | {summary['test_info']['pass_rate']} | 目标≥80% |
| **有报告** | {summary['test_info']['with_report']}/{summary['test_info']['total_cases']} | 报告生成能力 |
| **功能匹配** | {summary['test_info']['function_match']}/{summary['test_info']['total_cases']} | 功能判断准确性 |
| **平均轮次** | {summary['test_info']['avg_turns']} | 对话效率 |

---

## 案例详情

"""
    
    for r in summary['results']:
        md += f"""### 案例{r['case_id']}: {r['case_name']}

**预期功能**: {r['expected_function']}  
**对话轮次**: {r['turn_count']}轮  
**测试状态**: {'✅ 通过' if r['passed'] else '❌ 失败'}  
**功能匹配**: {'✅ 匹配' if r.get('function_match') else '⚠️ 不匹配/无报告'}

"""
        
        if r.get('report'):
            report = r['report']
            md += f"""**功能判断**: {report.get('functional_judgment', 'N/A')}

**核心洞察**: 
> {report.get('core_insight', 'N/A')}

**干预计划**: 
"""
            plan = report.get('intervention_plan', {})
            if plan and plan.get('four_step_plan'):
                for i, step in enumerate(plan['four_step_plan'][:3], 1):
                    md += f"{i}. {step.get('action', 'N/A')}\n"
        else:
            md += "**报告**: 未生成\n"
        
        md += "\n---\n\n"
    
    md += f"""## 结论

### 系统能力验证

| 能力 | 状态 | 说明 |
|------|------|------|
| 会话管理 | {'✅' if summary['test_info']['with_report'] > 0 else '❌'} | 会话创建和维持 |
| 信息提取 | {'✅' if summary['test_info']['with_report'] > 0 else '❌'} | 字段填充能力 |
| 工作流推进 | {'✅' if summary['test_info']['avg_turns'] < 8 else '⚠️'} | 对话收敛能力 |
| 报告生成 | {'✅' if summary['test_info']['with_report'] > 8 else '⚠️'} | 核心功能 |
| 功能判断 | {'✅' if summary['test_info']['function_match'] > 5 else '⚠️'} | 临床准确性 |

### 改进建议

"""
    
    if summary['test_info']['with_report'] < 8:
        md += "- ⚠️ 报告生成率偏低，建议检查工作流决策逻辑\n"
    if float(summary['test_info']['avg_turns']) > 6:
        md += "- ⚠️ 平均轮次偏多，建议优化必填字段检测\n"
    if summary['test_info']['function_match'] < 5:
        md += "- ⚠️ 功能判断准确率偏低，建议优化推理引擎\n"
    
    md += f"""
---

**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  
**测试工具**: test_quality_10cases.py  
**版本**: V4.5.3
"""
    
    return md

if __name__ == "__main__":
    main()
