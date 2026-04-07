# OpenClaw 安全使用指南

> **最后更新：** 2026-03-30  
> **状态：** 初版  
> **参考：** 国家互联网应急中心风险预警

---

## 🚨 核心风险

恶意 Skills 攻击手法：
- 窃取密钥（API keys, credentials）
- 植入木马（下载执行不明文件）
- 劫持系统权限（root, sudo）
- base64 解码执行
- curl/wget 管道到 bash

**典型案例：** ClawHub 用户 `hightower6eu` 发布的 314 个 Skills 全部为恶意程序。

---

## 📋 安装前审查清单

### 1. 来源验证

```
[ ] 检查作者信誉（clawhub inspect <slug>）
[ ] 检查创建/更新时间（过于集中需警惕）
[ ] 检查下载量/星标数（异常低需警惕）
[ ] 检查 homepage 是否有效
[ ] 避免第三方镜像站（如 openclawSkills.best）
```

### 2. 代码审计

```
[ ] 检查 SKILL.md 中的危险模式
[ ] 检查是否有 base64 解码执行
[ ] 检查是否有 curl|bash 模式
[ ] 检查是否访问敏感文件（~/.ssh, ~/.aws, /etc）
[ ] 检查是否需要 root/sudo 权限
```

### 3. 权限评估

| 风险等级 | 标识 | 示例 | 处理方式 |
|----------|------|------|----------|
| 🟢 低风险 | 笔记工具 | bear-notes, apple-notes | 可直接安装 |
| 🟡 中风险 | API 调用 | github, weather | 审查后安装 |
| 🔴 高风险 | 系统配置 | tmux, coding-agent | 人工二次确认 |
| ⛔ 极端风险 | root 权限 | 涉及 sudo, /etc | 禁止安装 |

---

## 🔍 已安装技能审查

### 当前状态（2026-03-30 扫描）

| 技能 | 风险等级 | 状态 | 备注 |
|------|----------|------|------|
| `coding-agent` | 🔴 高风险 | ⚠️ 需审查 | 涉及代码执行 |
| `github` | 🟡 中风险 | ✅ 可用 | 需 token |
| `1password` | 🟡 中风险 | ⚠️ 需审查 | 涉及凭证 |
| `tmux` | 🔴 高风险 | ⚠️ 需审查 | 涉及系统权限 |
| `clawhub` | 🟡 中风险 | ✅ 可用 | 技能下载入口 |
| `skill-creator` | 🟢 低风险 | ✅ 可用 | 本地技能创建 |
| 其他 46 个 | 低 - 中 | ✅ 待逐一审查 | - |

### 危险模式扫描结果

```
扫描时间：2026-03-30 09:11
扫描范围：/home/admin/.npm-global/lib/node_modules/openclaw/skills/

发现的可疑模式：
1. coding-agent: 使用 codex exec（预期行为，但需 PTY 模式）
2. trello: 使用 curl | jq（预期行为，API 调用）
3. canvas: 引用 root 目录（预期行为，配置路径）

未发现：
- base64 解码执行
- curl|bash 管道
- 敏感文件访问（~/.ssh, ~/.aws）
- sudo/root 权限请求
```

---

## 🛡️ 安全工具推荐

### 已安装

| 工具 | 用途 | 状态 |
|------|------|------|
| `session-logs` | 审计日志 | ✅ 已安装 |
| `model-usage` | 模型使用监控 | ✅ 已安装 |

### 建议安装

| 工具 | 用途 | 优先级 |
|------|------|--------|
| `security-auditor` | 代码安全审查 | 🔴 高 |
| `skill-vetter` | 技能安全审查 | 🔴 高 |
| `security-scanner` | 定期安全扫描 | 🟡 中 |

**安装命令：**
```bash
clawhub install security-auditor
clawhub install skill-vetter
```

---

## 📅 定期审查计划

| 周期 | 任务 | 工具 |
|------|------|------|
| 每周 | 审查高风险技能调用日志 | session-logs |
| 每月 | 扫描已安装技能危险模式 | security-scanner |
| 每季度 | 更新技能到最新版本 | clawhub update |
| 每半年 | 清理未使用技能 | clawhub list |

---

## ⚠️ 安全底线

1. **不安装不需要的技能** - 每个技能都要知道用途
2. **不信任未审查的技能** - 尤其是排行榜热门
3. **不授予过度权限** - 警惕 root/sudo 请求
4. **不忽略异常行为** - 日志中出现不明命令立即调查
5. **定期备份配置** - auth-profiles.json, config.json

---

## 🔐 凭证管理

### 存储位置
```
~/.openclaw/agents/main/agent/auth-profiles.json
```

### 保护建议
```bash
# 设置权限
chmod 600 ~/.openclaw/agents/main/agent/auth-profiles.json

# 定期检查
ls -la ~/.openclaw/agents/*/agent/auth-profiles.json
```

---

## 📞 应急响应

发现可疑行为时：

1. **立即停止** - 停止当前会话
2. **检查日志** - `session-logs` 查看技能调用
3. **隔离技能** - 禁用可疑技能
4. **修改凭证** - 更新可能泄露的 API keys
5. **报告问题** - 向 OpenClaw 社区报告

---

## 📚 参考资料

- OpenClaw 官方文档：https://docs.openclaw.ai
- ClawHub: https://clawhub.com
- 国家互联网应急中心预警（2026-03）

---

*本指南应根据最新安全威胁定期更新。*
