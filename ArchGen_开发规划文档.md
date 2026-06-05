# ArchGen 架构生成器 - 开发规划文档

> **版本：** v0.1  
> **创建日期：** 2026-05-26  
> **项目定位：** 文章转架构图的工业化流水线  
> **核心理念：** 先逻辑，后视觉

---

## 📋 目录

1. [项目概述](#项目概述)
2. [核心架构](#核心架构)
3. [技术选型](#技术选型)
4. [开发计划](#开发计划)
5. [核心模块设计](#核心模块设计)
6. [项目结构](#项目结构)
7. [待讨论决策](#待讨论决策)

---

## 项目概述

### 项目定位

**ArchGen（Architecture Generator）** - 将 Markdown 文章自动转换为结构化架构图的工具。

### 核心价值

| 问题 | 传统文生图 | ArchGen 方案 |
|------|------------|-------------|
| **文字渲染** | AI 乱写字符 | ✅ HTML/CSS 精确控制 |
| **排版一致性** | 每次随机 | ✅ 模板化输出 |
| **调试成本** | 重绘整个图 | ✅ 只改 CSS 或 Prompt |
| **尺寸适配** | 重新生成 | ✅ 改参数秒出 |
| **职责分离** | 混在一起 | ✅ 逻辑/视觉解耦 |

### 设计原则

1. **逻辑归逻辑，视觉归视觉** - 拆解不准调 AI Prompt，图太丑改 CSS
2. **DeepSeek 只做擅长的事** - 字符串替换 + 基础 HTML 语法
3. **彻底规避文生图死穴** - 不再担心 AI 把文字画成鬼画符

---

## 核心架构

### 流水线设计

```
┌──────────────────────────────────────────────────────────────┐
│                      ArchGen 架构生成器                        │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │   Router    │ →  │ Extractor   │ →  │   HTML      │      │
│  │   Agent     │    │   Agent     │    │ Generator   │      │
│  │  文章分类   │    │  结构拆解   │    │  视觉渲染   │      │
│  └─────────────┘    └─────────────┘    └─────────────┘      │
│         ↓                  ↓                  ↓              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │ 5 种文章类型 │    │ 5 个 JSON     │    │ 5 个 HTML     │      │
│  │             │    │ Schema      │    │ 模板        │      │
│  └─────────────┘    └─────────────┘    └─────────────┘      │
│                                               ↓              │
│                                      ┌─────────────┐        │
│                                      │  Playwright │        │
│                                      │  Screenshot │        │
│                                      └─────────────┘        │
│                                               ↓              │
│                                      ┌─────────────┐        │
│                                      │ final_image │        │
│                                      │   .png      │        │
│                                      └─────────────┘        │
└──────────────────────────────────────────────────────────────┘
```

### 四步流程

| 步骤 | 阶段 | 输入 | 处理逻辑 | 输出 |
|------|------|------|----------|------|
| ① | 分类路由 | 原始文章 (Markdown) | Router Agent 分析文章骨相 | 文章类型 |
| ② | 结构拆解 | 原始文章 + 文章类型 | Extractor Agent 调用对应模板 | 结构化 JSON |
| ③ | 视觉渲染 | 结构化数据 + 尺寸参数 | HTML Generator 填充模板 | index.html |
| ④ | 截图出图 | HTML 文件 | Playwright 无头浏览器截图 | final_image.png |

### 文章类型定义

| 类型 | 特征 | 适用场景 | 模板示例 |
|------|------|----------|----------|
| **主张型** | 核心观点 + 分论点支撑 | 观点文、议论文 | 中心辐射图 |
| **因果型** | A→B→C 逻辑链条 | 分析文、推理文 | 流程图 |
| **系统型** | 多模块相互作用 | 架构文档、系统说明 | 架构图 |
| **对比型** | A vs B 多维度比较 | 评测文、选型文 | 对比表 |
| **流程型** | 步骤 1→2→3→4 | 教程、操作指南 | 时间轴 |

---

## 技术选型

### 后端技术栈

| 组件 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **框架** | FastAPI | 0.100+ | 异步高性能，与 AI-Pulse 一致 |
| **Python** | Python | 3.10+ | 不支持 3.9 及以下 |
| **LLM** | DeepSeek V4 | - | 结构化输出能力强 |
| **数据库** | SQLite | 3.37+ | 存储文章记录、模板配置 |
| **截图** | Playwright | 1.44+ | 无头浏览器截图 |
| **模板引擎** | Jinja2 | 3.0+ | HTML 模板渲染 |
| **依赖包** | requests, beautifulsoup4 | - | HTTP 请求、HTML 解析 |

### 前端技术栈

| 组件 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **框架** | Vue 3 | 3.3+ | Composition API + `<script setup>` |
| **构建工具** | Vite | 4.4+ | 快速开发体验 |
| **UI 组件库** | Arco Design Vue | 2.5+ | 与 AI-Pulse 统一体验 |
| **工具库** | dayjs, axios | - | 日期处理、HTTP 请求 |

### 部署要求

- **单进程运行：** 前端打包后挂载到 FastAPI 静态目录
- **默认端口：** 8905（可配置）
- **无额外依赖：** 不需要 Nginx、Redis、Docker

---

## 开发计划

### ✅ P0 阶段：MVP 核心流程（2-3 天）

**目标：** 跑通"上传 Markdown → 下载 PNG"全链路

| 序号 | 任务 | 预计时间 | 验收标准 |
|------|------|----------|----------|
| 1 | 项目初始化 | 2h | FastAPI 项目可启动 |
| 2 | Router Agent 开发 | 4h | 5 种文章类型分类准确率>80% |
| 3 | Extractor Agent 开发（3 个核心模板） | 8h | JSON 输出符合 Schema |
| 4 | HTML 模板开发（3 个） | 6h | 样式美观，文字清晰 |
| 5 | Screenshot 模块 | 2h | 截图清晰，尺寸正确 |
| 6 | API 接口开发 | 4h | `/api/generate` 接口可用 |
| 7 | 前端页面开发 | 8h | 上传→预览→下载流程可用 |
| 8 | 端到端测试 | 4h | 10 篇文章测试通过率 100% |

**P0 交付物：**
- 可用的 CLI 工具
- 简单的 Web 界面
- 3 个核心模板（主张/因果/流程）

---

### ✅ P1 阶段：增强功能（3-4 天）

| 序号 | 任务 | 预计时间 | 验收标准 |
|------|------|----------|----------|
| 1 | 增加 2 个模板类型 | 4h | 共 5 种类型全覆盖 |
| 2 | CSS 主题系统 | 4h | 支持 3 套配色方案（极简/商务/科技） |
| 3 | 尺寸配置 | 2h | 支持公众号/小红书/PPT 尺寸 |
| 4 | 批量处理 | 4h | 一次上传多篇文章 |
| 5 | 历史记录 | 4h | SQLite 存储 + 查询 |
| 6 | 前端优化 | 6h | 体验对齐 AI-Pulse |

**P1 交付物：**
- 功能完整的生产版本
- 5 种文章类型全支持
- 多尺寸输出

---

### 📋 P2 阶段：高阶功能（按需迭代）

- [ ] 自定义模板编辑器
- [ ] 团队协作（共享模板）
- [ ] API 开放（第三方调用）
- [ ] Obsidian/Notion 集成
- [ ] 一键发布到社交媒体

---

## 核心模块设计

### 1. Router Agent（文章分类）

**文件：** `src/router_agent.py`

```python
class ArticleRouter:
    TYPES = {
        "claim": "主张型",      # 核心观点 + 分论点
        "causal": "因果型",     # A→B→C 链条
        "system": "系统型",     # 多模块架构
        "comparison": "对比型", # A vs B
        "process": "流程型"     # 步骤 1→2→3→4
    }
    
    def classify(self, markdown: str) -> dict:
        """
        分析文章骨相，返回类型
        
        Returns:
            {
                "type": "claim",
                "confidence": 0.9,
                "reason": "文章包含明确的核心主张和多个分论点支撑"
            }
        """
        # DeepSeek Prompt: 分析文章结构特征...
        pass
```

**Prompt 设计要点：**
- 给明确的结构特征定义
- 要求输出 JSON 格式
- 设置置信度阈值（<0.6 时要求用户手动选择）

**示例 Prompt：**
```
你是一个文章结构分析专家。请分析以下 Markdown 文章的骨相，判断它属于哪种类型：

文章类型定义：
- 主张型：有明确的核心主张，多个分论点支撑
- 因果型：展示 A→B→C 的因果链条
- 系统型：描述多个模块的相互作用
- 对比型：A vs B 的多维度比较
- 流程型：按步骤 1→2→3→4 展开

请输出 JSON 格式：
{
    "type": "类型",
    "confidence": 0.0-1.0,
    "reason": "判断理由"
}

文章：
{markdown}
```

---

### 2. Extractor Agent（结构提取）

**文件：** `src/extractor_agent.py`

```python
class StructureExtractor:
    SCHEMAS = {
        "claim": {
            "metadata": {
                "author": str,
                "date": str,
                "source": str
            },
            "title": str,
            "central_claim": str,
            "supporting_points": List[{
                "label": str,
                "text": str,
                "weight": float  # 0.0-1.0，重要性权重
            }],
            "evidence": List[str],
            "conclusion": str,
            "layout_hints": {
                "central_position": str,  # "center" | "top"
                "point_layout": str       # "grid" | "list" | "radial"
            }
        },
        "causal": {
            "metadata": {"author": str, "date": str, "source": str},
            "title": str,
            "chain": List[{
                "step": int,
                "cause": str,
                "effect": str
            }],
            "root_cause": str,
            "final_effect": str,
            "layout_hints": {"direction": str}  # "horizontal" | "vertical"
        },
        "system": {
            "metadata": {"author": str, "date": str, "source": str},
            "title": str,
            "modules": List[{
                "name": str,
                "role": str,
                "connections": List[str],
                "color": str  # 可选，模块颜色
            }],
            "overview": str,
            "layout_hints": {"pattern": str}  # "hub-spoke" | "layered" | "network"
        },
        "comparison": {
            "metadata": {"author": str, "date": str, "source": str},
            "title": str,
            "dimensions": List[str],
            "items": List[{
                "name": str,
                "scores": List[float],
                "highlight": bool  # 是否高亮显示
            }],
            "layout_hints": {"chart_type": str}  # "radar" | "bar" | "table"
        },
        "process": {
            "metadata": {"author": str, "date": str, "source": str},
            "title": str,
            "steps": List[{
                "order": int,
                "title": str,
                "description": str,
                "tips": List[str]
            }],
            "layout_hints": {"flow_direction": str}  # "left-to-right" | "top-to-bottom"
        }
    }
    
    def extract(self, markdown: str, article_type: str) -> dict:
        """根据类型调用对应模板，提取结构化数据"""
        schema = self.SCHEMAS[article_type]
        # DeepSeek Prompt: 按 Schema 提取...
        pass
```

---

### 3. HTML Generator（视觉渲染）

**文件：** `src/html_generator.py`

```python
class HTMLGenerator:
    TEMPLATES = {
        "claim": "templates/claim.html",
        "causal": "templates/causal.html",
        "system": "templates/system.html",
        "comparison": "templates/comparison.html",
        "process": "templates/process.html",
    }
    
    STYLES = {
        "minimal": "styles/minimal.css",
        "business": "styles/business.css",
        "tech": "styles/tech.css",
    }
    
    SIZES = {
        "wechat": (1080, 1920),      # 公众号
        "xiaohongshu": (1080, 1440), # 小红书
        "ppt": (1920, 1080),         # PPT
        "default": (1200, 800)       # 默认
    }
    
    def render(self, data: dict, article_type: str, style: str = "minimal", size: str = "default") -> str:
        """渲染 HTML"""
        template = load(self.TEMPLATES[article_type])
        css = load(self.STYLES[style])
        html = template.replace("{{data}}", json.dumps(data))
                    .replace("{{css}}", css)
        return html
```

**HTML 模板示例（主张型）：**

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>{{css}}</style>
</head>
<body>
    <div class="diagram-container">
        <h1 class="title">{{data.title}}</h1>
        
        <div class="central-claim">
            {{data.central_claim}}
        </div>
        
        <div class="supporting-points">
            {% for point in data.supporting_points %}
            <div class="point" style="opacity: {{point.weight}}">
                <strong>{{point.label}}</strong>
                <p>{{point.text}}</p>
            </div>
            {% endfor %}
        </div>
        
        <div class="evidence">
            <h3>支撑证据</h3>
            <ul>
            {% for item in data.evidence %}
                <li>{{item}}</li>
            {% endfor %}
            </ul>
        </div>
        
        <div class="conclusion">{{data.conclusion}}</div>
    </div>
</body>
</html>
```

**CSS 样式示例（极简风格）：**

```css
/* styles/minimal.css */
.diagram-container {
    width: 1200px;
    height: 800px;
    padding: 60px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.title {
    font-size: 36px;
    color: #1a1a1a;
    text-align: center;
    margin-bottom: 40px;
}

.central-claim {
    font-size: 28px;
    color: #2c3e50;
    text-align: center;
    padding: 30px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    margin-bottom: 40px;
}

.supporting-points {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
    margin-bottom: 40px;
}

.point {
    background: white;
    padding: 20px;
    border-radius: 8px;
    border-left: 4px solid #3498db;
}

.point strong {
    display: block;
    font-size: 18px;
    color: #2c3e50;
    margin-bottom: 10px;
}

.point p {
    font-size: 14px;
    color: #7f8c8d;
    line-height: 1.6;
}
```

---

### 4. Screenshot Service（截图服务）

**文件：** `src/screenshot.py`

```python
from playwright.sync_api import sync_playwright
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ScreenshotService:
    SIZES = {
        "wechat": (1080, 1920),
        "xiaohongshu": (1080, 1440),
        "ppt": (1920, 1080),
        "default": (1200, 800)
    }
    
    FONTS = [
        "Arial",
        "Helvetica",
        "Times New Roman",
        "Courier New",
        "Microsoft YaHei",  # 中文字体
        "SimHei",
        "PingFang SC"
    ]
    
    def capture(self, html_path: str, output_path: str, size: str = "default") -> str:
        """
        截图 HTML 文件并保存为 PNG
        
        Args:
            html_path: HTML 文件路径
            output_path: 输出 PNG 路径
            size: 尺寸预设
            
        Returns:
            输出文件路径
            
        Raises:
            ScreenshotError: 截图失败时抛出
        """
        width, height = self.SIZES.get(size, (1200, 800))
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--font-hint-subpixel"
                    ]
                )
                page = browser.new_page()
                
                # 字体预加载，避免截图时文字缺失
                page.add_init_script("""
                    document.fonts.ready.then(() => {
                        console.log('Fonts loaded');
                    });
                """)
                
                page.goto(f"file://{html_path}", wait_until="networkidle")
                
                # 等待字体加载完成
                page.wait_for_timeout(1000)
                
                page.screenshot(
                    path=output_path,
                    clip={"x": 0, "y": 0, "width": width, "height": height},
                    full_page=False,
                    type="png",
                    quality=100
                )
                
                browser.close()
            
            logger.info(f"Screenshot saved: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            raise ScreenshotError(f"Failed to capture screenshot: {e}")
```

---

### 5. API 接口设计

**文件：** `api.py`

```python
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from typing import Optional
import uuid
import asyncio

app = FastAPI(title="ArchGen API", version="1.0.0")

# 异步任务存储
tasks = {}

@app.post("/api/generate")
async def generate_diagram(
    file: UploadFile = File(...),
    article_type: str = Form(None),
    style: str = Form("minimal"),
    size: str = Form("default"),
    async_mode: bool = Form(False)  # 是否异步模式
):
    """
    生成架构图
    
    Args:
        file: Markdown 文件
        article_type: 文章类型（可选，不传则自动分类）
        style: 样式风格
        size: 输出尺寸
        async_mode: 是否异步模式（长文章建议用异步）
        
    Returns:
        PNG 文件（同步模式）或 任务 ID（异步模式）
    """
    task_id = str(uuid.uuid4())
    
    try:
        # 1. 读取文件
        markdown = await file.read()
        
        # 2. 文章分类（如果未指定）
        if not article_type:
            router = ArticleRouter()
            result = await router.classify_async(markdown)
            if result.get("confidence", 0) < 0.6:
                # 置信度低，返回类型列表让用户手动选择
                return JSONResponse({
                    "code": 1,
                    "msg": "分类置信度低，请手动选择类型",
                    "data": {"possible_types": result.get("possible_types", [])}
                })
            article_type = result["type"]
        
        # 3. 异步模式
        if async_mode:
            tasks[task_id] = {"status": "processing", "progress": 0}
            asyncio.create_task(process_diagram(task_id, markdown, article_type, style, size))
            return JSONResponse({
                "code": 0,
                "msg": "任务已提交",
                "data": {"task_id": task_id, "status": "processing"}
            })
        
        # 4. 同步模式
        output_path = await process_diagram(None, markdown, article_type, style, size)
        return FileResponse(output_path, media_type="image/png")
        
    except Exception as e:
        return JSONResponse({
            "code": -1,
            "msg": str(e),
            "data": None
        }, status_code=500)


async def process_diagram(task_id, markdown, article_type, style, size):
    """处理流程图（可异步执行）"""
    try:
        # 更新进度
        if task_id:
            tasks[task_id]["progress"] = 20
        
        # 结构提取（带重试）
        extractor = StructureExtractor()
        data = await extractor.extract_with_retry(markdown, article_type, max_retries=3)
        
        if task_id:
            tasks[task_id]["progress"] = 50
        
        # HTML 渲染
        generator = HTMLGenerator()
        html = generator.render(data, article_type, style, size)
        
        if task_id:
            tasks[task_id]["progress"] = 70
        
        # 截图
        screenshot = ScreenshotService()
        output_path = screenshot.capture(html, f"output/{task_id or 'default'}.png", size)
        
        if task_id:
            tasks[task_id] = {"status": "completed", "progress": 100, "output": output_path}
        
        return output_path
        
    except Exception as e:
        if task_id:
            tasks[task_id] = {"status": "failed", "error": str(e)}
        raise e


@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    """查询异步任务状态"""
    task = tasks.get(task_id)
    if not task:
        return JSONResponse({"code": -1, "msg": "任务不存在"}, status_code=404)
    return JSONResponse({"code": 0, "data": task})


@app.post("/api/generate/quick")
async def quick_generate(
    markdown: str = Form(...),
    article_type: str = Form("claim"),
    style: str = Form("minimal"),
    size: str = Form("default")
):
    """
    快速生成（直接传入 Markdown 文本，不需要上传文件）
    适合 CLI 工具调用
    """
    # 处理逻辑同 generate_diagram
    pass


@app.get("/api/types")
async def get_article_types():
    """获取支持的文章类型"""
    return {
        "code": 0,
        "data": ArticleRouter.TYPES
    }


@app.get("/api/styles")
async def get_styles():
    """获取支持的样式"""
    return {
        "code": 0,
        "data": list(HTMLGenerator.STYLES.keys())
    }


@app.get("/api/sizes")
async def get_sizes():
    """获取支持的尺寸"""
    return {
        "code": 0,
        "data": HTMLGenerator.SIZES
    }
```

---

## 项目结构

```
archgen/
├── api.py                      # FastAPI 接口
├── main.py                     # 主入口
├── requirements.txt            # Python 依赖
├── config/
│   └── config.yaml             # 配置文件（LLM API Key 等）
├── src/
│   ├── __init__.py
│   ├── router_agent.py         # 文章分类
│   ├── extractor_agent.py      # 结构提取
│   ├── html_generator.py       # HTML 渲染
│   ├── screenshot.py           # 截图服务
│   └── storage.py              # 数据库操作
├── templates/
│   ├── claim.html              # 主张型模板
│   ├── causal.html             # 因果型模板
│   ├── system.html             # 系统型模板
│   ├── comparison.html         # 对比型模板
│   └── process.html            # 流程型模板
├── styles/
│   ├── minimal.css             # 极简风格
│   ├── business.css            # 商务风格
│   └── tech.css                # 科技风格
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   ├── components/
│   │   └── views/
│   └── dist/                   # 构建产物
├── data/
│   └── archgen.db              # SQLite 数据库
├── logs/
├── output/                     # 生成的图片
└── docs/
    └── ArchGen_开发规划文档.md
```

---

## 错误处理设计

### 错误码定义

```python
# src/errors.py

class ArchGenError(Exception):
    """基础异常类"""
    code = -1
    msg = "Unknown error"

class RouterError(ArchGenError):
    """文章分类错误"""
    code = 1001
    
class ExtractorError(ArchGenError):
    """结构提取错误"""
    code = 2001
    
class TemplateError(ArchGenError):
    """模板渲染错误"""
    code = 3001
    
class ScreenshotError(ArchGenError):
    """截图错误"""
    code = 4001

# 错误码规范
# 1xxx: Router 相关
# 2xxx: Extractor 相关
# 3xxx: HTML Generator 相关
# 4xxx: Screenshot 相关
# 5xxx: API 相关
```

### 重试机制

```python
# src/utils.py
import asyncio
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def retry(max_retries=3, delay=1, backoff=2, exceptions=(Exception,)):
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 延迟倍数
        exceptions: 需要重试的异常类型
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            _delay = delay
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed: {e}, retrying in {_delay}s...")
                    await asyncio.sleep(_delay)
                    _delay *= backoff
        return wrapper
    return decorator

# 使用示例
class StructureExtractor:
    @retry(max_retries=3, delay=2, exceptions=(ExtractorError,))
    async def extract_with_retry(self, markdown: str, article_type: str) -> dict:
        """带重试的结构提取"""
        return await self.extract(markdown, article_type)
```

### 日志规范

```python
# 日志级别使用规范
# DEBUG: 详细调试信息（API 请求参数、中间结果）
# INFO: 正常流程信息（任务开始/完成、文件保存）
# WARNING: 可恢复的异常（重试、降级处理）
# ERROR: 不可恢复的错误（API 调用失败、文件写入失败）
# CRITICAL: 系统级错误（数据库连接失败、服务崩溃）

# 日志格式
"%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
```

---

## 待讨论决策

### 1. Router 实现方式

| 方案 | 优点 | 缺点 | 建议 |
|------|------|------|------|
| **LLM 分类** | 灵活，能处理复杂文章 | 可能不稳定，成本高 | ✅ P0 采用 |
| **规则匹配** | 稳定，快速 | 不够智能，覆盖有限 | ✅ P1 作为兜底 |

**建议方案：** LLM 分类 + 置信度阈值（<0.6 时要求用户手动选择）+ 规则兜底

**规则兜底实现：**
```python
class ArticleRouter:
    KEYWORD_PATTERNS = {
        "claim": ["我认为", "核心观点", "主张", "应该", "必须"],
        "causal": ["导致", "因此", "所以", "原因是", "结果是"],
        "process": ["第一步", "然后", "接下来", "最后", "步骤"],
        "system": ["模块", "架构", "组件", "系统", "层次"],
        "comparison": ["对比", "vs", "优于", "不如", "差异"]
    }
    
    def classify_with_fallback(self, markdown: str) -> dict:
        """LLM 分类 + 规则兜底"""
        # 1. 尝试 LLM 分类
        llm_result = self.classify_by_llm(markdown)
        if llm_result.get("confidence", 0) >= 0.6:
            return llm_result
        
        # 2. LLM 置信度低，使用规则匹配
        return self.classify_by_keywords(markdown)
```

### 6. 文章类型扩展（P1 考虑）

| 类型 | 特征 | 适用场景 |
|------|------|----------|
| **层次型** | 树状结构，父子关系 | 组织架构图、分类体系 |
| **矩阵型** | 多维度交叉，2x2 矩阵 | RACI 矩阵、优先级矩阵 |

**建议：** P0 不做，P1 根据用户需求再添加

---

### 2. 模板扩展性

| 方案 | 优点 | 缺点 | 建议 |
|------|------|------|------|
| **硬编码** | 开发快，易调试 | 扩展需要改代码 | ✅ P0 采用 |
| **配置化** | 灵活，用户可自定义 | 开发复杂度高 | P1 实现 |

**建议方案：** P0 硬编码 5 个模板，P1 支持配置化

---

### 3. 部署方式

| 方案 | 优点 | 缺点 | 建议 |
|------|------|------|------|
| **本地 CLI** | 开发效率高，隐私好 | 需要安装环境 | ✅ P0 优先 |
| **Web 服务** | 易用，可分享 | 需要服务器 | P0 同步开发 |

**建议方案：** CLI 和 Web 同时开发，CLI 优先

---

### 4. 前端参考 AI-Pulse 的程度

| 方案 | 优点 | 缺点 | 建议 |
|------|------|------|------|
| **完全复用** | 开发快，体验统一 | 可能过度设计 | ✅ 布局复用 |
| **重新设计** | 量身定制 | 开发成本高 | ❌ 不推荐 |

**建议方案：** 布局复用 AI-Pulse，功能简化（只保留上传/预览/下载）

---

## 下一步行动

### 立即可执行

#### 1. 项目初始化
```bash
mkdir -p archgen/{src,templates,styles,frontend,data,logs,output}
cd archgen
# 创建 requirements.txt
# 创建 FastAPI 骨架
```

#### 2. Router Agent Prompt 测试
- 准备 10 篇不同类型的测试文章
- 手动测试分类 Prompt 的准确率
- 迭代优化 Prompt

#### 3. HTML 模板原型
- 手写 3 个静态 HTML 模板
- 确认样式效果
- 转成 Jinja2 模板

### 测试数据准备

**需要准备 10 篇测试文章：**

| 类型 | 数量 | 来源建议 |
|------|------|----------|
| 主张型 | 3 篇 | 观点文、评论文 |
| 因果型 | 2 篇 | 分析文、推理文 |
| 流程型 | 2 篇 | 教程、操作指南 |
| 系统型 | 2 篇 | 架构文档、系统说明 |
| 对比型 | 1 篇 | 评测文、选型文 |

**测试文章要求：**
- 长度：500-2000 字
- 格式：Markdown
- 来源：公众号文章、技术博客、内部文档

### 开发顺序建议

```
Day 1: 项目骨架 + Router Agent + Extractor Agent (3 个模板)
Day 2: HTML 模板 + Screenshot 模块 + API 接口
Day 3: 前端页面 + 端到端测试 + 部署
```

### 开发里程碑

| 里程碑 | 预计时间 | 验收标准 |
|--------|----------|----------|
| M1: 项目骨架完成 | Day 1 上午 | 目录结构创建，requirements.txt 完成 |
| M2: Router Agent 完成 | Day 1 下午 | 分类准确率>80% |
| M3: Extractor Agent 完成 | Day 2 上午 | JSON 输出符合 Schema |
| M4: HTML 模板完成 | Day 2 下午 | 3 个模板样式确认 |
| M5: Screenshot 完成 | Day 2 晚上 | 截图清晰，文字完整 |
| M6: API 接口完成 | Day 3 上午 | /api/generate 可用 |
| M7: 端到端测试通过 | Day 3 下午 | 10 篇测试文章通过率 100% |
| M8: P0 发布 | Day 3 晚上 | CLI + Web 可用 |

---

## 附录：JSON Schema 完整定义

### 主张型 Schema

```json
{
  "type": "object",
  "properties": {
    "title": {"type": "string"},
    "central_claim": {"type": "string"},
    "supporting_points": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "label": {"type": "string"},
          "text": {"type": "string"},
          "weight": {"type": "number", "minimum": 0, "maximum": 1}
        }
      }
    },
    "evidence": {"type": "array", "items": {"type": "string"}},
    "conclusion": {"type": "string"}
  },
  "required": ["title", "central_claim", "supporting_points", "conclusion"]
}
```

### 因果型 Schema

```json
{
  "type": "object",
  "properties": {
    "title": {"type": "string"},
    "chain": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "step": {"type": "integer"},
          "cause": {"type": "string"},
          "effect": {"type": "string"}
        }
      }
    },
    "root_cause": {"type": "string"},
    "final_effect": {"type": "string"}
  },
  "required": ["title", "chain", "root_cause", "final_effect"]
}
```

### 流程型 Schema

```json
{
  "type": "object",
  "properties": {
    "title": {"type": "string"},
    "steps": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "order": {"type": "integer"},
          "title": {"type": "string"},
          "description": {"type": "string"},
          "tips": {"type": "array", "items": {"type": "string"}}
        }
      }
    }
  },
  "required": ["title", "steps"]
}
```

---

**文档版本：** v0.1  
**最后更新：** 2026-05-26  
**联系方式：** DAVID
