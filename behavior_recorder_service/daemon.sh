#!/bin/bash
# V4.5.1 守护进程脚本 - 确保服务持续运行

LOG_FILE="/home/admin/.openclaw/workspace/behavior_recorder_service/daemon.log"
PID_FILE="/home/admin/.openclaw/workspace/behavior_recorder_service/backend.pid"
WORK_DIR="/home/admin/.openclaw/workspace/behavior_recorder_service"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> $LOG_FILE
}

check_and_restart() {
    # 检查后端进程
    if [ -f $PID_FILE ]; then
        PID=$(cat $PID_FILE)
        if ps -p $PID > /dev/null 2>&1; then
            log "✅ 后端进程运行中 (PID: $PID)"
            return 0
        else
            log "❌ 后端进程已停止 (PID: $PID)"
            rm -f $PID_FILE
        fi
    else
        log "⚠️  未找到 PID 文件"
    fi
    
    # 重启后端
    log "🔄 重启后端服务..."
    cd $WORK_DIR
    nohup python3 main.py > server.log 2>&1 &
    NEW_PID=$!
    echo $NEW_PID > $PID_FILE
    log "✅ 后端服务已启动 (PID: $NEW_PID)"
    
    # 等待启动
    sleep 5
    
    # 验证启动
    if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
        log "✅ 后端服务验证成功"
        return 0
    else
        log "❌ 后端服务启动失败"
        return 1
    fi
}

# 主循环
log "=========================================="
log "🚀 守护进程启动"
log "=========================================="

while true; do
    check_and_restart
    sleep 30  # 每 30 秒检查一次
done
