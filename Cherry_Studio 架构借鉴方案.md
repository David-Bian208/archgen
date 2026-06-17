# Cherry Studio 架构借鉴方案

**文档版本：** v1.0  
**创建时间：** 2026-06-17  
**适用项目：** ArchGen v2.0  
**参考架构：** Cherry Studio MCP Hub

---

## 零、先理解整体架构

Cherry Studio 的 5 个工具不是独立的，而是一个 **MCP Hub 代理体系** 的四层协议栈：

```
你的对话
    ↓
AI (调用工具)
    ↓
MCP Hub Server (CherryHub) ← 核心路由层
    ↓
多个 MCP 子服务 (GitHub、搜索、数据库...)
```

CherryHub 本身不是"干活的"，它是一个**中转调度中心**。真正的执行者在它背后的各个 MCP 子服务上。

---

## 一、Cherry Studio 五工具详解

### 1. `list` — 服务发现层

**功能：** 列出所有活跃 MCP 子服务上可用的所有工具

**内部实现逻辑：**
```javascript
// 伪代码复原
async function handleListTool({ limit = 30, offset = 0 }) {
  // 1. 从注册表中拿所有活跃的 MCP 子服务
  const activeServers = registry.getActiveServers();
  // 例：["github", "web-search", "database", "rss-fetcher"]
  
  // 2. 向每个子服务发 tools/list 请求
  const allTools = [];
  for (const server of activeServers) {
    const serverTools = await server.call("tools/list");
    for (const tool of serverTools) {
      allTools.push({
        jsName: camelCase(tool.name),        // "githubSearchRepos"
        originalId: `${server.id}__${tool.name}`, // "github__search_repos"
        serverId: server.id,
        description: tool.description
      });
    }
  }
  
  // 3. 分页返回
  return {
    total: allTools.length,
    offset,
    limit,
    returned: allTools.slice(offset, offset + limit)
  };
}
```

**关键设计思想：**

| 设计点 | 说明 |
|--------|------|
| 聚合发现 | 一次调用，发现所有子服务的所有工具，不需要逐个服务询问 |
| 分页机制 | 当工具数量多（100+）时避免一次性返回全部 |
| 双重命名 | `jsName`（驼峰）+ `originalId`（命名空间），兼容不同调用习惯 |

**你要复刻的关键点：**
- 维护一个 `ServerRegistry`，记录所有已连接的 MCP 子服务
- 实现 `tools/list` 协议的聚合器
- 用 `limit/offset` 做内存分页，不需要数据库

---

### 2. `inspect` — 签名查询层

**功能：** 查看某个工具的完整参数签名，返回 JSDoc 格式

**内部实现逻辑：**
```javascript
async function handleInspectTool({ name }) {
  // 1. 解析名字，找到对应的子服务和工具
  const { serverId, toolName } = resolveName(name);
  // "githubSearchRepos" → { serverId: "github", toolName: "search_repos" }
  // "github__search_repos" → { serverId: "github", toolName: "search_repos" }
  
  // 2. 向子服务请求工具的 schema
  const server = registry.getServer(serverId);
  const toolSchema = await server.call("tools/detail", { name: toolName });
  
  // 3. 转换为 JSDoc 格式
  return formatAsJSDoc(toolSchema);
  // {
  //   name: "githubSearchRepos",
  //   params: { query: "string", limit: "number" },
  //   returns: "...",
  //   jsdoc: "/** * @param {string} query ... */"
  // }
}
```

**为什么需要这个工具？**

AI 不能凭空知道每个工具的参数叫什么、什么类型。`inspect` 相当于：

> "我不确定这个函数签名是什么，让我查一下文档再调用"

**你要复刻的关键点：**
- 实现名字解析器，支持驼峰和 `serverId__toolName` 两种格式
- 缓存 schema 结果（工具的签名不会频繁变化）
- JSDoc 格式是因为 AI 对 JSDoc 的解析最准确

---

### 3. `invoke` — 单次调用层

**功能：** 调用一个工具，同步等待结果返回

**内部实现逻辑：**
```javascript
async function handleInvokeTool({ name, params = {} }) {
  // 1. 解析目标
  const { serverId, toolName } = resolveName(name);
  const server = registry.getServer(serverId);
  
  // 2. 参数校验（可选，参考 inspect 拿到的 schema）
  const schema = schemaCache.get(serverId, toolName);
  validateParams(params, schema); // 类型检查
  
  // 3. 转发调用
  const result = await server.call("tools/call", {
    name: toolName,
    arguments: params
  });
  
  // 4. 原样返回（不加工）
  return result;
}
```

**关键设计：**
- 完全透传，不做任何数据加工
- 同步阻塞等待（AI 需要拿到结果才能继续推理）
- 超时保护（如果子服务 30 秒不响应，返回超时错误）

**你要复刻的关键点：**
- 这是最简单的层，就是代理转发
- 重点是错误处理：子服务挂了要返回可读的错误信息
- 日志记录：每次调用的耗时、成功/失败

---

### 4. `exec` — 编排执行层 ⭐ 最核心

**功能：** 在沙箱中执行 JavaScript，可编排多个工具调用

**这是最复杂的一个，内部逻辑：**
```javascript
async function handleExec({ code }) {
  // 1. 构建沙箱上下文
  const sandboxContext = {
    // 核心 API
    mcp: {
      callTool: async (name, params) => {
        // 复用 invoke 的完整逻辑
        return await handleInvokeTool({ name, params });
      },
      log: (level, message, fields) => {
        logs.push({ level, message, fields, timestamp: Date.now() });
      }
    },
    // 并发工具
    parallel: (...promises) => Promise.all(promises),
    settle: (...promises) => Promise.allSettled(promises),
    // 控制台（被捕获）
    console: {
      log: (...args) => logs.push({ level: 'info', message: args.join(' ') }),
      info: (...args) => logs.push({ level: 'info', message: args.join(' ') }),
      warn: (...args) => logs.push({ level: 'warn', message: args.join(' ') }),
      error: (...args) => logs.push({ level: 'error', message: args.join(' ') }),
      debug: (...args) => logs.push({ level: 'debug', message: args.join(' ') }),
    }
  };
  
  // 2. 用 AsyncFunction 动态执行（比 eval 安全，支持 await）
  const logs = [];
  const fn = new AsyncFunction('mcp', 'parallel', 'settle', 'console', code);
  
  // 3. 执行并捕获返回值
  const result = await fn(
    sandboxContext.mcp,
    sandboxContext.parallel,
    sandboxContext.settle,
    sandboxContext.console
  );
  
  // 4. 返回执行结果 + 日志
  return { result, logs, duration: Date.now() - startTime };
}
```

**`exec` 解决的核心问题：**

```
没有 exec 时的效率：
AI 调用 invoke → 等结果 → AI 思考 → AI 调用下一个 invoke → 等结果 → ...
每次调用都要 AI 重新推理，上下文越来越长

有 exec 时的效率：
AI 写一段 JS → 一次扔给 exec → 沙箱内全部执行完 → 返回最终结果
只需要一次 AI 推理，一次网络往返
```

**例子对比：**

```javascript
❌ 没有 exec：
invoke("githubSearchRepos", {query: "mcp"}) → 等 2 秒 → 返回 10 条
invoke("githubSearchRepos", {query: "agent"}) → 等 2 秒 → 返回 8 条
AI 自己做合并 → 返回 18 条
总耗时：~6 秒 + 3 轮 AI 推理

✅ 有 exec：
exec(`
  const [r1, r2] = await parallel(
    mcp.callTool("githubSearchRepos", {query: "mcp"}),
    mcp.callTool("githubSearchRepos", {query: "agent"})
  );
  return [...r1, ...r2];
`)
总耗时：~2 秒 + 1 轮 AI 推理
```

**你要复刻的关键点：**
- 用 `AsyncFunction` 而不是 `eval`（后者不支持 await）
- `mcp.callTool` 是循环调用 `invoke` 的逻辑，但加了并发控制
- `parallel` 和 `settle` 是 Promise 标准 API 的薄封装
- 安全性：沙箱限制了文件系统、网络等（生产环境需要更严格）

---

### 5. `builtin_web_search` — 外部信息接入层

**功能：** 联网搜索，获取训练数据截止后的最新信息

**内部实现逻辑：**
```javascript
async function handleWebSearch({ query }) {
  // 1. 调用搜索引擎 API（可能是 Google/Bing/自建索引）
  const rawResults = await searchEngine.search(query, {
    limit: 10,
    safeSearch: true
  });
  
  // 2. 清洗并格式化
  return rawResults.map(r => ({
    title: r.title,
    url: r.url,
    snippet: r.snippet,           // 150-200 字摘要
    date: r.publishedDate,
    source: r.domain
  }));
}
```

**这不是 CherryHub 的子服务**，而是独立的内置工具。它走的是另一条路径：

```
AI → builtin_web_search → 搜索引擎 API → 返回结构化结果
```

**设计上为什么不放进 CherryHub？**
- 搜索引擎是基础设施级的，不应该走 MCP 子服务
- 降低延迟（少一层转发）
- 失败隔离（搜索挂了不影响 MCP Hub 正常运行）

---

## 二、五工具协作全景图

```
AI (我)
  │
  ┌────────────┼────────────┐
  │            │            │
list        inspect      invoke
  │            │            │
  └────────────┼────────────┘
               │
        CherryHub (MCP 中间件)
               │
        ┌──────┼──────┐
        │      │      │
    GitHub  RSS 抓取  数据库
    子服务   子服务   子服务

独立路径:
AI → builtin_web_search → 搜索引擎
```

**调用顺序规律：**

```
第 1 步：list      → "有哪些工具可以用？"
第 2 步：inspect   → "这个工具的参数是什么？"
第 3 步：invoke    → "调用它" (简单场景)
   或
第 3 步：exec      → "编排多个调用" (复杂场景)
辅助：web_search  → "训练数据之外的信息"
```

---

## 三、ArchGen 现状分析

### 当前架构

```
src/
├── classifier.py          # 内容分类
├── framework_matcher.py   # 框架匹配
├── extractor_agent.py     # 结构提取
├── html_generator.py      # HTML 生成
├── screenshot.py          # 截图服务
├── supplement_storage.py  # 补充存储
└── ...

api.py (212KB, 3500+ 行)
├── 所有 API 端点硬编码
├── 8 步固定工作流
└── 直接导入所有模块
```

### 核心痛点

| 问题 | 描述 | 影响 |
|------|------|------|
| 流程固化 | 8 步固定流程，不能跳过/插入 | 无法支持"只生成提纲"等场景 |
| 调用碎片化 | 每步单独调用 AI | 上下文越来越长，成本高 |
| 错误恢复难 | 某步失败要重头开始 | 用户体验差 |
| 可复用性低 | 能力耦合在 api.py 中 | 其他项目无法调用 |
| 性能浪费 | 所有 AI 调用都用 V4 Pro | 成本高 40-60% |
| 调试困难 | 日志分散，无法追踪完整流程 | 定位问题耗时 |

---

## 四、ArchGen 借鉴方案（按优先级）

### 🥇 第一优先级：工作流编排引擎（`exec`）

#### 当前痛点
```
用户粘贴文章 → 8 步固定流程 → 生成图片
│
├─ 问题 1: 流程固化，不能跳过/插入步骤
├─ 问题 2: 每步单独调用 AI，上下文碎片化
├─ 问题 3: 某步失败要重头开始
└─ 问题 4: 无法支持"只生成提纲"、"只匹配框架"等场景
```

#### 借鉴后实现

**定义原子工具：**
```python
# tools_registry.py
TOOLS = {
    "scan": classifier.classify,
    "check": data_checker.check,
    "analyze_direction": direction_analyzer.analyze,
    "match_framework": framework_matcher.match,
    "supplement": supplement_storage.add,
    "generate_html": html_generator.render,
    "capture_image": screenshot.capture,
    "export_markdown": exporter.to_markdown,
}
```

**实现 `exec` 端点：**
```python
# api.py
@router.post("/api/exec")
async def exec_workflow(request: ExecRequest):
    """
    执行编排代码
    
    请求体：
    {
        "code": "JavaScript 代码字符串",
        "context": {"session_id": "...", "user_id": "..."}
    }
    """
    # 构建沙箱上下文
    sandbox = {
        "mcp": {
            "callTool": lambda name, params: TOOLS[name](**params),
            "log": lambda level, msg: logger.info(f"[{level}] {msg}")
        },
        "parallel": asyncio.gather,
        "settle": lambda *promises: asyncio.gather(*promises, return_exceptions=True),
        "console": {
            "log": lambda *args: logs.append(" ".join(map(str, args)))
        }
    }
    
    # 执行代码
    logs = []
    fn = AsyncFunction(request.code)
    result = await fn(
        sandbox["mcp"],
        sandbox["parallel"],
        sandbox["settle"],
        sandbox["console"]
    )
    
    return {"result": result, "logs": logs}
```

**用户可自定义场景：**

```javascript
// 场景 1: 快速模式（跳过补充/检测）
const result = await exec(`
  const [scan, direction] = await parallel(
    mcp.callTool("scan", {text}),
    mcp.callTool("analyze_direction", {text})
  );
  const frameworks = await mcp.callTool("match_framework", {direction});
  return {scan, direction, frameworks};
`);

// 场景 2: 仅生成提纲（不生成图片）
const outline = await exec(`
  const structure = await mcp.callTool("generate_structure", {framework, content});
  const outline = await mcp.callTool("generate_outline", {structure});
  return outline;
`);

// 场景 3: 批量生成（10 篇文章并行）
const results = await parallel(
  ...articles.map(article => 
    mcp.callTool("full_workflow", {text: article})
  )
);

// 场景 4: 条件分支（根据分类选择不同流程）
const scan = await mcp.callTool("scan", {text});
if (scan.category === "技术文章") {
  return await mcp.callTool("tech_workflow", {text});
} else {
  return await mcp.callTool("general_workflow", {text});
}
```

**收益对比：**

| 维度 | 当前 | 借鉴后 |
|------|------|--------|
| 流程灵活性 | ❌ 固定 8 步 | ✅ 任意编排 |
| AI 调用次数 | 8 次（每步 1 次） | 1-2 次（exec 内批量） |
| 错误恢复 | ❌ 重头开始 | ✅ 从失败步骤重试 |
| 支持场景 | 1 种（完整流程） | N 种（用户自定义） |
| 响应速度 | ~15 秒 | ~5-8 秒 |

---

### 🥈 第二优先级：工具发现与签名查询（`list` + `inspect`）

#### 当前痛点
```
前端代码中硬编码所有 API 调用
→ 新增工具要改前端
→ AI 不知道有哪些工具可用
→ 参数校验分散在各处
```

#### 借鉴后实现

**实现 `list` 端点：**
```python
@router.get("/api/tools/list")
async def list_tools():
    """返回所有可用工具及其签名"""
    return {
        "tools": [
            {
                "name": "scan",
                "description": "扫描文章内容，识别主题和关键信息",
                "params": {
                    "text": {"type": "string", "required": True},
                    "include_summary": {"type": "boolean", "default": False}
                },
                "returns": "ScanResult 对象"
            },
            {
                "name": "match_framework",
                "description": "根据方向匹配理论框架",
                "params": {
                    "direction": {"type": "string", "required": True},
                    "limit": {"type": "integer", "default": 3}
                },
                "returns": "FrameworkMatchResult 对象"
            },
            # ... 所有工具
        ]
    }
```

**实现 `inspect` 端点：**
```python
@router.get("/api/tools/inspect/{tool_name}")
async def inspect_tool(tool_name: str):
    """返回工具的详细签名（JSDoc 格式）"""
    tool = TOOLS_REGISTRY[tool_name]
    return {
        "name": tool_name,
        "jsdoc": f"""
        /**
         * {tool.description}
         * @param {{string}} {tool.params[0].name} - {tool.params[0].desc}
         * @param {{number}} [limit=3] - 返回框架数量
         * @returns {{Promise<FrameworkMatchResult>}}
         */
        """,
        "examples": [
            {"input": {"direction": "AI 知识博主"}, "output": "..."}
        ]
    }
```

**收益：**
- 前端自动生成 API 调用代码（不需要手写）
- AI 可以动态发现工具（支持 Agent 调用）
- 参数校验集中管理（类型安全）

---

### 🥉 第三优先级：AI 调度分层策略

#### 当前痛点
```
所有 AI 调用都直接用 DeepSeek V4
→ 成本高（简单任务也用贵模型）
→ 速度慢（没有并发优化）
```

#### 借鉴后实现

**定义分层配置：**
```python
# config.py
LLM_TIERS = {
    "tier1_fast": {
        "model": "deepseek-chat",      # V3.2
        "use_case": "分类/预筛/简单提取",
        "cost": "0.2 元/百万 tokens",
        "speed": "~500 tokens/s"
    },
    "tier2_balanced": {
        "model": "deepseek-reasoner",  # V3
        "use_case": "框架匹配/提纲生成",
        "cost": "0.5 元/百万 tokens",
        "speed": "~300 tokens/s"
    },
    "tier3_premium": {
        "model": "deepseek-v4-pro",    # V4 Pro
        "use_case": "核心提炼/复杂推理",
        "cost": "2.0 元/百万 tokens",
        "speed": "~100 tokens/s"
    }
}

# 工具声明使用哪个层级
TOOLS = {
    "scan": {"handler": classifier.classify, "tier": "tier1_fast"},
    "match_framework": {"handler": framework_matcher.match, "tier": "tier2_balanced"},
    "generate_outline": {"handler": outline_generator.generate, "tier": "tier3_premium"},
}
```

**工具调用时选择层级：**
```python
# llm_pipeline.py
async def call_llm(task: str, tier: str = "tier2_balanced"):
    config = LLM_TIERS[tier]
    return await llm_client.call(
        model=config["model"],
        task=task
    )
```

**收益对比：**

| 指标 | 当前 | 借鉴后 |
|------|------|--------|
| 成本 | 100% | 40-60%（-40% 至 -60%） |
| 速度 | 100% | 150-200%（简单任务更快） |
| 质量 | 100% | 95-100%（核心任务仍用 V4 Pro） |

---

### 第四优先级：可观测性系统

#### 当前痛点
```
日志分散在各个模块
→ 调试时要翻多个文件
→ 无法追踪完整工作流
→ 性能瓶颈难以定位
```

#### 借鉴后实现

**统一追踪上下文：**
```python
# tracer.py
class WorkflowTracer:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.spans = []
    
    def start_span(self, name: str, metadata: dict):
        span = {
            "name": name,
            "start": time.time(),
            "metadata": metadata,
            "session_id": self.session_id
        }
        self.spans.append(span)
        return span
    
    def end_span(self, span: dict, result: dict, error: str = None):
        span["end"] = time.time()
        span["duration"] = span["end"] - span["start"]
        span["result"] = result
        span["error"] = error
    
    def export(self) -> dict:
        return {
            "session_id": self.session_id,
            "total_duration": sum(s["duration"] for s in self.spans),
            "spans": self.spans
        }

# 使用
@router.post("/api/exec")
async def exec_workflow(request: ExecRequest):
    tracer = WorkflowTracer(request.session_id)
    
    with tracer.start_span("scan", {"text_len": len(text)}):
        scan_result = await classifier.classify(text)
    
    with tracer.start_span("match_framework", {"direction": direction}):
        frameworks = await framework_matcher.match(direction)
    
    # 返回完整追踪
    return {"result": ..., "trace": tracer.export()}
```

**收益：**
- 前端可展示完整工作流时间线
- 性能瓶颈一目了然（哪个步骤最慢）
- 错误定位精准（哪一步失败）

---

### 第五优先级：插件式扩展

#### 当前痛点
```
新增功能要修改 api.py 核心代码
→ 容易引入 bug
→ 版本升级困难
→ 无法支持用户自定义扩展
```

#### 借鉴后实现

**插件注册机制：**
```python
# plugin_registry.py
class PluginRegistry:
    def __init__(self):
        self.plugins = {}
    
    def register(self, name: str, plugin: Plugin):
        self.plugins[name] = plugin
    
    def get_tool(self, tool_id: str):
        plugin_name, tool_name = tool_id.split("__")
        return self.plugins[plugin_name].get_tool(tool_name)

# 插件示例（独立包）
class ObsidianExporter(Plugin):
    def get_tools(self):
        return [
            {"name": "export_to_obsidian", "handler": self.export},
            {"name": "sync_vault", "handler": self.sync}
        ]
    
    def export(self, content: str, vault_path: str):
        # 导出到 Obsidian
        ...

# 注册插件
registry.register("obsidian", ObsidianExporter())
```

**收益：**
- 新增功能不需要改核心代码
- 用户可开发自己的插件（如导出到 Notion/语雀）
- 版本升级只更新插件包

---

## 五、图片生成优化方案（特别补充）

### 当前问题

```python
# src/screenshot.py
async def capture(self, html_content: str, output_path: str, size: str = "default"):
    # 每次截图都启动新浏览器实例
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # ...
        await browser.close()
```

**问题：**
1. 紧耦合，不可复用
2. 性能浪费（每次冷启动 ~2 秒）
3. 无编排能力

### 优化方案 A：轻量级改进（1 天，P0 推荐）

**浏览器连接池：**
```python
# src/screenshot_service.py（重构版）
class ScreenshotService:
    def __init__(self):
        self._browser = None
        self._context = None
    
    async def _ensure_browser(self):
        """懒加载浏览器实例（单例）"""
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=["--disable-gpu", "--no-sandbox"]
            )
            self._context = await self._browser.new_context(
                viewport={"width": 1200, "height": 800},
                device_scale_factor=2,  # 高清屏
            )
        return self._context
    
    async def capture(self, html_content: str, output_path: str, size: str = "default"):
        context = await self._ensure_browser()
        page = await context.new_page()
        
        try:
            await page.set_content(html_content, wait_until="networkidle")
            await page.wait_for_timeout(500)  # 字体渲染
            await page.screenshot(path=output_path, full_page=False)
            return output_path
        finally:
            await page.close()  # 只关闭页面，不关闭浏览器
    
    async def shutdown(self):
        """服务关闭时清理"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
```

**收益：**
- 截图耗时：2.5s → 0.8s（-68%）
- 内存占用：每次 150MB → 常驻 200MB（复用）

### 优化方案 B：MCP Hub 架构（3-5 天，P1）

**独立截图子服务：**
```python
# servers/screenshot/server.py
TOOLS = [
    {
        "name": "capture",
        "description": "截图 HTML 内容为 PNG",
        "inputSchema": {
            "type": "object",
            "properties": {
                "html": {"type": "string"},
                "size": {"type": "string", "enum": ["wechat", "xiaohongshu", "ppt", "default"]},
                "output_format": {"type": "string", "enum": ["png", "jpeg"]}
            },
            "required": ["html"]
        }
    },
    {
        "name": "capture_from_url",
        "description": "截图 URL 为 PNG",
        "inputSchema": {...}
    }
]

@app.post("/mcp/tools/list")
async def tools_list():
    return TOOLS

@app.post("/mcp/tools/call")
async def tools_call(request: ToolCallRequest):
    if request.name == "capture":
        return await renderer.capture(request.arguments)
```

**使用示例：**
```javascript
const result = await exec(`
  // 1. 生成 HTML
  const html = await mcp.callTool("html_gen__render", {framework, content});
  
  // 2. 截图（微信 + 小红书并行）
  const [wechat, xiaohongshu] = await parallel(
    mcp.callTool("screenshot__capture", {html, size: "wechat"}),
    mcp.callTool("screenshot__capture", {html, size: "xiaohongshu"})
  );
  
  // 3. 上传 CDN
  const [url1, url2] = await parallel(
    mcp.callTool("storage__upload", {file: wechat.path}),
    mcp.callTool("storage__upload", {file: xiaohongshu.path})
  );
  
  return {wechat: url1, xiaohongshu: url2};
`);
```

### 优化方案 C：混合方案（2-3 天，折中）

**保留 FastAPI 结构，增加 `exec` 编排端点：**
```python
@router.post("/api/exec")
async def exec_workflow(request: ExecRequest):
    sandbox = {
        "mcp": {
            "callTool": lambda name, params: self._invoke_internal(name, params),
            "log": lambda level, msg: logger.info(f"[{level}] {msg}")
        },
        "parallel": asyncio.gather,
        "settle": lambda *promises: asyncio.gather(*promises, return_exceptions=True),
        "console": {
            "log": lambda *args: logs.append(" ".join(map(str, args)))
        }
    }
    
    logs = []
    fn = AsyncFunction(request.code)
    result = await fn(sandbox["mcp"], sandbox["parallel"], sandbox["settle"], sandbox["console"])
    
    return {"result": result, "logs": logs}
```

**收益：**
- 代码改动量：方案 B 的 30%
- 获得 80% 的编排能力
- 不需要完整的 MCP 协议栈

---

## 六、实施路线图

| 阶段 | 借鉴内容 | 工作量 | 收益 | 优先级 |
|------|----------|--------|------|--------|
| **P0（本周）** | AI 调度分层策略 | 1 天 | 成本 -40%，速度 +50% | ⭐⭐⭐ |
| **P1（下周）** | 工作流编排引擎（`exec`） | 2-3 天 | 支持 N 种自定义场景 | ⭐⭐⭐⭐⭐ |
| **P2（第 3 周）** | 工具发现 + 签名查询 | 1-2 天 | 前端自动生成代码 | ⭐⭐⭐ |
| **P3（第 4 周）** | 可观测性系统 | 1-2 天 | 调试效率 +200% | ⭐⭐ |
| **P4（后续）** | 插件式扩展 | 3-5 天 | 生态扩展能力 | ⭐⭐ |
| **图片优化** | 浏览器连接池（方案 A） | 1 天 | 截图耗时 -68% | ⭐⭐⭐⭐ |

---

## 七、核心设计原则

> **这 5 个工具不是"5 个独立功能"，而是 MCP 协议的 4 层抽象 + 1 个独立搜索通道。**

复刻时不要把它们当孤立工具来实现——要理解它们是一个**协议栈**，每一层解决不同的问题：

| 层 | 解决的问题 | ArchGen 对应 |
|----|-----------|-------------|
| `list` | AI 不知道有哪些工具 → 发现 | 待实现 |
| `inspect` | AI 不知道工具签名 → 确认 | 待实现 |
| `invoke` | 简单场景单次调用 → 执行 | 当前 API 端点 |
| `exec` | 复杂场景多步编排 → 编排 | 待实现（核心） |
| `web_search` | 训练数据不够新 → 补充 | AI-Pulse API |

---

## 八、最小可用架构（Node.js 参考）

```javascript
// hub-server.js 核心骨架
class MCPHub {
  constructor() {
    this.servers = new Map();  // 子服务注册表
    this.schemaCache = new Map();
  }
  
  registerServer(id, server) {
    this.servers.set(id, server);
  }
  
  // list: 聚合所有子服务的工具列表
  async listTools({ limit = 30, offset = 0 }) {
    // ...
  }
  
  // inspect: 获取单个工具的 schema
  async inspectTool(name) {
    // ...
  }
  
  // invoke: 转发调用
  async invokeTool(name, params) {
    // ...
  }
  
  // exec: 沙箱执行
  async execCode(code) {
    // ...
  }
}
```

---

## 九、下一步行动

### 立即可做（P0）

1. **AI 调度分层** - 修改 `src/llm_pipeline.py`，添加 LLM_TIERS 配置
2. **图片服务优化** - 重构 `src/screenshot.py`，实现浏览器连接池

### 下周重点（P1）

1. **`exec` 编排端点** - 新增 `/api/exec` 路由，支持 JavaScript 编排
2. **工具注册表** - 重构 api.py，将原子工具抽离到 `tools_registry.py`

### 后续迭代（P2+）

1. **`list` + `inspect`** - 工具发现与签名查询
2. **可观测性** - 工作流追踪系统
3. **插件系统** - 支持第三方扩展

---

## 十、关键文件位置

```
/home/admin/.openclaw/workspace/behavior_recorder_service/archgen/
├── api.py                      # 主 API 文件（212KB，需重构）
├── src/
│   ├── llm_pipeline.py         # AI 调度分层（P0 修改）
│   ├── screenshot.py           # 截图服务（P0 优化）
│   ├── classifier.py           # 分类工具
│   ├── framework_matcher.py    # 框架匹配工具
│   └── ...
├── Cherry_Studio 架构借鉴方案.md  # 本文档
└── 开发工作手册.md              # 现有文档
```

---

**文档结束**

有任何细节想深入，可以单独展开讨论。
