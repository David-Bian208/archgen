# 行为观察助手 V6.4.1 阿里云部署指南

**版本：** V6.4.1  
**更新日期：** 2026-04-29  
**提交：** 39cb5da

---

## 📦 部署包内容

```
deploy_v641/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── agents/
│   │   ├── __init__.py
│   │   └── clinical_reasoning_engine.py    # 临床推理引擎 V4.6.0
│   ├── knowledge/
│   │   ├── __init__.py
│   │   ├── hypothesis_network.json         # 18个假设（含H_VISUAL_DISCRIMINATION）
│   │   └── intent_keywords.json            # 283个关键词
│   └── llm/
│       ├── __init__.py
│       ├── base.py
│       └── openai_client.py
├── chainlit_v62/
│   ├── app.py                               # Chainlit 应用主文件
│   ├── abc_prompts.py                       # ABC 引导提示词
│   ├── start_chainlit.sh                    # 启动脚本
│   ├── .chainlit/
│   │   └── config.toml                      # 白色主题配置
│   └── public/
│       ├── custom.css                       # 自定义样式
│       └── custom.js                        # 自定义脚本
├── requirements.txt                         # Python 依赖
├── .env.example                             # 环境变量模板
└── .gitignore
```

---

## 🚀 部署步骤

### 1. 上传文件

将 `deploy_v641/` 目录上传到阿里云服务器：

```bash
# 在本地执行
scp -r deploy_v641/* user@your-server:/path/to/behavior-recorder/
```

### 2. 配置环境变量

```bash
cd /path/to/behavior-recorder/
cp .env.example .env
nano .env  # 编辑填入实际的 API Key
```

**.env 内容：**
```env
LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

### 3. 安装依赖

```bash
pip3 install -r requirements.txt
```

### 4. 启动服务

```bash
cd chainlit_v62
bash start_chainlit.sh
```

或使用命令：
```bash
python3 -m chainlit run app.py --port 8005 --host 0.0.0.0
```

### 5. 验证服务

```bash
# 检查服务是否运行
curl http://localhost:8005/health

# 应返回：{"status":"ok"}
```

---

## 🔧 关键配置

### requirements.txt 重要说明

```txt
# Chainlit 1.x（必须，2.x 有 ContextVar bug）
chainlit>=1.1.0,<2.0.0

# Pydantic 1.x（必须，2.x 不兼容 Chainlit 1.x）
pydantic<2.0.0
```

### config.toml 主题配置

```toml
[UI.theme]
default = "light"  # 白色背景
```

---

## ✅ V6.4.1 更新内容

### 新增功能
1. **H_VISUAL_DISCRIMINATION（视觉辨别挑战）**
   - 18个假设节点（原17个）
   - 283个关键词（原263个）
   - 支持方向混淆、镜像错误等认知错误型行为分析

### 关键词示例
- 看错、搞反、搞混
- 左右不分、方向搞反
- 6和9看错、b d分不清
- 镜像错误、说反、听反

---

## 🐛 常见问题

### 1. 服务启动失败
```bash
# 检查端口是否被占用
fuser -k 8005/tcp

# 清理 Python 缓存
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete
```

### 2. 关键词数量不对
- 应显示 **18个假设**、**279个关键词**（去重后）
- 如果数量不对，检查文件是否完整上传

### 3. UI 显示黑色背景
- 检查 `.chainlit/config.toml` 中 `default = "light"`
- 清理浏览器缓存

---

## 📊 验证清单

- [ ] 服务启动成功（`{"status":"ok"}`）
- [ ] 假设数量：18个
- [ ] 关键词数量：279个（去重后）
- [ ] UI 主题：白色背景
- [ ] 测试视觉辨别关键词："搞反"、"看错"
- [ ] 推理过程正常显示
- [ ] 报告生成完整

---

## 📞 技术支持

如遇问题，请检查：
1. 日志输出（启动时应有详细日志）
2. 环境变量是否正确
3. 文件是否完整上传
