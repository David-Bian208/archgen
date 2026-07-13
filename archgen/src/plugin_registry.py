"""Plugin Registry - 插件式扩展架构"""

import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PluginTool:
    """插件工具定义"""
    name: str
    handler: Callable
    description: str = ""
    params: Dict[str, Any] = field(default_factory=dict)


class Plugin:
    """插件基类"""
    
    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id
    
    def get_tools(self) -> List[PluginTool]:
        """返回该插件提供的所有工具"""
        raise NotImplementedError
    
    def get_tool(self, tool_name: str) -> Optional[PluginTool]:
        """获取指定工具"""
        for tool in self.get_tools():
            if tool.name == tool_name:
                return tool
        return None
    
    async def initialize(self):
        """插件初始化"""
        pass
    
    async def shutdown(self):
        """插件关闭"""
        pass


class PluginRegistry:
    """插件注册表"""
    
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
        self._tool_cache: Dict[str, PluginTool] = {}
    
    def register(self, plugin_id: str, plugin: Plugin):
        """注册插件"""
        self.plugins[plugin_id] = plugin
        logger.info(f"插件已注册: {plugin_id}")
        
        for tool in plugin.get_tools():
            tool_id = f"{plugin_id}__{tool.name}"
            self._tool_cache[tool_id] = tool
            logger.info(f"  工具已注册: {tool_id}")
    
    async def initialize_all(self):
        """初始化所有插件"""
        for plugin_id, plugin in self.plugins.items():
            try:
                await plugin.initialize()
                logger.info(f"插件初始化成功: {plugin_id}")
            except Exception as e:
                logger.error(f"插件初始化失败: {plugin_id} - {e}")
    
    async def shutdown_all(self):
        """关闭所有插件"""
        for plugin_id, plugin in self.plugins.items():
            try:
                await plugin.shutdown()
                logger.info(f"插件已关闭: {plugin_id}")
            except Exception as e:
                logger.error(f"插件关闭失败: {plugin_id} - {e}")
    
    def get_tool(self, tool_id: str) -> Optional[PluginTool]:
        """获取工具"""
        return self._tool_cache.get(tool_id)
    
    def list_all_tools(self) -> List[Dict[str, Any]]:
        """列出所有工具"""
        tools = []
        for tool_id, tool in self._tool_cache.items():
            tools.append({
                "id": tool_id,
                "name": tool.name,
                "description": tool.description,
                "params": tool.params
            })
        return tools


_global_plugin_registry = PluginRegistry()


def get_plugin_registry() -> PluginRegistry:
    return _global_plugin_registry
