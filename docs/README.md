# ArchGen - 架构生成器

> 将 Markdown 文章自动转换为结构化架构图

## 核心特性

- **逻辑归逻辑，视觉归视觉** - 拆解不准调 AI Prompt，图太丑改 CSS
- **DeepSeek 只做擅长的事** - 字符串替换 + 基础 HTML 语法
- **彻底规避文生图死穴** - 不再担心 AI 把文字画成鬼画符

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置

编辑 `config/config.yaml`，设置 DeepSeek API Key：

```yaml
llm:
  api_key: "your-deepseek-api-key-here"
```

### 3. 启动 Web 服务

```bash
python main.py
# 访问 http://localhost:8927
```

### 4. CLI 使用

```bash
# 启动服务
python cli.py serve

# 单次生成
python cli.py generate article.md --type claim --style minimal
```

## 项目结构

```
archgen/
├── api.py                      # FastAPI 接口
├── main.py                     # 主入口
├── cli.py                      # CLI 入口
├── requirements.txt            # Python 依赖
├── config/
│   └── config.yaml             # 配置文件
├── src/
│   ├── router_agent.py         # 文章分类
│   ├── extractor_agent.py      # 结构提取
│   ├── html_generator.py       # HTML 渲染
│   ├── screenshot.py           # 截图服务
│   └── storage.py              # 数据库操作
├── templates/                  # HTML 模板
├── styles/                     # CSS 样式
├── frontend/                   # Vue 前端
├── test_data/                  # 测试数据
├── data/                       # 数据库和临时文件
├── logs/                       # 日志
└── output/                     # 生成的图片
```

## 开发状态

- [x] 项目骨架
- [ ] Router Agent (LLM 分类)
- [ ] Extractor Agent (结构化提取)
- [ ] HTML 模板渲染
- [ ] Playwright 截图
- [ ] 前端页面

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | FastAPI + Python 3.10+ |
| LLM | DeepSeek V4 |
| 截图 | Playwright |
| 模板 | Jinja2 |
| 前端 | Vue 3 + Arco Design |
| 数据库 | SQLite |
