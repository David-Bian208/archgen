#!/bin/bash
set -e

echo "🚀 初始化 OpenClaw + Trea + Qwen3.6-Plus 协同开发环境..."
echo ""

# 1. 创建核心目录
mkdir -p .claw/prompts .claw/context .git/hooks

# 2. 创建 Prompt 模板
cat > .claw/prompts/architect.md << 'EOF'
# OpenClaw Architect Prompt
**角色：** 架构规划与任务路由
**输出模板：** 架构决策表 + 任务拆解 + 架构约束
EOF

cat > .claw/prompts/coder.md << 'EOF'
# Trea Coder Prompt
**角色：** 代码实现与闭环调试
**输出模板：** 实现方案 + Diff + 验证用例 + 架构检查
EOF

cat > .claw/prompts/warship.md << 'EOF'
# Warship Validator Prompt
**角色：** 自动化验证与质量门禁
**输出模板：** 验证结果 + 检查清单 + 下一步建议
EOF

echo "✅ Prompt 模板已创建"

# 3. 写入 OpenClaw 路由配置
cat > .claw/agents.yaml << 'EOF'
version: "1.0"
defaults:
  model: "qwen3.6-plus"
  temperature: 0.2
  max_tokens: 4096
  api_key_env: "DASHSCOPE_API_KEY"
  top_p: 0.8
  frequency_penalty: 0.5

observability:
  trace_enabled: true
  log_dir: "/tmp/qwen36_traces"

quality_gates:
  enabled: true
  lint_tool: "ruff"
  type_tool: "mypy"
  security_tool: "bandit"
  incremental: true

agents:
  openclaw_architect:
    role: "architect"
    prompt_file: "./prompts/architect.md"
    routing_rules:
      - trigger: ["仓库分析", "基线锁定", "架构", "设计"]
        target: "openclaw_architect"
        max_steps: 3
      - trigger: ["代码改进", "Bug 修复", "实现"]
        target: "trea_coder"
        context_lock: ["REPO_MAP"]
  
  trea_coder:
    role: "coder"
    prompt_file: "./prompts/coder.md"
    routing_rules:
      - trigger: ["验证通过", "测试完成"]
        target: "warship_validator"
      - trigger: ["⚠️ Failed", "编译失败"]
        target: "trea_coder"
        auto_retry: 2
  
  warship_validator:
    role: "validator"
    prompt_file: "./prompts/warship.md"
    routing_rules:
      - trigger: ["验证通过"]
        target: "openclaw_architect"
        action: "archive_to_memory"

safety_limits:
  max_retry_count: 3
  max_conversation_turns: 20
  token_budget_per_task: 10000
EOF

echo "✅ 路由配置已创建：.claw/agents.yaml"

# 3. 生成 REPO_MAP
ENTRY=$(find . -maxdepth 1 -name "main.*" | head -n 1 | sed 's|^\./||')
CONFIGS=$(find . -maxdepth 2 -name "*.yaml" -o -name "*.json" | grep -v node_modules | head -n 5 | sed 's|^\./||' | tr '\n' ', ')

cat > .claw/context/repo_map.md << EOF
# 🗺️ REPO_MAP - 仓库指纹

**入口文件:** ${ENTRY:-main.py}
**配置文件:** ${CONFIGS:-config.yaml}
**生成时间:** $(date '+%Y-%m-%d %H:%M:%S')

## 改进协议
1. 基线锁定：REPO_MAP 永久保留
2. 局部修改：仅修改指定文件
3. 增量门禁：仅检查变更文件
EOF

echo "✅ REPO_MAP 已生成"

# 4. 绑定 Git Hook
cat > .git/hooks/pre-commit << 'HOOK'
#!/bin/bash
set -e
echo "🛡️ 运行增量质量门禁..."
CHANGED=$(git diff --cached --name-only)
if [ -n "$CHANGED" ]; then
    python3 scripts/trea_hook.py --incremental --files "$CHANGED" || exit 1
fi
echo "✅ 门禁通过"
HOOK

chmod +x .git/hooks/pre-commit
echo "✅ Git pre-commit 已绑定"

echo ""
echo "=========================================="
echo "✅ 初始化完成！"
echo "=========================================="
echo ""
