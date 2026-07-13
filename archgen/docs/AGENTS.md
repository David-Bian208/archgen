# AGENTS.md — 三列分析工作台 AI 开发指令

> Vibe Coding Step 4：AI 代理指令
>
> 告诉 AI 在这个项目中应该遵循什么规则。

---

## 一、开发规范

### 1.1 语言

| 位置 | 语言 |
|------|------|
| 代码变量/函数/类名 | 英文（camelCase / snake_case 按语言惯例） |
| 代码注释 | 中文 |
| Git commit | 中文 |
| 用户可见文案 | 中文 |

### 1.2 后端规范（Python / FastAPI）

- 函数命名：`snake_case`
- 端点路径：`/api/workflow/slot/xxx`
- 所有端点返回统一格式：`{ "code": 0, "data": {...} }` 或 `{ "code": 400, "msg": "..." }`
- 使用现有的 `_success()` / `_error()` 辅助函数
- session 读写用现有的 `_get_session()` / `_save_sessions_to_disk()`
- LLM 调用用现有的 `_call_llm()` 函数
- 新增函数优先放在 `api.py` 内联（除非逻辑特别复杂才拆到 `src/`）
- 不允许引入新的 Python 依赖（除 PaddleOCR）

### 1.3 前端规范（Vue 3 / Arco Design）

- 组件命名：`PascalCase`（如 `ThreeColumnWorkbench.vue`）
- Composable 命名：`useXxxYyy.js`
- 所有新组件用 `<script setup>` + Composition API
- 禁止引入新的 npm 包（用现有的 Arco Design 组件）
- 样式用 `<style scoped>`，不污染全局
- 响应式：rem 单位 + 媒体查询断点 768px / 1024px
- 所有用户可见文案用中文字符（不用 Unicode 转义）

### 1.4 代码风格

- 不写的：过度抽象、提前优化、为"未来可能"写的接口
- 必须写的：错误处理边界、关键操作日志（仅 console.log 调试，不引入日志库）
- 最小改动原则：能复用 v3.0 代码就不重写；能用现有函数就不新建
- 一次只做一件事：每个 commit 对应文档中一个实施步骤

---

## 二、组件开发规范

### 2.1 新组件三要素

每个新建的 `.vue` 组件必须包含：

```
1. Props 定义（类型 + 默认值 + 注释）
2. Emits 定义（事件名 + 参数类型 + 注释）
3. 暴露的方法（defineExpose 仅必要的）
```

示例：

```vue
<script setup>
/**
 * ThreeColumnWorkbench — 三列分析工作台主组件
 *
 * Props:
 *   sessionId   — 当前会话 ID
 *   topic       — 用户选题文本
 *   materialPool— 素材池数组
 *
 * Emits:
 *   proceed-to-article — 用户确认所有槽位，跳 Step 4
 */
const props = defineProps({
  sessionId: { type: String, required: true },
  topic: { type: String, default: '' },
  materialPool: { type: Array, default: () => [] }
})

const emit = defineEmits(['proceed-to-article'])
</script>
```

### 2.2 组件通信

- 父 → 子：Props
- 子 → 父：Emits
- 跨组件共享状态：Composable（`useStep3_Workbench.js`）
- 禁止：全局 EventBus、Vuex/Pinia action 跨组件调用

### 2.3 组件拆封原则

- 一个组件不超过 300 行（template + script + style 合计）
- 超过则拆子组件
- 可复用的 UI 片段抽成独立组件

---

## 三、测试要求

### 3.1 后端测试

| 层级 | 方式 | 频率 |
|------|------|------|
| 语法检查 | `python3 -c "import ast; ast.parse(open('api.py').read())"` | 每次修改后 |
| 端点可用性 | `curl -s http://localhost:8765/api/workflow/session/xxx` | 每个新端点 |
| LLM 调用 | 手动触发一次完整调用验证 Prompt 输出格式 | 每个新 Prompt |

### 3.2 前端测试

| 层级 | 方式 | 频率 |
|------|------|------|
| 语法/构建 | `npx vite build` | 每个组件写完 |
| 渲染验证 | 浏览器中走通页面，检查控制台无红色报错 | 步骤 6/7/8 后 |
| 交互验证 | 完整走通：流式→素材预检→替换建议→确认槽位→填充→编辑→生成全文 | 步骤 10 |
| 素材预检 | 每个槽位根据素材统计显示 🟢🟡🔴 标识，🟡🔴 自动展示 AI 替换建议 | 步骤 10 |

---

## 四、注意事项

### 4.1 不动/已改/注意清单

| 文件/目录 | 状态 | 说明 |
|-----------|:----:|------|
| `StepSupplement.vue` | ✅ **已改** | 方案B 已增加 KB 文件选择、联网搜索、素材池展示（详情见 `memory/2026-07-01.md`） |
| `StepDirection.vue` | 🔒 不动 | 选题逻辑不变 |
| `StepContent.vue` | 🔒 不动 | 文章+配图逻辑不变，只是 currentStep 值变了 |
| `source_tag_processor.py` | 🔒 不动 | 来源标签已写好，直接用 |
| `slot_fill` 端点 | 🔒 不动 | 已有功能，编辑面板复用 |
| `ai_infer_supplement` API | ✅ **新增** | `/api/workflow/supplement/ai-auto` 端点的方案B增强版 |
| `materialPool` 逻辑 | ✅ **已改** | 确认补充后素材追加到 `session.material_pool`，按类型分列 |

### 4.2 需要小心的东西

| 风险点 | 应对 |
|--------|------|
| `currentStep` 数字变了 | 用步骤名称枚举替代裸数字，全局搜索替换 |
| session JSON 结构扩展 | 向后兼容：缺少新字段时，前端给默认值 |
| 多个流式连接 | 保证同一时间只有一个 SSE 连接 |
| `sandbox` 中 `--reload` 不工作 | 提示用户手动 Ctrl+C 重启后端 |

### 4.3 性能边界

| 约束 | 值 |
|------|-----|
| 单次 LLM 调用超时 | 60s |
| SSE 流式超时 | 60s |
| 并行槽位填充上限 | 6 个（通过 asyncio.Semaphore(6)） |
| 前端首次加载时间 | < 3s（组件懒加载） |
| 素材池最大条数 | 50 条（超过截断） |

---

## 五、交互细节清单

以下细节在开发中必须遵守：

- [ ] 流式输出过程中，[确认槽位] 按钮始终可用（可提前结束流式）
- [ ] 槽位编辑时，输入框失焦自动保存
- [ ] 删除槽位需二次确认（Modal.confirm）
- [ ] 三列填充中，已完成的行显示内容，未完成的行显示 `a-spin`
- [ ] 填充失败的行显示「生成失败，点击重试」
- [ ] 编辑面板 300ms slide 动画
- [ ] 点击编辑面板外区域关闭面板
- [ ] F11: 流式完成后展示槽位关系图谱（CSS 连线，可折叠）
- [ ] F12: 编辑面板追问区 → 用户输入问题 → AI 回复 → 可采纳/忽略
- [ ] F13: 槽位确认阶段追问框 → AI 回复追加到流式区域
- [ ] 追问历史保留在当前页面（不超过5轮）
- [ ] 全部槽位确认后，[生成全文] 按钮才解除 disabled
- [ ] 文件上传后显示文件名 + 上传进度（如有）
- [ ] 图片上传后调用 OCR，显示提取的文字预览

---

## 六、废弃文件清理

实施完成后删除以下文件（先保留做参考）：

```bash
# 逐步删除，不是一次性
rm frontend/src/components/workflow/FrameworkWorkbench.vue
rm frontend/src/components/workflow/SlotCard.vue
rm frontend/src/components/workflow/StepFramework.vue
rm frontend/src/views/FrameworkSelectView.vue
# store 如存在也清理
```

---

## 七、Git 提交规范

每个实施步骤完成后提交一次：

```
[步骤1] feat: 新增 generate_slots SSE 流式端点
[步骤2] feat: 新增 match_materials 素材匹配端点
[步骤3] feat: 新增 batch_fill_v4 + generate_outline 端点
[步骤4] feat: 前端 api.js 新增 SSE 流式 + 3 个 API
[步骤5] feat: useStep3_Workbench 扩展状态管理
[步骤6] feat: 新增 StreamSlotsPanel 流式推理组件
[步骤7] feat: 新增 ThreeColumnWorkbench 三列表格
[步骤8] feat: 新增 EditPanel 编辑面板
[步骤9] refactor: WorkflowView 步骤条 8→5 步
[步骤10] fix: 全链路联调修复
```

---

*Step 4 完成。下一步 → 开始实现。*
