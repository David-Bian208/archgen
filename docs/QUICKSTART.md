# ArchGen 快速启动指南

## ✅ 配置已完成

DeepSeek API Key 已配置，可以直接启动测试。

## 🚀 启动步骤

### 1. 启动后端服务

```bash
cd /home/admin/.openclaw/workspace/behavior_recorder_service/archgen
python3 main.py
```

服务将在 **http://localhost:8927** 启动

### 2. 启动前端开发服务器（可选）

```bash
cd frontend
npm run dev
```

前端将在 **http://localhost:3018** 启动

### 3. 测试 API

```bash
# 测试文章分类
curl http://localhost:8927/api/classify \
  -H "Content-Type: application/json" \
  -d '{
    "markdown": "# 人工智能的未来\n\n人工智能正在改变世界。首先，它提高了生产效率。其次，它创造了新的就业机会。"
  }'

# 测试架构图生成
curl http://localhost:8927/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "markdown": "# 系统架构\n\n## 核心模块\n- 用户模块\n- 订单模块\n- 支付模块\n\n## 数据流\n用户 → 订单 → 支付"
  }'
```

### 4. 查看生成的图片

生成的架构图保存在 `output/` 目录

## 📋 配置信息

| 配置项 | 值 |
|--------|-----|
| API Key | `请通过环境变量 DEEPSEEK_API_KEY 配置`  |
| Base URL | `https://api.deepseek.com/v1` |
| Model | `deepseek-chat` |
| 端口 | 8927 |
| 数据库 | `data/archgen.db` |
| 输出目录 | `output/` |

## 🔧 测试工具

已创建测试脚本 `test_api_config.py`，可以快速验证 API 配置：

```bash
python3 test_api_config.py
```

## 📝 下一步

1. 测试核心功能（分类 → 提取 → 生成 → 截图）
2. 验证 3 个核心模板（主张型、因果型、流程型）
3. 准备 10 篇测试文章验证通过率

---

**配置时间**: 2026-05-28 13:15
**配置人**: 战舰 🛳️
