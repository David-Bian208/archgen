"""HTML Generation MCP Service - HTML 生成子服务（MCP 协议实现）"""

import logging
from typing import Dict, List, Any, Optional

from ..hub_server import MCPSubService
from ...html_generator import HTMLGenerator

logger = logging.getLogger(__name__)


class HTMLGenMCPService(MCPSubService):
    """HTML 生成 MCP 子服务 - 封装 HTMLGenerator 提供 MCP 工具接口"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("html_gen")
        self.config = config or {}
        self.generator = HTMLGenerator(self.config)
    
    async def tools_list(self) -> List[Dict]:
        return [
            {
                "name": "render",
                "description": "渲染结构化数据为 HTML 页面",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "object",
                            "description": "结构化数据（JSON 格式）"
                        },
                        "framework": {
                            "type": "string",
                            "description": "框架类型（如 claim, comparison, flowchart 等）"
                        },
                        "style": {
                            "type": "string",
                            "enum": ["minimal", "modern", "classic"],
                            "default": "minimal",
                            "description": "样式主题"
                        },
                        "size": {
                            "type": "string",
                            "enum": ["wechat", "xiaohongshu", "ppt", "default"],
                            "default": "default",
                            "description": "尺寸预设"
                        }
                    },
                    "required": ["data", "framework"]
                }
            },
            {
                "name": "render_from_article",
                "description": "从文章数据直接渲染为 HTML 页面",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "文章标题"
                        },
                        "paragraphs": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "content": {"type": "string"}
                                }
                            },
                            "description": "段落列表"
                        },
                        "framework": {
                            "type": "string",
                            "description": "框架类型"
                        },
                        "style": {
                            "type": "string",
                            "enum": ["minimal", "modern", "classic"],
                            "default": "minimal",
                            "description": "样式主题"
                        },
                        "size": {
                            "type": "string",
                            "enum": ["wechat", "xiaohongshu", "ppt", "default"],
                            "default": "default",
                            "description": "尺寸预设"
                        }
                    },
                    "required": ["title", "paragraphs", "framework"]
                }
            }
        ]
    
    async def tools_call(self, tool_name: str, arguments: Dict) -> Any:
        if tool_name == "render":
            return self.generator.render(
                data=arguments["data"],
                article_type=arguments["framework"],
                style=arguments.get("style", "minimal"),
                size=arguments.get("size", "default")
            )
        
        elif tool_name == "render_from_article":
            data = {
                "title": arguments["title"],
                "paragraphs": arguments["paragraphs"]
            }
            return self.generator.render(
                data=data,
                article_type=arguments["framework"],
                style=arguments.get("style", "minimal"),
                size=arguments.get("size", "default")
            )
        
        else:
            raise ValueError(f"未知工具: {tool_name}")
