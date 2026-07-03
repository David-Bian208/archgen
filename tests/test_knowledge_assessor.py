"""
知识评估模块单元测试
"""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from src.knowledge_assessor import KnowledgeAssessor, get_knowledge_assessor

# 测试配置
TEST_LLM_CONFIG = {
    "base_url": "https://api.deepseek.com/v1",
    "api_key": "test-key",
    "model": "deepseek-chat",
    "timeout": 10,
}


@pytest.fixture
def assessor():
    """创建测试用评估器"""
    return KnowledgeAssessor(TEST_LLM_CONFIG, cache_enabled=False)


@pytest.fixture
def assessor_with_cache():
    """创建带缓存的评估器"""
    return KnowledgeAssessor(TEST_LLM_CONFIG, cache_enabled=True)


class TestKnowledgeAssessor:
    """知识评估器测试"""

    def test_build_cache_key(self, assessor):
        """测试缓存 key 生成"""
        key1 = assessor._build_cache_key("topic1", "context1")
        key2 = assessor._build_cache_key("topic1", "context1")
        key3 = assessor._build_cache_key("topic2", "context1")

        assert key1 == key2
        assert key1 != key3
        assert len(key1) == 32  # MD5 长度

    def test_parse_result_valid_json(self, assessor):
        """测试解析有效 JSON"""
        result = {
            "content": '{"knowledge_level": "L0", "reason": "有案例支撑", "confidence": "high"}'
        }
        parsed = assessor._parse_result(result)

        assert parsed["knowledge_level"] == "L0"
        assert parsed["reason"] == "有案例支撑"
        assert parsed["confidence"] == "high"

    def test_parse_result_markdown_code_block(self, assessor):
        """测试解析 Markdown 代码块"""
        result = {
            "content": '''```json
{
  "knowledge_level": "L1",
  "reason": "缺少案例",
  "confidence": "medium"
}
```'''
        }
        parsed = assessor._parse_result(result)

        assert parsed["knowledge_level"] == "L1"
        assert parsed["reason"] == "缺少案例"
        assert parsed["confidence"] == "medium"

    def test_parse_result_invalid_json(self, assessor):
        """测试解析无效 JSON（默认降级到 L1）"""
        result = {"content": "这是一段无效的 JSON"}
        parsed = assessor._parse_result(result)

        assert parsed["knowledge_level"] == "L1"

    def test_parse_result_invalid_level(self, assessor):
        """测试解析无效知识级别（默认降级到 L1）"""
        result = {
            "content": '{"knowledge_level": "L5", "reason": "无效级别", "confidence": "high"}'
        }
        parsed = assessor._parse_result(result)

        assert parsed["knowledge_level"] == "L1"

    def test_should_reevaluate_l0(self, assessor):
        """测试 L0 需要重新评估"""
        from src.degradation_chain import DegradationChain
        chain = DegradationChain(TEST_LLM_CONFIG)
        assert chain._should_reevaluate("L0") is True

    def test_should_reevaluate_l2(self, assessor):
        """测试 L2 不需要重新评估"""
        from src.degradation_chain import DegradationChain
        chain = DegradationChain(TEST_LLM_CONFIG)
        assert chain._should_reevaluate("L2") is False

    @pytest.mark.asyncio
    async def test_assess_llm_failure_fallback(self, assessor):
        """测试 LLM 调用失败时降级到 L1"""
        with patch("httpx.AsyncClient.post", side_effect=Exception("网络错误")):
            result = await assessor.assess("测试话题", "测试上下文")

            assert result["knowledge_level"] == "L1"
            assert result["reason"] == "LLM 调用失败，保守降级"
            assert result["confidence"] == "low"

    def test_cache_dir_exists(self, assessor_with_cache):
        """测试缓存目录存在"""
        from src.knowledge_assessor import CACHE_DIR
        assert CACHE_DIR.exists()
        assert CACHE_DIR.is_dir()

    def test_clear_cache(self, assessor_with_cache):
        """测试清除缓存"""
        import time
        # 先保存一些缓存（使用当前时间戳，避免 TTL 过期）
        cache_key = "test_key_123"
        assessor_with_cache._save_cache(cache_key, {
            "knowledge_level": "L0",
            "reason": "测试",
            "confidence": "high",
            "timestamp": time.time(),
        })

        # 验证缓存存在
        assert assessor_with_cache._load_cache(cache_key) is not None

        # 清除缓存
        assessor_with_cache.clear_cache(cache_key)

        # 验证缓存已删除
        assert assessor_with_cache._load_cache(cache_key) is None


class TestDegradationChain:
    """降级链测试"""

    def test_parse_content_result(self):
        """测试解析内容型结果（L0/L1）"""
        from src.degradation_chain import DegradationChain
        chain = DegradationChain(TEST_LLM_CONFIG)

        content = '{"content": "测试内容", "evidence_quote": "案例", "gap_hint": "待补充"}'
        result = chain._parse_content_result(content)

        assert result["content"] == "测试内容"
        assert result["evidence_quote"] == "案例"
        assert result["gap_hint"] == "待补充"

    def test_parse_questions_result(self):
        """测试解析问题型结果（L2）"""
        from src.degradation_chain import DegradationChain
        chain = DegradationChain(TEST_LLM_CONFIG)

        content = '''{"questions": [
            {"question": "问题 1", "hint": "提示 1"},
            {"question": "问题 2", "hint": "提示 2"}
        ]}'''
        result = chain._parse_questions_result(content)

        assert len(result["questions"]) == 2
        assert result["questions"][0]["question"] == "问题 1"

    def test_extract_questions_from_text(self):
        """测试从文本提取问题"""
        from src.degradation_chain import DegradationChain
        chain = DegradationChain(TEST_LLM_CONFIG)

        text = """1. 第一个问题？这是提示
2. 第二个问题？这是另一个提示"""

        questions = chain._extract_questions_from_text(text)

        assert len(questions) >= 1

    def test_should_reevaluate(self):
        """测试重新评估规则"""
        from src.degradation_chain import DegradationChain
        chain = DegradationChain(TEST_LLM_CONFIG)

        assert chain._should_reevaluate("L0") is True
        assert chain._should_reevaluate("L1") is True
        assert chain._should_reevaluate("L2") is False
        assert chain._should_reevaluate("L3") is False
        assert chain._should_reevaluate("L4") is False


class TestDegradationManager:
    """降级管理器测试"""

    def test_get_next_level(self):
        """测试获取下一级"""
        from src.degradation_chain import DegradationManager
        manager = DegradationManager(TEST_LLM_CONFIG)

        assert manager._get_next_level("L0") == "L1"
        assert manager._get_next_level("L1") == "L2"
        assert manager._get_next_level("L2") == "L3"
        assert manager._get_next_level("L3") == "L4"
        assert manager._get_next_level("L4") is None  # 不能再降

    @pytest.mark.asyncio
    async def test_degrade_to_l4_returns_error(self):
        """测试 L4 时返回错误提示"""
        from src.degradation_chain import DegradationManager
        manager = DegradationManager(TEST_LLM_CONFIG)

        result = await manager.degrade("L4", "话题", "上下文")

        assert result["knowledge_level"] == "L4"
        assert result["can_degrade"] is False
        assert "已达降级上限" in result["alert_message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
