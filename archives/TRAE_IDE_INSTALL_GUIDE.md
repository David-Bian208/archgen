# Trae IDE 安装指南

> **创建时间：** 2026-03-30  
> **状态：** ⚠️ 需要手动下载

---

## 📥 下载步骤

### 第 1 步：访问官网

打开浏览器访问：**https://www.trae.cn/ide/download**

---

### 第 2 步：选择版本

根据你的系统选择：

| 系统 | 版本 | 说明 |
|------|------|------|
| **macOS** | .dmg (Apple Silicon) | M1/M2/M3 芯片 |
| **macOS** | .dmg (Intel) | Intel 芯片 |
| **Windows** | .exe (x64) | Windows 10/11 |
| **Linux** | .deb / .rpm | Ubuntu/Debian 或 RedHat/CentOS |

---

### 第 3 步：下载安装

**macOS：**
```bash
# 1. 下载完成后，打开 .dmg 文件
# 2. 拖动 Trae.app 到 Applications 文件夹
# 3. 在 Applications 中打开 Trae IDE
```

**Windows：**
```bash
# 1. 运行下载的安装程序
# 2. 按照安装向导完成安装
```

**Linux：**
```bash
# Debian/Ubuntu
sudo dpkg -i Trae-*.deb

# RedHat/CentOS
sudo rpm -ivh Trae-*.rpm
```

---

## 📂 打开项目

### 安装完成后

1. **启动 Trae IDE**
2. **File → Open Folder**
3. **选择项目目录：**
   ```
   /home/admin/.openclaw/workspace/behavior_recorder_service
   ```

---

## ⚙️ 项目配置

项目已配置好 Trae IDE 专用文件：

```
behavior_recorder_service/
├── .trae/
│   ├── context.md          # 项目上下文（Trae 自动读取）
│   └── instructions.md     # AI 开发指令（Trae AI 必读）
└── scripts/
    └── trae-integration.sh # 集成脚本
```

---

## 🎯 使用指南

### 在 Trae 中开始编码

1. **打开项目后**，Trae 会自动读取 `.trae/context.md`
2. **与 AI 对话**时，它会遵循 `.trae/instructions.md` 的规范
3. **示例对话：**
   ```
   "请阅读 .trae/instructions.md，了解项目开发规范"
   
   "根据 PRD.md 的 MVP 功能要求，帮我实现 XXX 功能"
   
   "遵循 AGENTS.md 的规范，优化这个端点"
   ```

---

## 🔧 集成脚本

### 在 Trae 终端中使用

```bash
# 同步项目配置
./scripts/trae-integration.sh sync

# 运行 P0 测试
./scripts/trae-integration.sh p0

# 运行全量测试
./scripts/trae-integration.sh test

# 检查服务状态
./scripts/trae-integration.sh status

# 执行安全扫描
./scripts/trae-integration.sh security
```

---

## 🤝 Trae + OpenClaw 协作

### 工作流

```
1. 在 Trae 中写代码
   ↓
2. 在 Trae 终端运行测试
   ↓
3. 回到 OpenClaw 告诉我：
   "执行 P0 测试"
   "生成测试报告"
   "扫描安全问题"
   ↓
4. 我帮你执行自动化任务
```

---

## ⚠️ 注意事项

### 1. API Key 配置

Trae 项目使用环境变量：
```bash
# 在项目根目录创建 .env 文件
LLM_API_KEY=sk-your-key-here
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

**⚠️ 不要将 .env 提交到 Git！**

---

### 2. 项目规范

所有开发必须遵循：
- `AGENTS.md` - AI 开发指令
- `PRD.md` - 产品需求
- `TECH_DESIGN.md` - 技术设计
- `test_checklist.md` - 测试清单

---

### 3. 提交前检查

```bash
# 运行 P0 测试
./scripts/trae-integration.sh p0

# 检查代码规范
# （Trae AI 会自动遵循 AGENTS.md）
```

---

## 📚 相关文档

| 文档 | 位置 |
|------|------|
| Trae 官网 | https://www.trae.cn |
| 项目上下文 | `.trae/context.md` |
| AI 指令 | `.trae/instructions.md` |
| 集成脚本 | `scripts/trae-integration.sh` |

---

## 🎉 完成安装后

告诉我，我会帮你：
1. 验证项目配置
2. 执行第一次测试
3. 开始新功能开发

---

*最后更新：2026-03-30*
