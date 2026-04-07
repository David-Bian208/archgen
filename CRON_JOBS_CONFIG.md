# 自动化任务配置

> **创建时间：** 2026-03-30  
> **最后更新：** 2026-03-30 09:17  
> **状态：** ✅ 已配置 4 个任务

---

## ✅ 已配置的 Cron 任务

### 1. 每周安全扫描 🔴

**任务 ID：** `6f235252-dd56-4ba3-90d1-d9b4977785e9`  
**时间：** 每周一 09:00 (Asia/Shanghai)  
**脚本：** `/home/admin/.openclaw/workspace/scripts/security-scan.sh`  
**下次运行：** 2026-04-07 09:00  
**状态：** ✅ 已启用

**触发内容：**
```
🛡️ 执行每周安全扫描 - 运行 security-scan.sh 脚本并生成报告
```

**报告位置：** `/home/admin/.openclaw/workspace/security-scan-YYYYMMDD.md`

---

### 2. 每月凭证备份 🟡

**任务 ID：** `63072cfa-e3d7-45e7-b339-4454fd0026ae`  
**时间：** 每月 1 号 08:00 (Asia/Shanghai)  
**脚本：** `/home/admin/.openclaw/workspace/scripts/backup-credentials.sh`  
**下次运行：** 2026-04-01 08:00  
**状态：** ✅ 已启用

**触发内容：**
```
🔐 执行每月凭证备份 - 运行 backup-credentials.sh 脚本
```

**备份位置：** `/home/admin/.openclaw/workspace/backups/credentials/`

---

### 3. 每日健康检查 🟢

**任务 ID：** `60186cd6-5d46-4c69-9853-acd4cc6b5681`  
**时间：** 每天 09:00, 14:00, 20:00 (Asia/Shanghai)  
**用途：** 检查 behavior_recorder_service 状态  
**下次运行：** 2026-03-30 14:00  
**状态：** ✅ 已启用

**触发内容：**
```
💓 检查 behavior_recorder_service 健康状态 - 确认 API 和前端服务正常运行
```

---

### 4. Behavior Recorder 心跳（已有）

**任务 ID：** `c5b501d1-fbc0-4f36-8c16-a37d011c367f`  
**时间：** 每 5 分钟  
**状态：** ✅ 运行中  
**上次运行：** 正常（6ms）

**触发内容：**
```
behavior-recorder service heartbeat - keep alive
```

---

## 🛠️ 使用 OpenClaw Cron 工具

### 查看任务状态
```
cron list
```

### 查看任务运行历史
```
cron runs <jobId>
```

### 手动触发任务
```
cron run <jobId>
```

### 禁用任务
```
cron update <jobId> {"enabled": false}
```

### 删除任务
```
cron remove <jobId>
```

---

## 📂 日志目录

```
/home/admin/.openclaw/workspace/logs/
├── security-scan.log      # 安全扫描日志
├── backup.log             # 备份日志
├── health-check.log       # 健康检查日志
└── cron.log               # cron 任务日志
```

创建日志目录：
```bash
mkdir -p /home/admin/.openclaw/workspace/logs
```

---

## 🔍 管理命令

### 查看所有任务
```bash
cron list
```

### 查看任务详情
```bash
cron runs 6f235252-dd56-4ba3-90d1-d9b4977785e9
```

### 手动执行安全扫描
```bash
cron run 6f235252-dd56-4ba3-90d1-d9b4977785e9
```

### 手动执行凭证备份
```bash
cron run 63072cfa-e3d7-45e7-b339-4454fd0026ae
```

---

## ⚠️ 注意事项

1. **时区：** 所有任务使用 Asia/Shanghai 时区
2. **日志轮转：** 定期清理旧日志（保留 30 天）
3. **权限：** 确保脚本有执行权限（chmod +x）
4. **通知：** 关键任务失败时发送通知（可配置飞书/钉钉机器人）
5. ** wakeMode：** 所有任务使用 `next-heartbeat` 模式，在下次心跳时唤醒

---

## 📅 任务日历

| 任务 | 周一 | 周二 | 周三 | 周四 | 周五 | 周六 | 周日 | 每月 1 号 |
|------|------|------|------|------|------|------|------|----------|
| 心跳 (5min) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 健康检查 (3x/天) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 安全扫描 | 09:00 | - | - | - | - | - | - | - |
| 凭证备份 | - | - | - | - | - | - | - | 08:00 |

---

*根据实际需求调整任务频率和时间。*
