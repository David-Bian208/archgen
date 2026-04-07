"""
safety-check Skill 执行器

安全关键词检测（行为观察伙伴专用）
"""


# 安全关键词列表
DANGER_KEYWORDS_HIGH = [
    "爬高", "危险", "利器", "冲撞", "跑到马路", "触电", "溺水", "水池",
    "从高处", "跳下", "攀爬", "窗户", "阳台", "烫",
    "尖锐", "刀子", "剪刀", "电源", "插座", "车祸", "交通"
]

DANGER_KEYWORDS_CONTEXT = {
    "火": ["玩火", "点火", "烧", "火灾", "打火机", "火柴"],
}

EXCLUDED_CONTEXTS = ["发火", "生气", "脾气"]  # 排除"发脾气"误报


def check_safety(behavior_text: str) -> str:
    """检查行为安全性"""
    found_high = []
    found_context = []
    
    # 检查高优先级关键词
    for keyword in DANGER_KEYWORDS_HIGH:
        if keyword in behavior_text:
            found_high.append(keyword)
    
    # 检查需要上下文的关键词
    for keyword, contexts in DANGER_KEYWORDS_CONTEXT.items():
        if keyword in behavior_text:
            has_danger_context = any(ctx in behavior_text for ctx in contexts)
            has_excluded = any(excl in behavior_text for excl in EXCLUDED_CONTEXTS)
            
            if has_danger_context and not has_excluded:
                found_context.append(f"{keyword} + 危险上下文")
    
    # 生成报告
    is_dangerous = len(found_high) > 0 or len(found_context) > 0
    
    lines = ["⚠️ 安全检测\n"]
    lines.append(f"**行为描述：** {behavior_text[:100]}")
    lines.append(f"**检测结果：** {'⚠️ 危险' if is_dangerous else '✅ 安全'}\n")
    
    if found_high:
        lines.append("**触发关键词（高优先级）：**")
        for kw in found_high:
            lines.append(f"- {kw}")
        lines.append("")
    
    if found_context:
        lines.append("**触发关键词（上下文确认）：**")
        for kw in found_context:
            lines.append(f"- {kw}")
        lines.append("")
    
    if is_dangerous:
        lines.append("**建议：**")
        lines.append("启用安全优先模式，优先处理安全问题")
        lines.append("⚠️ 重要：对于危险行为，绝不能简单'忽视'")
    else:
        lines.append("**建议：**")
        lines.append("行为安全，可按正常流程处理")
    
    return "\n".join(lines)


def get_safety_keywords() -> str:
    """获取安全关键词列表"""
    lines = ["📋 安全关键词列表\n"]
    
    lines.append("**高优先级（直接触发）：**")
    lines.append("```")
    lines.append(", ".join(DANGER_KEYWORDS_HIGH))
    lines.append("```\n")
    
    lines.append("**需要上下文确认：**")
    for keyword, contexts in DANGER_KEYWORDS_CONTEXT.items():
        lines.append(f"- {keyword}: {', '.join(contexts)}")
    
    lines.append("\n**排除上下文（避免误报）：**")
    lines.append(", ".join(EXCLUDED_CONTEXTS))
    
    return "\n".join(lines)


def execute(command: str) -> str:
    """执行命令"""
    cmd = command.lower()
    
    if "检查" in cmd and ("安全" in cmd or "危险" in cmd):
        # 提取行为描述
        if "：" in command or ":" in command:
            parts = command.split("：" if "：" in command else ":")
            if len(parts) > 1:
                behavior = parts[1].strip()
                return check_safety(behavior)
        return "📝 请提供要检查的行为描述"
    
    if "关键词" in cmd or "列表" in cmd:
        return get_safety_keywords()
    
    return """
⚠️ safety-check Skill

**可用命令：**
- 检查这个行为是否安全：[行为描述]
- 有危险吗：[行为描述]
- 安全规则有哪些
- 危险关键词列表

**示例：**
- 检查这个行为是否安全：小明看到打火机想拿起来玩火
- 有危险吗：小明爬高
- 危险关键词列表
"""


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
    else:
        command = input("输入命令：")
    
    print(execute(command))
