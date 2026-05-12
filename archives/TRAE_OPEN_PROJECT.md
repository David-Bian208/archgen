# Trae IDE 手动打开项目指南

> **时间：** 2026-03-30  
> **状态：** ✅ 项目已准备好

---

## 📂 手动打开项目步骤

### 方法 1：使用菜单

1. **在 Trae IDE 中**
2. **点击菜单：** `File` → `Open Folder...`
3. **导航到目录：**
   ```
   /home/admin/.openclaw/workspace/behavior_recorder_service
   ```
4. **点击"选择文件夹"**

---

### 方法 2：使用快捷键

1. **按快捷键：** `Ctrl + K` 然后 `Ctrl + O`
2. **选择目录：**
   ```
   /home/admin/.openclaw/workspace/behavior_recorder_service
   ```
3. **点击"选择文件夹"**

---

### 方法 3：直接拖拽

1. **打开文件管理器**
2. **找到目录：**
   ```
   /home/admin/.openclaw/workspace/behavior_recorder_service
   ```
3. **拖拽到 Trae IDE 窗口**

---

## ✅ 确认项目打开

### 检查文件树

打开后，左侧应该看到：

```
behavior_recorder_service/
├── .trae/
│   ├── context.md          ← 项目上下文
│   └── instructions.md     ← AI 开发指令
├── app/
│   ├── agents/
│   ├── knowledge/
│   └── config.py
├── api/
│   └── endpoints_v4.py
├── frontend/
├── tests/
│   └── test_checklist.md
├── scripts/
│   └── trae-integration.sh
├── AGENTS.md
├── PRD.md
├── TECH_DESIGN.md
├── RESEARCH.md
├── main.py
└── requirements.txt
```

---

## 🤖 开始使用 AI

### 第一次对话

**打开 AI 面板后（通常在右侧），输入：**

```
你好！请阅读以下文档了解项目：
1. .trae/instructions.md - AI 开发指令
2. AGENTS.md - 开发规范
3. PRD.md - 产品需求

阅读完成后告诉我，然后我们开始开发。
```

---

### 开始开发

**让 AI 帮你：**

```
"根据 PRD.md 的 MVP 功能，下一步应该做什么？"

"帮我实现行为记录 API 端点"

"为这个函数编写单元测试"
```

---

## 🔧 终端使用

### 打开终端

**快捷键：** `Ctrl + `` ` ``

### 常用命令

```bash
# 切换到项目目录（如不在）
cd /home/admin/.openclaw/workspace/behavior_recorder_service

# 运行 P0 测试
./scripts/trae-integration.sh p0

# 启动后端服务
source venv/bin/activate
uvicorn main:app --reload --port 8000

# 启动前端（另一个终端）
cd frontend
npm run dev
```

---

## ⚠️ 如果遇到问题

### Q1: 找不到 .trae 文件夹？

**检查：**
```bash
ls -la /home/admin/.openclaw/workspace/behavior_recorder_service/.trae/
```

**应该看到：**
```
context.md
instructions.md
```

---

### Q2: AI 不遵循规范？

**告诉 AI：**
```
"请严格遵守 .trae/instructions.md 和 AGENTS.md 中的规范"
```

---

### Q3: 终端命令执行失败？

**检查权限：**
```bash
chmod +x scripts/*.sh
```

---

## 🤝 与 OpenClaw 协作

### 分工

| 任务 | 工具 |
|------|------|
| **写代码** | Trae IDE（AI 辅助） |
| **执行测试** | Trae 终端 或 告诉我 |
| **生成报告** | 我（OpenClaw） |
| **安全扫描** | 我（OpenClaw） |
| **文档完善** | 我（OpenClaw） |

### 示例流程

```
1. 在 Trae 中写代码
   ↓
2. 在 Trae 终端测试
   ↓
3. 遇到问题或需要报告 → 告诉我
   ↓
4. 我帮你执行自动化任务
```

---

## 📚 相关文档

| 文档 | 位置 |
|------|------|
| Trae 配置指南 | `/home/admin/.openclaw/workspace/TRAE_IDE_CONFIG.md` |
| 项目上下文 | `.trae/context.md` |
| AI 指令 | `.trae/instructions.md` |
| 开发规范 | `AGENTS.md` |
| 集成脚本 | `scripts/trae-integration.sh` |

---

## 🎉 打开项目后

**告诉我，我会帮你：**
1. 验证项目配置
2. 执行第一次 P0 测试
3. 开始新功能开发

---

*现在在 Trae 中打开项目吧！* 🛳️
