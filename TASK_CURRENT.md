# P0 紧急任务 - 修复前端 CORS 错误

**创建时间：** 2026-04-09 12:38  
**优先级：** 🔴 **P0 紧急**  
**派发对象：** trae（小治 - Dev-2）  
**问题类型：** 前后端集成

---

## 🔴 问题描述

**错误信息：**
```
Cross-Origin Request Blocked: CORS request did not succeed
http://localhost:8003/api/v4/analyze
```

**症状：**
- 前端发送消息时失败
- 后端 API 无法访问
- 可能是后端服务未启动 或 CORS 配置缺失

---

## 🔍 检测步骤（小治）

### 1. 检查后端服务状态
```bash
# 检查端口 8003 是否监听
netstat -tlnp | grep 8003

# 或者检查进程
ps aux | grep main.py
ps aux | grep uvicorn
```

### 2. 启动后端服务（如未运行）
```bash
cd /home/admin/.openclaw/workspace/behavior_recorder_service
python3 main.py
```

### 3. 检查 CORS 配置
```bash
# 查看 main.py 中的 CORS 配置
grep -A 10 "add_middleware.*CORSMiddleware" main.py
```

**预期配置：**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 或特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 4. 测试后端 API
```bash
# 测试 API 是否可访问
curl -X POST http://localhost:8003/api/v4/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "测试"}'
```

---

## ✅ 修复标准

1. **后端服务运行** - 端口 8003 监听
2. **CORS 配置正确** - 允许前端访问
3. **API 可访问** - curl 测试成功
4. **前端测试通过** - 发送消息成功

---

## 📝 输出要求

修复完成后填写：

```markdown
## 修复报告

### 问题根因
[后端未启动 / CORS 配置缺失 / 其他]

### 修复内容
- [ ] 启动后端服务
- [ ] 配置 CORS
- [ ] 其他修改

### 验证结果
- 后端服务：✅ 运行中（端口 8003）
- CORS 配置：✅ 已配置
- API 测试：✅ curl 成功
- 前端测试：✅ 发送消息成功

### 修改的文件
[列出修改的文件和代码]
```

---

## 📞 联系方式

- **架构师：** 战舰 🛳️（全局统筹）
- **产品经理：** DAVID（最终判定）
- **执行者：** trae（小治 - Dev-2）

---

**状态：** 🔴 紧急，立即执行！
