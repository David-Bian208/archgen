# 行为分析 Agent 设计文档（V2 - 专家思维版）

**创建时间：** 2026-04-09  
**版本：** V2.0  
**类型：** Agent（复杂推理）+ Skills（可复用模块）

---

## 🎯 设计理念

基于自闭症专家的思考流程：
1. **从具体到抽象** - 从行为细节出发，向上归因到认知功能
2. **平行假设** - 同时考虑多种可能性，避免过早收敛
3. **阶段思维** - 所有能力都用"发展程度"来衡量
4. **系统观** - 关注不同认知功能如何相互作用
5. **证据驱动** - 每一个判断都链接回可观察的行为证据

---

## 🏗️ 架构设计

```
用户输入（ABC 描述）
  ↓
┌─────────────────────────────────────────┐
│  行为分析 Agent（统筹推理）              │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  Skills 层（可复用模块）         │   │
│  │                                 │   │
│  │  1. 行为解码 Skills             │   │
│  │     → 提取认知行为单元          │   │
│  │                                 │   │
│  │  2. 模式提炼 Skills             │   │
│  │     → 聚类相似行为模式          │   │
│  │                                 │   │
│  │  3. 多维度假设生成 Skills        │   │
│  │     → 平行列举假设清单          │   │
│  │                                 │   │
│  │  4. 证据权衡 Skills             │   │
│  │     → 支持/反驳证据评估         │   │
│  └─────────────────────────────────┘   │
│                                         │
│  Agent 整合层：                          │
│  - 阶段定位（发展程度）                 │
│  - 整合归因（结构化陈述）               │
└─────────────────────────────────────────┘
  ↓
输出：结构化诊断描述
```

---

## 📋 Skills 层详细设计

### Skills 1: 行为解码

**功能：** 从 ABC 描述中提取"认知行为单元"

**输入：**
```json
{
  "antecedent": "妈妈让 OK 收拾玩具",
  "behavior": "OK 说'妈妈收'，然后继续玩",
  "consequence": "妈妈妥协了，帮 OK 收拾"
}
```

**输出：**
```json
{
  "cognitive_units": [
    {
      "unit_id": "CU1",
      "type": "任务响应",
      "description": "接收到任务指令后，用语言拒绝而非行动执行"
    },
    {
      "unit_id": "CU2",
      "type": "行为持续",
      "description": "拒绝后继续原有活动（玩玩具），未表现出不适"
    }
  ]
}
```

**提示词要点：**
- 剥离情境细节，关注"做了什么"
- 用中性语言描述，不带价值判断
- 每个单元聚焦一个认知操作

---

### Skills 2: 模式提炼

**功能：** 将多个认知行为单元聚类为行为模式

**输入：** 多个认知行为单元（来自多条 ABC 记录）

**输出：**
```json
{
  "behavior_patterns": [
    {
      "pattern_id": "BP1",
      "pattern_name": "任务延迟响应",
      "description": "在接收到任务指令时，倾向于用语言延迟而非立即执行",
      "related_units": ["CU1", "CU3", "CU5"]
    },
    {
      "pattern_id": "BP2",
      "pattern_name": "成人依赖",
      "description": "遇到困难时，期待成人介入而非独立尝试",
      "related_units": ["CU2", "CU4"]
    }
  ]
}
```

**提示词要点：**
- 寻找重复出现的行为特征
- 用描述性语言命名模式（非标签化）
- 关联相关的认知行为单元

---

### Skills 3: 多维度假设生成

**功能：** 针对每个行为模式，平行列举认知功能解释

**输入：** 行为模式列表

**输出：**
```json
{
  "hypotheses": [
    {
      "hypothesis_id": "H1",
      "related_pattern": "BP1",
      "cognitive_domain": "执行功能 - 抑制控制",
      "description": "难以抑制'继续玩玩具'这一优势反应，切换到任务执行",
      "neural_system": "前额叶皮层（尤其是下前额叶）",
      "developmental_stage": "能抑制明显无关干扰，但无法抑制内在优势认知反应"
    },
    {
      "hypothesis_id": "H2",
      "related_pattern": "BP1",
      "cognitive_domain": "执行功能 - 认知灵活性",
      "description": "从'游戏状态'切换到'任务状态'的转换困难",
      "neural_system": "前额叶皮层 - 顶叶网络",
      "developmental_stage": "需要外部提示辅助转换"
    },
    {
      "hypothesis_id": "H3",
      "related_pattern": "BP2",
      "cognitive_domain": "心理理论 - 意图理解",
      "description": "可能未完全理解'妈妈让收拾'背后的期望和意图",
      "neural_system": "内侧前额叶、颞顶联合区",
      "developmental_stage": "能理解直接指令，但推断隐含期望有困难"
    }
  ]
}
```

**核心假设框架（参考专家设计）：**

| 行为模式 | 假设 ID | 认知功能解释 | 关联系统 |
|----------|--------|--------------|----------|
| "报告自身视角，无法推断他人" | H1 | 心理理论 - 错误信念 | 颞顶联合区、内侧前额叶 |
| | H2 | 执行功能 - 抑制控制 | 前额叶皮层 |
| | H3 | 工作记忆超载 | 前额叶 - 顶叶网络 |
| | H4 | 语言理解具体化 | 左颞叶语言区 |
| "固着于角色 - 物品关联" | H5 | 认知灵活性不足 | 前额叶皮层 |
| | H6 | 视觉空间规则内化弱 | 顶叶、枕叶视觉联合区 |

**提示词要点：**
- 平行列举，不急于下结论
- 每个假设必须与行为模式有逻辑关联
- 标注关联的神经/发展系统

---

### Skills 4: 证据权衡

**功能：** 评估每个假设的强弱证据

**输入：** 假设清单 + ABC 描述

**输出：**
```json
{
  "evidence_evaluation": [
    {
      "hypothesis_id": "H1",
      "supporting_evidence": [
        "OK 能报告自己知道的真实内容（糖果）",
        "OK 知道爸爸打开过盒子"
      ],
      "contradicting_evidence": [],
      "weight": "强",
      "confidence": 0.85
    },
    {
      "hypothesis_id": "H2",
      "supporting_evidence": [
        "OK 在需要等待时表现出困难"
      ],
      "contradicting_evidence": [
        "OK 能在结构化情境中等待"
      ],
      "weight": "中",
      "confidence": 0.60
    }
  ]
}
```

**提示词要点：**
- 寻找支持证据（行为观察中的具体细节）
- 寻找反驳证据（与假设矛盾的行为）
- 评估证据权重（强/中/弱）
- 给出置信度（0-1）

---

## 🧠 Agent 整合层设计

### 行为分析 Agent

**功能：** 整合 Skills 输出，进行阶段定位和整合归因

**输入：**
- Skills 1-4 的输出
- 多条 ABC 记录（如有）

**处理流程：**

**Step 1: 阶段定位**
- 不问"执行功能有没有问题？"
- 改问"在执行功能的哪个子项（抑制、转换、更新）上，处于哪个发展阶段？"
- 为每个认知维度定位发展阶段

**Step 2: 整合归因**
- 将各假设的评估结果整合
- 形成非平衡的能力发展剖面图
- 识别强项、当前发展焦点、潜在挑战

**Step 3: 结构化陈述**
- 生成最终的诊断性描述
- 用发展性语言（"正处在...过渡的关键期"）
- 强调多认知环节的协同运作

**输出：**
```json
{
  "success": true,
  "developmental_profile": {
    "strengths": [
      "事实记忆能力良好",
      "字面语言理解正常",
      "共同注意能力发展适当"
    ],
    "current_focus": [
      "心理理论（二级错误信念）",
      "执行功能（抑制控制/认知灵活性）"
    ],
    "potential_challenges": [
      "视觉空间推理的抽象规则应用"
    ]
  },
  "attribution_statement": "根据观察，孩子目前的核心挑战在于多认知环节的协同运作。其心理理论正处在从'理解知识状态不同'向'处理复杂视角采择'过渡的关键期，表现为二级错误信念任务困难。这一挑战被执行功能中抑制控制能力的阶段性限制所加剧——他难以抑制自身已知信息的自动输出。同时，视觉空间认知中对于'视角取决于位置'这一抽象规则的内化尚不稳固，导致他更依赖具体的'人物 - 物品'关联进行判断。这三者相互影响，共同构成了当前在换位思考任务中观察到的行为模式。",
  "hypotheses_ranking": [
    {"id": "H1", "rank": 1, "confidence": 0.85},
    {"id": "H2", "rank": 2, "confidence": 0.60},
    {"id": "H3", "rank": 3, "confidence": 0.45}
  ]
}
```

---

## 💻 技术实现

### 文件结构
```
skills/behavior-analysis/
├── SKILL.md              # Skills 说明
├── agent.py              # Agent 主程序
├── skills/
│   ├── __init__.py
│   ├── behavior_decoding.py    # Skills 1
│   ├── pattern_extraction.py   # Skills 2
│   ├── hypothesis_generation.py # Skills 3
│   └── evidence_weighing.py    # Skills 4
├── prompts/
│   ├── decoding_prompt.py
│   ├── pattern_prompt.py
│   ├── hypothesis_prompt.py
│   └── evidence_prompt.py
├── test.py
└── examples/
```

### Agent 主程序（agent.py）

```python
#!/usr/bin/env python3
"""行为分析 Agent - 专家思维版"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

# 添加项目路径
PROJECT_ROOT = Path('/home/admin/.openclaw/workspace/behavior_recorder_service')
sys.path.insert(0, str(PROJECT_ROOT))

from skills.behavior_decoding import BehaviorDecodingSkill
from skills.pattern_extraction import PatternExtractionSkill
from skills.hypothesis_generation import HypothesisGenerationSkill
from skills.evidence_weighing import EvidenceWeighingSkill
from app.llm.openai_client import OpenAIClient


class BehaviorAnalysisAgent:
    """行为分析 Agent"""
    
    def __init__(self):
        self.client = OpenAIClient()
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
                abc_records=abc_records
            )
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _integrate(self, patterns, hypotheses, evidence, abc_records):
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
            max_tokens=2000
        )
        
        return {
            "success": True,
            **response
        }
    
    def _build_integration_prompt(self, patterns, hypotheses, evidence, abc_records):
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
    
    # 测试用例
    test_records = [{
        "antecedent": "妈妈和 OK 玩薯片盒子游戏",
        "behavior": "OK 能说出盒子里是糖果，但当被问'妈妈会看到什么'时，OK 说'糖'",
        "consequence": "妈妈继续引导，但 OK 不太理解"
    }]
    
    result = agent.analyze(test_records)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

---

## ✅ 测试用例

### 测试用例 1：二级错误信念

**输入：** 薯片盒子游戏 ABC 记录

**预期输出：**
- 发展阶段定位：心理理论（一级信念通过，二级信念困难）
- 整合归因：多认知环节协同挑战

---

## 📊 质量标准

### 准确性
- 行为解码准确率 ≥90%
- 假设生成覆盖率 ≥95%（不遗漏主要可能性）
- 证据评估一致性 ≥85%

### 性能
- 单次分析响应时间 <30 秒
- JSON 解析成功率 100%

### 专业性
- 使用发展性语言（非标签化）
- 强调多因素协同（非单一归因）
- 证据驱动（每个判断有行为支撑）

---

**设计版本：** V2.0  
**设计状态：** ⏳ 待 DAVID 确认  
**下一步：** 实现 + 测试
