# 🧹 代码清理计划

**日期：** 2026-03-23  
**目标：** 清理无用文件，保留核心代码

---

## ✅ 已备份

- **完整备份：** `/home/admin/Desktop/behavior_recorder_V4.10.4_完整备份_20260323_130317.tar.gz` (35MB)
- **Git 仓库：** https://github.com/David-bian/-.git

---

## 🗑️ 待删除文件

### 1. 测试日志和临时文件（无价值）

```
-                              # 空文件
2, 3, 4, 5, 6, 7, 8           # 测试输出文件
案例测试                        # 空文件
案例深度诊断                     # 空文件
第                              # 空文件
轮日志                          # 空文件
```

### 2. 旧版本历史记录（保留最新的即可）

```
V3.6_UPGRADE_SUMMARY.md
V3.7_UPGRADE_SUMMARY.md
V3.8_UPGRADE_SUMMARY.md
V3.9.1_FINAL_RELEASE.md
V3.9.2_FIX_SUMMARY.md
V3.9_FINAL_SUMMARY.md
V4.0_RELEASE_SUMMARY.md
V4.0_TEST_REPORT.md
V4.1_EMERGENCY_FIX.md
V4.1_FINAL_TEST_REPORT.md
V4.1_MEMORY_DIAGNOSIS_REPORT.md
V4.1_TEST_REPORT.md
V4.2_FIX_REPORT.md
V4.5.10_FIX_SUMMARY.md
V4.5.11_COMPREHENSIVE_EVALUATION.md
V4.5.11_HYPOTHESIS_DRIVEN_FIX.md
V4.5.19_FINAL_TEST_REPORT.md
V4.5.19_FIX_SUMMARY.md
V4.5.20_COMPLETE_SUMMARY.md
V4.5.20_FINAL_VERIFICATION.md
V4.5.20_P0_COMPLETE.md
V4.5.20_P0_FIX_PLAN.md
V4.5.20_P2_COMPLETE.md
V4.5.20_TEST_REPORT.md
V4_FINAL_FIX_REPORT.md
```

### 3. 测试脚本（保留 tests/ 目录即可）

```
test_*.py (根目录的)
test_*.sh (根目录的)
```

### 4. 旧 API 文件（只保留 v4）

```
api/endpoints.py
api/endpoints_v2.py
api/endpoints_v3.py
```

### 5. 旧 agent 版本（只保留当前使用的）

```
app/agents/guided_recorder_agent.py
app/agents/guided_recorder_agent_v3.py
app/agents/guided_recorder_agent_v3_v4.py
app/agents/guided_recorder_v4.py
app/agents/intervention_planner_v4_fixed.py
app/agents/intervention_planner_v4.py
```

### 6. 日志文件

```
*.log
*.txt (测试日志类)
```

---

## ✅ 保留文件

### 核心代码
- `main.py` - 主入口
- `api/endpoints_v4.py` - 当前 API
- `app/agents/` - 当前使用的 agent
- `app/knowledge/` - 知识库
- `app/utils/` - 工具函数
- `frontend/` - 小程序前端

### 文档
- `README.md` - 项目说明
- `CHANGELOG.md` - 更新日志
- `AGENTS.md` - 开发规范
- `快速启动指南.md`
- `微信小程序发布流程.md`
- `小程序导入操作指南.md`
- `小程序上传指南.md`
- `测试用户任务卡.md`
- `内测方案_简化版.md`
- `内测使用指南.md`
- `测试与发布完整方案.md`
- `技术验证完成报告.md`
- `P0 优化完成报告.md`
- `P0 优化执行摘要.md`

### 配置
- `config.yaml.example`
- `requirements.txt`
- `.gitignore`
- `VERSION.json`

### 测试（tests/ 目录）
- `tests/` - 保留所有测试文件

---

## 📋 执行步骤

1. 删除无用文件
2. 更新 .gitignore
3. 提交清理 commit
4. 推送到 GitHub

---

**执行前确认：** 确保备份已完成 ✅
