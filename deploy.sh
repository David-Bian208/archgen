#!/bin/bash

# ============================================
# 行为观察伙伴 - 阿里云自动化部署脚本
# ============================================
# 用途：Git 拉取 + 服务重启 + 健康检查
# 使用：./deploy.sh
# ============================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
PROJECT_DIR="/home/admin/.openclaw/workspace/behavior_recorder_service"
GIT_REMOTE="origin"
GIT_BRANCH="master"
BACKUP_DIR="/home/admin/.openclaw/workspace/backups"
LOG_FILE="/home/admin/.openclaw/workspace/behavior_recorder_service/deploy.log"

# 日志函数
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$LOG_FILE"
}

info() { log "${BLUE}INFO${NC}" "$@"; }
success() { log "${GREEN}SUCCESS${NC}" "$@"; }
warn() { log "${YELLOW}WARN${NC}" "$@"; }
error() { log "${RED}ERROR${NC}" "$@"; }

# 开始部署
echo ""
echo "============================================"
echo "  行为观察伙伴 - 自动化部署脚本"
echo "  版本：V4.10.4"
echo "  时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"
echo ""

info "开始部署流程..."

# Step 1: 进入项目目录
info "Step 1: 进入项目目录..."
if [ ! -d "$PROJECT_DIR" ]; then
    error "项目目录不存在：$PROJECT_DIR"
    exit 1
fi
cd "$PROJECT_DIR"
success "已进入项目目录"

# Step 2: 备份当前版本
info "Step 2: 备份当前版本..."
BACKUP_NAME="backup_$(date '+%Y%m%d_%H%M%S')"
mkdir -p "$BACKUP_DIR"
tar -czf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" \
    --exclude=".git" \
    --exclude="*.pyc" \
    --exclude="__pycache__" \
    --exclude="*.log" \
    --exclude="test_logs.db" \
    -C "$(dirname $PROJECT_DIR)" \
    "$(basename $PROJECT_DIR)" 2>/dev/null || true
success "已备份到：$BACKUP_DIR/$BACKUP_NAME.tar.gz"

# Step 3: Git 拉取最新代码
info "Step 3: Git 拉取最新代码..."
git fetch "$GIT_REMOTE"
LOCAL_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "none")
REMOTE_COMMIT=$(git rev-parse "$GIT_REMOTE/$GIT_BRANCH" 2>/dev/null || echo "none")

if [ "$LOCAL_COMMIT" == "$REMOTE_COMMIT" ]; then
    warn "代码已是最新，无需更新"
else
    info "本地版本：$LOCAL_COMMIT"
    info "远程版本：$REMOTE_COMMIT"
    
    # 处理可能的分支冲突
    git config pull.rebase false
    if git pull "$GIT_REMOTE" "$GIT_BRANCH"; then
        success "Git 拉取成功"
    else
        error "Git 拉取失败，尝试重置到远程版本..."
        git reset --hard "$GIT_REMOTE/$GIT_BRANCH"
        success "已强制重置到远程版本"
    fi
    
    NEW_COMMIT=$(git rev-parse HEAD)
    success "已更新到版本：$NEW_COMMIT"
fi

# Step 4: 检查配置文件
info "Step 4: 检查配置文件..."
if [ ! -f "config.yaml" ]; then
    warn "config.yaml 不存在，从示例复制..."
    cp config.yaml.example config.yaml
    warn "请编辑 config.yaml 填写 API Key"
    exit 1
fi

# 检查 API Key 是否配置
if grep -q "sk-" config.yaml; then
    success "配置文件检查通过"
else
    warn "config.yaml 中未检测到 API Key，请确认已配置"
fi

# Step 5: 检查依赖
info "Step 5: 检查 Python 依赖..."
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt -q
    success "依赖检查完成"
fi

# Step 6: 停止旧服务
info "Step 6: 停止旧服务..."
if [ -f "stop-all.sh" ]; then
    bash stop-all.sh 2>/dev/null || true
fi

# 清理残留进程
pkill -f "python.*main.py" 2>/dev/null || true
pkill -f "python.*endpoints" 2>/dev/null || true
sleep 2
success "旧服务已停止"

# Step 7: 启动新服务
info "Step 7: 启动新服务..."
if [ -f "start-all.sh" ]; then
    bash start-all.sh
    sleep 3
    success "新服务已启动"
else
    error "start-all.sh 不存在"
    exit 1
fi

# Step 8: 健康检查
info "Step 8: 执行健康检查..."
HEALTH_CHECK_ATTEMPTS=5
HEALTH_CHECK_INTERVAL=2

for i in $(seq 1 $HEALTH_CHECK_ATTEMPTS); do
    sleep $HEALTH_CHECK_INTERVAL
    
    # 检查端口
    if netstat -tlnp 2>/dev/null | grep -q ":8000" || \
       ss -tlnp 2>/dev/null | grep -q ":8000"; then
        success "端口 8000 已监听"
        
        # 检查 API
        if curl -s http://localhost:8000/api/health | grep -q "ok"; then
            success "API 健康检查通过"
            break
        fi
    fi
    
    if [ $i -eq $HEALTH_CHECK_ATTEMPTS ]; then
        error "健康检查失败：服务未在 $HEALTH_CHECK_ATTEMPTS 次尝试内启动"
        exit 1
    fi
    
    info "等待服务启动... (尝试 $i/$HEALTH_CHECK_ATTEMPTS)"
done

# Step 9: 检查服务状态
info "Step 9: 检查服务状态..."
echo ""
echo "----------------------------------------"
echo "  服务状态:"
echo "----------------------------------------"

# 检查后端
if pgrep -f "python.*main.py" > /dev/null; then
    echo "  ✅ 后端服务：运行中 (PID: $(pgrep -f 'python.*main.py' | head -1))"
else
    echo "  ❌ 后端服务：未运行"
fi

# 检查端口
if netstat -tlnp 2>/dev/null | grep -q ":8000" || ss -tlnp 2>/dev/null | grep -q ":8000"; then
    echo "  ✅ 端口 8000: 已监听"
else
    echo "  ❌ 端口 8000: 未监听"
fi

# 检查 Git 版本
CURRENT_VERSION=$(git rev-parse --short HEAD)
echo "  📦 当前版本：$CURRENT_VERSION"

echo "----------------------------------------"
echo ""

# 完成
success "============================================"
success "  部署完成！"
success "============================================"
echo ""
info "日志文件：$LOG_FILE"
info "备份位置：$BACKUP_DIR/$BACKUP_NAME.tar.gz"
echo ""

# 显示访问信息
echo "============================================"
echo "  访问信息:"
echo "============================================"
echo "  API 地址：http://47.103.229.125:8000"
echo "  健康检查：http://47.103.229.125:8000/api/health"
echo "  API 文档：http://47.103.229.125:8000/docs"
echo "============================================"
echo ""

exit 0
