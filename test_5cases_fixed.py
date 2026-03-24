#!/usr/bin/env python3
"""
V4.10.3 5 案例快速验证测试
验证修复后的测试逻辑是否正常工作
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

BASE_URL = "http://localhost:8000"
CHAT_ENDPOINT = f"{BASE_URL}/api/v4/chat"
TIMEOUT = 60

# 5 个代表性测试案例
TEST_CASES = [
    {
        "id": 1,
        "scene": "joint_play",
        "parent_input": "我女儿跟小朋友玩的时候，总以为自己跟别人在玩，其实人家没带她玩。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": ["社交信号监测", "监测"]
    },
    {
        "id": 2,
        "scene": "rules_rigidity",
        "parent_input": "我儿子每天回家必须走同一条路，有一次换了条路走，他就崩溃大哭。",
        "expected_hypothesis": "坚持同一性",
        "expected_capability_gap": ["认知灵活性", "灵活性"]
    },
    {
        "id": 3,
        "scene": "body_boundary",
        "parent_input": "我女儿抱小朋友的时候特别用力，把人家的肋骨都勒疼了。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": ["身体边界", "身体感知"]
    },
    {
        "id": 4,
        "scene": "emotion_recognition",
        "parent_input": "我儿子跟小朋友玩，人家都皱眉了他还继续，最后人家生气走了。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": ["情绪识别", "情绪"]
    },
    {
        "id": 5,
        "scene": "conversation_intro",
        "parent_input": "我女儿给别人介绍朋友的时候，说完就走了，也不看人家有没有在听。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": ["社交信号监测", "监测"]
    }
]

class TestRunner:
    def __init__(self):
        self.session = requests.Session()
        self.results = []
    
    def send_message(self, text: str, session_id: Optional[str] = None) -> Tuple[dict, str]:
        """发送消息并获取响应"""
        if not text or not text.strip():
            return {"error": "empty_input"}, session_id
        
        payload = {
            "user_input": text.strip(),
            "session_id": session_id
        }
        
        try:
            response = self.session.post(CHAT_ENDPOINT, json=payload, timeout=TIMEOUT)
            
            if response.status_code == 400:
                error_detail = response.json().get("detail", "Unknown error")
                return {"error": f"400: {error_detail}"}, session_id
            
            response.raise_for_status()
            data = response.json()
            new_session_id = data.get("session_id", session_id)
            
            return data, new_session_id
            
        except requests.exceptions.Timeout:
            return {"error": "timeout"}, session_id
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}, session_id
    
    def get_follow_up_input(self, data: dict, turn: int) -> str:
        """根据系统响应生成后续输入"""
        message = data.get("message", "")
        
        if "几岁" in message or "年龄" in message:
            return "5 岁"
        elif "男孩" in message or "女孩" in message:
            return "女孩"
        elif "地方" in message or "哪里" in message or "幼儿园" in message or "学校" in message:
            return "在幼儿园"
        elif "时候" in message or "情况" in message or "活动" in message:
            return "做操的时候"
        elif "持续" in message or "多久" in message or "时间" in message:
            return "半年了"
        elif "评估" in message or "报告" in message or "完成" in message:
            return "完成评估"
        else:
            return "是的，请继续评估"
    
    def extract_report_info(self, data: dict) -> dict:
        """从响应中提取报告信息"""
        result = {
            "summary": "",
            "functional_judgment": "",
            "capability_gap": ""
        }
        
        try:
            report = data.get("report", {})
            result["summary"] = report.get("summary", "")
            result["functional_judgment"] = report.get("functional_judgment", "") or report.get("expert_view", "")
            result["capability_gap"] = report.get("capability_hypothesis", "") or report.get("core_capability_goal", "")
        except Exception as e:
            print(f"⚠️ 提取失败：{e}")
        
        return result
    
    def check_match(self, actual: str, expected_keywords: List[str]) -> bool:
        """检查实际结果是否包含预期关键词"""
        if not actual:
            return False
        
        actual_lower = actual.lower()
        for keyword in expected_keywords:
            if keyword.lower() in actual_lower:
                return True
        
        return False
    
    def run_test(self, case: dict) -> dict:
        """运行单个测试案例 - 多轮对话"""
        print(f"\n{'='*60}")
        print(f"测试 #{case['id']} ({case['scene']})")
        print(f"输入：{case['parent_input'][:50]}...")
        print(f"{'='*60}")
        
        session_id = None
        final_data = None
        max_turns = 8
        
        for turn in range(1, max_turns + 1):
            if turn == 1:
                user_input = case["parent_input"]
            else:
                status = final_data.get("status", "")
                if status == "completed":
                    break
                user_input = self.get_follow_up_input(final_data, turn)
            
            print(f"  第{turn}轮：发送 '{user_input[:30]}...'")
            data, session_id = self.send_message(user_input, session_id)
            final_data = data
            
            if "error" in data:
                print(f"  ❌ 错误：{data['error']}")
                return {
                    "case_id": case["id"],
                    "scene": case["scene"],
                    "passed": False,
                    "error": data["error"],
                    "failure_reasons": [f"API 错误：{data['error']}"]
                }
            
            status = data.get("status", "")
            print(f"  响应：status={status}")
            
            if status == "completed" and "report" in data:
                print(f"  ✅ 报告已生成")
                break
            
            time.sleep(0.5)  # 短暂间隔
        
        # 提取并评估
        extracted = self.extract_report_info(final_data)
        
        hypothesis_match = self.check_match(extracted["functional_judgment"], [case["expected_hypothesis"]])
        capability_match = self.check_match(extracted["capability_gap"], case["expected_capability_gap"])
        passed = hypothesis_match and capability_match
        
        print(f"\n  结果：")
        print(f"    功能判断：{extracted['functional_judgment'][:60]}...")
        print(f"    能力缺口：{extracted['capability_gap'][:60]}...")
        print(f"    假设匹配：{'✅' if hypothesis_match else '❌'}")
        print(f"    能力匹配：{'✅' if capability_match else '❌'}")
        print(f"    总评：{'✅ 通过' if passed else '❌ 失败'}")
        
        return {
            "case_id": case["id"],
            "scene": case["scene"],
            "passed": passed,
            "functional_judgment": extracted["functional_judgment"],
            "capability_gap": extracted["capability_gap"],
            "hypothesis_match": hypothesis_match,
            "capability_match": capability_match
        }
    
    def run_all(self):
        """运行所有测试"""
        print("\n" + "="*60)
        print("🧪 V4.10.3 5 案例快速验证测试")
        print("="*60)
        
        for case in TEST_CASES:
            result = self.run_test(case)
            self.results.append(result)
            time.sleep(1)  # 案例间隔
        
        # 汇总
        passed = sum(1 for r in self.results if r["passed"])
        total = len(self.results)
        
        print(f"\n{'='*60}")
        print(f"测试结果：{passed}/{total} 通过 ({passed/total*100:.1f}%)")
        print(f"{'='*60}")
        
        return passed == total

if __name__ == "__main__":
    runner = TestRunner()
    success = runner.run_all()
    exit(0 if success else 1)
