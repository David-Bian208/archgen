"""
行为观察伙伴 - 性能测试脚本
使用 locust 进行并发测试
"""

from locust import HttpUser, task, between
import json


class BehaviorRecorderUser(HttpUser):
    """模拟用户行为"""
    
    wait_time = between(1, 3)  # 用户操作间隔 1-3 秒
    
    @task(3)
    def submit_behavior(self):
        """提交行为描述（权重 3）"""
        scenarios = [
            "我儿子在课堂上总是突然发出奇怪的声音，老师看他时他就笑。",
            "我女儿每天写作业时总是要去喝水、上厕所，就是不想写作业。",
            "孩子经常一个人摇晃身体，盯着旋转的风扇看。",
            "孩子每天都要走同样的路线去幼儿园，换一条路就会大哭大闹。",
            "孩子在游乐场想和其他小朋友玩，但直接抢玩具。",
        ]
        
        import random
        payload = {
            "session_id": None,
            "user_input": random.choice(scenarios)
        }
        
        self.client.post(
            "/api/v4/chat",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30.0
        )
    
    @task(1)
    def health_check(self):
        """健康检查（权重 1）"""
        self.client.get("/api/health")
    
    @task(1)
    def submit_feedback(self):
        """提交反馈（权重 1）"""
        payload = {
            "session_id": "load_test_session",
            "rating": 5,
            "accuracy": "accurate",
            "feedback_text": "性能测试反馈"
        }
        
        self.client.post(
            "/api/v4/feedback",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5.0
        )


# 运行方式：
# locust -f test_performance.py --host=http://localhost:8000
