# Behavior Recorder Service 技术设计文档

> **版本：** V4.10.4  
> **创建时间：** 2026-03-30  
> **最后更新：** 2026-03-30  
> **状态：** ✅ 已启用

---

## 📋 技术栈

### 后端

| 组件 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **Web 框架** | FastAPI | >=0.104.0 | 异步 API 框架 |
| **服务器** | Uvicorn | >=0.24.0 | ASGI 服务器 |
| **生产部署** | Gunicorn | >=21.0.0 | WSGI HTTP 服务器 |
| **HTTP 客户端** | HTTPX | >=0.25.0 | 异步 HTTP 请求 |
| **配置管理** | PyYAML | >=6.0 | YAML 配置解析 |
| **环境变量** | python-dotenv | >=1.0.0 | .env 文件加载 |
| **文件操作** | aiofiles | >=23.0.0 | 异步文件读写 |

### 前端

| 组件 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **框架** | Vue 3 | 最新 | Composition API |
| **构建工具** | Vite | 4.5.14 | 快速开发服务器 |
| **UI 框架** | 原生 CSS | - | 轻量级 |
| **HTTP 客户端** | Axios/Fetch | - | API 调用 |

### AI 服务

| 组件 | 技术 | 说明 |
|------|------|------|
| **LLM 提供商** | DeepSeek | 通过 OpenAI 兼容 API |
| **模型** | deepseek-chat | 主要分析模型 |
| **备用模型** | Qwen | 阿里云 DashScope |

### 部署环境

| 组件 | 技术 | 说明 |
|------|------|------|
| **操作系统** | Linux | Ubuntu 20.04+ |
| **Python** | 3.10+ | 后端运行环境 |
| **Node.js** | 18+ | 前端构建环境 |
| **部署平台** | 阿里云 | 云服务器 |

---

## 🏗️ 项目结构

```
behavior_recorder_service/
├── main.py                      # 应用入口
├── config.yaml                  # 配置文件（敏感信息移至.env）
├── .env                         # 环境变量（不提交）
├── .env.example                 # 环境变量示例
├── requirements.txt             # Python 依赖
├── AGENTS.md                    # AI 开发指令
├── PRD.md                       # 产品需求文档
├── TECH_DESIGN.md               # 技术设计文档
│
├── app/                         # 应用核心代码
│   ├── config.py                # 配置加载模块
│   ├── agents/                  # AI 代理模块
│   │   ├── structured_assessor_v4.py  # V4 结构化评估
│   │   ├── insight_analyzer.py        # 洞察分析
│   │   └── intervention_planner.py    # 干预规划
│   ├── knowledge/               # 知识库
│   │   ├── intervention_scene_mapping.md  # 场景映射
│   │   └── ...                  # 其他知识文件
│   └── utils/                   # 工具函数
│
├── api/                         # API 层
│   ├── endpoints_v4.py          # V4 API 端点
│   └── __init__.py
│
├── frontend/                    # 前端代码
│   ├── index.html               # 入口 HTML
│   ├── App.vue                  # 根组件
│   ├── main.js                  # 入口 JS
│   ├── pages/                   # 页面组件
│   ├── utils/                   # 工具函数
│   └── dist/                    # 构建输出
│
├── tests/                       # 测试代码
│   ├── test_checklist.md        # 测试清单
│   └── ...                      # 测试文件
│
├── scripts/                     # 脚本工具
│   ├── start-all.sh             # 启动脚本
│   ├── stop-all.sh              # 停止脚本
│   └── status.sh                # 状态检查
│
└── docs/                        # 文档
    ├── 阿里云部署指南.md
    └── ops_notes.md
```

---

## 📊 数据模型

### 行为记录 (BehaviorRecord)

```python
class BehaviorRecord(BaseModel):
    id: str                          # 记录 ID
    child_name: str                  # 儿童姓名（可选）
    child_age: int                   # 儿童年龄（可选）
    antecedent: str                  # 情境（前因）
    behavior: str                    # 行为描述
    consequence: str                 # 结果（后果）
    time: datetime                   # 发生时间
    location: str                    # 地点
    intensity: int = 3               # 强度等级 (1-5)
    created_at: datetime             # 创建时间
```

### 分析请求 (AnalyzeRequest)

```python
class AnalyzeRequest(BaseModel):
    records: list[BehaviorRecord]    # 行为记录列表
    context: str                     # 额外情境信息
    focus_areas: list[str] = []      # 关注领域（可选）
```

### 分析结果 (AnalyzeResult)

```python
class AnalyzeResult(BaseModel):
    id: str                          # 分析 ID
    capability_hypothesis: str       # 能力假设
    inferred_hypotheses: list[str]   # 推断假设列表
    confidence: float                # 置信度 (0-1)
    scene_category: str              # 场景分类
    intervention_suggestions: list[InterventionSuggestion]
    created_at: datetime
```

### 干预建议 (InterventionSuggestion)

```python
class InterventionSuggestion(BaseModel):
    focus: str                       # 干预重点
    directions: list[str]            # 可尝试方向
    scene_bridge: str                # 场景衔接说明
    disclaimer: str                  # 免责声明
```

### 评估报告 (AssessmentReport)

```python
class AssessmentReport(BaseModel):
    summary: str                     # 摘要（100 字内）
    core_challenge: str              # 核心挑战
    ability_pattern: str             # 能力模式解读
    capability_gap: str              # 能力缺口
    intervention_framework: str      # 干预框架
    disclaimer: str                  # 免责声明
    generated_at: datetime
```

---

## 🔄 核心流程

### 1. 行为分析流程

```
用户输入 ABC 记录
    ↓
前端验证
    ↓
调用 /api/v4/analyze
    ↓
后端验证（安全检查）
    ↓
调用 AI 分析（structured_assessor_v4）
    ↓
生成行为功能假设
    ↓
场景分类（intervention_planner）
    ↓
生成干预建议
    ↓
返回分析结果
    ↓
前端展示
```

### 2. 报告生成流程

```
用户请求生成报告
    ↓
调用 /api/v4/report
    ↓
获取分析结果
    ↓
调用 insight_analyzer
    ↓
生成临床推理分析
    ↓
生成摘要、核心挑战、能力模式
    ↓
生成干预框架
    ↓
返回完整报告
    ↓
前端展示/导出
```

---

## 🔌 API 设计

### API 端点

| 端点 | 方法 | 说明 | 认证 |
|------|------|------|------|
| `/api/v4/analyze` | POST | 行为分析 | 可选 |
| `/api/v4/report` | POST | 生成报告 | 可选 |
| `/api/v4/records` | GET | 获取记录列表 | 可选 |
| `/api/v4/records` | POST | 创建记录 | 可选 |
| `/health` | GET | 健康检查 | 无 |

### 请求/响应示例

**分析请求：**
```json
POST /api/v4/analyze
{
  "records": [
    {
      "antecedent": "在幼儿园，老师让小朋友们轮流玩玩具",
      "behavior": "小明直接抢走小红的玩具，跑到一边自己玩",
      "consequence": "老师批评了小明，让他把玩具还给小红"
    }
  ],
  "context": "小明，5 岁，诊断为自闭症谱系障碍"
}
```

**分析响应：**
```json
{
  "id": "analysis_001",
  "capability_hypothesis": "社交认知能力还在发展中",
  "inferred_hypotheses": ["寻求关注", "获取物品"],
  "confidence": 0.85,
  "scene_category": "共同游戏场景",
  "intervention_suggestions": [
    {
      "focus": "社交信号监测能力",
      "directions": [
        "在日常生活中创造练习机会",
        "使用视觉提示辅助理解",
        "及时强化积极行为"
      ],
      "scene_bridge": "针对'忽略他人反应'这一具体困难...",
      "disclaimer": "本报告仅供参考，建议咨询专业治疗师"
    }
  ]
}
```

---

## 🔐 安全设计

### API 安全

```python
# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 速率限制（未来）
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v4/analyze")
@limiter.limit("10/minute")
async def analyze(request: Request, ...):
    pass
```

### 数据安全

```python
# 输入验证
class BehaviorRecord(BaseModel):
    antecedent: str = Field(..., min_length=1, max_length=1000)
    behavior: str = Field(..., min_length=1, max_length=1000)
    consequence: str = Field(..., min_length=1, max_length=1000)

# 敏感信息脱敏
def anonymize_record(record: BehaviorRecord) -> dict:
    return {
        "id": record.id,
        "antecedent": record.antecedent,
        "behavior": record.behavior,
        "consequence": record.consequence,
        # 移除个人信息
    }
```

### AI 安全

```python
# 危险关键词检测
DANGER_KEYWORDS = ["火", "刀", "高处", "交通", ...]

def contains_danger_keywords(text: str) -> bool:
    # 带上下文验证，避免误报
    # "发火"（发脾气）不应误报为"火"（危险）
    pass

# 安全优先模式
if contains_danger_keywords(text):
    return safe_response()  # 降级到安全建议
```

---

## 📈 性能设计

### 优化目标

| 指标 | 目标值 | 当前值 |
|------|--------|--------|
| 单次分析时间 | <10s | 5.8s |
| P95 响应时间 | <15s | - |
| 并发 10 请求成功率 | >90% | 50% (待优化) |
| 超时率 | <5% | 已优化至<1% |

### 优化策略

**已实施：**
```python
# 1. API 超时优化：30s → 60s
httpx.AsyncClient(timeout=60.0)

# 2. 前端 loading 提示
"分析需要 5-10 秒，请耐心等待..."

# 3. 错误提示优化
区分超时/其他错误
```

**计划实施：**
```python
# 1. 异步架构（Redis + Celery）
# 2. 结果缓存
# 3. 数据库优化
# 4. CDN 静态资源
```

---

## 🧪 测试策略

### 测试层次

```
┌─────────────────────────────────┐
│         E2E 测试                 │  ← 用户流程
├─────────────────────────────────┤
│         集成测试                 │  ← API 端点
├─────────────────────────────────┤
│         单元测试                 │  ← 函数/类
└─────────────────────────────────┘
```

### 测试覆盖目标

| 模块 | 覆盖率目标 | 当前 |
|------|------------|------|
| app/agents/ | >90% | - |
| api/endpoints/ | >85% | - |
| app/utils/ | >95% | - |
| 整体 | >85% | - |

### 关键测试用例

**P0 级（必须通过）：**
```python
def test_danger_keywords_trigger_safe_mode():
    """危险关键词触发安全模式"""
    pass

def test_intervention_matches_scene():
    """干预建议与场景匹配"""
    pass

def test_report_summary_consistent_with_analysis():
    """报告摘要与后文分析一致"""
    pass
```

**P1 级（重要）：**
```python
def test_empty_input_handling():
    """空输入处理"""
    pass

def test_api_timeout_handling():
    """API 超时处理"""
    pass

def test_concurrent_requests():
    """并发请求处理"""
    pass
```

---

## 🚀 部署方案

### 开发环境

```bash
# 后端
cd behavior_recorder_service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

### 生产环境（阿里云）

```bash
# 后端
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile access.log \
  --error-logfile error.log

# 前端
npm run build
# dist/ 目录部署到 Nginx
```

### 环境变量

```bash
# .env
LLM_API_KEY=sk-your-key-here
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DEBUG=false
```

---

## 📚 技术债务

### 已知问题

| 问题 | 影响 | 优先级 | 计划 |
|------|------|--------|------|
| 并发性能不足 | 10 并发 50% 超时 | 🔴 高 | V4.11.0 |
| 前端无状态管理 | 刷新丢失数据 | 🟡 中 | V4.11.0 |
| 无用户系统 | 数据无法同步 | 🟡 中 | V4.11.0 |
| 测试覆盖不足 | 回归风险 | 🟡 中 | 持续改进 |

### 重构计划

**V4.11.0：**
- [ ] 异步架构（Redis + Celery）
- [ ] 用户系统
- [ ] 数据库持久化

**V5.0.0：**
- [ ] 前端重构（TypeScript）
- [ ] API 版本管理
- [ ] 微服务拆分（可选）

---

## 📖 参考资料

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Vue 3 官方文档](https://vuejs.org/)
- [DeepSeek API 文档](https://platform.deepseek.com/)
- [ABC 行为分析理论](https://en.wikipedia.org/wiki/Three-term_contingency)

---

## 🔄 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 1.0.0 | 2026-03-30 | 初始版本 |

---

**本文档应与 PRD.md、AGENTS.md 配合使用。**
