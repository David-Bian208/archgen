#!/bin/bash

# ============================================
# 行为观察伙伴 - 状态检查脚本
# ============================================
# 用途：快速检查服务运行状态
# 使用：./status.sh
# ============================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="/home/admin/.openclaw/workspace/behavior_recorder_service"

echo ""
echo "============================================"
echo "  行为观察伙伴 - 服务状态"
echo "============================================"
echo ""

# 1. 检查进程
echo "1️⃣  进程状态:"
if pgrep -f "python.*main.py" > /dev/null; then
    PID=$(pgrep -f "python.*main.py" | head -1)
    echo -e "   ${GREEN}✅${NC} 后端服务运行中 (PID: $PID)"
else
    echo -e "   ${RED}❌${NC} 后端服务未运行"
fi
echo ""

# 2. 检查端口
echo "2️⃣  端口监听:"
if netstat -tlnp 2>/dev/null | grep -q ":8000" || ss -tlnp 2>/dev/null | grep -q ":8000"; then
    PORT_INFO=$(netstat -tlnp 2>/dev/null | grep ":8000" || ss -tlnp 2>/dev/null | grep ":8000")
    echo -e "   ${GREEN}✅${NC} 端口 8000 已监听"
    echo "      $PORT_INFO"
else
    echo -e "   ${RED}❌${NC} 端口 8000 未监听"
fi
echo ""

# 3. 健康检查
echo "3️⃣  API 健康检查:"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8000/api/health 2>/dev/null)
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -1)
BODY=$(echo "$HEALTH_RESPONSE" | head -n -1)

if [ "$HTTP_CODE" == "200" ]; then
    echo -e "   ${GREEN}✅${NC} API 响应正常 (HTTP $HTTP_CODE)"
    echo "      响应：$BODY"
else
    echo -e "   ${RED}❌${NC} API 无响应 (HTTP $HTTP_CODE)"
fi
echo ""

# 4. Git 版本
echo "4️⃣  版本信息:"
if [ -d "$PROJECT_DIR/.git" ]; then
    cd "$PROJECT_DIR"
    SHORT_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
    LAST_COMMIT=$(git log -1 --format="%cd" --date=format:"%Y-%m-%d %H:%M" 2>/dev/null || echo "unknown")
    
    echo -e "   ${BLUE}📦${NC} 分支：$BRANCH"
    echo -e "   ${BLUE}📦${NC} 版本：$SHORT_HASH"
    echo -e "   ${BLUE}📦${NC} 提交时间：$LAST_COMMIT"
    
    # 检查是否有未提交更改
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
        echo -e "   ${YELLOW}⚠️${NC} 有未提交的更改"
    else
        echo -e "   ${GREEN}✅${NC} 工作区干净"
    fi
else
    echo -e "   ${YELLOW}⚠️${NC} 非 Git 仓库"
fi
echo ""

# 5. 磁盘空间
echo "5️⃣  磁盘空间:"
DISK_USAGE=$(df -h "$PROJECT_DIR" 2>/dev/null | tail -1 | awk '{print $5}')
echo -e "   使用率：$DISK_USAGE"
if [ "${DISK_USAGE%\%}" -gt 80 ]; then
    echo -e "   ${RED}⚠️${NC} 磁盘空间不足，请清理"
else
    echo -e "   ${GREEN}✅${NC} 磁盘空间正常"
fi
echo ""

# 6. 日志最新内容
echo "6️⃣  最新日志:"
if [ -f "$PROJECT_DIR/server.log" ]; then
    echo "   ────────────────────────────────────────"
    tail -5 "$PROJECT_DIR/server.log" | sed 's/^/   /'
    echo "   ────────────────────────────────────────"
else
    echo -e "   ${YELLOW}⚠️${NC} 日志文件不存在"
fi
echo ""

# 7. 公网访问测试
echo "7️⃣  公网访问测试:"
echo "   测试地址：http://47.103.229.125:8000/api/health"
PUBLIC_RESPONSE=$(curl -s -w "\n%{http_code}" http://47.103.229.125:8000/api/health 2>/dev/null)
PUBLIC_CODE=$(echo "$PUBLIC_RESPONSE" | tail -1)

if [ "$PUBLIC_CODE" == "200" ]; then
    echo -e "   ${GREEN}✅${NC} 公网可访问 (HTTP $PUBLIC_CODE)"
else
    echo -e "   ${RED}❌${NC} 公网无法访问 (HTTP $PUBLIC_CODE)"
    echo -e "   ${YELLOW}提示:${NC} 请检查阿里云安全组是否开放 8000 端口"
fi
echo ""

echo "============================================"
echo ""

exit 0
