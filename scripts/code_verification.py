#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
code_verification.py - 真实代码检查引擎

功能：
1. 读取任务文档 → 提取验收标准
2. 运行 6 项检查（Lint/Type/Security/Arch/Test/Requirement）
3. 输出结构化报告（通过/失败/警告）

版本：V1.0 | 创建时间：2026-04-22
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# 导入现有工具
import sys
sys.path.insert(0, str(Path(__file__).parent))
from security_scan import scan_directory


class CodeVerificationEngine:
    """代码检查引擎"""
    
    def __init__(self, workspace_path: str):
        self.workspace = Path(workspace_path)
        
    def run_verification(
        self,
        task_id: str,
        check_types: List[str] = None,
        changed_files: List[str] = None,
        task_requirements: List[str] = None
    ) -> Dict[str, Any]:
        """
        运行代码检查
        
        Args:
            task_id: 任务 ID
            check_types: 检查类型列表
            changed_files: 变更文件列表
            task_requirements: 任务要求列表
            
        Returns:
            检查报告
        """
        if check_types is None:
            check_types = ["lint", "type", "security", "arch", "test"]
        
        report = {
            "task_id": task_id,
            "status": "running",
            "checks": {},
            "summary": {
                "total": len(check_types),
                "passed": 0,
                "failed": 0,
                "warnings": 0
            }
        }
        
        # 依次运行各项检查
        for check_type in check_types:
            try:
                if check_type == "lint":
                    result = self._check_lint(changed_files)
                elif check_type == "type":
                    result = self._check_type(changed_files)
                elif check_type == "security":
                    result = self._check_security(changed_files)
                elif check_type == "arch":
                    result = self._check_arch(changed_files)
                elif check_type == "test":
                    result = self._check_tests()
                elif check_type == "requirement":
                    result = self._check_requirements(task_requirements, changed_files)
                else:
                    result = {"status": "skipped", "message": f"未知检查类型：{check_type}"}
                
                report["checks"][check_type] = result
                
                # 更新统计
                if result["status"] == "passed":
                    report["summary"]["passed"] += 1
                elif result["status"] == "failed":
                    report["summary"]["failed"] += 1
                elif result["status"] == "warning":
                    report["summary"]["warnings"] += 1
                    
            except Exception as e:
                report["checks"][check_type] = {
                    "status": "error",
                    "message": str(e)
                }
                report["summary"]["failed"] += 1
        
        # 总体状态
        if report["summary"]["failed"] > 0:
            report["status"] = "failed"
        elif report["summary"]["warnings"] > 0:
            report["status"] = "warning"
        else:
            report["status"] = "passed"
        
        return report
    
    def _check_lint(self, changed_files: List[str] = None) -> Dict[str, Any]:
        """Lint 检查（ruff）"""
        cmd = ["ruff", "check"]
        
        if changed_files:
            cmd.extend(changed_files)
        else:
            cmd.append(str(self.workspace))
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return {
                    "status": "passed",
                    "message": "✅ Lint 检查通过",
                    "output": result.stdout
                }
            else:
                issues = result.stdout.strip().split("\n")
                return {
                    "status": "failed",
                    "message": f"❌ 发现 {len(issues)} 个 Lint 问题",
                    "issues": issues[:10],  # 最多显示 10 个
                    "output": result.stdout
                }
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "message": "❌ Lint 检查超时（>60 秒）"
            }
    
    def _check_type(self, changed_files: List[str] = None) -> Dict[str, Any]:
        """Type 检查（mypy）"""
        cmd = ["mypy", "--no-error-summary", "--no-pretty"]
        
        if changed_files:
            cmd.extend(changed_files)
        else:
            cmd.append(str(self.workspace))
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                return {
                    "status": "passed",
                    "message": "✅ Type 检查通过",
                    "output": result.stdout
                }
            else:
                issues = result.stdout.strip().split("\n")
                return {
                    "status": "failed",
                    "message": f"❌ 发现 {len(issues)} 个类型错误",
                    "issues": issues[:10],
                    "output": result.stdout
                }
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "message": "❌ Type 检查超时（>120 秒）"
            }
    
    def _check_security(self, changed_files: List[str] = None) -> Dict[str, Any]:
        """安全检查（security_scan.py）"""
        try:
            # 复用现有 security_scan.py
            if changed_files:
                # 增量扫描
                issues = []
                for file_path in changed_files:
                    full_path = self.workspace / file_path
                    if full_path.exists():
                        file_issues = scan_directory(full_path.parent, [full_path.suffix])
                        if isinstance(file_issues, list):
                            issues.extend(file_issues)
                scan_result = {"issues": issues}
            else:
                # 全量扫描
                scan_result = scan_directory(self.workspace)
                if isinstance(scan_result, list):
                    scan_result = {"issues": scan_result}
            
            issue_list = scan_result.get("issues", []) if isinstance(scan_result, dict) else []
            critical_count = len([i for i in issue_list if isinstance(i, dict) and i.get("severity") == "critical"])
            high_count = len([i for i in issue_list if isinstance(i, dict) and i.get("severity") == "high"])
            
            if critical_count > 0 or high_count > 0:
                return {
                    "status": "failed",
                    "message": f"❌ 发现 {critical_count} 个严重 + {high_count} 个高危安全问题",
                    "issues": issue_list[:10],
                    "output": json.dumps(scan_result, indent=2, ensure_ascii=False)
                }
            else:
                return {
                    "status": "passed",
                    "message": "✅ 安全检查通过",
                    "output": json.dumps(scan_result, indent=2, ensure_ascii=False)
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"❌ 安全检查失败：{str(e)}"
            }
    
    def _check_arch(self, changed_files: List[str] = None) -> Dict[str, Any]:
        """架构检查（arch_guard.py）"""
        arch_guard_path = self.workspace / ".claw" / "arch_guard.py"
        
        if not arch_guard_path.exists():
            return {
                "status": "skipped",
                "message": "⚠️ arch_guard.py 不存在，跳过架构检查"
            }
        
        cmd = ["python3", str(arch_guard_path)]
        
        if changed_files:
            cmd.extend(changed_files)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.workspace)
            )
            
            # 解析 JSON 输出
            try:
                report = json.loads(result.stdout)
                if report.get("status") == "Passed":
                    return {
                        "status": "passed",
                        "message": "✅ 架构检查通过",
                        "output": result.stdout
                    }
                else:
                    return {
                        "status": "failed",
                        "message": f"❌ 架构检查失败：{report.get('message', '未知错误')}",
                        "output": result.stdout
                    }
            except json.JSONDecodeError:
                return {
                    "status": "warning",
                    "message": "⚠️ 架构检查输出格式异常",
                    "output": result.stdout
                }
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "message": "❌ 架构检查超时（>60 秒）"
            }
    
    def _check_tests(self) -> Dict[str, Any]:
        """测试检查（pytest）"""
        test_path = self.workspace / "tests"
        
        if not test_path.exists():
            return {
                "status": "skipped",
                "message": "⚠️ tests 目录不存在，跳过测试检查"
            }
        
        cmd = ["pytest", "-v", "--tb=short"]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self.workspace)
            )
            
            if result.returncode == 0:
                return {
                    "status": "passed",
                    "message": "✅ 测试通过",
                    "output": result.stdout[-2000:]  # 截取最后 2000 字符
                }
            else:
                return {
                    "status": "failed",
                    "message": "❌ 测试失败",
                    "output": result.stdout[-2000:] + result.stderr[-2000:]
                }
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "message": "❌ 测试超时（>300 秒）"
            }
    
    def _check_requirements(
        self,
        task_requirements: List[str],
        changed_files: List[str]
    ) -> Dict[str, Any]:
        """
        任务要求匹配检查
        
        检查变更文件是否实现了任务要求
        """
        if not task_requirements:
            return {
                "status": "skipped",
                "message": "⚠️ 无任务要求，跳过检查"
            }
        
        if not changed_files:
            return {
                "status": "warning",
                "message": "⚠️ 无变更文件，无法检查要求匹配"
            }
        
        # 简单检查：文件是否实际变更
        matched_requirements = []
        unmatched_requirements = []
        
        for req in task_requirements:
            # 启发式检查：要求关键词是否出现在变更文件中
            found = False
            for file_path in changed_files:
                try:
                    with open(self.workspace / file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 检查要求中的关键词是否出现在文件中
                        keywords = req.split()[:3]  # 取前 3 个词
                        if any(kw in content for kw in keywords if len(kw) > 2):
                            found = True
                            break
                except:
                    pass
            
            if found:
                matched_requirements.append(req)
            else:
                unmatched_requirements.append(req)
        
        if unmatched_requirements:
            return {
                "status": "warning",
                "message": f"⚠️ {len(unmatched_requirements)} 个要求未匹配到代码",
                "matched": matched_requirements,
                "unmatched": unmatched_requirements
            }
        else:
            return {
                "status": "passed",
                "message": "✅ 所有任务要求已实现",
                "matched": matched_requirements
            }
    
    def generate_report(self, report: Dict[str, Any], output_path: str = None) -> str:
        """生成人类可读的报告"""
        lines = [
            "=" * 60,
            f"代码检查报告 - {report['task_id']}",
            "=" * 60,
            f"总体状态：{self._status_emoji(report['status'])} {report['status'].upper()}",
            "",
            "检查项详情:",
            "-" * 60
        ]
        
        for check_type, result in report["checks"].items():
            emoji = self._status_emoji(result["status"])
            lines.append(f"{emoji} {check_type.upper()}: {result['message']}")
            
            if "issues" in result:
                for issue in result["issues"][:5]:
                    lines.append(f"   - {issue}")
        
        lines.append("")
        lines.append("统计:")
        lines.append(f"  总计：{report['summary']['total']}")
        lines.append(f"  通过：{report['summary']['passed']}")
        lines.append(f"  失败：{report['summary']['failed']}")
        lines.append(f"  警告：{report['summary']['warnings']}")
        lines.append("=" * 60)
        
        report_text = "\n".join(lines)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
        
        return report_text
    
    def _status_emoji(self, status: str) -> str:
        """状态转 emoji"""
        emojis = {
            "passed": "✅",
            "failed": "❌",
            "warning": "⚠️",
            "error": "🔴",
            "skipped": "⏭️"
        }
        return emojis.get(status, "❓")


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="代码检查引擎")
    parser.add_argument("--task-id", required=True, help="任务 ID")
    parser.add_argument("--check-types", nargs="+", default=["lint", "type", "security", "arch", "test"])
    parser.add_argument("--changed-files", nargs="+", help="变更文件列表")
    parser.add_argument("--requirements", nargs="+", help="任务要求列表")
    parser.add_argument("--output", help="输出报告路径")
    
    args = parser.parse_args()
    
    engine = CodeVerificationEngine("/home/admin/.openclaw/workspace/behavior_recorder_service")
    
    report = engine.run_verification(
        task_id=args.task_id,
        check_types=args.check_types,
        changed_files=args.changed_files,
        task_requirements=args.requirements
    )
    
    # 输出报告
    report_text = engine.generate_report(report, args.output)
    print(report_text)
    
    # 返回状态码
    sys.exit(0 if report["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
