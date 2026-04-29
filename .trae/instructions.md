# Trae AI 开发指令

> **创建时间：** 2026-03-30  
> **项目：** Behavior Recorder Service  
> **用途：** Trae AI 在这个项目中必须遵守的开发指令

---

## 🎯 你的角色

你是 Behavior Recorder Service 项目的 AI 编程助手。

**项目定位：** 自闭症儿童行为观察与评估工具（临床系统）

**核心原则：** 安全第一 > 功能完成

---

## 📋 开发前必读

### 开始任何任务前

```
1. 阅读 AGENTS.md - 了解开发规范
2. 阅读 PRD.md - 确认功能需求
3. 阅读 TECH_DESIGN.md - 了解技术设计
4. 阅读 test_checklist.md - 了解测试要求
```

**不要跳过这些步骤！**

---

## 🔐 安全红线（必须遵守）

### 1. API Key 安全

```python
# ✅ 正确：使用环境变量
import os
api_key = os.getenv("LLM_API_KEY")

# ❌ 错误：硬编码
api_key = "sk-578100de3afd494ca759cc096a4a1aaa"  # 禁止！
```

### 2. 临床安全

```python
# ✅ 正确：危险行为触发安全模式
if contains_danger_keywords(text):
    return safe_response()  # 降级到安全建议

# ❌ 错误：直接分析危险行为
result = analyze_behavior(text)  # 禁止！
```

### 3. 免责声明

```python
# ✅ 正确：所有报告必须包含
disclaimer = "本报告仅供参考，建议咨询专业治疗师"

# ❌ 错误：省略免责声明
report = generate_report()  # 没有 disclaimer 字段
```

---

## 🚫 临床系统禁止事项

### 禁止输出

```markdown
# ❌ 禁止诊断结论
"您的孩子患有自闭症"
"这是典型的自闭症行为"

# ❌ 禁止治疗方案
"建议每天训练 3 小时"
"应该使用 ABA 疗法"

# ❌ 禁止绝对化表述
"一定会改善"
"保证有效"
"100% 准确"
```

### 正确输出

```markdown
# ✅ 能力发展视角
"玥玥还没学会如何识别他人的社交信号"

# ✅ 建议口吻
"可以考虑尝试以下方法"
"建议咨询专业治疗师"

# ✅ 概率表述
"可能是寻求关注行为"
"倾向于社交认知能力还在发展中"
```

---

## 💻 编码规范

### Python 后端

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
    """
    pass

# ✅ 使用类型提示
def process_data(data: list[str]) -> dict[str, float]:
    pass

# ✅ 异步端点
@app.post("/api/v4/analyze")
async def analyze_endpoint(request: AnalyzeRequest):
    pass

# ✅ 异常处理
try:
    result = await call_ai_api()
except httpx.TimeoutException:
    logger.error("AI API 超时")
    raise HTTPException(status_code=504, detail="分析超时")
```

### Vue 前端

```vue
<script setup>
// ✅ 使用 Composition API
import { ref, computed, onMounted } from 'vue'

// ✅ 响应式变量
const loading = ref(false)
const report = ref(null)

// ✅ 错误处理
const submit = async () => {
  loading.value = true
  try {
    report.value = await analyze()
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    loading.value = false
  }
}
</script>
```

---

## 🧪 测试要求

### 编写代码时必须同时编写测试

```python
# ✅ 正确：代码 + 测试
def analyze_behavior(context: str, behavior: str) -> dict:
    pass

# 测试
def test_analyze_danger_keywords():
    """测试危险关键词触发安全模式"""
    result = analyze_behavior("玩火", "他想拿打火机")
    assert result["mode"] == "safety_first"
```

### P0 测试必须通过

```bash
# 提交前执行
pytest tests/test_p0_regression.py -v

# 验收标准：100% 通过
```

---

## 📝 代码审查清单

### 提交前自查

```
[ ] 是否遵循 AGENTS.md 的规范
[ ] 是否有类型提示
[ ] 是否有 docstring
[ ] 是否有异常处理
[ ] API Key 是否使用环境变量
[ ] 是否包含免责声明（如适用）
[ ] 是否编写测试
[ ] P0 测试是否通过
[ ] 代码是否简洁（避免过度设计）
```

---

## 🎯 任务优先级

### P0 - 紧急且重要

- 安全相关 Bug
- 数据丢失风险
- 核心功能故障

**响应：** 立即处理

---

### P1 - 重要不紧急

- 新功能开发
- 性能优化
- 文档完善

**响应：** 计划内完成

---

### P2 - 日常优化

- 代码重构
- 小 Bug 修复
- 体验优化

**响应：** 有空时处理

---

## 🤖 与 OpenClaw 协作

### 我的工作流程

```
1. 用户告诉我需求
   ↓
2. 我创建文档/配置
   ↓
3. 你用 Trae 写代码
   ↓
4. 我执行测试
   ↓
5. 我生成报告
   ↓
6. 我部署配置
```

### 你可以让我做的

```
"帮我执行 P0 测试"
"生成测试报告"
"配置定时任务"
"扫描安全问题"
"备份凭证文件"
"查看服务状态"
```

### 我不会做的

```
❌ 写复杂代码（你更擅长）
❌ 代码重构（你用 Trae 更好）
❌ 调试代码（Trae 更强）
```

---

## 🛠️ Skills 技能系统

### 什么是 Skills

Skills 是可插拔的技能包，帮助你（trae）更好地完成开发工作。

### 可用 Skills（6 个）

#### 通用技能（3 个）

| Skill | 用途 | 唤醒词 |
|-------|------|--------|
| dev-test | 测试生成、运行、分析 | "为这个函数生成单元测试" |
| dev-context | 项目结构、模块依赖 | "查看项目结构" |
| dev-logs | 日志查看、搜索、分析 | "查看最近日志" |

#### 领域技能（3 个）

| Skill | 用途 | 唤醒词 |
|-------|------|--------|
| clinical-rules | 查询 14 条临床规则 | "查询临床规则" |
| report-style | 检查报告语言风格 | "检查报告风格" |
| safety-check | 安全关键词检测 | "检查这个行为是否安全" |

### 如何使用 Skills

**位置：** `/home/admin/.openclaw/workspace/skills/`

**示例：**

```bash
# 测试技能
cd /home/admin/.openclaw/workspace/skills/generic/dev-test
python3 executor.py "为这个函数生成单元测试：analyze_behavior"

# 临床规则查询
cd /home/admin/.openclaw/workspace/skills/domains/behavior-recorder/clinical-rules
python3 executor.py "查询临床规则"

# 安全检测
cd /home/admin/.openclaw/workspace/skills/domains/behavior-recorder/safety-check
python3 executor.py "检查这个行为是否安全：小明看到打火机想拿起来玩火"
```

### 加载 Skills

```bash
cd /home/admin/.openclaw/workspace/skills
python3 loader.py load -p behavior-recorder
```

### 完整文档

查看：`/home/admin/.openclaw/workspace/skills/README.md`

---

## 📚 文档位置

| 文档 | 路径 | 用途 |
|------|------|------|
| AGENTS.md | / | AI 开发指令 |
| PRD.md | / | 产品需求 |
| TECH_DESIGN.md | / | 技术设计 |
| RESEARCH.md | / | 需求调研 |
| test_checklist.md | tests/ | 测试清单 |
| context.md | .trae/ | Trae 项目上下文 |
| instructions.md | .trae/ | 本文件 |

---

## ⚠️ 常见错误

### 错误 1：硬编码 API Key

```python
# ❌ 错误
api_key = "sk-xxx"

# ✅ 正确
api_key = os.getenv("LLM_API_KEY")
```

### 错误 2：忽略异常处理

```python
# ❌ 错误
result = call_api()

# ✅ 正确
try:
    result = call_api()
except Exception as e:
    logger.error(f"API 调用失败：{e}")
    raise
```

### 错误 3：缺少免责声明

```python
# ❌ 错误
report = {"summary": "..."}

# ✅ 正确
report = {
    "summary": "...",
    "disclaimer": "本报告仅供参考，建议咨询专业治疗师"
}
```

---

## 🔄 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 1.0.0 | 2026-03-30 | 初始版本 |

---

**开始编码前，请再次阅读本指令！**
