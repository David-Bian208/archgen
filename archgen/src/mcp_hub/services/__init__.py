"""MCP Services - 子服务基类和实现"""

from .screenshot_service import ScreenshotMCPService
from .html_gen_service import HTMLGenMCPService
from .storage_service import StorageMCPService

__all__ = ["ScreenshotMCPService", "HTMLGenMCPService", "StorageMCPService"]
