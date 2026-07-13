"""Extractor Agent - 结构提取模块"""

import json
import logging
import re
import time
from typing import Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class StructureExtractor:
    # 每种类型的提取 Prompt 模板
    EXTRACT_PROMPTS = {
        "claim": """你是结构化信息提取专家。请从以下 Markdown 文章中提取主张型结构。

请提取以下内容并输出 JSON：
{
    "title": "文章标题",
    "central_claim": "核心主张（一句话概括）",
    "supporting_points": [
        {"label": "分论点1标题", "text": "分论点内容", "weight": 0.8}
    ],
    "evidence": ["证据1", "证据2"],
    "conclusion": "结论"
}

weight 是重要性权重 (0.0-1.0)，核心分论点给 0.8-1.0，次要分论点给 0.5-0.7。

只输出 JSON，不要输出其他内容。

文章：
{markdown}
""",

        "causal": """你是结构化信息提取专家。请从以下 Markdown 文章中提取因果型结构。

请提取以下内容并输出 JSON：
{
    "title": "文章标题",
    "chain": [
        {"step": 1, "cause": "原因A", "effect": "结果B"}
    ],
    "root_cause": "根本原因",
    "final_effect": "最终结果"
}

chain 按因果顺序排列，每个 step 包含 cause 和 effect。

只输出 JSON，不要输出其他内容。

文章：
{markdown}
""",

        "system": """你是结构化信息提取专家。请从以下 Markdown 文章中提取系统型结构。

请提取以下内容并输出 JSON：
{
    "title": "文章标题",
    "overview": "系统概述（一句话）",
    "modules": [
        {"name": "模块名", "role": "模块职责", "connections": ["连接的模块1", "连接的模块2"]}
    ]
}

只输出 JSON，不要输出其他内容。

文章：
{markdown}
""",

        "comparison": """你是结构化信息提取专家。请从以下 Markdown 文章中提取对比型结构。

请提取以下内容并输出 JSON：
{
    "title": "文章标题",
    "dimensions": ["维度1", "维度2", "维度3"],
    "items": [
        {"name": "对比项A", "scores": ["维度1评价", "维度2评价", "维度3评价"]},
        {"name": "对比项B", "scores": ["维度1评价", "维度2评价", "维度3评价"]}
    ]
}

dimensions 是对比的维度，items 是对比的项，scores 对应每个维度的评价。

只输出 JSON，不要输出其他内容。

文章：
{markdown}
""",

        "process": """你是结构化信息提取专家。请从以下 Markdown 文章中提取流程型结构。

请提取以下内容并输出 JSON：
{
    "title": "文章标题",
    "steps": [
        {"order": 1, "title": "步骤标题", "description": "步骤描述", "tips": ["提示1", "提示2"]}
    ]
}

steps 按执行顺序排列，order 从 1 开始。tips 是可选的提示列表。

只输出 JSON，不要输出其他内容。

文章：
{markdown}
""",

        "swot": """你是结构化信息提取专家。请从以下文本中提取 SWOT 分析数据。

请提取以下内容并输出 JSON：
{
    "title": "分析标题",
    "strengths": ["优势1", "优势2", "优势3"],
    "weaknesses": ["劣势1", "劣势2", "劣势3"],
    "opportunities": ["机会1", "机会2", "机会3"],
    "threats": ["威胁1", "威胁2", "威胁3"],
    "summary": "总结建议"
}

每个象限至少提取 2-3 个条目。

只输出 JSON，不要输出其他内容。

文本：
{markdown}
""",

        "business_canvas": """你是结构化信息提取专家。请从以下文本中提取商业模式画布数据。

请提取以下内容并输出 JSON：
{
    "title": "分析标题",
    "customer_segments": ["客户细分1", "客户细分2"],
    "value_propositions": ["价值主张1", "价值主张2"],
    "channels": ["渠道1", "渠道2"],
    "customer_relationships": ["客户关系1", "客户关系2"],
    "revenue_streams": ["收入来源1", "收入来源2"],
    "key_resources": ["核心资源1", "核心资源2"],
    "key_activities": ["关键业务1", "关键业务2"],
    "key_partnerships": ["合作伙伴1", "合作伙伴2"],
    "cost_structure": ["成本结构1", "成本结构2"]
}

只输出 JSON，不要输出其他内容。

文本：
{markdown}
""",

        "pestel": """你是结构化信息提取专家。请从以下文本中提取 PESTEL 分析数据。

请提取以下内容并输出 JSON：
{
    "title": "分析标题",
    "political": ["政治因素1", "政治因素2"],
    "economic": ["经济因素1", "经济因素2"],
    "social": ["社会因素1", "社会因素2"],
    "technological": ["技术因素1", "技术因素2"],
    "environmental": ["环境因素1", "环境因素2"],
    "legal": ["法律因素1", "法律因素2"],
    "summary": "总结建议"
}

每个维度至少提取 1-2 个条目。

只输出 JSON，不要输出其他内容。

文本：
{markdown}
""",

        "user_journey": """你是结构化信息提取专家。请从以下文本中提取用户旅程数据。

请提取以下内容并输出 JSON：
{
    "title": "分析标题",
    "persona": "用户角色描述",
    "stages": [
        {"order": 1, "name": "阶段名", "description": "阶段描述", "touchpoints": ["触点1", "触点2"], "pain_points": ["痛点1", "痛点2"], "emotion": 3}
    ],
    "summary": "总结建议"
}

emotion 是情绪评分 (1-5)，stages 按时间顺序排列，至少 4-5 个阶段。

只输出 JSON，不要输出其他内容。

文本：
{markdown}
""",

        "time_matrix": """你是结构化信息提取专家。请从以下文本中提取时间管理矩阵数据。

请提取以下内容并输出 JSON：
{
    "title": "分析标题",
    "q1_important_urgent": [{"name": "任务名", "description": "描述"}],
    "q2_important_not_urgent": [{"name": "任务名", "description": "描述"}],
    "q3_not_important_urgent": [{"name": "任务名", "description": "描述"}],
    "q4_not_important_not_urgent": [{"name": "任务名", "description": "描述"}],
    "summary": "总结建议"
}

Q1: 重要且紧急（立即做）
Q2: 重要不紧急（计划做）
Q3: 不重要但紧急（委派做）
Q4: 不重要不紧急（减少做）

每个象限至少提取 1-2 个任务。

只输出 JSON，不要输出其他内容。

文本：
{markdown}
""",
    }

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.api_key = self.config.get("api_key", "")
        self.base_url = self.config.get("base_url", "https://api.deepseek.com/v1")
        self.model = self.config.get("model", "deepseek-v4-flash")
        self.max_tokens = self.config.get("max_tokens", 2048)
        self.temperature = self.config.get("temperature", 0.1)
        self.timeout = self.config.get("timeout", 60)
        self.retry_times = self.config.get("retry_times", 3)
        self.retry_delay = self.config.get("retry_delay", 2)

    # 框架中文名/别名 → key 映射（前端可能传名称而非 key）
    FRAMEWORK_NAME_MAP = {
        # 通用映射
        "主张型": "claim", "claim": "claim", "主张": "claim",
        "因果型": "causal", "causal": "causal", "因果": "causal",
        "系统型": "system", "system": "system", "系统": "system",
        "对比型": "comparison", "comparison": "comparison", "对比": "comparison",
        "流程型": "process", "process": "process", "流程": "process",
        "swot": "swot", "SWOT": "swot", "SWOT分析": "swot",
        "商业模式画布": "business_canvas", "business_canvas": "business_canvas", "画布": "business_canvas",
        "PESTEL": "pestel", "pestel": "pestel",
        "用户旅程": "user_journey", "user_journey": "user_journey", "旅程": "user_journey",
        "时间矩阵": "time_matrix", "time_matrix": "time_matrix", "四象限": "time_matrix",
        # 常见五步法/多步法 → process
        "五步法": "process", "六步法": "process", "四步法": "process", "三步法": "process",
        "步骤": "process", "流程步骤": "process",
    }

    def resolve_framework_key(self, framework_key: str) -> str:
        """将框架中文名/别名解析为标准 key"""
        resolved = self.FRAMEWORK_NAME_MAP.get(framework_key, "")
        if not resolved:
            for name, key in self.FRAMEWORK_NAME_MAP.items():
                if name in framework_key or framework_key in name:
                    resolved = key
                    break
        if not resolved:
            resolved = framework_key
        # 确保返回的 key 在 EXTRACT_PROMPTS 中，否则降级为 process
        if resolved not in self.EXTRACT_PROMPTS:
            logger.warning(f"未知框架 '{framework_key}'，降级为 process（流程型）")
            resolved = "process"
        return resolved

    def extract(self, text: str, framework_key: str, user_data: Optional[Dict] = None) -> Dict:
        """根据框架类型调用对应模板，提取结构化数据

        Args:
            text: 原文内容（MCP 总结或用户输入）
            framework_key: 框架 key（支持中文名，会自动映射）
            user_data: 用户已填写的数据（可选），如果提供则作为提取参考
        """
        resolved_key = self.resolve_framework_key(framework_key)
        logger.info(f"开始提取 {resolved_key} 框架数据 (原始输入: {framework_key})...")
        prompt_template = self.EXTRACT_PROMPTS[resolved_key]

        # 如果有用户数据，优先基于用户数据构建结构化输出，LLM 只做整理/补全
        if user_data:
            prompt = f"""你是一个结构化数据整理专家。请根据以下信息输出最终的 JSON 数据。

## 用户已填写的数据（优先使用这些值，不要篡改）：
{json.dumps(user_data, ensure_ascii=False, indent=2)}

## 参考资料（仅用于补全缺失字段，不要改变用户已填写的内容）：
{text[:4000]}

## 输出格式要求：
{prompt_template}

只输出 JSON，不要输出其他内容。
"""
        else:
            prompt = prompt_template.replace("{markdown}", text[:4000])

        result = self._call_llm(prompt)

        if result:
            result["metadata"] = {
                "framework_key": framework_key,
                "source_length": len(text),
                "tolerance_mode": True,
            }
            result["layout_hints"] = self._get_layout_hints(framework_key)
            return result

        raise ValueError(f"结构化提取失败，框架: {framework_key}")

    def extract_with_prompt(self, text: str, custom_prompt: str) -> Dict:
        """使用自定义 Prompt 提取结构化数据"""
        logger.info("使用自定义 Prompt 提取数据...")
        prompt = custom_prompt.replace("{text}", text[:4000])
        result = self._call_llm(prompt)

        if result:
            result["metadata"] = {
                "custom_prompt": True,
                "source_length": len(text),
            }
            return result

        raise ValueError("自定义 Prompt 提取失败")

    def _call_llm(self, prompt: str) -> Optional[Dict]:
        """调用 LLM 进行结构化提取"""
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
                logger.debug(f"提取请求 (尝试 {attempt}/{self.retry_times})...")
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
                logger.warning(f"请求失败 (尝试 {attempt}/{self.retry_times}): {last_error}")
            except json.JSONDecodeError as e:
                last_error = f"JSON 解析失败: {str(e)}"
                logger.warning(f"返回格式错误: {last_error}")
            except Exception as e:
                last_error = f"未知错误: {str(e)}"
                logger.warning(f"请求异常: {last_error}")

            if attempt < self.retry_times:
                time.sleep(self.retry_delay * attempt)

        logger.error(f"提取失败，所有重试都失败: {last_error}")
        return None

    def _parse_json_response(self, content: str) -> Optional[Dict]:
        """解析 LLM 返回的 JSON 内容"""
        # 尝试直接解析
        try:
            result = json.loads(content)
            return result
        except json.JSONDecodeError:
            pass

        # 尝试从代码块中提取 JSON
        json_match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                return result
            except json.JSONDecodeError:
                pass

        # 尝试从大括号中提取
        brace_match = re.search(r"\{.*\}", content, re.DOTALL)
        if brace_match:
            try:
                result = json.loads(brace_match.group(0))
                return result
            except json.JSONDecodeError:
                pass

        return None

    def _get_layout_hints(self, framework_key: str) -> Dict:
        """获取布局提示"""
        hints = {
            "claim": {"layout": "center", "central_emphasis": True, "grid_columns": 2},
            "causal": {"layout": "vertical", "show_arrows": True, "chain_direction": "top-to-bottom"},
            "system": {"layout": "grid", "grid_columns": 3, "show_connections": True},
            "comparison": {"layout": "table", "highlight_best": True},
            "process": {"layout": "vertical", "show_timeline": True, "step_number_style": "circle"},
            "swot": {"layout": "2x2_grid", "show_quadrants": True},
            "business_canvas": {"layout": "9_grid", "show_grid_lines": True},
            "pestel": {"layout": "6_columns", "show_headers": True},
            "user_journey": {"layout": "horizontal_timeline", "show_emotions": True},
            "time_matrix": {"layout": "2x2_grid", "show_quadrants": True},
        }
        return hints.get(framework_key, {})
