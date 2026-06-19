# 知识评估 (AI-Assess) API 设计 v1.0

**版本：** v1.0  
**创建时间：** 2026-06-19  
**作者：** 战舰  
**状态：** 📋 设计阶段，待实施  
**关联文档：** `内容补充架构设计.md`、`降级链 (Chain) 实现规范.md`

---

## 一、API 概述

### 1.1 功能定位

**知识评估 API** 用于在内容补充环节，让 AI 自评对话题的知识覆盖度（L0-L4），并根据级别选择合适的输出策略。

**核心价值：**
- 避免 AI 硬编内容
- 提升用户对 AI 输出的信任度
- 减少"补充后问题变多"的死循环

### 1.2 使用场景

| 场景 | 调用时机 | 调用方 |
|------|---------|-------|
| Step 4 补充环节 | 用户点击"AI 智能补充" | 前端 → 后端 → LLM |
| Step 2 评估环节（P2） | 完整度评估后 | 前端 → 后端 → LLM |
| 手动重新补充 | 用户对补充不满意 | 前端 → 后端 → LLM |

---

## 二、API 接口定义

### 2.1 知识评估接口

#### 接口信息

| 属性 | 值 |
|------|-----|
| **路径** | `POST /api/v1/assess-knowledge` |
| **认证** | 不需要（session_id 鉴权） |
| **超时** | 15 秒 |
| **重试** | 1 次 |

#### 请求参数

```json
{
  "session_id": "string (必填)",
  "item": {
    "topic": "string (必填，缺失项名称)",
    "context": "string (可选，上下文信息)",
    "user_input": "string (必填，用户原始输入摘要)"
  },
  "options": {
    "force_level": "string (可选，强制指定级别，用于手动降级)",
    "skip_cache": "boolean (可选，默认 false，是否跳过缓存)"
  }
}
```

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `session_id` | string | ✅ | 会话 ID，用于追踪和存储 |
| `item.topic` | string | ✅ | 缺失项名称（如"具体应用场景"） |
| `item.context` | string | ❌ | 上下文信息（如当前方向、框架） |
| `item.user_input` | string | ✅ | 用户原始输入摘要（200-300 字） |
| `options.force_level` | string | ❌ | 强制指定级别（L0-L4），用于手动降级 |
| `options.skip_cache` | boolean | ❌ | 是否跳过缓存（默认 false） |

#### 响应格式

**成功响应（200）：**

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "knowledge_level": "L0",
    "reason": "能直接补充具体内容，且有用户输入中的案例支撑",
    "output": {
      "item": "具体应用场景",
      "knowledge_level": "L0",
      "content": "Vibe Coding 特别适合以下场景：\n1. 快速原型开发...",
      "evidence_quote": "它比传统编程快很多...",
      "source": "user_content",
      "confidence": "high",
      "reevaluate": true
    },
    "metrics": {
      "assess_duration_ms": 1250,
      "llm_model": "deepseek-v3.2",
      "cached": false
    }
  }
}
```

**失败响应：**

```json
{
  "code": 400,
  "msg": "参数错误：session_id 不能为空",
  "data": null
}
```

```json
{
  "code": 500,
  "msg": "知识评估失败：LLM 超时",
  "data": {
    "fallback_level": "L1",
    "hint": "知识评估超时，默认降级到 L1"
  }
}
```

#### 错误码定义

| 错误码 | 说明 | 处理方式 |
|--------|------|---------|
| 0 | 成功 | - |
| 400 | 参数错误 | 检查请求参数 |
| 404 | Session 不存在 | 检查 session_id |
| 500 | 服务器错误（LLM 超时/失败） | 降级到 L1，记录日志 |
| 503 | 限流 | 前端提示"请稍后再试" |

---

### 2.2 批量知识评估接口（可选）

#### 接口信息

| 属性 | 值 |
|------|-----|
| **路径** | `POST /api/v1/assess-knowledge-batch` |
| **认证** | 不需要（session_id 鉴权） |
| **超时** | 30 秒 |
| **重试** | 1 次 |

#### 请求参数

```json
{
  "session_id": "string (必填)",
  "items": [
    {
      "topic": "具体应用场景",
      "context": "...",
      "user_input": "..."
    },
    {
      "topic": "技术实现细节",
      "context": "...",
      "user_input": "..."
    }
  ],
  "options": {
    "parallel": "boolean (可选，默认 true，是否并行评估)",
    "skip_cache": "boolean (可选，默认 false)"
  }
}
```

#### 响应格式

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "results": [
      {
        "topic": "具体应用场景",
        "knowledge_level": "L0",
        "output": {...},
        "metrics": {...}
      },
      {
        "topic": "技术实现细节",
        "knowledge_level": "L1",
        "output": {...},
        "metrics": {...}
      }
    ],
    "summary": {
      "total": 2,
      "l0_count": 1,
      "l1_count": 1,
      "l2_count": 0,
      "l3_count": 0,
      "l4_count": 0,
      "total_duration_ms": 2500
    }
  }
}
```

---

## 三、knowledge_level 计算规则

### 3.1 评估 Prompt 模板

```
请评估你对这个话题的知识覆盖度：

【话题】
{topic}

【用户输入】
{user_input}

【上下文】
{context}

【判断流程】
1. 问自己：我能直接补充具体内容吗？
   - 能 → 继续问：我补充的内容有具体案例/数据支撑吗？
     - 有 → L0
     - 没有 → L1
   - 不能 → 继续问：我能用类比或框架帮助用户吗？
     - 能 → L3
     - 不能 → L4

2. 特殊情况：
   - 用户输入包含具体技术术语（如'RAG'、'DAG'），且你知道 → 至少 L1
   - 用户输入包含具体数据（如'40 分钟'、'50+ 上游'），且你能解释 → 至少 L0
   - 用户输入是模糊描述（如'很多'、'有问题'） → 最多 L2
   - 如果你需要靠类比才能理解 → L3
   - 如果你完全不知道用户在说什么 → L4

3. 保守原则：
   - 如果不确定，宁可降级，不要升级
   - L0 和 L1 的界限：有具体案例/数据 = L0，只有通用模式 = L1
   - L2 和 L3 的界限：能提出具体问题 = L2，只能类比 = L3

【输出格式】
请严格按以下 JSON 格式输出：
{
  "knowledge_level": "L0/L1/L2/L3/L4",
  "reason": "简短说明判断依据（50 字以内）",
  "confidence": "high/medium/low"
}
```

### 3.2 级别判定规则

| 级别 | 判定条件（满足任意一条即可） |
|------|---------------------------|
| **L0** | 1. 能引用用户输入中的具体案例/数据<br>2. 能补充具体技术细节（如框架名称、API 端点）<br>3. 能给出具体场景/步骤/流程 |
| **L1** | 1. 知道通用模式，但缺少具体案例<br>2. 能展开框架，但需要用户补充细节<br>3. 用户输入包含术语，AI 知道术语含义 |
| **L2** | 1. 不能直接补充内容<br>2. 能提出 3-5 个结构化问题<br>3. 用户输入模糊，AI 无法确定具体指向 |
| **L3** | 1. 只能用类比推导<br>2. 类比必须明确标注<br>3. 用户输入涉及 AI 知识盲区 |
| **L4** | 1. 完全不知道用户在说什么<br>2. 只能给空框架/维度<br>3. 涉及公司内部系统/私有知识 |

### 3.3 边界情况处理

| 边界情况 | 处理规则 |
|---------|---------|
| AI 部分知道（如知道 RAG 但不知道具体实现） | L1（标注缺口） |
| 用户输入包含多个话题（有的知道有的不知道） | 按最低级别处理 |
| AI 不确定自己是否知道 | 降级到 L2 |
| LLM 输出格式错误 | 后端兜底，默认 L1 |
| LLM 超时 | 降级到 L1，记录日志 |

---

## 四、输出物生成规则

### 4.1 L0 输出生成

**Prompt 模板：**
```
请补充以下内容：

【话题】
{topic}

【用户输入】
{user_input}

【要求】
1. 必须有具体案例/数据/技术细节
2. 能准确引用用户输入中的关键信息
3. 内容要有实质信息，不是空话

【输出格式】
{
  "content": "具体内容",
  "evidence_quote": "引用的用户原话",
  "source": "user_content"
}
```

**验收标准：**
- ✅ 内容有实质信息（>100 字）
- ✅ 有具体案例/数据/技术细节
- ✅ evidence_quote 非空

---

### 4.2 L1 输出生成

**Prompt 模板：**
```
请基于通用模式补充以下内容：

【话题】
{topic}

【用户输入】
{user_input}

【要求】
1. 展开通用模式/框架
2. 明确标注缺口（需要用户补充什么）
3. 不假装知道具体内容

【输出格式】
{
  "content": "基于通用模式的展开内容",
  "gap_hint": "需要你补充：XXX"
}
```

**验收标准：**
- ✅ 内容有通用模式支撑
- ✅ gap_hint 非空且具体
- ✅ 不包含假装知道的内容

---

### 4.3 L2 输出生成

**Prompt 模板：**
```
请针对以下话题提出结构化问题：

【话题】
{topic}

【用户输入】
{user_input}

【要求】
1. 提出 3-5 个具体问题
2. 问题能帮助用户思考
3. 问题要有引导性（不是泛泛而问）

【输出格式】
{
  "questions": [
    "问题 1（引导性说明）",
    "问题 2（引导性说明）",
    "问题 3（引导性说明）"
  ]
}
```

**验收标准：**
- ✅ 问题数量 3-5 个
- ✅ 问题有引导性（带括号说明）
- ✅ 问题能帮助用户思考

---

### 4.4 L3 输出生成

**Prompt 模板：**
```
请针对以下话题进行类比推导：

【话题】
{topic}

【用户输入】
{user_input}

【要求】
1. 用类比的方式解释
2. 类比必须合理（不是牵强附会）
3. 明确标注是类比推导

【输出格式】
{
  "analogy": "类比内容（格式：A ≈ B，然后解释）"
}
```

**验收标准：**
- ✅ 类比合理（不是牵强附会）
- ✅ 格式正确（A ≈ B）
- ✅ 有解释说明

---

### 4.5 L4 输出生成

**Prompt 模板：**
```
请针对以下话题给出逻辑框架：

【话题】
{topic}

【用户输入】
{user_input}

【要求】
1. 给出 3-5 个思考维度
2. 每个维度有简短提示
3. 不包含任何具体内容

【输出格式】
{
  "framework": {
    "dimensions": [
      {"name": "维度 1", "hint": "提示 1"},
      {"name": "维度 2", "hint": "提示 2"},
      {"name": "维度 3", "hint": "提示 3"}
    ]
  }
}
```

**验收标准：**
- ✅ 维度数量 3-5 个
- ✅ 每个维度有 hint
- ✅ 不包含具体内容

---

## 五、条件化重新评估逻辑

### 5.1 重新评估规则

| 知识级别 | 是否重新评估 | 理由 |
|---------|------------|------|
| **L0** | ✅ 是 | 验证补充内容质量 |
| **L1** | ✅ 是 | 验证缺口标注是否准确 |
| **L2** | ❌ 否 | 输出的是问题，不需要评估 |
| **L3** | ❌ 否 | 输出的是类比，不需要评估 |
| **L4** | ❌ 否 | 输出的是框架，不需要评估 |

### 5.2 重新评估触发条件

**触发条件（必须同时满足）：**
1. 知识级别为 L0 或 L1
2. 补充内容已保存
3. 用户未跳过补充

**不触发条件（满足任意一条即可）：**
1. 知识级别为 L2/L3/L4
2. 用户跳过补充
3. 补充失败
4. 降级次数已达上限（2 次）

### 5.3 重新评估实现

```python
async def conditional_reevaluate(session_id: str, supplements: list) -> bool:
    """
    条件化重新评估
    
    Returns:
        bool: 是否执行了重新评估
    """
    # 筛选需要重新评估的项
    items_to_reevaluate = [
        s for s in supplements 
        if s.get('knowledge_level') in ['L0', 'L1'] 
        and s.get('reevaluate', True)
    ]
    
    if not items_to_reevaluate:
        logger.info(f"[Session {session_id}] 无需重新评估（无 L0/L1 项）")
        return False
    
    # 执行完整评估
    try:
        await run_full_assessment(session_id)
        logger.info(f"[Session {session_id}] 重新评估完成（{len(items_to_reevaluate)} 项）")
        return True
    except Exception as e:
        logger.error(f"[Session {session_id}] 重新评估失败：{e}")
        return False
```

---

## 六、缓存策略

### 6.1 缓存键设计

```
cache_key = "assess:{session_id}:{topic}:{user_input_hash}"
```

**说明：**
- `session_id`: 会话 ID
- `topic`: 缺失项名称
- `user_input_hash`: 用户输入的 MD5 哈希（前 8 位）

### 6.2 缓存过期策略

| 缓存类型 | 过期时间 | 说明 |
|---------|---------|------|
| L0 评估结果 | 24 小时 | 知识充足，结果稳定 |
| L1 评估结果 | 12 小时 | 通用模式，相对稳定 |
| L2/L3/L4 评估结果 | 不缓存 | 知识不足，每次重新评估 |

### 6.3 缓存命中处理

```python
async def get_cached_assessment(session_id: str, topic: str, user_input: str) -> dict | None:
    """
    获取缓存的评估结果
    
    Returns:
        缓存结果或 None
    """
    cache_key = f"assess:{session_id}:{topic}:{md5(user_input)[:8]}"
    cached = await redis.get(cache_key)
    
    if cached:
        logger.debug(f"[Session {session_id}] 缓存命中：{topic}")
        return json.loads(cached)
    
    return None
```

---

## 七、监控与埋点

### 7.1 关键指标

| 指标 | 类型 | 说明 |
|------|------|------|
| `assess_duration_ms` | Histogram | 知识评估耗时 |
| `knowledge_level_distribution` | Counter | 各级别数量分布 |
| `reevaluate_trigger_rate` | Gauge | 重新评估触发率 |
| `cache_hit_rate` | Gauge | 缓存命中率 |
| `error_rate` | Gauge | 错误率 |

### 7.2 埋点事件

```json
{
  "event": "knowledge_assess",
  "session_id": "...",
  "topic": "...",
  "knowledge_level": "L0",
  "duration_ms": 1250,
  "cached": false,
  "reevaluated": true,
  "timestamp": "2026-06-19T10:00:00Z"
}
```

### 7.3 告警规则

| 告警 | 触发条件 | 处理方式 |
|------|---------|---------|
| 评估耗时过长 | P95 > 5 秒 | 检查 LLM 服务 |
| 错误率过高 | > 5% | 检查代码/LLM |
| L0 比例异常 | < 10% 或 > 90% | 检查 Prompt |
| 重新评估失败率 | > 10% | 检查评估逻辑 |

---

## 八、测试用例

### 8.1 单元测试

```python
# 测试 L0 判定
def test_l0_detection():
    result = assess_knowledge_level(
        topic="具体应用场景",
        user_input="Vibe Coding 比传统编程快很多，特别适合快速原型开发"
    )
    assert result['knowledge_level'] == 'L0'
    assert result['output']['content'] is not None
    assert result['output']['reevaluate'] == True

# 测试 L2 判定
def test_l2_detection():
    result = assess_knowledge_level(
        topic="性能优化策略",
        user_input="系统很慢，有问题"
    )
    assert result['knowledge_level'] == 'L2'
    assert len(result['output']['questions']) >= 3
    assert result['output']['reevaluate'] == False

# 测试降级逻辑
def test_degradation():
    result = assess_knowledge_level(
        topic="Chronos 系统",
        user_input="公司内部系统",
        force_level="L4"
    )
    assert result['knowledge_level'] == 'L4'
    assert result['output']['framework'] is not None
```

### 8.2 集成测试

```python
# 测试完整流程
async def test_full_flow():
    session_id = create_session()
    
    # 1. 知识评估
    assess_result = await assess_knowledge(session_id, item)
    
    # 2. 验证返回格式
    assert assess_result['code'] == 0
    assert assess_result['data']['knowledge_level'] in ['L0', 'L1', 'L2', 'L3', 'L4']
    
    # 3. 验证条件化重新评估
    if assess_result['data']['knowledge_level'] in ['L0', 'L1']:
        reevaluate_result = await conditional_reevaluate(session_id, [assess_result['data']['output']])
        assert reevaluate_result == True
    else:
        reevaluate_result = await conditional_reevaluate(session_id, [assess_result['data']['output']])
        assert reevaluate_result == False
```

---

## 九、文档维护

**每次迭代后更新：**
- [ ] 接口参数变化
- [ ] Prompt 调整记录
- [ ] 缓存策略优化
- [ ] 监控指标更新

**文档位置：** `/home/admin/.openclaw/workspace/behavior_recorder_service/archgen/知识评估 (AI-Assess)API 设计.md`

**关联文档：**
- `内容补充架构设计.md` - 整体架构设计
- `降级链 (Chain) 实现规范.md` - 降级实现细节
- `前端交互流程图.md` - 前端展示规范

---

_这份文档是知识评估 API 的详细设计，TRAE 实施时严格按此执行。_
