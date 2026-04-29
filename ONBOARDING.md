# AI 协同开发 Onboarding 指南

**版本：** V6.0.7  
**时间：** 2026-04-20  
**适用团队：** DAVID + 战舰 + 小治/小测/小强/小文

---

## 🚀 快速开始（5 分钟）

### 1. 环境准备

```bash
# 克隆项目
git clone <你的仓库>
cd behavior_recorder_service

# 安装依赖
pip3 install -r requirements-ci.txt

# 配置环境变量
export DASHSCOPE_API_KEY=sk-xxx
export NOTIFY_WEBHOOK=你的钉钉/飞书 Webhook
export NOTIFY_PLATFORM=dingtalk  # 或 feishu/wechat
```

### 2. 初始化环境

```bash
# 一键初始化
make init

# 或手动执行
python3 .claw/skill_loader.py
python3 .claw/skill_guard.py
```

**预期输出：**
```
🧩 技能自动注册引擎 - 启动
  ✅ skill_api_contract (8 个触发词)
  ✅ skill_code_review (7 个触发词)
  ✅ skill_abc_scene (9 个触发词)
  ✅ skill_db_migration (7 个触发词)
  ✅ skill_behavior_analysis (8 个触发词)

✅ 成功注册 5 个技能
```

### 3. 测试技能系统

```bash
# 测试技能追踪
python3 test_skill_trace.py

# 预期输出：
# 🧪 测试技能追踪器...
# ✅ 追踪记录已写入
```

---

## 📋 日常开发 SOP

### 需求输入 → 编码实现 → 提交合并

| 阶段 | 动作 | 工具/命令 | 验收标准 |
|------|------|----------|---------|
| **需求输入** | 自然语言描述 | OpenClaw 交互 | REPO_MAP 更新 + TDD 测试矩阵 |
| **编码实现** | Trea 生成 Diff + 自测 | trea_hook.py | trea_report.json 全绿 |
| **提交合并** | git commit → git push | CI ai-guard-pipeline | 质量门禁通过 → 自动合并 |
| **每日巡检** | 查看技能健康与 ROI | make patrol | skill_alerts.md 无冻结 |
| **技能扩容** | 新增 AI 能力 | skills/*.yaml → make sync | 路由索引更新 |
| **故障排查** | 技能连续失败 | 查 .claw/logs/ → 解冻/修复 | 熔断器自动恢复 |

---

## 🛠️ 常用命令

### Makefile 命令

```bash
# 初始化环境
make init

# 同步技能声明
make sync

# 清理缓存
make clean

# 查看帮助
make help
```

### 技能管理

```bash
# 查看已注册技能
cat .claw/router_index.json | python3 -m json.tool

# 查看技能调用日志
cat .claw/logs/skill_trace.jsonl | python3 -m json.tool

# 查看熔断清单
cat .claw/generated/skill_bypass.md

# 手动解冻技能
# 编辑 .claw/generated/skill_bypass.md，删除对应行后重新运行 make sync
```

### 质量门禁

```bash
# 运行增量质量门禁
python3 scripts/trea_hook.py --incremental --files "file1.py,file2.py"

# 运行架构一致性检查
python3 .claw/arch_guard.py --format json

# 运行安全扫描
python3 scripts/security_scan.py
```

---

## 🔧 故障排查

### 问题 1：技能未注册

**症状：** 发送技能调用指令，OpenClaw 未匹配到技能

**解决：**
```bash
# 1. 检查 skills/ 目录是否有 YAML 文件
ls -la skills/

# 2. 重新同步技能
make sync

# 3. 验证路由索引
cat .claw/router_index.json | python3 -m json.tool
```

### 问题 2：技能连续失败

**症状：** 收到"技能熔断警告"通知

**解决：**
```bash
# 1. 查看熔断清单
cat .claw/generated/skill_bypass.md

# 2. 查看技能调用日志
cat .claw/logs/skill_trace.jsonl | grep "skill_xxx"

# 3. 修复技能依赖或 Schema 问题

# 4. 手动解冻（编辑熔断清单后重新同步）
make sync
```

### 问题 3：CI 构建失败

**症状：** GitHub Actions 显示 quality-gate 失败

**解决：**
```bash
# 1. 查看 CI 日志
# GitHub → Actions → quality-gate → 查看具体步骤

# 2. 本地复现
python3 scripts/trea_hook.py --incremental --files "变更文件"

# 3. 修复后重新提交
git add .
git commit -m "fix: 修复质量问题"
git push
```

### 问题 4：报警通知未收到

**症状：** 技能熔断但无通知

**解决：**
```bash
# 1. 检查环境变量
echo $NOTIFY_WEBHOOK
echo $NOTIFY_PLATFORM

# 2. 测试通知
python3 -c "from .claw.plugins.notify import send_alert; send_alert('测试', '测试消息')"

# 3. 检查 Webhook 是否有效（钉钉/飞书后台查看）
```

---

## 📊 技能开发规范

### 创建新技能

**步骤：**

1. **创建 YAML 文件**
```yaml
# skills/my_skill.yaml
id: skill_my_skill
name: 我的技能
description: 技能描述
triggers: ["触发词 1", "触发词 2"]
parameters:
  type: object
  properties:
    param1:
      type: string
      description: "参数 1 描述"
  required: [param1]
```

2. **同步技能**
```bash
make sync
```

3. **验证路由**
```bash
cat .claw/router_index.json | python3 -m json.tool
```

### 技能命名规范

- ✅ 使用 `skill_` 前缀
- ✅ 使用小写字母和下划线
- ✅ 名称简洁明了（如 `skill_code_review`）

### 触发词规范

- ✅ 包含中文和英文触发词
- ✅ 5-10 个触发词为宜
- ✅ 避免过于宽泛的词（如"分析"）

---

## 🎯 最佳实践

### 1. 技能调用

**推荐：**
```python
# 明确指定技能 ID 和参数
result = execute_skill('skill_code_review', {'file_path': 'auth.py', 'level': 'strict'})
```

**不推荐：**
```python
# 模糊调用，依赖模型猜测
result = execute_skill('审查代码')  # ❌ 缺少参数
```

### 2. 错误处理

**推荐：**
```python
try:
    result = execute_skill(skill_id, arguments)
    if result.get('status') == 'error':
        logger.error(f"技能执行失败：{result.get('error')}")
except Exception as e:
    logger.error(f"技能调用异常：{e}")
```

### 3. 日志记录

**推荐：**
```python
# 使用 skill_tracer.py 自动记录
# 日志格式：.claw/logs/skill_trace.jsonl
# 包含：ts, id, skill, params, latency_ms, status
```

---

## 📁 目录结构

```
behavior_recorder_service/
├── .claw/                      # AI 协同体核心配置
│   ├── agents.yaml             # 路由配置
│   ├── skill_loader.py         # 技能注册引擎
│   ├── skill_guard.py          # 技能熔断器
│   ├── plugins/
│   │   ├── notify.py           # 消息推送模块
│   │   └── skill_tracer.py     # 技能追踪器
│   ├── prompts/                # Prompt 模板
│   ├── generated/              # 运行时生成（Git Ignore）
│   └── logs/                   # 运行时日志（Git Ignore）
├── skills/                     # 技能声明目录
│   ├── code_review.yaml
│   ├── api_contract.yaml
│   └── ...
├── scripts/                    # 工具脚本
│   ├── auto_test.py
│   ├── security_scan.py
│   └── trea_hook.py
├── Makefile                    # 一键运维命令
└── requirements-ci.txt         # CI 依赖
```

---

## 🔗 相关文档

- [开发工作方式说明](/workspace/开发工作方式说明.md)
- [Qwen3.6 System Prompt](/workspace/QWEN3.6_SYSTEM_PROMPT.md)
- [技能系统实施报告](V6.0.7_技能系统最终完成报告.md)
- [最终交付清单](V6.0.7_最终交付清单.md)

---

**创建者：** 小治 + 战舰（OpenClaw）  
**版本：** V6.0.7  
**最后更新：** 2026-04-20 21:30
