"""Content Classifier - 内容分类器模块"""

import json
import logging
import re
import time
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class ContentClassifier:
    """内容分类器，基于语义理解的业务领域分类"""

    # AI Pulse 内容分类（5 个固定分类）
    CATEGORIES = {
        "ai-models": {
            "name": "模型",
            "description": "大模型发布、更新、评测等",
            "keywords": ["模型发布", "模型更新", "大模型", "LLM", "基础模型", "预训练", "微调",
                        "模型评测", "基准测试", "性能评测", "参数", "上下文窗口", "推理速度"],
        },
        "ai-products": {
            "name": "产品",
            "description": "AI 产品/工具/平台发布或更新",
            "keywords": ["产品发布", "产品更新", "AI 工具", "AI 平台", "SaaS", "应用",
                        "工具链", "IDE", "编程助手", "Copilot", "自动化", "工作流",
                        "AI Agent", "智能体", "多模态"],
        },
        "industry": {
            "name": "行业",
            "description": "行业新闻、政策、融资、合作等",
            "keywords": ["行业动态", "新闻", "政策", "融资", "投资", "合作", "收购",
                        "监管", "合规", "趋势", "市场分析", "商业模式", "竞争",
                        "生态", "开源", "社区", "标准"],
        },
        "paper": {
            "name": "论文",
            "description": "学术论文、研究报告、技术突破等",
            "keywords": ["论文", "研究", "学术", "arXiv", "会议", "CVPR", "NeurIPS", "ICML",
                        "技术突破", "新架构", "算法", "方法论", "实验", "数据集",
                        "MoE", "RAG", "CoT", "RLHF"],
        },
        "tip": {
            "name": "技巧",
            "description": "教程、技巧、观点、经验分析等",
            "keywords": ["教程", "技巧", "指南", "实践", "经验", "观点", "分析",
                        "最佳实践", "踩坑", "部署", "优化", "提示词", "Prompt",
                        "落地", "应用案例", "使用技巧"],
        },
    }

    CONFIDENCE_THRESHOLD = 0.7

    CLASSIFY_PROMPT = """你是一个 AI 行业分类专家。请分析以下文本，判断它属于哪个内容类型。

内容类型定义：
- ai-models: 模型（大模型发布、更新、评测等）
- ai-products: 产品（AI 产品/工具/平台发布或更新）
- industry: 行业（行业新闻、政策、融资、合作等）
- paper: 论文（学术论文、研究报告、技术突破等）
- tip: 技巧（教程、技巧、观点、经验分析等）

请输出 JSON 格式：
{{
    "primary": "主要分类（必须是上述 5 个之一）",
    "confidence": 0.0-1.0（浮点数，判断置信度）,
    "alternatives": ["备选分类 1", "备选分类 2"],
    "reason": "判断理由（50 字以内）"
}}

文本：
{text}
"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.api_key = self.config.get("api_key", "")
        self.base_url = self.config.get("base_url", "https://api.deepseek.com/v1")
        self.model = self.config.get("model", "deepseek-chat")
        self.max_tokens = self.config.get("max_tokens", 1024)
        self.temperature = self.config.get("temperature", 0.1)
        self.timeout = self.config.get("timeout", 30)
        self.retry_times = self.config.get("retry_times", 3)
        self.retry_delay = self.config.get("retry_delay", 2)

    def classify_by_intent(self, text: str) -> Dict:
        """
        语义理解分类

        Returns:
            {
                "primary": "business",
                "confidence": 0.85,
                "alternatives": ["product", "operations"],
                "reason": "文本涉及商业模式和市场竞争分析"
            }
        """
        logger.info("开始语义分类...")

        # 1. 调用 LLM 分类
        result = self._classify_with_llm(text)

        # 2. 如果置信度低于阈值，补充规则分类结果
        if result["confidence"] < self.CONFIDENCE_THRESHOLD:
            rule_result = self._classify_by_rules(text)
            # 融合 LLM 和规则结果
            result["alternatives"] = list(set(
                result.get("alternatives", []) + [rule_result["primary"]]
            ))
            result["alternatives"] = [a for a in result["alternatives"] if a != result["primary"]]
            result["rule_suggestion"] = rule_result["primary"]

        logger.info(f"分类结果: {result['primary']}, 置信度: {result['confidence']}")
        return result

    def get_categories(self) -> Dict:
        """获取所有分类定义"""
        return self.CATEGORIES

    def get_category_info(self, key: str) -> Optional[Dict]:
        """获取单个分类信息"""
        cat = self.CATEGORIES.get(key)
        if cat:
            return {"key": key, **cat}
        return None

    def _classify_with_llm(self, text: str) -> Dict:
        """使用 LLM 进行分类"""
        prompt = self.CLASSIFY_PROMPT.replace("{text}", text[:3000])

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        last_error = None
        for attempt in range(1, self.retry_times + 1):
            try:
                logger.debug(f"LLM 分类请求 (尝试 {attempt}/{self.retry_times})...")
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                    content = data["choices"][0]["message"]["content"].strip()

                result = self._parse_json_response(content)
                if result:
                    return result

            except httpx.HTTPError as e:
                last_error = f"HTTP 错误: {str(e)}"
                logger.warning(f"LLM 请求失败 (尝试 {attempt}/{self.retry_times}): {last_error}")
            except json.JSONDecodeError as e:
                last_error = f"JSON 解析失败: {str(e)}"
                logger.warning(f"LLM 返回格式错误: {last_error}")
            except Exception as e:
                last_error = f"未知错误: {str(e)}"
                logger.warning(f"LLM 请求异常: {last_error}")

            if attempt < self.retry_times:
                time.sleep(self.retry_delay * attempt)

        logger.error(f"LLM 分类失败: {last_error}")
        return {
            "primary": "business",
            "confidence": 0.0,
            "alternatives": list(self.CATEGORIES.keys()),
            "reason": f"LLM 调用失败: {last_error}",
        }

    def _classify_by_rules(self, text: str) -> Dict:
        """规则分类兜底"""
        lower_text = text.lower()
        scores = {}

        for key, cat in self.CATEGORIES.items():
            score = sum(1 for kw in cat["keywords"] if kw.lower() in lower_text)
            scores[key] = score

        primary = max(scores, key=scores.get)
        max_score = scores[primary]
        total_score = sum(scores.values())
        confidence = min(max_score / max(total_score, 1) * 2, 0.8) if max_score > 0 else 0.3

        # 获取备选
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        alternatives = [s[0] for s in sorted_scores[1:3] if s[1] > 0]

        return {
            "primary": primary,
            "confidence": round(confidence, 2),
            "alternatives": alternatives,
            "reason": f"规则匹配: {self.CATEGORIES[primary]['name']}，关键词命中 {max_score} 次",
        }

    def _parse_json_response(self, content: str) -> Optional[Dict]:
        """解析 LLM 返回的 JSON（增强容错）"""
        # 清理可能的非标准字符
        content = content.replace("'", '"').replace('`', '')
        
        # 方法 1: 直接解析
        try:
            result = json.loads(content)
            validated = self._validate_result(result)
            if validated:
                return validated
        except json.JSONDecodeError:
            pass

        # 方法 2: 查找代码块中的 JSON
        json_match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                validated = self._validate_result(result)
                if validated:
                    return validated
            except json.JSONDecodeError:
                pass

        # 方法 3: 查找最外层花括号
        brace_match = re.search(r"\{.*\}", content, re.DOTALL)
        if brace_match:
            try:
                result = json.loads(brace_match.group(0))
                validated = self._validate_result(result)
                if validated:
                    return validated
            except json.JSONDecodeError:
                pass

        # 方法 4: 提取关键字段（最后的兜底）
        primary_match = re.search(r'"primary"\s*:\s*"(\w+)"', content)
        confidence_match = re.search(r'"confidence"\s*:\s*([0-9.]+)', content)
        reason_match = re.search(r'"reason"\s*:\s*"([^"]+)"', content)
        
        if primary_match:
            primary = primary_match.group(1)
            confidence = float(confidence_match.group(1)) if confidence_match else 0.5
            reason = reason_match.group(1) if reason_match else ""
            
            if primary in self.CATEGORIES:
                return {
                    "primary": primary,
                    "confidence": confidence,
                    "alternatives": [],
                    "reason": reason or f"从非标准 JSON 提取: {primary}",
                }

        return None

    def _validate_result(self, result: Dict) -> Optional[Dict]:
        """验证结果格式"""
        if (
            "primary" in result
            and "confidence" in result
            and result["primary"] in self.CATEGORIES
        ):
            return {
                "primary": result["primary"],
                "confidence": float(result["confidence"]),
                "alternatives": result.get("alternatives", []),
                "reason": result.get("reason", ""),
            }
        return None
