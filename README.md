# 行为记录员微服务 (Behavior Recorder Service)

自闭症干预辅助系统 - 第一阶段 MVP

**当前版本**: 1.1.0（优化版）

## 项目简介

行为记录员是自闭症干预辅助系统的第一个核心组件，负责将家长的自然语言行为描述转化为结构化的 ABC 分析报告。

### 核心功能

- **ABC 结构化提取**：从自然语言描述中自动提取前因 (Antecedent)、行为 (Behavior)、后果 (Consequence)
- **功能假设分析**：基于 ABA 理论，判断行为的四种可能功能（逃避、实物、关注、自我刺激）
- **可插拔 LLM 层**：支持百炼、DeepSeek、OpenAI 等多种大模型服务商，通过配置自由切换

### 工作流程

```
家长描述 → [步骤一：ABC 提取] → [步骤二：功能假设] → 结构化报告
```

## 技术栈

- **后端**: Python 3.10+ + FastAPI
- **前端**: Vue 3 + Vite
- **LLM 接口**: OpenAI 兼容 API（支持百炼、DeepSeek、OpenAI 等）
- **配置**: YAML 配置文件 + 环境变量

## 快速开始

### 1. 环境准备

确保已安装 Python 3.10+ 和 Node.js 18+

```bash
# 检查版本
python --version  # 应 >= 3.10
node --version    # 应 >= 18
```

### 2. 后端安装与配置

```bash
# 进入项目目录
cd behavior_recorder_service

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 复制配置文件
cp config.yaml.example config.yaml

# 编辑配置文件，填入你的 API 密钥
# 可以使用百炼、DeepSeek 或 OpenAI
```

#### 配置文件说明 (config.yaml)

```yaml
llm:
  provider: "openai"
  openai:
    # 百炼示例
    api_key: "sk-your-api-key"
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model: "qwen-turbo"
    
    # DeepSeek 示例（取消注释使用）
    # base_url: "https://api.deepseek.com/v1"
    # model: "deepseek-chat"
    
    # OpenAI 原生示例（取消注释使用）
    # base_url: "https://api.openai.com/v1"
    # model: "gpt-4"

server:
  host: "0.0.0.0"
  port: 8000
  debug: false
```

#### 支持的 LLM 服务商

| 服务商 | base_url | 推荐模型 |
|--------|----------|----------|
| 阿里百炼 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | qwen-turbo, qwen-plus, qwen-max |
| DeepSeek | `https://api.deepseek.com/v1` | deepseek-chat, deepseek-coder |
| OpenAI | `https://api.openai.com/v1` | gpt-4, gpt-3.5-turbo |

### 3. 启动后端服务

```bash
# 方式一：直接运行
python main.py

# 方式二：使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000

# 开发模式（自动重载）
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

访问 API 文档：http://localhost:8000/docs

### 4. 前端安装与运行

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 开发模式（带热重载）
npm run dev

# 生产构建
npm run build
```

开发服务器将运行在 http://localhost:3000

### 5. 测试

```bash
# 运行单元测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_agent.py -v
```

## API 接口说明

### POST /api/analyze

行为分析接口

**请求体**:
```json
{
  "description": "不给他手机，他就打自己头，我赶紧把手机给他了。"
}
```

**响应** (V1.1 新增 `reasoning` 字段):
```json
{
  "success": true,
  "message": "分析成功",
  "data": {
    "antecedent": "不给他手机",
    "behavior": "打自己头",
    "consequence": "把手机给他",
    "hypothesized_function": "tangible",
    "reasoning": "行为后获得了想要的物品，符合实物获取特征。"
  }
}
```

### GET /api/health

健康检查接口

**响应**:
```json
{
  "status": "healthy",
  "llm_provider": "openai",
  "llm_model": "qwen-turbo"
}
```

### GET /api/

服务信息接口

## 环境变量覆盖

配置可通过环境变量覆盖（优先级高于 config.yaml）：

```bash
export LLM_API_KEY="sk-your-key"
export LLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export LLM_MODEL="qwen-plus"
```

## 项目结构

```
behavior_recorder_service/
├── app/
│   ├── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   └── behavior_recorder_agent.py  # 核心 Agent 实现
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py                     # LLM 抽象基类
│   │   └── openai_client.py            # OpenAI 兼容客户端
│   └── config.py                       # 配置加载
├── api/
│   ├── __init__.py
│   └── endpoints.py                    # FastAPI 路由
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── App.vue                     # 主界面组件
│   │   └── main.js                     # 入口文件
│   ├── package.json
│   └── vite.config.js
├── tests/
│   ├── __init__.py
│   └── test_agent.py                   # 单元测试
├── config.yaml.example                 # 配置模板
├── requirements.txt                    # Python 依赖
├── main.py                             # 应用入口
└── README.md                           # 本文档
```

## 核心业务逻辑

### 步骤一：ABC 结构化提取

**系统提示词**: "你是一个精准的信息提取工具，请严格按照用户要求输出 JSON，不要任何解释。"

**用户提示词**: 从描述中提取前因、行为、后果三要素

### 步骤二：功能假设

**系统提示词**: "你是一名应用行为分析（ABA）专家，请从四个标准功能中做出最严谨的选择。"

**功能选项**:
- **escape**: 为逃避/终止任务或情境
- **tangible**: 为获得物品、食物或活动
- **attention**: 为获得他人的注意（正负皆可）
- **automatic**: 为自我刺激或感官调节

## 示例用例

### 输入示例

```
不给他手机，他就打自己头，我赶紧把手机给他了。
```

### 输出示例

```json
{
  "antecedent": "不给他手机",
  "behavior": "打自己头",
  "consequence": "把手机给他",
  "hypothesized_function": "tangible"
}
```

**分析**: 孩子通过自伤行为获得了想要的手机，符合"实物 (tangible)"功能。

## Docker 部署（可选）

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 故障排除

### 常见问题

1. **API 密钥错误**
   - 检查 config.yaml 中的 api_key 是否正确
   - 确认账户余额充足

2. **连接超时**
   - 检查网络连接
   - 确认 base_url 地址正确
   - 增加 timeout 配置

3. **JSON 解析失败**
   - 检查 LLM 模型是否支持 response_format
   - 尝试更换模型（如 qwen-turbo → qwen-plus）

### 日志查看

后端日志会输出到控制台，包含：
- Agent 初始化信息
- 每步分析的输入输出
- API 调用详情

## 下一步计划

第一阶段 MVP 完成后，后续将实现：

1. **策略分析师 Agent**: 基于 ABC 分析生成干预策略
2. **进展教练 Agent**: 追踪干预进度并动态优化
3. **沟通协调员 Agent**: 生成多角色报告
4. **数据持久化**: 添加数据库支持
5. **用户系统**: 多用户、多儿童支持

## 许可证

本项目为自闭症干预辅助系统内部开发，未经许可不得外传。

---

**开发团队**: OpenClaw  
**版本**: 1.0.0  
**日期**: 2026 年 3 月 5 日
