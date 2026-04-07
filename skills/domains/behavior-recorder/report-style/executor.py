"""
report-style Skill 执行器

报告风格检查（行为观察伙伴专用）
"""


def check_report_style(report_text: str) -> str:
    """检查报告风格"""
    checks = {
        "视角": {"passed": True, "issues": []},
        "能力描述": {"passed": True, "issues": []},
        "干预用词": {"passed": True, "issues": []},
        "句子长度": {"passed": True, "issues": []},
        "比喻": {"passed": True, "issues": []},
    }
    
    # 检查视角（避免"临床上通常"）
    if "临床上通常" in report_text or "临床上" in report_text:
        checks["视角"]["passed"] = False
        checks["视角"]["issues"].append("发现说教感表述：'临床上'")
    
    # 检查能力描述（避免"不会"）
    if "不会" in report_text and "还没学会" not in report_text:
        checks["能力描述"]["passed"] = False
        checks["能力描述"]["issues"].append("建议使用'还没学会'而非'不会'")
    
    # 检查干预用词（避免"训练"）
    if "训练" in report_text and "练习" not in report_text:
        checks["干预用词"]["passed"] = False
        checks["干预用词"]["issues"].append("建议使用'练习'而非'训练'")
    
    # 检查句子长度
    sentences = report_text.replace('\n', ' ').split('。')
    long_sentences = [s for s in sentences if len(s.strip()) > 30]
    if long_sentences:
        checks["句子长度"]["passed"] = False
        checks["句子长度"]["issues"].append(f"发现{len(long_sentences)}个长句（>30 字）")
    
    # 检查通用比喻
    generic_metaphors = ["社交雷达", "像", "如同", "仿佛"]
    found_metaphors = [m for m in generic_metaphors if m in report_text]
    if found_metaphors:
        checks["比喻"]["passed"] = False
        checks["比喻"]["issues"].append(f"发现通用比喻：{', '.join(found_metaphors)}")
    
    # 生成报告
    passed_count = sum(1 for c in checks.values() if c["passed"])
    total_count = len(checks)
    
    lines = ["📋 报告风格检查\n"]
    lines.append(f"**检查项：** {total_count}项")
    lines.append(f"**通过：** {passed_count}/{total_count}\n")
    lines.append("**检查结果：**\n")
    
    for check_name, result in checks.items():
        status = "✅" if result["passed"] else "❌"
        lines.append(f"{status} {check_name}: {result['issues'][0] if result['issues'] else '通过'}")
    
    # 修改建议
    all_issues = []
    for check_name, result in checks.items():
        all_issues.extend(result["issues"])
    
    if all_issues:
        lines.append("\n**修改建议：**")
        for i, issue in enumerate(all_issues, 1):
            lines.append(f"{i}. {issue}")
    
    return "\n".join(lines)


def get_style_guidelines() -> str:
    """获取风格指南"""
    return """
📋 报告风格指南

**核心原则：**
1. 用"我们"视角 - "从玥玥的表现来看，我们觉得..."
2. 能力发展视角 - "还没学会"而不是"不会"
3. 用"练习"而不是"训练"
4. 短句优先 - 每句<30 字
5. 避免通用比喻 - 用具体行为细节

**避免的表述：**
- ❌ "临床上通常考虑几种可能性"
- ❌ "孩子不会社交"
- ❌ "需要进行社交训练"
- ❌ "社交雷达"等模板化比喻

**推荐的表述：**
- ✅ "从玥玥的表现来看，我们觉得..."
- ✅ "孩子还没学会这个社交技能"
- ✅ "可以一起练习这个技能"
- ✅ 具体行为细节描述
"""


def execute(command: str) -> str:
    """执行命令"""
    cmd = command.lower()
    
    if "检查" in cmd and "风格" in cmd:
        # 需要报告文本
        return "📝 请提供要检查的报告文本"
    
    if "指南" in cmd or "要求" in cmd or "规范" in cmd:
        return get_style_guidelines()
    
    return """
📋 report-style Skill

**可用命令：**
- 检查这个报告的风格
- 报告风格有哪些要求
- 避免哪些表述

**示例：**
- 检查这个报告的风格：[报告文本]
- 报告风格有哪些要求
"""


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
    else:
        command = input("输入命令：")
    
    print(execute(command))
