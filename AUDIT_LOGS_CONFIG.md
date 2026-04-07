# 审计日志配置说明

> **创建时间：** 2026-03-30  
> **状态：** 配置指南

---

## 📜 Session Logs（会话日志）

### 位置
```
~/.openclaw/agents/<agentId>/sessions/
```

### 文件结构
- `sessions.json` - 会话索引
- `<session-id>.jsonl` - 完整对话记录

### 启用状态
✅ **默认启用** - OpenClaw 自动记录所有会话

### 查看日志
```bash
# 列出所有会话
ls -lh ~/.openclaw/agents/main/sessions/

# 查看最近会话
tail -100 ~/.openclaw/agents/main/sessions/*.jsonl | head -50
```

### 使用 session-logs 技能
```
用户问："我之前说过什么？"
→ 自动调用 session-logs 搜索历史
```

---

## 📊 Model Usage（模型使用）

### 状态
⚠️ **需要 CodexBar** - 仅 macOS 支持（当前系统为 Linux）

### 替代方案
使用 OpenClaw 内置的 session_status 工具查看当前会话使用情况。

---

## 🔐 凭证管理

### 位置
```
~/.openclaw/agents/main/agent/auth-profiles.json（如存在）
~/.openclaw/agents/main/agent/models.json
```

### 当前状态
- `auth-profiles.json` - 未找到（可能使用环境变量）
- `models.json` - ✅ 存在（8888 字节）

### 备份策略
```bash
# 手动备份
cp ~/.openclaw/agents/main/agent/models.json \
   /home/admin/.openclaw/workspace/backups/credentials/

# 定期检查
ls -la ~/.openclaw/agents/*/agent/
```

---

## 🔍 Exec 审批配置

### 位置
```
~/.openclaw/exec-approvals.json
```

### 当前状态
✅ **已配置** - 需要检查内容

### 建议
- 审查已批准的命令
- 定期更新白名单
- 避免批准通配符命令

---

## 📅 定期检查清单

### 每周
- [ ] 检查 session logs 大小（异常增长需调查）
- [ ] 审查 exec-approvals.json

### 每月
- [ ] 备份凭证文件
- [ ] 清理旧会话日志（保留最近 30 天）

### 每季度
- [ ] 审查所有已安装技能
- [ ] 更新安全文档

---

## 🛠️ 实用命令

```bash
# 查看会话数量
ls ~/.openclaw/agents/main/sessions/*.jsonl | wc -l

# 查看总会话大小
du -sh ~/.openclaw/agents/main/sessions/

# 查找包含特定关键词的会话
grep -l "behavior_recorder" ~/.openclaw/agents/main/sessions/*.jsonl

# 查看最近的 exec 调用
grep -i "exec" ~/.openclaw/agents/main/sessions/*.jsonl | tail -20
```

---

*本配置应根据实际使用情况调整。*
