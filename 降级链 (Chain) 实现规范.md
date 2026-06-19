# 降级链 (Chain) 实现规范 v1.0

**版本：** v1.0  
**创建时间：** 2026-06-19  
**作者：** 战舰  
**状态：** 📋 设计阶段，待实施  
**关联文档：** `内容补充架构设计.md`

---

## 一、核心概念定义

### 1.1 什么是降级链？

**降级链（Degradation Chain）** 是一套分层决策机制，用于在 AI 知识不足时，按预设规则逐级降级输出策略，避免"硬编内容"。

**核心思想：** 宁可承认不知道，也不编造错误信息。

### 1.2 为什么需要降级链？

**旧架构问题：**
```
用户输入 → AI 补充 → 硬编内容 → 重新评估 → 暴露更多问题 → 死循环
```

**新架构解决：**
```
用户输入 → 知识评估 → 选择降级级别 → 输出对应策略 → 条件化重新评估
```

### 1.3 降级链 vs 知识评估

| 概念 | 作用 | 输出 |
|------|------|------|
| **知识评估** | AI 自评"我知道多少" | L0/L1/L2/L3/L4 |
| **降级链** | 根据级别选择"怎么输出" | 补充内容/问题/类比/框架 |

---

## 二、L0-L4 级别详细定义

### 2.1 判定标准矩阵

| 级别 | 名称 | 判定标准（必须同时满足） | 典型特征 |
|------|------|------------------------|---------|
| **L0** | 知识充足 | 1. 能直接补充具体内容<br>2. 有具体案例/数据/技术细节支撑<br>3. 能准确引用用户输入中的关键信息 | "这个我知道，具体是..." |
| **L1** | 知识部分 | 1. 知道通用模式/框架<br>2. 缺少具体案例/数据<br>3. 能标注缺口在哪里 | "基于通用模式...但具体 XX 需要你补充" |
| **L2** | 知识稀疏 | 1. 不能直接补充内容<br>2. 能提出结构化问题<br>3. 问题能帮助用户思考 | "这个话题我不太熟，但你可以思考这些问题..." |
| **L3** | 知识几乎没有 | 1. 无法提出具体问题<br>2. 只能用类比推导<br>3. 类比必须明确标注 | "这个超出我的知识范围，但类似..." |
| **L4** | 知识空白 | 1. 完全不知道用户在说什么<br>2. 只能给空框架/维度<br>3. 框架不包含任何具体内容 | "这个话题我完全不懂，建议你提供资料" |

### 2.2 快速判断流程图

```
开始
  ↓
问：我能直接补充具体内容吗？
  ├─ 能 → 问：有具体案例/数据支撑吗？
  │        ├─ 有 → 【L0 知识充足】
  │        └─ 没有 → 【L1 知识部分】
  │
  └─ 不能 → 问：我能提出结构化问题吗？
           ├─ 能 → 【L2 知识稀疏】
           └─ 不能 → 问：能用类比推导吗？
                    ├─ 能 → 【L3 知识几乎没有】
                    └─ 不能 → 【L4 知识空白】
```

### 2.3 特殊情况处理

| 情况 | 处理方式 | 示例 |
|------|---------|------|
| 用户输入包含专业术语 | 至少 L1（如果知道术语含义） | 用户说"RAG 优化"→ AI 知道 RAG → L1 |
| 用户输入包含具体数据 | 至少 L0（如果能解释数据） | 用户说"40 分钟"→ AI 能解释为什么 40 分钟 → L0 |
| 用户输入模糊描述 | 最多 L2 | 用户说"很多"、"有问题"→ L2 |
| AI 需要靠类比理解 | L3 | 量子计算 → 类比高速公路 |
| AI 完全听不懂 | L4 | 公司内部系统 Chronos → L4 |

---

## 三、各级别输出规范

### 3.1 L0（知识充足）

**输出物：** 具体事实/案例/数据

**格式要求：**
```json
{
  "item": "缺失项名称",
  "knowledge_level": "L0",
  "content": "具体内容（必须有实质信息）",
  "evidence_quote": "引用的用户原话或数据",
  "source": "user_content | general_knowledge | ai_inference",
  "confidence": "high",
  "reevaluate": true
}
```

**示例：**
```json
{
  "item": "具体应用场景",
  "knowledge_level": "L0",
  "content": "Vibe Coding 特别适合以下场景：\n1. 快速原型开发（如仪表盘、CRUD 应用）\n2. 学习编程（初学者通过对话理解概念）\n3. 代码重构（用自然语言描述重构目标）",
  "evidence_quote": "它比传统编程快很多，特别适合快速原型开发",
  "source": "user_content",
  "confidence": "high",
  "reevaluate": true
}
```

**验收标准：**
- ✅ 内容有实质信息（不是空话）
- ✅ 有具体案例/数据/技术细节
- ✅ 能准确引用用户输入
- ✅ confidence = "high"

---

### 3.2 L1（知识部分）

**输出物：** 通用模式展开 + 缺口标注

**格式要求：**
```json
{
  "item": "缺失项名称",
  "knowledge_level": "L1",
  "content": "基于通用模式的展开内容",
  "gap_hint": "明确标注缺口在哪里",
  "source": "general_knowledge",
  "confidence": "medium",
  "reevaluate": true
}
```

**示例：**
```json
{
  "item": "技术实现细节",
  "knowledge_level": "L1",
  "content": "基于通用 AI 编程模式，实现可能涉及：\n1. 自然语言理解（Prompt 解析）\n2. 代码生成（LLM 输出）\n3. 代码验证（测试/运行）",
  "gap_hint": "需要你补充：具体技术栈、模型选择、框架名称",
  "source": "general_knowledge",
  "confidence": "medium",
  "reevaluate": true
}
```

**验收标准：**
- ✅ 内容有通用模式支撑
- ✅ 明确标注缺口（gap_hint 必填）
- ✅ confidence = "medium"
- ✅ 不假装知道具体内容

---

### 3.3 L2（知识稀疏）

**输出物：** 结构化问题列表

**格式要求：**
```json
{
  "item": "缺失项名称",
  "knowledge_level": "L2",
  "questions": ["问题 1", "问题 2", "问题 3"],
  "hint": "这个话题我的知识有限，以下基于通用模式推导",
  "source": "ai_inference",
  "confidence": "low",
  "reevaluate": false
}
```

**示例：**
```json
{
  "item": "性能优化策略",
  "knowledge_level": "L2",
  "questions": [
    "你说的'性能问题'具体指什么？→ 响应时间？吞吐量？资源占用？",
    "当前系统的性能指标是多少？→ 有基线数据吗？",
    "性能瓶颈在哪里？→ 数据库？网络？计算？"
  ],
  "hint": "这个话题我的知识有限，以下基于通用模式推导",
  "source": "ai_inference",
  "confidence": "low",
  "reevaluate": false
}
```

**验收标准：**
- ✅ 问题必须是结构化的（不是泛泛而问）
- ✅ 问题能帮助用户思考
- ✅ 有 hint 提示用户 AI 知识有限
- ✅ reevaluate = false（不重新评估）

---

### 3.4 L3（知识几乎没有）

**输出物：** 类比推导

**格式要求：**
```json
{
  "item": "缺失项名称",
  "knowledge_level": "L3",
  "analogy": "类比内容",
  "hint": "这个话题超出我的知识范围，以下基于类比推导",
  "source": "ai_analogy",
  "confidence": "low",
  "reevaluate": false
}
```

**示例：**
```json
{
  "item": "量子计算对区块链的影响",
  "knowledge_level": "L3",
  "analogy": "量子计算对区块链 ≈ 高速公路对马车系统的影响\n- 不是'更快'，是'范式转变'\n- 旧系统（马车/传统加密）在新范式下可能完全失效",
  "hint": "这个话题超出我的知识范围，以下基于类比推导，需要你验证",
  "source": "ai_analogy",
  "confidence": "low",
  "reevaluate": false
}
```

**验收标准：**
- ✅ 类比必须合理（不是牵强附会）
- ✅ 明确标注是类比推导
- ✅ hint 提示用户验证
- ✅ reevaluate = false

---

### 3.5 L4（知识空白）

**输出物：** 逻辑脚手架（空框架）

**格式要求：**
```json
{
  "item": "缺失项名称",
  "knowledge_level": "L4",
  "framework": {
    "dimensions": [
      {"name": "维度 1", "hint": "提示 1"},
      {"name": "维度 2", "hint": "提示 2"}
    ]
  },
  "hint": "这个话题超出我的知识范围，建议你先提供相关资料",
  "source": "ai_framework",
  "confidence": "low",
  "reevaluate": false
}
```

**示例：**
```json
{
  "item": "公司内部系统 Chronos 的依赖管理",
  "knowledge_level": "L4",
  "framework": {
    "dimensions": [
      {"name": "依赖类型", "hint": "静态依赖 vs 动态依赖？"},
      {"name": "依赖解析", "hint": "如何检测循环依赖？"},
      {"name": "版本管理", "hint": "上游变更如何通知下游？"}
    ]
  },
  "hint": "这个话题超出我的知识范围，建议你先提供相关资料",
  "source": "ai_framework",
  "confidence": "low",
  "reevaluate": false
}
```

**验收标准：**
- ✅ 框架维度合理（不是瞎编）
- ✅ hint 建议用户提供资料
- ✅ 不包含任何具体内容
- ✅ reevaluate = false

---

## 四、降级触发条件

### 4.1 自动触发（系统判断）

| 触发条件 | 降级级别 | 示例 |
|---------|---------|------|
| AI 能直接补充 + 有具体案例 | L0 | 用户说"RAG"→ AI 知道 RAG 原理 |
| AI 知道通用模式 + 无具体案例 | L1 | 用户说"性能优化"→ AI 知道通用优化模式 |
| AI 不能补充 + 能提问 | L2 | 用户说"系统很慢"→ AI 问"哪里慢？" |
| AI 只能类比 | L3 | 用户说"量子计算"→ AI 用类比 |
| AI 完全不懂 | L4 | 用户说"Chronos 系统"→ AI 不知道 |

### 4.2 手动触发（用户选择）

**场景：** 用户对 AI 补充不满意，手动点击"重新补充"

**处理逻辑：**
1. 记录用户不满意的项
2. **强制降级一级**（L0→L1, L1→L2, L2→L3, L3→L4）
   - 注意：手动降级是"强制指定级别"，不是重新评估
3. 重新输出
4. 最多降级 2 次（防止无限循环）

**边界条件：**
- **L4 时用户不满意** → 直接提示"建议手动输入"，不再降级
- 降级次数已达 2 次 → 提示"AI 知识有限，建议你手动补充"

**示例：**
```
用户：这个补充不对（L0）
系统：强制降级到 L1，输出通用模式 + 缺口标注
用户：还是不对（L1）
系统：强制降级到 L2，输出结构化问题（已达 2 次上限）
用户：还是不对（L2）
系统：提示"AI 知识有限，建议你手动补充"，不再降级
```

---

## 五、Fallback 机制

### 5.1 降级失败处理

| 失败场景 | Fallback 策略 |
|---------|-------------|
| L0 补充后重新评估失败 | 降级到 L1，标注缺口 |
| L1 补充后重新评估失败 | 降级到 L2，输出问题 |
| L2 问题用户无法回答 | 降级到 L3，输出类比 |
| L3 类比用户不认可 | 降级到 L4，输出框架 |
| L4 框架用户仍不满意 | 停止降级，建议手动输入 |

### 5.2 降级次数限制

**规则：** 单个缺失项最多降级 2 次

**理由：**
- 防止无限循环
- 避免用户体验恶化
- 2 次降级后，AI 已经承认知识不足，继续降级无意义

**实现：**
```python
max_degradation = 2
current_degradation = item.get('degradation_count', 0)

if current_degradation >= max_degradation:
    return {
        'status': 'max_degradation_reached',
        'hint': '这个话题 AI 知识有限，建议你手动补充',
        'allow_manual_input': True
    }
```

### 5.3 异常处理

| 异常 | 处理方式 |
|------|---------|
| LLM 评估超时 | 默认 L1，输出通用模式 |
| LLM 输出格式错误 | 后端兜底，填充默认字段 |
| 知识级别判断矛盾 | 取较低级别（宁可降级，不要升级） |
| 用户连续点击补充 | 限制频率（10 秒内只能点 1 次） |

---

## 六、后端实现伪代码

### 6.1 知识评估函数

```python
async def assess_knowledge_level(item: dict, user_input: str) -> str:
    """
    评估 AI 对话题的知识覆盖度
    
    Args:
        item: 缺失项字典
        user_input: 用户原始输入
    
    Returns:
        "L0" | "L1" | "L2" | "L3" | "L4"
    """
    prompt = f"""
请评估你对这个话题的知识覆盖度：

话题：{item['topic']}
用户输入：{user_input}

【判断流程】
1. 问自己：我能直接补充具体内容吗？
   - 能 → 继续问：我补充的内容有具体案例/数据支撑吗？
     - 有 → L0
     - 没有 → L1
   - 不能 → 继续问：我能用类比或框架帮助用户吗？
     - 能 → L3
     - 不能 → L4

2. 特殊情况：
   - 用户输入包含具体技术术语，且你知道 → 至少 L1
   - 用户输入包含具体数据，且你能解释 → 至少 L0
   - 用户输入是模糊描述 → 最多 L2
   - 如果你需要靠类比才能理解 → L3
   - 如果你完全不知道用户在说什么 → L4

【输出格式】
knowledge_level: "L0/L1/L2/L3/L4"
reason: "简短说明判断依据"
"""
    
    try:
        response = await call_llm(prompt, timeout=10)
        result = parse_knowledge_level(response)
        
        # 安全兜底：宁可降级，不要升级
        if result not in ['L0', 'L1', 'L2', 'L3', 'L4']:
            return 'L1'
        
        return result
    except Exception as e:
        logger.warning(f"知识评估失败：{e}")
        return 'L1'  # 默认降级到 L1
```

### 6.2 降级链主函数

```python
async def run_degradation_chain(item: dict, user_input: str) -> dict:
    """
    执行降级链逻辑
    
    Returns:
        补充结果字典（包含 knowledge_level, content/questions/analogy/framework 等）
    """
    # 1. 评估知识覆盖度
    knowledge_level = await assess_knowledge_level(item, user_input)
    
    # 2. 根据级别选择策略
    if knowledge_level == 'L0':
        content = await generate_supplement(item)
        return {
            'item': item,
            'knowledge_level': 'L0',
            'content': content,
            'reevaluate': True,
            'confidence': 'high',
            'source': 'user_content'
        }
    
    elif knowledge_level == 'L1':
        content = await generate_supplement(item)
        gap_hint = await generate_gap_hint(item)
        return {
            'item': item,
            'knowledge_level': 'L1',
            'content': content,
            'gap_hint': gap_hint,
            'reevaluate': True,
            'confidence': 'medium',
            'source': 'general_knowledge'
        }
    
    elif knowledge_level == 'L2':
        questions = await generate_structured_questions(item)
        return {
            'item': item,
            'knowledge_level': 'L2',
            'questions': questions,
            'hint': '这个话题我的知识有限，以下基于通用模式推导',
            'reevaluate': False,
            'confidence': 'low',
            'source': 'ai_inference'
        }
    
    elif knowledge_level == 'L3':
        analogy = await generate_analogy(item)
        return {
            'item': item,
            'knowledge_level': 'L3',
            'analogy': analogy,
            'hint': '这个话题超出我的知识范围，以下基于类比推导',
            'reevaluate': False,
            'confidence': 'low',
            'source': 'ai_analogy'
        }
    
    else:  # L4
        framework = await generate_framework(item)
        return {
            'item': item,
            'knowledge_level': 'L4',
            'framework': framework,
            'hint': '这个话题超出我的知识范围，建议你先提供相关资料',
            'reevaluate': False,
            'confidence': 'low',
            'source': 'ai_framework'
        }
```

### 6.3 字段兜底函数

```python
def sanitize_supplement_result(result: dict) -> dict:
    """
    后端兜底：确保返回格式始终正确
    """
    # knowledge_level 必填
    if 'knowledge_level' not in result:
        result['knowledge_level'] = 'L1'
    
    # reevaluate 根据级别设置
    if 'reevaluate' not in result:
        result['reevaluate'] = result['knowledge_level'] in ['L0', 'L1']
    
    # confidence 默认
    result.setdefault('confidence', 'medium')
    
    # source 默认
    result.setdefault('source', 'user_implied')
    
    # 清理多余字段
    allowed_fields = [
        'item', 'knowledge_level', 'content', 'questions', 
        'analogy', 'framework', 'hint', 'gap_hint', 
        'reevaluate', 'confidence', 'source', 'evidence_quote'
    ]
    result = {k: v for k, v in result.items() if k in allowed_fields}
    
    return result
```

---

## 七、验收标准

### 7.1 功能验收

| 测试项 | 预期结果 | 验证方法 |
|--------|---------|---------|
| L0 内容补充 | 返回具体内容 + 案例/数据 | 人工检查内容质量 |
| L1 通用模式 | 返回通用模式 + 缺口标注 | 检查 gap_hint 字段 |
| L2 结构化问题 | 返回 3-5 个具体问题 | 检查问题是否有引导性 |
| L3 类比推导 | 返回合理类比 | 检查类比是否牵强 |
| L4 逻辑框架 | 返回空框架 + 维度 | 检查框架是否合理 |
| 重新评估逻辑 | L0/L1 重新评估，L2/L3/L4 不评估 | 检查 API 调用日志 |
| 降级次数限制 | 最多降级 2 次 | 模拟用户连续点击 |

### 7.2 性能验收

| 指标 | 要求 | 验证方法 |
|------|------|---------|
| 知识评估耗时 | < 3 秒 | 压测 |
| 补充生成耗时 | < 10 秒 | 压测 |
| 并发支持 | 10 个 session 同时补充 | 压测 |
| 错误率 | < 1% | 监控日志 |

### 7.3 质量验收

| 指标 | 要求 | 验证方法 |
|------|------|---------|
| L0 准确率 | > 90% | 随机抽取 100 个 L0 补充，由 2 人独立评分，一致性 > 80% |
| 降级合理性 | > 85% | 随机抽取 100 个降级案例，由 2 人独立评分，一致性 > 80% |
| 用户满意度 | > 4.0/5.0 | A/B 测试问卷（1-5 分） |
| 补充后问题减少率 | > 70% | 数据统计（补充前后缺失项数量对比） |

---

## 八、文档维护

**每次迭代后更新：**
- [ ] 级别定义调整
- [ ] 输出格式变化
- [ ] Fallback 机制优化
- [ ] 验收标准更新

**文档位置：** `/home/admin/.openclaw/workspace/behavior_recorder_service/archgen/降级链 (Chain) 实现规范.md`

**关联文档：**
- `内容补充架构设计.md` - 整体架构设计
- `知识评估 (AI-Assess)API 设计.md` - API 接口定义
- `前端交互流程图.md` - 前端展示规范

---

_这份文档是降级链实现的详细规范，TRAE 实施时严格按此执行。_
