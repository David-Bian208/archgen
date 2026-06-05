#!/usr/bin/env python3
"""
ArchGen 端到端测试脚本
完整流程：文件读取 → 语义分类 → 框架匹配 → 结构化提取 → HTML 渲染 → 截图生成
"""

import sys
import json
import logging
import yaml
import asyncio
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent


def load_config() -> dict:
    """加载配置文件"""
    config_path = BASE_DIR / "config" / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


async def end_to_end_test():
    """端到端完整流程测试"""
    logger.info("=" * 60)
    logger.info("端到端测试：完整流程验证")
    logger.info("=" * 60)

    config = load_config()

    # Step 1: 读取测试文件
    logger.info("\n[Step 1] 读取测试文件")
    test_files = list((BASE_DIR / "test_data").glob("*.md"))
    if not test_files:
        logger.error("❌ 没有找到测试文件")
        return False

    test_file = test_files[0]
    text = test_file.read_text(encoding="utf-8")
    logger.info(f"✅ 读取成功: {test_file.name} ({len(text)} 字符)")

    # Step 2: 语义分类
    logger.info("\n[Step 2] 语义分类")
    sys.path.insert(0, str(BASE_DIR))
    from src.classifier import ContentClassifier

    classifier = ContentClassifier(config.get("llm", {}))
    classification = classifier.classify_by_intent(text)
    logger.info(f"✅ 分类结果: {classification['primary']} (置信度: {classification['confidence']:.2f})")

    # Step 3: 框架匹配
    logger.info("\n[Step 3] 框架匹配")
    from src.framework_matcher import FrameworkMatcher

    matcher = FrameworkMatcher(config.get("llm", {}))
    frameworks = matcher.match_frameworks(text, classification['primary'], top_n=3)
    if frameworks:
        top_framework = frameworks[0]
        logger.info(f"✅ Top 1 框架: {top_framework['name']} (分数: {top_framework['score']:.3f})")
        logger.info(f"   框架 Key: {top_framework['key']}")
    else:
        logger.error("❌ 框架匹配失败")
        return False

    # Step 4: 结构化提取
    logger.info("\n[Step 4] 结构化提取")
    from src.extractor_agent import StructureExtractor

    extractor = StructureExtractor(config.get("llm", {}))
    extracted_data = extractor.extract(text, top_framework['key'])
    if extracted_data:
        logger.info(f"✅ 提取成功，包含 {len(extracted_data)} 个字段")
        logger.info(f"   字段列表: {list(extracted_data.keys())[:5]}...")
    else:
        logger.error("❌ 结构化提取失败")
        return False

    # Step 5: 数据完整性检查
    logger.info("\n[Step 5] 数据完整性检查")
    from src.data_checker import DataCompletenessChecker

    checker = DataCompletenessChecker()
    completeness = checker.check_completeness(extracted_data, top_framework['key'])
    logger.info(f"✅ 完整度: {completeness['completeness_score']:.0%}")
    logger.info(f"   缺失字段: {completeness['missing_field_names']}")

    # Step 6: HTML 渲染
    logger.info("\n[Step 6] HTML 渲染")
    from src.html_generator import HTMLGenerator

    generator = HTMLGenerator()
    extracted_data['title'] = extracted_data.get('title', test_file.stem)
    html = generator.render(extracted_data, top_framework['key'], "minimal", "default")
    if html and "<html" in html.lower():
        output_html = BASE_DIR / "output" / f"e2e_{top_framework['key']}.html"
        output_html.parent.mkdir(parents=True, exist_ok=True)
        output_html.write_text(html, encoding="utf-8")
        logger.info(f"✅ HTML 渲染成功: {output_html} ({len(html)} 字符)")
    else:
        logger.error("❌ HTML 渲染失败")
        return False

    # Step 7: 截图生成
    logger.info("\n[Step 7] 截图生成")
    from src.screenshot import ScreenshotService

    screenshot = ScreenshotService()
    output_png = BASE_DIR / "output" / f"e2e_{top_framework['key']}.png"
    result = await screenshot.capture(html, str(output_png), "default")
    if Path(result).exists():
        file_size = Path(result).stat().st_size
        logger.info(f"✅ 截图生成成功: {result} ({file_size} bytes)")
    else:
        logger.error("❌ 截图生成失败")
        return False

    logger.info("\n" + "=" * 60)
    logger.info("🎉 端到端测试全部通过!")
    logger.info("=" * 60)
    logger.info(f"完整流程: 文件读取 → 语义分类({classification['primary']}) → 框架匹配({top_framework['name']}) → 结构化提取 → HTML 渲染 → 截图生成")
    logger.info(f"输出文件: {output_html}, {result}")

    return True


async def main():
    logger.info("ArchGen 端到端测试开始")
    logger.info("")

    success = await end_to_end_test()

    if not success:
        logger.error("\n❌ 端到端测试失败")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
