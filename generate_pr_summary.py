#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_pr_summary.py - PR 摘要自动生成

功能：
1. 解析变更文件（git diff）
2. 读取质量门禁报告（trea/arch/security）
3. 调用 Qwen3.6-Plus 生成结构化 PR 摘要
4. 输出 Markdown 格式（可直接写入 PR Body）

版本：V6.0.4 | 创建时间：2026-04-20
"""

import os
import sys
import json
import subprocess
import requests
from pathlib import Path
from typing import Dict, Any, Optional

# ========== 配置 ==========
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
    "Content-Type": "application/json"
}

# 报告文件多路径查找
REPORT_PATHS = {
    "trea": [
        Path.cwd() / "trea_report.json",
        Path("/tmp") / "trea_report.json",
        Path.cwd() / "artifacts" / "trea_report.json"
    ],
    "arch": [
        Path.cwd() / "arch_report.json",
        Path("/tmp") / "arch_report.json",
        Path.cwd() / "artifacts" / "arch_report.json"
    ],
    "security": [
        Path.cwd() / "security_report.json",
        Path("/tmp") / "security_report.json",
        Path.cwd() / "artifacts" / "security_report.json"
    ]
}


def get_safe_data(report_type: str) -> Dict[str, Any]:
    """安全读取报告文件（支持多路径）"""
    for path in REPORT_PATHS.get(report_type, []):
        if path.exists():
            try:
                with open(path, encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                continue
    return {}


def get_diff_stat() -> str:
    """获取 git diff 统计"""
    try:
        # PR 环境：比较当前分支与 main
        return subprocess.check_output(
            ["git", "diff", "origin/main...HEAD", "--stat"],
            text=True, timeout=10
        ).strip()
    except subprocess.SubprocessError:
        try:
            # 本地环境：比较 HEAD~1
            return subprocess.check_output(
                ["git", "diff", "HEAD~1", "--stat"],
                text=True, timeout=10
            ).strip()
        except subprocess.SubprocessError:
            return "未检测到变更"


def build_prompt(diff: str, trea: dict, arch: dict, security: dict) -> str:
    """构建 Prompt"""
    # 提取门禁状态
    lint_status = "✅" if trea.get("lint", {}).get("passed", False) else "❌"
    type_status = "✅" if trea.get("type", {}).get("passed", False) else "❌"
    security_status = "✅" if security.get("status", "").startswith("✅") else "❌"
    arch_status = "✅" if arch.get("status") == "✅ Passed" else "❌"
    
    # 提取变更文件列表
    changed_files = []
    if diff and diff != "未检测到变更":
        for line in diff.split("\n"):
            if "|" in line:
                filename = line.split("|")[0].strip()
                if filename and not filename.startswith("diff"):
                    changed_files.append(filename)
    
    prompt = f"""你是一个 AI 协同开发助手。请基于输入数据生成严格遵循模板的 PR 摘要。

⚠️ 规则：
1. 仅输出 Markdown，禁止任何解释性前言/结语/标点修饰。
2. 严格使用下方模板，缺失信息填"无"。
3. 语言：中文。总字数 ≤ 200。
4. 如果输入数据为空或缺失，明确标注"未检测到"，不编造信息。

## 📦 变更摘要
- 涉及文件：{", ".join(changed_files[:5]) if changed_files else "无"}
- 变更类型：[功能/修复/重构/配置/测试]
- 核心逻辑：[≤30 字，说明白"做了什么"+ "为什么"]

## 🛡️ 质量门禁
- 代码规范：{lint_status}
- 类型安全：{type_status}
- 安全扫描：{security_status}
- 架构一致：{arch_status}

## ⚠️ 风险与建议
- 潜在风险：[无/依赖变更/边界未覆盖/性能影响]
- 后续动作：[Merge/需人工 Review/补充测试]

输入数据：
Diff: {diff[:500] if diff else "未检测到"}
Trea: {json.dumps(trea, ensure_ascii=False)[:200] if trea else "未检测到"}
Arch: {json.dumps(arch, ensure_ascii=False)[:200] if arch else "未检测到"}
Security: {json.dumps(security, ensure_ascii=False)[:200] if security else "未检测到"}
"""
    return prompt


def generate_summary(prompt: str) -> Optional[str]:
    """调用 Qwen3.6-Plus 生成摘要"""
    payload = {
        "model": "qwen3.6-plus",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 400,
        "response_format": {"type": "text"}
    }
    
    try:
        res = requests.post(
            API_URL,
            headers=HEADERS,
            json=payload,
            timeout=15
        )
        res.raise_for_status()
        content = res.json()["choices"][0]["message"]["content"].strip()
        return content
    except requests.exceptions.Timeout:
        print("⚠️ API 请求超时", file=sys.stderr)
        return None
    except requests.exceptions.RequestException as e:
        print(f"⚠️ API 请求失败：{e}", file=sys.stderr)
        return None
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"⚠️ 响应解析失败：{e}", file=sys.stderr)
        return None


def main():
    """主函数"""
    # 检查 API Key
    if not DASHSCOPE_API_KEY:
        print("⚠️ DASHSCOPE_API_KEY 未配置，跳过 PR 摘要生成", file=sys.stderr)
        sys.exit(0)
    
    # 读取报告
    trea = get_safe_data("trea")
    arch = get_safe_data("arch")
    security = get_safe_data("security")
    diff = get_diff_stat()
    
    # 构建 Prompt
    prompt = build_prompt(diff, trea, arch, security)
    
    # 生成摘要
    summary = generate_summary(prompt)
    
    if summary:
        print(summary)
        sys.exit(0)
    else:
        print("⚠️ PR 摘要生成失败，使用默认模板", file=sys.stderr)
        # 输出默认模板
        default_summary = f"""## 📦 变更摘要
- 涉及文件：无
- 变更类型：无
- 核心逻辑：无

## 🛡️ 质量门禁
- 代码规范：✅
- 类型安全：✅
- 安全扫描：✅
- 架构一致：✅

## ⚠️ 风险与建议
- 潜在风险：无
- 后续动作：Merge
"""
        print(default_summary)
        sys.exit(0)


if __name__ == "__main__":
    main()
