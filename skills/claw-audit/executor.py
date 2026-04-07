"""
claw-audit Skill 执行器

提供自然语言接口调用 claw-code 架构优化模块
"""

import sys
from pathlib import Path

# 添加路径
WORKSPACE = Path(__file__).parent.parent.parent
BEHAVIOR_RECORDER = WORKSPACE / "behavior_recorder_service"
sys.path.insert(0, str(WORKSPACE))
sys.path.insert(0, str(BEHAVIOR_RECORDER))


def run_parity_audit() -> str:
    """运行覆盖率审计"""
    try:
        import sys
        from pathlib import Path
        br_path = Path(__file__).parent.parent.parent / "behavior_recorder_service"
        sys.path.insert(0, str(br_path))
        sys.path.insert(0, str(br_path / "tests"))
        
        from parity_audit import run_clinical_parity_audit
        
        result = run_clinical_parity_audit()
        report = result.to_markdown()
        
        # 保存到桌面
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d")
        report_path = Path.home() / "Desktop" / f"临床功能覆盖率审计报告_{timestamp}.md"
        report_path.write_text(report, encoding='utf-8')
        
        deployable = "✅ 系统可部署" if result.is_deployable() else "❌ 系统不可部署"
        
        return f"{report}\n\n**结论：** {deployable}\n\n📄 报告已保存到：{report_path}"
    except Exception as e:
        return f"❌ 审计失败：{str(e)}"


def analyze_behavior(text: str) -> str:
    """分析行为描述，匹配临床规则"""
    try:
        from app.knowledge.clinical_rules_registry import get_clinical_rules_registry
        
        registry = get_clinical_rules_registry()
        matches = registry.evaluate(text)
        
        if not matches:
            return "🔍 未匹配到临床规则"
        
        lines = ["🔍 **临床规则匹配结果**\n"]
        lines.append(f"匹配到 **{len(matches)}** 条规则：\n")
        
        for i, match in enumerate(matches[:5], 1):
            confidence_emoji = "⚠️" if match.confidence >= 0.9 else "📌"
            lines.append(f"{i}. {confidence_emoji} **{match.rule.name}** (置信度：{match.confidence})")
            lines.append(f"   - 类别：{match.rule.category.value}")
            lines.append(f"   - 假设：{match.rule.hypothesis}")
            lines.append("")
        
        # 安全检查
        safety_matches = [m for m in matches if m.rule.category.value == "safety"]
        if safety_matches:
            lines.append("⚠️ **检测到危险行为，建议优先处理安全问题！**\n")
        
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 分析失败：{str(e)}"


def list_tools(category: str = None) -> str:
    """列出工具"""
    try:
        from tool_registry import get_tool_registry, ToolCategory
        
        registry = get_tool_registry()
        
        if category:
            cat_map = {
                "browser": ToolCategory.BROWSER,
                "file": ToolCategory.FILE,
                "shell": ToolCategory.SHELL,
                "memory": ToolCategory.MEMORY,
                "session": ToolCategory.SESSION,
                "web": ToolCategory.WEB,
                "message": ToolCategory.MESSAGE,
            }
            cat = cat_map.get(category.lower())
            if cat:
                tools = registry.list_by_category(cat)
            else:
                tools = registry.search(category)
        else:
            tools = registry.list_all()
        
        lines = ["🛠️ **工具列表**\n"]
        lines.append(f"共 **{len(tools)}** 个工具：\n")
        
        for tool in tools:
            permission_emoji = {
                "public": "🌐",
                "user": "👤",
                "admin": "🔐",
                "dangerous": "⚠️",
            }.get(tool.permission.value, "📌")
            
            lines.append(f"{permission_emoji} **{tool.name}** (`{tool.id}`)")
            lines.append(f"   - 描述：{tool.description}")
            lines.append(f"   - 权限：{tool.permission.value}")
            if tool.examples:
                lines.append(f"   - 示例：{tool.examples[0]}")
            lines.append("")
        
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 查询失败：{str(e)}"


def search_tools(query: str) -> str:
    """搜索工具"""
    try:
        from tool_registry import get_tool_registry
        
        registry = get_tool_registry()
        matches = registry.search(query, limit=10)
        
        if not matches:
            return f"🔍 未找到匹配 '{query}' 的工具"
        
        lines = [f"🔍 搜索 '**{query}**' 的工具（{len(matches)} 个结果）\n"]
        
        for tool in matches:
            lines.append(f"- **{tool.name}** (`{tool.id}`): {tool.description}")
        
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 搜索失败：{str(e)}"


def get_tool_stats() -> str:
    """获取工具统计"""
    try:
        from tool_registry import get_tool_registry
        
        registry = get_tool_registry()
        stats = registry.get_statistics()
        
        lines = ["📊 **工具注册表统计**\n"]
        lines.append(f"**工具总数：** {stats['total_tools']}\n")
        lines.append("**按类别分布：**\n")
        
        for cat, count in stats['by_category'].items():
            lines.append(f"- {cat}: {count}")
        
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 统计失败：{str(e)}"


def run_workflow(mode: str, task: str, **kwargs) -> str:
    """运行工作流"""
    try:
        from workflow_orchestrator import get_workflow_orchestrator
        
        orchestrator = get_workflow_orchestrator()
        
        if mode.lower() == "collaborate":
            agents = kwargs.get("agents", ["agent-1", "agent-2"])
            result = orchestrator.collaborate(task=task, agents=agents)
            
            lines = ["🎭 **COLLABORATE 模式完成**\n"]
            lines.append(f"- 任务：{task[:50]}...")
            lines.append(f"- 代理数：{len(result.agent_results)}")
            lines.append(f"- 成功：{result.success}")
            lines.append(f"- 执行时间：{result.execution_time_seconds:.2f}s")
            lines.append(f"\n**合并输出：**\n{result.merged_output[:500]}")
            
        elif mode.lower() == "persistent":
            max_turns = kwargs.get("max_turns", 5)
            result = orchestrator.persistent(task=task, max_turns=max_turns)
            
            lines = ["🔄 **PERSISTENT 模式完成**\n"]
            lines.append(f"- 任务：{task[:50]}...")
            lines.append(f"- 轮次：{result.turns}/{max_turns}")
            lines.append(f"- 完成：{result.completed}")
            lines.append(f"- 停止原因：{result.stop_reason}")
            lines.append(f"\n**最终输出：**\n{result.final_output[:500]}")
            
        elif mode.lower() == "review":
            criteria = kwargs.get("criteria", ["准确性", "完整性", "可读性"])
            result = orchestrator.review(output=task, criteria=criteria)
            
            lines = ["🔍 **REVIEW 模式完成**\n"]
            lines.append(f"- 审查标准：{', '.join(criteria)}")
            lines.append(f"- 总体分数：{result.overall_score:.2%}")
            lines.append(f"- 通过：{result.passed}")
            lines.append(f"\n**审查结果：**\n")
            for criterion, cr in result.criteria_results.items():
                status = "✅" if cr.get("passed") else "❌"
                lines.append(f"{status} {criterion}: {cr.get('score', 0):.2%}")
            if result.suggestions:
                lines.append(f"\n**建议：**\n" + "\n".join(f"- {s}" for s in result.suggestions[:5]))
            
        else:
            return f"❌ 未知模式：{mode}。支持：collaborate, persistent, review"
        
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 工作流执行失败：{str(e)}"


def get_help() -> str:
    """获取帮助"""
    return """
# 🛠️ claw-audit Skill 帮助

## 可用命令

### 覆盖率审计
- `运行覆盖率审计` - 运行临床功能覆盖率审计
- `检查系统覆盖率` - 同上
- `生成审计报告` - 生成 Markdown 审计报告
- `系统可以部署吗` - 判断系统是否可部署

### 行为分析
- `分析这个行为：[行为描述]` - 匹配临床规则
- `匹配临床规则：[行为描述]` - 同上
- `有哪些安全规则` - 列出安全规则
- `规则注册表统计` - 显示规则统计

### 工具查询
- `列出所有工具` - 显示所有工具
- `文件工具有哪些` - 按类别列出工具
- `搜索工具：[关键词]` - 搜索工具
- `工具注册表统计` - 显示工具统计

### 工作流编排
- `多代理协作：[任务]` - COLLABORATE 模式
- `持续执行：[任务]` - PERSISTENT 模式
- `审查这个输出：[文本]` - REVIEW 模式

## 示例

```
运行覆盖率审计
分析这个行为：小明看到打火机想拿起来玩火
列出所有工具
文件工具有哪些
搜索工具：记忆
多代理协作：分析这个代码库
```
"""


def execute(command: str) -> str:
    """
    执行自然语言命令
    
    Args:
        command: 自然语言命令
        
    Returns:
        执行结果
    """
    cmd = command.strip().lower()
    
    # 覆盖率审计
    if any(kw in cmd for kw in ["覆盖率审计", "检查系统覆盖率", "生成审计报告"]):
        return run_parity_audit()
    
    if "系统可以部署吗" in cmd or "可以部署吗" in cmd:
        result = run_parity_audit()
        return result
    
    # 行为分析
    if "分析这个行为" in cmd or "分析行为" in cmd:
        text = command.split("：")[-1] if "：" in command else command.split(":")[-1]
        return analyze_behavior(text)
    
    if "匹配临床规则" in cmd:
        text = command.split("：")[-1] if "：" in command else command.split(":")[-1]
        return analyze_behavior(text)
    
    if "有哪些安全规则" in cmd:
        return list_tools("safety")
    
    if "规则注册表统计" in cmd:
        from app.knowledge.clinical_rules_registry import get_clinical_rules_registry
        registry = get_clinical_rules_registry()
        stats = registry.get_statistics()
        return f"📊 规则统计\n\n**规则总数：** {stats['total_rules']}\n\n**按类别：**\n" + "\n".join(f"- {k}: {v}" for k, v in stats['by_category'].items())
    
    # 工具查询
    if "列出所有工具" in cmd:
        return list_tools()
    
    if "工具工具有哪些" in cmd or "文件工具" in cmd:
        return list_tools("file")
    
    if "搜索工具" in cmd:
        query = command.split("：")[-1] if "：" in command else command.split(":")[-1]
        return search_tools(query)
    
    if "工具注册表统计" in cmd:
        return get_tool_stats()
    
    # 工作流
    if "多代理协作" in cmd:
        task = command.split("：")[-1] if "：" in command else command.split(":")[-1]
        return run_workflow("collaborate", task)
    
    if "持续执行" in cmd:
        task = command.split("：")[-1] if "：" in command else command.split(":")[-1]
        return run_workflow("persistent", task)
    
    if "审查这个输出" in cmd or "审查输出" in cmd:
        text = command.split("：")[-1] if "：" in command else command.split(":")[-1]
        return run_workflow("review", text)
    
    # 帮助
    if "帮助" in cmd or "help" in cmd:
        return get_help()
    
    return "❓ 未知命令。输入'帮助'查看可用命令。"


# CLI 入口
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
    else:
        command = input("输入命令：")
    
    print(execute(command))
