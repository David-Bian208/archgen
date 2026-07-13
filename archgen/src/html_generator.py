"""HTML Generator - 视觉渲染模块"""

import logging
from pathlib import Path
from typing import Dict, Optional

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)


class HTMLGenerator:
    TEMPLATES = {
        "claim": "templates/claim.html",
        "causal": "templates/causal.html",
        "system": "templates/system.html",
        "comparison": "templates/comparison.html",
        "process": "templates/process.html",
        "swot": "templates/swot_matrix.html",
        "business_canvas": "templates/business_canvas.html",
        "pestel": "templates/pestel.html",
        "user_journey": "templates/user_journey.html",
        "time_matrix": "templates/time_matrix.html",
    }

    STYLES = {
        "minimal": "styles/minimal.css",
        "business": "styles/business.css",
        "tech": "styles/tech.css",
    }

    SIZES = {
        "wechat": (1080, 1920),
        "xiaohongshu": (1080, 1440),
        "ppt": (1920, 1080),
        "default": (1200, 800),
    }

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.base_dir = Path(__file__).parent.parent
        self.env = Environment(
            loader=FileSystemLoader(str(self.base_dir)),
            autoescape=True,
        )

    def render(
        self,
        data: Dict,
        article_type: str,
        style: str = "minimal",
        size: str = "default",
    ) -> str:
        """渲染 HTML"""
        logger.info(f"渲染 {article_type} 类型文章，风格: {style}，尺寸: {size}")

        if article_type not in self.TEMPLATES:
            raise ValueError(f"不支持的模板类型: {article_type}")
        if style not in self.STYLES:
            raise ValueError(f"不支持的样式: {style}")

        # 加载模板
        template_path = self.TEMPLATES[article_type]
        template = self.env.get_template(template_path)

        # 加载 CSS
        css_path = self.STYLES[style]
        css_file = self.base_dir / css_path
        css_content = ""
        if css_file.exists():
            css_content = css_file.read_text(encoding="utf-8")
        else:
            logger.warning(f"样式文件不存在: {css_path}")

        # 获取尺寸
        width, height = self.get_size(size)

        # 提取数据字段（去掉 metadata 和 layout_hints）
        template_data = {k: v for k, v in data.items() if k not in ("metadata", "layout_hints")}
        template_data["css"] = css_content
        template_data["width"] = width
        template_data["height"] = height

        # 渲染 HTML
        html = template.render(**template_data)
        return html

    def get_size(self, size: str) -> tuple:
        """获取尺寸预设"""
        return self.SIZES.get(size, self.SIZES["default"])
