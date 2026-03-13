#!/usr/bin/env python3
"""
V4.5.9 5 案例深度诊断测试
测试目的：逐个分析 5 个持续失败案例，定位对话卡顿根因
"""

import requests
import json
from datetime import datetime
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v4"
OUTPUT_DIR = Path("/home/admin/Desktop/V4.5.9-5 案例深度诊断")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 5 个持续失败案例
FAILING_CASES = [
    {"id": 2, "name": "需要示范才做", "category": "提示依赖",
     "input": "老师教新动作时，必须老师做一遍他才会跟着做。",
     "answers": ["6 岁", "男孩", "教室里", "能模仿"]},
    {"id": 5, "name": "穿衣看镜子", "category": "提示依赖",
     "input": "穿衣服时必须看着镜子里的自己，不看就不会穿。",
     "answers": ["5 岁", "女孩", "卧室", "能穿好"]},
    {"id": 12, "name": "客人来捣乱", "category": "寻求关注",
     "input": "家里有客人时，他就故意捣乱吸引注意。",
     "answers": ["5 岁", "男孩", "家里", "我说他"]},
    {"id": 13, "name": "写作业求关注", "category": "寻求关注",
     "input": "写作业时不停地叫我，其实他都会做。",
     "answers": ["7 岁", "女孩", "家里", "我过去看他"]},
    {"id": 19, "name": "拒绝光脚", "category": "感觉逃避",
     "input": "死活不肯光脚踩草地或沙地。",
     "answers": ["4 岁", "男孩", "户外", "我们抱他"]},
]

def run_case(case):
    """执行单个案例测试，详细记录对话"""
    print(f"\n{'='*60}")
    print(f"案例{case['id']}: {case['name']} ({case['category']})")
    print(f"{'='*60}")
    
    session_id = None
    conversation_log = []
    report = None
    turn_count = 0
    max_turns = 10  # 增加到 10 轮
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
    print(f"【AI】{ai_msg[:100]}...")
    conversation_log.append({"role": "user", "content": user_input})
    conversation_log.append({"role": "ai", "content": ai_msg, "status": data.get("status")})
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
        conversation_log.append({"role": "ai", "content": ai_msg, "status": data.get("status")})
        turn_count += 1
        
        if data.get("status") == "completed":
            report = data.get("data")
            print(f"\n✅ 报告已生成（{turn_count}轮）")
            break
    
    # 如果仍未完成，尝试生成报告
    if turn_count < max_turns and data.get("status") != "completed":
        try:
            print(f"\n【用户】生成报告")
            resp = requests.post(f"{BASE_URL}/chat", json={
                "session_id": session_id,
                "user_input": "生成报告"
            }, timeout=timeout)
            data = resp.json()
            if data.get("status") == "completed":
                report = data.get("data")
                turn_count += 1
                print(f"\n✅ 报告已生成（{turn_count}轮）")
            else:
                print(f"\n❌ 无法生成报告，状态：{data.get('status')}")
        except Exception as e:
            print(f"\n❌ 请求失败：{e}")
    
    # 评估
    passed = report is not None
    
    result = {
        "case_id": case["id"],
        "case_name": case["name"],
        "category": case["category"],
        "conversation_log": conversation_log,
        "report": report,
        "turn_count": turn_count,
        "passed": passed,
        "status": data.get("status", "unknown"),
        "timestamp": datetime.now().isoformat(),
        "diagnosis": diagnose_failure(conversation_log, data)
    }
    
    print(f"\n📊 结果：轮次={turn_count}, 报告={'有' if report else '无'}, 通过={'✅' if passed else '❌'}")
    print(f"🔍 诊断：{result['diagnosis']}")
    
    if report:
        inner_report = report.get("report", report)
        func = inner_report.get("functional_judgment", "N/A")
        print(f"   功能判断：{func}")
    
    return result

def diagnose_failure(conv_log, final_data):
    """诊断失败原因"""
    if final_data.get("status") == "completed":
        return "✅ 成功"
    
    # 检查是否重复提问
    ai_messages = [msg["content"] for msg in conv_log if msg.get("role") == "ai"]
    if len(ai_messages) >= 3:
        # 检查是否有重复问题
        for i in range(len(ai_messages) - 2):
            if ai_messages[i][:50] == ai_messages[i+1][:50] == ai_messages[i+2][:50]:
                return f"❌ 重复提问循环（第{i+1}-{i+3}轮）"
    
    # 检查是否字段未填充
    if len(conv_log) >= 6:
        return "⚠️ 字段填充失败或工作流决策错误"
    
    return "⚠️ 未知原因"

def main():
    print("="*60)
    print("🧪 V4.5.9 5 案例深度诊断测试")
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("测试重点：定位对话卡顿根因")
    print("="*60)
    
    results = []
    for case in FAILING_CASES:
        result = run_case(case)
        results.append(result)
        import time
        time.sleep(2)  # 案例间等待
    
    # 汇总
    total = len(results)
    passed = sum(1 for r in results if r.get("passed"))
    
    summary = {
        "test_info": {
            "version": "V4.5.9-Round8",
            "test_type": "5 案例深度诊断",
            "total_cases": total,
            "passed": passed,
            "pass_rate": f"{passed/total*100:.1f}%",
            "timestamp": datetime.now().isoformat()
        },
        "results": results
    }
    
    # 保存 JSON
    json_file = OUTPUT_DIR / "诊断结果.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    # 生成 Markdown 报告
    md_report = generate_markdown_report(summary)
    md_file = OUTPUT_DIR / "诊断报告.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(md_report)
    
    print(f"\n{'='*60}")
    print("📊 诊断汇总")
    print(f"{'='*60}")
    print(f"总数：{total} | 通过：{passed} | 通过率：{summary['test_info']['pass_rate']}")
    print(f"\n📄 详情：{md_file}")
    
    import shutil
    desktop_md = Path("/home/admin/Desktop/V4.5.9-5 案例深度诊断报告.md")
    shutil.copy(md_file, desktop_md)
    print(f"📋 已复制到：{desktop_md}")
    
    return summary

def generate_markdown_report(summary):
    """生成 Markdown 诊断报告"""
    md = f"""# V4.5.9 5 案例深度诊断报告

**测试时间**: {summary['test_info']['timestamp']}  
**测试版本**: V4.5.9-Round8  
**测试类型**: 5 案例深度诊断（定位对话卡顿根因）  
**测试案例**: 5 个（持续失败案例）

---

## 诊断汇总

| 指标 | 结果 | 说明 |
|------|------|------|
| **测试案例数** | {summary['test_info']['total_cases']} | 持续失败案例 |
| **通过数** | {summary['test_info']['passed']} | 生成报告的案例 |
| **通过率** | {summary['test_info']['pass_rate']} | 当前水平 |

---

## 逐个案例诊断

"""
    
    for r in summary['results']:
        md += f"""### 案例{r['case_id']}: {r['case_name']} ({r['category']})

**对话轮次**: {r['turn_count']}轮  
**测试状态**: {'✅ 通过' if r.get('passed') else '❌ 失败'}  
**诊断结果**: {r.get('diagnosis', 'N/A')}

**对话日志**:
"""
        for i, msg in enumerate(r['conversation_log'][:12], 1):  # 只显示前 12 条
            role = "用户" if msg['role'] == 'user' else "AI"
            content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
            md += f"{i}. **{role}**: {content}\n"
        
        if len(r['conversation_log']) > 12:
            md += f"...（还有{len(r['conversation_log'])-12}条）\n"
        
        md += "\n---\n\n"
    
    md += f"""## 根因分析

### 共同问题

"""
    
    # 分析共同问题
    failure_reasons = [r.get('diagnosis', '') for r in summary['results'] if not r.get('passed')]
    if any('重复提问' in reason for reason in failure_reasons):
        md += "1. **重复提问循环**: 部分案例陷入重复提问同一字段的死循环\n"
    if any('字段填充' in reason for reason in failure_reasons):
        md += "2. **字段填充失败**: `is_field_filled()` 判断可能有问题\n"
    if any('未知' in reason for reason in failure_reasons):
        md += "3. **未知原因**: 需要更详细的 DEBUG 日志\n"
    
    md += f"""
### 建议修复方向

1. **优化 `_decide_next_action()` 逻辑**:
   - 增加已问字段跟踪，避免重复提问
   - 增强对非标准回答的容错性

2. **修复 `is_field_filled()` 判断**:
   - 确保字段填充后被正确识别
   - 增加 DEBUG 日志

3. **增强 `_rule_based_extraction()` 容错性**:
   - 处理更多自然语言变体
   - 增加纯数字回答处理（V4.5.8 已部分修复）

---

## 下一步行动

### P0: 根治对话流程卡顿

- [ ] 为 5 个失败案例增加全链路 DEBUG 日志
- [ ] 重点审查 `_decide_next_action()` 函数
- [ ] 优化状态机逻辑，支持"答非所问"场景
- [ ] 增强 `_rule_based_extraction()` 容错性

### 验收标准

- [ ] 5 个失败案例全部能够完成对话并生成报告
- [ ] 其他案例不出现倒退

---

**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  
**版本**: V4.5.9-Round8  
**状态**: {'✅ 部分修复' if summary['test_info']['passed'] > 0 else '❌ 仍需修复'}
"""
    
    return md

if __name__ == "__main__":
    main()
