#!/bin/bash
# 凭证备份脚本
# 用法：./backup-credentials.sh

set -e

BACKUP_DIR="/home/admin/.openclaw/workspace/backups/credentials"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "🔐 凭证备份"
echo "备份时间：$(date)"
echo "备份目录：$BACKUP_DIR"
echo ""

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 备份凭证文件
echo "正在备份凭证文件..."

# models.json
if [ -f ~/.openclaw/agents/main/agent/models.json ]; then
    cp ~/.openclaw/agents/main/agent/models.json "$BACKUP_DIR/models.$TIMESTAMP.json"
    echo "✅ models.json 备份成功"
else
    echo "⚠️ models.json 未找到"
fi

# auth-profiles.json
if [ -f ~/.openclaw/agents/main/agent/auth-profiles.json ]; then
    cp ~/.openclaw/agents/main/agent/auth-profiles.json "$BACKUP_DIR/auth-profiles.$TIMESTAMP.json"
    echo "✅ auth-profiles.json 备份成功"
else
    echo "ℹ️ auth-profiles.json 不存在（可能使用环境变量）"
fi

# exec-approvals.json
if [ -f ~/.openclaw/exec-approvals.json ]; then
    cp ~/.openclaw/exec-approvals.json "$BACKUP_DIR/exec-approvals.$TIMESTAMP.json"
    echo "✅ exec-approvals.json 备份成功"
else
    echo "⚠️ exec-approvals.json 未找到"
fi

# openclaw.json
if [ -f ~/.openclaw/openclaw.json ]; then
    cp ~/.openclaw/openclaw.json "$BACKUP_DIR/openclaw.$TIMESTAMP.json"
    echo "✅ openclaw.json 备份成功"
else
    echo "⚠️ openclaw.json 未找到"
fi

echo ""
echo "备份完成！"
echo ""
echo "备份文件列表："
ls -lh "$BACKUP_DIR/" | tail -10

# 清理旧备份（保留最近 10 个）
echo ""
echo "清理旧备份（保留最近 10 个）..."
cd "$BACKUP_DIR"
ls -t *.json 2>/dev/null | tail -n +11 | xargs -r rm -v
echo "✅ 清理完成"
