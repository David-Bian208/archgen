<template>
  <div class="thinking-log-panel">
    <!-- 悬浮触发按钮 -->
    <div class="panel-trigger" @click="togglePanel">
      <span class="trigger-icon">🧠</span>
      <span class="trigger-label">AI思考日志</span>
      <span v-if="runningCount > 0" class="trigger-badge">{{ runningCount }}</span>
    </div>

    <!-- 面板主体 -->
    <transition name="slide-up">
      <div v-if="visible" class="panel-body">
        <div class="panel-header">
          <h3>AI 思考日志</h3>
          <div class="panel-header-actions">
            <span class="log-count">共 {{ allLogs.length }} 条</span>
            <button class="btn-clear" @click="clearLogs">清空</button>
            <button class="btn-close" @click="visible = false">✕</button>
          </div>
        </div>

        <div class="panel-scroll">
          <!-- 空状态 -->
          <div v-if="allLogs.length === 0" class="empty-state">
            <span>🧠</span>
            <p>暂无AI思考记录</p>
            <p class="hint">进行槽位分析、整合生成等操作后，这里会显示AI的完整思考过程</p>
          </div>

          <!-- 日志列表 - 按阶段分组 -->
          <div
            v-for="group in phasedLogs"
            :key="group.phase"
            class="phase-group"
          >
            <div class="phase-header" @click="togglePhase(group.phase)">
              <span class="phase-arrow" :class="{ expanded: !collapsedPhases.has(group.phase) }">▾</span>
              <span class="phase-label">{{ phaseIcon(group.phase) }} {{ group.phase }}</span>
              <span class="phase-count">{{ group.logs.length }} 条</span>
            </div>
            <div v-if="!collapsedPhases.has(group.phase)">
              <div
                v-for="log in group.logs"
                :key="log.log_id || log.call_id"
                class="log-item"
                :class="{ running: log.status === 'running', failed: log.status === 'failed' }"
              >
            <div class="log-item-header" @click="toggleExpand(log)">
              <div class="log-status-icon">
                <span v-if="log.status === 'running'" class="spinner"></span>
                <span v-else-if="log.status === 'failed'" class="icon-fail">✕</span>
                <span v-else class="icon-ok">✓</span>
              </div>
              <div class="log-item-info">
                <div class="log-name">{{ log.call_name }}</div>
                <div class="log-meta">
                  <span class="log-model">{{ log.model }}</span>
                  <span class="log-duration" v-if="log.duration">{{ formatDuration(log.duration * 1000) }}</span>
                  <span class="log-status-tag" :class="log.status">{{ statusLabel(log.status) }}</span>
                </div>
              </div>
              <span class="expand-arrow" :class="{ expanded: expandedLogs.has(log.log_id || log.call_id) }">▾</span>
            </div>

            <!-- 展开详情 -->
            <transition name="expand">
              <div v-if="expandedLogs.has(log.log_id || log.call_id)" class="log-item-detail">
                <!-- 错误信息 -->
                <div v-if="log.error" class="detail-section error-section">
                  <h5>错误</h5>
                  <pre>{{ log.error }}</pre>
                </div>

                <!-- 思考链 -->
                <div v-if="log.thinking_chain && log.thinking_chain.length > 0" class="detail-section">
                  <h5>🧠 思考过程</h5>
                  <div class="thinking-steps">
                    <div
                      v-for="step in log.thinking_chain"
                      :key="step.step"
                      class="thinking-step"
                    >
                      <div class="step-number">{{ step.step }}</div>
                      <div class="step-content">
                        <div class="step-action">{{ step.step_name || step.action || '未知步骤' }}</div>
                        <div v-if="step.input" class="step-input">
                          <span class="label">输入：</span>{{ step.input }}
                        </div>
                        <div v-if="step.reasoning" class="step-reason">
                          <span class="label">推理：</span>{{ step.reasoning }}
                        </div>
                        <div v-else-if="step.reason" class="step-reason">
                          <span class="label">原因：</span>{{ step.reason }}
                        </div>
                        <div v-if="step.output !== undefined" class="step-result">
                          <span class="label">结果：</span>
                          <template v-if="typeof step.output === 'object'">
                            <pre class="step-output-json">{{ JSON.stringify(step.output, null, 2) }}</pre>
                          </template>
                          <template v-else>{{ step.output }}</template>
                        </div>
                        <div v-else-if="step.result" class="step-result">
                          <span class="label">结果：</span>{{ step.result }}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 最终输出 -->
                <div v-if="log.result || log.final_output" class="detail-section">
                  <h5>📤 最终输出</h5>
                  <pre class="final-output">{{ log.result || log.final_output }}</pre>
                </div>

                <!-- Prompt（调试用，默认折叠） -->
                <details v-if="log.full_prompt" class="detail-section prompt-details">
                  <summary><h5>📥 完整 Prompt</h5></summary>
                  <pre class="prompt-text">{{ log.full_prompt }}</pre>
                </details>

                <!-- 元信息 -->
                <div class="detail-meta">
                  <span>模型：{{ log.model }}</span>
                  <span v-if="log.temperature !== undefined">温度：{{ log.temperature }}</span>
                  <span v-if="log.duration">耗时：{{ formatDuration(log.duration * 1000) }}</span>
                  <span>ID：{{ log.call_id }}</span>
                </div>
              </div>
            </transition>
              </div> <!-- end phase-group log-item -->
            </div> <!-- end phase-group inner -->
          </div> <!-- end phase-group -->
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { getThinkingLogs } from '../../utils/api.js'
import { useSession } from '../../composables/useSession.js'

// 使用模块级单例，确保拿到的是同一个 sessionId
const { sessionId } = useSession()

const visible = ref(false)
const allLogs = ref([])
const expandedLogs = ref(new Set())
const collapsedPhases = ref(new Set())
const pollingTimer = ref(null)

// 阶段顺序（按业务流程）
const phaseOrder = ['选题', '补充', '角度推荐', '槽位生成', '其他']

// 按业务归属归并分组
const phasedLogs = computed(() => {
  const groups = new Map()
  for (const log of allLogs.value) {
    // 优先用后端设置的 phase，call_name 只作为缺失时的 fallback
    let phaseKey = log.phase || '其他'
    
    // 如果 phase 是 '其他' 或缺失，再通过 call_name 判断归属
    if (phaseKey === '其他') {
      const name = log.call_name || ''
      if (name === '方向检测' || name === 'MCP题材推荐' || name === '方向分析') {
        phaseKey = '选题'
      } else if (name.startsWith('角度推荐')) {
        phaseKey = '角度推荐'
      } else if (name === 'AI推断补充' || name === '完整度评估') {
        phaseKey = '补充'
      } else if (name === '槽位生成') {
        phaseKey = '槽位生成'
      }
    }
    
    // 不在业务阶段列表里的，统一归到「其他」
    if (!phaseOrder.includes(phaseKey)) {
      phaseKey = '其他'
    }
    
    if (!groups.has(phaseKey)) groups.set(phaseKey, [])
    groups.get(phaseKey).push(log)
  }
  // 按阶段顺序排列，组内按时间排序
  return phaseOrder
    .filter(p => groups.has(p))
    .map(p => ({ phase: p, logs: groups.get(p).sort((a, b) => (a.start_time || 0) - (b.start_time || 0)) }))
})

function phaseIcon(phase) {
  const icons = { '选题': '📌', '补充': '📝', '角度推荐': '🎯', '槽位生成': '📋', '其他': '📎' }
  return icons[phase] || '📎'
}

function togglePhase(phase) {
  const set = new Set(collapsedPhases.value)
  if (set.has(phase)) {
    set.delete(phase)
  } else {
    set.add(phase)
  }
  collapsedPhases.value = set
}

const runningCount = computed(() => allLogs.value.filter(l => l.status === 'running').length)

function statusLabel(status) {
  return status === 'running' ? '运行中' : status === 'failed' ? '失败' : '成功'
}

function togglePanel() {
  visible.value = !visible.value
}

function toggleExpand(log) {
  const key = log.log_id || log.call_id
  const set = new Set(expandedLogs.value)
  if (set.has(key)) {
    set.delete(key)
  } else {
    set.add(key)
  }
  expandedLogs.value = set
}

function clearLogs() {
  allLogs.value = []
  expandedLogs.value = new Set()
  collapsedPhases.value = new Set()
}

function formatDuration(val) {
  if (!val && val !== 0) return ''
  const ms = Math.round(val)
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`
}

async function pollLogs() {
  if (!sessionId.value) return
  try {
    // 增量拉取：只拉上次之后的
    const lastTime = allLogs.value.length > 0
      ? Math.max(...allLogs.value.map(l => l.start_time || 0))
      : 0
    const res = await getThinkingLogs(sessionId.value, lastTime)
    const data = res.data?.data || res.data || {}
    const newLogs = data.logs || []

    if (newLogs.length > 0) {
      // 合并：同call_id的用最新覆盖
      const existingMap = new Map(allLogs.value.map(l => [l.call_id || l.log_id, l]))
      for (const log of newLogs) {
        const key = log.call_id || log.log_id
        existingMap.set(key, log)
      }
      allLogs.value = [...existingMap.values()].sort((a, b) => (a.start_time || 0) - (b.start_time || 0))
    }
  } catch (e) {
    // 静默失败，避免刷屏
  }
}

onMounted(() => {
  // 初始加载
  pollLogs()
  // 每2秒轮询
  pollingTimer.value = setInterval(pollLogs, 2000)
})

onUnmounted(() => {
  if (pollingTimer.value) {
    clearInterval(pollingTimer.value)
  }
})

// 监听sessionId变化
watch(sessionId, () => {
  allLogs.value = []
  expandedLogs.value = new Set()
  collapsedPhases.value = new Set()
  pollLogs()
})
</script>

<style scoped>
.thinking-log-panel {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 9999;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* 触发按钮 */
.panel-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: #1a1a2e;
  color: #e0e0e0;
  border-radius: 20px;
  cursor: pointer;
  box-shadow: 0 2px 12px rgba(0,0,0,0.3);
  transition: transform 0.15s, box-shadow 0.15s;
  user-select: none;
}
.panel-trigger:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.4);
}
.trigger-icon { font-size: 18px; }
.trigger-label { font-size: 13px; font-weight: 500; }
.trigger-badge {
  background: #ff6b35;
  color: #fff;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
}

/* 面板主体 */
.panel-body {
  position: fixed;
  top: 40px;
  left: 40px;
  right: 40px;
  bottom: 80px;
  width: auto;
  max-height: none;
  background: #1a1a2e;
  border-radius: 12px;
  box-shadow: 0 4px 32px rgba(0,0,0,0.5);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #2a2a4a;
}
.panel-header h3 {
  margin: 0;
  font-size: 15px;
  color: #e0e0e0;
}
.panel-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.log-count {
  font-size: 11px;
  color: #888;
}
.btn-clear, .btn-close {
  background: none;
  border: 1px solid #444;
  color: #aaa;
  padding: 3px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
}
.btn-clear:hover, .btn-close:hover {
  background: #333;
  color: #fff;
}

.panel-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: #888;
}
.empty-state span { font-size: 36px; }
.empty-state p { margin: 8px 0 0; font-size: 13px; }
.empty-state .hint { font-size: 11px; color: #666; }

/* 阶段分组 */
.phase-group {
  margin: 0;
}
.phase-group:not(:last-child) {
  border-bottom: 1px solid #333;
}
.phase-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  cursor: pointer;
  background: #1e1e34;
  user-select: none;
}
.phase-header:hover { background: #24244a; }
.phase-arrow {
  font-size: 12px;
  color: #888;
  transition: transform 0.2s;
  flex-shrink: 0;
}
.phase-arrow.expanded { transform: rotate(-90deg); }
.phase-label {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
  color: #ccc;
}
.phase-count {
  font-size: 11px;
  color: #666;
}

/* 日志项 */
.log-item {
  border-bottom: 1px solid #2a2a4a;
}
.log-item.running { background: rgba(255, 107, 53, 0.05); }
.log-item.failed { background: rgba(255, 70, 70, 0.05); }

.log-item-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  cursor: pointer;
  transition: background 0.1s;
}
.log-item-header:hover { background: rgba(255,255,255,0.03); }

.log-status-icon {
  width: 18px;
  flex-shrink: 0;
  text-align: center;
}
.icon-ok { color: #4caf50; font-size: 12px; }
.icon-fail { color: #ff4646; font-size: 12px; }
.spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid #ff6b35;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.log-item-info {
  flex: 1;
  min-width: 0;
}
.log-name {
  font-size: 13px;
  color: #e0e0e0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.log-meta {
  display: flex;
  gap: 8px;
  margin-top: 2px;
  font-size: 11px;
  color: #888;
}
.log-status-tag.running { color: #ff6b35; }
.log-status-tag.failed { color: #ff4646; }
.log-status-tag.success { color: #4caf50; }

.expand-arrow {
  flex-shrink: 0;
  color: #666;
  font-size: 14px;
  transition: transform 0.2s;
}
.expand-arrow.expanded { transform: rotate(180deg); }

/* 详情 */
.log-item-detail {
  padding: 0 16px 14px;
  border-top: 1px solid #2a2a4a;
}
.detail-section {
  margin-top: 12px;
}
.detail-section h5 {
  margin: 0 0 6px;
  font-size: 12px;
  color: #aaa;
  font-weight: 500;
}
.detail-section pre {
  margin: 0;
  padding: 10px;
  background: #111;
  border-radius: 6px;
  font-size: 12px;
  color: #ccc;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 200px;
  overflow-y: auto;
  line-height: 1.5;
}
.error-section { border-left: 2px solid #ff4646; }
.error-section pre { color: #ff6b6b; }

/* 思考步骤 */
.thinking-steps {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.thinking-step {
  display: flex;
  gap: 10px;
  padding: 8px;
  background: #111;
  border-radius: 6px;
}
.step-number {
  width: 22px;
  height: 22px;
  background: #333;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: #ccc;
  flex-shrink: 0;
}
.step-content {
  flex: 1;
  font-size: 12px;
  color: #bbb;
  line-height: 1.5;
}
.step-action { color: #e0e0e0; font-weight: 500; margin-bottom: 6px; }
.step-input, .step-reason, .step-result { margin-top: 4px; line-height: 1.6; }
.step-reason {
  white-space: pre-wrap;
  word-break: break-word;
  color: #bbb;
}
.step-input { white-space: pre-wrap; color: #aaa; }
.step-input .label { color: #666; font-size: 11px; }
.label { color: #888; font-size: 11px; }
.step-output-json {
  margin: 4px 0 0;
  padding: 6px 8px;
  background: #0a0a1a;
  border-radius: 4px;
  font-size: 11px;
  color: #aaa;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 120px;
  overflow-y: auto;
  line-height: 1.4;
}

.final-output { max-height: 300px !important; }

.prompt-details summary { cursor: pointer; }
.prompt-details summary h5 { display: inline; }
.prompt-text {
  max-height: 150px;
  overflow-y: auto;
  font-size: 11px !important;
  color: #777 !important;
}

.detail-meta {
  display: flex;
  gap: 12px;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid #2a2a4a;
  font-size: 11px;
  color: #666;
}

/* 过渡 */
.slide-up-enter-active, .slide-up-leave-active {
  transition: all 0.2s ease;
}
.slide-up-enter-from, .slide-up-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
.expand-enter-active, .expand-leave-active {
  transition: all 0.15s ease;
  overflow: hidden;
}
.expand-enter-from, .expand-leave-to {
  opacity: 0;
  max-height: 0;
}
</style>
