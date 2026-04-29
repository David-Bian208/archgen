# 技能索引（Skill Index）

**版本：** V6.0.8  
**更新时间：** 2026-04-22 10:50  
**维护者：** 战舰 🛳️

---

## 📚 已注册技能清单

| ID | 名称 | 触发词 | 优先级 | 状态 |
|----|------|--------|--------|------|
| **skill_code_review** | 代码安全与规范审查 | 审查/安全/lint/漏洞/规范/review | 1 | ✅ |
| **skill_code_verification** | 真实代码检查 | 检查代码/验证任务/代码审查/验收检查/提交前检查 | 1 | ✅ |
| **skill_api_contract** | API 契约生成 | 接口/API/契约/OpenAPI/Swagger/路由/endpoint | 1 | ✅ |
| **skill_db_migration** | 数据库迁移脚本生成 | 迁移/数据库/schema/migration/表结构/alter/create table | 1 | ✅ |
| **skill_abc_scene** | ABC 场景提取 | ABC 提取/场景分析/前因后果 | 2 | ✅ |
| **skill_behavior_analysis** | 行为观察分析 | 行为分析/功能评估/ABC 分析 | 2 | ✅ |

---

## 🔍 skill_code_verification 详细信息

### 基本信息
- **ID:** skill_code_verification
- **名称:** 真实代码检查
- **描述:** 根据任务派发要求，真实验证代码是否符合要求（Lint/Type/Security/Arch/Test/Requirement）
- **优先级:** 1（高优先级）

### 触发词
```
- 检查代码
- 验证任务
- 代码审查
- 验收检查
- 提交前检查
```

### 参数
```yaml
task_id: string (必填) - 任务 ID
check_types: array (可选) - 检查类型列表
  - lint: 代码规范检查
  - type: 类型检查
  - security: 安全扫描
  - arch: 架构检查
  - test: 单元测试
  - requirement: 任务要求匹配
changed_files: array (可选) - 变更文件列表
task_requirements: array (可选) - 任务要求列表
```

### 使用示例

**示例 1：命令行调用**
```bash
python3 scripts/code_verification.py \
  --task-id TASK_V6.1_LLM_DRIVEN_REASONING \
  --check-types lint,type,security \
  --changed-files app/agents/clinical_reasoning_engine.py
```

**示例 2：Skill 系统调用**
```
战舰：call skill_code_verification(
  task_id="TASK_V6.1_LLM_DRIVEN_REASONING",
  check_types=["lint", "type", "security", "arch", "test"],
  changed_files=["app/agents/clinical_reasoning_engine.py"]
)
```

**示例 3：自然语言触发**
```
DAVID: "检查一下小治的代码"
战舰：自动调用 skill_code_verification → 返回报告
```

### 输出格式

```json
{
  "task_id": "TASK_XXX",
  "status": "passed/failed/warning",
  "checks": {
    "lint": {"status": "passed", "message": "✅ Lint 检查通过"},
    "type": {"status": "passed", "message": "✅ Type 检查通过"},
    "security": {"status": "passed", "message": "✅ 安全检查通过"},
    "arch": {"status": "passed", "message": "✅ 架构检查通过"},
    "test": {"status": "passed", "message": "✅ 测试通过"}
  },
  "summary": {
    "total": 5,
    "passed": 5,
    "failed": 0,
    "warnings": 0
  }
}
```

### 集成点

| 集成点 | 文件 | 说明 |
|--------|------|------|
| **trea_hook.py V2.0** | `scripts/trea_hook.py` | 提交前自动检查 |
| **路由配置** | `.claw/agents.yaml` | 自动触发路由 |
| **工具配置** | `.claw/tools_config.json` | Skill 函数定义 |
| **Skill 声明** | `.claw/skill_code_verification.yaml` | Skill 元数据 |

---

## 📊 技能调用统计

| 技能 | 调用次数 | 成功率 | 平均耗时 |
|------|---------|--------|---------|
| skill_code_review | - | - | - |
| skill_code_verification | 0（新增） | - | - |
| skill_api_contract | - | - | - |
| skill_db_migration | - | - | - |

---

## 🛠️ 维护说明

### 添加新技能
1. 创建 `skills/[skill_id]/SKILL.md`
2. 更新 `.claw/tools_config.json`
3. 更新 `.claw/agents.yaml` 路由
4. 更新本索引文件

### 修改现有技能
1. 修改技能文件
2. 更新触发词（如需要）
3. 更新本索引文件
4. 测试验证

### 删除技能
1. 确认无依赖
2. 删除技能文件
3. 更新 `.claw/tools_config.json`
4. 更新 `.claw/agents.yaml`
5. 更新本索引文件

---

**最后更新：** 2026-04-22 10:50  
**状态：** ✅ 6 个技能已注册
