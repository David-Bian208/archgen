#!/usr/bin/env python3
"""快速 5 案例测试 - 验证 API 是否正常"""

import requests
import json

BASE_URL = "http://localhost:8000"
CHAT_ENDPOINT = f"{BASE_URL}/api/v4/chat"
TIMEOUT = 60

TEST_CASES = [
    {
        "id": 1,
        "scene": "joint_play",
        "parent_input": "我女儿跟小朋友玩的时候，总以为自己跟别人在玩，其实人家没带她玩。",
        "expected_hypothesis": "社交技能不足"
    },
    {
        "id": 2,
        "scene": "rules_rigidity", 
        "parent_input": "我儿子每天回家必须走同一条路，有一次换了条路走，他就崩溃大哭。",
        "expected_hypothesis": "坚持同一性"
    },
    {
        "id": 3,
        "scene": "body_boundary",
        "parent_input": "我女儿抱小朋友的时候特别用力，把人家的肋骨都勒疼了。",
        "expected_hypothesis": "社交技能不足"
    },
    {
        "id": 4,
        "scene": "emotion_recognition",
        "parent_input": "我儿子跟小朋友玩，人家都皱眉了他还继续，最后人家生气走了。",
        "expected_hypothesis": "社交技能不足"
    },
    {
        "id": 5,
        "scene": "conversation_intro",
        "parent_input": "我女儿给别人介绍朋友的时候，说完就走了，也不看人家有没有在听。",
        "expected_hypothesis": "社交技能不足"
    }
]

def test_api():
    print("="*60)
    print("🧪 快速 5 案例测试")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for case in TEST_CASES:
        print(f"\n案例{case['id']}: {case['scene']}")
        
        try:
            resp = requests.post(
                CHAT_ENDPOINT,
                json={"user_input": case["parent_input"]},
                timeout=TIMEOUT
            )
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"   ✅ Status: {resp.status_code}")
                print(f"   Session: {data.get('session_id', 'N/A')}")
                print(f"   Response type: {data.get('response_type', 'N/A')}")
                passed += 1
            else:
                print(f"   ❌ Status: {resp.status_code}")
                print(f"   Response: {resp.text[:200]}")
                failed += 1
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"结果：{passed}通过，{failed}失败")
    print(f"{'='*60}")
    
    return failed == 0

if __name__ == "__main__":
    success = test_api()
    exit(0 if success else 1)
