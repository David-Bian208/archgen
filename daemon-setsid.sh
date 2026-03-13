#!/bin/bash
# V4.5.1 独立会话守护进程 - 不受 OpenClaw 会话超时影响

LOG_FILE="/home/admin/.openclaw/workspace/behavior_recorder_service/daemon.log"
PID_FILE="/home/admin/.openclaw/workspace/behavior_recorder_service/backend.pid"
WORK_DIR="/home/admin/.openclaw/workspace/behavior_recorder_service"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> $LOG_FILE
}

check_and_restart() {
    # 检查后端进程（使用 PID 文件）
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
    
    # 使用 setsid 创建新会话，完全独立于当前终端
    log "🔄 使用 setsid 重启后端服务..."
    cd $WORK_DIR
    
    # setsid 创建新会话，nohup 忽略挂起信号，disown 解除 shell 绑定
    setsid sh -c '
        cd /home/admin/.openclaw/workspace/behavior_recorder_service
        exec python3 main.py >> server.log 2>&1
    ' &
    NEW_PID=$!
    echo $NEW_PID > $PID_FILE
    log "✅ 后端服务已启动 (PID: $NEW_PID, 独立会话)"
    
    # 立即解除与当前 shell 的绑定
    disown $NEW_PID 2>/dev/null
    
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

# 主循环 - 每 60 秒检查一次
log "=========================================="
log "🚀 独立会话守护进程启动 (抗会话超时)"
log "=========================================="

while true; do
    check_and_restart
    sleep 60  # 每 60 秒检查一次
done
