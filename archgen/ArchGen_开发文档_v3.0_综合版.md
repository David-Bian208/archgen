# ArchGen 开发文档 v3.0（综合版）

> **版本:** v3.0 | **更新日期:** 2026-07-07 | **状态:** 持续迭代中  
> **参与人:** DAVID（产品）、战舰（架构/诊断）、小治 / TRAE（实现）  
> **项目路径:** `/home/admin/.openclaw/workspace/behavior_recorder_service/archgen/`

---

## 目录

1. [项目定位与目标](#一项目定位与目标)
2. [核心架构](#二核心架构)
3. [开发进度总览](#三开发进度总览)
4. [关键技术决策记录](#四关键技术决策记录)
5. [API 接口全景图](#五api-接口全景图)
6. [前端架构](#六前端架构)
7. [技术栈与依赖](#七技术栈与依赖)
8. [测试与验证](#八测试与验证)
9. [下一步规划](#九下一步规划)

---

## 一、项目定位与目标

### 1.1 当前定位

**ArchGen = AI 写作全流程工作台。**

从初代"文章转架构图"演进为**完整的 AI 辅助创作流水线**：

```
选题 → 补充 → 角度推荐 → 槽位编排 → 内容生成 → 配图输出
```

### 1.2 短期目标（1-2 周）

| 目标 | 状态 | 说明 |
|------|------|------|
| 完整选题流程 | ✅ 已上线 | MCP 扫描 → 分类 → LLM 推荐 |
| 思考日志面板 | ✅ 已上线 | 按业务阶段分组的 AI 思维审计 |
| AI 补充信息 | ✅ 已上线 | 分级补充（L0-L4）+ AI-Pulse |
| 槽位编排工作台 | ✅ 已上线 | 三栏布局 + 素材匹配 + 整合生成 |
| 文章全文生成 | ✅ 已上线 | 基于槽位提纲的端到端生成 |
| 选题扫描升级（Phase 1） | ⏳ 设计中 | 密度评分 + 多样性兜底 + 语义切片 |
| 向量检索增强（Phase 1.5） | ⏳ 设计中 | MiniLM 本地向量 + 召回去重 |

### 1.3 长期目标（2-3 月）

| 目标 | 说明 |
|------|------|
| 多模态知识库 | 支持 PDF/网页/音频转写 |
| 文章风格克隆 | 自动学习历史文章的写作风格 |
| 多人协作 | 共享知识库 + 审核工作流 |
| 一键分发 | 生成文章 → 自动适配公众号/知乎/头条排版 |

---

## 二、核心架构

### 2.1 整体架构（四步流水线）

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  选题    │ → │  补充    │ → │  写作    │ → │  输出    │
│ (Step 0) │    │ (Step 1) │    │ (Steps   │    │ (Step 7) │
│          │    │          │    │  2/3/4/5)│    │          │
├──────────┤    ├──────────┤    ├──────────┤    ├──────────┤
│ MCP 扫描 │    │ AI推断   │    │ 角度推荐 │    │ 配图生成 │
│ 方向检测 │    │ 用户补充 │    │ 框架匹配 │    │ 文章导出 │
│ 选题推荐 │    │ 完整度   │    │ 槽位生成 │    │          │
│          │    │ 评估     │    │ 内容生成 │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

### 2.2 核心设计原则

1. **先逻辑，后视觉** — 内容质量先于排版美观
2. **MCP 文件直读** — 零向量、零切块，保真度优先（Phase 1.5 仅在选题阶段用向量做召回，LLM 仍读全文）
3. **透明推理** — 所有 AI 决策可追溯、可审计 (ThinkingLogPanel)
4. **人与 AI 协作** — 任何 AI 产出都可由人编辑/确认/驳回

### 2.3 项目文件结构

```
archgen/
├── api.py                        # FastAPI 主文件 (9300+ 行，93 个端点)
├── main.py                       # 入口
├── cli.py                        # CLI 入口
├── requirements.txt              # Python 依赖
├── config/
│   ├── config.yaml               # 主配置 (LLM API Key 等)
│   ├── prompts.yaml              # LLM Prompt 模板
│   ├── persona_dimensions.md     # 六维人设配置
│   └── archgen_topic_routing.yaml # 话题路由配置
├── src/
│   ├── local_folder_reader.py    # 本地文件夹读取
│   ├── classifier.py             # 内容分类器
│   ├── router_agent.py           # 文章类型路由
│   ├── extractor_agent.py        # 结构提取
│   ├── html_generator.py         # HTML 渲染
│   ├── screenshot.py             # Playwright 截图
│   ├── storage.py                # SQLite 存储
│   ├── ai_pulse_client.py        # AI-Pulse API 客户端
│   ├── source_tag_processor.py   # Source Tag 处理
│   ├── llm_pipeline.py           # 4 阶段 LLM Pipeline
│   ├── degradation_chain.py      # 降级链
│   ├── knowledge_assessor.py     # 知识覆盖度评估
│   ├── framework_matcher.py      # 框架匹配
│   ├── web_search.py             # DuckDuckGo 搜索
│   ├── stream_utils.py           # SSE 流式工具
│   ├── ab_test_manager.py        # A/B 测试管理
│   ├── analytics_tracker.py      # 数据分析埋点
│   ├── checkpoint_manager.py     # 检查点管理
│   ├── supplement_storage.py     # 补充内容存储
│   ├── workflow_tracer.py        # 工作流追踪
│   └── mcp_hub/                  # MCP Hub 子系统
│       ├── hub_server.py
│       ├── api_routes.py
│       ├── exec_sandbox.py
│       └── services/
├── frontend/
│   ├── src/
│   │   ├── views/                # 14 个页面视图
│   │   ├── components/
│   │   │   └── workflow/         # 11 个工作流组件
│   │   ├── composables/          # 8 个组合函数
│   │   ├── utils/api.js          # API 调用层 (含 30+ 函数)
│   │   └── stores/              
│   ├── dist/                     # 构建产物
│   └── vite.config.js
├── templates/                    # HTML 模板 (含 Jinja2)
├── styles/                       # CSS 样式
├── test_data/                    # 测试数据
├── data/                         # SQLite + 缓存
├── output/                       # 生成图片输出
└── docs/
```

---

## 三、开发进度总览

### 3.1 已完成模块（按时间倒序）

#### 2026-07-07：思考日志系统 + 选题流程完善

| 模块 | 状态 | 说明 |
|------|------|------|
| ThinkingLogPanel 前端 | ✅ | 按业务阶段分组的折叠面板，实时 SSE 拉取 |
| `_call_llm` 日志函数 | ✅ | 统一异步 LLM 调用，自动记录 `phase`/`thinking_chain` |
| `_log_process_step` | ✅ | 非 LLM 步骤（扫描/分类/精选）也记录日志 |
| MCP 自动推荐日志 | ✅ | 快速路径 `_auto_recommend_topics` 走 `_call_llm` 记录 |
| `analyze_directions_v2` 日志 | ✅ | httpx → `_call_llm(phase="选题")` |
| `evaluate_completeness` 日志 | ✅ | httpx → `_call_llm(phase="补充")` |
| 前端 `session_id` 补传 | ✅ | `mcp/suggest` 调用点补传 `session_id` |
| 日志截断限制放宽 | ✅ | prompt: 8000, output: 5000, reasoning: 1000 |
| 槽位生成心跳修复 | ✅ | 120s 硬限制 → `while True` 无限循环 |
| 日志分组业务归并 | ✅ | 优先信任后端 `phase`，`call_name` 做 fallback |

#### 2026-07-06：槽位工作台改造（W1-W4 + 紧急修复）

| 模块 | 状态 | 说明 |
|------|------|------|
| W1: AI-Pulse LLM 语义匹配 | ✅ | `_match_aipulse_by_llm()` 替代关键词匹配 |
| W2-1: EditPanel PC 端适配 | ✅ | 420px → min(620px, 40vw) |
| W2-2: 整合生成 (integrate_outline) | ✅ | 单 Prompt 两步推理 + 三类 relation + from/reasoning |
| W3: 槽位联网搜索 | ✅ | DuckDuckGo 按需搜索 + 素材评估 |
| W4: 统一确认所有槽位 | ✅ | 删每行确认 → 底部统一按钮 |
| 紧急：素材文本截断修复 (3 处) | ✅ | ThreeColumnWorkbench / EditPanel / StreamSlotsPanel |
| 紧急：联网按钮始终显示 | ✅ | 去掉 `<3` 条件限制 |
| 紧急：分析双击重复 | ✅ | 删冗余 `emit('apply-analyze')` |

#### 2026-06-05：P0/P1/P2 任务

| 模块 | 状态 |
|------|------|
| P0：六维人设配置 (`persona_dimensions.md`) | ✅ |
| P0：Prompt 模板化 (`prompts.yaml`) | ✅ |
| P0：5A/5B/5C 模式选择 UI | ✅ |
| P0：内容比例约束 (理论≤20%，实战≥80%) | ✅ |
| P1：AI-Pulse 模块框架 | ✅ |
| P1：案例库结构 | ✅ |
| P2：source_tag 硬约束 | ✅ |
| P2：4 阶段 LLM Pipeline (`llm_pipeline.py`) | ✅ |
| P2：前端 source_tag 组件 | ✅ |
| P2：3 个 P2 API 端点 | ✅ |

#### 早期里程碑

| 里程碑 | 状态 | 日期 |
|--------|------|------|
| 项目骨架 + FastAPI + SQLite | ✅ | 2026-05 |
| MCP 检索引擎 (LocalFolderReader) | ✅ | 2026-05-28 |
| 框架匹配与配图系统 (V1) | ✅ | 2026-05 |
| 配图系统 v3.0 (两阶段管线) | ✅ | 2026-07-15 |
| 内容补充架构 v2.0 (L0-L4) | ✅ | 2026-06-18 |
| 透明推理规范 v1.1 | ✅ | 2026-06-18 |
| 降级链 (Chain) | ✅ | 2026-06 |
| A/B 测试 + 埋点系统 | ✅ | 2026-06 |

### 3.2 进行中

| 模块 | 进度 | 预计完成 |
|------|------|----------|
| 选题扫描 Phase 1（密度+多样性+语义切片） | 📋 设计完成 | 2026-07-08 |
| 选题扫描 Phase 1.5（向量召回 MiniLM） | 📋 设计完成 | 待 Phase 1 验收后 |

### 3.3 计划中

| 模块 | 优先级 | 说明 |
|------|--------|------|
| 配图系统 v4.0 (三站接力) | P0 | 见 `docs/IMAGE_GENERATION_SPEC.md` v4.0 |
| 文章风格克隆 | P1 | 学习历史文章语气/结构 |
| 多模态 KB (PDF/网页) | P1 | 扩展知识库格式 |
| 一键分发 | P2 | 多平台格式适配 |
| 团队协作 | P2 | 共享 KB + 审核流 |

---

## 四、关键技术决策记录

### 4.1 架构决策

| 决策点 | 决策 | 原因 |
|--------|------|------|
| **MCP 检索 vs 向量数据库** | MCP 文件直读 | 保真度优先，全文不切块 |
| **选题扫描采样** | 密度优先 + 多样性兜底 | 替换纯时间排序，防止老基石文档被遗漏 |
| **向量召回** | MiniLM + NumPy (非 Chroma) | 1000 篇以内够用，零运维 |
| **整合生成** | 单 Prompt 两步推理 | 纯文本推理无需外部调用，性价比高 |
| **Llama vs R1** | 看场景选 | 结构提取用 Llama（结构化输出），选题推荐用 R1（推理强） |
| **5A/5B/5C 模式** | 保留 3 模式，5C 为 5B 子选项 | 完整度 80/60 分段 |
| **source_tag** | 渐进实施: P0 打标签 → P2 硬约束 | 降低风险 |
| **AI-Pulse 集成** | 通过文件夹松耦合 | 两个独立软件，零耦合 |

### 4.2 思考日志设计决策

| 决策点 | 决策 | 原因 |
|--------|------|------|
| **`phase` 字段** | 后端 `_call_llm` 设置 `phase` 参数 | 业务阶段在调用时就确定 |
| **分组逻辑** | 前端优先信任 `log.phase`，`call_name` 做 fallback | 减少前端硬编码 |
| **非 LLM 步骤** | `_log_process_step` 独立记录 | 扫描/分类/精选也要可见 |
| **日志上限** | 50 条，超出删旧 | 防止 session 内存膨胀 |
| **截断限制** | prompt: 8000, output: 5000, reasoning: 1000 | 足够展示完整推理 |

### 4.3 选题扫描策略演变

```
v2.0 (旧): 每类取 mtime 最新 2 篇 + [:1500] 粗暴截断
  ↓
v3.0 Phase 1 (新): 密度评分 + 多样性兜底 + 语义切片
v3.0 Phase 1.5:  + MiniLM 向量召回 (10 篇 → 15 篇上下文)
```

**评分公式 (Phase 1):**
```
score = info_density × log(max(word_count, 1)) × 0.9^years_since_mtime
```

**语义切片 (Phase 1):**
```
保留: Front Matter + H1/H2 标题列表 + 第一段 + 最后一段
中间: 按语义块截断，截断点必须在句号/换行/代码块结束/表格结束后
```

---

## 五、API 接口全景图

### 5.1 按业务模块分类

#### 知识库与文件夹

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/kb/categories` | GET | 获取知识库分类列表 |
| `/api/kb/files` | GET | 列出知识库文件 |
| `/api/kb/read` | POST | 读取知识库文件内容 |
| `/api/folders/verify` | POST | 验证文件夹 |
| `/api/folders/list` | POST | 列出文件夹结构 |
| `/api/folders/read` | POST | 读取文件夹文件内容 |

#### MCP 检索与选题

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/mcp/search` | POST | MCP 检索：扫描 → 过滤 → 读取 → LLM 总结 |
| `/api/mcp/suggest` | POST | MCP 题材推荐 |
| `/api/mcp/match-files` | POST | 按主题匹配文件（纯关键词） |

#### 工作流 Session

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/workflow/session/create` | POST | 创建新会话 |
| `/api/workflow/session/status` | POST | 获取会话状态 |
| `/api/workflow/session/metadata` | POST | 记录元数据（埋点） |

#### 选题 + 方向

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/workflow/directions/analyze` | POST | 推荐写作方向 |
| `/api/workflow/directions/evaluate` | POST | 评估用户自定义方向 |
| `/api/workflow/direction/check` | POST | 方向检测 |
| `/api/workflow/direction/fix` | POST | 自动修正方向问题 |
| `/api/workflow/angle/recommend` | POST | 写作角度推荐（多步推理） |

#### 补充信息

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/workflow/completeness/evaluate` | POST | 评估信息完整度 |
| `/api/workflow/supplement/ai-auto` | POST | AI 自动补充 |
| `/api/workflow/supplement/ai-infer` | POST | AI 推断补充 + 匹配素材 |
| `/api/workflow/supplement/ai-pulse` | POST | AI-Pulse 补充 |
| `/api/workflow/supplement/add` | POST | 添加补充内容 |
| `/api/workflow/supplement/confirm` | POST | 确认补充内容 |
| `/api/workflow/supplement/smart` | POST | 智能补充（L0-L4） |
| `/api/workflow/supplement/degrade` | POST | 降级补充 |

#### 框架与结构

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/workflow/frameworks/match` | POST | 推荐分析框架 |
| `/api/frameworks` | POST | 获取框架定义 |
| `/api/frameworks/detail/{key}` | GET | 框架详情 |
| `/api/workflow/structures/recommend` | POST | 推荐内容结构 |

#### 槽位系统（V4）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/workflow/slot/build_material_pool` | POST | 构建素材池 |
| `/api/workflow/slot/generate_slots` | POST | SSE 流式槽位生成 |
| `/api/workflow/slot/generate_outline` | POST | 生成单个槽位提纲 |
| `/api/workflow/slot/match_materials` | POST | 素材匹配到槽位 |
| `/api/workflow/slot/batch_fill_v4` | POST | 批量填充（提纲+素材） |
| `/api/workflow/slot/integrate_outline` | POST | 整合生成连贯提纲 |
| `/api/workflow/slot/web_search` | POST | 槽位联网搜索 |
| `/api/workflow/slot/analyze` | POST | 槽位素材分析 |
| `/api/workflow/slot/content_preview` | POST | 内容预览 |
| `/api/workflow/slot/slot_relations` | POST | 槽位间关系图谱 |
| `/api/workflow/slot/pre_check_materials` | POST | 素材可行性预检 |

#### 内容生成

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/workflow/outline/generate` | POST | 生成写作提纲 |
| `/api/workflow/article/generate` | POST | 全文生成 |
| `/api/content/ai_generate_full` | POST | 一键生成全文 |
| `/api/content/smart_fill` | POST | 智能补全 |
| `/api/content/pipeline/generate` | POST | 4 阶段 Pipeline 单步 |
| `/api/content/pipeline/full_workflow` | POST | 4 阶段完整工作流 |

#### 身份定位

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/persona/parse` | POST | AI 解析身份定位 |
| `/api/persona/info` | GET | 获取身份定位信息 |
| `/api/persona/set_path` | POST | 设置身份文件路径 |
| `/api/persona/save` | POST | 保存身份内容 |

#### 思考日志

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/workflow/thinking/logs` | GET | 获取 AI 思考日志（支持增量拉取） |

#### 配图系统 v4.0

> 架构：三站接力（拆卡片→排格子→印海报），见 `docs/IMAGE_GENERATION_SPEC.md` v4.0

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/framework/suggest-from-slots` | POST | 从槽位推荐配图框架 |
| `/api/generate/infographic` | POST | 生成信息图（v4.0 三站接力） |
| `/api/generate/preview` | POST | 预览 HTML |
| `/api/generate/async` | POST | 异步生成 |
| `/api/task/{task_id}` | GET | 查询异步任务 |

#### A/B 测试与埋点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/analytics/event` | POST | 记录事件 |
| `/api/analytics/events` | GET | 获取事件列表 |
| `/api/analytics/overview` | GET | 分析概览 |
| `/api/ab-test/assign` | POST | 分组 |
| `/api/ab-test/experiments` | GET | 实验配置 |

### 5.2 总计

**共 93 个端点**（GET 19 个，POST 74 个），全部在一个文件 `api.py`（约 9100 行）。

---

## 六、前端架构

### 6.1 页面视图（14 个）

```
WorkflowView.vue     ← 核心工作流页面（Step 0-7）
HomeView.vue          ← 首页
SettingsView.vue      ← 设置
PersonaSettingsView.vue ← 人设配置
MCPSearchView.vue     ← MCP 搜索
TopicSuggestView.vue  ← 选题建议
DirectionSuggestView.vue ← 方向推荐
FrameworkSelectView.vue  ← 框架选择
StructuredFormView.vue   ← 结构化表单
DataInputView.vue     ← 数据输入
PreviewView.vue       ← 预览
TextPreviewView.vue   ← 文本预览
OutputView.vue        ← 输出
NotFoundView.vue      ← 404
```

### 6.2 工作流组件（11 个）

```
StepDirection.vue     ← Step 0: 选题
StepSupplement.vue    ← Step 1: 补充信息
StepFramework.vue     ← Step 2: 框架推荐
ThreeColumnWorkbench.vue ← Step 3: 槽位工作台（三栏）
SlotCard.vue          ← 槽位卡片
EditPanel.vue         ← 槽位编辑弹窗
StreamSlotsPanel.vue  ← 槽位流式面板
StepContent.vue       ← Step 4-5: 内容生成
FrameworkWorkbench.vue ← 框架工作台
ThinkingLogPanel.vue  ← 思考日志面板
WorkflowModals.vue    ← 工作流弹出层
```

### 6.3 组合函数（8 个）

```
useSession.js         ← 会话单例
useWorkflowState.js   ← 工作流状态管理
useStep0_Topics.js    ← 选题业务逻辑
useStep2_Framework.js ← 框架业务逻辑
useStep3_Workbench.js ← 槽位工作台业务逻辑
useStep4_Outline.js   ← 提纲业务逻辑
useStep5_Article.js   ← 文章业务逻辑
useStep7_Images.js    ← 配图业务逻辑 (v4.0 三站接力)
```

---

## 七、技术栈与依赖

### 后端

| 组件 | 技术 | 版本 |
|------|------|------|
| 框架 | FastAPI | 0.100+ |
| Python | Python | 3.10+ |
| LLM | DeepSeek V4 / R1 | — |
| 数据库 | SQLite | 3.37+ |
| 截图 | Playwright | 1.44+ |
| 模板引擎 | Jinja2 | 3.0+ |
| 搜索 | DuckDuckGo (duckduckgo_search) | — |

### 前端

| 组件 | 技术 | 版本 |
|------|------|------|
| 框架 | Vue 3 | 3.3+ |
| 构建 | Vite | 4.4+ |
| UI 库 | Arco Design Vue | 2.5+ |
| 工具库 | dayjs, axios | — |

### 开发工具

| 工具 | 用途 |
|------|------|
| `npm run build` | 前端构建 (dist/) |
| `python3 main.py` | 启动 FastAPI 服务 |
| `python3 -c "import api"` | 后端语法检查 |

---

## 八、测试与验证

### 8.1 系统测试

| 测试项 | 日期 | 结果 |
|--------|------|------|
| P0/P1/P2 综合测试 (11 项) | 2026-06-05 | ✅ 11/11 通过 |
| 前端构建 | 每次变更 | ✅ 持续通过 |
| 后端语法检查 | 每次变更 | ✅ 持续通过 |
| 思考日志端到端 (选题流程) | 2026-07-07 | ✅ 4 条日志，分组正确 |
| 槽位 SSE 流式生成 | 2026-07-06 | ✅ 心跳修复后正常工作 |

### 8.2 功能验收清单

- [x] MCP 文件夹扫描 + 分类 + LLM 推荐选题
- [x] 方向检测 + 角度推荐（3 步）
- [x] 信息完整度评估（L0-L4）
- [x] 槽位生成 + 素材匹配 + 批量填充
- [x] 整合生成（两步推理）
- [x] 联网按需搜索
- [x] 思考日志面板（分组 + 折叠 + 实时增量）
- [x] 六维人设注入
- [x] 内容比例约束（理论 ≤20%，实战 ≥80%）
- [x] source_tag 处理链
- [x] A/B 测试 + 埋点
- [x] 配图生成（HTML + Playwright）

---

## 九、下一步规划

### Phase 1: 选题扫描升级（立即）

```
Week 1:
  ├─ 1.1 smart_truncate() → 替换 [:1500]
  ├─ 1.2 calc_heuristic_density() (A: FM dense字段 + B: 启发式)
  ├─ 1.3 密度优先 + 多样性兜底精选
  └─ 1.4 日志 Step 1-3 扁平化显示
```

### Phase 1.5: 向量检索增强（Phase 1 验收后）

```
  ├─ 2.1 requirements.txt → sentence-transformers
  ├─ 2.2 build_index.py (MiniLM 384维)
  ├─ 2.3 启动时 load_vectors + get_embedding_model
  ├─ 2.4 search_similar + recall_with_dedup
  ├─ 2.5 选题逻辑接入 (10 → 15 篇上下文)
  └─ 2.6 日志 Step 4
```

### 后续 P1/P2

- 文章风格克隆
- 多模态知识库
- 一键分发
- 团队协作

---

## 附录

### 附录 A: 文档索引

| 文档 | 用途 |
|------|------|
| `开发工作手册.md` | 开发流程、Skill 使用、常见问题 |
| `ArchGen_开发规划文档.md` | 原始架构规划 (v0.1) |
| `进度报告_20260706.md` | W1-W4 改造详情 |
| `ArchGen_v2.0_开发总结_2026-06-05.md` | P0/P1/P2 总结 |
| `开发文档_v2.0_MCP 检索增强版.md` | v2.0 定位变更 |
| `推荐场景透明推理规范.md` | 透明推理四原则 |
| `内容补充架构设计.md` | L0-L4 补充分级 |
| `降级链 (Chain) 实现规范.md` | 降级策略 |
| `知识评估 (AI-Assess)API 设计.md` | 知识评估 API |
| `Cherry_Studio 架构借鉴方案.md` | 借鉴分析 |
| `A_B 测试与数据埋点方案.md` | 实验框架 |
| `前端交互流程图.md` | 交互流程 |
| `QUICKSTART.md` | 快速开始 |

### 附录 B: 环境变量

| 变量 | 用途 |
|------|------|
| `LLM_API_KEY` | LLM API Key |
| `LLM_BASE_URL` | LLM Base URL |
| `LLM_MODEL` | 默认模型名 |
| `DEFAULT_MD_DIR` | 知识库 MD 根目录（build_index.py） |

---

**文档维护:** 战舰 / DAVID  
**最后更新:** 2026-07-07  
**下次更新:** Phase 1 验收后
