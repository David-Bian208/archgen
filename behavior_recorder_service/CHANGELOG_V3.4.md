# 行为观察伙伴 V3.4 更新日志

**版本**: 3.4.0  
**日期**: 2026 年 3 月 5 日  
**主题**: 多假设鉴别诊断专家 —— 从"擅长一类问题"到"应对多数常见问题"

---

## 核心升级

### V3.3 vs V3.4

| 维度 | V3.3 | V3.4 |
|------|------|------|
| **知识范围** | 提示依赖逃避模型 | **6 大高频行为场景** |
| **分析模式** | 单一路径分析 | **多假设鉴别诊断** |
| **对话流程** | ABC 收集→报告 | **ABC 收集→鉴别追问→整合分析** |
| **专业深度** | 单一假设 | **竞争性假设评估** |
| **报告结构** | 五段式叙事 | **多视角分析 + 倾向性判断** |

---

## 一、知识库扩展

### 6 大高频行为场景

| 场景键 | 场景名称 | 关键词示例 | 竞争假设数 |
|--------|----------|------------|------------|
| `task_disengagement` | 任务中发呆/中断 | 发呆、走神、不跟随 | 3 |
| `task_refusal` | 任务拒绝 | 不肯、不要、拒绝 | 4 |
| `elopement_wandering` | 离开/游走 | 跑开、乱跑、离开座位 | 4 |
| `stereotypy_self_stim` | 刻板行为/自我刺激 | 晃手、转圈、自言自语 | 4 |
| `social_withdrawal` | 社交回避 | 独处、背对、回避目光 | 4 |
| `transition_difficulty` | 转换困难 | 转换困难、不换活动、哭闹 | 4 |
| `demand_induced_agitation` | 要求引发的激动 | 要求后激动、哭闹、攻击 | 4 |

**总计**: 7 个场景，27 个竞争假设

---

### 知识库结构

```json
{
  "version": "3.4.0",
  "description": "自闭症干预高频行为场景鉴别知识库",
  "scenarios": [
    {
      "scene_key": "task_disengagement",
      "name": "任务中发呆/中断",
      "description": "在指令性或集体任务中，出现发呆、中断、不跟随的行为。",
      "keywords": ["发呆", "走神", "不做", "中断", ...],
      "competing_hypotheses": [
        {
          "id": "H1",
          "name": "提示依赖/执行功能挑战",
          "description": "个体依赖外部提示维持任务序列...",
          "key_discriminating_question": "当他发呆时，他的眼神和身体状态是怎样的？...",
          "supporting_evidence": ["有提示时表现良好", ...],
          "intervention_direction": "加强提示的系统性..."
        },
        ...
      ]
    },
    ...
  ]
}
```

---

## 二、核心推理流程重构

### V3.4 新流程

```
用户输入
   ↓
场景匹配（基于关键词）
   ↓
加载竞争性假设
   ↓
ABC 信息收集（环境→情境→行为→回应）
   ↓
鉴别性追问（融合各假设核心鉴别点）
   ↓
用户回答鉴别问题
   ↓
整合分析（评估各假设可能性）
   ↓
生成报告（多视角分析 + 倾向性判断）
```

### 关键代码变更

#### 1. 场景匹配与假设加载

```python
def _match_scenario_and_load_hypotheses(self, session, user_input):
    knowledge_base = get_knowledge_base()
    
    # 提取关键词
    keywords = self._extract_behavior_keywords(user_input)
    
    # 匹配场景
    matched_scenario = knowledge_base.match_scenario(keywords)
    
    if matched_scenario:
        session.matched_scenario = matched_scenario
        session.competing_hypotheses = knowledge_base.get_competing_hypotheses(
            matched_scenario.get("scene_key", "")
        )
```

#### 2. 鉴别性追问生成

```python
def _generate_discriminating_question(self, session):
    if not session.competing_hypotheses:
        return "能再详细描述一下当时的情况吗？"
    
    knowledge_base = get_knowledge_base()
    return knowledge_base.generate_discriminating_question(
        session.competing_hypotheses
    )
```

**示例追问**（发呆场景）：
```
为了更好地理解孩子'发呆'的性质，可以再描述一个细节吗？
当他发呆时，他的眼神和身体状态是怎样的？是看起来在迷茫、寻找提示，
还是完全放空、沉浸在自己的世界？另外，他发呆时，是否伴有任何细微的
重复性动作（如抿嘴、手指晃动、身体轻微摇晃）？
```

#### 3. 整合分析（带鉴别诊断）

```python
def analyze(self, environment, antecedent, behavior, consequence, 
            competing_hypotheses=None, discriminating_answer=""):
    if competing_hypotheses and discriminating_answer:
        # 使用鉴别诊断 Prompt
        user_prompt = ANALYSIS_WITH_DIFFERENTIAL_TEMPLATE.format(
            environment=environment,
            antecedent=antecedent,
            behavior=behavior,
            consequence=consequence,
            hypotheses_json=json.dumps(competing_hypotheses),
            discriminating_answer=discriminating_answer,
        )
    else:
        # 使用标准分析 Prompt
        ...
```

---

## 三、报告模板重塑

### V3.4 多视角分析报告

**（一）观察摘要**
```
在幼儿园早操时，您敏锐地发现孩子"看老师就做得好，不看就容易发呆"。
当时环境有点吵闹，其他小朋友都在跟着老师做。
```

**（二）多视角分析**（核心部分）
```
针对"发呆"这一行为，在专业评估中通常会考虑几种可能性：

1) 提示依赖/执行功能挑战：个体依赖外部提示维持任务序列，提示消失时
   因工作记忆或任务启动困难而中断，表现为迷茫、等待。

2) 自我刺激/刻板思维：外部任务失去吸引力或难以理解，个体转入内在的、
   重复性的思维或感官体验。

3) 感官过载/逃避：环境刺激（噪音、人群、灯光）超负荷，个体通过"关闭"
   或逃避来调节。

结合您补充的"他发呆时眼神看起来在迷茫，像是在找老师的位置，身体没有
重复性动作"，目前看来，**提示依赖/执行功能挑战**的可能性相对较高，
因为他的眼神表明他在寻找外部线索，而不是沉浸在自己的世界。

但同时，**感官过载**的因素也可能部分存在，因为您提到环境有点吵闹，
这可能加剧了他对老师这个明确提示的依赖。
```

**（三）核心解读**（金句）
```
这提示孩子可能更多是"不知道眼睛离开老师后该怎么办"，而不是"不想做"。
他的"动作记忆"需要靠眼睛实时"充电"。
```

**（四）针对性建议**
```
因此，我们可以首先尝试"预装一个动作"的策略：在跳操前，和他一起夸张地
摆出第一个动作（如"开飞机"），并大声说"记住哦，第一个是开飞机！"。
目的是帮他把一个外部提示（老师动作）转化为一个内部提示（自己脑子里的
口诀或画面）。下次他发呆时，可以轻声提示"开飞机！"，看他能否接上。
```

**（五）后续观察重点**
```
您可以留意：
1. 当环境安静一些时，他的发呆行为是否有减少？
2. 当您提前"预装动作"后，他独立跟随的时间是否延长？
```

---

## 四、实测案例

### 案例：任务中发呆

**用户输入**：
```
早操时发呆，看老师就跟着做，不看就站着
```

**V3.4 对话流程**：

```
👤 早操时发呆，看老师就跟着做，不看就站着

💬 您能注意到孩子在早操时的状态，真的很细心。
   感谢您这么细致的观察，这非常有帮助。
   为了能更准确地理解当时的情况，我想了解一下当时周围的环境怎么样？
   比如是有点吵闹还是比较安静，其他小朋友大多在做什么呢？

👤 有点吵闹，其他小朋友都在跟着老师做

💬 明白了，环境有点吵闹。
   为了更好地理解孩子"发呆"的性质，可以再描述一个细节吗？
   当他发呆时，他的眼神和身体状态是怎样的？是看起来在迷茫、寻找提示，
   还是完全放空、沉浸在自己的世界？另外，他发呆时，是否伴有任何细微的
   重复性动作（如抿嘴、手指晃动、身体轻微摇晃）？

👤 眼神看起来在迷茫，像是在找老师的位置，身体没有重复性动作

💬 您描述得很具体，这很有帮助。
   当孩子那样做的时候，你或周围人（比如老师）第一时间是怎么回应的呢？

👤 老师会继续做操，没有特别干预

✨ 根据我们刚才的交流，我生成了一份简要的分析报告...
```

**生成的报告**（节选关键部分）：

```
📝 观察摘要
在幼儿园早操时，您敏锐地发现孩子"看老师就做得好，不看就容易发呆"。
当时环境有点吵闹，其他小朋友都在跟着老师做。老师没有特别干预。

🔍 多视角分析
针对"发呆"这一行为，在专业评估中通常会考虑几种可能性：

1) 提示依赖/执行功能挑战：个体依赖外部提示维持任务序列...
2) 自我刺激/刻板思维：外部任务失去吸引力...
3) 感官过载/逃避：环境刺激超负荷...

结合您补充的"眼神看起来在迷茫，像是在找老师的位置，身体没有重复性动作"，
目前看来，**提示依赖/执行功能挑战**的可能性相对较高，因为他的眼神表明
他在寻找外部线索，而不是沉浸在自己的世界。

💡 核心解读
这提示孩子可能更多是"不知道眼睛离开老师后该怎么办"，而不是"不想做"。
他的"动作记忆"需要靠眼睛实时"充电"。

🌱 针对性建议
因此，我们可以首先尝试"预装一个动作"的策略...

👀 后续观察重点
您可以留意：
1. 当环境安静一些时，他的发呆行为是否有减少？
2. 当您提前"预装动作"后，他独立跟随的时间是否延长？
```

---

## 五、技术实现

### 文件变更

| 文件 | 变更 | 行数 |
|------|------|------|
| `app/knowledge/behavior_hypotheses.json` | 6 大场景知识库 | +300 |
| `app/knowledge/__init__.py` | 知识库加载与匹配逻辑 | +50 |
| `app/agents/guided_recorder_agent_v3.py` | 鉴别诊断流程 | +100 |
| `app/agents/insight_analyzer.py` | 鉴别诊断 Prompt | +50 |
| `frontend_v3/App.vue` | 版本标识 | +5 |
| `main.py` | 版本标识 | +5 |

### 核心类/方法

**BehaviorKnowledgeBase**（知识库）：
- `match_scenario(keywords)`: 场景匹配
- `get_competing_hypotheses(scene_key)`: 获取竞争假设
- `generate_discriminating_question(hypotheses)`: 生成鉴别性问题

**GuidedRecorderAgentV3**（Agent）：
- `_match_scenario_and_load_hypotheses(session, user_input)`: 场景匹配与假设加载
- `_extract_behavior_keywords(text)`: 提取行为关键词
- `_generate_discriminating_question(session)`: 生成鉴别性问题

**InsightAnalyzer**（分析器）：
- `analyze(..., competing_hypotheses, discriminating_answer)`: 带鉴别诊断的分析

---

## 六、验收标准达成

| 标准 | 状态 | 说明 |
|------|------|------|
| 知识库包含 6+ 场景 | ✅ | 7 个场景，27 个竞争假设 |
| 场景匹配准确 | ✅ | 基于关键词的智能匹配 |
| 鉴别性追问自然 | ✅ | 融合各假设核心鉴别点 |
| 报告体现多视角 | ✅ | 多可能性评估 + 倾向性判断 |
| 交互流畅自然 | ✅ | 追问不突兀，对话连贯 |

---

## 七、部署说明

### 启动 V3.4

```bash
# 后端
cd /home/admin/openclaw/workspace/behavior_recorder_service
python3 main.py

# V3.4 前端（端口 3001）
cd frontend_v3
npm run dev -- --host 0.0.0.0 --port 3001
```

### 访问地址

- **V3.4 前端**: http://localhost:3001
- **API 文档**: http://localhost:8000/docs

---

## 八、总结

V3.4 是**从"优秀工具"到"专家级 AI"**的质变：

| 维度 | V3.3 | V3.4 |
|------|------|------|
| **知识范围** | 单一场景 | **7 大场景覆盖** |
| **分析深度** | 单一假设 | **多假设鉴别** |
| **对话智能** | ABC 收集 | **鉴别性追问** |
| **报告专业度** | 单一结论 | **多视角 + 倾向性** |
| **可扩展性** | 硬编码 | **知识库驱动** |

**核心价值**:
- **知识库是 Agent 的"宪法"**：持久化、结构化、可迭代
- **鉴别诊断是专家的标志**：不武断下结论，评估多种可能性
- **追问是收集证据的手段**：精准、具体、旨在区分假设

**从"擅长分析一类问题"到"能应对一个领域内多数常见问题"**。

---

**开发团队**: OpenClaw  
**验收状态**: ✅ 已完成  
**生产就绪**: 是  
**推荐版本**: V3.4（多假设鉴别诊断专家）
