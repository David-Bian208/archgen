#!/usr/bin/env python
"""ArchGen v2.0 核心模块测试脚本"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.knowledge_base import KnowledgeBaseReader
from src.classifier import ContentClassifier
from src.framework_matcher import FrameworkMatcher
from src.data_checker import DataCompletenessChecker
from src.extractor_agent import StructureExtractor
from src.html_generator import HTMLGenerator


def test_all():
    """测试所有核心模块"""
    passed = 0
    failed = 0

    print("=" * 60)
    print("ArchGen v2.0 核心模块测试")
    print("=" * 60)

    # ===== 测试 1: 知识库模块 =====
    print("\n[测试 1] 知识库读取模块")
    try:
        kb = KnowledgeBaseReader({
            "root_path": str(Path(__file__).parent / "knowledge_base"),
            "mode": "local",
        })
        categories = kb.list_categories()
        assert len(categories) > 0, "应该有至少一个分类"
        print(f"  ✓ 分类数: {len(categories)}")

        files = kb.list_directory("business")
        assert len(files) > 0, "business 目录下应该有文件"
        print(f"  ✓ business 文件数: {len(files)}")

        content = kb.read_file("business/swot_example.md")
        assert content is not None, "应该能读取文件"
        print(f"  ✓ 文件内容长度: {len(content)}")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failed += 1

    # ===== 测试 2: 分类器模块 =====
    print("\n[测试 2] 分类器模块")
    try:
        classifier = ContentClassifier()
        categories = classifier.get_categories()
        assert len(categories) == 7, "应该有 7 个分类"
        print(f"  ✓ 分类数: {len(categories)}")

        info = classifier.get_category_info("business")
        assert info is not None, "应该能获取分类信息"
        print(f"  ✓ business 分类: {info['name']}")

        # 规则分类测试
        result = classifier._classify_by_rules("我们的商业模式是 SaaS 订阅制，目标客户是企业")
        assert result["primary"] == "business", f"应该识别为 business，实际: {result['primary']}"
        print(f"  ✓ 规则分类: {result['primary']} (置信度: {result['confidence']})")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failed += 1

    # ===== 测试 3: 框架匹配模块 =====
    print("\n[测试 3] 框架匹配模块")
    try:
        matcher = FrameworkMatcher()
        frameworks = matcher.get_all_frameworks()
        assert len(frameworks) == 10, f"应该有 10 个框架，实际: {len(frameworks)}"
        print(f"  ✓ 框架数: {len(frameworks)}")

        # 关键词匹配测试
        text = "分析公司的优势劣势机会威胁"
        scores = matcher._keyword_match(text)
        assert scores["swot"] > 0, "SWOT 关键词应该匹配"
        print(f"  ✓ SWOT 关键词分数: {scores['swot']}")

        # 规则匹配测试（带分类）
        scores = matcher._rule_match(text, "business")
        assert scores["swot"] > 0.5, "business 分类下 SWOT 应该得高分"
        print(f"  ✓ business 下 SWOT 规则分数: {scores['swot']}")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failed += 1

    # ===== 测试 4: 数据检查模块 =====
    print("\n[测试 4] 数据检查模块")
    try:
        checker = DataCompletenessChecker()

        # 完整数据测试
        complete_data = {
            "title": "SWOT 分析",
            "strengths": ["技术领先", "品牌知名度高"],
            "weaknesses": ["成本较高"],
            "opportunities": ["市场增长"],
            "threats": ["竞争加剧"],
        }
        result = checker.check_completeness(complete_data, "swot")
        assert result["complete"] is True, "完整数据应该通过检查"
        print(f"  ✓ 完整数据检查通过 (完整度: {result['completeness_score']})")

        # 缺失数据测试
        incomplete_data = {"title": "SWOT 分析"}
        result = checker.check_completeness(incomplete_data, "swot")
        assert result["complete"] is False, "缺失数据应该不通过"
        assert len(result["missing_fields"]) == 4, f"应该缺失 4 个字段，实际: {len(result['missing_fields'])}"
        print(f"  ✓ 缺失数据检查通过 (缺失: {result['missing_field_names']})")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failed += 1

    # ===== 测试 5: HTML Generator =====
    print("\n[测试 5] HTML Generator")
    try:
        generator = HTMLGenerator()

        # 测试 SWOT 模板
        swot_data = {
            "title": "SWOT 分析",
            "strengths": ["技术领先", "团队优秀"],
            "weaknesses": ["成本高"],
            "opportunities": ["市场增长"],
            "threats": ["竞争加剧"],
            "summary": "总结建议",
        }
        html = generator.render(swot_data, "swot", "minimal", "default")
        assert "SWOT 分析" in html, "应该包含标题"
        assert "技术领先" in html, "应该包含优势内容"
        print(f"  ✓ SWOT 模板渲染成功 ({len(html)} 字符)")

        # 测试主张型模板（v1.0 复用）
        claim_data = {
            "title": "主张型分析",
            "central_claim": "核心主张",
            "supporting_points": [
                {"label": "分论点1", "text": "内容", "weight": 0.9},
            ],
            "conclusion": "结论",
        }
        html = generator.render(claim_data, "claim", "minimal", "default")
        assert "主张型分析" in html, "应该包含标题"
        print(f"  ✓ 主张型模板渲染成功 ({len(html)} 字符)")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failed += 1

    # ===== 总结 =====
    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    if failed == 0:
        print("\n✅ 所有核心模块测试通过！")
    else:
        print(f"\n⚠️ 有 {failed} 个测试失败，请检查错误信息")

    return failed == 0


if __name__ == "__main__":
    success = test_all()
    sys.exit(0 if success else 1)
