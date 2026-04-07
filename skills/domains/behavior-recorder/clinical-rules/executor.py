"""
clinical-rules Skill 执行器

临床规则查询（行为观察伙伴专用）
"""

import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))


def list_rules(category: str = None) -> str:
    """列出临床规则"""
    try:
        from behavior_recorder_service.app.knowledge.clinical_rules_registry import (
            get_clinical_rules_registry,
            RuleCategory,
        )
        
        registry = get_clinical_rules_registry()
        
        if category:
            cat_map = {
                "safety": RuleCategory.SAFETY,
                "social": RuleCategory.SOCIAL,
                "rigidity": RuleCategory.RIGIDITY,
                "sensory": RuleCategory.SENSORY,
                "avoidance": RuleCategory.AVOIDANCE,
                "attention": RuleCategory.ATTENTION,
                "prompt_dependent": RuleCategory.PROMPT_DEPENDENT,
            }
            cat = cat_map.get(category.lower())
            if cat:
                rules = registry.list_by_category(cat)
            else:
                rules = registry.search(category)
        else:
            rules = registry.list_all()
        
        lines = ["📋 临床规则查询\n"]
        
        if category:
            lines.append(f"**类别：** {category}")
        
        lines.append(f"**规则数量：** {len(rules)}\n")
        lines.append("**规则列表：**\n")
        
        for i, rule in enumerate(rules, 1):
            lines.append(f"{i}. **{rule.name}**")
            lines.append(f"   - 类别：{rule.category.value}")
            lines.append(f"   - 假设：{rule.hypothesis}")
            lines.append(f"   - 置信度：{rule.confidence}")
            lines.append("")
        
        return "\n".join(lines)
    
    except Exception as e:
        return f"❌ 查询失败：{str(e)}"


def get_rule_detail(rule_name: str) -> str:
    """获取规则详情"""
    try:
        from behavior_recorder_service.app.knowledge.clinical_rules_registry import (
            get_clinical_rules_registry,
        )
        
        registry = get_clinical_rules_registry()
        
        # 查找规则
        rules = registry.list_all()
        matched = None
        
        for rule in rules:
            if rule_name.lower() in rule.name.lower():
                matched = rule
                break
        
        if not matched:
            return f"❌ 未找到规则：{rule_name}"
        
        lines = ["📋 规则详情\n"]
        lines.append(f"**规则名：** {matched.name}")
        lines.append(f"**类别：** {matched.category.value}")
        lines.append(f"**假设：** {matched.hypothesis}")
        lines.append(f"**置信度：** {matched.confidence}")
        lines.append(f"**描述：** {matched.description}")
        lines.append(f"\n**关键词：** {', '.join(matched.condition_keywords)}")
        
        if matched.exclude_keywords:
            lines.append(f"\n**排除词：** {', '.join(matched.exclude_keywords)}")
        
        return "\n".join(lines)
    
    except Exception as e:
        return f"❌ 查询失败：{str(e)}"


def execute(command: str) -> str:
    """执行命令"""
    cmd = command.lower()
    
    if "查询" in cmd and "规则" in cmd:
        # 提取类别
        category = None
        for cat in ["safety", "social", "rigidity", "sensory", "avoidance", "attention", "prompt_dependent"]:
            if cat in cmd:
                category = cat
                break
        return list_rules(category)
    
    if "详情" in cmd or "干预方向" in cmd:
        # 提取规则名
        return get_rule_detail("规则")
    
    return """
📋 clinical-rules Skill

**可用命令：**
- 查询临床规则
- 查询安全规则
- 查询社交规则
- [规则名] 的详情

**示例：**
- 查询临床规则
- 查询安全规则
- 火源危险检测的详情
"""


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
    else:
        command = input("输入命令：")
    
    print(execute(command))
