#!/usr/bin/env python3
"""
V4.5.3 修复后 10 案例验证测试
测试目的：验证修复效果，确保无重复提问
"""

import requests
import json
from datetime import datetime
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v4"
OUTPUT_DIR = Path("/home/admin/Desktop/10 案例修复验证测试")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 10 个测试案例
TEST_CASES = [
    {"id": 1, "name": "典型提示依赖", "input": "孩子 5 岁，在幼儿园做操时，不看老师就不会做，一看老师就会做。", "answers": ["男孩", "户外操场", "老师提醒", "没有了"]},
    {"id": 2, "name": "逃避难度", "input": "我家孩子 7 岁，一写数学作业就说太难了，然后开始哭。", "answers": ["女孩", "在家", "我安慰她", "就这些"]},
    {"id": 3, "name": "感觉逃避", "input": "一到超市他就捂耳朵，哭闹要出去。", "answers": ["5 岁", "男孩", "很吵", "我们离开", "没有了"]},
    {"id": 4, "name": "寻求关注", "input": "我打电话时，他就故意大声唱歌或捣乱。", "answers": ["6 岁", "女孩", "家里", "我说他", "没有了"]},
    {"id": 5, "name": "自我刺激", "input": "他总是不停地晃手，盯着手看，叫名字没反应。", "answers": ["4 岁", "男孩", "任何时间", "我们打断他", "没有了"]},
    {"id": 6, "name": "拒绝穿衣", "input": "早上不肯穿衣服，挑衣服。", "answers": ["5 岁", "女孩", "家里", "我催她", "就这些"]},
    {"id": 7, "name": "不会轮流", "input": "游戏时不会等，总是抢着来。", "answers": ["6 岁", "男孩", "和小朋友玩", "我告诉他要有耐心", "没有了"]},
    {"id": 8, "name": "眼神回避", "input": "说话时不看人，低头或看别处。", "answers": ["5 岁", "男孩", "和人交流时", "我提醒他看人", "就这些"]},
    {"id": 9, "name": "完美主义", "input": "写字擦来擦去，纸都破了。", "answers": ["7 岁", "女孩", "写作业时", "我说差不多就行了", "没有了"]},
    {"id": 10, "name": "挑食", "input": "只吃白色食物，米饭、面条、馒头。", "answers": ["5 岁", "男孩", "吃饭时", "我们哄他吃别的", "就这些"]},
]

def run_case(case):
    """执行单个案例"""
    print(f"\n{'='*60}")
    print(f"案例{case['id']}: {case['name']}")
    print(f"{'='*60}")
    
    session_id = None
    conversation_log = []
    report = None
    turn_count = 0
    max_turns = 8
    timeout = 60
    
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
    print(f"【AI】{ai_msg[:100]}...")
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
        print(f"【AI】{ai_msg[:100] if ai_msg else '(空回复)'}...")
        conversation_log.append({"role": "user", "content": answer})
        conversation_log.append({"role": "ai", "content": ai_msg})
        turn_count += 1
        
        if data.get("status") == "completed":
            report = data.get("data")
            print(f"\n✅ 报告已生成（{turn_count}轮）")
            break
    
    # 评估
    passed = report is not None and turn_count <= 6
    repeated_question = check_repeated_questions(conversation_log)
    
    result = {
        "case_id": case["id"],
        "case_name": case["name"],
        "conversation_log": conversation_log,
        "report": report,
        "turn_count": turn_count,
        "passed": passed,
        "repeated_question": repeated_question,
        "status": data.get("status", "unknown"),
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"\n📊 结果：轮次={turn_count}, 报告={'有' if report else '无'}, 重复提问={'❌' if repeated_question else '✅'}, 通过={'✅' if passed else '❌'}")
    
    if report:
        func = report.get("functional_judgment", "N/A")
        print(f"   功能判断：{func}")
        insight = report.get("core_insight", "")
        if insight:
            print(f"   核心洞察：{insight[:60]}...")
    
    return result

def check_repeated_questions(conv_log):
    """检查是否有重复提问"""
    ai_messages = [msg["content"] for msg in conv_log if msg["role"] == "ai"]
    seen = set()
    for msg in ai_messages:
        # 简化消息进行比较
        simplified = msg[:50] if len(msg) > 50 else msg
        if simplified in seen:
            return True
        seen.add(simplified)
    return False

def main():
    print("="*60)
    print("🧪 V4.5.3 修复后 10 案例验证测试")
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*60)
    
    results = []
    for case in TEST_CASES:
        result = run_case(case)
        results.append(result)
        import time
        time.sleep(1)
    
    # 汇总
    total = len(results)
    passed = sum(1 for r in results if r.get("passed"))
    with_report = sum(1 for r in results if r.get("report"))
    no_repeat = sum(1 for r in results if not r.get("repeated_question"))
    avg_turns = sum(r.get("turn_count", 0) for r in results) / total if total > 0 else 0
    
    summary = {
        "test_info": {
            "version": "V4.5.3-Fixed",
            "test_type": "修复验证",
            "total_cases": total,
            "passed": passed,
            "pass_rate": f"{passed/total*100:.1f}%",
            "with_report": with_report,
            "no_repeated_question": no_repeat,
            "avg_turns": f"{avg_turns:.1f}",
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
    print(f"有报告：{with_report}/{total}")
    print(f"无重复提问：{no_repeat}/{total}")
    print(f"平均轮次：{avg_turns:.1f}")
    print(f"\n📄 详情：{md_file}")
    
    # 复制到桌面
    import shutil
    desktop_md = Path("/home/admin/Desktop/10 案例修复验证测试报告.md")
    shutil.copy(md_file, desktop_md)
    print(f"📋 已复制到：{desktop_md}")
    
    return summary

def generate_markdown_report(summary):
    """生成 Markdown 报告"""
    md = f"""# V4.5.3 修复后 10 案例验证测试报告

**测试时间**: {summary['test_info']['timestamp']}  
**测试版本**: V4.5.3-Fixed  
**测试类型**: 修复验证（无重复提问）  
**修复内容**: 添加规则匹配 fallback 机制

---

## 测试汇总

| 指标 | 结果 | 目标 | 状态 |
|------|------|------|------|
| **测试案例数** | {summary['test_info']['total_cases']} | 10 | ✅ |
| **报告生成数** | {summary['test_info']['with_report']} | ≥8 | {'✅' if summary['test_info']['with_report'] >= 8 else '⚠️'} |
| **报告生成率** | {summary['test_info']['pass_rate']} | ≥80% | {'✅' if float(summary['test_info']['pass_rate'][:-1]) >= 80 else '⚠️'} |
| **无重复提问** | {summary['test_info']['no_repeated_question']}/{summary['test_info']['total_cases']} | 10/10 | {'✅' if summary['test_info']['no_repeated_question'] == 10 else '❌'} |
| **平均轮次** | {summary['test_info']['avg_turns']} | ≤5 | {'✅' if float(summary['test_info']['avg_turns']) <= 5 else '⚠️'} |

---

## 案例详情

"""
    
    for r in summary['results']:
        status_icon = "✅" if r['passed'] else "❌"
        repeat_icon = "❌" if r.get('repeated_question') else "✅"
        md += f"""### 案例{r['case_id']}: {r['case_name']}

**对话轮次**: {r['turn_count']}轮  
**测试状态**: {status_icon} {'通过' if r['passed'] else '失败'}  
**重复提问**: {repeat_icon} {'有' if r.get('repeated_question') else '无'}  

"""
        
        if r.get('report'):
            report = r['report']
            md += f"""**功能判断**: {report.get('functional_judgment', 'N/A')}

**核心洞察**: 
> {report.get('core_insight', 'N/A')[:100]}...

"""
        md += "---\n\n"
    
    md += f"""## 修复验证结论

### 修复效果

| 问题 | 修复前 | 修复后 | 状态 |
|------|--------|--------|------|
| 重复提问 | 7/10 案例 | {summary['test_info']['total_cases'] - summary['test_info']['no_repeated_question']}/{summary['test_info']['total_cases']} | {'✅ 已修复' if summary['test_info']['no_repeated_question'] == 10 else '⚠️ 部分修复'} |
| 平均轮次 | 6.2 轮 | {summary['test_info']['avg_turns']} 轮 | {'✅ 改善' if float(summary['test_info']['avg_turns']) < 6.2 else '⚠️ 无改善'} |
| 报告生成率 | 100% | {summary['test_info']['pass_rate']} | {'✅ 保持' if float(summary['test_info']['pass_rate'][:-1]) >= 90 else '❌ 下降'} |

### 修复内容

1. **添加规则匹配 fallback**: 确保简单回答（"5 岁"、"男孩"）能被正确提取
2. **增加字段确认日志**: 每次填充后记录确认信息
3. **优化 LLM 提示词**: 简化提取逻辑

---

**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  
**版本**: V4.5.3-Fixed
"""
    
    return md

if __name__ == "__main__":
    main()
