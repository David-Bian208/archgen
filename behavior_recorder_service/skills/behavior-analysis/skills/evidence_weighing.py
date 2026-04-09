"""证据权衡 Skills - 支持/反驳证据评估"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 延迟导入，避免循环依赖
import importlib


def get_llm_client():
    """获取 LLMClient"""
    app_llm = importlib.import_module("app.llm")
    return app_llm.OpenAIClient


class EvidenceWeighingSkill:
    """证据权衡 Skills：评估每个假设的强弱证据"""

    def __init__(self, llm_client=None):
        LLMClient = get_llm_client()
        self.client = llm_client or LLMClient()
        self.system_prompt = """你是一位自闭症儿童行为证据分析专家。
你的任务是评估每个假设的支持证据和反驳证据。

核心原则：
1. 寻找支持证据（行为观察中的具体细节）
2. 寻找反驳证据（与假设矛盾的行为）
3. 评估证据权重（强/中/弱）
4. 给出置信度（0-1）
5. 证据必须来自可观察的行为，不是推测

证据权重标准：
- 强：多个独立行为一致支持，无反驳证据
- 中：有部分行为支持，或存在少量反驳证据
- 弱：支持证据不足，或存在明显反驳证据"""

        self.user_prompt_template = """请评估以下假设的证据权重：

## 假设清单
{hypotheses_json}

## ABC 观察记录
{abc_records_json}

## 输出格式（JSON）
```json
{{
  "evidence_evaluation": [
    {{
      "hypothesis_id": "H1",
      "supporting_evidence": [
        "具体的行为观察细节 1",
        "具体的行为观察细节 2"
      ],
      "contradicting_evidence": [],
      "weight": "强",
      "confidence": 0.85
    }}
  ]
}}
```"""

    def weigh(
        self, hypotheses: List[Dict[str, Any]], abc_records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        评估假设的证据权重

        Args:
            hypotheses: 假设列表
            abc_records: ABC 观察记录列表

        Returns:
            证据评估列表
        """
        hypotheses_json = json.dumps(hypotheses, ensure_ascii=False, indent=2)
        abc_records_json = json.dumps(abc_records, ensure_ascii=False, indent=2)

        user_prompt = self.user_prompt_template.format(
            hypotheses_json=hypotheses_json, abc_records_json=abc_records_json
        )

        response = self.client.generate_json(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=2500
        )

        return response.get("evidence_evaluation", [])


def main():
    """测试"""
    skill = EvidenceWeighingSkill()

    test_hypotheses = [
        {
            "hypothesis_id": "H1",
            "related_pattern": "BP1",
            "cognitive_domain": "执行功能 - 抑制控制",
            "description": "难以抑制'继续玩玩具'这一优势反应",
            "neural_system": "前额叶皮层",
            "developmental_stage": "能抑制明显无关干扰，但无法抑制内在优势认知反应"
        }
    ]

    test_records = [
        {
            "antecedent": "妈妈让 OK 收拾玩具",
            "behavior": "OK 说'妈妈收'，然后继续玩",
            "consequence": "妈妈妥协了，帮 OK 收拾"
        }
    ]

    evidence = skill.weigh(test_hypotheses, test_records)
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
