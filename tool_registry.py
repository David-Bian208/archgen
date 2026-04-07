"""
OpenClaw 工具注册表 (Tool Registry)

灵感来源：claw-code 项目的 tools.py / execution_registry.py
用途：统一工具管理、发现、权限检查、执行追踪

核心设计：
1. 工具元数据与执行逻辑分离
2. 统一的工具数据结构
3. 支持工具覆盖率审计
4. 便于新增工具

使用方式：
    from workspace.tool_registry import get_tool_registry
    
    registry = get_tool_registry()
    
    # 列出所有工具
    tools = registry.list_all()
    
    # 查找工具
    tool = registry.get("browser")
    
    # 执行工具
    result = registry.execute("browser", action="snapshot", url="https://example.com")
    
    # 统计信息
    stats = registry.get_statistics()
"""

import logging
from dataclasses import dataclass, field
from typing import Callable, List, Dict, Any, Optional, Tuple
from enum import Enum
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class ToolCategory(str, Enum):
    """工具类别"""
    BROWSER = "browser"           # 浏览器控制
    FILE = "file"                 # 文件操作
    SHELL = "shell"               #  shell 命令
    MEMORY = "memory"             # 记忆管理
    SESSION = "session"           # 会话管理
    WEB = "web"                   # 网络工具
    MESSAGE = "message"           # 消息工具
    SYSTEM = "system"             # 系统工具
    CUSTOM = "custom"             # 自定义工具


class ToolPermission(str, Enum):
    """工具权限级别"""
    PUBLIC = "public"             # 公开，无需权限
    USER = "user"                 # 需要用户确认
    ADMIN = "admin"               # 需要管理员权限
    DANGEROUS = "dangerous"       # 危险操作，需要明确授权


@dataclass(frozen=True)
class ToolDefinition:
    """
    工具定义
    
    Attributes:
        id: 工具唯一标识
        name: 工具名称
        category: 工具类别
        description: 工具描述
        handler: 处理函数
        parameters: 参数定义
        permission: 权限级别
        examples: 使用示例
        tags: 标签
    """
    id: str
    name: str
    category: ToolCategory
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    permission: ToolPermission = ToolPermission.PUBLIC
    examples: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "parameters": self.parameters,
            "permission": self.permission.value,
            "examples": self.examples,
            "tags": self.tags,
        }
    
    def matches_query(self, query: str) -> bool:
        """检查是否匹配查询"""
        query_lower = query.lower()
        searchable = f"{self.name} {self.description} {' '.join(self.tags)}".lower()
        return query_lower in searchable


@dataclass(frozen=True)
class ToolResult:
    """工具执行结果"""
    success: bool
    output: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata,
        }


class ToolRegistry:
    """
    工具注册表
    
    管理所有工具，支持：
    - 工具注册
    - 工具查找
    - 工具执行
    - 权限检查
    - 统计信息
    """
    
    def __init__(self):
        """初始化注册表"""
        self._tools: Dict[str, ToolDefinition] = {}
        self._execution_log: List[Dict[str, Any]] = []
        self._load_default_tools()
        logger.info(f"ToolRegistry 初始化完成，加载 {len(self._tools)} 个工具")
    
    def _load_default_tools(self) -> None:
        """加载默认工具（OpenClaw 内置工具）"""
        
        # ========== 浏览器工具 ==========
        self.register(ToolDefinition(
            id="browser",
            name="Browser",
            category=ToolCategory.BROWSER,
            description="控制网页浏览器（快照、点击、输入、导航等）",
            parameters={
                "action": {"type": "string", "required": True, "enum": ["snapshot", "click", "type", "navigate", "screenshot"]},
                "url": {"type": "string", "required": False},
                "selector": {"type": "string", "required": False},
                "text": {"type": "string", "required": False},
            },
            permission=ToolPermission.PUBLIC,
            examples=[
                "browser snapshot - 获取页面快照",
                "browser navigate url=https://example.com - 导航到 URL",
                "browser click selector='#button' - 点击元素",
            ],
            tags=["web", "automation", "browser"],
        ))
        
        # ========== 文件工具 ==========
        self.register(ToolDefinition(
            id="read",
            name="Read",
            category=ToolCategory.FILE,
            description="读取文件内容（支持文本和图片）",
            parameters={
                "path": {"type": "string", "required": True, "description": "文件路径"},
                "offset": {"type": "number", "required": False, "description": "起始行号"},
                "limit": {"type": "number", "required": False, "description": "最大行数"},
            },
            permission=ToolPermission.PUBLIC,
            examples=[
                "read path=file.txt - 读取文件",
                "read path=large.log offset=100 limit=50 - 读取大文件的部分内容",
            ],
            tags=["file", "read"],
        ))
        
        self.register(ToolDefinition(
            id="write",
            name="Write",
            category=ToolCategory.FILE,
            description="写入文件内容",
            parameters={
                "path": {"type": "string", "required": True, "description": "文件路径"},
                "content": {"type": "string", "required": True, "description": "文件内容"},
            },
            permission=ToolPermission.USER,
            examples=[
                "write path=file.txt content='Hello World' - 写入文件",
            ],
            tags=["file", "write"],
        ))
        
        self.register(ToolDefinition(
            id="edit",
            name="Edit",
            category=ToolCategory.FILE,
            description="编辑文件（精确替换文本）",
            parameters={
                "path": {"type": "string", "required": True},
                "oldText": {"type": "string", "required": True},
                "newText": {"type": "string", "required": True},
            },
            permission=ToolPermission.USER,
            examples=[
                "edit path=file.txt oldText='old' newText='new' - 替换文本",
            ],
            tags=["file", "edit"],
        ))
        
        # ========== Shell 工具 ==========
        self.register(ToolDefinition(
            id="exec",
            name="Exec",
            category=ToolCategory.SHELL,
            description="执行 shell 命令",
            parameters={
                "command": {"type": "string", "required": True, "description": "shell 命令"},
                "workdir": {"type": "string", "required": False, "description": "工作目录"},
                "timeout": {"type": "number", "required": False, "description": "超时秒数"},
            },
            permission=ToolPermission.DANGEROUS,
            examples=[
                "exec command='ls -la' - 列出文件",
                "exec command='git status' workdir=/path/to/repo - 检查 git 状态",
            ],
            tags=["shell", "command"],
        ))
        
        # ========== 记忆工具 ==========
        self.register(ToolDefinition(
            id="memory_search",
            name="Memory Search",
            category=ToolCategory.MEMORY,
            description="语义搜索记忆（MEMORY.md + memory/*.md）",
            parameters={
                "query": {"type": "string", "required": True, "description": "搜索查询"},
                "maxResults": {"type": "number", "required": False, "description": "最大结果数"},
                "minScore": {"type": "number", "required": False, "description": "最低分数"},
            },
            permission=ToolPermission.PUBLIC,
            examples=[
                "memory_search query='上次讨论的项目' - 搜索记忆",
            ],
            tags=["memory", "search"],
        ))
        
        self.register(ToolDefinition(
            id="memory_get",
            name="Memory Get",
            category=ToolCategory.MEMORY,
            description="从记忆文件读取片段",
            parameters={
                "path": {"type": "string", "required": True, "description": "记忆文件路径"},
                "from": {"type": "number", "required": False, "description": "起始行"},
                "lines": {"type": "number", "required": False, "description": "行数"},
            },
            permission=ToolPermission.PUBLIC,
            examples=[
                "memory_get path=MEMORY.md from=1 lines=10 - 读取记忆文件",
            ],
            tags=["memory", "read"],
        ))
        
        # ========== 会话工具 ==========
        self.register(ToolDefinition(
            id="sessions_spawn",
            name="Sessions Spawn",
            category=ToolCategory.SESSION,
            description=" spawn 子代理会话",
            parameters={
                "task": {"type": "string", "required": True, "description": "任务描述"},
                "agentId": {"type": "string", "required": False, "description": "代理 ID"},
                "timeoutSeconds": {"type": "number", "required": False, "description": "超时秒数"},
            },
            permission=ToolPermission.USER,
            examples=[
                "sessions_spawn task='分析这个代码库' - spawn 子代理",
            ],
            tags=["session", "agent"],
        ))
        
        # ========== Web 工具 ==========
        self.register(ToolDefinition(
            id="web_search",
            name="Web Search",
            category=ToolCategory.WEB,
            description="使用 Brave Search API 搜索网络",
            parameters={
                "query": {"type": "string", "required": True, "description": "搜索查询"},
                "count": {"type": "number", "required": False, "description": "结果数量"},
                "freshness": {"type": "string", "required": False, "description": "时间范围"},
            },
            permission=ToolPermission.PUBLIC,
            examples=[
                "web_search query='最新 AI 新闻' count=10 - 搜索网络",
            ],
            tags=["web", "search"],
        ))
        
        self.register(ToolDefinition(
            id="web_fetch",
            name="Web Fetch",
            category=ToolCategory.WEB,
            description="抓取网页内容并提取可读文本",
            parameters={
                "url": {"type": "string", "required": True, "description": "网页 URL"},
                "extractMode": {"type": "string", "required": False, "enum": ["markdown", "text"]},
            },
            permission=ToolPermission.PUBLIC,
            examples=[
                "web_fetch url=https://example.com - 抓取网页",
            ],
            tags=["web", "fetch"],
        ))
        
        # ========== 消息工具 ==========
        self.register(ToolDefinition(
            id="message",
            name="Message",
            category=ToolCategory.MESSAGE,
            description="发送消息到频道（Telegram、Discord 等）",
            parameters={
                "action": {"type": "string", "required": True, "enum": ["send", "broadcast"]},
                "target": {"type": "string", "required": False, "description": "目标频道/用户"},
                "message": {"type": "string", "required": False, "description": "消息内容"},
            },
            permission=ToolPermission.DANGEROUS,
            examples=[
                "message action=send target=telegram message='Hello' - 发送消息",
            ],
            tags=["message", "communication"],
        ))
    
    def register(self, tool: ToolDefinition) -> None:
        """
        注册工具
        
        Args:
            tool: 工具定义
        """
        self._tools[tool.id] = tool
        logger.debug(f"注册工具：{tool.id} - {tool.name}")
    
    def get(self, tool_id: str) -> Optional[ToolDefinition]:
        """
        获取工具定义
        
        Args:
            tool_id: 工具 ID
            
        Returns:
            ToolDefinition or None
        """
        return self._tools.get(tool_id)
    
    def list_all(self) -> List[ToolDefinition]:
        """列出所有工具"""
        return list(self._tools.values())
    
    def list_by_category(self, category: ToolCategory) -> List[ToolDefinition]:
        """按类别列出工具"""
        return [t for t in self._tools.values() if t.category == category]
    
    def search(self, query: str, limit: int = 20) -> List[ToolDefinition]:
        """搜索工具"""
        matches = [t for t in self._tools.values() if t.matches_query(query)]
        return matches[:limit]
    
    def execute(self, tool_id: str, **kwargs) -> ToolResult:
        """
        执行工具（模拟执行，实际执行需要调用 OpenClaw 工具）
        
        Args:
            tool_id: 工具 ID
            **kwargs: 工具参数
            
        Returns:
            ToolResult: 执行结果
        """
        tool = self.get(tool_id)
        if not tool:
            return ToolResult(
                success=False,
                output=None,
                error=f"未知工具：{tool_id}",
            )
        
        # 记录执行日志
        log_entry = {
            "tool_id": tool_id,
            "parameters": kwargs,
            "timestamp": str(Path(__file__).stat().st_mtime),  # 简化时间戳
        }
        self._execution_log.append(log_entry)
        
        # 实际执行需要调用 OpenClaw 工具系统
        # 这里返回模拟结果
        return ToolResult(
            success=True,
            output=f"工具 {tool_id} 执行成功（模拟）",
            metadata={"tool_name": tool.name, "category": tool.category.value},
        )
    
    def check_permission(self, tool_id: str, user_permission: ToolPermission) -> bool:
        """
        检查用户权限是否足够执行工具
        
        Args:
            tool_id: 工具 ID
            user_permission: 用户权限级别
            
        Returns:
            bool: 是否有权限
        """
        tool = self.get(tool_id)
        if not tool:
            return False
        
        permission_hierarchy = {
            ToolPermission.PUBLIC: 0,
            ToolPermission.USER: 1,
            ToolPermission.ADMIN: 2,
            ToolPermission.DANGEROUS: 3,
        }
        
        tool_level = permission_hierarchy.get(tool.permission, 0)
        user_level = permission_hierarchy.get(user_permission, 0)
        
        return user_level >= tool_level
    
    def count(self) -> int:
        """获取工具总数"""
        return len(self._tools)
    
    def count_by_category(self) -> Dict[str, int]:
        """按类别统计工具数量"""
        counts = {}
        for tool in self._tools.values():
            cat = tool.category.value
            counts[cat] = counts.get(cat, 0) + 1
        return counts
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_tools": len(self._tools),
            "by_category": self.count_by_category(),
            "tool_ids": list(self._tools.keys()),
            "execution_count": len(self._execution_log),
        }
    
    def get_execution_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取执行日志"""
        return self._execution_log[-limit:]
    
    def to_markdown(self) -> str:
        """生成工具列表 Markdown"""
        lines = [
            "# 🛠️ OpenClaw 工具注册表",
            "",
            f"**工具总数：** {self.count()}",
            "",
            "## 按类别分布",
            "",
        ]
        
        for cat, count in self.count_by_category().items():
            lines.append(f"- {cat}: {count}")
        
        lines.extend(["", "## 工具列表", ""])
        
        for tool in sorted(self._tools.values(), key=lambda t: t.category.value):
            lines.append(f"### {tool.name} (`{tool.id}`)")
            lines.append(f"- 类别：{tool.category.value}")
            lines.append(f"- 描述：{tool.description}")
            lines.append(f"- 权限：{tool.permission.value}")
            if tool.examples:
                lines.append("- 示例:")
                for ex in tool.examples:
                    lines.append(f"  - `{ex}`")
            lines.append("")
        
        return "\n".join(lines)


# ========== 全局单例 ==========

_registry_instance: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """获取全局注册表实例"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ToolRegistry()
    return _registry_instance


# ========== CLI 入口 ==========

if __name__ == "__main__":
    registry = get_tool_registry()
    
    print("🛠️ OpenClaw 工具注册表统计")
    print("=" * 50)
    stats = registry.get_statistics()
    print(f"工具总数：{stats['total_tools']}")
    print(f"按类别分布：{stats['by_category']}")
    print()
    
    # 生成 Markdown
    print(registry.to_markdown())
