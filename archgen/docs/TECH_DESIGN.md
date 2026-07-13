# TECH_DESIGN.md — 三列分析工作台 技术设计文档

> Vibe Coding Step 3：技术设计
>
> 技术栈、项目结构、数据模型、关键技术点、API 设计

---

## 一、技术栈

### 1.1 当前技术栈（不变）

| 层级 | 技术 | 版本 |
|------|------|------|
| 前端框架 | Vue 3 (Composition API) | 3.x |
| UI 库 | Arco Design Vue | 2.x |
| 构建工具 | Vite | 5.x |
| 状态管理 | Composable (reactive/ref) | — |
| 后端框架 | FastAPI (Python) | 0.x |
| LLM | DeepSeek V3 (文本) | — |
| OCR | PaddleOCR (离线) | 3.x |
| 实时通信 | SSE (Server-Sent Events) | — |

### 1.2 新增依赖

| 依赖 | 用途 | 安装 |
|------|------|------|
| `paddleocr` | 图片文字提取 | `pip install paddleocr` |

---

## 二、项目结构

### 2.1 目录树（仅标注改动部分）

```
archgen/
├── api.py                              # [改] 新增 4 个端点
├── src/
│   ├── slot_filler.py                  # [改] 素材匹配 + 提纲生成逻辑
│   └── source_tag_processor.py        # [不改] 来源标签已写好
├── docs/
│   ├── RESEARCH.md                     # [新] Step 1
│   ├── PRD.md                          # [新] Step 2
│   ├── TECH_DESIGN.md                  # [新] Step 3 ← 当前文件
│   ├── AGENTS.md                       # [新] Step 4
│   └── 三列分析工作台方案-v4.0.md       # [已有] 完整方案文档
└── frontend/
    └── src/
        ├── views/
        │   └── WorkflowView.vue        # [改] 步骤条 8→5, currentStep 调整
        ├── composables/
        │   └── useStep3_Workbench.js   # [改] 扩展状态+方法
        ├── utils/
        │   └── api.js                  # [改] 新增 4 个 API + SSE 流式
        └── components/
            └── workflow/
                ├── ThreeColumnWorkbench.vue  # [新] 三列主组件
                ├── StreamSlotsPanel.vue      # [新] 阶段1: 流式推理+槽位编辑
                ├── EditPanel.vue             # [新] 阶段3: 右侧编辑面板
                ├── FrameworkWorkbench.vue    # [弃] v3.0 横向表格
                ├── SlotCard.vue              # [弃] v2.1 双栏卡片
                └── StepFramework.vue         # [弃] 框架选择
```

---

## 三、API 设计

### 3.1 新增端点总览

| 方法 | 端点 | 功能 | 类型 |
|------|------|------|------|
| POST | `/slot/generate_slots` | AI 流式推理槽位 | SSE 流 |
| POST | `/slot/match_materials` | 素材池匹配到槽位 | JSON |
| POST | `/slot/batch_fill_v4` | 确认槽位后批量填充（素材+提纲） | JSON |
| POST | `/slot/generate_outline` | 单槽位提纲生成 | JSON |
| POST | `/slot/slot_relations` | 生成槽位间关系图谱 | JSON |
| POST | `/slot/ask_followup` | 追问 AI（编辑面板 / 槽位确认阶段） | JSON |
| POST | `/slot/pre_check_materials` | 素材可行性预检：快速统计槽位素材覆盖度 + AI 替换建议 | JSON |

### 3.2 `POST /api/workflow/slot/generate_slots`

```
功能：流式 SSE 推理，逐行输出分析 + 槽位建议
输入：
{
  "session_id": "xxx",
  "topic": "甜品行业新品市场分析",
  "material_pool_summary": "已准备 3 份素材：行业报告.pdf / 用户评价集 / 网络搜索(2条)"
}

SSE 输出格式：
data: {"type":"thinking","text":"正在理解你的选题..."}

data: {"type":"thinking","text":"核心问题：如何评估新品上市前的市场机会与风险？"}

data: {"type":"slot","slot_key":"slot_1","label":"消费路径分析","description":"用户从注意到购买的全流程触达"}

data: {"type":"slot","slot_key":"slot_2","label":"满意度诊断","description":"现有竞品的评分/口碑/复购分析"}

data: {"type":"done","slots":[
  {"slot_key":"slot_1","label":"消费路径分析","description":"..."},
  {"slot_key":"slot_2","label":"满意度诊断","description":"..."}
]}

实现要点：
- 后端用 StreamingResponse + yield
- 前端用 fetch + ReadableStream reader
- 超时 60s，中断时前端 close reader
```

### 3.3 `POST /api/workflow/slot/match_materials`

```
功能：将素材池按槽位关键词分配
输入：
{
  "session_id": "xxx",
  "confirmed_slots": [
    {"slot_key": "slot_1", "label": "消费路径分析", "description": "..."},
    {"slot_key": "slot_2", "label": "满意度诊断", "description": "..."}
  ]
}

输出：
{
  "slot_materials": {
    "slot_1": [
      {
        "text": "消费者在购买前通常浏览 3-5 个平台...",  // 素材片段
        "source_type": "knowledge_base",
        "source_name": "行业报告.pdf",
        "confidence": 0.92
      }
    ],
    "slot_2": []
  }
}

匹配策略：
1. 从 session 读取 material_pool（Step 2 补充阶段构建的素材池）
2. 对每条素材计算与每个槽位 label+description+keywords 的相关度
3. 相关度 > 0.6 的分配到该槽位（调用 LLM 做分类，非纯关键词）
4. 低于阈值的不分配，保留在通用池
```

### 3.4 `POST /api/workflow/slot/batch_fill_v4`

```
功能：确认槽位后，并行调用素材匹配 + 提纲生成
输入：
{
  "session_id": "xxx",
  "confirmed_slots": [...]
}

处理流程：
for each slot (parallel):
  1. match_materials(slot)  → 素材
  2. generate_outline(slot) → 提纲
  返回: { slot_key, materials, outline }

输出：
{
  "results": {
    "slot_1": {
      "materials": [...],
      "outline": [
        {"point": "当前触达路径分析", "order": 1},
        {"point": "竞品路径对比", "order": 2}
      ]
    },
    "slot_2": {...}
  }
}

性能：多个槽位并行调用 LLM（Python asyncio.gather），4 个槽位约 15-25s
```

### 3.5 `POST /api/workflow/slot/generate_outline`

```
功能：为单个槽位生成提纲要点
输入：
{
  "session_id": "xxx",
  "slot_key": "slot_1",
  "topic": "...",
  "materials": [...],             // 该槽位已匹配的素材
  "writing_plan": "用对比手法"    // 可选：用户写作方案
}

输出：
{
  "outline": [
    {"point": "当前触达路径", "order": 1},
    {"point": "竞品路径对比", "order": 2},
    {"point": "优化建议", "order": 3}
  ]
}

Prompt 约束：
- 3-5 个要点
- 每个要点 20-60 字
- 必须基于素材内容，不编造
- 如果有 writing_plan，遵循其风格要求
```

### 3.6 复用现有端点

| 端点 | 用途 | 状态 |
|------|------|------|
| `POST /slot/upload_source` | 文件/图片上传解析 | ✅ 已有 |
| `POST /slot/slot_fill` | 编辑面板中单槽位 AI 重分析 | ✅ 已有 |
| `session` 读写 | 存储所有槽位数据 | ✅ 已有，加字段 |

### 3.7 `POST /api/workflow/slot/slot_relations`

```
功能：根据已确认的槽位清单，生成槽位间逻辑依赖关系图谱
输入：
{
  "session_id": "xxx",
  "confirmed_slots": [
    {"slot_key":"slot_1","label":"消费路径分析","description":"..."},
    {"slot_key":"slot_2","label":"满意度诊断","description":"..."}
  ]
}

输出：
{
  "relations": [
    {"from":"slot_1","to":"slot_4","label":"路径分析 → 驱动因素转化"},
    {"from":"slot_1","to":"slot_2","label":"路径数据 → 满意度验证"},
    {"from":"slot_2","to":"slot_5","label":"满意度发现 → 定价优化"}
  ],
  "graph_description": "消费路径分析是上游输入，驱动购买决策和满意度诊断，定价敏感度受满意度结果影响"
}

实现：调用 LLM 生成，前端用纯 CSS 连线渲染（不用 Canvas）
```

### 3.8 `POST /api/workflow/slot/ask_followup`

```
功能：用户追问 AI，AI 基于上下文回复（支持两处调用：槽位确认阶段 + 编辑面板）
输入：
{
  "session_id": "xxx",
  "context": "slot_confirmation",        // slot_confirmation | edit_panel
  "slot_key": "slot_1",                  // 可选，编辑面板追问时指定槽位
  "question": "为什么消费路径分析和购买驱动归纳是独立的两个维度？",
  "history": [...]                       // 可选，之前的追问历史
}
输出：
{ "reply": "...", "suggestions": [] }
实现：非流式，单次 JSON 请求
```

### 3.9 `POST /api/workflow/slot/pre_check_materials`

```
功能：确认槽位前快速统计每个槽位能匹配几条素材，缺素材的槽位 AI 会推荐替代维度
输入：
{
  "session_id": "xxx",
  "confirmed_slots": [
    {"slot_key":"slot_1","label":"人群画像","description":"..."},
    ...
  ]
}
输出：
{
  "check_results": {
    "slot_1": {
      "count": 0,
      "level": "empty",         // full(≥3) | partial(1-2) | empty(0)
      "alternatives": [
        {"label":"行业规模与增速","reason":"有 3 条素材覆盖此方向","slot_key":null},
        {"label":"消费场景分析","reason":"有 2 条素材覆盖此方向","slot_key":null}
      ]
    },
    "slot_2": {"count": 5, "level": "full", "alternatives": []},
    "slot_3": {"count": 1, "level": "partial", "alternatives": [
      {"label":"供应链分析","reason":"知识库摘要中有供应链相关数据","slot_key":null}
    ]}
  }
}

实现：
1. 复用 _match_materials_internal() 做快速匹配（不持久化）
2. 对 level != full 的槽位，调 LLM 根据素材池内容推荐替代维度
3. 前端接收后展示 🟢/🟡/🔴 标识 + AI 替换建议
```

---

## 四、数据流

### 4.1 完整数据流

```
Step 2 (补充) 完成
  ↓
  session.material_pool = [
    { text: "..." , source_type: "knowledge_base", source_name: "报告.pdf" },
    { text: "..." , source_type: "user_input", source_name: "手动补充" },
    { text: "..." , source_type: "web_search", source_name: "搜索" }
  ]
  ↓
Step 3 进入
  ↓
① POST /slot/generate_slots (SSE)
  ← AI 流式返回 slots[]
  ↓ 流式完成后自动触发预检
①.5 POST /slot/pre_check_materials
  ← 返回每个槽位的素材覆盖度（🟢🟡🔴）+ AI 替换建议
  ↓ 用户：采纳建议 / 手动编辑 / 保留原槽位
  ↓ 用户确认
② POST /slot/batch_fill_v4
  ← 返回 { slot_1: {materials, outline}, slot_2: {...} }
  ↓ 写入 session.framework_slots[slot_key].materials / .outline
  ↓ 前端渲染三列表格（逐行出现）
  ↓ 用户编辑某行
③ EditPanel 操作
  - 写作方案 → session.framework_slots[slot_key].writing_plan
  - 补充素材 → POST /slot/upload_source → 文本返回 → add to materials
  - 微调提纲 → 直接编辑 outline
  ↓ [保存] → session 写入
  ↓ 全部确认
④ 点 [生成全文] → jump Step 4
```

### 4.2 前端状态流

```
useStep3_Workbench.js

阶段状态: 'streaming' | 'editing_slots' | 'filling' | 'done'

streaming:
  - SSE 连接 → streamingThinking 逐行更新
  - streamDone = true → 阶段切换为 'editing_slots'

editing_slots:
  - 用户增删改 confirmedSlots[]
  - 点「确认」→ 阶段切换为 'filling'

filling:
  - 调用 batchFillSlots(confirmedSlots)
  - 返回后 → slotMaterials / slotOutlines 填充
  - 逐个槽位展示完成 → 阶段切换为 'done'

done:
  - 用户可在三列中编辑任意行
  - 点「生成全文」→ emit('proceed-to-article')
```

---

## 五、组件树

```
WorkflowView.vue (currentStep === 2)
  └─ ThreeColumnWorkbench.vue
       ├─ StreamSlotsPanel.vue         (阶段 1: streaming + editing_slots)
       │   ├─ [流式文本区]              (打字机效果)
       │   ├─ [槽位间关系图谱]          (F11: CSS 连线图，可折叠)
       │   ├─ [槽位清单编辑器]          (行内编辑 + 增删)
       │   └─ [追问输入框]              (F13: 槽位确认阶段追问)
       │
       ├─ [三列表格]                    (阶段 2-3: filling + done)
       │   └─ <slot-row> (v-for slots)
       │       ├─ 状态灯 + 槽位名
       │       ├─ 素材列 (来源标签 + 文本片段)
       │       ├─ 提纲列 (有序要点)
       │       └─ 操作按钮 (编辑 / 确认)
       │
       └─ EditPanel.vue                (阶段 3: 右侧滑出)
           ├─ [写作方案] textarea
           ├─ [补充素材] textarea + 文件上传
           ├─ [微调提纲] 可编辑列表
           └─ [追问 AI] 追问区 (F12)
```

---

## 六、关键技术点

### 6.1 SSE 流式实现

```python
# api.py — 后端
from fastapi.responses import StreamingResponse
import json, asyncio

@router.post("/api/workflow/slot/generate_slots")
async def generate_slots(request: dict):
    session_id = request["session_id"]
    topic = request["topic"]
    summary = request.get("material_pool_summary", "")

    async def event_stream():
        # 调用 DeepSeek stream=True
        response = await _call_llm_stream(prompt, timeout=60)

        async for chunk in response:
            text = chunk.get("content", "")
            # 按行拆分，解析 thinking / slot / done
            for line in text.split("\n"):
                if line.startswith("- "):  # 槽位行
                    slot_label = line[2:].split("——")[0].strip()
                    yield f"data: {json.dumps({'type':'slot','label':slot_label})}\n\n"
                else:
                    yield f"data: {json.dumps({'type':'thinking','text':line})}\n\n"
            await asyncio.sleep(0.1)

        yield f"data: {json.dumps({'type':'done','slots':slots})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

```javascript
// api.js — 前端
export async function generateSlots(sessionId, topic, summary, { onThinking, onSlot, onDone }) {
  const response = await fetch('/api/workflow/slot/generate_slots', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, topic, material_pool_summary: summary })
  })

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''  // 保留不完整的行

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6))
        if (data.type === 'thinking') onThinking(data.text)
        else if (data.type === 'slot') onSlot(data)
        else if (data.type === 'done') onDone(data.slots)
      }
    }
  }
}
```

### 6.2 槽位独立填充（并行）

```python
# api.py
@router.post("/api/workflow/slot/batch_fill_v4")
async def batch_fill_v4(request: dict):
    session_id = request["session_id"]
    confirmed_slots = request["confirmed_slots"]

    async def fill_one(slot):
        mats = await _match_materials_for_slot(session_id, slot)
        outline = await _generate_outline_for_slot(session_id, slot, mats)
        return {
            "slot_key": slot["slot_key"],
            "materials": mats,
            "outline": outline
        }

    # 所有槽位并行填充
    results = await asyncio.gather(*[fill_one(s) for s in confirmed_slots])

    # 写入 session
    for r in results:
        session["framework_slots"][r["slot_key"]]["materials"] = r["materials"]
        session["framework_slots"][r["slot_key"]]["outline"] = r["outline"]

    return _success({ "results": { r["slot_key"]: r for r in results } })
```

### 6.3 图片 OCR（PaddleOCR）

```python
# src/image_processor.py (新增)
from paddleocr import PaddleOCR

ocr = PaddleOCR(lang='ch')  # 中文模型，首次自动下载

def extract_text_from_image(image_path: str) -> str:
    """从图片提取文字"""
    result = ocr.ocr(image_path)
    texts = []
    for line in result[0]:
        texts.append(line[1][0])  # line[1][0] 是识别文字
    return "\n".join(texts)
```

**为什么用 PaddleOCR**：
- DeepSeek V3 文本模型不支持图片输入
- PaddleOCR 离线、免费、中文识别准确率高
- 提取文字后，可传给 DeepSeek 做结构化分析

### 6.4 步骤条 8→5 改造

```javascript
// WorkflowView.vue — 修改 stepNames
const stepNames = ['选题', '补充', '分析工作台', '文章', '配图']

// currentStep 映射：
// 旧: 0(选题) 1(补充) 2(框架) 2.5(工作台) 4(检测) 5(结构) 6(提纲) 7(文章) 8(配图)
// 新: 0(选题) 1(补充) 2(工作台) 3(文章) 4(配图)

// 模板中：
<StepDirection v-if="currentStep === 0" />
<StepSupplement v-if="currentStep === 1" />
<ThreeColumnWorkbench v-if="currentStep === 2" />
<StepContent v-if="currentStep >= 3" />  // 文章+配图复用现有组件
```

### 6.5 v3.0 代码复用策略

| v3.0 代码 | v4.0 复用方式 |
|-----------|-------------|
| `FrameworkWorkbench.vue` 横向表头 | → `ThreeColumnWorkbench.vue` 三列表头（加宽一列） |
| `batchFillSlots()` | → `batchFillSlotsV4()` （加素材匹配+提纲生成） |
| `uploadSlotSource()` | → 编辑面板中复用 |
| 来源标签 CSS (.source-tag) | → 素材列复用 |
| 编辑面板 CSS (.edit-panel) | → 扩展为含三个区域的面板 |
| SSE 流式（无） | → 全新实现 |

---

## 七、实施顺序

| 步骤 | 内容 | 预估 | 输出 |
|------|------|------|------|
| 1 | 后端 SSE 端点 + slot_relations | 5h | `generate_slots` + `slot_relations` 可调通 |
| 2 | 后端 match_materials | 3h | 素材匹配可调通 |
| 3 | 后端 generate_outline + batch_fill_v4 + ask_followup | 3h | 批量填充 + 追问可调通 |
| 4 | 前端 api.js 新增 | 2h | SSE + 5 个 API |
| 5 | 前端 useStep3_Workbench | 2h | 状态管理就绪 |
| 6 | StreamSlotsPanel.vue（含关系图 + 追问） | 6h | 流式+槽位编辑+图谱+追问 |
| 7 | ThreeColumnWorkbench.vue | 5h | 三列表格 |
| 8 | EditPanel.vue（含追问） | 4h | 编辑面板+追问 |
| 9 | WorkflowView 步骤条 | 2h | 8→5 步 |
| 10 | 全链路联调 | 2h | 走通全流程 |
| **总** | | **~34h** | |

---

*Step 3 完成。下一步 → [AGENTS.md](./AGENTS.md)*
