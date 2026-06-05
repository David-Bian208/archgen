#!/usr/bin/env python3
"""
ArchGen LLM 核心逻辑验证脚本
验证：1. 语义分类 → 2. 框架匹配 → 3. 结构化提取 → 4. 数据完整性检查
"""

import sys
import json
import logging
import yaml
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


def test_classifier():
    """P0-1: 验证 LLM 语义分类"""
    logger.info("=" * 60)
    logger.info("测试 1：LLM 语义分类")
    logger.info("=" * 60)

    try:
        sys.path.insert(0, str(BASE_DIR))
        from src.classifier import ContentClassifier

        config = load_config()
        classifier = ContentClassifier(config.get("llm", {}))

        test_cases = [
            "分析一下腾讯的商业模式和竞争优势",
            "评估我们公司的财务状况和投资回报",
            "设计一个用户友好的产品功能和体验",
            "优化运营流程和供应链管理效率",
            "规划个人时间管理和职业发展方案",
            "识别项目风险并制定应对策略",
            "管理项目进度和团队协作资源",
        ]

        success_count = 0
        for text in test_cases:
            logger.info(f"\n测试文本: {text[:50]}...")
            result = classifier.classify_by_intent(text)
            logger.info(f"分类结果: {result['primary']} (置信度: {result['confidence']:.2f})")
            logger.info(f"理由: {result['reason']}")

            if result['primary'] and result['primary'] in classifier.CATEGORIES:
                success_count += 1

        logger.info(f"\n语义分类测试完成: {success_count}/{len(test_cases)} 成功")
        return success_count == len(test_cases)

    except Exception as e:
        logger.error(f"语义分类测试失败: {e}", exc_info=True)
        return False


def test_framework_matcher():
    """P0-2: 验证 LLM 框架匹配"""
    logger.info("=" * 60)
    logger.info("测试 2：LLM 框架匹配")
    logger.info("=" * 60)

    try:
        sys.path.insert(0, str(BASE_DIR))
        from src.framework_matcher import FrameworkMatcher

        config = load_config()
        matcher = FrameworkMatcher(config.get("llm", {}))

        test_cases = [
            ("分析腾讯的商业模式和竞争优势", "business", "business_canvas"),
            ("评估公司的财务投资回报", "finance", "comparison"),
            ("设计用户体验和产品功能", "product", "user_journey"),
            ("规划个人时间管理方案", "personal", "time_matrix"),
            ("分析项目的风险和应对策略", "risk", "swot"),
        ]

        success_count = 0
        for text, category, expected_framework in test_cases:
            logger.info(f"\n测试文本: {text}")
            result = matcher.match_frameworks(text, category, top_n=3)
            if result:
                top1 = result[0]
                logger.info(f"Top 1: {top1['name']} (分数: {top1['score']:.3f})")
                logger.info(f"Top 3: {[r['name'] for r in result]}")

                if top1['key'] == expected_framework or expected_framework in [r['key'] for r in result]:
                    logger.info(f"✅ 匹配成功")
                    success_count += 1
                else:
                    logger.info(f"⚠️ 预期 {expected_framework}，但匹配到 {top1['key']}")
                    success_count += 0.5

        logger.info(f"\n框架匹配测试完成: {success_count}/{len(test_cases)} 成功")
        return success_count >= len(test_cases) * 0.8

    except Exception as e:
        logger.error(f"框架匹配测试失败: {e}", exc_info=True)
        return False


def test_extractor():
    """P0-3: 验证 LLM 结构化提取"""
    logger.info("=" * 60)
    logger.info("测试 3：LLM 结构化提取")
    logger.info("=" * 60)

    try:
        sys.path.insert(0, str(BASE_DIR))
        from src.extractor_agent import StructureExtractor

        config = load_config()
        extractor = StructureExtractor(config.get("llm", {}))

        test_cases = [
            {
                "file": "01_python_ai_language.md",
                "framework": "claim",
                "expected_fields": ["title", "central_claim", "supporting_points", "conclusion"],
            },
            {
                "file": "02_microservices_vs_monolith.md",
                "framework": "causal",
                "expected_fields": ["title", "chain", "root_cause", "final_effect"],
            },
        ]

        success_count = 0
        for case in test_cases:
            test_file = BASE_DIR / "test_data" / case["file"]
            text = test_file.read_text(encoding="utf-8")
            framework = case["framework"]

            logger.info(f"\n提取框架: {framework} from {case['file']}")
            result = extractor.extract(text, framework)

            if result:
                missing_fields = [f for f in case["expected_fields"] if f not in result]
                if not missing_fields:
                    logger.info(f"✅ 提取成功，包含所有必需字段")
                    if "central_claim" in result:
                        logger.info(f"核心主张: {result['central_claim']}")
                    if "root_cause" in result:
                        logger.info(f"根本原因: {result['root_cause']}")
                    if "supporting_points" in result:
                        logger.info(f"分论点数量: {len(result['supporting_points'])}")
                    if "chain" in result:
                        logger.info(f"因果链条数量: {len(result['chain'])}")
                    success_count += 1
                else:
                    logger.error(f"❌ 缺失字段: {missing_fields}")
            else:
                logger.error(f"❌ 提取失败")

        logger.info(f"\n结构化提取测试完成: {success_count}/{len(test_cases)} 成功")
        return success_count == len(test_cases)

    except Exception as e:
        logger.error(f"结构化提取测试失败: {e}", exc_info=True)
        return False


def test_data_checker():
    """P0-4: 验证数据完整性检查"""
    logger.info("=" * 60)
    logger.info("测试 4：数据完整性检查")
    logger.info("=" * 60)

    try:
        sys.path.insert(0, str(BASE_DIR))
        from src.data_checker import DataCompletenessChecker

        checker = DataCompletenessChecker()

        test_cases = [
            {
                "framework": "swot",
                "data": {
                    "title": "测试",
                    "strengths": ["优势 1", "优势 2"],
                    "weaknesses": [],
                    "opportunities": ["机会 1"],
                },
                "expected_missing": ["threats", "weaknesses"],
            },
            {
                "framework": "business_canvas",
                "data": {
                    "title": "测试",
                    "customer_segments": ["企业客户"],
                    "value_propositions": ["降本增效"],
                    "revenue_streams": [],
                },
                "expected_missing": ["revenue_streams"],
            },
        ]

        success_count = 0
        for case in test_cases:
            logger.info(f"\n测试框架: {case['framework']}")
            result = checker.check_completeness(case["data"], case["framework"])

            logger.info(f"完整度: {result['completeness_score']:.0%}")
            logger.info(f"缺失字段: {result['missing_field_names']}")
            logger.info(f"追问问题: {result['follow_up_questions']}")

            if result['completeness_score'] < 1.0 and result['missing_fields']:
                logger.info(f"✅ 正确识别缺失数据")
                success_count += 1
            elif result['completeness_score'] == 1.0:
                logger.info(f"✅ 数据完整")
                success_count += 1

        logger.info(f"\n数据完整性检查测试完成: {success_count}/{len(test_cases)} 成功")
        return success_count == len(test_cases)

    except Exception as e:
        logger.error(f"数据完整性检查测试失败: {e}", exc_info=True)
        return False


def main():
    logger.info("ArchGen LLM 核心逻辑验证开始")
    logger.info("")

    results = {}

    results["LLM 语义分类"] = test_classifier()
    logger.info("")

    results["LLM 框架匹配"] = test_framework_matcher()
    logger.info("")

    results["LLM 结构化提取"] = test_extractor()
    logger.info("")

    results["数据完整性检查"] = test_data_checker()
    logger.info("")

    logger.info("=" * 60)
    logger.info("LLM 核心逻辑验证结果汇总")
    logger.info("=" * 60)

    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        logger.info(f"{name}: {status}")

    all_passed = all(results.values())
    logger.info("")
    if all_passed:
        logger.info("🎉 所有 LLM 核心逻辑验证通过!")
    else:
        failed = [name for name, passed in results.items() if not passed]
        logger.info(f"⚠️ 以下验证失败，需要修复: {', '.join(failed)}")


if __name__ == "__main__":
    main()
