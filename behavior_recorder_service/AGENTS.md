# Behavior Recorder Service 开发指令

> **版本：** 1.2.0  
> **创建时间：** 2026-03-30  
> **最后更新：** 2026-04-01  
> **状态：** ✅ 已启用

---

## 📋 项目概述

**项目名称：** Behavior Recorder Service（行为观察伙伴）  
**版本：** V4.11.1（claw-code 架构优化版）  
**技术栈：** FastAPI + Vue 3  
**定位：** 自闭症儿童行为观察与评估工具

**核心价值：**
- 基于 ABC 行为分析理论
- AI 驱动的行为功能假设生成
- 场景化干预建议
- 结构化评估报告

---

## 🏗️ V4.11.1 新增模块（2026-04-01）

### claw-code 架构优化成果

**灵感来源：** https://github.com/instructkr/claw-code (OmX 工作流模式)

#### 1. 覆盖率审计模块

**位置：** `tests/parity_audit.py`

**功能：**
- 5 个维度覆盖率量化（临床假设、干预模板、场景分类、安全检查、测试案例）
- `is_deployable()` 判断系统是否可部署
- Markdown 审计报告生成

**使用：**
```bash
# 运行审计
python3 tests/parity_audit.py

# 输出
| 维度 | 覆盖率 | 状态 |
|------|--------|------|
| 临床假设 | 5/5 (100%) | ✅ |
| 干预模板 | 3/3 (100%) | ✅ |
| 场景分类 | 10/10 (100%) | ✅ |
| 安全检查 | 5/5 (100%) | ✅ |
| 测试案例 | 18/18 (100%) | ✅ |
| **总体** | **100%** | **✅ 优秀** |

✅ 系统可部署
```

---

#### 2. 临床规则注册表

**位置：** `app/knowledge/clinical_rules_registry.py`

**功能：**
- 14 条临床规则统一管理
- 规则匹配、查询、统计
- 已集成到 `intervention_planner.py`

**规则分类：**
- safety: 2（安全优先）
- social: 3（社交功能）
- rigidity: 2（坚持同一性）
- sensory: 2（感觉寻求）
- avoidance: 2（逃避需求）
- attention: 1（寻求关注）
- prompt_dependent: 2（提示依赖）

**使用：**
```python
from app.knowledge.clinical_rules_registry import get_clinical_rules_registry

registry = get_clinical_rules_registry()
matches = registry.evaluate("小明看到打火机想拿起来玩火")
```

---

#### 3. 自动化回归测试

**位置：** `tests/test_parity_audit.py`

**测试套件：**
- TestParityAudit (9 测试) - 覆盖率审计
- TestClinicalRulesRegistry (8 测试) - 规则注册表

**运行：**
```bash
pytest tests/test_parity_audit.py -v

# 输出
======================== 17 passed in 0.06s =========================
```

---

#### 4. Skills 技能系统

**位置：** `/home/admin/.openclaw/workspace/skills/`

**架构：** 混合技能（通用 + 领域）

**通用技能（3 个）：**
- dev-test - 测试生成、运行、分析
- dev-context - 项目结构、模块依赖
- dev-logs - 日志查看、搜索、分析

**领域技能（3 个）：**
- clinical-rules - 临床规则查询
- report-style - 报告风格检查
- safety-check - 安全关键词检测

**使用：**
```bash
# 加载技能
cd /home/admin/.openclaw/workspace/skills
python3 loader.py load -p behavior-recorder

# 调用技能
cd skills/domains/behavior-recorder/clinical-rules
python3 executor.py "查询临床规则"
```

**完整文档：** `/home/admin/.openclaw/workspace/skills/README.md`

---

## 🎯 开发规范

### 代码风格

**Python 后端：**
```python
# ✅ 函数名使用 snake_case
def analyze_behavior(context: str, behavior: str) -> dict:
    pass

# ✅ 类名使用 PascalCase
class BehaviorAnalyzer:
    pass

# ✅ 常量使用 UPPER_SNAKE_CASE
DEFAULT_MODEL = "deepseek-chat"

# ✅ 使用类型提示
def process_data(data: list[str]) -> dict[str, float]:
    pass

# ✅ 异步端点使用 async/await
@app.post("/api/v4/analyze")
async def analyze_endpoint(request: AnalyzeRequest):
    pass
```

**Vue 前端：**
```vue
<script setup>
// ✅ 使用 Composition API
import { ref, computed, onMounted } from 'vue'

// ✅ 响应式变量
const loading = ref(false)
const report = ref(null)

// ✅ 计算属性
const isValid = computed(() => report.value && report.value.status === 'complete')

// ✅ 生命周期钩子
onMounted(async () => {
  await loadData()
})
</script>
```

---

### 文档规范

**注释要求：**
```python
# ✅ 函数必须有 docstring
def analyze_behavior(context: str, behavior: str) -> dict:
    """
    分析行为模式并生成假设

    Args:
        context: 行为发生的情境描述
        behavior: 具体行为描述

    Returns:
        包含行为功能假设的字典

    Raises:
        ValueError: 当输入为空时
    """
    pass
```

**文件头注释：**
```python
"""
行为观察伙伴 V4.11.0
模块说明：XXX 模块负责 XXX 功能
"""
```

---

## 🔐 安全要求

### 敏感信息管理

```bash
# ✅ API Key 使用环境变量
LLM_API_KEY=sk-your-key-here
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

# ❌ 禁止硬编码
api_key = "sk-578100de3afd494ca759cc096a4a1aaa"  # 禁止！
```

### .env 文件规则

```bash
# ✅ .env - 真实配置（不提交）
LLM_API_KEY=sk-real-key

# ✅ .env.example - 示例（可提交）
LLM_API_KEY=sk-your-api-key-here

# ✅ .gitignore 必须包含
.env
.env.*
!.env.example
```

### 数据安全

```python
# ✅ 临床数据脱敏
def anonymize_data(data: dict) -> dict:
    return {
        "age_range": "3-5 岁",  # 不显示具体年龄
        "gender": "女",  # 保留性别
        # 移除姓名、地址等个人信息
    }

# ✅ 日志不记录敏感信息
logger.info(f"分析请求：{request.id}")  # ✅
logger.info(f"用户数据：{request.user_data}")  # ❌ 禁止
```

---

## 🏥 临床系统特殊要求

### 安全第一原则

```python
# ✅ 危险行为优先处理安全
if contains_danger_keywords(text):
    return safe_response()  # 降级到安全优先模式

# ✅ 不确定时保守处理
if confidence < 0.7:
    return conservative_response()  # 保守方案

# ✅ 明确免责声明
disclaimer = "本报告仅供参考，建议咨询专业治疗师"
```

### 干预建议边界

```markdown
# ✅ 通用框架
干预重点通常是 X 能力的培养，可尝试以下方向：
1. 在日常生活中创造练习机会
2. 使用视觉提示辅助理解
3. 及时强化积极行为

# ❌ 禁止具体医疗建议
你应该每天训练 3 次，每次 30 分钟...  # 禁止！
```

### 报告语言风格

```markdown
# ✅ 能力发展视角
"玥玥还没学会如何识别他人的社交信号"

# ❌ 缺陷视角
"玥玥不会识别他人的社交信号"

# ✅ "我们"视角
"从玥玥的表现来看，我们觉得..."

# ❌ 说教感
"临床上通常考虑几种可能性"
```

---

## 🧪 测试要求

### 测试覆盖

```python
# ✅ 单元测试
class TestBehaviorAnalyzer:
    def test_analyze_normal_case(self):
        """测试正常案例"""
        pass

    def test_analyze_danger_keywords(self):
        """测试危险关键词触发"""
        pass

    def test_analyze_empty_input(self):
        """测试空输入处理"""
        pass
```

### 测试清单

```markdown
## 功能测试
- [ ] API 端点正常响应
- [ ] AI 分析结果准确
- [ ] 干预建议匹配场景
- [ ] 报告生成完整
- [ ] 错误处理友好

## 安全测试
- [ ] 危险行为触发安全模式
- [ ] API Key 不泄露
- [ ] 日志不记录敏感信息
- [ ] 免责声明显示

## 性能测试
- [ ] 单次请求 <10 秒
- [ ] 并发 10 请求成功率 >90%
- [ ] 超时处理正常
```

---

## 📦 开发流程

### 5 步工作流

```
1. 需求研究 (RESEARCH.md)
   ↓
2. 产品需求 (PRD.md)
   ↓
3. 技术设计 (TECH_DESIGN.md)
   ↓
4. AI 指令 (AGENTS.md) ← 本文件
   ↓
5. 开发迭代
```

### 小步快跑

```
✅ 正确：小功能 → 测试 → 提交 → 下一个
❌ 错误：大功能 → 大测试 → 大提交
```

---

## 🚨 禁止事项

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
exec(user_input)  # 禁止！
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

## 📚 相关文档

### 项目文档

| 文档 | 位置 | 用途 |
|------|------|------|
| PRD.md | 项目根目录 | 产品需求文档 |
| TECH_DESIGN.md | 项目根目录 | 技术设计文档 |
| RESEARCH.md | 项目根目录 | 需求调研文档 |
| SECURITY_GUIDELINES.md | workspace | 安全使用指南 |
| MEMORY.md | workspace | 长期记忆 |

### 架构优化文档

| 文档 | 位置 | 用途 |
|------|------|------|
| 团队职责分工表.md | workspace/ | 3 角色 10 职责定义 |
| WORKFLOW.md | workspace/ | 6 阶段标准流程 |
| 三方分工.md | workspace/ | DAVID+ 战舰+trae 分工 |
| skills/README.md | workspace/skills/ | Skills 技能系统文档 |
| flow-master/SKILL.md | workspace/skills/ | 流程主控 Skill |

---

## 🔄 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 1.0.0 | 2026-03-30 | 初始版本 |
| 1.1.0 | 2026-04-05 | V4.11.0 新功能：用户系统、多儿童管理、数据云同步、历史记录查看、数据管理 |
| 1.2.0 | 2026-04-01 | V4.11.1 claw-code 架构优化：覆盖率审计、临床规则注册表、自动化回归测试、Skills 技能系统 |

## 🚀 V4.11.0 新功能

### 用户系统
- **注册/登录**：支持用户注册和登录，使用 JWT 进行身份验证
- **密码安全**：使用 bcrypt 进行密码哈希，确保密码安全
- **用户信息**：存储用户基本信息，支持多用户管理

### 多儿童管理
- **添加儿童**：支持为用户添加多个儿童信息
- **儿童信息**：记录儿童姓名、性别、年龄、出生日期和备注
- **儿童选择**：在行为分析时可以选择特定儿童

### 数据云同步
- **数据备份**：将用户数据备份到云端（AWS S3）
- **数据恢复**：从云端恢复用户数据
- **备份管理**：查看和删除备份文件

### 历史记录查看
- **会话列表**：查看用户的所有会话记录
- **搜索功能**：根据关键词搜索会话
- **筛选功能**：根据儿童和状态筛选会话
- **分页加载**：支持加载更多会话记录

### 数据管理
- **数据导出**：支持导出用户数据为 CSV 或 JSON 格式
- **数据筛选**：根据不同条件筛选数据
- **数据搜索**：快速查找相关数据

### 前端界面优化
- **导航栏**：添加顶部导航栏，方便切换不同功能
- **登录页面**：全新的登录和注册界面
- **儿童管理页面**：专门的儿童信息管理界面
- **历史记录页面**：会话记录查看和管理界面
- **响应式设计**：适配不同屏幕尺寸

### API 端点
- **用户认证**：`/api/v4/auth/register`, `/api/v4/auth/login`
- **儿童管理**：`/api/v4/children`, `/api/v4/children/{user_id}`
- **会话管理**：`/api/v4/sessions/{user_id}`
- **数据搜索**：`/api/v4/data/search/{user_id}`
- **数据筛选**：`/api/v4/data/filter/{user_id}`
- **数据导出**：`/api/v4/data/export`
- **云同步**：`/api/v4/cloud/backup`, `/api/v4/cloud/restore`, `/api/v4/cloud/backups/{user_id}`, `/api/v4/cloud/backup`

---

**所有参与本项目的 AI 和开发者必须遵守本指令！**
