#!/usr/bin/env python3
"""
V4.5.3 10 案例压力测试 - 修复版
"""

import requests
import json
import time
from datetime import datetime
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v4/chat"
OUTPUT_DIR = Path("/home/admin/.openclaw/workspace/behavior_recorder_service/tests/stress_test_10cases")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 10 个测试案例
TEST_CASES = [
    {
        "id": 1, "name": "典型提示依赖",
        "input": "孩子 5 岁，在幼儿园做操时，不看老师就不会做，一看老师就会做。",
        "answers": {
            "age": "5 岁，幼儿园中班",
            "gender": "男孩",
            "setting": "户外操场，有点吵",
            "consequence": "老师偶尔提醒'看这里'",
            "end": "没有了"
        }
    },
    {
        "id": 2, "name": "逃避难度",
        "input": "我家孩子 7 岁，一写数学作业就说'太难了'，然后开始哭。",
        "answers": {
            "age": "7 岁，一年级",
            "gender": "女孩",
            "setting": "在家写作业",
            "consequence": "我给她讲道理，许诺奖励",
            "end": "就这些"
        }
    },
    {
        "id": 3, "name": "感觉逃避",
        "input": "一到超市他就捂耳朵，哭闹要出去。",
        "answers": {
            "age": "5 岁",
            "gender": "男孩",
            "setting": "超市，嘈杂明亮",
            "consequence": "我们通常直接离开",
            "end": "没有了"
        }
    },
    {
        "id": 4, "name": "寻求关注",
        "input": "我打电话时，他就故意大声唱歌或捣乱。",
        "answers": {
            "age": "6 岁",
            "gender": "女孩",
            "setting": "我接电话或专注做事时",
            "consequence": "我会暂停电话说他",
            "end": "就这些"
        }
    },
    {
        "id": 5, "name": "自我刺激",
        "input": "他总是不停地晃手，盯着手看，叫名字没反应。",
        "answers": {
            "age": "4 岁",
            "gender": "男孩",
            "setting": "任何时间地点",
            "consequence": "我们会打断他",
            "end": "没有了"
        }
    },
    {
        "id": 6, "name": "拒绝穿衣",
        "input": "早上不肯穿衣服，挑衣服。",
        "answers": {
            "age": "5 岁",
            "gender": "女孩",
            "setting": "早上在家",
            "consequence": "我会催她，有时妥协",
            "end": "就这些"
        }
    },
    {
        "id": 7, "name": "不会轮流",
        "input": "游戏时不会等，总是抢着来。",
        "answers": {
            "age": "6 岁",
            "gender": "男孩",
            "setting": "和小朋友玩游戏时",
            "consequence": "我会告诉他要有耐心",
            "end": "没有了"
        }
    },
    {
        "id": 8, "name": "眼神回避",
        "input": "说话时不看人，低头或看别处。",
        "answers": {
            "age": "5 岁",
            "gender": "男孩",
            "setting": "和人交流时",
            "consequence": "我会提醒他看人",
            "end": "就这些"
        }
    },
    {
        "id": 9, "name": "完美主义",
        "input": "写字擦来擦去，纸都破了。",
        "answers": {
            "age": "7 岁",
            "gender": "女孩",
            "setting": "写作业时",
            "consequence": "我说差不多就行了",
            "end": "没有了"
        }
    },
    {
        "id": 10, "name": "挑食",
        "input": "只吃白色食物，米饭、面条、馒头。",
        "answers": {
            "age": "5 岁",
            "gender": "男孩",
            "setting": "吃饭时",
            "consequence": "我们会哄他吃别的",
            "end": "就这些"
        }
    },
]

class TestRunner:
    def __init__(self):
        self.results = []
        self.start_time = datetime.now()
    
    def run_case(self, case):
        """执行单个案例"""
        print(f"\n{'='*60}")
        print(f"案例{case['id']}: {case['name']}")
        print(f"{'='*60}")
        
        session_id = None
        conversation_log = []
        report = None
        turn_count = 0
        max_turns = 8
        
        # 第 1 轮
        user_input = case['input']
        print(f"\n【用户】{user_input}")
        response = self._send(session_id, user_input)
        session_id = response.get('session_id')
        ai_msg = response.get('message', '')
        print(f"【AI】{ai_msg[:80]}...")
        conversation_log.append({"role": "user", "content": user_input})
        conversation_log.append({"role": "ai", "content": ai_msg})
        turn_count += 1
        
        # 后续轮次
        answer_keys = ['age', 'gender', 'setting', 'consequence', 'end']
        answer_idx = 0
        
        while response.get('status') != 'completed' and turn_count < max_turns:
            # 智能选择回答
            ai_msg_lower = ai_msg.lower()
            if '几岁' in ai_msg or '年龄' in ai_msg:
                user_input = case['answers']['age']
            elif '男孩' in ai_msg or '女孩' in ai_msg or '性别' in ai_msg:
                user_input = case['answers']['gender']
            elif '环境' in ai_msg or '地方' in ai_msg or '吵' in ai_msg:
                user_input = case['answers']['setting']
            elif '回应' in ai_msg or '反应' in ai_msg or '管' in ai_msg:
                user_input = case['answers']['consequence']
            elif answer_idx < len(answer_keys):
                user_input = case['answers'][answer_keys[answer_idx]]
                answer_idx += 1
            else:
                user_input = case['answers']['end']
            
            print(f"\n【用户】{user_input}")
            response = self._send(session_id, user_input)
            ai_msg = response.get('message', '')
            print(f"【AI】{ai_msg[:80]}...")
            
            conversation_log.append({"role": "user", "content": user_input})
            conversation_log.append({"role": "ai", "content": ai_msg})
            turn_count += 1
            
            if response.get('status') == 'completed':
                break
            
            time.sleep(0.5)
        
        # 获取报告
        if response.get('status') == 'completed' and response.get('data'):
            report = response['data']
            print(f"\n✅ 报告生成完成（{turn_count}轮）")
        
        # 评估
        eval_result = self._evaluate(case, conversation_log, report, turn_count)
        
        # 保存
        result = {
            "case_id": case['id'],
            "case_name": case['name'],
            "conversation_log": conversation_log,
            "report": report,
            "evaluation": eval_result,
            "turn_count": turn_count,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)
        self._save(result)
        
        return result
    
    def _send(self, session_id, user_input):
        payload = {"session_id": session_id, "user_input": user_input}
        try:
            resp = requests.post(BASE_URL, json=payload, timeout=30)
            return resp.json()
        except Exception as e:
            return {"error": str(e), "status": "error"}
    
    def _evaluate(self, case, conv_log, report, turns):
        ev = {
            "A1_empathy": 3, "A2_extraction": 3, "B1_question": 3,
            "B2_turns": turns, "C1_accuracy": 3, "C2_consistency": 3,
            "C3_completeness": 3, "D1_personal": 3, "D2_actionable": 3,
            "passed": False, "issues": []
        }
        
        if not report:
            ev['issues'].append("未生成报告")
            ev['C2_consistency'] = 1
            return ev
        
        # 评估逻辑
        if report.get('context') or report.get('child_behavior'):
            ev['A2_extraction'] = 4
        else:
            ev['issues'].append("信息提取不完整")
        
        if turns <= 4:
            ev['B1_question'] = 5
        elif turns <= 6:
            ev['B1_question'] = 4
        else:
            ev['B1_question'] = 3
        
        if report.get('functional_judgment'):
            ev['C1_accuracy'] = 4
        else:
            ev['issues'].append("功能判断缺失")
        
        if report.get('core_insight') and report.get('intervention_plan'):
            ev['C2_consistency'] = 4
            ev['passed'] = True
        else:
            ev['issues'].append("逻辑不自洽")
        
        fields = ['summary', 'context', 'child_behavior', 'clinical_differential']
        missing = [f for f in fields if not report.get(f)]
        ev['C3_completeness'] = 5 if not missing else 2
        if missing:
            ev['issues'].append(f"缺少：{missing}")
        
        plan = report.get('intervention_plan', {})
        ev['D2_actionable'] = 4 if plan and plan.get('four_step_plan') else 2
        
        return ev
    
    def _save(self, result):
        fn = OUTPUT_DIR / f"case_{result['case_id']:02d}.json"
        with open(fn, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"📄 已保存：{fn}")
    
    def summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r['evaluation']['passed'])
        
        metrics = ['A1_empathy', 'A2_extraction', 'B1_question', 'C1_accuracy', 'C2_consistency', 'C3_completeness', 'D1_personal', 'D2_actionable']
        avgs = {m: sum(r['evaluation'][m] for r in self.results)/total for m in metrics}
        
        issues = []
        for r in self.results:
            for iss in r['evaluation']['issues']:
                issues.append(f"案例{r['case_id']}: {iss}")
        
        summary = {
            "test_info": {
                "total": total, "passed": passed, "failed": total-passed,
                "pass_rate": f"{passed/total*100:.1f}%",
                "avg_turns": sum(r['turn_count'] for r in self.results)/total,
                "start": self.start_time.isoformat(),
                "end": datetime.now().isoformat()
            },
            "averages": avgs,
            "overall": sum(avgs.values())/len(avgs),
            "issues": issues[:20],
            "recommendations": []
        }
        
        if avgs.get('C2_consistency', 0) < 3:
            summary['recommendations'].append("【高】修复逻辑自洽性")
        if avgs.get('B1_question', 0) < 4:
            summary['recommendations'].append("【中】优化提问策略")
        
        fn = OUTPUT_DIR / "summary.json"
        with open(fn, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"\n{'='*60}")
        print("📊 10 案例测试汇总")
        print(f"{'='*60}")
        print(f"总数：{total} | 通过：{passed} | 通过率：{summary['test_info']['pass_rate']}")
        print(f"平均轮次：{summary['test_info']['avg_turns']:.1f}")
        print(f"总体评分：{summary['overall']:.2f}/5.0")
        print(f"\n维度平均分:")
        for m, v in avgs.items():
            print(f"  {m}: {v:.2f}")
        print(f"\n问题:")
        for iss in issues[:10]:
            print(f"  - {iss}")
        print(f"\n📄 详情：{fn}")
        
        return summary

if __name__ == "__main__":
    print("="*60)
    print("🧪 V4.5.3 10 案例压力测试")
    print("="*60)
    
    runner = TestRunner()
    for case in TEST_CASES:
        try:
            runner.run_case(case)
            time.sleep(1)
        except Exception as e:
            print(f"❌ 案例{case['id']}失败：{e}")
    
    runner.summary()
    print(f"\n✅ 完成！")
