#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_test.py - 战舰自动化小测试卷

功能：
1. 检查后端服务健康（端口 8003）
2. 检查前端服务健康（端口 5175）
3. 比对前后端版本号
4. 生成结构化验证报告

预计耗时：<1 分钟
"""

import requests
import json
import sys
from datetime import datetime
from pathlib import Path

# 配置
BACKEND_URL = "http://localhost:8003"
FRONTEND_URL = "http://localhost:5175"
REPORT_DIR = Path("/tmp/test_reports")

class AutoTester:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0
            }
        }
        REPORT_DIR.mkdir(exist_ok=True)
    
    def add_test(self, name: str, passed: bool, details: str = "", error: str = ""):
        """添加测试结果"""
        self.results["tests"].append({
            "name": name,
            "passed": passed,
            "details": details,
            "error": error
        })
        self.results["summary"]["total"] += 1
        if passed:
            self.results["summary"]["passed"] += 1
        else:
            self.results["summary"]["failed"] += 1
    
    def check_backend_health(self) -> bool:
        """检查后端服务健康"""
        try:
            response = requests.get(f"{BACKEND_URL}/api/v4/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                version = data.get("version", "unknown")
                self.add_test(
                    "后端服务健康检查",
                    True,
                    f"状态码：200，版本：{version}",
                    ""
                )
                return True
            else:
                self.add_test(
                    "后端服务健康检查",
                    False,
                    f"状态码：{response.status_code}",
                    f"HTTP {response.status_code}"
                )
                return False
        except requests.exceptions.ConnectionError:
            self.add_test(
                "后端服务健康检查",
                False,
                "无法连接到后端服务",
                f"后端服务未在 {BACKEND_URL} 运行"
            )
            return False
        except Exception as e:
            self.add_test(
                "后端服务健康检查",
                False,
                "未知错误",
                str(e)
            )
            return False
    
    def check_frontend_health(self) -> bool:
        """检查前端服务健康"""
        try:
            response = requests.get(FRONTEND_URL, timeout=5)
            if response.status_code == 200:
                self.add_test(
                    "前端服务健康检查",
                    True,
                    f"状态码：200，Vite 服务器正常运行",
                    ""
                )
                return True
            else:
                self.add_test(
                    "前端服务健康检查",
                    False,
                    f"状态码：{response.status_code}",
                    f"HTTP {response.status_code}"
                )
                return False
        except requests.exceptions.ConnectionError:
            self.add_test(
                "前端服务健康检查",
                False,
                "无法连接到前端服务",
                f"前端服务未在 {FRONTEND_URL} 运行"
            )
            return False
        except Exception as e:
            self.add_test(
                "前端服务健康检查",
                False,
                "未知错误",
                str(e)
            )
            return False
    
    def check_version_consistency(self) -> bool:
        """检查前后端版本号一致性"""
        try:
            # 获取后端版本
            backend_response = requests.get(f"{BACKEND_URL}/api/v4/health", timeout=5)
            backend_version = backend_response.json().get("version", "unknown")
            
            # 获取前端版本（从 package.json）
            frontend_package = Path("/home/admin/.openclaw/workspace/behavior_recorder_service/frontend/package.json")
            if frontend_package.exists():
                with open(frontend_package, 'r', encoding='utf-8') as f:
                    package_data = json.load(f)
                    frontend_version = package_data.get("version", "unknown")
            else:
                frontend_version = "package.json not found"
            
            # 比对版本
            if backend_version == frontend_version:
                self.add_test(
                    "版本号一致性检查",
                    True,
                    f"前后端版本均为 {backend_version}",
                    ""
                )
                return True
            else:
                self.add_test(
                    "版本号一致性检查",
                    False,
                    f"后端：{backend_version}，前端：{frontend_version}",
                    "前后端版本不一致"
                )
                return False
        except Exception as e:
            self.add_test(
                "版本号一致性检查",
                False,
                "无法获取版本信息",
                str(e)
            )
            return False
    
    def check_api_endpoints(self) -> bool:
        """检查核心 API 端点"""
        endpoints = [
            ("/api/v4/v6/analyze", "V6 临床推理 API"),
            ("/api/v4/l3/match-tfidf", "TF-IDF 匹配 API"),
            ("/api/v4/l3/match-embedding", "词向量匹配 API"),
        ]
        
        all_passed = True
        for endpoint, name in endpoints:
            try:
                response = requests.get(f"{BACKEND_URL}{endpoint}", timeout=5)
                if response.status_code in [200, 405]:  # 405 表示端点存在但需要 POST
                    self.add_test(
                        f"API 端点检查：{name}",
                        True,
                        f"端点 {endpoint} 可访问",
                        ""
                    )
                else:
                    self.add_test(
                        f"API 端点检查：{name}",
                        False,
                        f"状态码：{response.status_code}",
                        f"HTTP {response.status_code}"
                    )
                    all_passed = False
            except Exception as e:
                self.add_test(
                    f"API 端点检查：{name}",
                    False,
                    "无法访问",
                    str(e)
                )
                all_passed = False
        
        return all_passed
    
    def generate_report(self) -> str:
        """生成人类可读报告"""
        summary = self.results["summary"]
        passed = summary["passed"]
        total = summary["total"]
        success_rate = (passed / total * 100) if total > 0 else 0
        
        report = []
        report.append("=" * 60)
        report.append("🛳️ 战舰自动化小测试卷 - 验证报告")
        report.append("=" * 60)
        report.append(f"时间：{self.results['timestamp']}")
        report.append(f"后端：{BACKEND_URL}")
        report.append(f"前端：{FRONTEND_URL}")
        report.append("")
        report.append("-" * 60)
        report.append("📊 测试摘要")
        report.append("-" * 60)
        report.append(f"总测试数：{total}")
        report.append(f"通过：{passed} ✅")
        report.append(f"失败：{summary['failed']} ❌")
        report.append(f"通过率：{success_rate:.1f}%")
        report.append("")
        report.append("-" * 60)
        report.append("📋 详细结果")
        report.append("-" * 60)
        
        for test in self.results["tests"]:
            status = "✅" if test["passed"] else "❌"
            report.append(f"{status} {test['name']}")
            if test["details"]:
                report.append(f"   详情：{test['details']}")
            if test["error"]:
                report.append(f"   错误：{test['error']}")
            report.append("")
        
        report.append("-" * 60)
        if summary["failed"] == 0:
            report.append("🎉 所有测试通过！系统状态正常")
            report.append("-" * 60)
            report.append("✅ 建议操作：")
            report.append("   1. 创建 Git 提交任务派发给小治")
            report.append("   2. 附上提交信息草案")
            report.append("   3. 等待小治执行 Git 提交")
        else:
            report.append("❌ 存在失败测试！请检查系统状态")
            report.append("-" * 60)
            report.append("⚠️ 建议操作：")
            report.append("   1. 检查失败测试的错误信息")
            report.append("   2. 创建修复任务派发给小治")
            report.append("   3. 修复后重新运行验证")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def generate_json_report(self) -> str:
        """生成 JSON 报告"""
        return json.dumps(self.results, indent=2, ensure_ascii=False)
    
    def save_reports(self):
        """保存报告到文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存人类可读报告
        human_report = self.generate_report()
        human_path = REPORT_DIR / f"test_report_{timestamp}.txt"
        with open(human_path, 'w', encoding='utf-8') as f:
            f.write(human_report)
        
        # 保存 JSON 报告
        json_report = self.generate_json_report()
        json_path = REPORT_DIR / f"test_report_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            f.write(json_report)
        
        return human_path, json_path
    
    def run_all_tests(self) -> bool:
        """运行所有测试"""
        print("🛳️ 战舰自动化小测试卷 - 启动")
        print(f"时间：{datetime.now().isoformat()}")
        print("")
        
        # 执行测试
        self.check_backend_health()
        self.check_frontend_health()
        self.check_version_consistency()
        self.check_api_endpoints()
        
        # 生成并保存报告
        human_path, json_path = self.save_reports()
        
        # 打印报告
        print(self.generate_report())
        print("")
        print(f"📁 报告已保存：")
        print(f"   人类可读：{human_path}")
        print(f"   JSON 格式：{json_path}")
        
        # 返回是否全部通过
        return self.results["summary"]["failed"] == 0


def main():
    """主函数"""
    tester = AutoTester()
    all_passed = tester.run_all_tests()
    
    # 退出码（0=全部通过，1=存在失败）
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
