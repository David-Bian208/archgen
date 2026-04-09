# 行为分析 Skills 设计文档

**创建时间：** 2026-04-09  
**版本：** V1.0  
**类型：** Skills（技能模块）

---

## 🎯 Skills 定位

**行为分析 Skills** 是一个理性分析模块，基于 ABC 场景描述，客观分析孩子行为背后的原因。

**核心特点：**
- ✅ 理性、客观、基于证据
- ✅ 专业但不说教
- ✅ 输出结构化信息
- ✅ 不包含感性表达（那是心伴解读 Agent 的职责）

---

## 📋 输入输出

### 输入
```json
{
  "scenario": {
    "antecedent": "行为发生前的情境",
    "behavior": "孩子的具体表现",
    "consequence": "周围的反应和环境",
    "child_age": "孩子年龄"
  }
}
```

### 输出
```json
{
  "success": true,
  "behavior_function": "寻求关注/逃避/获得物品/自我刺激",
  "capability_gaps": [
    {
      "dimension": "心理理论",
      "description": "具体能力缺口描述"
    },
    {
      "dimension": "执行功能",
      "description": "具体能力缺口描述"
    }
  ],
  "identified_problems": [
    "问题 1",
    "问题 2",
    "问题 3"
  ],
  "analysis_summary": "简短的分析总结（100 字以内）"
}
```

---

## 🔍 分析维度

### 1. 行为功能判断

**四种功能类型：**

| 功能 | 特征 | 示例 |
|------|------|------|
| **寻求关注** | 通过行为获得他人注意 | 故意捣乱、大声说话 |
| **逃避** | 通过行为逃避任务/要求 | 拖延、哭闹、转移话题 |
| **获得物品** | 通过行为获得想要的东西 | 哭闹要玩具、抢东西 |
| **自我刺激** | 行为本身带来感官满足 | 摇晃身体、重复动作 |

**判断依据：**
- ABC 场景中的前因（A）
- 行为发生后的结果（C）
- 行为的重复模式

---

### 2. 能力缺口分析

**四维度框架：**

#### 2.1 心理理论（Theory of Mind）
**核心能力：**
- 观点采择（站在别人角度看问题）
- 错误信念理解（理解别人可能有错误认知）
- 意图推理（理解别人的行为意图）

**常见问题：**
- "以为别人都知道自己知道的事情"
- "不理解别人可能有不同的想法"
- "难以预测别人的反应"

#### 2.2 执行功能（Executive Function）
**核心能力：**
- 抑制控制（控制冲动）
- 工作记忆（记住信息并处理）
- 认知灵活性（适应变化）

**常见问题：**
- "控制不住冲动"
- "容易忘记规则"
- "不接受变化，坚持同一性"

#### 2.3 视觉 - 空间认知（Visual-Spatial）
**核心能力：**
- 视角转换（不同位置看到不同）
- 空间关系理解
- 心理旋转能力

**常见问题：**
- "不理解别人从不同位置看到的东西不一样"
- "空间定位困难"

#### 2.4 语言与概念理解（Language & Concept）
**核心能力：**
- 抽象概念理解
- 语言推理
- 隐喻理解

**常见问题：**
- "字面理解，不懂隐喻"
- "抽象概念困难"
- "语言推理能力弱"

---

### 3. 问题识别

**基于行为分析和能力缺口，列出具体问题：**

**示例：**
```
1. 孩子难以理解别人可能有不同的想法（心理理论 - 观点采择）
2. 在需要等待的情境中表现出冲动控制困难（执行功能 - 抑制控制）
3. 对规则变化的适应能力较弱（执行功能 - 认知灵活性）
```

---

## 💻 技术实现

### 文件结构
```
skills/behavior-analysis/
├── SKILL.md          # Skills 说明文档
├── prompt.py         # 提示词模板
├── executor.py       # 执行器
├── test.py           # 测试脚本
└── examples/
    ├── input_example.json
    └── output_example.json
```

### 提示词模板（prompt.py）

```python
BEHAVIOR_ANALYSIS_PROMPT = """
你是一位专业的儿童行为分析师。请基于 ABC 场景描述，理性分析孩子的行为。

## ABC 场景
**情境（前因）：** {antecedent}
**孩子的表现（行为）：** {behavior}
**周围的反应（结果）：** {consequence}
**孩子年龄：** {child_age}

## 分析任务

### 1. 行为功能判断
判断孩子的行为功能属于以下哪种：
- 寻求关注：通过行为获得他人注意
- 逃避：通过行为逃避任务/要求
- 获得物品：通过行为获得想要的东西
- 自我刺激：行为本身带来感官满足

### 2. 能力缺口分析
从以下四个维度分析能力缺口：
- 心理理论：观点采择、错误信念理解、意图推理
- 执行功能：抑制控制、工作记忆、认知灵活性
- 视觉 - 空间认知：视角转换、空间关系理解
- 语言与概念理解：抽象概念、语言推理

### 3. 问题识别
列出观察到的具体问题（3-5 个）

## 输出格式（JSON）
```json
{{
  "behavior_function": "寻求关注/逃避/获得物品/自我刺激",
  "capability_gaps": [
    {{
      "dimension": "心理理论/执行功能/视觉 - 空间/语言理解",
      "description": "具体能力缺口描述"
    }}
  ],
  "identified_problems": [
    "问题 1",
    "问题 2",
    "问题 3"
  ],
  "analysis_summary": "简短的分析总结（100 字以内）"
}}
```

## 分析原则
1. **理性客观** - 基于 ABC 信息，不主观臆断
2. **专业准确** - 使用专业术语，但解释清楚
3. **简洁清晰** - 每个问题用一句话描述
4. **避免说教** - 直接分析，不用"临床上通常..."
"""
```

### 执行器（executor.py）

```python
#!/usr/bin/env python3
"""行为分析 Skills 执行器"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

# 添加项目路径
PROJECT_ROOT = Path('/home/admin/.openclaw/workspace/behavior_recorder_service')
sys.path.insert(0, str(PROJECT_ROOT))

from prompt import BEHAVIOR_ANALYSIS_PROMPT
from app.llm.openai_client import OpenAIClient


class BehaviorAnalysisSkill:
    """行为分析 Skills"""
    
    def __init__(self):
        self.client = OpenAIClient(
            api_key=os.getenv('LLM_API_KEY', ''),
            base_url=os.getenv('LLM_BASE_URL', 'https://api.deepseek.com'),
            model=os.getenv('LLM_MODEL', 'deepseek-chat')
        )
    
    def analyze(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行行为分析
        
        Args:
            scenario: ABC 场景信息
            
        Returns:
            分析结果
        """
        try:
            # 构建提示词
            prompt = BEHAVIOR_ANALYSIS_PROMPT.format(
                antecedent=scenario.get('antecedent', ''),
                behavior=scenario.get('behavior', ''),
                consequence=scenario.get('consequence', ''),
                child_age=scenario.get('child_age', '')
            )
            
            # 调用 LLM
            response = self.client.generate_json(
                system_prompt="你是一位专业的儿童行为分析师，擅长理性分析孩子行为。",
                user_prompt=prompt,
                temperature=0.1,
                max_tokens=1500
            )
            
            # 验证输出格式
            return self._validate_response(response)
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _validate_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """验证响应格式"""
        required_fields = [
            'behavior_function',
            'capability_gaps',
            'identified_problems',
            'analysis_summary'
        ]
        
        for field in required_fields:
            if field not in response:
                return {
                    "success": False,
                    "error": f"缺少必需字段：{field}"
                }
        
        # 验证行为功能
        valid_functions = ['寻求关注', '逃避', '获得物品', '自我刺激']
        if response['behavior_function'] not in valid_functions:
            return {
                "success": False,
                "error": f"无效的行为功能：{response['behavior_function']}"
            }
        
        # 添加成功标记
        response['success'] = True
        return response


def main():
    """命令行测试"""
    skill = BehaviorAnalysisSkill()
    
    # 测试用例
    test_scenario = {
        "antecedent": "妈妈让 OK 收拾玩具",
        "behavior": "OK 开始哭闹，把玩具扔在地上",
        "consequence": "妈妈妥协了，说'好吧好吧，妈妈帮你收'",
        "child_age": "5 岁"
    }
    
    result = skill.analyze(test_scenario)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

---

## ✅ 测试用例

### 测试用例 1：逃避行为
**输入：**
```json
{
  "antecedent": "老师要求小明完成作业",
  "behavior": "小明说肚子疼，想去医务室",
  "consequence": "老师让他休息，暂时不需要写作业",
  "child_age": "8 岁"
}
```

**预期输出：**
- 行为功能：逃避
- 能力缺口：执行功能（任务坚持性）
- 问题：遇到困难任务时倾向于逃避而非坚持

---

### 测试用例 2：寻求关注
**输入：**
```json
{
  "antecedent": "妈妈在和客人聊天",
  "behavior": "小红故意大声唱歌，打断对话",
  "consequence": "妈妈停止聊天，看向小红",
  "child_age": "4 岁"
}
```

**预期输出：**
- 行为功能：寻求关注
- 能力缺口：心理理论（理解他人注意力）
- 问题：用不恰当方式获得关注

---

### 测试用例 3：获得物品
**输入：**
```json
{
  "antecedent": "在超市看到想要的玩具",
  "behavior": "躺在地上哭闹",
  "consequence": "爸爸买了玩具",
  "child_age": "6 岁"
}
```

**预期输出：**
- 行为功能：获得物品
- 能力缺口：执行功能（情绪调节）
- 问题：用哭闹作为获得物品的手段

---

## 📊 质量标准

### 准确性
- 行为功能判断准确率 ≥90%
- 能力缺口分析准确率 ≥85%
- 问题识别相关性 ≥90%

### 性能
- 单次分析响应时间 <10 秒
- JSON 解析成功率 100%
- 输出格式合规率 100%

### 语言风格
- 理性、客观
- 专业但不说教
- 简洁清晰（每个问题<30 字）

---

## 🔗 与其他模块的关系

```
ABC 场景描述（Skills 1）
  ↓
行为分析（Skills 2）← 本模块
  ↓
心伴解读 Agent
```

**依赖关系：**
- 输入：ABC 场景描述 Skills 的输出
- 输出：供心伴解读 Agent 使用

**边界：**
- ✅ 负责：理性分析问题
- ❌ 不负责：感性表达、建议生成（这是心伴解读 Agent 的职责）

---

**设计版本：** V1.0  
**设计状态：** ⏳ 待 DAVID 确认  
**下一步：** 实现 + 测试
