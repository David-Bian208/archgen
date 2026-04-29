#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metrics_dashboard_lite.py - ROI 看板生成器（简化版）

功能：
1. 统计 CI 运行次数
2. 统计门禁通过率
3. 估算 Token 消耗
4. 生成 Markdown 报表

特点：
- ✅ 零外部依赖（无需 CSV/API）
- ✅ 完全自动化（CI 集成）
- ✅ 可持续性（无需人工干预）

版本：V6.0.4 | 创建时间：2026-04-20
"""

import os
import sys
import json
import datetime
from pathlib import Path
from typing import Dict, Any, List

# ========== 配置 ==========
CONFIG = {
    "trea_report": "trea_report.json",
    "arch_report": "arch_report.json",
    "security_report": "security_report.json",
    "lessons_file": ".claw/lessons_learned.md",
    "output_file": "roi_report.md",
    # Token 估算（基于历史平均值）
    "avg_tokens_per_run": 50000,  # 每次 CI 运行平均 Token 消耗
    "input_price": 0.002,  # 元/千 tokens
    "output_price": 0.008,  # 元/千 tokens
}


def safe_load_json(path: str) -> Dict[str, Any]:
    """安全读取 JSON 文件"""
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def count_lessons() -> int:
    """统计失败样本数量"""
    lessons_path = Path(CONFIG["lessons_file"])
    if not lessons_path.exists():
        return 0
    
    try:
        with open(lessons_path, encoding='utf-8') as f:
            # 统计以 "### " 开头的行数（每个样本一个章节）
            return sum(1 for line in f if line.strip().startswith("### "))
    except IOError:
        return 0


def calculate_quality_score(trea: dict, arch: dict, security: dict) -> float:
    """计算质量评分（0-100）"""
    scores = []
    
    # Trea 门禁（Lint + Type + Security）
    if trea.get("lint", {}).get("passed", False):
        scores.append(1)
    if trea.get("type", {}).get("passed", False):
        scores.append(1)
    if trea.get("security", {}).get("passed", False):
        scores.append(1)
    
    # Arch 门禁
    if arch.get("status") == "✅ Passed":
        scores.append(1)
    
    # Security 门禁
    if security.get("status", "").startswith("✅"):
        scores.append(1)
    
    if not scores:
        return 0.0
    
    return sum(scores) / len(scores) * 100


def get_ci_info() -> Dict[str, str]:
    """获取 CI 环境信息"""
    return {
        "run_id": os.getenv("GITHUB_RUN_ID", "local"),
        "job_name": os.getenv("GITHUB_JOB", "quality-gate"),
        "workflow": os.getenv("GITHUB_WORKFLOW", "AI-Driven Quality Pipeline"),
        "ref": os.getenv("GITHUB_REF", "unknown"),
        "sha": os.getenv("GITHUB_SHA", "unknown")[:7]
    }


def estimate_tokens() -> Dict[str, int]:
    """估算 Token 消耗"""
    # 基于历史平均值估算
    input_tokens = int(CONFIG["avg_tokens_per_run"] * 0.7)  # 输入占 70%
    output_tokens = int(CONFIG["avg_tokens_per_run"] * 0.3)  # 输出占 30%
    
    return {
        "input": input_tokens,
        "output": output_tokens,
        "total": input_tokens + output_tokens
    }


def calculate_cost(tokens: Dict[str, int]) -> Dict[str, float]:
    """计算成本（考虑节省计划）"""
    # 简化计算：假设在节省计划额度内
    input_cost = tokens["input"] / 1000 * CONFIG["input_price"]
    output_cost = tokens["output"] / 1000 * CONFIG["output_price"]
    
    return {
        "input": round(input_cost, 2),
        "output": round(output_cost, 2),
        "total": round(input_cost + output_cost, 2)
    }


def calculate_roi(quality_score: float, cost: float) -> str:
    """计算 ROI 评级"""
    # 简化版评级标准
    if quality_score >= 80 and cost <= 1.0:  # 质量≥80% 且 成本≤¥1
        return "优秀 ✅"
    elif quality_score >= 60 and cost <= 2.0:  # 质量≥60% 且 成本≤¥2
        return "良好 ⚠️"
    else:
        return "待优化 ❌"


def generate_markdown_report(
    ci_info: dict,
    quality_score: float,
    tokens: dict,
    cost: dict,
    roi: str,
    lessons_count: int
) -> str:
    """生成 Markdown 报表"""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    lines = [
        f"## 📊 AI 协同 ROI 看板（简化版）",
        f"",
        f"**生成时间：** {now}",
        f"**CI 运行 ID：** {ci_info['run_id']}",
        f"**工作流：** {ci_info['workflow']}",
        f"**分支/提交：** {ci_info['ref']} / {ci_info['sha']}",
        f"",
        f"### 📈 核心指标",
        f"",
        f"| 指标 | 数值 | 说明 |",
        f"|------|------|------|",
        f"| 质量门禁通过率 | {quality_score:.1f}% | Lint/Type/Security/Arch 综合 |",
        f"| 估算 Token 消耗 | {tokens['total']:,} | 输入+输出 |",
        f"| 估算成本 | ¥{cost['total']:.2f} | 按 Qwen3.6-Plus 计价（额度内） |",
        f"| 失败样本沉淀 | {lessons_count} 条 | lessons_learned.md 累计 |",
        f"| ROI 评级 | {roi} | 质量≥80% 且 成本≤¥1 为优秀 |",
        f"",
        f"### 💡 自动调优建议",
        f"",
    ]
    
    # 根据指标生成建议
    suggestions = []
    
    if quality_score < 80:
        suggestions.append("- **质量门禁通过率低**：检查失败用例，将修复方案追加至 `.claw/lessons_learned.md`")
    
    if cost["total"] > 1.0:
        suggestions.append("- **Token 消耗偏高**：优化 Prompt，减少冗余历史，启用上下文压缩")
    
    if lessons_count == 0:
        suggestions.append("- **失败样本库为空**：建议积累≥10 个样本后分析共性模式")
    
    if not suggestions:
        suggestions.append("- ✅ 各项指标良好，继续保持！")
    
    lines.extend(suggestions)
    
    lines.extend([
        f"",
        f"### 📝 备注",
        f"",
        f"- 本报表为**简化版**，基于本地门禁报告生成，无需外部 CSV/API",
        f"- Token 消耗为**估算值**（平均 5 万 tokens/次），实际值请参考百炼控制台",
        f"- 成本计算**已考虑节省计划**（135 元包季版），显示为额度内边际成本",
        f"",
        f"---",
        f"",
        f"**生成工具：** metrics_dashboard_lite.py V6.0.4"
    ])
    
    return "\n".join(lines)


def main():
    """主函数"""
    print("📊 AI 协同 ROI 看板生成器（简化版）")
    print("=" * 50)
    
    # 1. 读取报告
    print("📝 读取质量门禁报告...")
    trea = safe_load_json(CONFIG["trea_report"])
    arch = safe_load_json(CONFIG["arch_report"])
    security = safe_load_json(CONFIG["security_report"])
    
    # 2. 获取 CI 信息
    print("🔍 获取 CI 环境信息...")
    ci_info = get_ci_info()
    
    # 3. 计算质量评分
    print("📊 计算质量评分...")
    quality_score = calculate_quality_score(trea, arch, security)
    
    # 4. 估算 Token
    print("💰 估算 Token 消耗...")
    tokens = estimate_tokens()
    
    # 5. 计算成本
    cost = calculate_cost(tokens)
    
    # 6. 计算 ROI
    roi = calculate_roi(quality_score, cost["total"])
    
    # 7. 统计失败样本
    lessons_count = count_lessons()
    
    # 8. 生成报表
    print("📝 生成 Markdown 报表...")
    report = generate_markdown_report(
        ci_info,
        quality_score,
        tokens,
        cost,
        roi,
        lessons_count
    )
    
    # 9. 输出
    print("\n" + "=" * 50)
    print(report)
    
    # 10. 保存
    output_path = Path(CONFIG["output_file"])
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n✅ 报表已保存至：{output_path}")
    except IOError as e:
        print(f"\n⚠️ 保存失败：{e}", file=sys.stderr)
    
    # 11. 退出码
    if quality_score >= 80:
        sys.exit(0)
    else:
        print(f"\n⚠️ 质量评分低于 80%：{quality_score:.1f}%", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
