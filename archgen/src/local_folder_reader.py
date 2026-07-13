"""MCP 本地文件夹读取与检索模块"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Optional

try:
    import frontmatter
except ImportError:
    frontmatter = None

logger = logging.getLogger(__name__)


class LocalFolderReader:
    """本地文件夹读取与 MCP 检索"""

    ALLOWED_EXTENSIONS = {".md", ".txt", ".markdown"}
    TEXT_EXTENSIONS = {".md", ".txt", ".markdown"}

    def __init__(self, folder_path: str):
        self.folder_path = Path(folder_path)
        if not self.folder_path.exists():
            raise ValueError(f"文件夹不存在: {folder_path}")
        if not self.folder_path.is_dir():
            raise ValueError(f"路径不是文件夹: {folder_path}")

    def _matches_keyword(self, file_info: Dict, keyword: str) -> bool:
        """检查文件是否匹配关键词（文件名 + 路径 + 全文）"""
        if not keyword:
            return True
        kw_lower = keyword.lower()

        # 匹配文件名
        if kw_lower in file_info.get("name", "").lower():
            return True

        # 匹配路径
        if kw_lower in file_info.get("relative_path", "").lower():
            return True

        # 匹配全文内容
        full_content = file_info.get("_full_content", "")
        if kw_lower in full_content.lower():
            return True

        # 匹配 Front Matter 中的 tags
        tags = file_info.get("tags", [])
        if any(kw_lower in str(t).lower() for t in tags):
            return True

        # 匹配 Front Matter 中的其他字段
        for key, value in file_info.items():
            if key in ("name", "path", "relative_path", "content", "preview", "_full_content"):
                continue
            if isinstance(value, str) and kw_lower in value.lower():
                return True

        return False

    def _keyword_relevance(self, file_info: Dict, keyword: str) -> float:
        """计算文件与关键词的相关度分数（0-1）
        
        拆词匹配：中文按常见分隔符拆词，英文按空格拆词
        文件名匹配权重 > 内容匹配权重
        """
        if not keyword:
            return 1.0
        
        # 拆词：中文按词组切分（2-4字），英文按空格
        tokens = []
        # 中文词组：2-4 字窗口
        kw_clean = re.sub(r'[^\w\u4e00-\u9fff]', ' ', keyword)
        for part in kw_clean.split():
            if re.search(r'[\u4e00-\u9fff]', part):
                # 中文：按 2 字窗口切分
                for i in range(len(part) - 1):
                    tokens.append(part[i:i+2])
                tokens.append(part)  # 完整词也加入
            else:
                tokens.append(part.lower())
        tokens = list(set(tokens))  # 去重
        if not tokens:
            tokens = [keyword.lower()]
        
        fname = file_info.get("name", "").lower()
        content = file_info.get("_full_content", "").lower()
        path = file_info.get("relative_path", "").lower()
        tags = [str(t).lower() for t in file_info.get("tags", [])]
        
        # 计算命中率
        name_hits = sum(1 for t in tokens if t in fname)
        content_hits = sum(1 for t in tokens if t in content)
        path_hits = sum(1 for t in tokens if t in path)
        tag_hits = sum(1 for t in tokens if any(t in tag for tag in tags))
        
        total_tokens = len(tokens)
        # 加权：文件名命中权重 3，内容命中权重 1
        score = (name_hits * 3 + content_hits + path_hits * 2 + tag_hits * 2) / (total_tokens * 7)
        return min(score, 1.0)

    def list_all_file_names(self, limit: int = 50) -> List[str]:
        """返回所有文件的名称清单（用于降级时给 LLM 判断相关性）"""
        names = []
        for md_file in self.folder_path.rglob("*.md"):
            if md_file.is_file():
                names.append(md_file.name)
                if limit and len(names) >= limit:
                    break
        return names

    def list_file_titles(self, limit: Optional[int] = None) -> List[Dict]:
        """
        轻量扫描：只获取文件名 + Front Matter 元数据（title, tags, category）
        不读取全文，速度比 list_files 快数倍
        用于全量标题列表，供 LLM 筛选
        
        Args:
            limit: 最多返回文件数（默认不限制）
            
        Returns:
            [{name, path, relative_path, title, tags, category, mtime}]
        """
        results = []
        pattern = "**/*"

        for file_path in self.folder_path.glob(pattern):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in self.ALLOWED_EXTENSIONS:
                continue

            # 只读 Front Matter，不读全文
            try:
                content_sample = file_path.read_text(encoding="utf-8", errors="ignore")[:2000]
            except Exception:
                continue

            meta = {}
            if frontmatter:
                try:
                    import io
                    post = frontmatter.loads(content_sample)
                    meta = dict(post.metadata)
                except Exception:
                    pass
            else:
                meta = self._manual_parse_frontmatter(content_sample)

            stat = file_path.stat()
            rel_path = str(file_path.relative_to(self.folder_path))

            results.append({
                "name": file_path.name,
                "path": str(file_path),
                "relative_path": rel_path,
                "title": meta.get("title", file_path.stem),
                "tags": meta.get("tags", []),
                "category": meta.get("category", ""),
                "mtime": stat.st_mtime,
            })

            if limit and len(results) >= limit:
                break

        logger.info(f"标题扫描: 在 {self.folder_path} 找到 {len(results)} 个文件")
        return results

    def list_files_fast(self, limit: Optional[int] = None) -> List[Dict]:
        """
        快速扫描：只获取文件名、路径、修改时间、大小
        不解析 Front Matter、不读取内容，速度快
        用于大规模文件的全量扫描
        """
        results = []
        
        try:
            for md_file in self.folder_path.rglob("*.md"):
                if not md_file.is_file():
                    continue
                    
                stat = md_file.stat()
                results.append({
                    "name": md_file.name,
                    "path": str(md_file),
                    "relative_path": str(md_file.relative_to(self.folder_path)),
                    "mtime": stat.st_mtime,
                    "size": stat.st_size,
                })
                
                if limit and len(results) >= limit:
                    break
        except Exception as e:
            logger.error(f"快速扫描失败: {e}")
            return []
        
        # 按修改时间倒序
        results.sort(key=lambda x: x.get("mtime", 0), reverse=True)
        
        logger.info(f"快速扫描: 在 {self.folder_path} 找到 {len(results)} 个文件")
        return results

    def list_files(
        self,
        keyword: str = None,
        tag: str = None,
        recursive: bool = True,
        limit: int = 20,
    ) -> List[Dict]:
        """
        MCP 检索：扫描文件夹 → 全文拆词匹配 → 按相关度排序

        Args:
            keyword: 关键词（拆词后匹配文件名、路径、全文内容）
            tag: 标签（匹配 Front Matter 中的 tags 字段）
            recursive: 是否递归扫描子目录
            limit: 最多返回文件数

        Returns:
            文件列表，包含元数据、预览和 relevance 分数
        """
        pattern = "**/*" if recursive else "*"
        results = []

        for file_path in self.folder_path.glob(pattern):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in self.ALLOWED_EXTENSIONS:
                continue

            file_info = self._parse_file_meta(file_path)
            if not file_info:
                continue

            # 计算相关度分数
            if keyword:
                relevance = self._keyword_relevance(file_info, keyword)
                if relevance <= 0:
                    continue  # 无匹配的跳过
                file_info["relevance"] = relevance
            else:
                file_info["relevance"] = 0

            # 过滤：标签匹配
            if tag:
                tags = file_info.get("tags", [])
                if not any(tag.lower() in str(t).lower() for t in tags):
                    continue

            results.append(file_info)

        # 按相关度降序排列
        results.sort(key=lambda x: x.get("relevance", 0), reverse=True)

        if limit and len(results) > limit:
            results = results[:limit]

        # 清理内部字段
        for r in results:
            r.pop("_full_content", None)

        logger.info(f"MCP 检索: 在 {self.folder_path} 找到 {len(results)} 个匹配文件 (关键词: {keyword}, 最高相关度: {results[0].get('relevance', 0) if results else 0:.2f})")
        return results

    def _parse_file_meta(self, file_path: Path) -> Optional[Dict]:
        """解析文件元数据（Front Matter + 预览）"""
        try:
            if frontmatter:
                post = frontmatter.load(str(file_path))
                meta = dict(post.metadata)
                content = post.content
            else:
                # 降级：手动解析 Front Matter
                content = file_path.read_text(encoding="utf-8")
                meta = self._manual_parse_frontmatter(content)
        except Exception as e:
            logger.warning(f"解析文件元数据失败 {file_path.name}: {e}")
            try:
                content = file_path.read_text(encoding="utf-8")
            except Exception:
                return None
            meta = {}

        # 生成预览（前 500 字）
        preview = content[:500].strip() if content else ""

        rel_path = str(file_path.relative_to(self.folder_path))

        return {
            "name": file_path.name,
            "path": str(file_path),
            "relative_path": rel_path,
            "size": file_path.stat().st_size,
            "tags": meta.get("tags", []),
            "tier": meta.get("tier", ""),
            "title": meta.get("title", ""),
            "category": meta.get("category", ""),  # 基础分类（用户已标注）
            "preview": preview,
            "_full_content": content,  # 内部字段，用于关键词匹配
        }

    @staticmethod
    def _manual_parse_frontmatter(content: str) -> Dict:
        """手动解析 YAML Front Matter（降级方案）"""
        meta = {}
        match = re.match(r"---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if match:
            try:
                import yaml
                meta = yaml.safe_load(match.group(1)) or {}
            except Exception:
                pass
        return meta

    def read_files(self, paths: List[str]) -> List[Dict]:
        """
        读取多个文件全文

        Args:
            paths: 文件路径列表

        Returns:
            [{"path": "...", "name": "...", "content": "..."}, ...]
        """
        results = []
        for path in paths:
            file_path = Path(path)
            if not file_path.exists():
                logger.warning(f"文件不存在: {path}")
                continue
            if file_path.suffix.lower() not in self.TEXT_EXTENSIONS:
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
                results.append({
                    "path": str(file_path),
                    "name": file_path.name,
                    "content": content,
                })
            except Exception as e:
                logger.error(f"读取文件失败 {path}: {e}")

        logger.info(f"读取文件: 成功 {len(results)}/{len(paths)}")
        return results

    def read_file(self, file_path: str) -> Optional[str]:
        """读取单个文件内容"""
        path = Path(file_path)
        if not path.exists():
            return None
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return None
