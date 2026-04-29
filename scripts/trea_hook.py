#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trea 增量质量门禁（V2.0 - 集成真实代码检查）

功能：
1. 增量扫描（仅检查变更文件）
2. 真实代码检查（Lint/Type/Security/Arch/Test/Requirement）
3. 输出安全脱敏（防止密钥泄露）
4. JSON 报告生成
5. 提交前自动拦截

使用：
  python3 scripts/trea_hook.py --incremental --files "file1.py,file2.py"
  python3 scripts/trea_hook.py --task-id TASK_XXX --check-types lint,type,security
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Any

# 导入运行时优化器（脱敏功能）
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入代码检查引擎（V2.0 新增）
from code_verification import CodeVerificationEngine

# 导入运行时优化器（脱敏功能）
try:
    from claw.runtime_optimizer import sanitize_output
except (ImportError, ModuleNotFoundError):
    # 如果没有 runtime_optimizer，使用简单的脱敏函数
    def sanitize_output(text: str) -> str:
        """简单脱敏：移除可能的 API 密钥"""
        import re
        text = re.sub(r'sk-[a-zA-Z0-9]{32,}', 'sk-***', text)
        text = re.sub(r'Bearer [a-zA-Z0-9._-]{20,}', 'Bearer ***', text)
        return text


def get_changed_files() -> List[str]:
    """获取变更文件"""
    try:
        staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=5
        ).stdout.strip().split('\n')
        working = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True, text=True, timeout=5
        ).stdout.strip().split('\n')
        return list(set(staged + working))
    except:
        return []


def pre_commit_check(task_id: str, files: List[str], check_types: List[str] = None) -> Dict[str, Any]:
    """
    提交前自动检查（V2.0 新增）
    
    Args:
        task_id: 任务 ID
        files: 变更文件列表
        check_types: 检查类型（默认 ["lint", "type", "security"]）
    
    Returns:
        检查报告
    """
    if check_types is None:
        check_types = ["lint", "type", "security"]
    
    workspace_path = str(Path(__file__).parent.parent)
    engine = CodeVerificationEngine(workspace_path)
    
    print(f"🔍 运行提交前检查（任务：{task_id}）")
    print(f"📝 检查文件：{len(files)} 个")
    print(f"🛠️  检查项：{', '.join(check_types)}")
    print("-" * 60)
    
    # 运行检查
    report = engine.run_verification(
        task_id=task_id,
        check_types=check_types,
        changed_files=files
    )
    
    # 生成人类可读报告
    report_text = engine.generate_report(report)
    print(report_text)
    
    return report


def run_quality_gates(files: List[str]) -> Dict[str, Any]:
    """运行质量门禁（向后兼容）"""
    if not files:
        return {"status": "✅ No changes"}
    
    # V2.0：使用 CodeVerificationEngine
    workspace_path = str(Path(__file__).parent.parent)
    engine = CodeVerificationEngine(workspace_path)
    
    report = engine.run_verification(
        task_id="pre_commit",
        check_types=["lint", "security"],
        changed_files=files
    )
    
    return report


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Trea 增量质量门禁 V2.0")
    parser.add_argument("--incremental", action="store_true", help="增量模式")
    parser.add_argument("--files", type=str, help="变更文件列表（逗号分隔）")
    parser.add_argument("--task-id", type=str, help="任务 ID（用于 Requirement 检查）")
    parser.add_argument("--check-types", type=str, default="lint,type,security", help="检查类型（逗号分隔）")
    parser.add_argument("--pre-commit", action="store_true", help="提交前检查模式")
    args = parser.parse_args()
    
    print("🛳️ Trea 增量质量门禁 V2.0 - 启动")
    
    # 获取变更文件
    if args.files:
        files = [f.strip() for f in args.files.split(",")]
    else:
        files = get_changed_files()
    
    if not files:
        print("✅ 无变更文件，跳过检查")
        sys.exit(0)
    
    print(f"📝 变更文件：{len(files)} 个")
    
    # 解析检查类型
    check_types = [t.strip() for t in args.check_types.split(",")]
    
    # V2.0：提交前检查模式
    if args.pre_commit or args.task_id:
        task_id = args.task_id or "pre_commit"
        print(f"🔍 运行提交前检查（任务：{task_id}）")
        print("-" * 60)
        
        report = pre_commit_check(task_id, files, check_types)
        
        # 保存报告
        report_file = Path("trea_report.json")
        report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n💾 报告已保存：{report_file}")
        
        # 退出码
        sys.exit(0 if report["status"] == "passed" else 1)
    else:
        # 向后兼容：旧版质量门禁
        print("🔍 运行质量门禁（兼容模式）")
        print("-" * 60)
        
        report = run_quality_gates(files)
        
        # 生成报告（脱敏处理）
        report_str = json.dumps(report, ensure_ascii=False, indent=2)
        safe_report = sanitize_output(report_str)  # 安全脱敏
        
        print("\n📊 检查结果:")
        print(f"  总状态：{report.get('status', 'unknown')}")
        print(f"  通过：{report.get('summary', {}).get('passed', 0)}")
        print(f"  失败：{report.get('summary', {}).get('failed', 0)}")
        
        # 保存报告
        report_file = Path("trea_report.json")
        report_file.write_text(safe_report, encoding="utf-8")
        print(f"\n💾 报告已保存：{report_file}")
        
        # 退出码
        sys.exit(0 if report.get("status") == "passed" else 1)


if __name__ == "__main__":
    main()
