#!/usr/bin/env python3
"""
ArchGen 核心逻辑验证脚本
验证：1. 文件读取 → 2. HTML 渲染 → 3. 截图生成
"""

import sys
import json
import asyncio
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent


def test_file_read():
    """P0-1: 验证文件读取"""
    logger.info("=" * 60)
    logger.info("测试 1：文件读取")
    logger.info("=" * 60)

    test_files = list((BASE_DIR / "test_data").glob("*.md"))
    if not test_files:
        logger.error("❌ 没有找到测试文件")
        return False

    success = True
    for f in test_files:
        try:
            content = f.read_text(encoding="utf-8")
            logger.info(f"✅ 读取成功: {f.name} ({len(content)} 字符)")
        except Exception as e:
            logger.error(f"❌ 读取失败 {f.name}: {e}")
            success = False

    return success


def test_html_generator():
    """P0-2: 验证 HTML 渲染"""
    logger.info("=" * 60)
    logger.info("测试 2：HTML 渲染")
    logger.info("=" * 60)

    try:
        sys.path.insert(0, str(BASE_DIR))
        from src.html_generator import HTMLGenerator

        generator = HTMLGenerator()

        test_data = {
            "title": "测试 SWOT 分析",
            "strengths": ["优势 1", "优势 2"],
            "weaknesses": ["劣势 1"],
            "opportunities": ["机会 1", "机会 2"],
            "threats": ["威胁 1"],
            "summary": "这是一个测试",
        }

        html = generator.render(test_data, "swot", "minimal", "default")

        if html and "<html" in html.lower():
            output_path = BASE_DIR / "output" / "test_swot.html"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(html, encoding="utf-8")
            logger.info(f"✅ HTML 渲染成功! 输出: {output_path}")
            logger.info(f"   HTML 长度: {len(html)} 字符")
            return True
        else:
            logger.error("❌ HTML 渲染失败")
            return False

    except Exception as e:
        logger.error(f"❌ HTML 渲染测试失败: {e}", exc_info=True)
        return False


async def test_screenshot():
    """P0-3: 验证截图生成"""
    logger.info("=" * 60)
    logger.info("测试 3：截图生成")
    logger.info("=" * 60)

    try:
        sys.path.insert(0, str(BASE_DIR))
        from src.screenshot import ScreenshotService

        html_content = """
        <html>
        <head><style>body{font-family:Arial;padding:40px;text-align:center;}</style></head>
        <body>
            <h1>ArchGen 测试截图</h1>
            <p>这是一个测试 HTML 页面</p>
            <div style="margin-top:20px;padding:20px;background:#f0f0f0;border-radius:8px;">
                如果能看到这段文字，说明截图功能正常
            </div>
        </body>
        </html>
        """

        screenshot = ScreenshotService()
        output_path = BASE_DIR / "output" / "test_screenshot.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        result = await screenshot.capture(html_content, str(output_path), "default")

        if Path(result).exists():
            file_size = Path(result).stat().st_size
            logger.info(f"✅ 截图成功! 输出: {result} ({file_size} bytes)")
            return True
        else:
            logger.error("❌ 截图失败")
            return False

    except Exception as e:
        logger.error(f"❌ 截图测试失败: {e}", exc_info=True)
        return False


async def test_all_templates():
    """P0-4: 验证所有 10 个模板"""
    logger.info("=" * 60)
    logger.info("测试 4：验证所有 10 个模板")
    logger.info("=" * 60)

    try:
        sys.path.insert(0, str(BASE_DIR))
        from src.html_generator import HTMLGenerator

        generator = HTMLGenerator()

        test_cases = {
            "swot": {
                "title": "SWOT 测试",
                "strengths": ["优势 1", "优势 2"],
                "weaknesses": ["劣势 1"],
                "opportunities": ["机会 1"],
                "threats": ["威胁 1"],
                "summary": "测试总结",
            },
            "business_canvas": {
                "title": "商业模式画布测试",
                "customer_segments": ["企业客户", "个人用户"],
                "value_propositions": ["降本增效"],
                "channels": ["线上渠道"],
                "customer_relationships": ["专属客服"],
                "revenue_streams": ["订阅费"],
                "key_resources": ["技术团队"],
                "key_activities": ["产品研发"],
                "key_partnerships": ["供应商"],
                "cost_structure": ["研发成本"],
            },
            "pestel": {
                "title": "PESTEL 测试",
                "political": ["政策支持"],
                "economic": ["消费升级"],
                "social": ["环保意识"],
                "technological": ["技术进步"],
                "environmental": ["碳排放要求"],
                "legal": ["安全法规"],
                "summary": "测试总结",
            },
            "claim": {
                "title": "主张型测试",
                "central_claim": "Python 是 AI 时代首选语言",
                "supporting_points": [
                    {"label": "生态系统", "text": "丰富的库", "weight": 0.9},
                    {"label": "学习曲线", "text": "容易上手", "weight": 0.8},
                ],
                "evidence": ["证据 1"],
                "conclusion": "Python 占据主导地位",
            },
            "causal": {
                "title": "因果分析测试",
                "chain": [
                    {"step": 1, "cause": "原因 A", "effect": "结果 B"},
                    {"step": 2, "cause": "原因 B", "effect": "结果 C"},
                ],
                "root_cause": "根本原因",
                "final_effect": "最终结果",
            },
            "system": {
                "title": "系统架构测试",
                "overview": "这是一个测试系统",
                "modules": [
                    {"name": "模块 A", "role": "职责 A", "connections": ["模块 B"]},
                    {"name": "模块 B", "role": "职责 B", "connections": ["模块 A"]},
                ],
            },
            "comparison": {
                "title": "对比分析测试",
                "dimensions": ["性能", "成本", "易用性"],
                "items": [
                    {"name": "方案 A", "scores": ["高", "低", "中"]},
                    {"name": "方案 B", "scores": ["中", "中", "高"]},
                ],
            },
            "process": {
                "title": "流程分析测试",
                "steps": [
                    {"order": 1, "title": "步骤 1", "description": "描述 1", "tips": ["提示 1"]},
                    {"order": 2, "title": "步骤 2", "description": "描述 2", "tips": []},
                ],
            },
            "user_journey": {
                "title": "用户旅程测试",
                "persona": "25-35 岁白领",
                "stages": [
                    {"order": 1, "name": "认知", "description": "看到广告", "touchpoints": ["广告"], "pain_points": [], "emotion": 3},
                    {"order": 2, "name": "购买", "description": "下单", "touchpoints": ["网站"], "pain_points": ["流程复杂"], "emotion": 4},
                ],
                "summary": "测试总结",
            },
            "time_matrix": {
                "title": "时间管理矩阵测试",
                "q1_important_urgent": [{"name": "紧急项目", "description": "今天必须交付"}],
                "q2_important_not_urgent": [{"name": "学习", "description": "本月计划"}],
                "q3_not_important_urgent": [{"name": "回复邮件", "description": "可以委托"}],
                "q4_not_important_not_urgent": [{"name": "刷社交媒体", "description": "控制时间"}],
                "summary": "测试总结",
            },
        }

        success_count = 0
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        for framework_key, data in test_cases.items():
            try:
                html = generator.render(data, framework_key, "minimal", "default")
                if html and "<html" in html.lower():
                    output_path = output_dir / f"test_{framework_key}.html"
                    output_path.write_text(html, encoding="utf-8")
                    logger.info(f"✅ {framework_key}: 渲染成功 ({len(html)} 字符)")
                    success_count += 1
                else:
                    logger.error(f"❌ {framework_key}: 渲染失败")
            except Exception as e:
                logger.error(f"❌ {framework_key}: {e}")

        logger.info(f"\n模板验证完成: {success_count}/10 成功")
        return success_count == 10

    except Exception as e:
        logger.error(f"❌ 模板验证失败: {e}", exc_info=True)
        return False


async def main():
    logger.info("ArchGen 核心逻辑验证开始")
    logger.info("")

    results = {}

    results["文件读取"] = test_file_read()
    logger.info("")

    results["HTML 渲染 (SWOT)"] = test_html_generator()
    logger.info("")

    results["10 个模板渲染"] = await test_all_templates()
    logger.info("")

    results["截图生成"] = await test_screenshot()
    logger.info("")

    logger.info("=" * 60)
    logger.info("验证结果汇总")
    logger.info("=" * 60)

    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        logger.info(f"{name}: {status}")

    all_passed = all(results.values())
    logger.info("")
    if all_passed:
        logger.info("🎉 所有核心逻辑验证通过!")
    else:
        failed = [name for name, passed in results.items() if not passed]
        logger.info(f"⚠️ 以下验证失败，需要修复: {', '.join(failed)}")


if __name__ == "__main__":
    asyncio.run(main())
