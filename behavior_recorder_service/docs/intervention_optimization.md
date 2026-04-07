# V4.11.0 干预建议优化 - 渐进式知识库建设

> **创建时间：** 2026-03-30  
> **优先级：** P0  
> **状态：** 待执行

---

## 🎯 核心问题

当前干预建议模块存在两个问题：

1. **知识库不足** - 很多能力缺口没有对应的干预策略
2. **映射逻辑简单** - 没有根据关键词调用对应方案

---

## 🎯 优化方案

**核心思路：渐进式知识库建设**

```
用户输入 → AI 分析 → 能力缺口识别 → 查询知识库
                                      ↓
                            ┌─────────┴─────────┐
                            ↓                   ↓
                       ✅ 有匹配           ❌ 无匹配
                            ↓                   ↓
                       使用知识库        1. 告知用户无匹配
                       具体策略         2. AI 推理回答
                                        3. 给出推理逻辑
                                        4. 记录到待补充
```

---

## 📋 实现步骤

### 第 1 步：完善知识库结构

**文件：** `app/knowledge/intervention_strategies.json`

**要求：**
- 至少包含 3 个能力缺口类型
- 每个类型至少 2-3 个具体策略
- 每个策略包含：步骤、成功标准、年龄范围、情境

**示例结构：**
```json
{
  "capability_gaps": {
    "theory_of_mind": {
      "name": "心理理论/观点采择",
      "strategies": [
        {
          "name": "错误信念训练",
          "description": "通过藏物游戏帮助孩子理解他人可能有错误信念",
          "age_range": "4-6 岁",
          "steps": ["步骤 1", "步骤 2", "步骤 3"],
          "success_criteria": "孩子能正确回答他人会有错误信念",
          "materials": "盒子、小玩具",
          "context": ["家庭", "学校"]
        }
      ]
    }
  }
}
```

---

### 第 2 步：优化干预建议生成逻辑

**文件：** `app/agents/intervention_planner.py`

**新增方法：**

1. **`_ai_reasoning()`** - AI 推理生成建议
   - 当知识库无匹配时调用
   - 返回 AI 推理的建议和推理逻辑

2. **`_build_reasoning_prompt()`** - 构建推理提示词
   - 包含孩子信息、行为分析
   - 要求输出活动、成功标准、推理逻辑

3. **`_log_missing_case()`** - 记录缺失案例
   - 记录能力缺口、情境、年龄
   - 保存 AI 推理结果

4. **`_save_missing_cases()`** - 保存到文件
   - 保存到 `data/missing_intervention_cases.json`
   - 用于后续补充知识库

**核心逻辑：**
```python
def generate_recommendations(self, analysis_result, child_profile):
    # 1. 提取能力缺口和关键词
    gaps = self._extract_capability_gaps(analysis_result)
    keywords = self._extract_keywords(analysis_result)
    
    # 2. 从知识库查询
    strategies = self._query_knowledge_base(gaps, keywords)
    
    # 3. 判断是否有匹配
    if strategies:
        # ✅ 使用知识库
        return self._use_knowledge_base(strategies, child_profile)
    else:
        # ❌ AI 推理
        return self._ai_reasoning(analysis_result, child_profile, gaps, keywords)
```

---

### 第 3 步：前端显示优化

**文件：** `frontend/App.vue`

**新增内容：**

1. **来源标识**
   - 知识库：绿色徽章 "✅ 基于已验证的干预策略库"
   - AI 推理：黄色徽章 "⚠️ 当前知识库暂无此类案例..."

2. **推理逻辑展示区域**
   - 当 `intervention.reasoning_logic` 存在时显示
   - 标题："🤔 推理逻辑"
   - 样式：灰色背景，pre-line 格式

3. **样式区分**
   - `.knowledge-base-badge` - 绿色背景
   - `.ai-reasoning-badge` - 黄色背景，左侧黄色边框
   - `.reasoning-logic` - 灰色背景，圆角

---

### 第 4 步：缺失案例记录

**文件：** `data/missing_intervention_cases.json`

**记录内容：**
```json
{
  "timestamp": "2026-03-30T23:45:00",
  "capability_gap": ["theory_of_mind"],
  "context": ["家庭"],
  "age": "5 岁",
  "reasoning_result": {
    "activities": [...],
    "success_criteria": {...}
  },
  "status": "pending_review"
}
```

**用途：**
- 定期 review 这些案例
- 专业人士审核后补充到知识库
- 持续完善干预策略库

---

## ✅ 输出示例

### 场景 1：知识库有匹配

**后端返回：**
```json
{
  "source": "knowledge_base",
  "confidence": "high",
  "activities": [...],
  "note": "基于已验证的干预策略库"
}
```

**前端显示：**
```
✅ 基于已验证的干预策略库

🎮 具体策略
活动 1：错误信念训练
...
```

---

### 场景 2：知识库无匹配

**后端返回：**
```json
{
  "source": "ai_reasoning",
  "confidence": "medium",
  "activities": [...],
  "reasoning_logic": "基于孩子的观点采择困难，推荐从简单的视觉角度训练开始...",
  "note": "⚠️ 当前知识库暂无此类案例，以下建议基于 AI 推理生成，建议在专业人士指导下使用。我们已记录此案例，将尽快补充到知识库。"
}
```

**前端显示：**
```
⚠️ 当前知识库暂无此类案例，以下建议基于 AI 推理生成，
   建议在专业人士指导下使用。我们已记录此案例，
   将尽快补充到知识库。

🤔 推理逻辑
基于孩子的观点采择困难，推荐从简单的视觉角度训练开始。
因为孩子已能理解盒子里的糖果，说明具备基本认知能力，
但在推断他人视角时有困难。因此设计此活动...

🎮 具体策略
活动 1：视角转换游戏（AI 推理）
...
```

---

## 🎯 优先级

**P0（今天）：**
1. ✅ 完善知识库结构（至少 3 个能力缺口 × 2-3 个策略）
2. ✅ 实现 AI 推理逻辑
3. ✅ 前端显示来源标识和推理逻辑

**P1（明天）：**
4. ⏳ 实现缺失案例记录功能
5. ⏳ 优化推理提示词
6. ⏳ 完善个性化调整逻辑

---

## 📁 相关文件

- `app/knowledge/intervention_strategies.json` - 干预策略知识库
- `app/agents/intervention_planner.py` - 干预建议生成
- `frontend/App.vue` - 前端显示
- `data/missing_intervention_cases.json` - 缺失案例记录（新建）

---

## ✅ 验证标准

- [ ] 知识库有匹配时，显示"基于已验证的干预策略库"
- [ ] 知识库无匹配时，显示 AI 推理提示和推理逻辑
- [ ] 缺失案例正确记录到文件
- [ ] 前端样式区分明显（绿色=知识库，黄色=AI 推理）
- [ ] 推理逻辑显示完整，易于理解
- [ ] 列表格式正确（换行、项目符号）

---

**请阅读此文档并开始实施！完成后告知"优化完成"！**
