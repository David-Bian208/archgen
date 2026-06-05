"""Knowledge Base Reader - 知识库读取模块"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class KnowledgeBaseReader:
    """知识库读取器，支持三种模式：local / mcp / upload"""

    ALLOWED_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml"}

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.root_path = Path(self.config.get("root_path", "knowledge_base"))
        self.mode = self.config.get("mode", "local")
        self.allowed_extensions = set(
            self.config.get("allowed_extensions", self.ALLOWED_EXTENSIONS)
        )

    def list_categories(self) -> List[Dict]:
        """
        列出知识库分类（根目录下的子目录）

        Returns:
            [{"key": "business", "name": "商业分析", "file_count": 5}, ...]
        """
        if self.mode == "mcp":
            return self._list_categories_mcp()

        if not self.root_path.exists():
            logger.warning(f"知识库目录不存在: {self.root_path}")
            return []

        categories = []
        for item in sorted(self.root_path.iterdir()):
            if item.is_dir():
                file_count = len([
                    f for f in item.rglob("*")
                    if f.is_file() and f.suffix.lower() in self.allowed_extensions
                ])
                categories.append({
                    "key": item.name,
                    "name": self._get_category_name(item.name),
                    "file_count": file_count,
                    "path": str(item),
                })

        logger.info(f"找到 {len(categories)} 个知识库分类")
        return categories

    def list_directory(self, category: Optional[str] = None) -> List[Dict]:
        """
        列出目录下的文件

        Args:
            category: 分类名称（子目录名），None 表示根目录

        Returns:
            [{"name": "file.md", "path": "...", "size": 1024}, ...]
        """
        if self.mode == "mcp":
            return self._list_directory_mcp(category)

        target_path = self.root_path
        if category:
            target_path = self.root_path / category
            if not target_path.exists():
                logger.warning(f"分类目录不存在: {target_path}")
                return []

        files = []
        for item in sorted(target_path.iterdir()):
            if item.is_file() and item.suffix.lower() in self.allowed_extensions:
                files.append({
                    "name": item.name,
                    "path": str(item.relative_to(self.root_path)),
                    "size": item.stat().st_size,
                    "suffix": item.suffix,
                })
            elif item.is_dir():
                files.append({
                    "name": item.name,
                    "path": str(item.relative_to(self.root_path)),
                    "size": 0,
                    "is_dir": True,
                })

        logger.info(f"目录 {target_path} 下有 {len(files)} 个条目")
        return files

    def read_file(self, file_path: str) -> Optional[str]:
        """
        读取文件内容

        Args:
            file_path: 相对于知识库根目录的路径

        Returns:
            文件内容字符串，失败返回 None
        """
        if self.mode == "mcp":
            return self._read_file_mcp(file_path)

        full_path = self.root_path / file_path

        if not full_path.exists():
            logger.error(f"文件不存在: {full_path}")
            return None

        if full_path.suffix.lower() not in self.allowed_extensions:
            logger.error(f"不支持的文件类型: {full_path.suffix}")
            return None

        try:
            content = full_path.read_text(encoding="utf-8")
            logger.info(f"读取文件成功: {file_path} ({len(content)} 字符)")
            return content
        except Exception as e:
            logger.error(f"读取文件失败: {file_path}, 错误: {e}")
            return None

    def get_file_info(self, file_path: str) -> Optional[Dict]:
        """
        获取文件信息

        Args:
            file_path: 相对于知识库根目录的路径

        Returns:
            {"name": "...", "path": "...", "size": 1024, "content": "..."}
        """
        if self.mode == "mcp":
            return self._get_file_info_mcp(file_path)

        full_path = self.root_path / file_path

        if not full_path.exists():
            return None

        content = self.read_file(file_path)
        if content is None:
            return None

        return {
            "name": full_path.name,
            "path": file_path,
            "size": full_path.stat().st_size,
            "content": content,
        }

    # ===== MCP 模式（预留接口） =====

    def _list_categories_mcp(self) -> List[Dict]:
        """MCP 模式列出分类"""
        logger.info("MCP 模式: 列出分类（待实现）")
        return []

    def _list_directory_mcp(self, category: Optional[str] = None) -> List[Dict]:
        """MCP 模式列出目录"""
        logger.info(f"MCP 模式: 列出目录 {category}（待实现）")
        return []

    def _read_file_mcp(self, file_path: str) -> Optional[str]:
        """MCP 模式读取文件"""
        logger.info(f"MCP 模式: 读取文件 {file_path}（待实现）")
        return None

    def _get_file_info_mcp(self, file_path: str) -> Optional[Dict]:
        """MCP 模式获取文件信息"""
        logger.info(f"MCP 模式: 获取文件信息 {file_path}（待实现）")
        return None

    # ===== 辅助方法 =====

    def _get_category_name(self, key: str) -> str:
        """获取分类显示名称"""
        category_names = {
            "business": "商业分析",
            "finance": "财务分析",
            "product": "产品设计",
            "operations": "运营优化",
            "personal": "个人成长",
            "risk": "风险管理",
            "project": "项目管理",
        }
        return category_names.get(key, key)

    def get_mode(self) -> str:
        """获取当前模式"""
        return self.mode
