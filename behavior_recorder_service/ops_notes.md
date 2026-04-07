# 运维笔记 (ops_notes.md)

**目的：** 记录生产环境踩坑经验，避免重复犯错

---

## 2026-03-25 阿里云部署问题

### 问题 1：启动脚本路径硬编码

**现象：**
```
./start-all.sh: line 17: cd: /home/admin/.openclaw/workspace/behavior_recorder_service: No such file or directory
```

**原因：**
- 本地路径：`/home/admin/.openclaw/workspace/behavior_recorder_service`
- 阿里云路径：`/opt/behavior-recorder/behavior_recorder_service`
- 脚本写死了本地路径

**解决：**
- 使用 `SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"` 自动检测
- 或本地和阿里云分别维护启动脚本

**教训：**
- ✅ 启动脚本不要硬编码绝对路径
- ✅ 使用相对路径或自动检测

---

### 问题 2：Gunicorn Worker 崩溃

**现象：**
```
[ERROR] Worker (pid:78833) exited with code 3
[ERROR] Shutting down: Master
```

**原因：**
- Gunicorn + uvicorn 组合复杂度高
- Python 3.9 兼容性问题
- 未经充分测试就上线

**解决：**
- 临时回退到 `python3 main.py`
- 后续如需并发，单独测试 Gunicorn 配置

**教训：**
- ✅ 生产环境不要引入未充分测试的依赖
- ✅ 简单 > 复杂（单进程稳定性 > 多进程并发）

---

### 问题 3：前端代理配置

**现象：**
- 前端能访问，但 API 请求超时
- 浏览器显示"响应时间较长"

**原因：**
- vite.config.js 代理配置为 `localhost:8000`
- 浏览器访问时，`localhost` 指向用户电脑，不是阿里云

**解决：**
- 修改 `vite.config.js` 代理目标为公网 IP
- 或支持环境变量 `VITE_API_URL`

**教训：**
- ✅ 前端代理配置要区分开发和生产环境
- ✅ 使用环境变量管理配置差异

---

### 问题 4：端口被占用

**现象：**
```
Port 3000 is in use, trying another one...
➜ Network: http://172.28.145.12:3001/
```

**原因：**
- 旧进程未清理干净
- 安全组只开放 3000，3001 无法访问

**解决：**
```bash
pkill -9 -f vite && pkill -9 -f "node.*3000" && sleep 3
```

**教训：**
- ✅ 启动前先清理旧进程
- ✅ stop-all.sh 要彻底清理所有相关进程

---

### 问题 5：长文本超时

**现象：**
- 短文本（20 字）：3 秒响应 ✅
- 长文本（150+ 字）：60 秒超时 ❌

**原因：**
- DeepSeek API 处理长文本需要更长时间
- 前端 axios 超时设置 60 秒

**解决：**
- 前端超时改为 180 秒
- 优化等待提示文案

**教训：**
- ✅ 超时时间要根据实际场景设置
- ✅ 长文本场景要单独测试

---

### 问题 6：Git 代码同步

**现象：**
- 阿里云直接修改代码，没有通过 Git
- 下次重新部署时修改丢失

**原因：**
- 为了快速修复，直接在阿里云修改文件
- 没有遵循"本地开发 → Git → 阿里云 pull"流程

**解决：**
- 所有修改先在本地完成
- 测试通过后提交 Git
- 阿里云通过 `git pull` 同步

**教训：**
- ✅ 永远不要在生产环境直接修改代码
- ✅ 紧急修复也要走 Git 流程

---

## 标准操作流程（SOP）

### 本地开发
```bash
cd /home/admin/.openclaw/workspace/behavior_recorder_service
./start-all.sh  # 启动服务
# 开发测试...
./stop-all.sh  # 停止服务
```

### 提交代码
```bash
git add .
git commit -m "描述修改内容"
git push origin clean-release
```

### 阿里云部署
```bash
cd /opt/behavior-recorder/behavior_recorder_service
git pull origin clean-release
./stop-all.sh
./start-all.sh
# 验证
curl http://localhost:8000/api/health
curl http://localhost:3000
```

### 健康检查
```bash
# 检查进程
ps aux | grep -E "python3|vite" | grep -v grep

# 检查端口
netstat -tlnp | grep -E "8000|3000"

# 检查 API
curl http://localhost:8000/api/health

# 检查前端
curl http://localhost:3000 | head -5
```

### 回滚操作
```bash
# 查看历史版本
git log --oneline -5

# 回滚到指定版本
git checkout <commit-hash>

# 重启服务
./stop-all.sh && ./start-all.sh
```

---

## 配置差异对照表

| 配置项 | 本地开发 | 阿里云生产 |
|--------|---------|-----------|
| 路径 | `/home/admin/.openclaw/workspace/behavior_recorder_service` | `/opt/behavior-recorder/behavior_recorder_service` |
| API 地址 | `http://localhost:8000` | `http://8.130.148.166:8000` |
| 前端访问 | `http://localhost:3000` | `http://8.130.148.166:3000` |
| 启动方式 | `./start-all.sh` | `./start-all.sh`（路径自动检测） |
| Python | 3.9.18 | 3.9.18 |
| 系统 | Ubuntu | Alibaba Cloud Linux (CentOS) |

---

## 已知限制

| 问题 | 当前状态 | 计划 |
|------|---------|------|
| 多窗口并发 | ❌ 单进程，排队处理 | 后续优化（Gunicorn 多 worker） |
| 长文本超时 | ✅ 180 秒超时 | 已修复 |
| 反馈按钮 | ⏳ 待验证 | 需要用户测试 |
| HTTPS | ❌ 仅 HTTP | 后续配置 SSL 证书（微信小程序要求） |

---

*最后更新：2026-03-25*
