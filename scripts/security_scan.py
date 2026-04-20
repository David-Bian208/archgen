#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
security_scan.py - 安全扫描脚本

功能：
1. 读取 SECURITY_CHECKLIST.yml
2. 遍历项目文件（.py/.js/.vue）
3. 执行正则匹配
4. 生成结构化报告（人类可读 + JSON）

预计耗时：<10 秒
"""

import re
import os
import sys
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


class SecurityScanner:
    def __init__(self, config_path: str, project_root: str):
        self.config_path = Path(config_path)
        self.project_root = Path(project_root)
        self.config = self._load_config()
        self.findings = []
        self.stats = {
            "files_scanned": 0,
            "total_findings": 0,
            "by_severity": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            }
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """加载 YAML 配置"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _should_exclude(self, file_path: Path) -> bool:
        """检查文件是否应排除"""
        exclude_dirs = self.config.get('scan_config', {}).get('exclude_dirs', [])
        
        # 检查路径中是否包含排除目录
        for exclude_dir in exclude_dirs:
            if exclude_dir in file_path.parts:
                return True
        
        return False
    
    def _get_files_to_scan(self) -> List[Path]:
        """获取需要扫描的文件列表"""
        files = []
        extensions = {'.py', '.js', '.ts', '.vue'}
        
        for root, dirs, filenames in os.walk(self.project_root):
            # 移除排除目录
            dirs[:] = [d for d in dirs if d not in self.config.get('scan_config', {}).get('exclude_dirs', [])]
            
            for filename in filenames:
                file_path = Path(root) / filename
                if file_path.suffix in extensions and not self._should_exclude(file_path):
                    files.append(file_path)
        
        # 限制文件数
        max_files = self.config.get('scan_config', {}).get('max_files', 500)
        return files[:max_files]
    
    def _scan_file(self, file_path: Path, check: Dict[str, Any]) -> List[Dict[str, Any]]:
        """扫描单个文件"""
        findings = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception as e:
            return findings
        
        pattern = check.get('pattern', '')
        try:
            regex = re.compile(pattern)
        except re.error as e:
            print(f"⚠️  正则表达式错误 [{check['id']}]: {e}")
            return findings
        
        for line_num, line in enumerate(lines, 1):
            if regex.search(line):
                findings.append({
                    "check_id": check['id'],
                    "description": check['description'],
                    "severity": check['severity'],
                    "file": str(file_path.relative_to(self.project_root)),
                    "line": line_num,
                    "content": line.strip()[:200],  # 限制长度
                    "message": check.get('message', ''),
                    "fix": check.get('fix', '')
                })
        
        return findings
    
    def scan(self) -> List[Dict[str, Any]]:
        """执行扫描"""
        print("🛡️  安全扫描 - 启动")
        print(f"项目根目录：{self.project_root}")
        print(f"配置文件：{self.config_path}")
        print("")
        
        checks = self.config.get('checks', [])
        files = self._get_files_to_scan()
        
        print(f"扫描配置：")
        print(f"  检查项：{len(checks)}")
        print(f"  文件数：{len(files)}")
        print("")
        
        print("正在扫描...")
        start_time = datetime.now()
        
        for file_path in files:
            self.stats["files_scanned"] += 1
            
            # 确定文件类型匹配的检查项
            file_ext = file_path.suffix
            matching_checks = [
                check for check in checks
                if any(f"*{ext}" in str(file_path) or file_ext in [f"*{ext}" for ext in check.get('files', [])] 
                       for ext in [file_ext])
                or any(file_ext[1:] in f for f in check.get('files', []))
            ]
            
            for check in matching_checks:
                file_findings = self._scan_file(file_path, check)
                self.findings.extend(file_findings)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # 统计
        for finding in self.findings:
            severity = finding['severity']
            self.stats["total_findings"] += 1
            self.stats["by_severity"][severity] += 1
        
        print(f"扫描完成！耗时：{duration:.2f}秒")
        print("")
        
        return self.findings
    
    def generate_human_report(self) -> str:
        """生成人类可读报告"""
        report = []
        report.append("=" * 80)
        report.append("🛡️  安全扫描报告")
        report.append("=" * 80)
        report.append(f"时间：{datetime.now().isoformat()}")
        report.append(f"项目：{self.project_root}")
        report.append(f"配置：{self.config_path}")
        report.append("")
        report.append("-" * 80)
        report.append("📊 扫描摘要")
        report.append("-" * 80)
        report.append(f"扫描文件数：{self.stats['files_scanned']}")
        report.append(f"发现问题数：{self.stats['total_findings']}")
        report.append("")
        report.append("按严重级别：")
        report.append(f"  🔴 Critical: {self.stats['by_severity']['critical']}")
        report.append(f"  🟠 High:      {self.stats['by_severity']['high']}")
        report.append(f"  🟡 Medium:    {self.stats['by_severity']['medium']}")
        report.append(f"  🟢 Low:       {self.stats['by_severity']['low']}")
        report.append("")
        
        # 按严重级别分组
        findings_by_severity = {}
        for finding in self.findings:
            severity = finding['severity']
            if severity not in findings_by_severity:
                findings_by_severity[severity] = []
            findings_by_severity[severity].append(finding)
        
        # 输出每个严重级别的问题
        severity_order = ['critical', 'high', 'medium', 'low']
        severity_icons = {
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🟢'
        }
        
        for severity in severity_order:
            if severity not in findings_by_severity:
                continue
            
            report.append("-" * 80)
            report.append(f"{severity_icons[severity]} {severity.upper()} ({len(findings_by_severity[severity])} 个问题)")
            report.append("-" * 80)
            
            # 按文件分组
            findings_by_file = {}
            for finding in findings_by_severity[severity]:
                file_path = finding['file']
                if file_path not in findings_by_file:
                    findings_by_file[file_path] = []
                findings_by_file[file_path].append(finding)
            
            for file_path, file_findings in sorted(findings_by_file.items()):
                report.append(f"\n📁 {file_path}")
                
                for finding in sorted(file_findings, key=lambda x: x['line']):
                    report.append(f"  行 {finding['line']}: {finding['description']}")
                    report.append(f"    匹配：{finding['content'][:100]}")
                    if finding.get('fix'):
                        report.append(f"    建议：{finding['fix']}")
                    report.append("")
        
        report.append("-" * 80)
        report.append("📋 告警阈值检查")
        report.append("-" * 80)
        
        thresholds = self.config.get('alert_thresholds', {})
        alerts = []
        
        for severity, threshold in thresholds.items():
            count = self.stats['by_severity'].get(severity, 0)
            if count > threshold:
                alerts.append(f"❌ {severity.upper()}: {count} > {threshold} (超出阈值)")
            else:
                alerts.append(f"✅ {severity.upper()}: {count} <= {threshold} (正常)")
        
        for alert in alerts:
            report.append(alert)
        
        report.append("")
        report.append("=" * 80)
        
        if self.stats['total_findings'] == 0:
            report.append("🎉 未发现安全问题！代码质量优秀")
        else:
            report.append(f"⚠️  发现 {self.stats['total_findings']} 个安全问题，建议优先修复 Critical 和 High 级别")
        
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def generate_json_report(self) -> str:
        """生成 JSON 报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "config_path": str(self.config_path),
            "stats": self.stats,
            "findings": self.findings,
            "thresholds": self.config.get('alert_thresholds', {})
        }
        return json.dumps(report, indent=2, ensure_ascii=False)
    
    def save_reports(self, output_dir: str):
        """保存报告"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 人类可读报告
        human_report = self.generate_human_report()
        human_path = output_path / f"security_scan_{timestamp}.txt"
        with open(human_path, 'w', encoding='utf-8') as f:
            f.write(human_report)
        
        # JSON 报告
        json_report = self.generate_json_report()
        json_path = output_path / f"security_scan_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            f.write(json_report)
        
        return human_path, json_path


def main():
    """主函数"""
    # 配置
    config_path = "/home/admin/.openclaw/workspace/SECURITY_CHECKLIST.yml"
    project_root = "/home/admin/.openclaw/workspace/behavior_recorder_service"
    output_dir = "/tmp/security_reports"
    
    # 检查配置文件
    if not Path(config_path).exists():
        print(f"❌ 配置文件不存在：{config_path}")
        sys.exit(1)
    
    # 检查项目目录
    if not Path(project_root).exists():
        print(f"❌ 项目目录不存在：{project_root}")
        sys.exit(1)
    
    # 执行扫描
    scanner = SecurityScanner(config_path, project_root)
    scanner.scan()
    
    # 保存报告
    human_path, json_path = scanner.save_reports(output_dir)
    
    # 打印报告
    print(scanner.generate_human_report())
    print("")
    print(f"📁 报告已保存：")
    print(f"   人类可读：{human_path}")
    print(f"   JSON 格式：{json_path}")
    
    # 检查是否超过阈值
    thresholds = scanner.config.get('alert_thresholds', {})
    has_critical_issues = False
    
    for severity, threshold in thresholds.items():
        count = scanner.stats['by_severity'].get(severity, 0)
        if count > threshold:
            has_critical_issues = True
    
    # 退出码
    sys.exit(1 if has_critical_issues else 0)


if __name__ == "__main__":
    main()
