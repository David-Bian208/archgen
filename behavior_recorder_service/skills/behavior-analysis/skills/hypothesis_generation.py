"""多维度假设生成 Skills - 平行列举认知功能解释"""

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


class HypothesisGenerationSkill:
    """多维度假设生成 Skills：针对行为模式平行列举认知功能解释"""

    def __init__(self, llm_client=None):
        LLMClient = get_llm_client()
        self.client = llm_client or LLMClient()
        self.system_prompt = """你是一位自闭症儿童认知功能分析专家。
你的任务是为每个行为模式，平行列举多种认知功能解释（假设）。

核心原则：
1. 平行列举，不急于下结论
2. 每个假设必须与行为模式有逻辑关联
3. 标注关联的神经/发展系统
4. 覆盖多个认知维度（心理理论、执行功能、视觉空间、语言理解）

认知维度框架：
- 心理理论（ToM）：理解他人想法、信念、意图
- 执行功能（EF）：工作记忆、抑制控制、认知灵活性
- 视觉 - 空间认知：空间理解、视角转换、心理旋转
- 语言 - 概念理解：词汇理解、概念抽象、问题解析

输出要求：
- 假设 ID 从 H1 开始连续编号
- 每个假设包含认知领域、描述、神经系统、发展阶段"""

        self.user_prompt_template = """请为以下行为模式生成多维度假设：

## 行为模式
{patterns_json}

## 输出格式（JSON）
```json
{{
  "hypotheses": [
    {{
      "hypothesis_id": "H1",
      "related_pattern": "BP1",
      "cognitive_domain": "执行功能 - 抑制控制",
      "description": "难以抑制'继续玩玩具'这一优势反应，切换到任务执行",
      "neural_system": "前额叶皮层（尤其是下前额叶）",
      "developmental_stage": "能抑制明显无关干扰，但无法抑制内在优势认知反应"
    }}
  ]
}}
```"""

    def generate(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        为行为模式生成多维度假设

        Args:
            patterns: 行为模式列表

        Returns:
            假设列表
        """
        patterns_json = json.dumps(patterns, ensure_ascii=False, indent=2)
        user_prompt = self.user_prompt_template.format(patterns_json=patterns_json)

        response = self.client.generate_json(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=2500
        )

        return response.get("hypotheses", [])


def main():
    """测试"""
    skill = HypothesisGenerationSkill()

    test_patterns = [
        {
            "pattern_id": "BP1",
            "pattern_name": "任务延迟响应",
            "description": "在接收到任务指令时，倾向于用语言延迟而非立即执行",
            "related_units": ["CU1", "CU3"]
        },
        {
            "pattern_id": "BP2",
            "pattern_name": "成人依赖",
            "description": "遇到困难时，期待成人介入而非独立尝试",
            "related_units": ["CU2", "CU4"]
        }
    ]

    hypotheses = skill.generate(test_patterns)
    print(json.dumps(hypotheses, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
