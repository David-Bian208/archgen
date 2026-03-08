# 引导式行为记录员 V2.0 更新日志

**版本**: 2.0.0  
**日期**: 2026 年 3 月 5 日  
**类型**: 架构升级 - 从单次分析到多轮引导对话

---

## 核心理念转变

### V1.x 旧模式
```
家长一次性输入 → Agent 直接分析 → 输出报告
```
**问题**: 成败看输入质量，信息不足时分析不准确

### V2.0 新模式
```
家长简单描述 → Agent 评估完整度 → 引导提问 → 家长补充 → 分析输出
```
**优势**: 主动创造完美输入，像一位有经验的督导

---

## 核心功能

### 1. 多轮对话会话管理

- 每个记录对话有唯一的 `session_id`
- Agent 内部维护会话状态（ABC 三要素）
- 支持连续多轮对话，直到信息完整

### 2. 智能信息评估

Agent 实时评估 ABC 三要素的完整度：
- `antecedent_status`: complete | incomplete | unclear
- `behavior_status`: complete | incomplete | unclear
- `consequence_status`: complete | incomplete | unclear

### 3. 引导式提问

根据缺失字段，生成针对性问题：
- **A 不清晰**: "在孩子出现这个行为之前，你们正在做什么？"
- **B 不清晰**: "你能更具体地描述一下孩子当时做了什么吗？"
- **C 不清晰**: "当孩子这样做之后，你或周围的人第一时间是怎么做的？"

### 4. 进度可视化

前端实时显示 ABC 收集进度：
```
✓ 前因 (A)  |  ✓ 行为 (B)  |  ○ 后果 (C)
```

---

## API 接口变更

### 新增接口（V2.0）

#### POST /api/v2/record

引导式行为记录接口

**请求**:
```json
{
  "session_id": "可选，首次请求为空",
  "user_input": "用户本次输入的文字"
}
```

**响应**（进行中）:
```json
{
  "session_id": "6819e551",
  "status": "in_progress",
  "response_type": "question",
  "message": "谢谢你的描述。\n\n在孩子出现这个行为之前，你们正在做什么？",
  "progress": {
    "antecedent_gathered": true,
    "behavior_gathered": true,
    "consequence_gathered": false
  }
}
```

**响应**（已完成）:
```json
{
  "session_id": "6819e551",
  "status": "completed",
  "response_type": "report",
  "message": "信息已收集完整，以下是分析报告：",
  "data": {
    "antecedent": "不给他手机",
    "behavior": "打自己头",
    "consequence": "我赶紧把手机给他了",
    "hypothesized_function": "tangible",
    "reasoning": "行为后获得了手机，符合实物获取特征。"
  },
  "progress": {
    "antecedent_gathered": true,
    "behavior_gathered": true,
    "consequence_gathered": true
  }
}
```

#### GET /api/v2/session/{session_id}

获取会话状态

**响应**:
```json
{
  "session_id": "6819e551",
  "created_at": "2026-03-05T10:27:59",
  "is_complete": true,
  "antecedent": "不给他手机",
  "behavior": "打自己头",
  "consequence": "我赶紧把手机给他了",
  "analysis_result": {
    "hypothesized_function": "tangible",
    "reasoning": "..."
  },
  "conversation_count": 3
}
```

#### DELETE /api/v2/session/{session_id}

清理会话

**响应**:
```json
{
  "success": true,
  "message": "会话已清理"
}
```

### 保留接口（V1.1 兼容）

#### GET /api/analyze?description=...

单次行为分析接口（保留用于兼容性）

---

## 前端交互升级

### 聊天式界面

- 欢迎消息引导
- 对话气泡样式（用户/AI 区分）
- 进度指示器（ABC 收集状态）
- 打字动画（等待提示）
- 完整报告卡片
- 一键复制报告
- 开始新记录按钮

### 交互流程

1. **用户输入简单描述**: "他今天打自己头"
2. **AI 评估并提问**: "谢谢描述。在孩子出现这个行为之前，你们正在做什么？"
3. **用户补充**: "因为不给他手机"
4. **AI 继续提问**: "当孩子这样做之后，你第一时间是怎么做的？"
5. **用户补充**: "我赶紧把手机给他了"
6. **AI 输出报告**: 完整 ABC 分析 + 功能假设 + 推理

---

## 实测案例

### 案例：多轮对话完成记录

**第一轮**:
```
用户：他今天打自己头
AI: 谢谢你的描述，我理解你观察到孩子打自己头的行为。

    在孩子出现这个行为之前，你们正在做什么？或者你正在要求他做什么？

进度：✓ A  ✓ B  ○ C
```

**第二轮**:
```
用户：因为不给他手机
AI: 谢谢你的补充，这让我更清楚了。

    当孩子打自己头之后，你或周围的人第一时间是怎么做的？

进度：✓ A  ✓ B  ○ C
```

**第三轮**:
```
用户：我赶紧把手机给他了
AI: 谢谢你的补充，这让我更清楚了。

    A（前因）：因为不给他手机
    B（行为）：打自己头
    C（后果）：我赶紧把手机给他了

📊 行为分析报告

前因 (A): 不给他手机
行为 (B): 打自己头
后果 (C): 我赶紧把手机给他了

假设功能：实物 (Tangible)
推理：行为后获得了手机这一具体物品，符合实物获取特征。

进度：✓ A  ✓ B  ✓ C
```

---

## 技术架构

### 新增文件

| 文件 | 说明 |
|------|------|
| `app/agents/guided_recorder_agent.py` | 引导式 Agent 核心（~300 行） |
| `api/endpoints_v2.py` | V2.0 API 路由 |
| `frontend/src/App.vue` | 聊天式前端界面（重写） |
| `tests/test_guided_agent.py` | V2.0 单元测试 |
| `CHANGELOG_V2.0.md` | 本更新日志 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `main.py` | 注册 V2 路由，版本号更新为 2.0.0 |
| `README.md` | 更新 API 示例 |

### 会话管理

```python
@dataclass
class ABCSession:
    session_id: str
    created_at: datetime
    antecedent: str
    behavior: str
    consequence: str
    conversation_history: list
    is_complete: bool
    analysis_result: dict
```

### 核心流程

```python
def process_input(self, session_id, user_input):
    # 1. 获取或创建会话
    session = self._get_or_create_session(session_id)
    
    # 2. 从输入中提取 ABC
    self._extract_abc_from_input(session, user_input)
    
    # 3. 评估信息完整度（LLM）
    evaluation = self._evaluate_input(session, user_input)
    
    # 4. 决策：提问 or 分析
    if evaluation['decision'] == 'analyze':
        result = self._analyze_complete_abc(session)
        return report_response
    else:
        question = self._generate_question(evaluation)
        return question_response
```

---

## 测试覆盖

### V2.0 测试用例

| 测试 | 说明 | 状态 |
|------|------|------|
| test_create_session | 会话创建 | ✅ |
| test_get_or_create_session | 会话获取 | ✅ |
| test_process_input_initial | 初始输入处理 | ✅ |
| test_process_input_complete | 完整输入处理 | ✅ |
| test_session_continuity | 会话连续性 | ✅ |
| test_generate_question | 问题生成 | ✅ |
| test_cleanup_session | 会话清理 | ✅ |
| test_extract_abc_from_input | ABC 提取 | ✅ |
| test_empty_input_handling | 空输入处理 | ✅ |

**总计**: 9/9 通过

---

## 部署说明

### 后端启动

```bash
cd /home/admin/openclaw/workspace/behavior_recorder_service
python3 main.py
```

### 前端启动

```bash
cd frontend
npm run dev -- --host 0.0.0.0
```

### 访问地址

- **前端界面**: http://localhost:3000
- **API 文档**: http://localhost:8000/docs
- **V2 API**: http://localhost:8000/api/v2/record

---

## 迁移指南

### 从 V1.x 升级

1. **保留 V1 API**: `/api/analyze` 接口继续可用
2. **新增 V2 API**: `/api/v2/record` 用于新界面
3. **前端升级**: 替换 `frontend/src/App.vue`
4. **依赖不变**: 无需新增 Python 依赖

### 兼容性

- ✅ V1.1 单次分析接口保留
- ✅ V1.1 测试用例保留
- ✅ 配置文件格式不变
- ✅ LLM 配置兼容

---

## 下一步建议

### 短期优化
1. **会话过期清理**: 添加定时任务清理旧会话
2. **会话持久化**: 将会话保存到数据库/文件
3. **多会话管理**: 支持同时进行多个记录
4. **引导策略优化**: 基于历史数据优化提问策略

### 中期扩展
1. **用户系统**: 登录、历史记录、多用户
2. **报告导出**: PDF、Word 格式导出
3. **数据可视化**: 行为趋势图表
4. **干预建议**: 基于功能假设生成干预策略

### 长期规划
1. **策略分析师 Agent**: 自动生成干预计划
2. **进展教练 Agent**: 追踪干预效果
3. **沟通协调员 Agent**: 生成多角色报告
4. **移动端应用**: iOS/Android App

---

## 总结

V2.0 是行为记录员系统的**重大架构升级**：

| 维度 | V1.x | V2.0 |
|------|------|------|
| 交互模式 | 单次请求 - 响应 | 多轮引导对话 |
| 用户角色 | 被动输入 | 主动协作 |
| Agent 角色 | 分析工具 | AI 教练 |
| 输入质量 | 依赖用户 | Agent 主动创造 |
| 专业性 | 关键词匹配 | 标准决策流程 |

**核心价值**: 不再等待完美输入，而是主动创造完美输入。这才是 AI 在专业支持领域该扮演的角色。

---

**开发团队**: OpenClaw  
**验收状态**: ✅ 已完成  
**生产就绪**: 是
