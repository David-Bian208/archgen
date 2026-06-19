# A/B 测试与数据埋点方案 v1.0

**版本：** v1.0  
**创建时间：** 2026-06-19  
**作者：** 战舰  
**状态：** 📋 设计阶段，待实施  
**关联文档：** `内容补充架构设计.md`、`降级链 (Chain) 实现规范.md`

---

## 一、测试目标

### 1.1 核心假设

> **假设：** 如果 AI 在 L2/L3 时明确告知用户"我的知识有限"，用户满意度会显著提升。

### 1.2 验证目标

| 目标 | 指标 | 预期提升 |
|------|------|---------|
| 提升用户信任度 | 满意度评分 > 4.0/5.0 | +20% |
| 降低补充后问题数量 | 补充后问题减少率 > 70% | +15% |
| 提高补充完成率 | 完成补充流程的比例 > 80% | +10% |
| 降低跳过率 | 跳过补充步骤的比例 < 20% | -10% |

### 1.3 测试范围（第一期）

**核心原则：一次只测试 1 个变量，避免混淆结果**

| 期数 | 测试变量 | 测试组 | 对照组 | 样本量 | 周期 |
|------|---------|-------|-------|--------|------|
| **第一期** | 降级提示 Alert | 显示 | 不显示 | 每组 64 次 | 7-14 天 |
| 第二期（待定） | 知识级别标签 | 显示 | 不显示 | 每组 64 次 | 7-14 天 |
| 第三期（待定） | 条件化重新评估 | 启用 | 不启用 | 每组 64 次 | 7-14 天 |

**说明：**
- 第一期只测试"降级提示 Alert"
- 其他两个变量（标签、重新评估）在两组中保持一致
- 第二期、第三期根据第一期结果决定是否执行

---

## 二、实验设计

### 2.1 A/B 分组策略

| 组别 | 名称 | 处理方式 | 预期 |
|------|------|---------|------|
| **A 组** | 对照组 | L2/L3 时直接给结构化提问/类比，**无提示** | 用户困惑"AI 为什么不给具体内容" |
| **B 组** | 实验组 | L2/L3 时先告知"知识有限"，**再给结构化提问/类比** | 用户理解 AI 的局限，满意度更高 |

### 2.2 分组实现

```python
# 后端分组逻辑
import hashlib

def get_ab_group(session_id: str) -> str:
    """
    根据 session_id 哈希分配 A/B 组
    
    Returns:
        "A" | "B"
    """
    hash_value = int(hashlib.md5(session_id.encode()).hexdigest(), 16)
    return "A" if hash_value % 2 == 0 else "B"

# 使用示例
group = get_ab_group(session_id)
if group == "B":
    # 实验组：显示降级提示
    supplement['show_alert'] = True
else:
    # 对照组：不显示降级提示
    supplement['show_alert'] = False
```

### 2.3 前端分组处理

```vue
<script setup>
const abGroup = ref('A')

onMounted(async () => {
  // 从后端获取分组
  const result = await api.getAbGroup(sessionId)
  abGroup.value = result.data.group
})

const showAlert = computed(() => {
  // 实验组显示 Alert，对照组不显示
  return abGroup.value === 'B' && ['L2', 'L3', 'L4'].includes(knowledgeLevel.value)
})
</script>
```

---

## 三、数据埋点

### 3.1 关键事件

| 事件名 | 触发时机 | 必填字段 | 可选字段 |
|--------|---------|---------|---------|
| `supplement_start` | 用户点击"AI 智能补充" | session_id, step, missing_items_count | - |
| `supplement_complete` | 补充完成（API 返回） | session_id, duration_ms, items_count | ab_group |
| `supplement_confirm` | 用户点击"确认" | session_id, item_id, knowledge_level | ab_group |
| `supplement_skip` | 用户点击"跳过" | session_id, item_id, knowledge_level | ab_group, skip_reason |
| `supplement_retry` | 用户点击"重新补充" | session_id, item_id, degradation_count | ab_group |
| `supplement_error` | 补充失败 | session_id, error_code, error_message | ab_group |
| `reevaluate_trigger` | 触发重新评估 | session_id, items_count, knowledge_levels | ab_group |
| `step_navigation` | 步骤跳转 | session_id, from_step, to_step | trigger |

### 3.2 事件格式

```json
{
  "event": "supplement_complete",
  "session_id": "abc123",
  "timestamp": "2026-06-19T10:00:00Z",
  "properties": {
    "duration_ms": 2500,
    "items_count": 3,
    "knowledge_levels": ["L0", "L1", "L2"],
    "ab_group": "B",
    "show_alert": true
  },
  "user": {
    "user_id": "user_456",
    "device": "desktop",
    "browser": "Chrome"
  }
}
```

### 3.3 埋点实现（前端）

```vue
<script setup>
import { track } from '@/utils/analytics'

// 补充开始
const startSupplement = async () => {
  track('supplement_start', {
    session_id: sessionId.value,
    step: 4,
    missing_items_count: missingItems.value.length
  })
  
  supplementState.value = 'loading'
  // ...
}

// 补充完成
const handleSupplementComplete = (result) => {
  track('supplement_complete', {
    session_id: sessionId.value,
    duration_ms: result.metrics.duration_ms,
    items_count: result.data.supplements.length,
    knowledge_levels: result.data.supplements.map(s => s.knowledge_level),
    ab_group: result.data.ab_group
  })
  
  supplementResults.value = result.data.supplements
  supplementState.value = 'showing'
}

// 用户确认
const confirmSupplement = async () => {
  supplementResults.value.forEach(item => {
    track('supplement_confirm', {
      session_id: sessionId.value,
      item_id: item.id,
      knowledge_level: item.knowledge_level,
      ab_group: item.ab_group
    })
  })
  
  await api.confirmSupplement(sessionId.value, supplementResults.value)
  // ...
}

// 用户跳过
const skipSupplement = async () => {
  track('supplement_skip', {
    session_id: sessionId.value,
    item_id: 'all',
    knowledge_level: 'N/A',
    skip_reason: 'user_choice'
  })
  
  await api.skipSupplement(sessionId.value)
  // ...
}

// 重新补充
const retrySupplement = async () => {
  track('supplement_retry', {
    session_id: sessionId.value,
    item_id: currentItem.value.id,
    degradation_count: degradationCount.value
  })
  
  // ...
}
</script>
```

### 3.4 埋点实现（后端）

```python
# 后端埋点装饰器
def track_event(event_name: str):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                
                # 异步发送埋点事件（不阻塞主流程）
                asyncio.create_task(send_analytics_event(
                    event=event_name,
                    properties={
                        'duration_ms': duration_ms,
                        **kwargs
                    }
                ))
                
                return result
            except Exception as e:
                # 错误埋点
                asyncio.create_task(send_analytics_event(
                    event='supplement_error',
                    properties={
                        'error_code': 500,
                        'error_message': str(e),
                        **kwargs
                    }
                ))
                raise
        return wrapper
    return decorator

# 使用示例
@track_event('supplement_complete')
async def ai_supplement(session_id: str, missing_items: list, ab_group: str):
    # ...
```

---

## 四、关键指标定义

### 4.1 核心指标

| 指标 | 定义 | 计算公式 | 目标值 |
|------|------|---------|--------|
| **补充完成率** | 用户完成补充流程的比例 | 完成次数 / 总尝试次数 | > 80% |
| **补充后问题减少率** | 补充后缺失项减少的比例 | (补充前 - 补充后) / 补充前 | > 70% |
| **用户满意度评分** | 用户对补充质量的评分（1-5 分） | 平均分 | > 4.0 |
| **跳过率** | 用户跳过补充步骤的比例 | 跳过次数 / 总尝试次数 | < 20% |
| **重新补充率** | 用户点击重新补充的比例 | 重新补充次数 / 总尝试次数 | < 30% |

### 4.2 辅助指标

| 指标 | 定义 | 计算公式 | 说明 |
|------|------|---------|------|
| **L0 比例** | L0 级别补充的占比 | L0 次数 / 总补充次数 | 反映 AI 知识充足率 |
| **L2/L3 比例** | L2/L3 级别补充的占比 | (L2+L3) 次数 / 总补充次数 | 反映 AI 知识不足率 |
| **平均补充耗时** | 补充 API 的平均耗时 | 总耗时 / 总次数 | 反映性能 |
| **错误率** | 补充失败的比例 | 失败次数 / 总尝试次数 | 反映稳定性 |
| **降级触发率** | 触发降级的比例 | 降级次数 / 总补充次数 | 反映降级链使用情况 |

### 4.3 指标计算 SQL

```sql
-- 补充完成率
SELECT 
    COUNT(CASE WHEN status = 'completed' THEN 1 END) * 1.0 / COUNT(*) AS completion_rate
FROM supplement_events
WHERE date = '2026-06-19'

-- 补充后问题减少率
SELECT 
    AVG((before_count - after_count) * 1.0 / before_count) AS reduction_rate
FROM supplement_sessions
WHERE date = '2026-06-19'

-- 用户满意度评分
SELECT 
    AVG(rating) AS avg_rating
FROM supplement_feedback
WHERE date = '2026-06-19'

-- A/B 组对比
SELECT 
    ab_group,
    COUNT(*) AS total,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) * 1.0 / COUNT(*) AS completion_rate,
    AVG(rating) AS avg_rating
FROM supplement_events
WHERE date = '2026-06-19'
GROUP BY ab_group
```

---

## 五、数据看板

### 5.1 实时看板

**更新频率：** 每分钟

**核心指标卡片：**
```
┌─────────────────────────────────────────────────────────┐
│  今日补充次数：128    完成率：85%    满意度：4.2/5.0    │
└─────────────────────────────────────────────────────────┘

┌──────────────────┐  ┌──────────────────┐
│  A 组 (对照组)      │  │  B 组 (实验组)      │
│  完成率：82%       │  │  完成率：88%       │
│  满意度：4.0       │  │  满意度：4.4       │
│  跳过率：22%       │  │  跳过率：15%       │
└──────────────────┘  └──────────────────┘

┌─────────────────────────────────────────────────────────┐
│  知识级别分布                                             │
│  L0: 45%  ████████████████████████████████████          │
│  L1: 30%  ██████████████████████████                    │
│  L2: 15%  ██████████████                                │
│  L3: 8%   ███████                                       │
│  L4: 2%   ██                                            │
└─────────────────────────────────────────────────────────┘
```

### 5.2 趋势图表

**补充完成率趋势（7 天）：**
```
日期      A 组    B 组
06-13    78%    80%
06-14    80%    83%
06-15    79%    85%
06-16    81%    86%
06-17    82%    87%
06-18    80%    88%
06-19    82%    88%
```

**满意度评分趋势（7 天）：**
```
日期      A 组    B 组
06-13    3.8    4.0
06-14    3.9    4.1
06-15    3.8    4.2
06-16    4.0    4.3
06-17    3.9    4.3
06-18    4.0    4.4
06-19    4.0    4.4
```

---

## 六、统计显著性检验

### 6.1 检验方法

**使用：双样本 t 检验（Two-sample t-test）**

**原假设 H0：** A 组和 B 组的满意度评分无显著差异

**备择假设 H1：** A 组和 B 组的满意度评分有显著差异

### 6.2 显著性水平

| 指标 | 显著性水平 (α) | 说明 |
|------|--------------|------|
| 满意度评分 | 0.05 | 95% 置信度 |
| 完成率 | 0.05 | 95% 置信度 |
| 跳过率 | 0.05 | 95% 置信度 |

### 6.3 检验实现（Python）

```python
from scipy import stats

def ab_test_significance(group_a, group_b, alpha=0.05):
    """
    A/B 测试显著性检验
    
    Args:
        group_a: A 组数据列表
        group_b: B 组数据列表
        alpha: 显著性水平
    
    Returns:
        dict: {
            't_statistic': float,
            'p_value': float,
            'significant': bool,
            'confidence': float
        }
    """
    t_stat, p_value = stats.ttest_ind(group_a, group_b)
    
    return {
        't_statistic': t_stat,
        'p_value': p_value,
        'significant': p_value < alpha,
        'confidence': 1 - p_value
    }

# 使用示例
group_a_ratings = [4.0, 3.8, 4.2, 3.9, 4.1]  # A 组满意度
group_b_ratings = [4.4, 4.5, 4.3, 4.6, 4.4]  # B 组满意度

result = ab_test_significance(group_a_ratings, group_b_ratings)

if result['significant']:
    print(f"✅ 差异显著 (p={result['p_value']:.4f}, 置信度={result['confidence']:.2%})")
else:
    print(f"❌ 差异不显著 (p={result['p_value']:.4f})")
```

### 6.4 样本量计算

```python
from statsmodels.stats.power import TTestIndPower

def calculate_sample_size(effect_size=0.5, alpha=0.05, power=0.8):
    """
    计算所需样本量
    
    Args:
        effect_size: 效应量（Cohen's d），0.5 为中等效应
        alpha: 显著性水平
        power: 统计功效（1-β）
    
    Returns:
        int: 每组所需样本量
    """
    analysis = TTestIndPower()
    sample_size = analysis.solve_power(effect_size=effect_size, alpha=alpha, power=power)
    return int(sample_size)

# 使用示例
sample_size = calculate_sample_size(effect_size=0.5, alpha=0.05, power=0.8)
print(f"每组需要至少 {sample_size} 个样本")  # 输出：每组需要至少 64 个样本
```

---

## 七、测试周期

### 7.1 时间安排

| 阶段 | 时间 | 内容 |
|------|------|------|
| **准备期** | 2026-06-19 ~ 2026-06-20 | 埋点开发、看板搭建 |
| **预热期** | 2026-06-21 | 小流量测试（10%） |
| **正式期** | 2026-06-22 ~ 2026-07-05 | 全流量测试（50%/50%），**14 天** |
| **分析期** | 2026-07-06 | 数据统计、显著性检验 |
| **决策期** | 2026-07-07 | 根据结果决定是否全量 |

**说明：**
- 正式期从 7 天延长到 14 天，确保收集足够样本
- 如果每天>20 个用户使用补充功能，可缩短到 7 天
- 如果每天<5 个用户，需延长到 21 天

### 7.2 里程碑

| 日期 | 里程碑 | 验收标准 |
|------|-------|---------|
| 2026-06-19 | 埋点开发完成 | 所有事件正常上报 |
| 2026-06-20 | 看板搭建完成 | 核心指标正常显示 |
| 2026-06-21 | 正式测试启动 | A/B 组各 50% 流量 |
| 2026-06-27 | 测试结束 | 每组至少 50 个样本 |
| 2026-06-28 | 分析报告完成 | 显著性检验完成 |
| 2026-06-29 | 决策会议 | 决定是否全量 |

---

## 八、决策规则

### 8.1 全量标准

**满足以下所有条件则全量上线：**

1. ✅ 满意度评分提升 > 10%（B 组 vs A 组）
2. ✅ p 值 < 0.05（统计显著）
3. ✅ 样本量 ≥ 50（每组）
4. ✅ 无负面反馈（如用户投诉）

### 8.2 迭代标准

**满足以下任意条件则迭代优化：**

1. ❌ 满意度评分提升 < 5%
2. ❌ p 值 > 0.05（不显著）
3. ❌ 样本量不足
4. ❌ 有负面反馈

### 8.3 回滚标准

**满足以下任意条件则立即回滚：**

1. 🔴 满意度评分下降 > 5%
2. 🔴 错误率 > 10%
3. 🔴 用户投诉 > 5 次
4. 🔴 系统性能下降 > 50%

---

## 九、风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|---------|
| 样本量不足 | 中 | 高 | 延长测试周期，增加流量 |
| 埋点数据丢失 | 低 | 高 | 本地缓存 + 重试机制 |
| A/B 分组不均 | 低 | 中 | 定期检查分组比例 |
| 用户感知差异 | 低 | 中 | 不告知用户 A/B 测试 |
| 统计结论错误 | 中 | 高 | 多重检验校正，人工复核 |

---

## 十、文档维护

**每次迭代后更新：**
- [ ] 埋点事件变化
- [ ] 指标定义调整
- [ ] 看板样式更新
- [ ] 测试结果记录

**文档位置：** `/home/admin/.openclaw/workspace/behavior_recorder_service/archgen/A_B 测试与数据埋点方案.md`

**关联文档：**
- `内容补充架构设计.md` - 整体架构设计
- `降级链 (Chain) 实现规范.md` - 降级实现细节
- `知识评估 (AI-Assess)API 设计.md` - API 接口定义
- `前端交互流程图.md` - 前端展示规范

---

_这份文档是 A/B 测试与数据埋点的详细方案，TRAE 实施时严格按此执行。_
