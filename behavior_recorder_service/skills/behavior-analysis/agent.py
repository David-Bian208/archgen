#!/usr/bin/env python3
"""行为分析 Agent - 专家思维版"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 本地导入
from skills.behavior_decoding import BehaviorDecodingSkill
from skills.pattern_extraction import PatternExtractionSkill
from skills.hypothesis_generation import HypothesisGenerationSkill
from skills.evidence_weighing import EvidenceWeighingSkill

# 延迟导入 LLM
import importlib


def get_llm_client():
    """获取 LLMClient"""
    app_llm = importlib.import_module("app.llm")
    return app_llm.OpenAIClient


class BehaviorAnalysisAgent:
    """行为分析 Agent：整合 Skills 输出，进行阶段定位和整合归因"""

    def __init__(self):
        LLMClient = get_llm_client()
        self.client = LLMClient()
        self.decoding_skill = BehaviorDecodingSkill(self.client)
        self.pattern_skill = PatternExtractionSkill(self.client)
        self.hypothesis_skill = HypothesisGenerationSkill(self.client)
        self.evidence_skill = EvidenceWeighingSkill(self.client)

    def analyze(self, abc_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        执行行为分析

        Args:
            abc_records: ABC 观察记录列表

        Returns:
            分析结果
        """
        try:
            # Step 1: 行为解码（Skills 1）
            cognitive_units = []
            for record in abc_records:
                units = self.decoding_skill.decode(record)
                cognitive_units.extend(units)

            # Step 2: 模式提炼（Skills 2）
            patterns = self.pattern_skill.extract(cognitive_units)

            # Step 3: 多维度假设生成（Skills 3）
            hypotheses = self.hypothesis_skill.generate(patterns)

            # Step 4: 证据权衡（Skills 4）
            evidence_eval = self.evidence_skill.weigh(hypotheses, abc_records)

            # Step 5: Agent 整合（阶段定位 + 整合归因）
            result = self._integrate(
                patterns=patterns,
                hypotheses=hypotheses,
                evidence=evidence_eval,
                abc_records=abc_records,
            )

            return result

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _integrate(
        self, patterns, hypotheses, evidence, abc_records
    ) -> Dict[str, Any]:
        """整合 Skills 输出，生成最终分析结果"""

        # 构建整合提示词
        integration_prompt = self._build_integration_prompt(
            patterns, hypotheses, evidence, abc_records
        )

        # 调用 LLM 进行整合
        response = self.client.generate_json(
            system_prompt="""你是一位资深自闭症儿童发展评估专家。
请基于行为分析 Skills 的输出，进行发展阶段定位和整合归因。

核心原则：
1. 阶段思维 - 用发展程度衡量，不是"有或无"
2. 系统观 - 关注不同认知功能如何相互作用
3. 证据驱动 - 每个判断链接回可观察的行为证据
4. 发展性语言 - "正处在...过渡的关键期"

输出结构化的发展剖面和归因陈述。""",
            user_prompt=integration_prompt,
            temperature=0.1,
            max_tokens=2000,
        )

        return {"success": True, **response}

    def _build_integration_prompt(
        self, patterns, hypotheses, evidence, abc_records
    ) -> str:
        """构建整合提示词"""
        return f"""
## ABC 观察记录
{json.dumps(abc_records, ensure_ascii=False, indent=2)}

## 行为模式
{json.dumps(patterns, ensure_ascii=False, indent=2)}

## 假设清单
{json.dumps(hypotheses, ensure_ascii=False, indent=2)}

## 证据评估
{json.dumps(evidence, ensure_ascii=False, indent=2)}

## 整合任务

### 1. 发展阶段定位
为每个认知维度定位发展阶段：
- 心理理论：处于什么阶段？
- 执行功能（抑制/转换/更新）：各处于什么阶段？
- 视觉空间认知：处于什么阶段？
- 语言与概念理解：处于什么阶段？

### 2. 能力发展剖面
- 强项：哪些能力发展良好？
- 当前发展焦点：哪些能力正在发展中？
- 潜在挑战：哪些能力可能需要关注？

### 3. 整合归因陈述
生成一份结构化的诊断性描述（200-300 字），包含：
- 核心挑战的定位
- 多认知环节的协同运作关系
- 发展性语言描述

### 输出格式（JSON）
```json
{{
  "developmental_profile": {{
    "strengths": ["强项 1", "强项 2"],
    "current_focus": ["焦点 1", "焦点 2"],
    "potential_challenges": ["挑战 1"]
  }},
  "attribution_statement": "整合归因陈述（200-300 字）",
  "hypotheses_ranking": [
    {{"id": "H1", "rank": 1, "confidence": 0.85}}
  ]
}}
```
"""


def main():
    """测试"""
    agent = BehaviorAnalysisAgent()

    # 测试用例 1：薯片盒子游戏（二级错误信念）
    test_records = [
        {
            "antecedent": "妈妈和 OK 玩薯片盒子游戏，OK 看到妈妈把糖果换成薯片",
            "behavior": "OK 能说出盒子里是薯片，但当被问'爸爸会看到什么'时，OK 说'糖'",
            "consequence": "妈妈继续引导，但 OK 不太理解为什么爸爸会说是糖",
        }
    ]

    result = agent.analyze(test_records)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
