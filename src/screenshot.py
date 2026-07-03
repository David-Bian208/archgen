"""Screenshot Service - 截图服务模块"""

import logging
from pathlib import Path
from typing import Optional, Dict

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


class ScreenshotService:
    SIZES = {
        "wechat": (1080, 1920),
        "xiaohongshu": (1080, 1440),
        "ppt": (1920, 1080),
        "default": (1200, 800),
    }

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._browser = None

    async def capture(
        self,
        html_content: str,
        output_path: str,
        size: str = "default",
    ) -> str:
        """
        截图 HTML 内容并保存为 PNG

        Args:
            html_content: HTML 内容字符串
            output_path: 输出 PNG 路径
            size: 尺寸预设

        Returns:
            输出文件路径
        """
        logger.info(f"开始截图，尺寸: {size}，输出: {output_path}")
        width, height = self.SIZES.get(size, self.SIZES["default"])

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": width, "height": height},
            )
            page = await context.new_page()

            # 加载 HTML 内容
            await page.set_content(html_content, wait_until="networkidle")

            # 等待字体加载和渲染完成
            await page.wait_for_timeout(1000)

            # 截图（截取整个页面内容，不只是 viewport）
            await page.screenshot(
                path=str(output_path),
                full_page=True,
            )

            await browser.close()

        logger.info(f"截图完成: {output_path}")
        return str(output_path)

    async def capture_from_file(
        self,
        html_file: str,
        output_path: str,
        size: str = "default",
    ) -> str:
        """
        截图 HTML 文件并保存为 PNG

        Args:
            html_file: HTML 文件路径
            output_path: 输出 PNG 路径
            size: 尺寸预设

        Returns:
            输出文件路径
        """
        logger.info(f"开始截图文件: {html_file}，输出: {output_path}")
        width, height = self.SIZES.get(size, self.SIZES["default"])

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        file_url = Path(html_file).resolve().as_uri()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": width, "height": height},
            )
            page = await context.new_page()

            # 加载 HTML 文件
            await page.goto(file_url, wait_until="networkidle")

            # 等待字体加载和渲染完成
            await page.wait_for_timeout(1000)

            # 截图
            await page.screenshot(
                path=str(output_path),
                full_page=False,
            )

            await browser.close()

        logger.info(f"截图完成: {output_path}")
        return str(output_path)
