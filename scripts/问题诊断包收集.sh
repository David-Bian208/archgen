#!/bin/bash
# 问题诊断包自动收集脚本
# 用法：./scripts/问题诊断包收集.sh [问题简述]

set -e

# 参数
PROBLEM_DESC="${1:-未命名问题}"
OUTPUT_DIR="/tmp/trae-diagnosis-$(date +%Y%m%d-%H%M%S)"
PROJECT_DIR="/home/admin/.openclaw/workspace/behavior_recorder_service"

echo "🔍 开始收集问题诊断包..."
echo "问题描述：$PROBLEM_DESC"
echo "输出目录：$OUTPUT_DIR"
echo ""

# 创建输出目录
mkdir -p $OUTPUT_DIR

# 1. Git 历史
echo "📝 收集 Git 历史..."
cd $PROJECT_DIR
git log --oneline -10 > $OUTPUT_DIR/git-history.txt 2>/dev/null || echo "无 Git 历史"
git diff HEAD~5 > $OUTPUT_DIR/git-diff.txt 2>/dev/null || echo "无变更记录"
git status > $OUTPUT_DIR/git-status.txt 2>/dev/null || echo "无法获取 Git 状态"

# 2. 最近修改的文件
echo "📁 收集最近修改的文件..."
find . -name "*.py" -o -name "*.vue" -o -name "*.js" -o -name "*.md" 2>/dev/null | \
  xargs ls -lt 2>/dev/null | head -20 > $OUTPUT_DIR/recent-files.txt || echo "无最近修改文件"

# 3. 日志
echo "📋 收集日志..."
tail -100 server.log > $OUTPUT_DIR/server.log 2>/dev/null || echo "无后端日志"
tail -100 frontend/vite.log > $OUTPUT_DIR/frontend.log 2>/dev/null || echo "无前端日志"
tail -100 analytics.log > $OUTPUT_DIR/analytics.log 2>/dev/null || echo "无分析日志"

# 4. 测试报告
echo "🧪 运行测试..."
python3 -m pytest tests/ -v --tb=short > $OUTPUT_DIR/test-report.txt 2>&1 || echo "测试执行失败"

# 5. 覆盖率审计
echo "📊 运行覆盖率审计..."
python3 tests/parity_audit.py > $OUTPUT_DIR/coverage-audit.txt 2>&1 || echo "覆盖率审计失败"

# 6. Skills 状态
echo "🛠️ 检查 Skills 状态..."
if [ -f "/home/admin/.openclaw/workspace/skills/.loaded_skills.json" ]; then
  cat /home/admin/.openclaw/workspace/skills/.loaded_skills.json > $OUTPUT_DIR/skills-status.txt
else
  echo "Skills 未加载" > $OUTPUT_DIR/skills-status.txt
fi

# 7. 创建诊断包文档
echo "📦 创建诊断包文档..."
cat > $OUTPUT_DIR/问题诊断包.md << EOF
# 问题诊断包

**生成时间：** $(date)
**生成方式：** 自动收集
**问题描述：** $PROBLEM_DESC
**项目目录：** $PROJECT_DIR

---

## 📋 包含的文件

| 文件 | 说明 | 状态 |
|------|------|------|
| git-history.txt | Git 提交历史（最近 10 条） | $([ -s $OUTPUT_DIR/git-history.txt ] && echo "✅" || echo "❌") |
| git-diff.txt | 最近代码变更（最近 5 次） | $([ -s $OUTPUT_DIR/git-diff.txt ] && echo "✅" || echo "❌") |
| git-status.txt | 当前 Git 状态 | $([ -s $OUTPUT_DIR/git-status.txt ] && echo "✅" || echo "❌") |
| recent-files.txt | 最近修改的文件（20 个） | $([ -s $OUTPUT_DIR/recent-files.txt ] && echo "✅" || echo "❌") |
| server.log | 后端日志（最近 100 行） | $([ -s $OUTPUT_DIR/server.log ] && echo "✅" || echo "❌") |
| frontend.log | 前端日志（最近 100 行） | $([ -s $OUTPUT_DIR/frontend.log ] && echo "✅" || echo "❌") |
| analytics.log | 分析日志（最近 100 行） | $([ -s $OUTPUT_DIR/analytics.log ] && echo "✅" || echo "❌") |
| test-report.txt | 测试报告 | $([ -s $OUTPUT_DIR/test-report.txt ] && echo "✅" || echo "❌") |
| coverage-audit.txt | 覆盖率审计报告 | $([ -s $OUTPUT_DIR/coverage-audit.txt ] && echo "✅" || echo "❌") |
| skills-status.txt | Skills 状态 | $([ -s $OUTPUT_DIR/skills-status.txt ] && echo "✅" || echo "❌") |

---

## 🎯 下一步

### 1. 填写问题描述

请编辑此文件，补充以下信息：

- **原始问题：** [用 1-2 句话描述]
- **沟通历史：** [和 DAVID 沟通了几轮？]
- **代码修改：** [修改了哪些文件？]
- **测试结果：** [哪些测试通过/失败？]
- **卡壳原因：** [为什么无法继续？]
- **需要的帮助：** [需要 DAVID/战舰帮助什么？]

### 2. 打包发送

\`\`\`bash
cd $OUTPUT_DIR
tar -czf diagnosis.tar.gz *
echo "诊断包已打包：$OUTPUT_DIR/diagnosis.tar.gz"
\`\`\`

### 3. 发送给 DAVID/战舰

**发送内容：**
1. 诊断包路径：\`$OUTPUT_DIR/diagnosis.tar.gz\`
2. 或发送填写后的 \`问题诊断包.md\`

**发送方式：**
- 直接复制文件内容
- 或发送文件路径
- 或上传到共享位置

---

## 📞 联系方式

**DAVID：** 产品负责人（需求、判定）
**战舰（OpenClaw）：** 架构师 + QA + Ops（技术支持）

**如何请求帮助：**

\`\`\`
请分析这个诊断包：[路径]
问题：[简要描述]
我需要的帮助：[具体需求]
\`\`\`

---

**自动生成完成！** 🎉

**诊断包位置：** $OUTPUT_DIR/问题诊断包.md
**压缩包位置：** $OUTPUT_DIR/diagnosis.tar.gz
EOF

# 创建压缩包
cd $OUTPUT_DIR
tar -czf diagnosis.tar.gz * 2>/dev/null || echo "打包失败"

echo ""
echo "✅ 诊断包生成完成！"
echo ""
echo "📄 文档位置：$OUTPUT_DIR/问题诊断包.md"
echo "📦 压缩包位置：$OUTPUT_DIR/diagnosis.tar.gz"
echo ""
echo "📋 下一步："
echo "1. 编辑 $OUTPUT_DIR/问题诊断包.md 填写问题描述"
echo "2. 运行：tar -czf diagnosis.tar.gz *"
echo "3. 发送诊断包给 DAVID/战舰"
echo ""
