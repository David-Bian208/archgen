# 任务：行为观察助手 V1.0.0 MVP 开发

**产品版本：** V1.0.0（新产品线，独立于 Behavior Recorder Service V4.x）  
**优先级：** P0  
**负责人：** trae（分配给小治 - 后端）  
**创建人：** 战舰 🛳️（架构师）  
**创建时间：** 2026-04-07 13:30  
**截止日期：** 2026-04-14（1 周）

---

## ⚠️ 协作原则

**trae 可以反驳：**
- 任务派发是双向讨论，不是单向命令
- 可以提出技术质疑、方案修改建议、排期调整请求
- 如有分歧，战舰组织讨论，DAVID 做最终判定

---

## 📋 任务描述

开发行为观察助手 V1.0 MVP，实现两层报告系统：
1. **简单版报告**：基于基础信息生成优先级排序的问题分析
2. **复杂版方案**：分步信息收集后生成个性化干预方向

**核心价值：** AI 定位为"理性导航仪"，找出卡点 + 提供方向与顺序，而非生成具体干预方案

---

## 🎯 完成标准（必须量化）

### 功能标准

- [ ] 简单版报告生成（基于 4 项基础信息）
  - [ ] 输入：孩子年龄、主要问题行为、发生场景、核心困扰
  - [ ] 输出：5 层优先级排序的可能原因（基础→替代→维持→高级）
  - [ ] 包含：简单验证建议 + 信息缺口提示

- [ ] 分步信息收集向导（5 步，每步 1 问）
  - [ ] 第 1 步：行为具体化（选择题 + 简答）
  - [ ] 第 2 步：前因明确化（选择题 + 简答）
  - [ ] 第 3 步：后果客观化（选择题 + 简答）
  - [ ] 第 4 步：历史尝试（简答）
  - [ ] 第 5 步：个体背景（选择题）
  - [ ] 进度提示：X/5 | 已完成的问题列表

- [ ] 复杂版方案生成（基于完整信息）
  - [ ] 精确定义目标行为
  - [ ] A→B→C 行为链条分析
  - [ ] 推测行为功能 + 依据
  - [ ] 3 阶段干预方向（阶段一/二/三）
  - [ ] 本周任务（3 选 1）+ 成功标准
  - [ ] 7 天复盘提醒入口

- [ ] 免责声明：每份报告底部包含"教育参考，非医疗诊断"

### 技术标准

- [ ] 代码覆盖率 ≥85%
- [ ] 所有 API 端点有单元测试
- [ ] 前端组件有基本交互测试
- [ ] 无 P0/P1 级 Bug

### 文档标准

- [ ] API 文档（Swagger/OpenAPI）
- [ ] 用户使用指南（简单版 + 复杂版）
- [ ] 部署文档

---

## 📐 技术方案

### 架构设计

```
┌─────────────────┐
│   前端 (Vue 3)   │
│  - 输入表单      │
│  - 报告展示      │
│  - 分步向导      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  后端 (FastAPI) │
│  - /api/report/basic   (简单报告) │
│  - /api/report/detailed (复杂报告) │
│  - /api/collect/step (分步收集) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   规则引擎      │
│  - 优先级逻辑    │
│  - 模板渲染      │
└─────────────────┘
```

### 核心数据结构

```python
# 简单报告输入
class BasicReportInput(BaseModel):
    child_age: int
    behavior_description: str
    scenario: str
    parent_concern: str

# 分步信息收集
class StepInput(BaseModel):
    step_number: int  # 1-5
    answers: Dict[str, Any]

# 复杂报告输入（5 步完成后）
class DetailedReportInput(BaseModel):
    basic: BasicReportInput
    step1_behavior: Dict[str, Any]
    step2_antecedent: Dict[str, Any]
    step3_consequence: Dict[str, Any]
    step4_history: str
    step5_background: Dict[str, Any]

# 用户画像
class FamilyProfile(BaseModel):
    family_id: str
    intervention_maturity: str  # "新手型"/"实践型"/"资深型"
    completed_reports: int
    last_report_date: datetime
```

### 优先级逻辑（核心算法）

```python
# 文件：app/agents/priority_engine.py

PRIORITY_ORDER = [
    "情绪觉察与识别",      # 第一优先：基础性卡点
    "沟通表达技能缺失",    # 第二优先：替代性技能
    "感觉调节策略不足",    # 第二优先：替代性技能
    "行为结果的影响",      # 第三优先：维持性因素
    "冲动控制执行困难",    # 第四优先：高级执行
]

def generate_priority_order(detailed_info: DetailedReportInput) -> List[str]:
    """
    基于收集的信息，动态调整优先级顺序
    
    规则：
    1. 如果孩子语言能力弱 → 情绪识别优先
    2. 如果前因是身体游戏 → 身体替代优先
    3. 如果后果是获得关注 → 维持因素优先
    """
    priorities = []
    
    # 规则 1：语言能力弱 → 情绪识别最优先
    if detailed_info.step5_background.get("communication_level") in ["不太会表达", "mostly 单词"]:
        priorities.append("情绪觉察与识别")
    
    # 规则 2：前因是身体游戏 → 身体替代优先
    if "玩追逐、挠痒痒等身体游戏" in detailed_info.step2_antecedent.get("antecedents", []):
        priorities.append("沟通表达技能缺失（身体替代）")
    
    # 规则 3：后果是获得关注 → 维持因素优先
    if "满足他的需求" in detailed_info.step3_consequence.get("consequences", ""):
        priorities.append("行为结果的影响")
    
    # 合并：已识别的优先 + 默认的剩余项
    final_order = priorities + [item for item in PRIORITY_ORDER if item not in priorities]
    
    return final_order
```

### API 端点设计

```python
# 文件：app/api/endpoints/report.py

# 1. 生成简单版报告
POST /api/report/basic
Request: BasicReportInput
Response: { report_id, report_url, summary }

# 2. 提交分步信息
POST /api/collect/step
Request: { session_id, step_number, answers }
Response: { next_step, completed, progress }

# 3. 生成复杂版方案
POST /api/report/detailed
Request: { session_id }
Response: { report_id, report_url, action_items }

# 4. 获取用户画像
GET /api/profile/{family_id}
Response: FamilyProfile

# 5. 提交复盘反馈
POST /api/feedback/review
Request: { report_id, task_completed, child_reaction, difficulties }
Response: { next_suggestion }
```

---

## 🧪 测试用例

### 测试 1：简单报告生成

```python
def test_basic_report_generation():
    input = BasicReportInput(
        child_age=5,
        behavior_description="兴奋时打人",
        scenario="舞蹈课/家里",
        parent_concern="讲了道理也没用"
    )
    response = client.post("/api/report/basic", json=input.dict())
    assert response.status_code == 200
    data = response.json()
    assert "report_id" in data
    assert "5 层优先级" in data["content"]
```

### 测试 2：分步信息收集

```python
def test_step_collection():
    session_id = "test_session_001"
    
    # 第 1 步：行为具体化
    response = client.post("/api/collect/step", json={
        "session_id": session_id,
        "step_number": 1,
        "answers": {"behavior_type": ["拍打"], "other": ""}
    })
    assert response.status_code == 200
    assert response.json()["next_step"] == 2
    
    # ... 完成 5 步
    # 第 5 步完成后，应返回 completed=True
```

### 测试 3：优先级逻辑

```python
def test_priority_order_language_weak():
    """测试：语言能力弱 → 情绪识别最优先"""
    detailed_info = DetailedReportInput(
        basic=...,
        step5_background={"communication_level": "不太会表达"}
    )
    order = generate_priority_order(detailed_info)
    assert order[0] == "情绪觉察与识别"

def test_priority_order_physical_play():
    """测试：前因是身体游戏 → 身体替代优先"""
    detailed_info = DetailedReportInput(
        basic=...,
        step2_antecedent={"antecedents": ["玩追逐、挠痒痒等身体游戏"]}
    )
    order = generate_priority_order(detailed_info)
    assert "沟通表达技能缺失（身体替代）" in order[:2]
```

---

## 📁 文件结构

```
behavior_observer_service/
├── app/
│   ├── api/
│   │   └── endpoints/
│   │       └── report.py          # 报告相关 API
│   ├── agents/
│   │   ├── priority_engine.py     # 优先级逻辑
│   │   └── report_generator.py    # 报告生成器
│   ├── templates/
│   │   ├── basic_report.md        # 简单报告模板
│   │   └── detailed_report.md     # 复杂报告模板
│   └── models/
│       └── report.py              # 数据模型
├── frontend/
│   └── components/
│       ├── BasicReportForm.vue    # 简单报告表单
│       ├── StepWizard.vue         # 分步向导
│       └── ReportViewer.vue       # 报告查看器
├── tests/
│   └── test_report_generation.py  # 测试用例
└── docs/
    ├── API.md                     # API 文档
    └── USER_GUIDE.md              # 用户指南
```

---

## 📅 开发计划

### 阶段 1：核心功能（1 周）

| 任务 | 负责人 | 预计时间 | 状态 |
|------|--------|----------|------|
| 简单报告模板开发 | 小治 | 2 天 | ⏳ |
| 信息收集向导 UI | 小治 | 2 天 | ⏳ |
| 复杂方案模板开发 | 小治 | 2 天 | ⏳ |
| 优先级逻辑实现 | 小治 | 1 天 | ⏳ |

### 阶段 2：测试与优化（3 天）

| 任务 | 负责人 | 预计时间 | 状态 |
|------|--------|----------|------|
| 内部测试（5 个模拟案例） | 小测试 | 1 天 | ⏳ |
| 小范围用户测试（3-5 个家庭） | 小测试 | 2 天 | ⏳ |

### 阶段 3：部署与监控（2 天）

| 任务 | 负责人 | 预计时间 | 状态 |
|------|--------|----------|------|
| 生产环境部署 | 战舰 | 1 天 | ⏳ |
| 监控与日志配置 | 战舰 | 1 天 | ⏳ |

---

## ⚠️ 风险提示

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 信息收集流程太长，用户放弃 | 高 | 分步设计，每步<30 秒；进度提示 |
| 方案感觉模板化，用户不信任 | 中 | 强调"方向"而非"具体台词"；增加"您的决策点" |
| 用户执行后无效果，流失 | 高 | 内置"如果做不到"退出机制；7 天复盘提醒 |
| 法律风险（医疗建议） | 高 | 每份报告加免责声明 |

---

## 📞 沟通规范

- **每日站会：** 每天 10:00，小治在群里同步进度（3 句话：昨天做了什么、今天做什么、有什么卡点）
- **卡壳处理：** 如遇技术问题>30 分钟未解决，立即@战舰 求助
- **完成确认：** 每个阶段完成后，@战舰 进行代码审查

---

**派发时间：** 2026-04-07 13:30  
**预计启动：** 2026-04-07 14:00  
**预计完成：** 2026-04-14 17:00

---

## ✅ 任务确认

- [ ] DAVID（PM）：确认需求与优先级
- [ ] 战舰（架构师）：确认技术方案
- [ ] 小治（开发）：确认任务接收与排期
