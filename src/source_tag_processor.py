"""
Source Tag 处理模块 - P2 硬约束实施

功能：
- 从 LLM 生成内容中提取 source_tag 标记
- 验证内容是否有有效来源标签
- 过滤无标签内容（硬约束）
- 渲染时添加来源标注

P2 阶段规则：
- 无 source_tag → 不渲染（直接过滤）
- ai_inferred → "⚠️ [AI 推断] ..."
- 其他 → "[来源：xxx] ..."
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ContentBlock:
    """内容块"""
    raw_content: str  # 原始内容
    source_tag: Optional[str] = None  # 来源标签
    rendered_content: str = ""  # 渲染后的内容
    is_valid: bool = True  # 是否有有效来源
    warning: str = ""  # 警告信息


class SourceTagProcessor:
    """Source Tag 处理器"""

    # source_tag 类型定义
    VALID_PREFIXES = [
        "local:",
        "ai_pulse:",
        "user_input:",
        "ai_inferred:",
    ]

    # AI 推断标记模式
    AI_INFERRED_PATTERN = re.compile(r'⚠️?\s*\[AI 推断\]')
    
    # 来源标记模式
    SOURCE_TAG_PATTERNS = [
        re.compile(r'\[来源[：:]\s*([^\]]+)\]'),
        re.compile(r'source_tag[：:]\s*([^\s\n]+)'),
    ]

    # 案例占位符模式
    CASE_PLACEHOLDER_PATTERN = re.compile(r'\[📌\s*待补充[案例素材]*[：:]\s*([^\]]+)\]')

    def extract_source_tags(self, content: str) -> List[Tuple[str, str]]:
        """
        从内容中提取 source_tag 标记

        Returns:
            List[Tuple[str, str]]: [(tag_type, original_text), ...]
        """
        tags = []

        # 检查 AI 推断标记
        if self.AI_INFERRED_PATTERN.search(content):
            tags.append(("ai_inferred:llm_generated", "⚠️ [AI 推断]"))

        # 检查来源标记
        for pattern in self.SOURCE_TAG_PATTERNS:
            matches = pattern.findall(content)
            for match in matches:
                tag_type = self._normalize_tag(match.strip())
                if tag_type:
                    tags.append((tag_type, match))

        return tags

    def validate_content(self, content: str) -> Tuple[bool, str]:
        """
        验证内容是否有有效来源标签

        Returns:
            Tuple[bool, str]: (是否有效, 警告/错误信息)
        """
        tags = self.extract_source_tags(content)

        if not tags:
            return False, "无来源标签，内容将被过滤"

        # 检查是否有有效前缀
        for tag_type, _ in tags:
            if any(tag_type.startswith(prefix) for prefix in self.VALID_PREFIXES):
                return True, ""

        return False, "来源标签格式无效"

    def process_content(self, content: str, strict_mode: bool = True) -> ContentBlock:
        """
        处理内容块，提取 source_tag 并生成渲染内容

        Args:
            content: 原始内容
            strict_mode: 是否启用硬约束（无标签不渲染）

        Returns:
            ContentBlock: 处理后的内容块
        """
        block = ContentBlock(raw_content=content)

        # 提取 source_tag
        tags = self.extract_source_tags(content)

        if tags:
            block.source_tag = tags[0][0]  # 使用第一个标签
            block.rendered_content = self._render_with_tag(content, block.source_tag)
            block.is_valid = True
        else:
            # 无标签情况
            if strict_mode:
                block.is_valid = False
                block.warning = "⚠️ [已过滤] 无来源标签，内容未渲染"
                block.rendered_content = ""
                logger.warning(f"内容被过滤（无来源标签）: {content[:50]}...")
            else:
                # P0/P1 阶段：无标签也渲染，但标记为 AI 推断
                block.source_tag = "ai_inferred:llm_generated"
                block.rendered_content = f"⚠️ [AI 推断] {content}"
                block.is_valid = True

        return block

    def process_full_article(self, content: str, strict_mode: bool = True) -> Dict:
        """
        处理完整文章，按段落分割并处理每个内容块

        Args:
            content: 完整文章内容（Markdown 格式）
            strict_mode: 是否启用硬约束

        Returns:
            Dict: {
                "blocks": [ContentBlock, ...],
                "valid_count": int,
                "filtered_count": int,
                "rendered_html": str
            }
        """
        # 按 Markdown 标题分割段落
        sections = re.split(r'(?=^## )', content, flags=re.MULTILINE)
        sections = [s.strip() for s in sections if s.strip()]

        blocks = []
        for section in sections:
            block = self.process_content(section, strict_mode)
            blocks.append(block)

        valid_count = sum(1 for b in blocks if b.is_valid)
        filtered_count = sum(1 for b in blocks if not b.is_valid)

        # 生成渲染后的 HTML（简单 Markdown 转 HTML）
        rendered_parts = []
        for block in blocks:
            if block.is_valid and block.rendered_content:
                rendered_parts.append(self._markdown_to_html(block.rendered_content))
            elif block.warning:
                rendered_parts.append(f'<div class="filtered-warning">{block.warning}</div>')

        return {
            "blocks": blocks,
            "valid_count": valid_count,
            "filtered_count": filtered_count,
            "rendered_html": "\n".join(rendered_parts),
            "source_tags": [b.source_tag for b in blocks if b.source_tag],
        }

    def _normalize_tag(self, tag: str) -> Optional[str]:
        """标准化来源标签"""
        tag = tag.strip()

        # 检查是否有有效前缀
        for prefix in self.VALID_PREFIXES:
            if tag.startswith(prefix):
                return tag

        # 尝试匹配常见来源名称
        if "知识库" in tag:
            return f"local:{tag}"
        elif "AI-Pulse" in tag or "ai_pulse" in tag.lower():
            return f"ai_pulse:{tag}"
        elif "用户" in tag or "user" in tag.lower():
            return f"user_input:{tag}"
        elif "AI 推断" in tag or "ai" in tag.lower():
            return f"ai_inferred:{tag}"

        return None

    def _render_with_tag(self, content: str, source_tag: str) -> str:
        """根据 source_tag 渲染内容"""
        if source_tag.startswith("ai_inferred"):
            # 移除原有的 AI 推断标记，统一格式
            content = self.AI_INFERRED_PATTERN.sub("", content).strip()
            return f"⚠️ [AI 推断] {content}"
        elif source_tag.startswith("local:"):
            return f"[来源：知识库] {content}"
        elif source_tag.startswith("ai_pulse:"):
            return f"[来源：AI-Pulse] {content}"
        elif source_tag.startswith("user_input:"):
            return f"[来源：用户补充] {content}"
        else:
            return f"[来源：{source_tag}] {content}"

    def _markdown_to_html(self, markdown: str) -> str:
        """简单 Markdown 转 HTML"""
        html = markdown

        # 标题
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

        # 粗体和斜体
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

        # 段落
        paragraphs = html.split('\n\n')
        html = '\n'.join(f'<p>{p}</p>' if not p.startswith('<h') else p for p in paragraphs)

        # 列表
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'(<li>.*</li>\n?)+', r'<ul>\g<0></ul>', html)

        return html


def get_source_tag_processor() -> SourceTagProcessor:
    """获取 source_tag 处理器实例"""
    return SourceTagProcessor()


# ============================================================
# 双栏 v0.1 新增：SourceItem + _enrich_sources
# ============================================================

@dataclass
class SourceItem:
    """结构化来源项"""
    type: str                       # knowledge_base / user_input / ai_search / ai_inferred
    name: str                       # 文件名 / 描述 / 来源名称
    confidence: float = 0.5         # 置信度 0.0~1.0
    tag: str = ""                   # 展示标签（含图标），如 "📄 知识库·报告-2025.pdf"

    def __post_init__(self):
        if not self.tag:
            self.tag = self._default_tag()

    def _default_tag(self) -> str:
        icon_map = {
            "knowledge_base": "📄",
            "user_input": "✏️",
            "ai_search": "🌐",
            "ai_inferred": "🤖",
        }
        icon = icon_map.get(self.type, "📄")
        label_map = {
            "knowledge_base": f"知识库·{self.name}",
            "user_input": "用户确认",
            "ai_search": f"AI搜索",
            "ai_inferred": "AI推断",
        }
        label = label_map.get(self.type, self.name)
        return f"{icon} {label}"


# 来源类型 → 置信度映射
SOURCE_CONFIDENCE_MAP = {
    "knowledge_base": 1.0,
    "user_input": 1.0,
    "ai_search": 0.5,
    "ai_inferred": 0.3,
}


def _normalize_source_type(raw: str) -> str:
    """把 LLM 输出的各种来源字符串归一化为 type"""
    r = raw.lower().strip()
    if any(k in r for k in ["知识库", "local:", "file", "文档", "报告", "pdf"]):
        return "knowledge_base"
    if any(k in r for k in ["用户", "user_input", "手动", "补充"]):
        return "user_input"
    if any(k in r for k in ["ai_pulse", "搜索", "网络", "web", "ai_search"]):
        return "ai_search"
    if any(k in r for k in ["AI 推断", "ai_inferred", "推断", "推理"]):
        return "ai_inferred"
    return "ai_inferred"  # 默认


def _enrich_sources(raw_sources: list) -> list:
    """
    slot_fill 后处理：把 string[] 转成 SourceItem[]

    Args:
        raw_sources: LLM 返回的原始 sources 数组（string[]）

    Returns:
        list[dict]: 结构化 sources（带 type/name/confidence/tag）
    """
    if not raw_sources:
        return []

    seen_types = set()
    results = []

    for s in raw_sources:
        if not s or not isinstance(s, str):
            continue
        s = s.strip()
        if not s:
            continue

        stype = _normalize_source_type(s)
        # 同类型去重（只保留第一个）
        if stype in seen_types:
            continue
        seen_types.add(stype)

        confidence = SOURCE_CONFIDENCE_MAP.get(stype, 0.3)
        item = SourceItem(type=stype, name=s, confidence=confidence)
        results.append({
            "type": item.type,
            "name": item.name,
            "confidence": item.confidence,
            "tag": item.tag,
        })

    return results
