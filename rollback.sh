#!/bin/bash

# ============================================
# 行为观察伙伴 - 回滚脚本
# ============================================
# 用途：快速回滚到上一个备份版本
# 使用：./rollback.sh [备份文件名]
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
PROJECT_DIR="/home/admin/.openclaw/workspace/behavior_recorder_service"
BACKUP_DIR="/home/admin/.openclaw/workspace/backups"

echo ""
echo "============================================"
echo "  行为观察伙伴 - 回滚脚本"
echo "============================================"
echo ""

# 列出可用备份
info() { echo -e "${BLUE}INFO${NC} $@"; }
success() { echo -e "${GREEN}SUCCESS${NC} $@"; }
error() { echo -e "${RED}ERROR${NC} $@"; }

if [ ! -d "$BACKUP_DIR" ]; then
    error "备份目录不存在：$BACKUP_DIR"
    exit 1
fi

echo "可用备份:"
ls -lht "$BACKUP_DIR"/*.tar.gz 2>/dev/null | head -10
echo ""

# 如果没有指定备份文件，使用最新的
if [ -z "$1" ]; then
    BACKUP_FILE=$(ls -t "$BACKUP_DIR"/*.tar.gz 2>/dev/null | head -1)
    if [ -z "$BACKUP_FILE" ]; then
        error "未找到备份文件"
        exit 1
    fi
    info "使用最新备份：$BACKUP_FILE"
else
    BACKUP_FILE="$BACKUP_DIR/$1"
    if [ ! -f "$BACKUP_FILE" ]; then
        error "备份文件不存在：$BACKUP_FILE"
        exit 1
    fi
fi

# 确认回滚
echo -n "确认回滚到 $(basename $BACKUP_FILE)? (y/N): "
read -r CONFIRM
if [[ ! $CONFIRM =~ ^[Yy]$ ]]; then
    info "已取消回滚"
    exit 0
fi

# 停止服务
info "停止当前服务..."
cd "$PROJECT_DIR"
bash stop-all.sh 2>/dev/null || true
pkill -f "python.*main.py" 2>/dev/null || true
sleep 2

# 备份当前版本（以防万一）
CURRENT_BACKUP="backup_before_rollback_$(date '+%Y%m%d_%H%M%S').tar.gz"
info "备份当前版本：$CURRENT_BACKUP"
tar -czf "$BACKUP_DIR/$CURRENT_BACKUP" \
    --exclude=".git" \
    --exclude="*.pyc" \
    --exclude="__pycache__" \
    -C "$(dirname $PROJECT_DIR)" \
    "$(basename $PROJECT_DIR)" 2>/dev/null || true

# 恢复备份
info "恢复备份：$(basename $BACKUP_FILE)..."
rm -rf "$PROJECT_DIR"/*
tar -xzf "$BACKUP_FILE" -C "$PROJECT_DIR"

# 恢复 Git 状态
info "恢复 Git 状态..."
cd "$PROJECT_DIR"
git checkout . 2>/dev/null || true

# 重启服务
info "重启服务..."
bash start-all.sh
sleep 3

# 检查服务
if curl -s http://localhost:8000/api/health | grep -q "ok"; then
    success "回滚完成！服务已恢复"
else
    error "回滚完成但健康检查失败，请手动检查"
    exit 1
fi

echo ""
success "============================================"
success "  回滚完成！"
success "============================================"
echo ""

exit 0
