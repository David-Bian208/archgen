"""
行为观察伙伴 - API 接口快速测试
不需要浏览器，直接测试后端 API
"""

import requests
import json
import time
from datetime import datetime

# 配置
API_URL = "http://localhost:8000"

# 测试结果记录
results = []

def log_result(test_id, name, status, message=""):
    """记录测试结果"""
    result = {
        "test_id": test_id,
        "name": name,
        "status": status,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    results.append(result)
    
    icon = "✅" if status == "PASS" else "❌"
    print(f"{icon} {test_id}: {name}")
    if message:
        print(f"   {message}")

def test_health_check():
    """TEST-F-016: API 健康检查"""
    try:
        response = requests.get(f"{API_URL}/api/health", timeout=5)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("status") == "healthy"
        
        log_result("TEST-F-016", "API 健康检查", "PASS", f"LLM: {data.get('llm_model')}")
    except Exception as e:
        log_result("TEST-F-016", "API 健康检查", "FAIL", str(e))

def test_v3_chat():
    """TEST-F-017: V3 API 对话"""
    try:
        payload = {
            "session_id": None,
            "user_input": "测试 V3 API 功能"
        }
        
        response = requests.post(f"{API_URL}/api/v3/chat", json=payload, timeout=30)
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data or "response" in data
        
        log_result("TEST-F-017", "V3 API 对话", "PASS", f"响应长度：{len(str(data))}")
    except Exception as e:
        log_result("TEST-F-017", "V3 API 对话", "FAIL", str(e))

def test_v4_chat():
    """TEST-F-018: V4 API 对话"""
    try:
        payload = {
            "session_id": None,
            "user_input": "测试 V4 API 功能"
        }
        
        response = requests.post(f"{API_URL}/api/v4/chat", json=payload, timeout=30)
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data or "response" in data
        
        log_result("TEST-F-018", "V4 API 对话", "PASS", f"响应长度：{len(str(data))}")
    except Exception as e:
        log_result("TEST-F-018", "V4 API 对话", "FAIL", str(e))

def test_feedback_api():
    """TEST-F-019: 反馈提交 API"""
    try:
        payload = {
            "session_id": "test_session_api_001",
            "rating": 5,
            "accuracy": "accurate",
            "feedback_text": "API 自动化测试反馈"
        }
        
        response = requests.post(f"{API_URL}/api/v4/feedback", json=payload, timeout=5)
        assert response.status_code == 200
        
        log_result("TEST-F-019", "反馈提交 API", "PASS")
    except Exception as e:
        log_result("TEST-F-019", "反馈提交 API", "FAIL", str(e))

def test_logs_api():
    """TEST-F-020: 测试日志查询 API"""
    try:
        response = requests.get(f"{API_URL}/api/v4/test/logs", timeout=5)
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data or "logs" in data
        
        log_result("TEST-F-020", "测试日志查询 API", "PASS", f"日志数量：{len(data.get('data', []))}")
    except Exception as e:
        log_result("TEST-F-020", "测试日志查询 API", "FAIL", str(e))

def test_core_scenarios():
    """测试核心场景"""
    scenarios = [
        ("寻求关注", "我儿子在课堂上总是突然发出奇怪的声音，老师看他时他就笑。"),
        ("逃避行为", "我女儿每天写作业时总是要去喝水、上厕所，就是不想写作业。"),
        ("感官刺激", "孩子经常一个人摇晃身体，盯着旋转的风扇看。"),
        ("坚持同一性", "孩子每天都要走同样的路线去幼儿园，换一条路就会大哭大闹。"),
        ("社交技能", "孩子在游乐场想和其他小朋友玩，但直接抢玩具。"),
    ]
    
    for name, input_text in scenarios:
        try:
            payload = {
                "session_id": None,
                "user_input": input_text
            }
            
            start_time = time.time()
            response = requests.post(f"{API_URL}/api/v4/chat", json=payload, timeout=30)
            elapsed = time.time() - start_time
            
            assert response.status_code == 200
            data = response.json()
            
            # 验证响应包含关键词
            response_text = str(data)
            keywords = {
                "寻求关注": ["关注", "注意"],
                "逃避行为": ["逃避", "任务", "难度"],
                "感官刺激": ["感官", "刺激", "自我"],
                "坚持同一性": ["同一", "常规", "固定"],
                "社交技能": ["社交", "技能", "互动"],
            }
            
            found = any(kw in response_text for kw in keywords.get(name, []))
            
            if found:
                log_result(f"TEST-F-00{name}", f"核心场景-{name}", "PASS", f"响应时间：{elapsed:.2f}s")
            else:
                log_result(f"TEST-F-00{name}", f"核心场景-{name}", "WARN", f"关键词未匹配，响应时间：{elapsed:.2f}s")
                
        except Exception as e:
            log_result(f"TEST-F-00{name}", f"核心场景-{name}", "FAIL", str(e))

def test_boundary_cases():
    """测试边界情况"""
    # 空输入
    try:
        payload = {"session_id": None, "user_input": ""}
        response = requests.post(f"{API_URL}/api/v4/chat", json=payload, timeout=10)
        # 应返回错误或提示
        log_result("TEST-B-001", "空输入处理", "PASS" if response.status_code in [200, 400] else "FAIL")
    except Exception as e:
        log_result("TEST-B-001", "空输入处理", "FAIL", str(e))
    
    # 特殊字符
    try:
        payload = {"session_id": None, "user_input": "测试😊表情符号"}
        response = requests.post(f"{API_URL}/api/v4/chat", json=payload, timeout=30)
        assert response.status_code == 200
        log_result("TEST-B-004", "表情符号输入", "PASS")
    except Exception as e:
        log_result("TEST-B-004", "表情符号输入", "FAIL", str(e))
    
    # HTML 标签（XSS 测试）
    try:
        payload = {"session_id": None, "user_input": "<script>alert('test')</script>"}
        response = requests.post(f"{API_URL}/api/v4/chat", json=payload, timeout=30)
        assert response.status_code == 200
        data = response.json()
        response_text = json.dumps(data)
        assert "<script>" not in response_text, "脚本应被转义"
        log_result("TEST-B-005", "HTML 标签输入（XSS）", "PASS", "脚本已转义")
    except Exception as e:
        log_result("TEST-B-005", "HTML 标签输入（XSS）", "FAIL", str(e))
    
    # SQL 注入尝试
    try:
        payload = {"session_id": None, "user_input": "' OR '1'='1"}
        response = requests.post(f"{API_URL}/api/v4/chat", json=payload, timeout=30)
        assert response.status_code == 200, "应正常处理，不报错"
        log_result("TEST-B-006", "SQL 注入尝试", "PASS", "正常处理")
    except Exception as e:
        log_result("TEST-B-006", "SQL 注入尝试", "FAIL", str(e))

def test_security():
    """安全测试"""
    # XSS 防护
    try:
        payload = {"session_id": None, "user_input": "<script>alert('xss')</script>"}
        response = requests.post(f"{API_URL}/api/v4/chat", json=payload, timeout=30)
        data = response.json()
        response_text = json.dumps(data)
        assert "<script>" not in response_text
        log_result("TEST-S-001", "XSS 防护", "PASS")
    except Exception as e:
        log_result("TEST-S-001", "XSS 防护", "FAIL", str(e))
    
    # SQL 注入防护
    try:
        payload = {"session_id": None, "user_input": "' OR '1'='1'; DROP TABLE users;--"}
        response = requests.post(f"{API_URL}/api/v4/chat", json=payload, timeout=30)
        assert response.status_code == 200
        log_result("TEST-S-002", "SQL 注入防护", "PASS")
    except Exception as e:
        log_result("TEST-S-002", "SQL 注入防护", "FAIL", str(e))
    
    # 目录遍历
    try:
        response = requests.get(f"{API_URL}/../../etc/passwd", timeout=5)
        assert response.status_code in [404, 403, 400]
        log_result("TEST-S-006", "目录遍历防护", "PASS")
    except Exception as e:
        log_result("TEST-S-006", "目录遍历防护", "FAIL", str(e))

def generate_report():
    """生成测试报告"""
    print("\n" + "=" * 60)
    print("测试报告")
    print("=" * 60)
    
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    warnings = sum(1 for r in results if r["status"] == "WARN")
    
    print(f"\n总计：{total} 个测试")
    print(f"✅ 通过：{passed} ({passed/total*100:.1f}%)")
    print(f"❌ 失败：{failed} ({failed/total*100:.1f}%)")
    print(f"⚠️  警告：{warnings} ({warnings/total*100:.1f}%)")
    
    if failed > 0:
        print("\n失败的测试:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"  - {r['test_id']}: {r['name']} - {r['message']}")
    
    # 保存报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "pass_rate": f"{passed/total*100:.1f}%"
        },
        "results": results
    }
    
    with open("api_test_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n报告已保存到：api_test_report.json")
    
    return failed == 0

def main():
    """主函数"""
    print("=" * 60)
    print("行为观察伙伴 - API 自动化测试")
    print("=" * 60)
    print()
    
    # 运行测试
    print("【基础功能测试】")
    test_health_check()
    test_v3_chat()
    test_v4_chat()
    test_feedback_api()
    test_logs_api()
    
    print("\n【核心场景测试】")
    test_core_scenarios()
    
    print("\n【边界测试】")
    test_boundary_cases()
    
    print("\n【安全测试】")
    test_security()
    
    # 生成报告
    success = generate_report()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
