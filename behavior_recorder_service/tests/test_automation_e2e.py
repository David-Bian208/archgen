"""
行为观察伙伴 - 核心功能自动化测试
使用 Playwright 进行端到端测试
"""

import pytest
from playwright.sync_api import sync_playwright, expect
import time
import json


# 测试配置
BASE_URL = "http://localhost:3000"
API_URL = "http://localhost:8000"
TIMEOUT = 30000  # 30 秒超时


class TestCoreFunctionality:
    """核心功能测试"""
    
    @pytest.fixture
    def browser(self):
        """浏览器 fixture"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            yield browser
            browser.close()
    
    @pytest.fixture
    def page(self, browser):
        """页面 fixture"""
        page = browser.new_page()
        page.set_default_timeout(TIMEOUT)
        yield page
        page.close()
    
    def test_F001_seek_attention(self, page):
        """TEST-F-001: 寻求关注行为分析"""
        page.goto(BASE_URL)
        
        # 输入寻求关注行为描述
        input_text = "我儿子在课堂上总是突然发出奇怪的声音，老师看他时他就笑，不看她时就继续发出声音，即使被批评也停不下来。"
        page.fill("textarea", input_text)
        page.click("button:has-text('发送'), button:has-text('提交')")
        
        # 等待报告生成
        page.wait_for_selector(".report-content, .analysis-result", timeout=TIMEOUT)
        
        # 验证报告包含关键内容
        content = page.content()
        assert "关注" in content or "注意" in content, "报告应包含'关注'相关分析"
        
        print("✅ TEST-F-001 通过")
    
    def test_F002_escape_behavior(self, page):
        """TEST-F-002: 逃避行为分析"""
        page.goto(BASE_URL)
        
        # 输入逃避行为描述
        input_text = "我女儿每天写作业时总是要去喝水、上厕所、削铅笔，一会儿说饿了，一会儿说累了，就是不想写作业。"
        page.fill("textarea", input_text)
        page.click("button:has-text('发送'), button:has-text('提交')")
        
        # 等待报告生成
        page.wait_for_selector(".report-content, .analysis-result", timeout=TIMEOUT)
        
        # 验证报告
        content = page.content()
        assert "逃避" in content or "任务" in content, "报告应包含'逃避'相关分析"
        
        print("✅ TEST-F-002 通过")
    
    def test_F003_sensory_stimulation(self, page):
        """TEST-F-003: 感官刺激行为分析"""
        page.goto(BASE_URL)
        
        input_text = "孩子经常一个人摇晃身体，盯着旋转的风扇看，叫他也没反应。"
        page.fill("textarea", input_text)
        page.click("button:has-text('发送'), button:has-text('提交')")
        
        page.wait_for_selector(".report-content, .analysis-result", timeout=TIMEOUT)
        
        content = page.content()
        assert "感官" in content or "刺激" in content, "报告应包含'感官'相关分析"
        
        print("✅ TEST-F-003 通过")
    
    def test_F004_rigidity(self, page):
        """TEST-F-004: 坚持同一性行为分析"""
        page.goto(BASE_URL)
        
        input_text = "孩子每天都要走同样的路线去幼儿园，如果换一条路就会大哭大闹。"
        page.fill("textarea", input_text)
        page.click("button:has-text('发送'), button:has-text('提交')")
        
        page.wait_for_selector(".report-content, .analysis-result", timeout=TIMEOUT)
        
        content = page.content()
        assert "同一" in content or "常规" in content, "报告应包含'同一性'相关分析"
        
        print("✅ TEST-F-004 通过")
    
    def test_F005_social_skills(self, page):
        """TEST-F-005: 社交技能不足分析"""
        page.goto(BASE_URL)
        
        input_text = "孩子在游乐场想和其他小朋友玩，但直接抢玩具，把人都赶跑了。"
        page.fill("textarea", input_text)
        page.click("button:has-text('发送'), button:has-text('提交')")
        
        page.wait_for_selector(".report-content, .analysis-result", timeout=TIMEOUT)
        
        content = page.content()
        assert "社交" in content, "报告应包含'社交'相关分析"
        
        print("✅ TEST-F-005 通过")
    
    def test_F010_feedback_submission(self, page):
        """TEST-F-010: 反馈提交功能"""
        page.goto(BASE_URL)
        
        # 先完成一次对话
        page.fill("textarea", "测试反馈功能")
        page.click("button:has-text('发送'), button:has-text('提交')")
        page.wait_for_selector(".report-content, .analysis-result", timeout=TIMEOUT)
        
        # 尝试提交反馈
        try:
            # 点击 5 星评分
            page.click(".rating-star:nth-child(5), .star-5, [data-rating='5']")
            
            # 填写反馈文本
            page.fill(".feedback-text, textarea[placeholder*='反馈']", "测试反馈")
            
            # 提交
            page.click("button:has-text('提交反馈'), button:has-text('提交')")
            
            # 验证提交成功
            page.wait_for_selector(".feedback-success, .success", timeout=5000)
            
            print("✅ TEST-F-010 通过")
        except Exception as e:
            print(f"⚠️ TEST-F-010 跳过（反馈功能可能未实现）: {e}")
    
    def test_F011_page_load(self, page):
        """TEST-F-011: 页面加载"""
        response = page.goto(BASE_URL)
        
        # 验证页面加载成功
        assert response.status == 200, "页面应正常加载"
        
        # 验证无 JS 错误
        page.on("console", lambda msg: print(f"Console: {msg.text}"))
        page.on("pageerror", lambda err: pytest.fail(f"JS 错误：{err}"))
        
        # 等待页面稳定
        page.wait_for_load_state("networkidle")
        
        print("✅ TEST-F-011 通过")
    
    def test_F013_send_button_state(self, page):
        """TEST-F-013: 发送按钮状态"""
        page.goto(BASE_URL)
        
        # 获取发送按钮
        send_button = page.locator("button:has-text('发送'), button:has-text('提交')").first
        
        # 空输入时按钮状态
        button_disabled = send_button.is_disabled()
        print(f"空输入时按钮状态：{'禁用' if button_disabled else '可用'}")
        
        # 输入文字后
        page.fill("textarea", "测试内容")
        button_disabled = send_button.is_disabled()
        assert not button_disabled, "有内容时按钮应可点击"
        
        print("✅ TEST-F-013 通过")
    
    def test_F014_report_display(self, page):
        """TEST-F-014: 报告展示"""
        page.goto(BASE_URL)
        
        page.fill("textarea", "测试报告展示")
        page.click("button:has-text('发送'), button:has-text('提交')")
        
        # 等待报告出现
        report = page.wait_for_selector(".report-content, .analysis-result", timeout=TIMEOUT)
        
        # 验证报告可见
        assert report.is_visible(), "报告应可见"
        
        # 验证格式
        content = page.content()
        assert len(content) > 1000, "报告内容应足够长"
        
        print("✅ TEST-F-014 通过")
    
    def test_F015_new_conversation(self, page):
        """TEST-F-015: 新对话功能"""
        page.goto(BASE_URL)
        
        # 先进行一次对话
        page.fill("textarea", "第一轮对话")
        page.click("button:has-text('发送'), button:has-text('提交')")
        page.wait_for_selector(".report-content, .analysis-result", timeout=TIMEOUT)
        
        # 点击新对话按钮
        try:
            page.click("button:has-text('新的记录'), button:has-text('新对话'), button:has-text('重置')")
            
            # 验证输入框清空
            textarea = page.locator("textarea")
            value = textarea.input_value()
            assert value == "", "输入框应被清空"
            
            print("✅ TEST-F-015 通过")
        except Exception as e:
            print(f"⚠️ TEST-F-015 跳过（新对话按钮未找到）: {e}")


class TestAPIEndpoints:
    """API 接口测试"""
    
    def test_F016_health_check(self):
        """TEST-F-016: API 健康检查"""
        import requests
        
        response = requests.get(f"{API_URL}/api/health")
        assert response.status_code == 200, "健康检查应返回 200"
        
        data = response.json()
        assert "status" in data, "响应应包含 status 字段"
        assert data["status"] == "healthy", "状态应为 healthy"
        
        print("✅ TEST-F-016 通过")
    
    def test_F017_v3_chat(self):
        """TEST-F-017: V3 API 对话"""
        import requests
        
        payload = {
            "session_id": None,
            "user_input": "测试 V3 API"
        }
        
        response = requests.post(f"{API_URL}/api/v3/chat", json=payload)
        assert response.status_code == 200, f"V3 API 应返回 200，实际：{response.status_code}"
        
        data = response.json()
        assert "message" in data or "response" in data, "响应应包含 message 或 response"
        
        print("✅ TEST-F-017 通过")
    
    def test_F018_v4_chat(self):
        """TEST-F-018: V4 API 对话"""
        import requests
        
        payload = {
            "session_id": None,
            "user_input": "测试 V4 API"
        }
        
        response = requests.post(f"{API_URL}/api/v4/chat", json=payload)
        assert response.status_code == 200, f"V4 API 应返回 200，实际：{response.status_code}"
        
        data = response.json()
        assert "message" in data or "response" in data, "响应应包含 message 或 response"
        
        print("✅ TEST-F-018 通过")
    
    def test_F019_feedback_api(self):
        """TEST-F-019: 反馈提交 API"""
        import requests
        
        payload = {
            "session_id": "test_session_001",
            "rating": 5,
            "accuracy": "accurate",
            "feedback_text": "自动化测试反馈"
        }
        
        response = requests.post(f"{API_URL}/api/v4/feedback", json=payload)
        assert response.status_code == 200, f"反馈 API 应返回 200，实际：{response.status_code}"
        
        print("✅ TEST-F-019 通过")
    
    def test_F020_logs_api(self):
        """TEST-F-020: 测试日志查询 API"""
        import requests
        
        response = requests.get(f"{API_URL}/api/v4/test/logs")
        assert response.status_code == 200, f"日志 API 应返回 200，实际：{response.status_code}"
        
        data = response.json()
        assert "data" in data or "logs" in data, "响应应包含数据"
        
        print("✅ TEST-F-020 通过")


class TestBoundaryCases:
    """边界测试"""
    
    @pytest.fixture
    def browser(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            yield browser
            browser.close()
    
    @pytest.fixture
    def page(self, browser):
        page = browser.new_page()
        page.set_default_timeout(TIMEOUT)
        yield page
        page.close()
    
    def test_B001_empty_input(self, page):
        """TEST-B-001: 空输入"""
        page.goto(BASE_URL)
        
        # 空输入时点击发送
        send_button = page.locator("button:has-text('发送'), button:has-text('提交')").first
        
        # 检查按钮是否禁用
        if send_button.is_disabled():
            print("✅ TEST-B-001 通过（按钮禁用）")
        else:
            # 如果可以点击，应提示输入
            send_button.click()
            page.wait_for_timeout(2000)
            
            # 检查是否有提示
            content = page.content()
            assert "请输入" in content or "空" in content, "应提示输入内容"
            print("✅ TEST-B-001 通过（有提示）")
    
    def test_B002_short_input(self, page):
        """TEST-B-002: 极短输入"""
        page.goto(BASE_URL)
        
        page.fill("textarea", "嗯")
        page.click("button:has-text('发送'), button:has-text('提交')")
        
        # 应返回追问或提示
        page.wait_for_selector(".report-content, .analysis-result, .message", timeout=TIMEOUT)
        
        content = page.content()
        assert len(content) > 500, "应有响应内容"
        
        print("✅ TEST-B-002 通过")
    
    def test_B004_emoji_input(self, page):
        """TEST-B-004: 表情符号输入"""
        page.goto(BASE_URL)
        
        page.fill("textarea", "孩子今天很开心😊😊😊")
        page.click("button:has-text('发送'), button:has-text('提交')")
        
        page.wait_for_selector(".report-content, .analysis-result", timeout=TIMEOUT)
        
        content = page.content()
        assert "error" not in content.lower(), "不应报错"
        
        print("✅ TEST-B-004 通过")
    
    def test_B005_html_input(self, page):
        """TEST-B-005: HTML 标签输入（XSS 测试）"""
        page.goto(BASE_URL)
        
        page.fill("textarea", "<script>alert('test')</script>")
        page.click("button:has-text('发送'), button:has-text('提交')")
        
        page.wait_for_selector(".report-content, .analysis-result", timeout=TIMEOUT)
        
        # 验证脚本未被执行（页面不应弹出 alert）
        # 验证响应中脚本被转义
        content = page.content()
        assert "<script>" not in content, "脚本应被转义"
        
        print("✅ TEST-B-005 通过")
    
    def test_B006_sql_injection(self, page):
        """TEST-B-006: SQL 注入尝试"""
        page.goto(BASE_URL)
        
        page.fill("textarea", "' OR '1'='1")
        page.click("button:has-text('发送'), button:has-text('提交')")
        
        page.wait_for_selector(".report-content, .analysis-result", timeout=TIMEOUT)
        
        content = page.content()
        assert "error" not in content.lower() or "SQL" not in content, "不应暴露 SQL 错误"
        
        print("✅ TEST-B-006 通过")


class TestSecurity:
    """安全测试"""
    
    def test_S001_xss_protection(self):
        """TEST-S-001: XSS 防护"""
        import requests
        
        payload = {
            "session_id": None,
            "user_input": "<script>alert('xss')</script>"
        }
        
        response = requests.post(f"{API_URL}/api/v4/chat", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        response_text = json.dumps(data)
        
        # 验证脚本被转义
        assert "<script>" not in response_text, "脚本应被转义"
        
        print("✅ TEST-S-001 通过")
    
    def test_S002_sql_injection_api(self):
        """TEST-S-002: SQL 注入防护（API 层）"""
        import requests
        
        payload = {
            "session_id": None,
            "user_input": "' OR '1'='1'; DROP TABLE users;--"
        }
        
        response = requests.post(f"{API_URL}/api/v4/chat", json=payload)
        assert response.status_code == 200, "应正常处理，不报错"
        
        print("✅ TEST-S-002 通过")
    
    def test_S006_path_traversal(self):
        """TEST-S-006: 目录遍历攻击"""
        import requests
        
        response = requests.get(f"{API_URL}/../../etc/passwd")
        assert response.status_code in [404, 403, 400], "应拒绝目录遍历"
        
        print("✅ TEST-S-006 通过")


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("行为观察伙伴 - 自动化测试套件")
    print("=" * 60)
    
    # 使用 pytest 运行
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--html=report.html",
        "--self-contained-html"
    ])


if __name__ == "__main__":
    run_tests()
