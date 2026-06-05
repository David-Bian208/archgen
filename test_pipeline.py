#!/usr/bin/env python
"""端到端测试脚本"""

import sys
import asyncio
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.router_agent import ArticleRouter
from src.extractor_agent import StructureExtractor
from src.html_generator import HTMLGenerator
from src.screenshot import ScreenshotService


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

async def test_pipeline(test_file: str):
    """测试完整流水线"""
    logger = logging.getLogger("test")
    
    # 读取测试文章
    test_path = Path(__file__).parent / "test_data" / test_file
    if not test_path.exists():
        logger.error(f"测试文件不存在: {test_path}")
        return
    
    markdown = test_path.read_text(encoding="utf-8")
    logger.info(f"加载测试文章: {test_file} ({len(markdown)} 字符)")
    
    # 1. Router Agent
    logger.info("=== 步骤 1: 文章分类 ===")
    router = ArticleRouter({
        "api_key": "test-key",  # 替换为真实 key
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
    })
    
    try:
        # 使用规则分类测试（不需要 API key）
        result = router.classify_by_rules(markdown)
        logger.info(f"分类结果: {result}")
        article_type = result["type"]
    except Exception as e:
        logger.error(f"分类失败: {e}")
        return
    
    # 2. Extractor Agent（跳过，需要 API key）
    logger.info("=== 步骤 2: 结构提取 ===")
    logger.info("跳过（需要 LLM API Key）")
    
    # 3. HTML Generator（使用模拟数据）
    logger.info("=== 步骤 3: HTML 渲染 ===")
    generator = HTMLGenerator()
    
    # 模拟提取数据
    mock_data = {
        "title": "测试标题",
        "central_claim": "这是核心主张",
        "supporting_points": [
            {"label": "分论点1", "text": "分论点内容1", "weight": 0.9},
            {"label": "分论点2", "text": "分论点内容2", "weight": 0.7},
        ],
        "evidence": ["证据1", "证据2"],
        "conclusion": "这是结论",
    }
    
    try:
        html = generator.render(mock_data, "claim", "minimal", "default")
        logger.info(f"HTML 渲染成功 ({len(html)} 字符)")
        
        # 保存 HTML
        output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(exist_ok=True)
        html_path = output_dir / "test_output.html"
        html_path.write_text(html, encoding="utf-8")
        logger.info(f"HTML 已保存: {html_path}")
    except Exception as e:
        logger.error(f"HTML 渲染失败: {e}", exc_info=True)
        return
    
    # 4. Screenshot（跳过，需要 Playwright）
    logger.info("=== 步骤 4: 截图 ===")
    logger.info("跳过（需要安装 Playwright）")
    
    logger.info("=== 测试完成 ===")
    logger.info(f"HTML 文件已生成: {html_path}")
    logger.info("请在浏览器中打开查看效果")


if __name__ == "__main__":
    test_file = sys.argv[1] if len(sys.argv) > 1 else "01_python_ai_language.md"
    asyncio.run(test_pipeline(test_file))
