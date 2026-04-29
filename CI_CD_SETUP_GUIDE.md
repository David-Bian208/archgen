# CI/CD 配置指南

## 📋 配置步骤

### 1. 配置 GitHub Secrets（必需）

**步骤：**
1. 访问：https://github.com/你的仓库/settings/secrets/actions
2. 点击 "New repository secret"
3. 填写：
   - **Name**: `DASHSCOPE_API_KEY`
   - **Value**: `sk-xxx`（你的 API 密钥）
4. 保存

**⚠️ 重要：** 绝对不要将 API 密钥明文写在 YAML 文件中！

---

### 2. 启用自动合并（可选但推荐）

**步骤：**
1. 仓库 Settings → Pull Requests
2. 勾选 "Allow auto-merge"
3. 保存

**分支保护规则（推荐）：**
1. Settings → Branches → Add branch protection rule
2. Branch name: `main`
3. 勾选：
   - ✅ "Require status checks to pass before merging"
   - ✅ 选择 "quality-gate" 作为必过检查
4. 保存

---

### 3. 安装本地依赖（可选）

```bash
# 安装 CI 专用依赖
pip install -r requirements-ci.txt

# 验证安装
python trea_hook.py --help
python .claw/arch_guard.py --help
python scripts/security_scan.py --help
```

---

## 🧪 测试验证

### 本地测试

```bash
# 1. 测试门禁脚本
python trea_hook.py --incremental
python .claw/arch_guard.py
python scripts/security_scan.py

# 2. 确认全部通过
# 应显示 "✅ Passed" 或 "✅ 安全检查通过"
```

### 推送测试

```bash
# 1. 提交 CI/CD 配置
git add .github/workflows/ai-guard-pipeline.yml requirements-ci.txt
git commit -m "ci: 添加 AI 质量门禁流水线"
git push origin main

# 2. 观察 GitHub Actions
# 访问：https://github.com/你的仓库/actions
# 查看 "AI-Driven Quality Pipeline" 运行状态
```

---

## 📊 效果验证指标

| 指标 | 达标线 | 查看位置 |
|------|--------|----------|
| **门禁拦截率** | 早期>30% → 后期<10% | Actions → quality-gate 日志 |
| **自动合并占比** | >70% | Pull Requests → Merged 标签 |
| **平均交付周期** | <5 分钟 | Actions 运行时间统计 |
| **架构违规漏报** | 0 次 | arch_report.json 与人工抽查对比 |

---

## ⚠️ 常见问题

### Q1: CI 运行超时

**原因：** 依赖安装慢

**解决方案：**
- 已配置 pip 缓存
- 首次运行较慢，后续会加速
- 可考虑使用 `python:3.10-slim` 基础镜像

---

### Q2: JSON 解析失败

**原因：** 报告文件不存在或格式错误

**解决方案：**
```bash
# 本地验证脚本输出
python trea_hook.py > trea_report.json
cat trea_report.json  # 确认是有效 JSON
```

---

### Q3: 自动合并不工作

**原因：** 权限不足

**解决方案：**
1. 确认已启用 auto-merge（见步骤 2）
2. 确认有仓库写入权限
3. 检查分支保护规则

---

### Q4: CI 失败如何调试

**步骤：**
1. 访问 Actions 面板
2. 点击失败的运行
3. 查看具体步骤日志
4. 本地复现问题
5. 修复后重新 Push，自动重跑

---

## 🎯 下一步

CI/CD 配置完成后，建议：

1. **跑通完整生命周期**
   - 本地修改 → Push → CI 门禁 → 自动合并

2. **监控效果指标**
   - 门禁拦截率
   - 自动合并占比
   - 平均交付周期

3. **持续优化**
   - 根据失败样本调整规则
   - 优化测试覆盖率
   - 减少误报

---

**配置完成后，每次 Push 和 PR 都会自动运行质量门禁！** 🛳️
