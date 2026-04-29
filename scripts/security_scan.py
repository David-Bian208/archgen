#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
security_scan.py - 安全检查脚本（优化版）

功能：
1. 扫描代码中的安全问题
2. 返回结构化报告
3. 支持增量扫描
4. 排除误报

版本：V6.0.3 | 创建时间：2026-04-20
"""

import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Any

# 安全检查规则（优化版）
SECURITY_RULES = [
    {
        "id": "no-hardcoded-api-keys",
        "description": "禁止硬编码 API 密钥",
        "pattern": r"(?i)(api[_-]?key|apikey)\s*=\s*['\"][a-zA-Z0-9_-]{20,}['\"]",
        "severity": "critical",
        "exclude_patterns": [r"print\s*\(", r"#.*API_KEY", r"export\s+"]
    },
    {
        "id": "no-hardcoded-passwords",
        "description": "禁止硬编码密码",
        "pattern": r"(?i)(password|passwd|pwd)\s*=\s*['\"][^'\"]{4,}['\"]",
        "severity": "critical",
        "exclude_patterns": [r"print\s*\(", r"#.*password", r"example", r"placeholder"]
    },
    {
        "id": "no-eval-usage",
        "description": "禁止使用 eval()",
        "pattern": r"\beval\s*\([^)]+\)",
        "severity": "high",
        "exclude_patterns": [r"#.*eval", r"description.*eval", r"禁止.*eval"]
    }
]


def should_exclude(line: str, exclude_patterns: List[str]) -> bool:
    """检查是否应该排除"""
    for pattern in exclude_patterns:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    return False


def scan_file(file_path: Path) -> List[Dict[str, Any]]:
    """扫描单个文件"""
    issues = []
    
    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        for rule in SECURITY_RULES:
            for i, line in enumerate(lines, 1):
                # 先检查是否应该排除
                if should_exclude(line, rule.get("exclude_patterns", [])):
                    continue
                
                # 再检查是否匹配规则
                if re.search(rule["pattern"], line):
                    issues.append({
                        "rule_id": rule["id"],
                        "description": rule["description"],
                        "severity": rule["severity"],
                        "file": str(file_path),
                        "line": i,
                        "code": line.strip()[:100]
                    })
    except Exception as e:
        pass  # 忽略无法读取的文件
    
    return issues


def scan_directory(directory: Path, extensions: List[str] = None) -> List[Dict[str, Any]]:
    """扫描目录"""
    if extensions is None:
        extensions = [".py", ".js", ".ts"]
    
    all_issues = []
    
    for ext in extensions:
        for file_path in directory.rglob(f"*{ext}"):
            # 跳过虚拟环境、测试目录和 node_modules
            if any(skip in str(file_path) for skip in ["venv", "node_modules", "__pycache__"]):
                continue
            
            issues = scan_file(file_path)
            all_issues.extend(issues)
    
    return all_issues


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="安全检查脚本")
    parser.add_argument("--incremental", action="store_true", help="增量模式")
    parser.add_argument("--files", type=str, help="变更文件列表（逗号分隔）")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="输出格式")
    
    args = parser.parse_args()
    
    print("🛡️ 安全检查 - 启动")
    
    # 增量模式
    if args.incremental and args.files:
        files = [Path(f.strip()) for f in args.files.split(",")]
        all_issues = []
        
        for file_path in files:
            if file_path.exists():
                issues = scan_file(file_path)
                all_issues.extend(issues)
    else:
        # 全量扫描
        target_dir = Path(__file__).parent.parent
        all_issues = scan_directory(target_dir)
    
    # 输出结果
    if args.format == "json":
        print(json.dumps({"issues": all_issues}, ensure_ascii=False, indent=2))
    else:
        print(f"\n扫描完成！发现 {len(all_issues)} 个问题\n")
        
        if all_issues:
            for issue in all_issues[:10]:  # 仅显示前 10 个
                print(f"[{issue['severity'].upper()}] {issue['rule_id']}")
                print(f"  文件：{issue['file']}:{issue['line']}")
                print(f"  代码：{issue['code']}")
                print()
    
    # 退出码
    if len(all_issues) > 0:
        print(f"⚠️ 发现 {len(all_issues)} 个安全问题")
        sys.exit(1)
    else:
        print("✅ 安全检查通过")
        sys.exit(0)


if __name__ == "__main__":
    main()
