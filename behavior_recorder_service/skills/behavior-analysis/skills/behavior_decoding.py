"""行为解码 Skills - 从 ABC 描述中提取认知行为单元"""

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


class BehaviorDecodingSkill:
    """行为解码 Skills：从 ABC 描述中提取认知行为单元"""

    def __init__(self, llm_client=None):
        LLMClient = get_llm_client()
        self.client = llm_client or LLMClient()
        self.system_prompt = """你是一位自闭症儿童行为分析专家。
你的任务是从 ABC（前因 - 行为 - 结果）描述中提取"认知行为单元"。

核心原则：
1. 剥离情境细节，关注"做了什么"
2. 用中性语言描述，不带价值判断
3. 每个单元聚焦一个认知操作
4. 不遗漏任何行为细节

认知行为单元类型参考：
- 任务响应：接收指令后的行为反应
- 社交互动：与他人互动的行为
- 情绪表达：情绪状态的外在表现
- 行为持续：继续或停止某行为
- 注意力转移：从一个对象/活动转向另一个
- 语言使用：用语言表达需求/拒绝等
- 感官行为：与感官刺激相关的行为"""

        self.user_prompt_template = """请从以下 ABC 描述中提取认知行为单元：

## ABC 描述
前因（Antecedent）：{antecedent}
行为（Behavior）：{behavior}
结果（Consequence）：{consequence}

## 输出格式（JSON）
```json
{{
  "cognitive_units": [
    {{
      "unit_id": "CU1",
      "type": "任务响应",
      "description": "具体描述做了什么，聚焦认知操作"
    }}
  ]
}}
```"""

    def decode(self, abc_record: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        解码单个 ABC 记录

        Args:
            abc_record: 包含 antecedent, behavior, consequence 的字典

        Returns:
            认知行为单元列表
        """
        user_prompt = self.user_prompt_template.format(**abc_record)

        response = self.client.generate_json(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=1500
        )

        return response.get("cognitive_units", [])

    def decode_batch(self, abc_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量解码多个 ABC 记录

        Args:
            abc_records: ABC 记录列表

        Returns:
            所有认知行为单元（带记录索引）
        """
        all_units = []
        for idx, record in enumerate(abc_records):
            units = self.decode(record)
            for unit in units:
                unit["record_index"] = idx
            all_units.extend(units)
        return all_units


def main():
    """测试"""
    skill = BehaviorDecodingSkill()

    test_record = {
        "antecedent": "妈妈让 OK 收拾玩具",
        "behavior": "OK 说'妈妈收'，然后继续玩",
        "consequence": "妈妈妥协了，帮 OK 收拾"
    }

    units = skill.decode(test_record)
    print(json.dumps(units, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
