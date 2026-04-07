# Behavior Recorder Service - Trae IDE 项目上下文

> **创建时间：** 2026-03-30  
> **项目版本：** V4.10.4  
> **用途：** 帮助 Trae AI 理解项目背景和开发规范

---

## 📋 项目概述

**项目名称：** Behavior Recorder Service（行为观察伙伴）  
**定位：** AI 驱动的自闭症儿童行为观察与评估工具  
**理论基础：** ABC 行为分析理论（Antecedent-Behavior-Consequence）

**核心价值：**
- 帮助家长和治疗师记录儿童行为
- AI 生成行为功能假设
- 提供场景化干预建议
- 生成结构化评估报告

**目标用户：**
- 自闭症儿童家长（核心用户）
- 康复机构治疗师
- 特教老师

---

## 🛠️ 技术栈

### 后端
| 组件 | 技术 | 版本 |
|------|------|------|
| Web 框架 | FastAPI | >=0.104.0 |
| 服务器 | Uvicorn | >=0.24.0 |
| HTTP 客户端 | HTTPX | >=0.25.0 |
| 配置管理 | PyYAML | >=6.0 |
| 环境变量 | python-dotenv | >=1.0.0 |

### 前端
| 组件 | 技术 | 版本 |
|------|------|------|
| 框架 | Vue 3 | 最新 |
| 构建工具 | Vite | 4.5.14 |
| UI | 原生 CSS | - |

### AI 服务
| 组件 | 技术 | 说明 |
|------|------|------|
| LLM 提供商 | DeepSeek | 通过 OpenAI 兼容 API |
| 模型 | deepseek-chat | 主要分析模型 |

---

## 📁 项目结构

```
behavior_recorder_service/
├── main.py                      # 应用入口
├── config.yaml                  # 配置文件
├── .env                         # 环境变量（不提交）
├── requirements.txt             # Python 依赖
│
├── AGENTS.md                    # AI 开发指令 ⭐
├── PRD.md                       # 产品需求文档 ⭐
├── TECH_DESIGN.md               # 技术设计文档 ⭐
├── RESEARCH.md                  # 需求调研 ⭐
│
├── app/                         # 应用核心代码
│   ├── config.py                # 配置加载
│   ├── agents/                  # AI 代理模块
│   │   ├── structured_assessor_v4.py
│   │   ├── insight_analyzer.py
│   │   └── intervention_planner.py
│   ├── knowledge/               # 知识库
│   └── utils/                   # 工具函数
│
├── api/                         # API 层
│   └── endpoints_v4.py          # V4 API 端点
│
├── frontend/                    # 前端代码
│   ├── App.vue
│   ├── main.js
│   └── pages/
│
├── tests/                       # 测试代码
│   └── test_checklist.md        # 测试清单 ⭐
│
└── scripts/                     # 脚本工具
    ├── start-all.sh
    ├── stop-all.sh
    └── status.sh
```

---

## 📖 核心文档说明

### AGENTS.md - AI 开发指令（最重要）
- **用途：** 告诉 AI 在这个项目中应该遵循什么规则
- **内容：** 开发规范、安全要求、临床系统特殊要求
- **AI 必读：** 所有 AI 助手（包括 Trae）必须遵守

### PRD.md - 产品需求文档
- **用途：** 明确产品功能边界
- **内容：** MVP 功能、目标用户、版本规划
- **开发依据：** 所有功能开发前查阅

### TECH_DESIGN.md - 技术设计文档
- **用途：** 技术实现蓝图
- **内容：** 数据模型、API 设计、安全设计
- **开发参考：** 编码时查阅

### RESEARCH.md - 需求调研
- **用途：** 产品和竞品分析
- **内容：** 用户画像、技术选型、风险识别

### test_checklist.md - 测试清单
- **用途：** 测试执行指南
- **内容：** P0/P1/P2 测试用例
- **质量保障：** 提交前必须通过

---

## 🎯 开发规范

### Python 代码风格
```python
# ✅ 函数名使用 snake_case
def analyze_behavior(context: str, behavior: str) -> dict:
    pass

# ✅ 类名使用 PascalCase
class BehaviorAnalyzer:
    pass

# ✅ 使用类型提示
def process_data(data: list[str]) -> dict[str, float]:
    pass

# ✅ 异步端点使用 async/await
@app.post("/api/v4/analyze")
async def analyze_endpoint(request: AnalyzeRequest):
    pass
```

### Vue 代码风格
```vue
<script setup>
// ✅ 使用 Composition API
import { ref, computed, onMounted } from 'vue'

// ✅ 响应式变量
const loading = ref(false)
const report = ref(null)
</script>
```

---

## 🔐 安全要求

### API Key 管理
```bash
# ✅ 使用环境变量
LLM_API_KEY=sk-your-key-here
LLM_BASE_URL=https://api.deepseek.com

# ❌ 禁止硬编码
api_key = "sk-xxx"  # 禁止！
```

### 临床系统安全
```python
# ✅ 危险行为优先处理安全
if contains_danger_keywords(text):
    return safe_response()

# ✅ 不确定时保守处理
if confidence < 0.7:
    return conservative_response()

# ✅ 明确免责声明
disclaimer = "本报告仅供参考，建议咨询专业治疗师"
```

---

## 🧪 测试要求

### P0 测试（必须 100% 通过）
1. 安全优先模式触发
2. 干预建议与场景匹配
3. 报告摘要与后文一致
4. API 超时处理
5. 空输入处理

### 测试执行
```bash
# 运行测试
pytest tests/ -v --cov=app

# 查看覆盖率
open htmlcov/index.html
```

---

## 🚀 常用命令

### 开发环境
```bash
# 启动后端
cd behavior_recorder_service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 启动前端
cd frontend
npm install
npm run dev
```

### 测试
```bash
# 执行 P0 测试
pytest tests/test_p0_regression.py -v

# 查看测试报告
cat tests/test_checklist.md
```

### 部署
```bash
# 生产启动
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

---

## ⚠️ 禁止事项

### 代码层面
```python
# ❌ 禁止硬编码敏感信息
api_key = "sk-xxx"

# ❌ 禁止忽略异常
try:
    dangerous_operation()
except:
    pass  # 禁止！

# ❌ 禁止使用 eval/exec
eval(user_input)  # 禁止！
```

### 临床层面
```markdown
# ❌ 禁止诊断结论
"您的孩子患有自闭症"  # 禁止！

# ❌ 禁止治疗方案
"建议每天训练 3 小时"  # 禁止！

# ❌ 禁止绝对化表述
"一定会改善"  # 禁止！
```

---

## 📚 相关资源

### 核心文档

| 资源 | 位置 | 用途 |
|------|------|------|
| AGENTS.md | 项目根目录 | AI 开发指令 |
| PRD.md | 项目根目录 | 产品需求 |
| TECH_DESIGN.md | 项目根目录 | 技术设计 |
| test_checklist.md | tests/ | 测试清单 |
| SECURITY_GUIDELINES.md | workspace | 安全指南 |

### 架构优化文档

| 资源 | 位置 | 用途 |
|------|------|------|
| 团队职责分工表.md | workspace/ | 3 角色 10 职责定义 |
| WORKFLOW.md | workspace/ | 6 阶段标准流程 |
| skills/README.md | workspace/skills/ | Skills 技能系统 |

---

## 🛠️ Skills 技能系统（trae 专用）

### 什么是 Skills

Skills 是可插拔的技能包，帮助你更好地完成开发工作。

### 可用 Skills（6 个）

**通用技能（3 个）：**
- `dev-test` - 测试生成、运行、分析
- `dev-context` - 项目结构、模块依赖  
- `dev-logs` - 日志查看、搜索、分析

**领域技能（3 个）：**
- `clinical-rules` - 查询 14 条临床规则
- `report-style` - 检查报告语言风格
- `safety-check` - 安全关键词检测

### 使用 Skills

```bash
# 1. 加载技能
cd /home/admin/.openclaw/workspace/skills
python3 loader.py load -p behavior-recorder

# 2. 调用技能
cd skills/generic/dev-test
python3 executor.py "为这个函数生成单元测试：analyze_behavior"

cd skills/domains/behavior-recorder/clinical-rules
python3 executor.py "查询临床规则"

cd skills/domains/behavior-recorder/safety-check
python3 executor.py "检查这个行为是否安全：小明玩火"
```

### 完整文档

`/home/admin/.openclaw/workspace/skills/README.md`

---

## 🔄 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 1.0.0 | 2026-03-30 | 初始版本 |

---

**Trae AI 必读：开始编码前，请先阅读 AGENTS.md！**
