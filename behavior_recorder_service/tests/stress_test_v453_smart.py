#!/usr/bin/env python3
"""
V4.5.3 智能压力测试框架 - 根据 AI 问题动态回答
"""

import requests
import json
import time
from datetime import datetime
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v4/chat"
OUTPUT_DIR = Path("/home/admin/.openclaw/workspace/behavior_recorder_service/tests/stress_test_results_v2")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 测试案例集（精简版 5 个案例）
TEST_CASES = [
    {
        "id": 1,
        "name": "典型提示依赖（视觉）",
        "first_input": "孩子 5 岁，在幼儿园做操时，不看老师就不会做，一看老师就会做。",
        "background": {
            "age": "5 岁",
            "setting": "幼儿园户外操场，有点吵",
            "behavior": "不看老师就发呆，看老师就会做",
            "consequence": "老师偶尔提醒'看这里'",
            "pattern": "老师走到旁边就发呆"
        },
        "expected_logic": "视觉提示依赖 → 工作记忆/持续性注意 → 建立内部动作提示"
    },
    {
        "id": 2,
        "name": "典型逃避难度",
        "first_input": "我家孩子 7 岁，一写数学作业就说'太难了'，然后开始哭。",
        "background": {
            "age": "7 岁",
            "setting": "在家写作业",
            "behavior": "说太难了，哭闹不肯做",
            "consequence": "家长讲道理、许诺奖励",
            "pattern": "遇到应用题就抗拒"
        },
        "expected_logic": "逃避任务难度 → 任务理解/挫折耐受 → 任务分解与降低起点"
    },
    {
        "id": 3,
        "name": "感觉逃避",
        "first_input": "一到超市他就捂耳朵，哭闹要出去。",
        "background": {
            "age": "5 岁",
            "setting": "超市，嘈杂明亮",
            "behavior": "捂耳朵、哭闹要出去",
            "consequence": "家长通常直接离开",
            "pattern": "离开后很快平静"
        },
        "expected_logic": "感觉逃避（听觉/视觉超载）→ 环境调整与脱敏"
    },
    {
        "id": 4,
        "name": "寻求关注",
        "first_input": "我打电话时，他就故意大声唱歌或捣乱。",
        "background": {
            "age": "6 岁",
            "setting": "妈妈接电话或专注做事时",
            "behavior": "故意大声唱歌或捣乱",
            "consequence": "妈妈暂停电话说他",
            "pattern": "独处时安静"
        },
        "expected_logic": "寻求关注 → 关注重定向与计划性忽略"
    },
    {
        "id": 5,
        "name": "自我刺激行为",
        "first_input": "他总是不停地晃手，盯着手看，叫名字没反应。",
        "background": {
            "age": "4 岁",
            "setting": "任何时间地点",
            "behavior": "晃手，盯着手看",
            "consequence": "家长打断他",
            "pattern": "无聊或兴奋时更多"
        },
        "expected_logic": "自动强化（自我刺激）→ 感觉寻求 → 提供替代性感觉输入"
    },
]

class SmartStressTestRunner:
    def __init__(self):
        self.results = []
        self.start_time = datetime.now()
    
    def run_case(self, case):
        """执行单个测试案例 - 智能响应"""
        print(f"\n{'='*60}")
        print(f"案例 {case['id']}: {case['name']}")
        print(f"{'='*60}")
        
        session_id = None
        conversation_log = []
        report = None
        max_turns = 8
        turn_count = 0
        
        # 第 1 轮：发送用户第一条输入
        user_input = case['first_input']
        print(f"\n【用户】{user_input}")
        response = self._send_message(session_id, user_input)
        session_id = response.get('session_id')
        
        ai_message = response.get('message', '')
        print(f"【AI】{ai_message[:100]}...")
        conversation_log.append({"role": "user", "content": user_input})
        conversation_log.append({"role": "ai", "content": ai_message})
        turn_count += 1
        
        # 后续轮次：根据 AI 问题智能回答
        while response.get('status') != 'completed' and turn_count < max_turns:
            user_input = self._generate_smart_response(case['background'], ai_message)
            print(f"\n【用户】{user_input}")
            
            response = self._send_message(session_id, user_input)
            ai_message = response.get('message', '')
            print(f"【AI】{ai_message[:100]}...")
            
            conversation_log.append({"role": "user", "content": user_input})
            conversation_log.append({"role": "ai", "content": ai_message})
            turn_count += 1
            
            time.sleep(1)
        
        # 如果还没完成，发送结束信号
        if response.get('status') != 'completed':
            print(f"\n【用户】没有了，就这些信息。")
            response = self._send_message(session_id, "没有了，就这些信息。")
            ai_message = response.get('message', '')
            print(f"【AI】{ai_message[:100]}...")
            conversation_log.append({"role": "user", "content": "没有了，就这些信息。"})
            conversation_log.append({"role": "ai", "content": ai_message})
        
        # 获取最终报告
        if response.get('status') == 'completed' and response.get('data'):
            report = response['data']
            print(f"\n✅ 报告生成完成（{turn_count}轮）")
        
        # 评估
        evaluation = self._evaluate_case(case, conversation_log, report)
        
        # 保存结果
        result = {
            "case_id": case['id'],
            "case_name": case['name'],
            "conversation_log": conversation_log,
            "report": report,
            "evaluation": evaluation,
            "turn_count": turn_count,
            "timestamp": datetime.now().isoformat(),
        }
        self.results.append(result)
        
        # 保存单个案例结果
        self._save_case_result(result)
        
        return result
    
    def _generate_smart_response(self, background, ai_message):
        """根据 AI 问题智能生成回答"""
        ai_message_lower = ai_message.lower()
        
        # 检测 AI 在问什么
        if "几岁" in ai_message or "年龄" in ai_message:
            return background.get('age', '不太清楚')
        elif "男孩" in ai_message or "女孩" in ai_message or "性别" in ai_message:
            return "这个不太重要吧"
        elif "回应" in ai_message or "反应" in ai_message or "管" in ai_message:
            return background.get('consequence', '没什么特别反应')
        elif "环境" in ai_message or "地方" in ai_message or "吵" in ai_message:
            return background.get('setting', '就普通环境')
        elif "做" in ai_message and "行为" in ai_message:
            return background.get('behavior', '就是那样')
        elif "提醒" in ai_message or "示范" in ai_message:
            return background.get('consequence', '有时会提醒')
        elif "难" in ai_message or "简单" in ai_message:
            return background.get('behavior', '可能有点难吧')
        elif "感官" in ai_message or "声音" in ai_message or "光线" in ai_message:
            return "没特别注意"
        else:
            # 默认回答
            return background.get('behavior', '这个我不太清楚')
    
    def _send_message(self, session_id, user_input):
        """发送消息到 API"""
        payload = {
            "session_id": session_id,
            "user_input": user_input
        }
        try:
            response = requests.post(BASE_URL, json=payload, timeout=30)
            return response.json()
        except Exception as e:
            return {"error": str(e), "status": "error"}
    
    def _evaluate_case(self, case, conversation_log, report):
        """评估案例"""
        evaluation = {
            "A1_empathy": 3,  # 共情与关系建立
            "A2_extraction": 3,  # 信息提取能力
            "B1_question_quality": 3,  # 提问有效性
            "B2_turn_count": len([m for m in conversation_log if m['role'] == 'user']),  # 对话轮次
            "C1_accuracy": 3,  # 临床分析准确性
            "C2_consistency": 3,  # 逻辑自洽性
            "C3_completeness": 3,  # 报告完整性
            "D1_personalization": 3,  # 个性化程度
            "D2_actionable": 3,  # 建议可操作性
            "passed": False,
            "issues": []
        }
        
        if not report:
            evaluation['issues'].append("未生成报告")
            evaluation['C2_consistency'] = 1
            return evaluation
        
        # A1: 检查首轮是否共情
        if conversation_log:
            first_ai = conversation_log[1]['content'] if len(conversation_log) > 1 else ""
            if any(kw in first_ai for kw in ["理解", "明白", "谢谢", "描述"]):
                evaluation['A1_empathy'] = 4
        
        # A2: 检查信息提取
        if report.get('context') or report.get('child_behavior'):
            evaluation['A2_extraction'] = 4
        else:
            evaluation['issues'].append("信息提取不完整")
        
        # B1: 提问有效性（根据轮次判断）
        if evaluation['B2_turn_count'] <= 4:
            evaluation['B1_question_quality'] = 5
        elif evaluation['B2_turn_count'] <= 6:
            evaluation['B1_question_quality'] = 4
        else:
            evaluation['B1_question_quality'] = 3
            evaluation['issues'].append("提问轮次较多")
        
        # C1: 临床分析准确性
        if report.get('functional_judgment'):
            evaluation['C1_accuracy'] = 4
        else:
            evaluation['issues'].append("功能判断缺失")
        
        # C2: 逻辑自洽性（关键项）
        if report.get('core_insight') and report.get('intervention_plan'):
            evaluation['C2_consistency'] = 4
            evaluation['passed'] = True
        else:
            evaluation['issues'].append("逻辑不自洽")
        
        # C3: 报告完整性
        required_fields = ['summary', 'context', 'child_behavior', 'clinical_differential']
        missing = [f for f in required_fields if not report.get(f)]
        if not missing:
            evaluation['C3_completeness'] = 5
        else:
            evaluation['issues'].append(f"缺少字段：{missing}")
        
        # D1: 个性化程度
        report_text = json.dumps(report, ensure_ascii=False)
        if len(report_text) > 500:
            evaluation['D1_personalization'] = 4
        else:
            evaluation['D1_personalization'] = 3
        
        # D2: 建议可操作性
        plan = report.get('intervention_plan', {})
        if plan and plan.get('four_step_plan'):
            evaluation['D2_actionable'] = 4
        else:
            evaluation['issues'].append("干预计划不完整")
        
        return evaluation
    
    def _save_case_result(self, result):
        """保存单个案例结果"""
        filename = OUTPUT_DIR / f"case_{result['case_id']:02d}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"📄 结果已保存：{filename}")
    
    def generate_summary_report(self):
        """生成汇总报告"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r['evaluation']['passed'])
        
        # 计算平均分
        metrics = ['A1_empathy', 'A2_extraction', 'B1_question_quality', 'C1_accuracy', 'C2_consistency', 'C3_completeness', 'D1_personalization', 'D2_actionable']
        averages = {}
        for m in metrics:
            values = [r['evaluation'][m] for r in self.results if r['evaluation'][m] > 0]
            averages[m] = sum(values) / len(values) if values else 0
        
        # 收集问题
        all_issues = []
        for r in self.results:
            for issue in r['evaluation']['issues']:
                all_issues.append(f"案例{r['case_id']}: {issue}")
        
        summary = {
            "test_info": {
                "total_cases": total,
                "passed": passed,
                "failed": total - passed,
                "pass_rate": f"{passed/total*100:.1f}%" if total > 0 else "0%",
                "start_time": self.start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "avg_turn_count": sum(r['turn_count'] for r in self.results) / total if total > 0 else 0,
            },
            "averages": averages,
            "overall_score": sum(averages.values()) / len(averages) if averages else 0,
            "issues": all_issues[:20],
            "recommendations": []
        }
        
        # 生成建议
        if averages.get('C2_consistency', 0) < 3:
            summary['recommendations'].append("【高优先级】修复逻辑自洽性问题")
        if averages.get('B1_question_quality', 0) < 3:
            summary['recommendations'].append("【中优先级】优化提问策略，减少冗余")
        if averages.get('D2_actionable', 0) < 3:
            summary['recommendations'].append("【中优先级】增强干预计划的可操作性")
        
        # 保存汇总报告
        summary_file = OUTPUT_DIR / "summary_report.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        # 打印摘要
        print(f"\n{'='*60}")
        print("📊 测试汇总报告")
        print(f"{'='*60}")
        print(f"总案例数：{total}")
        print(f"通过数：{passed}")
        print(f"通过率：{summary['test_info']['pass_rate']}")
        print(f"平均轮次：{summary['test_info']['avg_turn_count']:.1f}")
        print(f"总体评分：{summary['overall_score']:.2f}/5.0")
        print(f"\n各维度平均分:")
        for m, avg in averages.items():
            print(f"  {m}: {avg:.2f}")
        print(f"\n主要问题:")
        for issue in all_issues[:10]:
            print(f"  - {issue}")
        print(f"\n建议:")
        for rec in summary['recommendations']:
            print(f"  - {rec}")
        print(f"\n📄 详细报告：{summary_file}")
        
        return summary

if __name__ == "__main__":
    print("="*60)
    print("🧪 V4.5.3 智能压力测试（5 案例精简版）")
    print("="*60)
    print(f"开始时间：{datetime.now().isoformat()}")
    
    runner = SmartStressTestRunner()
    
    # 执行测试案例
    for case in TEST_CASES:
        try:
            runner.run_case(case)
            time.sleep(2)
        except Exception as e:
            print(f"❌ 案例{case['id']}执行失败：{e}")
    
    # 生成汇总报告
    runner.generate_summary_report()
    
    print(f"\n✅ 测试完成！")
