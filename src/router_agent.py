"""Router Agent - 文章分类模块"""

import json
import logging
import re
import time
from typing import Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class ArticleRouter:
    TYPES = {
        "claim": "主张型",
        "causal": "因果型",
        "system": "系统型",
        "comparison": "对比型",
        "process": "流程型",
    }

    CONFIDENCE_THRESHOLD = 0.6

    CLASSIFY_PROMPT = """你是一个文章结构分析专家。请分析以下 Markdown 文章的骨相，判断它属于哪种类型。

文章类型定义：
- 主张型 (claim): 有明确的核心主张，多个分论点支撑，常见于观点文、议论文
- 因果型 (causal): 展示 A→B→C 的因果链条，常见于分析文、推理文
- 系统型 (system): 描述多个模块的相互作用，常见于架构文档、系统说明
- 对比型 (comparison): A vs B 的多维度比较，常见于评测文、选型文
- 流程型 (process): 按步骤 1→2→3→4 展开，常见于教程、操作指南

请只输出 JSON 格式，不要输出其他内容：
{
    "type": "类型（必须是上述5种之一）",
    "confidence": 0.0-1.0（浮点数，表示判断置信度）,
    "reason": "判断理由（50字以内）"
}

文章：
{markdown}
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

    def classify(self, markdown: str) -> Dict:
        """
        分析文章骨相，返回类型

        Returns:
            {
                "type": "claim",
                "confidence": 0.9,
                "reason": "文章包含明确的核心主张和多个分论点支撑"
            }
        """
        logger.info("开始文章分类...")

        # 1. 调用 LLM 分类
        result = self._classify_with_llm(markdown)

        # 2. 如果置信度低于阈值，使用规则兜底
        if result["confidence"] < self.CONFIDENCE_THRESHOLD:
            logger.warning(
                f"LLM 分类置信度 {result['confidence']} 低于阈值 {self.CONFIDENCE_THRESHOLD}，使用规则兜底"
            )
            result = self.classify_by_rules(markdown)

        logger.info(f"文章分类结果: {self.TYPES.get(result['type'], result['type'])}, 置信度: {result['confidence']}")
        return result

    def _classify_with_llm(self, markdown: str) -> Dict:
        """使用 LLM 进行分类"""
        prompt = self.CLASSIFY_PROMPT.replace("{markdown}", markdown[:4000])  # 截断防止超长

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

                # 解析 JSON 输出
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

        # 所有尝试都失败，返回默认结果
        logger.error(f"LLM 分类失败，所有重试都失败: {last_error}")
        return {"type": "claim", "confidence": 0.0, "reason": f"LLM 调用失败: {last_error}"}

    def _parse_json_response(self, content: str) -> Optional[Dict]:
        """解析 LLM 返回的 JSON 内容"""
        # 尝试直接解析
        try:
            result = json.loads(content)
            return self._validate_result(result)
        except json.JSONDecodeError:
            pass

        # 尝试从代码块中提取 JSON
        json_match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                return self._validate_result(result)
            except json.JSONDecodeError:
                pass

        # 尝试从大括号中提取
        brace_match = re.search(r"\{.*\}", content, re.DOTALL)
        if brace_match:
            try:
                result = json.loads(brace_match.group(0))
                return self._validate_result(result)
            except json.JSONDecodeError:
                pass

        return None

    def _validate_result(self, result: Dict) -> Optional[Dict]:
        """验证返回结果格式"""
        if (
            "type" in result
            and "confidence" in result
            and "reason" in result
            and result["type"] in self.TYPES
        ):
            return {
                "type": result["type"],
                "confidence": float(result["confidence"]),
                "reason": result["reason"],
            }
        return None

    def classify_by_rules(self, markdown: str) -> Dict:
        """规则兜底分类"""
        logger.info("使用规则兜底分类...")

        lower_md = markdown.lower()

        # 规则 1: 流程型 - 包含步骤关键词
        process_keywords = ["步骤一", "步骤二", "步骤三", "步骤四", "步骤五",
                           "第一步", "第二步", "第三步", "第四步", "第五步",
                           "step 1", "step 2", "step 3", "step 4", "step 5"]
        process_score = sum(1 for kw in process_keywords if kw in lower_md)

        # 规则 2: 对比型 - 包含对比关键词
        comparison_keywords = ["vs", "对比", "比较", "差异", "区别", "优劣", "优缺点",
                              "versus", "compared to", "vs."]
        comparison_score = sum(1 for kw in comparison_keywords if kw in lower_md)

        # 规则 3: 因果型 - 包含因果关键词
        causal_keywords = ["因为", "所以", "导致", "原因", "结果", "因果",
                          "因此", "从而", "引发", "造成", "due to", "because", "therefore",
                          "导致", "→", "->"]
        causal_score = sum(1 for kw in causal_keywords if kw in lower_md)

        # 规则 4: 主张型 - 包含主张关键词
        claim_keywords = ["我认为", "核心观点", "主张", "论点", "观点是",
                         "in my opinion", "core argument", "核心主张"]
        claim_score = sum(1 for kw in claim_keywords if kw in lower_md)

        # 规则 5: 系统型 - 包含系统关键词
        system_keywords = ["架构", "模块", "系统", "组件", "交互", "依赖",
                          "architecture", "module", "system", "component"]
        system_score = sum(1 for kw in system_keywords if kw in lower_md)

        scores = {
            "process": process_score,
            "comparison": comparison_score,
            "causal": causal_score,
            "claim": claim_score,
            "system": system_score,
        }

        best_type = max(scores, key=scores.get)
        max_score = scores[best_type]

        # 计算置信度
        total_score = sum(scores.values())
        confidence = min(max_score / max(total_score, 1) * 2, 0.9) if max_score > 0 else 0.3

        return {
            "type": best_type,
            "confidence": round(confidence, 2),
            "reason": f"规则匹配: {self.TYPES[best_type]}，关键词命中 {max_score} 次",
        }
