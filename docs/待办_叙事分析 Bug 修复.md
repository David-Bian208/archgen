# 待办：叙事分析 Bug 修复（P0 紧急）

**优先级：** P0（阻塞性 Bug）  
**分配给：** TRAE（小治）  
**时间：** 2026-04-08 12:33  
**错误信息：** `TypeError: text.replace is not a function`

---

## 问题描述

**现象：**
- 前端页面加载报告时报错
- 控制台错误：`formatNarrative App.vue:731:10`
- 页面无法正常显示

**根因：**
- `formatNarrative()` 方法期望接收字符串
- 但实际接收的是对象（`narrative_analysis` 是对象）

**后端数据结构：**
```python
# structured_assessor_v4.py
"narrative_analysis": {
  "narrative_summary": "整合以上所有内容的连贯叙事（200-300 字）",
  "primary_attribution": "主要归因",
  ...
}
```

**前端错误代码：**
```vue
<div v-html="formatNarrative(insightReport.narrative_analysis)"></div>
```

**应该改为：**
```vue
<div v-html="formatNarrative(insightReport.narrative_analysis.narrative_summary)"></div>
```

---

## 修复方案

### 方案 A：修改前端数据访问（推荐）

**文件：** `frontend/App.vue`

**修改位置：** line 110 左右（叙事分析区块）

**修改前：**
```vue
<div v-if="insightReport.narrative_analysis" class="narrative-section">
  <h3>📖 叙事分析</h3>
  <div class="narrative-content" v-html="formatNarrative(insightReport.narrative_analysis)"></div>
</div>
```

**修改后：**
```vue
<div v-if="insightReport.narrative_analysis?.narrative_summary" class="narrative-section">
  <h3>📖 叙事分析</h3>
  <div class="narrative-content" v-html="formatNarrative(insightReport.narrative_analysis.narrative_summary)"></div>
</div>
```

---

### 方案 B：增强 formatNarrative 方法（防御性编程）

**文件：** `frontend/App.vue`

**修改 `formatNarrative()` 方法：**

**修改前：**
```javascript
formatNarrative(text) {
  if (!text) return ''
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br/>')
}
```

**修改后：**
```javascript
formatNarrative(text) {
  if (!text) return ''
  
  // 如果是对象，提取 narrative_summary 字段
  if (typeof text === 'object' && text !== null) {
    text = text.narrative_summary || text.summary || JSON.stringify(text)
  }
  
  if (typeof text !== 'string') return ''
  
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br/>')
}
```

---

## 推荐方案

**同时实施方案 A + B：**
- 方案 A：正确访问数据结构
- 方案 B：防御性编程，避免未来类似问题

---

## 验收标准

- [ ] 页面不再报错
- [ ] 叙事分析正常显示
- [ ] 格式正确（粗体、斜体、换行）
- [ ] 其他报告部分不受影响

---

## 测试步骤

```bash
# 1. 重启前端（热更新可能不生效）
cd /home/admin/.openclaw/workspace/behavior_recorder_service/frontend
pkill -9 -f "node.*vite"
npm run dev &

# 2. 浏览器访问
http://localhost:5173

# 3. 提交测试
输入："叫他不理，不看人"

# 4. 验证
- 控制台无报错
- 页面显示"📖 叙事分析"区块
- 内容格式正确
```

---

## 相关文件

- `frontend/App.vue` - 需要修复的文件
- `app/agents/structured_assessor_v4.py` - 后端数据结构

---

**完成后通知：** @战舰  
**优先级：** P0（阻塞性 Bug，立即修复）
