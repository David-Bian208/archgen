# ArchGen 工作流 V2 开发文档

> 版本：V2.2  
> 日期：2026-06-26  
> 最后更新：2026-07-01（MCP 主题加载优化 + 注意事项补充）

---

## 一、核心设计原则

1. **框架先于素材** — 先定框架拆槽位，再按槽位定向补充。杜绝"盲补"。
2. **单屏工作台** — 框架确认后，从填槽位到缝合审核，一个界面完成。
3. **素材严谨，文章宽泛** — 槽位填充 LLM 温度 0.1，文章生成温度 0.5。
4. **槽位独立** — 每个槽位补充互不影响，可并行操作。
5. **宁可降级，不硬编** — AI 知识不足时，诚实告知而非编造（L0-L4 降级链）。
6. **模块解耦** — 每个 Step 的状态和逻辑独立管理，修改一个 Step 不影响其他 Step。各 Step 之间通过 session 数据字段传递信息，不依赖其他 Step 的组件或 composable。

---

## 二、工作流步骤（5+1 步）

| 步骤 | 名称 | 做什么 | 界面 |
|------|------|--------|------|
| 0 | 选题 | KB 扫描 → 候选方向评分 → 用户确认 | StepDirection.vue |
| 1 | 补充 | 推荐写作角度 + 素材管理 + AI 补充 + 缺失检测 | StepSupplement.vue（重构） |
| 2 | 槽位工作台 | 按写作角度拆槽位 → 素材填充 → 细则修改 | FrameworkWorkbench.vue |
| 3 | 生成提纲 | 基于 stitched_body → 产出文章提纲 | StepContent |
| 4 | 合成文章 | 提纲展开为全文 | StepContent |
| +1 | 配图 | 生成配图并嵌入 | StepContent |

---

## 三、Step 1 补充对话框：AI 补充 + 素材管理 ✅ 已实现

> **状态**：✅ 已实现，运行中  
> **涉及文件**：`StepSupplement.vue` / `SupplementDialog.vue` / `useWorkflowState.js`

### 3.1 机制

原补充对话框支持三个独立来源，补充内容可追溯：

```
用户点击「AI 补充」
    ↓
打开补充对话框，包含：
├─ 📂 知识库文件选择（勾选需要读取的 KB 文件）
├─ 🌐 联网搜索开关 + 关键词输入（搜索 AI-Pulse 内容）
├─ 📝 手动输入区
    ↓
后端处理 (POST /api/workflow/supplement/ai-auto):
1. 读取选中的 KB 文件内容（KnowledgeBaseReader，截取前 3000 字）
2. 联网搜索（AIPulseClient.fetch_latest_cases，匹配关键词）
3. 综合所有素材 + LLM 推断 → 生成补充文字
    ↓
返回 matched_materials（kb_files + ai_pulse_articles + inference）
    ↓
用户确认采纳后 → 素材做加法追加到 materialPool
```

### 3.2 素材池展示

确认后在页面展示按类型分类：

```
📦 已收集素材（N 条）
├─ 🤖 AI 推断（1 条）
├─ 📂 知识库文件（2 条）
├─ 🌐 联网检索（3 条）
```

### 3.3 已知问题（待修复）

| 问题 | 原因 | 修复方向 |
|------|------|---------|
| AI 智能补充按钮有时失效 | StepSupplement 改为 props 后变量前缀遗漏 | 已部分修复，需验证 |
| 补充后按钮消失 | `v-if="!supplement2Text"` 条件 | 改为始终可见 |
| 缺失项不显示 | props.preCheckResult 绑定未全部纠正 | 逐一核对模板绑定 |
| 确认补充完毕禁用 | supplement2Text 状态同步断裂 | 检查 WorkflowView → StepSupplement 数据流 |
| 方向/框架显示冗余 | Step 1 不需要显示框架选择 | 去掉框架相关展示 |

### 3.4 当前 API 端点（已实现）

| 端点 | 功能 | 状态 |
|------|------|------|
| `POST /api/workflow/supplement/ai-auto` | AI 智能补充（KB + AI-Pulse + LLM 推断） | ✅ |
| `POST /api/workflow/supplement/confirm` | 确认补充内容 | ✅ |
| `POST /api/workflow/supplement/list` | 列出已补充项 | ✅ |

---

## 四、计划：Step 1 写作角度推荐 🔮 规划中

> **状态**：🔮 规划中，尚未实现  
> **背景**：2026-07-01 讨论确认方案B，当前文档为设计规范，API 端点和前端组件均未开始

### 4.1 动机

Step 0 选题评分解决的是"这个方向值不值得写"（方向适合度 / 内容完整度 / 综合评分）。Step 1 需要进一步解决"既然定了方向，该怎么写"。两者不重叠：

| | Step 0（选题） | Step 1 规划（补充增强） |
|---|---|---|
| 目的 | 帮用户选哪个方向值得写 | 帮用户确定写作角度 + 补素材 |
| 输入 | 知识库全部文件 | 选中方向 + MCP 匹配素材 |
| 输出 | 方向评分 + 推荐排名 | 写作角度选项 + 素材清单 + 缺失维度 |
| 操作 | 选方向 → 下一步 | 选角度 → 管素材 → AI补 → 检测 → 下一步 |

### 4.2 规划页面结构

```
┌──────────────────────────────────────────────────────┐
│  补充分析内容                                         │
│                                                      │
│  📄 选题方向：【AI赋能中层管理者】(Step 0 已选定)      │
│                                                      │
│  ┌─ 推荐写作角度 ──────────────────────────────────┐  │
│  │                                                │  │
│  │  ○ 角度A：工具盘点型                           │  │
│  │    主旨：推荐适合中层管理者使用的10款AI工具      │  │
│  │    产出：清单型文章                             │  │
│  │    匹配素材：12/15 篇相关  ← 素材覆盖度          │  │
│  │                                                │  │
│  │  ● 角度B：案例研究型（已选）                    │  │
│  │    主旨：深入拆解3家企业的中层AI赋能实践         │  │
│  │    产出：案例对比型文章                         │  │
│  │    匹配素材：8/15 篇相关  ← 需补充案例数据       │  │
│  │    ⚠️ 缺失：落地效果数据、中层反馈              │  │
│  │                                                │  │
│  │  ○ 角度C：方法论型                             │  │
│  │    主旨：给出中层管理者落地AI的5步框架           │  │
│  │    产出：方法论型文章                           │  │
│  │    匹配素材：6/15 篇相关  ← 素材不足             │  │
│  │                                                │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  ┌─ 素材管理 ─────────────────────────────────────┐  │
│  │ 📂 某银行AI转型案例.md            [预览] [删除] │  │
│  │ 📂 某制造企业数字化报告.pdf       [预览] [删除] │  │
│  │ 📂 中层管理培训手册.docx          [预览] [删除] │  │
│  │ ...（共 N 篇已选中素材）                        │  │
│  │                                                │  │
│  │ [➕ 添加素材]  [🚀 AI 智能补充]                 │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  ┌─ 底部操作 ─────────────────────────────────────┐  │
│  │  [ 🔍 检测素材完整性 ]  (大号按钮)               │  │
│  │  [✅ 确认补充完毕]  [⏭ 跳过]                    │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

### 4.3 Step 1 与 Step 2 的边界

| Step 1 | Step 2 |
|---|---|
| **决定** "文章什么类型" | **填充** "文章每个段落写什么" |
| **类比** 选户型（三室/两室/复试） | 填装修细节（客厅墙色/厨房台面） |

**具体例子**：选题"AI赋能中层管理者"

| 写作角度 | 主旨 | Step 2 框架倾向 |
|----------|------|----------------|
| 工具盘点型 | 推荐10款AI工具 | 功能清单结构 |
| 案例研究型 | 拆解3家企业实践 | 背景→案例对比→关键发现→落地建议 |
| 方法论型 | 5步落地框架 | 步骤拆解结构 |

### 4.4 待新增 API

| 端点 | 功能 | 状态 |
|------|------|------|
| `POST /api/workflow/angle/recommend` | 基于选题+素材推荐 2-3 个写作角度 | 🔮 待开发 |
| `POST /api/workflow/material/gaps` | 基于选定角度检测素材缺失类型 | 🔮 待开发 |

### 4.5 待改造文件

| 文件 | 当前行数 | 预估改造后 | 改造内容 |
|------|---------|-----------|---------|
| `StepSupplement.vue` | ~350 行 | ~600+ 行 | 角度选择 + 素材管理 + 预览 + 检测 |
| `WorkflowView.vue` | ~2970 行 | 需调整 | Step 1 状态管理（角度、素材池、检测结果） |
| `api.js` | — | 新增 2 个函数 | `recommendAngles()` / `detectMaterialGaps()` |
| `api.py` | — | 新增 2 个端点 | 角度推荐 + 素材缺失检测 |

> ⚠️ **风险提示**：`StepSupplement.vue` 和 `WorkflowView.vue` 同时改造，两个大文件有叠加冲突风险。建议先稳定 StepSupplement 的当前实现（修已知 Bug），再推进写作角度功能。

---

## 五、前端架构：按 Step 拆分 Composable

### 5.1 拆分方案

将当前 `useWorkflowState.js`（2000+ 行）拆分为独立模块，每个模块只管理自己步骤的状态。

```
useSession.js           ← 公共：sessionId / currentStep / loading
useStep0_Topics.js      ← 选题：topics / selectedDirection / mcpSummary
useStep2_Framework.js   ← 框架：frameworks / selectedFramework / supplement2Form
useStep3_Workbench.js   ← 工作台：slotResults / slotCoverage / stitchResult（全新独立）
useStep3_Check.js       ← 检测：directionCheckResult / checkingDirection / issues
useStep4_Outline.js     ← 提纲：outlineResult / structures
useStep5_Article.js     ← 文章：articleResult
useStep7_Images.js      ← 配图：infographicHtml
```

**原则**：纯搬家，不改逻辑。每拆一个模块验证一次构建。

> 注意：Composable 拆分不在 P0 执行范围内，先以新建 `useSession.js`（仅 sessionId / currentStep / loading 三个 ref）和 `useStep3_Workbench.js` 为主，其余在 P0 之后另排。

### 5.2 模块间数据约定

各 Step 通过 session 字段传递数据，不互相引用组件或 composable：

```
Step 1 → session.step1.direction
Step 2 → session.step2.framework
Step 3 → session.step3.slots
Step 4 → session.step4.outline
Step 5 → session.step5.article
Step 7 → session.step7.images
```

修改任意 Step 的内部实现，只要 session 字段不变，其他 Step 不受影响。

### 5.3 MCP 主题加载优化（2026-07-01）

**背景**：从 MCPSearchView 带着预选主题进入 WorkflowView 时，原来加载的是全部文件（94 篇），用户需要的是跟主题相关的文件子集。

**改动**：`WorkflowView.vue` onMounted 中，有主题时调用 `apiMcpSuggest` 获取主题匹配的文件。

```javascript
// 之前：调用 apiMcpSearch，返回全部文件
const res = await apiMcpSearch(topicName, folders)

// 现在：调用 apiMcpSuggest，返回主题匹配的文件
const suggestRes = await apiMcpSuggest({
  topic: topicName,
  folders,
  categories: [],
  time_range: 'all',
  start_date: '',
  end_date: '',
})
if (suggestRes.data?.code === 0 && suggestRes.data.data) {
  const suggestData = suggestRes.data.data
  mcpFiles.value = (suggestData.source_files || suggestData.files || []).map(f => ({
    name: typeof f === 'string' ? f : f.name || f.path || '',
    content: f.content || '',
  }))
  mcpSummary.value = suggestData.summary || `已搜索「${topicName}」相关素材 ${mcpFiles.value.length} 篇`
}
```

**原理**：后端 `mcp_suggest` API（`/api/mcp/suggest`）在第 3216 行调用 `reader.list_files(keyword=topic, limit=10)`，用主题关键词做文件名匹配。返回的 `source_files` 字段即为匹配的文件子集。

**注意点**：
1. `list_files(keyword=topic, limit=10)` 硬限制最多返回 10 个文件。如果相关文件多于 10 个，会有遗漏。建议视情况将 limit 调大到 30。
2. 当前匹配机制是**关键词匹配（文件名层面）**，不是语义匹配。如果后续发现文件名匹配遗漏太多，可改方案为在 `analyze_directions_v2` 的 prompt 中让 LLM 输出每个方向对应的 `source_files`。
3. 降级路径：后端搜索失败时，回退到读取文件夹全部文件，并在摘要中标注 "后端搜索降级"。

---

## 六、步骤 3 详解：框架工作台

### 6.1 界面布局（P0 简化版：无 L2/L3 问答 UI，只有 🟢/🟡 两级）

```
┌──────────────────────────────────────────────────────────┐
│ 框架：AI转型ROI四维评估    方向：烘焙企业转型               │
│ ████████████████░░░░░░  2/4 槽位完成                      │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ ┌─ 槽位1：研发创新 ───────────────────── 🟢 ─────────┐   │
│ │ 📎 素材：📄 白皮书.pdf  / 🔍 检索(3条)              │     │
│ │ ───────────────────────────────────────────────── │     │
│ │ 分析要点：                                          │     │
│ │ "配方优化算法可将 NPD 周期缩短 30%-50%..."          │     │
│ │ 来源：[知识库报告]                                  │     │
│ │ ⚠️ 缺口：配方算法的具体技术路径未核实                 │     │
│ │                                                    │     │
│ │ [ 确认 ✓ ] [ 补充素材 → 重分析 ] [ 跳过 ]            │     │
│ └───────────────────────────────────────────────────┘     │
│                                                          │
│ ┌─ 槽位2：供应链优化 ───────────────────── 🟡 ─────────┐  │
│ │ ⚠️ AI 知识不足，无法直接填充                           │  │
│ │ 📎 素材：无                                           │  │
│ │ 缺口清单：                                             │  │
│ │ · 库存周转率数据                                       │  │
│ │ · 预测方法类型                                         │  │
│ │                                                    │     │
│ │ [ 上传文件 ] [ 搜索知识库 ] [ 手写补充 ] [ 跳过 ]      │    │
│ └───────────────────────────────────────────────────┘    │
│                                                          │
│ ┌─ 槽位3：零售转型 ───────────────────── ⚪ 空 ────────┐  │
│ │ [ 上传文件 ] [ 搜索知识库 ] [ 手写补充 ] [ 🤖 AI 分析 ]│  │
│ └───────────────────────────────────────────────────┘    │
│                                                          │
│ ┌─ 槽位4：内容战略 ───────────────────── ⚪ 空 ────────┐  │
│ │ [ 上传文件 ] [ 搜索知识库 ] [ 手写补充 ] [ 🤖 AI 分析 ]│  │
│ └───────────────────────────────────────────────────┘    │
│                                                          │
├──────────────────────────────────────────────────────────┤
│ [ 🔗 缝合审核（承上启下）]       [ ⏭ 生成提纲 → ]         │
└──────────────────────────────────────────────────────────┘
```

### 6.2 槽位状态

| 状态 | 图标 | 含义 |
|------|------|------|
| 空 | ⚪ | 未开始 |
| 进行中 | 🔵 | 有素材但未生成分析要点 |
| 缺数据 | 🟡 | AI 已分析但标注了关键缺口 |
| 已完成 | 🟢 | 有素材、有分析、无关键缺口 |

### 6.3 素材来源

| 来源 | 操作 | 说明 | 前端标签 |
|------|------|------|---------|
| 手动上传 | 用户传文件/文件夹/图片 | 直接附加到槽位 | `<a-tag color="blue">📄 文件</a-tag>` |
| 知识库检索 | 按槽位关键词 + 方向词定向搜索 | 后端接口 `/api/workflow/slot/search`（P1）; P0 用 MCP 摘要兜底 | `<a-tag color="green">🔍 检索</a-tag>` |
| 手写输入 | 自由文本 | 用户直接粘贴或输入 | `<a-tag color="orange">✏️ 手写</a-tag>` |

---

## 七、降级链 L0-L4

### 7.1 级别定义

| 级别 | 名称 | 触发条件 | AI 输出 | P0/P1 | 槽位状态 |
|------|------|---------|---------|-------|---------|
| L0 | 知识充足 | 有具体案例/数据/技术细节 | 直接填充分析要点 + 引用来源 | P0（不暴露前端标签） | 🟢 已完成 |
| L1 | 知识部分 | 知道通用模式，缺具体案例 | 展开通用要点 + 标注缺口 | P0（不暴露前端标签） | 🟢 已完成 |
| L2 | 知识稀疏 | 无法直接补充，能提结构化问题 | 3-5 个引导性填空问题 | P1 | 🟡 缺数据 |
| L3 | 知识几乎没有 | 只能用类比推导 | 类比推导 + 明确标注 | P1 | 🟡 缺数据 |
| L4 | 知识空白 | 完全不知道 | 空框架（维度清单） | P0 | 🔵 进行中 |

> **P0 简化版**：前端只区分 🟢（AI 成功填充，含缺口也标 🟢）和 🟡（AI 无法填充，标缺口 + 上传/手写/跳过）。L0-L4 完整 UI（L2 问答输入框 + L3 类比卡片）留到 P1。后端降级配置（max_degradation=2）在 P0 写入，但前端暂不暴露降级按钮。

### 7.2 AI 自评流程

```
问1：我能直接补充具体内容吗？
  ├─ 能 → 问1a：有具体案例/数据支撑吗？
  │        ├─ 有 → L0
  │        └─ 没有 → L1
  └─ 不能 → 问2：我能提出结构化问题吗？
           ├─ 能 → L2
           └─ 不能 → 问3：能用类比推导吗？
                    ├─ 能 → L3
                    └─ 不能 → L4
```

### 7.3 完整降级路径

```
                    槽位状态：空
                         │
                    点「AI 分析」
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
           AI 能填              AI 不能填
           (L0/L1)              (L4 空框架)
              │                     │
       显示分析+缺口            显示缺口清单
       🟢 状态                  🟡 状态
              │                     │
     ┌───────┼────────┐      ┌──────┼──────┐
     │       │        │      │      │      │
   确认   补素材    跳过   上传   手写   跳过
     │     │                       │
     ▼     ▼                       ▼
    过   AI重分析              素材到位→过
```

**规则**：
- 每次点"重试"降一级，单槽位最多降 2 次（P0 后端配置，P1 前端暴露）
- 降到 L4 无法再降，必须手写
- 任何时候可选"跳过"直接过（缺口和空白会带进缝合审核）
- L4 空框架不硬拦，进度条标黄提醒

### 7.4 L2 提问机制

L2 的问题由 AI 动态生成，不是固定模板。P1 在前端新增结构化输入框。

| 约束 | 说明 |
|------|------|
| 问题必须追问具体数据或事实 | 禁止开放式问题（如"你觉得呢"） |
| 1 个问题只问 1 个明确维度 | 数字型 / 分类型 / 事实型，不和稀泥 |
| 生成 3-5 个问题 | 太少无用，太多烦人 |
| 优先追问知识库已有信息的周边数据 | 已有 A，追问关联的 B/C |

### 7.5 各级别 UI

| 级别 | AI 给什么 | 用户操作 | 卡片标签色 | P0/P1 |
|------|----------|---------|-----------|-------|
| L0/L1 | 分析要点 + ⚠️ 缺口清单 | [确认] [补素材→AI重分析] [跳过] | 绿色/黄色 | P0 |
| L4 | 缺口清单 + 维度提示 | [上传文件] [手写补充] [搜索知识库] [跳过] | 灰色 | P0 |
| L2 | 3-5 个结构化输入框 | [答完→AI重写] [跳过] | 橙色 | P1 |
| L3 | 类比段落 + 💡 启发方向 | [按类比展开] [补真实数据→AI重写] [跳过] | 红色 | P1 |

### 7.6 条件化重新评估

缝合审核时只对 L0/L1 槽位检查内容质量，L2/L3/L4 槽位只检查框架逻辑是否自洽。

---

## 八、后端 API 变更

### 8.1 新增：单槽位填充 `/api/workflow/slot/fill`（P0）

新建 API，不碰旧 `framework/fill`。一次只填一个槽位，不影响其他槽位。

**请求**：

```json
POST /api/workflow/slot/fill
{
    "session_id": "abc123",
    "slot_key": "r_and_d",
    "supplement_input": "用户补充的文本，可选",
    "confirmed_sources": [
        {"type": "file", "name": "白皮书.pdf"},
        {"type": "ai_pulse", "title": "烘焙行业AI应用趋势"}
    ]
}
```

**后端逻辑**：

1. 从 session 读取该槽位的 keywords + 已有素材
2. 组合 prompt：slot_keywords + supplement_input + confirmed_sources + mcp_summary
3. LLM 填充（temperature=0.1, max_tokens=4000）
4. 自评 coverage + gaps
5. 写入 `session.framework_slots[slot_key]`

**核心规则**：只写这一个槽位，不碰其他槽位。

**响应**：

```json
{
    "code": 0,
    "data": {
        "slot_key": "r_and_d",
        "level": "L1",
        "points": ["要点1...", "要点2..."],
        "sources": ["文件A.pdf", "AI推理"],
        "gaps": ["配方算法具体路径待核实"],
        "coverage": 0.75
    }
}
```

### 8.2 新增：槽位级检索 `/api/workflow/slot/search`（P1）

```
POST /api/workflow/slot/search
入参：{ slot_name, keywords, direction }
出参：{ results: [{ source, snippet, relevance }] }
```

在 MCP 知识库摘要中按槽位关键词定向匹配，返回相关片段。

### 8.3 缝合审核 `/api/workflow/direction/check` — 新增 coherence 模式（P0）

**方案**：后端从 session 自动读取所有槽位 → 自动缝合 → 检测衔接。前端只传 `session_id` + `check_mode`。

```
POST /api/workflow/direction/check
入参：{ session_id, check_mode: "coherence" }

后端逻辑：
  1. 从 session 读取所有 framework_slots
  2. 将各槽位要点按框架顺序拼接为 stitched_body
  3. 检测跨槽位衔接问题
  4. 返回 transition_issues

出参：{
  "code": 0,
  "data": {
    "transition_issues": [
      { "from_slot": "研发创新", "to_slot": "供应链优化", "issue": "...", "suggestion": "..." }
    ],
    "ready_for_next": true
  }
}
```

**用户只点一次按钮**，不需要前端先调 stitch 再调 check。

### 8.4 文章生成 `/api/workflow/article/generate`

- max_tokens=16384
- temperature=0.5

---

## 九、前端组件变更

### 9.1 新增组件

| 组件 | 文件 | 说明 |
|------|------|------|
| FrameworkWorkbench | `components/workflow/FrameworkWorkbench.vue` | 框架工作台主组件（~500行） |
| SlotCard | `components/workflow/SlotCard.vue` | 槽位卡片：上传区、检索区、分析结果区、操作区（~300行）。来源标签直接用 `<a-tag>`，不需要独立 MaterialBadge 组件 |

### 9.2 新增 Composable

| 文件 | 说明 | P0/P1 |
|------|------|-------|
| `composables/useSession.js` | sessionId / currentStep / loading 等跨步骤共享状态（仅 3 个 ref） | P0 |
| `composables/useStep3_Workbench.js` | 工作台全部状态：slotResults / slotCoverage / stitchResult / 降级记录 | P0 |

### 9.3 修改文件

| 文件 | 改动 |
|------|------|
| StepFramework.vue | 选完框架后跳转 FrameworkWorkbench |
| WorkflowView.vue | 新增 currentStep 值走 FrameworkWorkbench |
| useWorkflowState.js | 不拆分。P0 仅从中解构工作台所需状态 |

---

## 十、数据流

```
Step 1 选题
  ↓ direction + mcp_summary
Step 2 选框架
  ↓ framework_key + slot_names + slot_keywords
Step 3 框架工作台
  ├─ 用户手动：上传文件/图片/手写文本
  ├─ AI 分析：POST /api/workflow/slot/fill × N（每槽位独立调用）
  └─ 缝合审核：POST /api/workflow/direction/check (check_mode: "coherence")
  ↓ stitched_body（后端自动缝合的连贯文本）
Step 4 生成提纲
  ↓ outline（标题 + 段落 + 引用素材）
Step 5 合成文章
  ↓ full_article
Step +1 配图
```

---

## 十一、实施计划

### 11.1 执行顺序（4 个迭代）

| 迭代 | 谁写 | 交付 | 验证方式 |
|------|------|------|---------|
| 1 | 后端 | `slot_fill` API + 降级配置 L0-L4 | curl 测试：传入一个槽位，返回对应要点 + coverage |
| 2 | 前端 | `SlotCard.vue` + `FrameworkWorkbench.vue` 骨架 + 对接 slot_fill | 手动填一个槽位，卡片显示 🟢/🟡 |
| 3 | 后端 | `check_direction` coherence 模式 | curl 测试：传入 session_id，返回 transition_issues |
| 4 | 前端 | FrameworkWorkbench 集成缝合审核 + WorkflowView 挂载 | 全流程：选框架→填槽位→缝合→通过→生成提纲 |

### 11.2 任务分级

| 优先级 | 任务 | 文件 | 迭代 | 工作量 |
|--------|------|------|------|--------|
| P0 | 新建 `useSession.js`（sessionId/currentStep/loading） | composable | 2 | 小 |
| P0 | 新建 `useStep3_Workbench.js` | composable | 2 | 中 |
| P0 | 后端 `slot_fill` API | api.py | 1 | 中 |
| P0 | 后端降级 L0-L4 自评逻辑 | api.py | 1 | 中 |
| P0 | 后端 coherence 模式 | api.py | 3 | 中 |
| P0 | 新建 FrameworkWorkbench.vue | 组件 | 2+4 | 大 |
| P0 | 新建 SlotCard.vue（简化版，🟢/🟡 两级） | 组件 | 2 | 中 |
| P0 | WorkflowView 集成 FrameworkWorkbench | 修改 | 4 | 中 |
| P1 | L2/L3 完整 UI（问答输入框 + 类比卡片） | SlotCard.vue | — | 中 |
| P1 | 降级链前端 buttons（重试→降级、次数限制） | SlotCard.vue | — | 中 |
| P1 | 后端 slot/search 检索接口 | api.py | — | 中 |
| P2 | Composable 全量拆分 | 多文件 | — | 大 |
| P2 | LLM 温度分阶校验 | api.py | — | 小 |

---

## 十二、降级链配置

```python
SLOT_ANALYSIS_CONFIG = {
    "max_degradation": 2,         # 单槽位最多降级次数
    "temperature": 0.1,           # 分析用温度
    "default_max_tokens": 8192,   # 兜底值
    "slots_per_token": 2000,      # 每槽位分配 token 数
    "max_total_tokens": 32768,    # 总 token 上限
}
```
