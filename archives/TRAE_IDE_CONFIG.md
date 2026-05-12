# Trae IDE 配置指南

> **创建时间：** 2026-03-30  
> **用途：** Trae IDE 首次启动配置

---

## 🎯 配置步骤

### 第 1 步：偏好设置（当前界面）

**建议配置：**

| 选项 | 推荐选择 | 说明 |
|------|----------|------|
| **导入配置** | 从 VS Code 导入配置 | 如果你用过 VS Code |
| **快捷键风格** | 使用 VS Code 快捷键风格 | 最常用，符合习惯 |

**操作：**
1. 选择"从 VS Code 导入配置"（如有）
2. 选择"使用 VS Code 快捷键风格"
3. 点击"继续"

---

### 第 2 步：登录账号（如提示）

** Trae 可能需要登录：**

1. **使用 GitHub 登录**（推荐）
   - 点击 GitHub 图标
   - 授权 Trae 访问

2. **使用邮箱登录**
   - 输入邮箱
   - 接收验证码

**注意：** 国内版 Trae 可能需要手机号注册

---

### 第 3 步：选择项目

**如果 Trae 没有自动打开项目：**

1. **File → Open Folder**
2. **选择项目目录：**
   ```
   /home/admin/.openclaw/workspace/behavior_recorder_service
   ```
3. **点击"选择文件夹"**

---

## ⚙️ 项目配置检查

### 确认文件存在

打开项目后，检查以下文件：

```
behavior_recorder_service/
├── .trae/
│   ├── context.md          ✅ 项目上下文
│   └── instructions.md     ✅ AI 开发指令
├── AGENTS.md               ✅ 开发规范
├── PRD.md                  ✅ 产品需求
└── TECH_DESIGN.md          ✅ 技术设计
```

---

## 🤖 AI 配置

### 首次使用 AI 功能

1. **打开 AI 面板**（右侧或左侧图标）
2. **阅读项目指令**：
   ```
   告诉 AI："请阅读 .trae/instructions.md"
   ```
3. **开始对话**：
   ```
   "根据 PRD.md，帮我实现行为记录功能"
   ```

---

## 🔧 推荐配置

### 1. 终端配置

**打开终端：** `Ctrl + `` ` ``

**测试集成脚本：**
```bash
# 运行 P0 测试
./scripts/trae-integration.sh p0

# 检查状态
./scripts/trae-integration.sh status
```

---

### 2. Python 环境

**如果使用 Python 后端：**

1. **打开命令面板：** `Ctrl + Shift + P`
2. **输入：** "Python: Select Interpreter"
3. **选择：**
   ```
   /home/admin/.openclaw/workspace/behavior_recorder_service/venv/bin/python
   ```
   （如没有虚拟环境，使用系统 Python）

---

### 3. 安装依赖

**在 Trae 终端中：**

```bash
cd /home/admin/.openclaw/workspace/behavior_recorder_service

# 创建虚拟环境（如没有）
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

---

### 4. Vue 前端配置

**如果使用 Vue 前端：**

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

---

## 📋 快速开始

### 配置完成后

1. **阅读文档**
   - `.trae/context.md` - 项目背景
   - `.trae/instructions.md` - AI 指令
   - `AGENTS.md` - 开发规范

2. **与 AI 对话**
   ```
   "帮我了解这个项目"
   "根据 PRD，下一步应该做什么？"
   ```

3. **开始开发**
   - 让 AI 帮你写代码
   - 在终端运行测试
   - 查看代码效果

---

## 🤝 与 OpenClaw 协作

### 分工

| 任务 | 工具 |
|------|------|
| **写代码** | Trae IDE（AI 辅助） |
| **执行测试** | Trae 终端 或 OpenClaw |
| **生成报告** | OpenClaw |
| **安全扫描** | OpenClaw |
| **部署配置** | OpenClaw |

### 示例工作流

```
1. 在 Trae 中让 AI 写代码
   ↓
2. 在 Trae 终端运行测试
   ↓
3. 回到 OpenClaw：
   "执行 P0 测试"
   "生成测试报告"
   ↓
4. 根据结果继续开发
```

---

## ⚠️ 常见问题

### Q1: Trae 打不开项目？

**解决：**
```bash
# 手动打开
/usr/share/trae-cn/bin/trae-cn /home/admin/.openclaw/workspace/behavior_recorder_service
```

---

### Q2: AI 不遵循项目规范？

**解决：**
```
告诉 AI："请阅读 .trae/instructions.md 和 AGENTS.md"
```

---

### Q3: 终端命令找不到？

**解决：**
```bash
# 确保在项目根目录
cd /home/admin/.openclaw/workspace/behavior_recorder_service

# 确保脚本有执行权限
chmod +x scripts/*.sh
```

---

## 📚 相关文档

| 文档 | 位置 |
|------|------|
| Trae 配置指南 | 本文件 |
| 项目上下文 | `.trae/context.md` |
| AI 指令 | `.trae/instructions.md` |
| 开发规范 | `AGENTS.md` |
| 集成脚本 | `scripts/trae-integration.sh` |

---

## 🎉 配置完成后

告诉我，我会帮你：
1. 验证配置
2. 执行第一次测试
3. 开始新功能开发

---

*最后更新：2026-03-30*
