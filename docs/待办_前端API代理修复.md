# 待办：前端 API 代理配置修复

**优先级：** P0  
**分配给：** 小治  
**时间：** 2026-04-08 11:38

---

## 问题描述

前端页面 (`http://localhost:5173`) 能正常打开，但 **API 调用失败**。

**已确认：**
- ✅ API 后端正常：`curl http://localhost:8001/health` → `{"status":"ok"}`
- ✅ 前端服务正常：`curl http://localhost:5173` → HTML 返回
- ❌ 前端 → API 调用失败

---

## 诊断步骤

```bash
# 1. 检查 vite.config.js 代理配置
cat /home/admin/.openclaw/workspace/behavior_recorder_service/frontend/vite.config.js

# 2. 确认 API 地址配置
grep -r "VITE_API_URL\|localhost:800" /home/admin/.openclaw/workspace/behavior_recorder_service/frontend/

# 3. 测试跨域访问（绕过代理）
curl -X POST http://localhost:8001/api/v4/analyze \
  -H "Content-Type: application/json" \
  -d '{"user_input":"小明今天很开心"}'

# 4. 检查 CORS 配置
curl -v -X OPTIONS http://localhost:8001/api/v4/analyze \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: POST"
```

---

## 可能原因

1. **vite.config.js 代理目标端口错误** - 可能还是 `8000` 而非 `8001`
2. **CORS 未配置** - 后端未允许跨域请求
3. **前端代码硬编码错误地址** - 检查 `.env` 或 API 客户端配置

---

## 修复方案

### 方案 A：修复 Vite 代理配置
```javascript
// vite.config.js
server: {
  port: 5173,
  proxy: {
    '/api': {
      target: 'http://localhost:8001',  // 确保是 8001
      changeOrigin: true,
    },
  },
}
```

### 方案 B：添加 CORS 支持
```python
# main.py 或 app/__init__.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 验证标准

1. 打开浏览器 `http://localhost:5173`
2. 打开开发者工具 → Network 标签
3. 提交测试 → 看到 API 请求返回 200 状态码
4. 页面显示分析报告

---

## 相关文件

- `frontend/vite.config.js`
- `frontend/.env` (如果有)
- `main.py` (CORS 配置)
- `frontend/src/` 下的 API 客户端代码

---

**修复完成后：** 通知战舰进行功能测试
