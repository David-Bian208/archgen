# 行为观察助手 V6.4 — 完整项目总结

**文档版本：** 2026-04-24  
**当前版本：** V6.4  
**当前运行端口：** http://localhost:8014  
**适用对象：** 战舰（后续开发参考）

---

## 零、写在前面（战舰必看）

欢迎回来。以下是你离开后项目的所有关键变化：

### 核心变化概览
1. **交互方式变了**：从 FastAPI + SSE 改为 **Chainlit 对话式 UI**（类似腾讯元宝），用户体验大幅提升
2. **引擎核心未变**：`ClinicalReasoningEngine` 仍然是 5 步临床推理，但做了大量 UI/体验优化
3. **ABC 引导已完成**：你之前文档里提到的"待实现"功能，现在已经全部实现
4. **Chainlit 2.x 配置文件坑**：`config.yaml` 不生效，实际读取的是 `.chainlit/config.toml`

---

## 一、当前系统架构

### 1.1 服务架构

```
┌─────────────────────────────────────────────────────────────┐
│                       用户浏览器                              │
│                     http://localhost:8014                    │
└───────────────────────────┬─────────────────────────────────┘
                            │
                    ┌───────▼───────┐
                    │  Chainlit UI  │  端口 8014 (V6.4)
                    │  (对话界面)    │  流式进度 + 折叠推理 + 报告
                    └───────┬───────┘
                            │
                    ┌───────▼───────┐
                    │  推理引擎     │  ClinicalReasoningEngine (V6.2)
                    │  (LLM 驱动)   │  4 次 LLM 调用（5 步推理）
                    └───────┬───────┘
                            │
                    ┌───────▼───────┐
                    │  OpenAI API   │  deepseek-chat (DeepSeek)
                    └───────────────┘

┌─────────────────────────────────────────────────────────────┐
│  FastAPI V6.1 (端口 8001) - 原有 API 服务，保留但非主要入口   │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 核心文件清单

| 文件 | 角色 | 说明 |
|------|------|------|
| `chainlit_v62/app.py` | **主入口** | Chainlit 对话界面，处理用户输入、ABC 引导、流式进度、报告展示 |
| `chainlit_v62/abc_prompts.py` | ABC 话术 | 所有 ABC 引导对话模板（教育话术、引导问题、确认话术） |
| `chainlit_v62/.chainlit/config.toml` | **Chainlit 配置** | ⚠️ 真正生效的配置文件（不是 config.yaml） |
| `chainlit_v62/public/custom.css` | 自定义样式 | 隐藏按钮、主题等 |
| `chainlit_v62/public/custom.js` | 自定义脚本 | JS 方式隐藏"说明"和主题切换按钮 |
| `app/agents/clinical_reasoning_engine.py` | **核心引擎** | V6.2 推理引擎，5 步临床推理 + ABC 提取 + 报告生成 |
| `app/llm/openai_client.py` | LLM 客户端 | 封装 DeepSeek API 调用 |
| `app/config.py` | 配置管理 | 加载 config.yaml 和环境变量 |
| `api/endpoints_v6.py` | 备用 API | FastAPI 端点（SSE 流式），保留但不作为主要交互入口 |
| `main.py` | FastAPI 入口 | 端口 8001，V6.1 版本 |

### 1.3 关键架构变更（V4 → V6.4 的演进）

```
V4: StructuredAssessorV4（多轮表单式对话，StructuredAssessmentState 状态管理）
  ↓
V5: （过渡版本）
  ↓
V6: ClinicalReasoningEngine（LLM 驱动的 5 步推理，单次对话出报告）
  ↓
V6.2: + Chainlit 流式对话界面 + ABC 提取 + 输入验证 + Step2+3 合并优化
  ↓
V6.3: + ABC 引导式多轮对话 + 语义判断路由 + 安全提示 + 个性化适配 + 回忆提示
  ↓
V6.4: + 推理过程可折叠 + 开场白精简 + ABC 话术精简 + 报告正文优化 + UI 清理
```

**重要：后续开发应基于当前架构（Chainlit + ClinicalReasoningEngine），不要回到 StructuredAssessorV4。**

---

## 二、V6.4 完整功能清单

### 2.1 输入处理层（语义判断 + 路由）

**文件：** `chainlit_v62/app.py` + `app/agents/clinical_reasoning_engine.py`

用户输入后，系统按以下流程判断：

```
用户输入
  │
  ├─ 是否在 ABC 引导流程中？
  │   ├─ 是 → handle_abc_guidance()
  │   │   └─ 智能判断：回复 >80 字 → 跳过引导，直接推理
  │   └─ 否 → 继续
  │
  ├─ analyze_input_quality() 语义判断
  │   ├─ valid=False + vague → 启动 ABC 教育 + 引导
  │   ├─ valid=False + greeting/short → 直接拒绝
  │   ├─ quality=complete → 直接推理
  │   ├─ quality=partial → 启动 ABC 引导
  │   └─ quality=vague → ABC 教育 + 引导
  │
  └─ run_full_reasoning() → 5 步推理 + 报告
```

**语义判断规则（`analyze_input_quality()`）：**

| 检查项 | 条件 | 结果 |
|--------|------|------|
| 长度太短 | 输入 < 5 字 | ❌ 拦截 |
| 纯问候语 | 你好/hi/hello/嗨/在吗 等 10+ 个模式 | ❌ 拦截 |
| 无意义回复 | 继续/好的/谢谢/行/可以 等 | ❌ 拦截 |
| 笼统描述 | 命中 16 个 vague_patterns + 输入 < 30 字 | ❌ 拦截，引导补充 |
| 关键词检测 | 包含 BEHAVIOR_KEYWORDS 或 SCENE_KEYWORDS | ✅ 认为有语义内容 |

### 2.2 ABC 引导式对话（V6.3 新增，V6.4 精简）

**文件：** `chainlit_v62/app.py` + `chainlit_v62/abc_prompts.py`

**核心逻辑：**
1. 用户输入信息不完整时，不拒绝，而是引导补充
2. 首轮显示精简版 ABC 教育话术（约 10 行，适配手机端）
3. 按 A→B→C 顺序逐步引导，每步确认后进入下一步
4. **智能跳过**：引导过程中用户回复 >80 字（说明一次性给完整了），自动跳过引导直接推理
5. 弹性上限 5 轮，超上限生成降级报告

**ABC 教育话术（当前版本，精简版）：**
```
理解您的困扰。为了更准确地分析，我们用 ABC 行为分析框架来收集信息——把行为拆成三个环节：

A 前因：行为发生前，孩子在哪里？和谁？在做什么？
B 行为：孩子具体做了什么？（越具体越好）
C 后果：您或周围人怎么反应的？最后怎么样了？

想到什么说什么，不用全部回答。
您可以一次性说完 A-B-C，也可以我们一步步来。

💡 回忆提示：孩子当时的状态如何？是第一次还是经常发生？
```

**状态管理：** `cl.user_session.set("abc_state", {...})`

### 2.3 5 步临床推理引擎（V6.2 核心）

**文件：** `app/agents/clinical_reasoning_engine.py`

| 步骤 | 功能 | LLM 调用 |
|------|------|----------|
| Step 1 | 场景识别 + ABC 提取 | ✅ 调用 1 |
| Step 2+3 | 假设生成 + 证据检验（V6.2 合并优化） | ✅ 调用 2 |
| Step 4 | 机制解释（认知机制 + 比喻 + 发展视角） | ✅ 调用 3 |
| Step 5 | 干预策略（具体做法 + 为什么有效） | ✅ 调用 4 |

**性能：** 总耗时 ~15-20 秒，4 次 LLM 调用（从 V6.1 的 5 次优化而来）

### 2.4 报告生成（V6.4 优化版）

**文件：** `app/agents/clinical_reasoning_engine.py` — `generate_report()`

**报告结构：**
```
# 行为观察分析报告

## 场景理解          ← V6.4 恢复（只显示名称，无类型代码）
这是一个 **XX 场景**。核心挑战：...

## ABC 行为分析      ← V6.2 新增
| 要素 | 描述 |

## 我们的推理
### 行为假设         ← V6.4 改名（原"可能的解释"）
1. XXX（较可能）     ← V6.4 编号简化（原"假设H1"）
2. XXX（较可能）
3. XXX（有可能）

### 深层机制
认知机制 / 比喻 / 发展视角

## 安全提示          ← V6.3.2 新增
（睡眠/饮食/健康确认 + 情感连接）

## 建议策略
策略1: XXX
策略2: XXX
策略3: XXX

> 💡 个性化适配提醒    ← V6.3.2 新增

---
> 📋 本次分析结束...

> ⚠️ 免责声明
> **AI 分析不能替代专业评估。如需正式诊断请咨询专业人士。**  ← V6.4 精简
```

**V6.4 报告正文优化：**
- "可能的解释" → "行为假设"
- "假设H1/H2/H3" → "1./2./3."
- 删除"专业解释："前缀
- 恢复"场景理解"（去掉类型代码如"A类"）
- 免责声明精简

### 2.5 UI 交互优化（V6.4）

| 功能 | 实现方式 | 文件 |
|------|----------|------|
| 推理过程可折叠 | `<details>` HTML 标签，默认折叠，点击展开，灰色小字 | `app.py` + `config.toml` (unsafe_allow_html) |
| 推理进度流式展示 | "🤔 正在分析中..." + Step 1~5 进度提示 | `app.py` |
| 浅色主题默认 | `default_theme = "light"` | `.chainlit/config.toml` |
| 隐藏上传按钮 | `enabled = false` | `.chainlit/config.toml` |
| 隐藏"说明"按钮 | CSS + JS 双方案 | `custom.css` + `custom.js` |
| 隐藏主题切换按钮 | CSS + JS 双方案 | `custom.css` + `custom.js` |
| 开场白精简 | 用户友好型文案 + 备注不支持图片 | `app.py` |
| ABC 话术精简 | ~25 行 → ~10 行 | `abc_prompts.py` |

### 2.6 置信度定性描述（V6.3.1）

**文件：** `app/agents/clinical_reasoning_engine.py` — `confidence_label()`

| 数值 | 定性标签 |
|------|----------|
| ≥ 0.7 | 较可能 |
| ≥ 0.5 | 有可能 |
| < 0.5 | 需更多观察 |

### 2.7 安全提示（V6.3.2）

报告正文中新增安全提示区块：
> 在尝试以下策略前，请确认孩子的基本需求已满足：
> - 睡眠充足（未过度疲劳）
> - 饮食正常（未饥饿或过饱）
> - 身体健康（无生病、疼痛等不适）
>
> 如孩子当前情绪极度不稳定，请先安抚情绪，再实施干预。
> **所有干预都建立在安全的情感连接之上。如任何策略导致孩子更抗拒或您更焦虑，请暂停，优先修复关系。**

---

## 三、Chainlit 配置注意事项

### ⚠️ 关键：配置文件路径

Chainlit 2.11.1 读取的配置文件是：
- ✅ **`.chainlit/config.toml`**（真正生效）
- ❌ `config.yaml`（不生效，历史遗留）

### 当前配置摘要

```toml
[features]
unsafe_allow_html = true          # 启用 HTML 渲染（折叠功能需要）

[features.spontaneous_file_upload]
    enabled = false               # 关闭文件上传

[UI]
default_theme = "light"           # 浅色主题默认
custom_css = "/public/custom.css" # 自定义 CSS
custom_js = "/public/custom.js"   # 自定义 JS
```

### 启动命令

```bash
# Chainlit（主要交互界面）
cd /home/admin/.openclaw/workspace/behavior_recorder_service/chainlit_v62
chainlit run app.py --port 8014 --headless

# FastAPI（备用，非主要入口）
cd /home/admin/.openclaw/workspace/behavior_recorder_service
python3 main.py   # 端口 8001
```

### 环境变量

```bash
# .env 文件（项目根目录）
LLM_API_KEY=sk-xxxxx
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

Chainlit 启动时会自动加载 `.env`（`app.py` 第 15 行 `load_dotenv()`）。

---

## 四、端口情况

| 端口 | 用途 | 状态 | 备注 |
|------|------|------|------|
| **8001** | FastAPI 后端（V6.1.0） | 运行中 | 保留，备用 |
| **8014** | **Chainlit UI（V6.4）** | **运行中** | **当前主要入口** |
| 8011-8013 | 历史 chainlit 实例 | 已 kill | 沙箱环境占着释放不了，等待 TIME_WAIT 超时 |

**端口清理：** 8011-8013 已尝试 `fuser -k` 和 `kill -9` 均无法释放，是沙箱容器环境的已知问题，不影响当前服务。

---

## 五、完整交互流程

```
用户打开 http://localhost:8014
  │
  ├─ 看到精简版开场白（白色背景）
  │   "您好！我是专注于儿童行为支持的观察助手。"
  │   "📷 注：当前版本暂不支持图片上传"
  │
  ├─ 用户输入行为描述
  │   │
  │   ├─ 完整输入（质量=complete）
  │   │   → 直接推理
  │   │   → 进度流式展示（🤔 Step 1~5）
  │   │   → 折叠的推理过程（灰色小字，可展开）
  │   │   → 正文报告（场景理解 → ABC → 行为假设 → 机制 → 安全 → 策略 → 免责声明）
  │   │
  │   ├─ 部分输入（质量=partial）
  │   │   → 启动 ABC 引导（精简话术）
  │   │   → A→B→C 逐步引导
  │   │   → 收集完成后触发推理
  │   │
  │   ├─ 模糊输入（valid=False + vague）
  │   │   → ABC 教育 + 引导
  │   │
  │   └─ 无效输入（问候语/太短）
  │       → 直接拒绝，提示描述具体行为
  │
  └─ 报告末尾显示会话结束语 + 免责声明
      "本次分析结束。如需进一步评估，请描述新的行为观察内容。"
      "AI 分析不能替代专业评估。如需正式诊断请咨询专业人士。"
```

---

## 六、已知问题和限制

1. **浏览器控制台警告**：`Skipped "*/*" MIME type` 和 `/avatars/... 400` 是 Chainlit 框架内部问题，不影响功能
2. **CSS/JS 隐藏按钮方案**：依赖 DOM 结构稳定性，Chainlit 版本升级后可能需要调整选择器
3. **沙箱端口占用**：8011-8013 被沙箱容器占着释放不了（TIME_WAIT），不影响当前服务
4. **推理过程折叠**：`<details>` 标签在浅色主题下背景色 `#fafafa` 可能不够明显，可根据实际效果调整

---

## 七、版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| V6.1.0 | 2026-04-22 | 首次 LLM 驱动版（5 次 LLM 调用） |
| V6.2.0 | 2026-04-23 | Step 2+3 合并（4 次调用）、Chainlit UI、ABC 提取、输入验证、语义判断 |
| V6.3.0 | 2026-04-24 | ABC 引导式多轮对话、安全提示、回忆提示 |
| V6.3.1 | 2026-04-24 | 免责声明、置信度定性标签（较可能/有可能/需更多观察） |
| V6.3.2 | 2026-04-24 | 个性化适配提醒、回忆提示增强 |
| **V6.4** | **2026-04-24** | **推理过程可折叠、开场白精简、ABC 话术精简、报告正文优化、UI 清理、浅色主题** |

---

**报告人：** 小治  
**更新时间：** 2026-04-24  
**当前服务：** http://localhost:8014  
**状态：** 运行中，功能完整
