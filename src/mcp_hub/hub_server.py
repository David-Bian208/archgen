"""MCP Hub Server - 聚合所有 MCP 子服务的路由层"""

import asyncio
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class MCPSubService:
    """MCP 子服务基类"""
    
    def __init__(self, service_id: str):
        self.service_id = service_id
    
    async def tools_list(self) -> List[Dict]:
        """返回该子服务提供的工具列表"""
        raise NotImplementedError
    
    async def tools_call(self, tool_name: str, arguments: Dict) -> Any:
        """调用子服务的某个工具"""
        raise NotImplementedError
    
    async def shutdown(self):
        """关闭子服务"""
        pass


class MCPHub:
    """MCP Hub - 聚合多个子服务，提供统一的工具调用接口"""
    
    def __init__(self):
        self.servers: Dict[str, MCPSubService] = {}
        self._initialized = False
    
    def register_server(self, server_id: str, server: MCPSubService):
        """注册子服务"""
        self.servers[server_id] = server
        logger.info(f"注册子服务: {server_id}")
    
    async def initialize(self):
        """初始化 Hub 和所有子服务"""
        if self._initialized:
            return
        self._initialized = True
        logger.info(f"MCP Hub 初始化完成，已注册 {len(self.servers)} 个子服务")
    
    async def list_tools(self) -> List[Dict]:
        """服务发现层：聚合所有子服务的工具列表"""
        all_tools = []
        for server_id, server in self.servers.items():
            try:
                tools = await server.tools_list()
                for tool in tools:
                    all_tools.append({
                        "jsName": f"{server_id}_{tool['name']}",
                        "originalId": f"{server_id}__{tool['name']}",
                        "serverId": server_id,
                        **tool
                    })
            except Exception as e:
                logger.error(f"获取子服务 {server_id} 工具列表失败: {e}")
        return all_tools
    
    async def invoke_tool(self, name: str, params: Dict) -> Any:
        """单次调用层：转发调用到对应子服务"""
        if "__" not in name:
            raise ValueError(f"工具名称格式错误: {name}，应为 server_id__tool_name")
        
        server_id, tool_name = name.split("__", 1)
        server = self.servers.get(server_id)
        if not server:
            raise KeyError(f"子服务不存在: {server_id}")
        
        try:
            return await server.tools_call(tool_name, params)
        except Exception as e:
            logger.error(f"调用工具 {name} 失败: {e}")
            raise
    
    async def exec_code(self, code: str, context: Optional[Dict] = None) -> Any:
        """编排执行层：在沙箱中执行编排代码"""
        from .exec_sandbox import ExecSandbox
        
        sandbox = ExecSandbox(self)
        return await sandbox.execute(code, context or {})
    
    async def shutdown(self):
        """关闭所有子服务"""
        for server_id, server in self.servers.items():
            try:
                await server.shutdown()
                logger.info(f"子服务 {server_id} 已关闭")
            except Exception as e:
                logger.error(f"关闭子服务 {server_id} 失败: {e}")
        self._initialized = False
        logger.info("MCP Hub 已关闭")
