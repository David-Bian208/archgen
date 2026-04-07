#!/bin/bash
# 定期安全扫描脚本
# 用法：./security-scan.sh

set -e

WORKSPACE="/home/admin/.openclaw/workspace"
SKILLS_DIR="/home/admin/.npm-global/lib/node_modules/openclaw/skills"
REPORT_FILE="$WORKSPACE/security-scan-$(date +%Y%m%d).md"

echo "🛡️  OpenClaw 安全扫描"
echo "扫描时间：$(date)"
echo "报告文件：$REPORT_FILE"
echo ""

# 创建报告头
cat > "$REPORT_FILE" << EOF
# 安全扫描报告

**扫描时间：** $(date)  
**扫描范围：** $SKILLS_DIR

---

## 危险模式扫描

EOF

# 扫描危险模式
echo "📋 扫描危险模式..."
echo "### 1. base64 解码执行" >> "$REPORT_FILE"
echo '```' >> "$REPORT_FILE"
grep -rn "base64.*decode\|atob\|btoa" "$SKILLS_DIR"/*.md 2>/dev/null | head -10 >> "$REPORT_FILE" || echo "未发现" >> "$REPORT_FILE"
echo '```' >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo "### 2. curl/wget 管道到 bash" >> "$REPORT_FILE"
echo '```' >> "$REPORT_FILE"
grep -rn "curl.*\|.*bash\|wget.*\|.*sh" "$SKILLS_DIR"/*.md 2>/dev/null | head -10 >> "$REPORT_FILE" || echo "未发现" >> "$REPORT_FILE"
echo '```' >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo "### 3. 敏感文件访问" >> "$REPORT_FILE"
echo '```' >> "$REPORT_FILE"
grep -rn "~/.ssh\|~/.aws\|/etc/passwd\|/etc/shadow" "$SKILLS_DIR"/*.md 2>/dev/null | head -10 >> "$REPORT_FILE" || echo "未发现" >> "$REPORT_FILE"
echo '```' >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo "### 4. sudo/root 权限" >> "$REPORT_FILE"
echo '```' >> "$REPORT_FILE"
grep -rn "sudo\|root\|chmod 777" "$SKILLS_DIR"/*.md 2>/dev/null | head -10 >> "$REPORT_FILE" || echo "未发现" >> "$REPORT_FILE"
echo '```' >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 统计技能数量
echo "## 技能统计" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
TOTAL_SKILLS=$(ls -d "$SKILLS_DIR"/*/ 2>/dev/null | wc -l)
echo "- 总技能数：$TOTAL_SKILLS" >> "$REPORT_FILE"
echo "- 扫描时间：$(date +%Y-%m-%d)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 检查 clawhub 更新
echo "## 技能更新检查" >> "$REPORT_FILE"
echo '```' >> "$REPORT_FILE"
clawhub list 2>&1 | head -20 >> "$REPORT_FILE"
echo '```' >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo ""
echo "✅ 扫描完成！"
echo "报告已保存到：$REPORT_FILE"
echo ""

# 如果有 security-auditor，扫描项目代码
if [ -d "$WORKSPACE/skills/security-auditor" ]; then
    echo "🔍 使用 security-auditor 扫描项目代码..."
    echo ""
    echo "建议手动调用 security-auditor 技能审查 behavior_recorder_service 代码"
fi
