# 🛠️ 给 trae 的指令：激活并使用 Skills

**创建时间：** 2026-04-01  
**优先级：** P0  
**用途：** 帮助 trae 快速激活并使用 Skills 技能系统

---

## 🎯 你的任务

作为 trae（开发工程师），你需要学会使用 Skills 技能系统来提高开发效率。

---

## 📋 什么是 Skills

Skills 是可插拔的技能包，提供以下能力：

### 通用技能（3 个）- 所有项目可用

| Skill | 用途 | 你什么时候用 |
|-------|------|--------------|
| **dev-test** | 测试生成、运行、分析 | 需要写单元测试时 |
| **dev-context** | 项目结构、模块依赖 | 需要了解项目结构时 |
| **dev-logs** | 日志查看、搜索、分析 | 需要查看日志诊断问题时 |

### 领域技能（3 个）- 行为观察伙伴专用

| Skill | 用途 | 你什么时候用 |
|-------|------|--------------|
| **clinical-rules** | 查询 14 条临床规则 | 需要了解临床规则时 |
| **report-style** | 检查报告语言风格 | 需要检查报告是否符合规范时 |
| **safety-check** | 安全关键词检测 | 需要判断行为是否危险时 |

---

## 🚀 激活步骤（3 步）

### 步骤 1：打开终端

在 Trae IDE 中打开终端（Terminal）

### 步骤 2：加载 Skills

```bash
cd /home/admin/.openclaw/workspace/skills
python3 loader.py load -p behavior-recorder
```

**预期输出：**
```
🛠️  为项目 'behavior-recorder' 加载技能...

📦 加载通用技能：
  ✅ generic/dev-context
  ✅ generic/dev-logs
  ✅ generic/dev-test

🎯 加载领域技能：
  ✅ domains/behavior-recorder/clinical-rules
  ✅ domains/behavior-recorder/report-style
  ✅ domains/behavior-recorder/safety-check

✅ 已加载 6 个技能
```

### 步骤 3：测试技能

```bash
# 测试 1：临床规则查询
cd domains/behavior-recorder/clinical-rules
python3 executor.py "查询临床规则"

# 测试 2：安全检测
cd ../safety-check
python3 executor.py "检查这个行为是否安全：小明看到打火机想拿起来玩火"

# 测试 3：测试生成
cd ../../generic/dev-test
python3 executor.py "为这个函数生成单元测试：analyze_behavior"
```

---

## 💡 使用场景示例

### 场景 1：接到新任务，需要了解项目结构

**你：** 这个模块在哪里？它依赖哪些模块？

**使用 Skill：** dev-context

```bash
cd /home/admin/.openclaw/workspace/skills/generic/dev-context
python3 executor.py "查看项目结构"
python3 executor.py "查找模块：clinical_rules"
```

---

### 场景 2：写完代码，需要生成单元测试

**你：** 我写了一个新函数，需要生成测试

**使用 Skill：** dev-test

```bash
cd /home/admin/.openclaw/workspace/skills/generic/dev-test
python3 executor.py "为这个函数生成单元测试：analyze_behavior"
```

**输出：**
```python
import pytest

def test_analyze_behavior_normal():
    '''测试正常情况'''
    pass

def test_analyze_behavior_edge_case():
    '''测试边界情况'''
    pass

def test_analyze_behavior_exception():
    '''测试异常情况'''
    with pytest.raises(Exception):
        pass
```

---

### 场景 3：遇到 Bug，需要查看日志

**你：** 这个错误是怎么回事？

**使用 Skill：** dev-logs

```bash
cd /home/admin/.openclaw/workspace/skills/generic/dev-logs
python3 executor.py "查看最近日志"
python3 executor.py "搜索包含'timeout'的日志"
```

---

### 场景 4：不确定行为是否安全

**你：** 这个行为描述是否涉及危险？

**使用 Skill：** safety-check

```bash
cd /home/admin/.openclaw/workspace/skills/domains/behavior-recorder/safety-check
python3 executor.py "检查这个行为是否安全：小明看到打火机想拿起来玩火"
```

**输出：**
```
⚠️ 安全检测

行为描述：小明看到打火机想拿起来玩火
检测结果：⚠️ 危险

触发关键词：
- 火 + 危险上下文

建议：
启用安全优先模式，优先处理安全问题
```

---

### 场景 5：需要查询临床规则

**你：** 社交功能有哪些临床规则？

**使用 Skill：** clinical-rules

```bash
cd /home/admin/.openclaw/workspace/skills/domains/behavior-recorder/clinical-rules
python3 executor.py "查询社交规则"
```

**输出：**
```
📋 临床规则查询

类别：social
规则数量：3 条

规则列表：
1. 社交信号忽略 - 社交认知能力还在发展中 - 0.85
2. 共同注意困难 - 共同注意能力还在发展中 - 0.8
3. 社交发起困难 - 社交发起能力还在发展中 - 0.8
```

---

## 📚 完整文档

**位置：** `/home/admin/.openclaw/workspace/skills/README.md`

**查看命令：**
```bash
cat /home/admin/.openclaw/workspace/skills/README.md
```

---

## ✅ 检查清单

完成任务后，确认以下事项：

- [ ] 已阅读本指令
- [ ] 已加载 Skills（运行 `loader.py load -p behavior-recorder`）
- [ ] 已测试至少 1 个 Skill
- [ ] 知道在什么场景下使用哪个 Skill
- [ ] 知道完整文档的位置

---

## 🎯 下一步

1. **立即执行：** 加载 Skills
2. **今天内：** 测试所有 6 个 Skills
3. **后续开发：** 在适当场景下使用 Skills

---

## ❓ 常见问题

### Q: Skills 是必须的吗？

A: 不是必须的，但强烈推荐使用。Skills 可以帮你：
- 快速生成测试代码
- 快速了解项目结构
- 快速查看日志
- 查询临床知识

### Q: 每个项目都要加载吗？

A: 是的。通用技能所有项目共享，领域技能按项目加载。

### Q: 如何查看可用 Skills？

A: 运行：
```bash
cd /home/admin/.openclaw/workspace/skills
python3 loader.py list
```

### Q: Skills 会影响我的代码吗？

A: 不会。Skills 只是辅助工具，不会修改你的代码。

---

##  与 OpenClaw（战舰）的协作

| 角色 | 职责 |
|------|------|
| **你（trae）** | 编码实现、单元测试 |
| **OpenClaw（战舰）** | 架构设计、代码审查、测试、部署 |

**协作流程：**
```
1. 你使用 Skills 辅助开发
   ↓
2. 你编写代码 + 单元测试
   ↓
3. OpenClaw 代码审查
   ↓
4. OpenClaw 运行测试
   ↓
5. OpenClaw 部署
```

---

**开始使用 Skills 吧！** 🚀
