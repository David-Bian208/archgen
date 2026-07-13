"""Storage MCP Service - 存储子服务（MCP 协议实现）"""

import os
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..hub_server import MCPSubService

logger = logging.getLogger(__name__)


class StorageMCPService(MCPSubService):
    """存储 MCP 子服务 - 提供文件存储/CDN上传工具接口"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("storage")
        self.config = config or {}
        self.output_dir = Path(self.config.get("output_dir", "output"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cdn_base_url = self.config.get("cdn_base_url", "")
    
    async def tools_list(self) -> List[Dict]:
        return [
            {
                "name": "upload_file",
                "description": "上传文件到本地存储或 CDN",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "源文件路径"
                        },
                        "destination": {
                            "type": "string",
                            "description": "目标路径（相对于 output_dir）"
                        },
                        "upload_to_cdn": {
                            "type": "boolean",
                            "default": False,
                            "description": "是否上传到 CDN"
                        }
                    },
                    "required": ["file_path", "destination"]
                }
            },
            {
                "name": "list_files",
                "description": "列出输出目录中的文件",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "default": "*.png",
                            "description": "文件匹配模式"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 50,
                            "description": "返回数量限制"
                        }
                    }
                }
            },
            {
                "name": "get_file_url",
                "description": "获取文件的访问 URL",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "文件路径"
                        }
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "delete_file",
                "description": "删除指定文件",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "文件路径"
                        }
                    },
                    "required": ["file_path"]
                }
            }
        ]
    
    async def tools_call(self, tool_name: str, arguments: Dict) -> Any:
        if tool_name == "upload_file":
            return await self._upload_file(arguments)
        
        elif tool_name == "list_files":
            return self._list_files(arguments)
        
        elif tool_name == "get_file_url":
            return self._get_file_url(arguments)
        
        elif tool_name == "delete_file":
            return self._delete_file(arguments)
        
        else:
            raise ValueError(f"未知工具: {tool_name}")
    
    async def _upload_file(self, arguments: Dict) -> Dict:
        file_path = Path(arguments["file_path"])
        destination = arguments["destination"]
        upload_to_cdn = arguments.get("upload_to_cdn", False)
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        dest_path = self.output_dir / destination
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(str(file_path), str(dest_path))
        logger.info(f"文件已保存: {dest_path}")
        
        result = {
            "local_path": str(dest_path),
            "size": dest_path.stat().st_size,
            "created_at": datetime.now().isoformat()
        }
        
        if upload_to_cdn and self.cdn_base_url:
            result["cdn_url"] = f"{self.cdn_base_url}/{destination}"
        
        return result
    
    def _list_files(self, arguments: Dict) -> List[Dict]:
        pattern = arguments.get("pattern", "*.png")
        limit = arguments.get("limit", 50)
        
        files = list(self.output_dir.glob(pattern))
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        files = files[:limit]
        
        return [
            {
                "name": f.name,
                "path": str(f),
                "size": f.stat().st_size,
                "modified_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            }
            for f in files
        ]
    
    def _get_file_url(self, arguments: Dict) -> Dict:
        file_path = Path(arguments["file_path"])
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        relative_path = file_path.relative_to(self.output_dir)
        
        if self.cdn_base_url:
            url = f"{self.cdn_base_url}/{relative_path}"
        else:
            url = f"/output/{relative_path}"
        
        return {
            "file_path": str(file_path),
            "url": url,
            "size": file_path.stat().st_size
        }
    
    def _delete_file(self, arguments: Dict) -> Dict:
        file_path = Path(arguments["file_path"])
        
        if not file_path.exists():
            return {"success": False, "error": "文件不存在"}
        
        file_path.unlink()
        logger.info(f"文件已删除: {file_path}")
        
        return {"success": True, "deleted": str(file_path)}
