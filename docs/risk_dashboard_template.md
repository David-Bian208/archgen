# 风险前置看板 - /start 指令增强

**版本：** V6.0.2  
**创建时间：** 2026-04-20  
**目的：** 在每日/start 指令中自动显示今日高风险任务

---

## 📊 风险看板模板

```
🛳️ 战舰晨间简报 - {日期}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 风险前置看板（今日最高风险）

【风险 1】{风险标题}
  任务：{任务 ID}
  执行者：{小治/小美/小测/小强/小文}
  风险等级：🔴 高 / 🟡 中 / 🟢 低
  风险描述：{1 句话描述风险}
  关注点：{需要 DAVID 关注的决策点}

【风险 2】{风险标题}
  ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 今日任务概览

| 任务 ID | 执行者 | 优先级 | 状态 | 预计完成 |
|---------|--------|--------|------|---------|
| {ID}    | {人}   | P0     | 🟡   | HH:MM   |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ 待 DAVID 决策

1. {决策事项 1}
2. {决策事项 2}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 昨日完成

✅ {任务 1} - {执行者}
✅ {任务 2} - {执行者}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🔍 风险关键词识别规则

战舰自动从任务文档中提取高风险关键词：

### 🔴 高风险关键词
- "核心逻辑"
- "重构"
- "首次实现"
- "架构变更"
- "数据库迁移"
- "API 变更"
- "安全相关"
- "性能优化"（>50% 提升目标）

### 🟡 中风险关键词
- "优化"
- "修复 Bug"
- "新增功能"
- "单元测试"

### 🟢 低风险关键词
- "文档"
- "注释"
- "格式化"
- "清理"

---

## 📁 文件位置

- 任务文档目录：`/workspace/TASK_*.md`
- 记忆目录：`/workspace/memory/YYYY-MM-DD.md`
- 输出位置：`/workspace/daily_briefings/YYYY-MM-DD_briefing.md`

---

## 🤖 自动化逻辑

```python
def generate_daily_briefing():
    # 1. 读取今日任务文档
    today_tasks = read_tasks_for_today()
    
    # 2. 识别高风险任务
    high_risk_tasks = []
    for task in today_tasks:
        content = read_task(task)
        if contains_high_risk_keywords(content):
            high_risk_tasks.append(task)
    
    # 3. 读取昨日完成情况
    yesterday_completed = read_memory_yesterday()
    
    # 4. 生成简报
    briefing = render_template(
        high_risk_tasks=high_risk_tasks,
        today_tasks=today_tasks,
        yesterday_completed=yesterday_completed
    )
    
    # 5. 保存到文件
    save_briefing(briefing)
    
    return briefing
```

---

## 📝 使用示例

**输入：** 任务文档 `TASK_V6_FIX_CORE_LOGIC.md`
```markdown
# TASK_V6_FIX_CORE_LOGIC.md
**任务描述：** 重构 multi_agent_orchestrator.py 核心推理逻辑
**优先级：** P0
**执行者：** 小治
```

**输出：** 风险看板条目
```
🔴 风险前置看板

【风险 1】核心逻辑重构
  任务：TASK_V6_FIX_CORE_LOGIC.md
  执行者：小治
  风险等级：🔴 高
  风险描述：重构核心推理引擎，可能影响现有功能
  关注点：需要确认测试覆盖率是否足够
```

---

## ✅ 验收标准

- ✅ 自动识别高风险关键词
- ✅ 生成结构化简报
- ✅ 保存到固定目录
- ✅ 支持手动触发（/start 指令）
- ✅ 性能优秀（<1 秒生成）

---

**版本：** V6.0.2  
**状态：** 🟡 设计中 → 待小治实现
