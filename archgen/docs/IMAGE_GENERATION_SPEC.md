# 文生图（信息图 HTML+CSS）功能规范 v4.0

> 日期：2026-07-17 | 状态：v4.0 三站接力架构设计完成，待实现
>
> v4.0 核心变更：
> - v3.0 两阶段管线（蒸馏→排版，LLM 同时做排版决策）→ v4.0 三站接力（拆卡片→排格子→印海报，LLM 只管内容拆解）
> - 去除 LLM 布局决策权：LLM 只输出结构化卡片 JSON，不写 CSS、不决定列型、不排格子
> - 引入装箱引擎：代码规则根据 density + content_shape 确定性分配行和列
> - 引入 content_shape 维度：flow / grid / list / compare，决定视觉结构约束
> - 两条输入路径：archgen 槽位（写作阶段已有的章节结构）和外来文章（LLM 语义拆解）

---

## 一、功能定位

将长文（Markdown）自动转化为信息图海报（HTML+CSS），输出为可预览、可下载、可修订的独立 HTML 页面。

**不是** AI 图片生成（Midjourney/DALL-E），**是** AI 排版引擎——LLM 根据内容拆解为结构化卡片，代码规则装箱排布，渲染引擎精确输出 HTML。

---

## 二、技术架构（v4.0 三站接力）

### 整体流程

```
文章（Archgen 槽位 / 外部 Markdown）
          │
          ▼
┌──────────────────────────────────────────────┐
│  第零站：定画布（代码写死）                    │
│  · 竖版 1080×1440，Hero 280px + 5行×232px    │
│  · 横版 1920×1080，Hero 240px + 4行×210px    │
└──────────────────┬───────────────────────────┘
                   ▼
┌──────────────────────────────────────────────┐
│  第一站：拆卡片（LLM 做）                     │
│  输入：文章内容                               │
│  输出：N 张信息卡片，每张含：                   │
│    · title, items, density, content_shape    │
│    · semantic_weight, icon, badge, relation   │
│  LLM 只做内容拆解，不做排版决策               │
└──────────────────┬───────────────────────────┘
                   ▼
┌──────────────────────────────────────────────┐
│  第二站：排格子（代码规则做）                   │
│  装箱引擎：density + content_shape → 行列分配 │
│  三重规则：                                    │
│    1. flow/grid → 强制独占整行                │
│    2. density=high → 强制独占整行             │
│    3. 其他 → 拼车候选                          │
│  拼车约束：竖版最多2列，横版最多3列             │
│  溢出：合并相邻 low list 卡片，不删内容         │
└──────────────────┬───────────────────────────┘
                   ▼
┌──────────────────────────────────────────────┐
│  第三站：印海报（代码模板做）                   │
│  按 content_shape 选渲染模板：                 │
│    · list → 图标列表（白底卡片）               │
│    · grid → 3列灰格（图标+标题+描述）          │
│    · flow → 横向节点+箭头                     │
│    · compare → 左右对照双列                    │
│  所有颜色/字号/间距写死在代码里，精确到像素     │
└──────────────────┬───────────────────────────┘
                   ▼
             返回 HTML → 前端 iframe 预览
```

### 两路径统一

| | 路径A：Archgen 文章 | 路径B：外部文章 |
|------|------|------|
| **卡片来源** | 直接使用写作阶段的槽位结构 | LLM 语义拆解 |
| **卡片数量** | 槽位有几个就是几个 | LLM 自定（4-8张） |
| **卡片边界** | 槽位已划分好 | LLM 划分 |
| **LLM 做的事** | 补标注（density/shape/icon/badge）+ 拆要点 | 全量（拆卡片+所有标注） |
| **可靠性** | 更高（槽位结构是用户确认过的） | 中（依赖 LLM 语义理解） |

两路径输出统一为相同的卡片 JSON 格式，下游装箱引擎和渲染引擎不关心来源。

---

## 三、基础参数

### 竖版（3:4）

| 参数 | 值 |
|------|-----|
| 画布 | 1080 × 1440 |
| Hero 区 | 280px（独立，不占正文行） |
| 内容行数 | 5 行 |
| 每行高度 | 232px（固定，超量 CSS overflow:hidden 截断） |
| 行内列数上限 | 2 列（双列） |

### 横版（16:9）

| 参数 | 值 |
|------|-----|
| 画布 | 1920 × 1080 |
| Hero 区 | 240px（独立，不占正文行） |
| 内容行数 | 4 行 |
| 每行高度 | 210px（固定，超量 CSS overflow:hidden 截断） |
| 行内列数上限 | 3 列 |

---

## 四、槽位属性定义

### density：内容量级

| 值 | 含义 | 判断依据 |
|------|------|------|
| high | 信息密集 | 图标+描述+对比表，或 ≥4 条带展开的长要点 |
| medium | 信息中等 | 若干要点，有一定展开但不过长 |
| low | 信息稀疏 | 3-5 条短句，每条≤15字，无图表 |

### content_shape：视觉结构需求

| 值 | 含义 | 示例 | LLM 判定依据 |
|------|------|------|------|
| flow | 流程型，节点+箭头，不容切割 | 采集→清洗→评分→分发 | 含先后顺序词、步骤编号 |
| grid | 网格型，需要全宽放置 3-4 列 | 三大架构对比 | 每项含"标题+长描述" |
| list | 列表型，要点罗列，可切割 | 核心功能清单 | 简单要点，无特殊结构 |
| compare | 对照型，左右对照，推荐拼车 | 优点 vs 缺点 | 含对比词，分两部分 |

### semantic_weight：语义权重

| 值 | 含义 | 对装箱的影响 |
|------|------|------|
| primary | 文章最重要、不能丢的模块 | 不合并、不裁内容、可独占一行 |
| secondary | 重要但不至于不能合并 | 正常参与装箱决策 |
| supporting | 可以合并甚至裁剪 | 合并时优先选择 |

### 判定机制（三层）

```
第一层：规则推导（确定性，无 LLM 成本）
  关键词检测 → 初步 shape
  · 含"步骤/流程/第一第二" → flow
  · 含"vs/相比/对比/差异" → compare
  · 每项描述字数 > 标题字数×2 → grid
  · 其他 → list

第二层：LLM 标注（可选，覆盖模糊情况）
  LLM 显式输出 density / content_shape → 覆盖规则结果

第三层：规则兜底（安全网）
  LLM 说 flow 但内容只有 2 项且无顺序词 → 降级为 list
  LLM 说 grid 但只有 2 项 → 降级为 list
```

---

## 五、卡片 JSON Schema（第一站 LLM 输出）

```json
{
  "thinking": "LLM 拆解思路（100-200字）",
  "header_title": "AI搭建新闻引擎 | 全自动化内容生产",
  "footer_text": "基于 DeepSeek V4 · 算力成本降低80%",
  "cards": [
    {
      "id": 1,
      "title": "核心亮点 · Vibe Coding开发流程",
      "items": [
        {"bold": "需求对齐", "text": "我+元宝+OpenClaw+Trae 四方针全链路对齐"},
        {"bold": "文档落地", "text": "所有决策输出标准化开发文档，无信息差"}
      ],
      "density": "high",
      "content_shape": "list",
      "semantic_weight": "primary",
      "icon": "rocket",
      "badge": "3天从0到1上线",
      "relation": null
    },
    {
      "id": 2,
      "title": "产品定位",
      "items": [
        {"text": "通用聚合引擎，可自定义任意领域信源"},
        {"text": "当前配置211个高质量信源"}
      ],
      "density": "low",
      "content_shape": "list",
      "semantic_weight": "secondary",
      "icon": "cogs",
      "badge": null,
      "relation": {"type": "pair", "with": 3}
    },
    {
      "id": 3,
      "title": "核心价值",
      "items": [
        {"text": "算力成本降低80%"},
        {"text": "响应速度提升40%"},
        {"text": "综合去重准确率达98%"}
      ],
      "density": "medium",
      "content_shape": "list",
      "semantic_weight": "secondary",
      "icon": "star",
      "badge": null,
      "relation": {"type": "pair", "with": 2}
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 必须 | 说明 |
|------|------|:--:|------|
| title | string | ✓ | 卡片标题，≤12字 |
| items | array | ✓ | 要点列表，2-5条 |
| items[].bold | string | | 加粗前缀（冒号前的关键词） |
| items[].text | string | ✓ | 要点正文 |
| density | enum | ✓ | high / medium / low |
| content_shape | enum | ✓ | flow / grid / list / compare |
| semantic_weight | enum | ✓ | primary / secondary / supporting |
| icon | string | | 从固定图标库选择（20-30个） |
| badge | string | | 原文量化亮点（如"3天上线"、"效率+40%"） |
| relation | object | | 可选标注，语义关联 |
| relation.type | enum | | "pair"（同组）/ "contrast"（对照） |
| relation.with | int | | 关联的卡片 id |

---

## 六、图标系统

### 固定图标库（20-30个）

```
architecture / rocket / shield / chart / workflow / code / cloud /
database / team / target / lightbulb / scale / clock / puzzle /
gear / star / flag / layers / compare / network / file / search /
check / robot / filter / download / book / newspaper / calendar
```

LLM 从库中选择 `icon` 字段值，不允许自己发明新名称。未匹配到 → 使用默认图标 `file`。

---

## 七、装箱引擎（第二站 代码规则）

### 7.1 列型约束计算

```
函数: max_slots_for(slot, canvas)

  规则1: content_shape ∈ {flow, grid} → 返回 1（强制独占）
  规则2: density == "high" → 返回 1（强制独占）
  规则3: 拼车候选

竖版（1080px）:
  content_shape ∈ {list, compare} && density == "low" → 返回 2
  其他 → 返回 1

横版（1920px）:
  content_shape == "list":
    density == "low" → 返回 3
    density == "medium" → 返回 2
  content_shape == "compare":
    density ∈ {low, medium} → 返回 2
  其他 → 返回 1
```

### 7.2 贪心装箱

```
输入: cards[N], canvas_info
输出: rows[M]（M ≤ maxRows）


遍历中的三种情况
├─ forceSolo（独占）：新建一行 → 立即封行
├─ 拼车候选 && 当前行有空位 → 拼入当前行
│   └─ 填满即封行
└─ 无法拼入当前行 → 当前行封行 → 新开一行

语义距离：拼车候选人有多位时，优先选原文位置近的
LLM 在卡片 JSON 中标了 relation → 布局阶段优先配对
```

### 7.3 溢出处理

```
rows.length > maxRows → mergeOverflow(rows, maxRows)

合并条件:
  两条相邻，都是 low density + list + 非 forceSolo
  按语义距离（原文位置 + relation 加权）排序合并

合并方式:
  title: a.title + " · " + b.title
  items: a.items + b.items
  density: "medium"（合并后）
  content_shape: "list"
  icon: a.icon（继承第一个）
  badge: a.badge || b.badge
  relation: null
  merged_from: [a.id, b.id]

绝不删内容，只合并。合并后还超 → JS 自缩放兜底。
```

---

## 八、渲染引擎（第三站 代码模板）

### 8.1 渲染模板

引用 Cherry-fidelity 精确参数（`cherry_fidelity.py`），所有视觉决策写死在代码中：

| 模板类型 | 匹配条件 | HTML 结构 |
|------|------|------|
| highlight | density=high + 有 badge | 渐变背景 + 左要点列表 + 右徽章 |
| list_solo | content_shape=list + 独占 | 白底卡片 + 图标列表纵向排列 |
| list_half | content_shape=list + 双列 | 同上，width:50% |
| grid | content_shape=grid | 3列灰格，图标+标题+描述 |
| flow | content_shape=flow | 横排图标→箭头→图标→箭头 |
| compare | content_shape=compare | 左右对照双列 |

### 8.2 颜色系统（Cherry 参考精确值）

| 颜色 | 色值 | 使用位置 |
|------|------|----------|
| primary | #165DFF | 编号圆、标题、图标、button |
| secondary | #36CFFB | 渐变端点 |
| text_main | #374151 | 正文要点 |
| text_title | #1F2937 | 模块标题 |
| text_sub | #4B5563 | 辅助说明 |
| border | #F3F4F6 | 卡片边框 |
| card_bg | #FFFFFF | 卡片背景 |
| page_bg | #F9FAFB | 页面背景 |
| shadow | 0 1px 6px rgba(22,93,255,0.06) | 卡片阴影 |

### 8.3 字号阶梯（1080px 画布，×2.41 缩放因子）

| 层级 | 字号 | 适用范围 |
|------|:--:|------|
| 头部标题 | 24px | Hero 区标题 |
| 模块标题 | 27px | 每行 h2 标题 |
| 编号圆 | 19px | 模块序号圆圈内文字 |
| 高亮正文 | 22px | highlight 型卡片要点 |
| 普通正文 | 19px | list 型卡片要点 |
| 小说明文 | 17px | grid 型描述文字 |
| 底栏 | 19px | footer 区文字 |

### 8.4 间距规范

| 参数 | 值 | 来源 |
|------|:--:|------|
| 模块间距 | 14px | Cherry space-y-1.5 ×2.41 |
| 卡片内边距 | 24px | Cherry p-2.5 ×2.41 |
| 卡片圆角 | 19px | Cherry rounded-lg ×2.41 |
| 灰格圆角 | 10px | Cherry rounded ×2.41 |
| 徽章圆角 | 10px | Cherry rounded ×2.41 |
| 徽章内边距 | 10px | Cherry p-1 ×2.41 |

---

## 九、关键文件

| 功能 | 文件 | 说明 |
|------|------|------|
| API 端点 | `archgen/api.py` | `generate_infographic_v4()` |
| LLM 拆解提示词 | `archgen/stage1_extract_prompt_v4.py` | 第一站：文章→卡片 JSON |
| 装箱引擎 | `archgen/bin_packer.py` | 第二站：卡片→行列分配 |
| Cherry 渲染引擎 | `archgen/cherry_fidelity.py` | 第三站：行列→HTML（已有） |
| 卡片 Schema | 本文档第五章 | JSON 结构定义 |
| 图标库 | `archgen/cherry_fidelity.py` → `FA_SVG` | 20-30个 SVG 图标 |

---

## 十、设计原则

1. **LLM 只做内容拆解，不做排版决策** — CSS/列型/行列分配全部在代码层
2. **结构约束优先** — density + content_shape 确定性决定布局，不依赖 LLM 审美
3. **行高固定，空间可算** — 每行 232px / 210px 死磕，溢出截断而非撑开
4. **不删内容，只合并** — 溢出时合并相邻 low list 卡片，合并不够用 JS 自缩放兜底
5. **两路径统一** — Archgen 槽位和外部文章输入统一为卡片 JSON，下游不区分
6. **渲染参数写死** — Cherry 参考的精确颜色/字号/间距全量硬编码，LLM 碰不到
