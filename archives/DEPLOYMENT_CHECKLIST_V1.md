# 行为观察助手 - 部署检查清单 V1.0

**更新日期：** 2026-04-28
**适用范围：** 阿里云服务器 (8.130.148.166)

---

## 前置条件检查

- [ ] 服务器磁盘空间 > 1GB
- [ ] 服务器内存 > 512MB
- [ ] 网络连接正常（可访问 api.deepseek.com）
- [ ] SSH 连接正常

---

## 部署前检查

- [ ] 本地代码已测试通过
- [ ] `.env` 文件包含正确的 API Key 和 Base URL
- [ ] `config.toml` 格式正确（Chainlit 1.3.2）
- [ ] 无语法错误（`python3 -m py_compile app.py`）

---

## 部署步骤

### 1. 同步代码到服务器

```bash
# 方式 1：rsync（推荐）
rsync -avz --exclude='__pycache__' --exclude='.pyc' \
  /home/admin/.openclaw/workspace/behavior_recorder_service/clean_deploy/ \
  root@8.130.148.166:/opt/behavior-recorder/behavior_recorder_service/

# 方式 2：git pull（如果服务器有 git 仓库）
ssh root@8.130.148.166 "cd /opt/behavior-recorder/behavior_recorder_service && git pull"
```

### 2. 清除缓存

```bash
ssh root@8.130.148.166 "cd /opt/behavior-recorder/behavior_recorder_service && find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null"
```

### 3. 重启服务

```bash
ssh root@8.130.148.166 "fuser -k 3000/tcp 2>/dev/null; sleep 3; cd /opt/behavior-recorder/behavior_recorder_service/chainlit_v62 && nohup chainlit run app.py --port 3000 --headless --host 0.0.0.0 > /tmp/chainlit.log 2>&1 &"
```

### 4. 验证服务启动

```bash
# 等待 10 秒
sleep 10

# 检查进程
ssh root@8.130.148.166 "ps aux | grep chainlit | grep -v grep"

# 检查日志
ssh root@8.130.148.166 "tail -10 /tmp/chainlit.log"
```

---

## 部署后验证

### 1. 健康检查

```bash
# 访问首页
curl -s http://8.130.148.166:3000 | head -5
```

### 2. API 连通性测试

```bash
# 使用测试脚本
python3 /tmp/test_api.py
```

### 3. 功能测试

- [ ] 发送测试输入："老师好，有个问题，玥玥有时候会把方向搞反，比如 6 和 9 会看错..."
- [ ] 检查场景标签：应为 "E 类（视觉辨别）— 视觉辨别与方向认知"
- [ ] 检查 5 步推理：全部执行完成
- [ ] 检查报告格式：Markdown 正确渲染
- [ ] 检查主题：白色背景

### 4. 日志检查

```bash
ssh root@8.130.148.166 "grep '意图检测\|Step 1\|HTTP Request' /tmp/chainlit.log | tail -10"
```

---

## 回滚步骤

如果部署后出现问题：

```bash
# 1. 停止服务
ssh root@8.130.148.166 "fuser -k 3000/tcp 2>/dev/null"

# 2. 恢复备份（如果有）
# ssh root@8.130.148.166 "cp -r /opt/behavior-recorder/backup/* /opt/behavior-recorder/behavior_recorder_service/"

# 3. 重启服务
ssh root@8.130.148.166 "cd /opt/behavior-recorder/behavior_recorder_service/chainlit_v62 && nohup chainlit run app.py --port 3000 --headless --host 0.0.0.0 > /tmp/chainlit.log 2>&1 &"
```

---

## 部署日志

| 日期 | 部署人 | 变更内容 | 状态 |
|------|--------|---------|------|
| 2026-04-28 | 战舰 | API Base URL 修复 | ✅ 成功 |
| 2026-04-28 | 战舰 | 场景标签修复 | ✅ 成功 |
| 2026-04-28 | 战舰 | 主题配置修复 | ✅ 成功 |

---

**下次更新：** 根据实际部署经验更新此清单
