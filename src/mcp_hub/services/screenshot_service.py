"""Screenshot MCP Service - 截图子服务（MCP 协议实现）"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from ..hub_server import MCPSubService
from ...screenshot import ScreenshotService

logger = logging.getLogger(__name__)


class ScreenshotMCPService(MCPSubService):
    """截图 MCP 子服务 - 封装 ScreenshotService 提供 MCP 工具接口"""
    
    def __init__(self, screenshot_service: Optional[ScreenshotService] = None):
        super().__init__("screenshot")
        self.screenshot_service = screenshot_service or ScreenshotService()
        self._initialized = False
    
    async def initialize(self):
        """初始化截图服务"""
        if self._initialized:
            return
        await self.screenshot_service.initialize()
        self._initialized = True
        logger.info("截图 MCP 子服务初始化完成")
    
    async def tools_list(self) -> List[Dict]:
        """返回截图工具列表"""
        return [
            {
                "name": "capture",
                "description": "截图 HTML 内容为 PNG",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "html": {
                            "type": "string",
                            "description": "HTML 内容字符串"
                        },
                        "output_path": {
                            "type": "string",
                            "description": "输出 PNG 文件路径"
                        },
                        "size": {
                            "type": "string",
                            "enum": ["wechat", "xiaohongshu", "ppt", "default"],
                            "default": "default",
                            "description": "尺寸预设"
                        }
                    },
                    "required": ["html", "output_path"]
                }
            },
            {
                "name": "capture_from_file",
                "description": "截图 HTML 文件为 PNG",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "html_file": {
                            "type": "string",
                            "description": "HTML 文件路径"
                        },
                        "output_path": {
                            "type": "string",
                            "description": "输出 PNG 文件路径"
                        },
                        "size": {
                            "type": "string",
                            "enum": ["wechat", "xiaohongshu", "ppt", "default"],
                            "default": "default",
                            "description": "尺寸预设"
                        }
                    },
                    "required": ["html_file", "output_path"]
                }
            },
            {
                "name": "capture_from_url",
                "description": "截图 URL 为 PNG",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "目标 URL"
                        },
                        "output_path": {
                            "type": "string",
                            "description": "输出 PNG 文件路径"
                        },
                        "size": {
                            "type": "string",
                            "enum": ["wechat", "xiaohongshu", "ppt", "default"],
                            "default": "default",
                            "description": "尺寸预设"
                        }
                    },
                    "required": ["url", "output_path"]
                }
            },
            {
                "name": "batch_capture",
                "description": "批量截图多个 HTML 内容",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tasks": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "html": {"type": "string"},
                                    "output_path": {"type": "string"},
                                    "size": {"type": "string"}
                                },
                                "required": ["html", "output_path"]
                            },
                            "description": "截图任务列表"
                        }
                    },
                    "required": ["tasks"]
                }
            }
        ]
    
    async def tools_call(self, tool_name: str, arguments: Dict) -> Any:
        """调用截图工具"""
        if not self._initialized:
            await self.initialize()
        
        if tool_name == "capture":
            return await self.screenshot_service.capture(
                html_content=arguments["html"],
                output_path=arguments["output_path"],
                size=arguments.get("size", "default")
            )
        
        elif tool_name == "capture_from_file":
            return await self.screenshot_service.capture_from_file(
                html_file=arguments["html_file"],
                output_path=arguments["output_path"],
                size=arguments.get("size", "default")
            )
        
        elif tool_name == "capture_from_url":
            return await self.screenshot_service.capture_from_url(
                url=arguments["url"],
                output_path=arguments["output_path"],
                size=arguments.get("size", "default")
            )
        
        elif tool_name == "batch_capture":
            tasks = arguments["tasks"]
            formatted_tasks = []
            for task in tasks:
                formatted_tasks.append({
                    "html_content": task.get("html"),
                    "output_path": task["output_path"],
                    "size": task.get("size", "default")
                })
            return await self.screenshot_service.batch_capture(formatted_tasks)
        
        else:
            raise ValueError(f"未知工具: {tool_name}")
    
    async def shutdown(self):
        """关闭截图服务"""
        if self._initialized:
            await self.screenshot_service.shutdown()
            self._initialized = False
            logger.info("截图 MCP 子服务已关闭")
