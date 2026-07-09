# ArchGen - AI 写作全流程工作台

> 将 Markdown 知识库转化为高质量文章，全流程 AI 辅助

## 当前定位

ArchGen 已从初代"文章转架构图"演进为**完整的 AI 辅助写作流水线**：

```
选题 → 补充 → 角度推荐 → 槽位编排 → 内容生成 → 配图输出
```

## 核心特性

- **MCP 文件直读** — 知识库全文检索，零向量、零切块、保真度优先
- **透明推理** — 所有 AI 决策可追溯、可审计（ThinkingLogPanel）
- **人机协作** — AI 产出可编辑/确认/驳回
- **槽位编排** — 将写作任务分解为可独立操作的槽位单元
- **密度优先选题** — 基于内容质量的动态推荐（Phase 1 规划中）
- **一键配图** — HTML + Playwright 截图，支持多尺寸多风格

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置

编辑 `config/config.yaml`，设置 LLM API Key：

```yaml
llm:
  api_key: "your-api-key-here"
  base_url: "https://api.deepseek.com/v1"
  model: "deepseek-chat"
```

### 3. 启动服务

```bash
python main.py
# 访问 http://localhost:8905（端口可在 config.yaml 配置）
```

### 4. 前端开发

```bash
cd frontend
npm install
npm run dev     # 开发模式 (热更新)
npm run build   # 生产构建
```

## 项目结构

```
archgen/
├── api.py                     # FastAPI 主文件 (93 个端点, ~9100 行)
├── main.py                    # 入口
├── requirements.txt
├── config/
│   ├── config.yaml            # 主配置
│   ├── prompts.yaml           # LLM Prompt 模板
│   └── persona_dimensions.md  # 六维人设配置
├── src/
│   ├── local_folder_reader.py  # 本地文件夹 MCP 读取
│   ├── classifier.py           # 内容分类器
│   ├── degradation_chain.py    # 降级链
│   ├── knowledge_assessor.py   # 知识覆盖度评估
│   ├── web_search.py           # DuckDuckGo 搜索
│   ├── stream_utils.py         # SSE 流式工具
│   └── ... (共 20+ 模块)
├── frontend/
│   └── src/
│       ├── views/              # 14 个页面
│       ├── components/workflow/ # 11 个工作流组件
│       ├── composables/        # 8 个组合函数
│       └── utils/api.js        # API 调用层
├── templates/                  # HTML 模板 + Jinja2
├── styles/                     # CSS 样式
├── knowledge_base/             # 本地知识库 MD 文件
└── data/                       # SQLite + 缓存
```

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | FastAPI + Python 3.10+ |
| LLM | DeepSeek V4 / R1 |
| 数据库 | SQLite 3.37+ |
| 截图 | Playwright 1.44+ |
| 前端 | Vue 3 + Arco Design + Vite 4.4+ |

## 开发状态

**稳定运行中**，当前版本 v3.0。93 个 API 端点全部可用。

核心功能全部完成：
- [x] MCP 检索引擎
- [x] 选题推荐（MCP 扫描 + LLM）
- [x] 方向检测 + 角度推荐
- [x] AI 补充（L0-L4 分级）
- [x] 槽位生成 + 素材匹配
- [x] 整合生成（两步推理）
- [x] 联网搜索
- [x] 全文生成
- [x] 配图系统
- [x] 思考日志审计
- [x] 六维人设注入
- [x] A/B 测试 + 埋点

规划中：
- [ ] 选题扫描 Phase 1（密度+多样性+语义切片）
- [ ] 选题扫描 Phase 1.5（MiniLM 向量召回）
- [ ] 文章风格克隆
- [ ] 多模态知识库

## 当前状态（2026-07-07）

**v3.1：接口冻结期 ✅**

组件间接口已完全锁定（93 个 API 端点稳定运行），全链路（选题→文章）可跑通。下一步进入**内部执行精炼期**——按精确定义优化每个步骤的 AI 决策逻辑。

## 文档

| 文档 | 内容 |
|------|------|
| `ArchGen_内部执行逻辑定义_v3.1.md` | **🔴 核心**：10 个模块的内部执行逻辑精确定义（给 Trae 看） |
| `ArchGen_开发文档_v3.0_综合版.md` | 架构/进度/API/决策全景 |
| `开发工作手册.md` | 开发流程/组件接口/常见问题 |
| `ArchGen_开发规划文档.md` | 里程碑/当前状态/下一步规划 |
| `进度报告_20260706.md` | W1-W4 槽位改造详情 |
| `推荐场景透明推理规范.md` | 透明推理四原则 |

## 参与人

| 角色 | 人员 | 职责 |
|------|------|------|
| 产品 | DAVID | 需求定义、验收 |
| 架构/诊断 | 战舰 | 方案设计、质量检查 |
| 实现 | 小治 (TRAE) | 代码修复、实现 |
