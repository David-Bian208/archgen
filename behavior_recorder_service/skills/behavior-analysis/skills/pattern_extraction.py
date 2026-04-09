"""模式提炼 Skills - 聚类相似行为模式"""

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


class PatternExtractionSkill:
    """模式提炼 Skills：将多个认知行为单元聚类为行为模式"""

    def __init__(self, llm_client=None):
        LLMClient = get_llm_client()
        self.client = llm_client or LLMClient()
        self.system_prompt = """你是一位自闭症儿童行为模式识别专家。
你的任务是将多个认知行为单元聚类为"行为模式"。

核心原则：
1. 寻找重复出现的行为特征
2. 用描述性语言命名模式（非标签化）
3. 关联相关的认知行为单元
4. 关注行为的功能性而非形式

行为模式示例：
- "任务延迟响应"：在接收任务指令时，倾向于用语言延迟而非立即执行
- "成人依赖"：遇到困难时，期待成人介入而非独立尝试
- "感官寻求"：主动寻找特定感官刺激（视觉、听觉、触觉等）
- "社交回避"：在社交情境中表现出回避或退缩行为
- "坚持同一性"：对环境变化或常规改变表现出不适"""

        self.user_prompt_template = """请从以下认知行为单元中提炼行为模式：

## 认知行为单元
{cognitive_units_json}

## 输出格式（JSON）
```json
{{
  "behavior_patterns": [
    {{
      "pattern_id": "BP1",
      "pattern_name": "任务延迟响应",
      "description": "在接收到任务指令时，倾向于用语言延迟而非立即执行",
      "related_units": ["CU1", "CU3"]
    }}
  ]
}}
```"""

    def extract(self, cognitive_units: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        从认知行为单元中提取行为模式

        Args:
            cognitive_units: 认知行为单元列表

        Returns:
            行为模式列表
        """
        units_json = json.dumps(cognitive_units, ensure_ascii=False, indent=2)
        user_prompt = self.user_prompt_template.format(cognitive_units_json=units_json)

        response = self.client.generate_json(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=2000
        )

        return response.get("behavior_patterns", [])


def main():
    """测试"""
    skill = PatternExtractionSkill()

    test_units = [
        {
            "unit_id": "CU1",
            "type": "任务响应",
            "description": "接收到任务指令后，用语言拒绝而非行动执行"
        },
        {
            "unit_id": "CU2",
            "type": "行为持续",
            "description": "拒绝后继续原有活动（玩玩具），未表现出不适"
        },
        {
            "unit_id": "CU3",
            "type": "任务响应",
            "description": "第二次接收到指令时，延迟 5 秒后才开始行动"
        }
    ]

    patterns = skill.extract(test_units)
    print(json.dumps(patterns, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
