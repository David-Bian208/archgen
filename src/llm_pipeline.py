"""
LLM Pipeline 模块

功能：
- Router：方向推荐（注入能力边界 Edge）
- Logic Editor：框架推荐（注入 Why+Filter+Value）
- Extractor：内容萃取（注入 Who+Value）
- Generator：内容生成（注入 Voice+Who）

当前阶段：单体 LLM 调用，通过 stage 参数区分不同 prompt
（P2 目标拆分为 4 个独立 LLM 调用，当前未实施）
"""

import logging
from typing import Dict, Optional, List, Any

logger = logging.getLogger(__name__)


class LLMPipeline:
    """LLM Pipeline 管理器"""

    def __init__(self, llm_config: Dict):
        self.llm_config = llm_config
        self.call_count = 0

    async def call_router(
        self,
        article_text: str,
        direction_list: List[Dict],
        edge_focus: str = "",
        edge_avoid: str = "",
    ) -> Dict:
        """
        LLM1: Router - 方向推荐
        注入维度：能力边界 (Edge)
        """
        prompt = self._build_router_prompt(
            article_text, direction_list, edge_focus, edge_avoid
        )
        result = await self._call_llm(prompt, max_tokens=512, temperature=0.2)
        self.call_count += 1
        logger.info(f"[Router] LLM 调用完成 (#{self.call_count})")
        return result

    async def call_logic_editor(
        self,
        outline: str,
        drive: str = "",
        filter_rule: str = "",
        value_standard: str = "",
    ) -> Dict:
        """
        LLM2: Logic Editor - 框架推荐
        注入维度：核心驱动 (Why) + 认知过滤 (Filter) + 价值标准 (Value)
        """
        prompt = self._build_logic_editor_prompt(outline, drive, filter_rule, value_standard)
        result = await self._call_llm(prompt, max_tokens=2048, temperature=0.2)
        self.call_count += 1
        logger.info(f"[LogicEditor] LLM 调用完成 (#{self.call_count})")
        return result

    async def call_extractor(
        self,
        revised_outline: str,
        audience_identity: str = "",
        audience_pain_points: str = "",
        audience_empathy: str = "",
        value_standard: str = "",
    ) -> Dict:
        """
        LLM3: Extractor - 内容萃取
        注入维度：受众画像 (Who) + 价值标准 (Value)
        """
        prompt = self._build_extractor_prompt(
            revised_outline,
            audience_identity,
            audience_pain_points,
            audience_empathy,
            value_standard,
        )
        result = await self._call_llm(prompt, max_tokens=4096, temperature=0.2)
        self.call_count += 1
        logger.info(f"[Extractor] LLM 调用完成 (#{self.call_count})")
        return result

    async def call_generator(
        self,
        structured_json: str,
        voice_style: str = "",
        voice_format: str = "",
        voice_ratio: str = "",
        audience_identity: str = "",
        audience_pain_points: str = "",
    ) -> Dict:
        """
        LLM4: Generator - 内容生成
        注入维度：表达范式 (Voice) + 受众画像 (Who)
        """
        prompt = self._build_generator_prompt(
            structured_json,
            voice_style,
            voice_format,
            voice_ratio,
            audience_identity,
            audience_pain_points,
        )
        result = await self._call_llm(prompt, max_tokens=8192, temperature=0.3)
        self.call_count += 1
        logger.info(f"[Generator] LLM 调用完成 (#{self.call_count})")
        return result

    def _build_router_prompt(
        self,
        article_text: str,
        direction_list: List[Dict],
        edge_focus: str,
        edge_avoid: str,
    ) -> str:
        """构建 Router prompt"""
        direction_str = "\n".join([f"- {d.get('name', '')}" for d in direction_list])

        return f"""你是一位内容策划专家，专注{edge_focus}领域。

【能力边界】
专注：{edge_focus}
回避：{edge_avoid}

【待分析主题】
{article_text[:3000]}

【候选方向列表】
{direction_str}

请从以上方向中，选出最适合的 5 个，按适合程度排序，并给出评分和简短理由。

评分标准：
- 0.8-1.0: 强烈推荐（资料非常充足，完全适合该方向）
- 0.6-0.8: 推荐（资料较充足，基本适合该方向）
- 0.4-0.6: 可以考虑（资料一般，需要补充一些内容）
- 0.2-0.4: 不太适合（资料较少，勉强可以写）

返回 JSON 格式（不要 markdown 代码块）：
[{{"name": "方向名", "score": 0.85, "reason": "因为资料中...", "confidence_label": "强烈推荐|推荐|可以考虑|不太适合"}}]
"""

    def _build_logic_editor_prompt(
        self,
        outline: str,
        drive: str,
        filter_rule: str,
        value_standard: str,
    ) -> str:
        """构建 Logic Editor prompt"""
        return f"""你是一位内容逻辑编辑专家。

【核心驱动】
{drive}

【认知过滤】
{filter_rule}

【价值标准】
{value_standard}

【待检查提纲】
{outline}

请检查以上提纲：
1. 是否偏离核心驱动？
2. 是否包含纯理论内容（应删除或精简）？
3. 是否缺少避坑指南、实操步骤？
4. 是否符合"读者看完能直接上手操作"的金标准？

返回修改后的提纲和变更日志：
{{
  "revised_outline": "修改后的提纲",
  "change_log": ["删除了纯理论部分X", "增加了避坑指南Y", ...]
}}
"""

    def _build_extractor_prompt(
        self,
        revised_outline: str,
        audience_identity: str,
        audience_pain_points: str,
        audience_empathy: str,
        value_standard: str,
    ) -> str:
        """构建 Extractor prompt"""
        return f"""你是一位内容萃取专家。

【受众画像】
身份：{audience_identity}
痛点：{audience_pain_points}
共情话术：{audience_empathy}

【价值标准】
{value_standard}

【待萃取内容】
{revised_outline}

请针对上述受众的痛点，提取可操作步骤：
1. 每个观点必须附带"下一步行动"
2. 使用受众能理解的语言
3. 突出实操价值，避免理论推导

返回结构化 JSON：
{{
  "sections": [
    {{
      "title": "段落标题",
      "core_point": "核心观点",
      "action_steps": ["步骤 1", "步骤 2", ...],
      "pitfalls": ["避坑 1", "避坑 2", ...],
      "expected_outcome": "预期收益"
    }}
  ]
}}
"""

    def _build_generator_prompt(
        self,
        structured_json: str,
        voice_style: str,
        voice_format: str,
        voice_ratio: str,
        audience_identity: str,
        audience_pain_points: str,
    ) -> str:
        """构建 Generator prompt"""
        return f"""你是一位专业内容创作者。

【表达范式】
风格：{voice_style}
格式：{voice_format}
比例：{voice_ratio}

【受众画像】
身份：{audience_identity}
痛点：{audience_pain_points}

【内容结构】
{structured_json}

【内容比例要求】
- 理论内容≤20%，实战内容≥80%
- 理论：概念解释、背景介绍、原理说明（简短精炼）
- 实战：操作步骤、具体案例、避坑指南、收益测算、工具推荐

【素材来源标注要求】（P2 硬约束阶段）
- 如果内容基于参考资料，在段落末尾标注 [来源：xxx]
- 如果内容基于逻辑推演/行业知识，在段落开头标注 ⚠️ [AI 推断]
- 如果案例/素材不足，使用占位符格式：[📌 待补充案例：xxx 类型的实际案例]
- 注意：无 source_tag 的内容将被过滤，不会渲染给用户

要求：
1. 使用{voice_style}风格
2. 遵循{voice_format}格式要求
3. 理论≤20%，实战≥80%
4. 每个案例/观点附带具体操作步骤
5. 语言直接了当，避免冗长铺垫
6. 使用 Markdown 格式
7. 直接输出内容，不要多余话语
8. 每个段落必须有明确的 source_tag 标记

请生成完整内容：
"""

    async def _call_llm(
        self, prompt: str, max_tokens: int = 2048, temperature: float = 0.3
    ) -> Dict:
        """调用 LLM"""
        import httpx

        base_url = self.llm_config.get("base_url", "https://api.deepseek.com/v1")
        api_key = self.llm_config.get("api_key", "")
        model = self.llm_config.get("model", "deepseek-v4-flash")
        timeout = self.llm_config.get("timeout", 60)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "seed": 42,
                },
            )
            response.raise_for_status()
            result = response.json()

        content = result["choices"][0]["message"]["content"].strip()
        return {"content": content, "usage": result.get("usage", {})}


def get_llm_pipeline(llm_config: Dict) -> LLMPipeline:
    """获取 LLM Pipeline 实例"""
    return LLMPipeline(llm_config)
