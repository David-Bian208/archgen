# claw-audit Skill

** claw-code 架构优化技能包**

灵感来源：claw-code 项目的架构模式，提供覆盖率审计、规则注册表、工具管理、工作流编排等功能。

---

## 🎯 功能列表

### 1. 临床功能覆盖率审计
- 量化 5 个维度覆盖率（临床假设、干预模板、场景分类、安全检查、测试案例）
- 生成 Markdown 审计报告
- 判断系统是否可部署

**唤醒词：**
- "运行覆盖率审计"
- "检查系统覆盖率"
- "生成审计报告"
- "系统可以部署吗"

### 2. 临床规则注册表
- 14 条临床规则（安全、社交、坚持同一性、感觉、逃避、关注、提示依赖）
- 规则匹配、查询、统计
- 辅助行为分析

**唤醒词：**
- "分析这个行为"
- "匹配临床规则"
- "规则注册表统计"
- "有哪些安全规则"

### 3. 工具注册表
- 11 个 OpenClaw 工具统一管理
- 工具搜索、分类、权限检查
- 执行日志追踪

**唤醒词：**
- "列出所有工具"
- "搜索文件工具"
- "工具注册表统计"
- "browser 工具怎么用"

### 4. 工作流编排器
- COLLABORATE 模式：多代理并行协作
- PERSISTENT 模式：持续执行循环
- REVIEW 模式：输出审查

**唤醒词：**
- "多代理协作分析"
- "持续执行这个任务"
- "审查这个输出"
- "用工作流模式处理"

---

## 📖 使用示例

### 覆盖率审计

**用户：** 运行覆盖率审计

**助手：** 
```
正在运行临床功能覆盖率审计...

📊 审计结果：
| 维度 | 覆盖率 | 状态 |
|------|--------|------|
| 临床假设 | 5/5 (100%) | ✅ |
| 干预模板 | 3/3 (100%) | ✅ |
| 场景分类 | 10/10 (100%) | ✅ |
| 安全检查 | 5/5 (100%) | ✅ |
| 测试案例 | 18/18 (100%) | ✅ |
| **总体** | **100%** | **✅ 优秀** |

✅ 系统可部署（所有 P0 维度达标）

审计报告已保存到：/home/admin/Desktop/临床功能覆盖率审计报告_YYYY-MM-DD.md
```

---

### 行为规则分析

**用户：** 分析这个行为：小明看到打火机想拿起来玩火

**助手：**
```
🔍 正在分析行为...

匹配到 3 条临床规则：

1. **火源危险检测** (置信度：1.0)
   - 类别：安全优先
   - 建议：启用安全优先模式

2. **视觉提示依赖** (置信度：0.8)
   - 类别：提示依赖
   - 建议：建立视觉锚点

3. **视觉刺激寻求** (置信度：0.75)
   - 类别：感觉寻求
   - 建议：提供安全替代

⚠️ 检测到危险行为，建议优先处理安全问题。
```

---

### 工具查询

**用户：** 有哪些文件操作工具？

**助手：**
```
🛠️ 文件操作工具（3 个）：

1. **Read** (`read`)
   - 描述：读取文件内容
   - 权限：public
   - 示例：`read path=file.txt`

2. **Write** (`write`)
   - 描述：写入文件内容
   - 权限：user
   - 示例：`write path=file.txt content='Hello'`

3. **Edit** (`edit`)
   - 描述：编辑文件（精确替换）
   - 权限：user
   - 示例：`edit path=file.txt oldText='old' newText='new'`
```

---

### 工作流编排

**用户：** 用多代理模式分析这个代码库

**助手：**
```
🎭 启动 COLLABORATE 模式...

正在调度 3 个子代理：
- agent-1: 分析架构
- agent-2: 检查代码质量
- agent-3: 生成文档

等待代理完成...

📊 协作结果：
- 代理 1 完成：架构分析...
- 代理 2 完成：质量报告...
- 代理 3 完成：文档草稿...

合并输出已生成，共 2500 字。
```

---

## 🔧 技术细节

### 文件位置

| 模块 | 路径 |
|------|------|
| 覆盖率审计 | `behavior_recorder_service/tests/parity_audit.py` |
| 规则注册表 | `behavior_recorder_service/app/knowledge/clinical_rules_registry.py` |
| 工具注册表 | `workspace/tool_registry.py` |
| 工作流编排器 | `workspace/workflow_orchestrator.py` |

### 测试命令

```bash
# 回归测试
pytest behavior_recorder_service/tests/test_parity_audit.py -v

# 覆盖率审计
python3 behavior_recorder_service/tests/parity_audit.py

# 规则注册表
python3 behavior_recorder_service/app/knowledge/clinical_rules_registry.py

# 工具注册表
python3 workspace/tool_registry.py

# 工作流编排器
python3 workspace/workflow_orchestrator.py
```

---

## 📝 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 1.0.0 | 2026-04-01 | 初始版本，包含 4 个核心模块 |

---

**灵感来源：** https://github.com/instructkr/claw-code
