<template>
  <div class="three-col-workbench">
    <!-- 顶部信息栏 -->
    <div class="workbench-header">
      <span class="workbench-title">Step 3/5 三列分析工作台</span>
      <a-space>
        <a-tag v-if="phase === 'selecting_angle'" color="arcoblue">选择写作角度</a-tag>
        <a-tag v-if="phase === 'streaming'" color="blue">AI 分析中...</a-tag>
        <a-tag v-else-if="phase === 'editing_slots'" color="orange">调整槽位</a-tag>
        <a-tag v-else-if="phase === 'filling'" color="purple">填充内容中...</a-tag>
        <a-tag v-else-if="phase === 'done'" color="green">内容就绪</a-tag>
      </a-space>
    </div>

    <!-- 写作角度选择 -->
    <div v-if="phase === 'selecting_angle'" class="angle-selector">
      <div class="angle-intro">
        <h3>选择写作角度</h3>
        <p>同一个选题可以从不同角度切入，请选择你想要的写作方式：</p>
      </div>

      <!-- 自定义角度入口 -->
      <div class="custom-angle-card">
        <a-space style="width: 100%">
          <IconEdit style="font-size: 16px; color: #165dff" />
          <span style="font-size: 13px; color: #4e5969">没有合适的角度？</span>
          <a-input
            v-model="customAngleText"
            placeholder="输入自定义写作角度..."
            style="flex: 1"
            size="small"
            @press-enter="evaluateCustomAngle"
          />
          <a-button type="primary" size="small" :loading="customAngleLoading" @click="evaluateCustomAngle">
            <template #icon><IconSearch /></template>
            AI评估
          </a-button>
        </a-space>
        <!-- 自定义角度评分 -->
        <div v-if="customAngleResult" class="custom-angle-result">
          <a-row :gutter="8" style="margin-top: 8px">
            <a-col :span="6">
              <div class="mini-score">适合度 {{ customAngleResult.direction_score || 0 }}分</div>
            </a-col>
            <a-col :span="6">
              <div class="mini-score">完整度 {{ customAngleResult.deficiency_score || 0 }}分</div>
            </a-col>
            <a-col :span="6">
              <div class="mini-score">综合 {{ customAngleResult.overall_score || 0 }}分</div>
            </a-col>
            <a-col :span="6" style="text-align: right">
              <a-button size="mini" type="primary" @click="useCustomAngle">选择此角度</a-button>
            </a-col>
          </a-row>
        </div>
      </div>

      <a-spin :loading="angleLoading" class="angle-spin">
        <div class="angle-grid" v-if="availableAngles.length > 0">
          <div
            v-for="(angle, idx) in availableAngles"
            :key="idx"
            class="angle-card"
            :class="{ selected: selectedAngle === angle }"
            @click="selectAngle(angle)"
          >
            <div class="angle-card-header">
              <span class="angle-label">{{ angle.name }}</span>
              <span
                class="angle-coverage"
                :class="coverageClass(angle.coverage)"
              >
                素材覆盖 {{ Math.round((angle.coverage || 0) * 100) }}%
              </span>
            </div>
            <p class="angle-desc">{{ angle.description }}</p>
            <div v-if="angle.gaps && angle.gaps.length > 0" class="angle-gaps">
              <div v-for="(gap, gi) in angle.gaps.slice(0, 3)" :key="gi" class="gap-item">
                ⚠️ {{ gap }}
              </div>
            </div>
            <div v-if="angle.missing_items && angle.missing_items.length > 0" class="angle-missing">
              <div v-for="(mi, miIdx) in angle.missing_items.slice(0, 2)" :key="miIdx" class="missing-item">
                <span class="missing-severity" :class="'sev-' + (mi.severity || 'medium')">{{ mi.severity }}</span>
                <span>{{ mi.name }}</span>
              </div>
            </div>
          </div>
        </div>
        <div v-else-if="!angleLoading" class="angle-empty">
          暂无推荐角度，请
          <a-button type="primary" size="small" @click="refreshAngles">重新加载</a-button>
        </div>
      </a-spin>

      <!-- 换一批 -->
      <div v-if="availableAngles.length > 0" style="text-align: center; margin-top: 16px">
        <a-button size="small" :loading="angleLoading" @click="refreshAngles">
          <IconRefresh style="margin-right: 4px" /> 换一批角度
        </a-button>
      </div>
    </div>

    <!-- 流式推理 + 槽位编辑区 -->
    <StreamSlotsPanel
      v-if="phase === 'streaming' || phase === 'editing_slots'"
      :phase="phase"
      :streaming-text="streamingThinking"
      :stream-done="streamDone"
      :slots="confirmedSlots"
      :slot-relations="slotRelationsData"
      :pre-check-results="preCheckResults"
      :pre-check-running="preCheckRunning"
      :slot-outlines="slotOutlines"
      :session-id="sessionId"
      :topic="topic"
      :selected-direction="selectedDirection"
      :slot-suggestions="slotSuggestions"
      @update-slot="onUpdateSlot"
      @remove-slot="onRemoveSlot"
      @add-slot="onAddSlot"
      @confirm-slots="onConfirmSlots"
      @stop-stream="onStopStream"
      @ask-followup="onAskFollowup('slot_confirmation', '', $event)"
      @run-pre-check="onRunPreCheck"
      @adopt-alternative="onAdoptAlternative"
      @update-outline="(sk, ol) => $emit('update-outline', sk, ol)"
    />

    <!-- 三列表格（填充完成后显示） -->
    <div v-if="phase === 'filling' || phase === 'done'" class="slot-table">
      <a-spin v-if="phase === 'filling'" tip="正在填充三列内容..." class="table-loading" />

      <table class="three-col-table" v-if="confirmedSlots.length">
        <thead>
          <tr>
            <th class="col-status">状态</th>
            <th class="col-slot">槽位</th>
            <th class="col-materials">已有素材</th>
            <th class="col-outline">提纲内容</th>
            <th class="col-actions">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(slot, idx) in confirmedSlots" :key="slot.slot_key" :class="rowClass(slot.slot_key)">
            <!-- 状态灯 -->
            <td class="col-status">
              <span class="status-dot" :class="statusClass(slot.slot_key)"></span>
              <span v-if="isSlotConfirmed(slot.slot_key)" class="status-check">√</span>
            </td>
            <!-- 槽位名 -->
            <td class="col-slot">
              <div class="slot-name">{{ slot.label }}</div>
              <div class="slot-desc" v-if="slot.description">{{ slot.description }}</div>
            </td>
            <!-- 素材列 -->
            <td class="col-materials">
              <div v-if="getSlotMats(slot.slot_key).length === 0 && phase === 'done'" class="empty-hint">
                暂无匹配素材
                <a-button type="text" size="mini" @click="onOpenEdit(slot.slot_key)">手动补充</a-button>
              </div>
              <div v-for="(mat, mi) in getSlotMats(slot.slot_key).slice(0, 6)" :key="mi" class="material-item">
                <span class="source-tag" :class="'src-' + (mat.source_type || 'unknown')">
                  {{ sourceIcon(mat.source_type) }}
                </span>
                <span class="material-file" @click="toggleMaterialPreview(slot.slot_key, mi)">
                  {{ mat.source_name || mat.filename || '未知文件' }}
                </span>
                <div v-if="expandedMaterials[`${slot.slot_key}-${mi}`]" class="material-preview">
                  <pre class="material-full-text">{{ mat.text }}</pre>
                </div>
              </div>
              <div v-if="getSlotMats(slot.slot_key).length > 6" class="more-hint">
                ...共 {{ getSlotMats(slot.slot_key).length }} 条素材
              </div>
            </td>
            <!-- 提纲列 -->
            <td class="col-outline">
              <div v-if="getSlotOutline(slot.slot_key).length === 0 && phase === 'done'" class="empty-hint">
                待生成提纲
              </div>
              <div v-for="(ol, oi) in getSlotOutline(slot.slot_key).slice(0, 3)" :key="oi" class="outline-item">
                <span class="outline-order">{{ ol.order || oi + 1 }}.</span>
                <span class="outline-point">{{ ol.point }}</span>
              </div>
            </td>
            <!-- 操作 -->
            <td class="col-actions">
              <a-space direction="vertical" size="mini">
                <a-button type="text" size="mini" @click="onOpenEdit(slot.slot_key)">✏️ 编辑</a-button>
                <a-button
                  type="text"
                  size="mini"
                  :status="isSlotConfirmed(slot.slot_key) ? 'success' : 'normal'"
                  @click="onConfirmSlot(slot.slot_key)"
                >
                  {{ isSlotConfirmed(slot.slot_key) ? '✅ 已确认' : '确认' }}
                </a-button>
              </a-space>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- 生成全文按钮 -->
      <div v-if="phase === 'done'" class="workbench-footer">
        <a-button type="primary" size="large" :disabled="!allSlotsConfirmed" @click="$emit('proceed-to-article')">
          📝 生成全文
        </a-button>
        <span v-if="!allSlotsConfirmed" class="footer-hint">请先确认所有槽位</span>
      </div>
    </div>

    <!-- 编辑面板（滑出） -->
    <EditPanel
      v-if="showEditPanel && editingSlot"
      :slot-key="editingSlot"
      :slot-label="getSlotLabel(editingSlot)"
      :materials="getSlotMats(editingSlot)"
      :outline="getSlotOutline(editingSlot)"
      :writing-plan="writingPlans[editingSlot] || ''"
      :followup-history="followupHistory"
      @close="closeEditPanel"
      @save-plan="(plan) => saveWritingPlan(editingSlot, plan)"
      @add-material="(text, filename) => addMaterialToSlot(editingSlot, text, filename)"
      @update-outline="(ol) => slotOutlines[editingSlot] = ol"
      @ask-followup="(q) => onAskFollowup('edit_panel', editingSlot, q)"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { IconEdit, IconRefresh, IconSearch } from '@arco-design/web-vue/es/icon'
import StreamSlotsPanel from './StreamSlotsPanel.vue'
import EditPanel from './EditPanel.vue'

const props = defineProps({
  phase: { type: String, default: 'init' },
  streamingThinking: { type: String, default: '' },
  streamDone: { type: Boolean, default: false },
  confirmedSlots: { type: Array, default: () => [] },
  slotMaterials: { type: Object, default: () => ({}) },
  slotOutlines: { type: Object, default: () => ({}) },
  slotConfirmed: { type: Object, default: () => ({}) },
  writingPlans: { type: Object, default: () => ({}) },
  slotRelationsData: { type: Object, default: null },
  editingSlot: { type: String, default: '' },
  showEditPanel: { type: Boolean, default: false },
  followupHistory: { type: Array, default: () => [] },
  allSlotsConfirmed: { type: Boolean, default: false },
  preCheckResults: { type: Object, default: () => ({}) },
  preCheckRunning: { type: Boolean, default: false },
  availableAngles: { type: Array, default: () => [] },
  angleLoading: { type: Boolean, default: false },
  sessionId: { type: String, default: '' },
  topic: { type: String, default: '' },
  selectedDirection: { type: Object, default: null },
  slotSuggestions: { type: Object, default: () => ({}) },
})

const emit = defineEmits([
  'update-slot', 'remove-slot', 'add-slot', 'confirm-slots',
  'stop-stream', 'open-edit-panel', 'close-edit-panel',
  'save-plan', 'add-material', 'update-outline',
  'ask-followup', 'confirm-slot', 'proceed-to-article',
  'run-pre-check', 'adopt-alternative',
  'select-angle', 'refresh-angles', 'evaluate-angle', 'use-custom-angle',
])

const showRelations = ref(true)
const selectedAngle = ref(null)
const customAngleText = ref('')
const customAngleLoading = ref(false)
const customAngleResult = ref(null)
const expandedMaterials = ref({})  // 展开的素材 { `${slot_key}-${index}`: true }

function selectAngle(angle) {
  selectedAngle.value = angle
  emit('select-angle', angle)
}

function refreshAngles() {
  customAngleText.value = ''
  customAngleResult.value = null  
  emit('refresh-angles')
}

async function evaluateCustomAngle() {
  if (!customAngleText.value.trim()) return
  customAngleLoading.value = true
  customAngleResult.value = null
  emit('evaluate-angle', customAngleText.value, (result) => {
    customAngleResult.value = result
    customAngleLoading.value = false
  })
}

function useCustomAngle() {
  if (!customAngleResult.value) return
  const angle = {
    name: customAngleText.value,
    description: customAngleResult.value.direction_analysis || '',
    coverage: (customAngleResult.value.overall_score || 0) / 100,
    gaps: [],
  }
  emit('use-custom-angle', angle)
}

function coverageClass(coverage) {
  const v = coverage || 0
  if (v >= 0.7) return 'cov-high'
  if (v >= 0.4) return 'cov-mid'
  return 'cov-low'
}

function sourceIcon(type) {
  const map = { knowledge_base: '📄', user_input: '✏️', web_search: '🌐', ai_inferred: '🤖' }
  return map[type] || '📎'
}

function truncateText(text, maxLen) {
  if (!text) return ''
  return text.length > maxLen ? text.slice(0, maxLen) + '...' : text
}

function getSlotMats(sk) { return props.slotMaterials[sk] || [] }
function getSlotOutline(sk) { return props.slotOutlines[sk] || [] }
function getSlotLabel(sk) {
  const s = props.confirmedSlots.find(s => s.slot_key === sk)
  return s?.label || sk
}

function statusClass(sk) {
  const mats = getSlotMats(sk)
  const outline = getSlotOutline(sk)
  if (mats.length === 0 && outline.length === 0) return 'empty'
  if (mats.length === 0 || outline.length === 0) return 'partial'
  return 'full'
}

function rowClass(sk) {
  return statusClass(sk)
}

function isSlotConfirmed(sk) {
  return props.slotConfirmed ? props.slotConfirmed[sk] : false
}

function toggleMaterialPreview(sk, idx) {
  const key = `${sk}-${idx}`
  expandedMaterials.value[key] = !expandedMaterials.value[key]
}

function onUpdateSlot(key, updates) { emit('update-slot', key, updates) }
function onRemoveSlot(key) { emit('remove-slot', key) }
function onAddSlot(label, desc) { emit('add-slot', label, desc) }
function onConfirmSlots() { emit('confirm-slots') }
function onStopStream() { emit('stop-stream') }
function onOpenEdit(sk) { emit('open-edit-panel', sk) }
function onConfirmSlot(sk) { emit('confirm-slot', sk) }
function onAskFollowup(context, slotKey, question) { emit('ask-followup', context, slotKey, question) }
function onRunPreCheck(slots) { emit('run-pre-check', slots) }
function onAdoptAlternative(slotKey, alt) { emit('adopt-alternative', slotKey, alt) }
</script>

<style scoped>
.three-col-workbench {
  width: 100%;
  position: relative;
}
.workbench-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border-2);
  background: var(--color-bg-1);
}
.workbench-title { font-size: 16px; font-weight: 600; }

/* ===== 自定义角度入口 ===== */
.custom-angle-card {
  background: linear-gradient(135deg, #f0f5ff 0%, #e6f7ff 100%);
  border: 1px solid #b3d8ff;
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 18px;
}
.custom-angle-result {
  background: #fff;
  border-radius: 8px;
  padding: 8px 10px;
}
.mini-score {
  font-size: 12px;
  color: #4e5969;
  padding: 4px 0;
}

/* ===== 写作角度选择 ===== */
.angle-selector {
  padding: 24px;
}
.angle-spin { display: block; min-height: 120px; }
.angle-intro { margin-bottom: 20px; }
.angle-intro h3 { margin: 0 0 6px; font-size: 18px; }
.angle-intro p { margin: 0; font-size: 14px; color: var(--color-text-3); }
.angle-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.angle-card {
  border: 2px solid var(--color-border-2);
  border-radius: 10px;
  padding: 18px;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--color-bg-1);
}
.angle-card:hover {
  border-color: var(--color-primary-light-3);
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.angle-card.selected {
  border-color: var(--color-primary);
  box-shadow: 0 2px 12px rgba(var(--primary-6), 0.2);
  background: var(--color-primary-light-1);
}
.angle-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.angle-label {
  font-size: 16px;
  font-weight: 600;
}
.angle-coverage {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}
.angle-coverage.cov-high { background: #dcfce7; color: #15803d; }
.angle-coverage.cov-mid { background: #fef3c7; color: #a16207; }
.angle-coverage.cov-low { background: #fee2e2; color: #b91c1c; }
.angle-desc {
  font-size: 13px;
  color: var(--color-text-2);
  line-height: 1.6;
  margin: 0 0 10px;
}
.angle-gaps { margin-bottom: 8px; }
.gap-item {
  font-size: 12px;
  color: #b91c1c;
  padding: 2px 0;
}
.angle-missing { display: flex; flex-direction: column; gap: 4px; }
.missing-item {
  font-size: 12px;
  color: var(--color-text-2);
  display: flex;
  align-items: center;
  gap: 6px;
}
.missing-severity {
  display: inline-block;
  padding: 0 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 500;
}
.sev-high { background: #fee2e2; color: #b91c1c; }
.sev-medium { background: #fef3c7; color: #a16207; }
.sev-low { background: #dcfce7; color: #15803d; }
.angle-empty {
  text-align: center;
  padding: 40px;
  color: var(--color-text-3);
  font-size: 14px;
}

/* ===== 三列表格 ===== */
.slot-table { position: relative; min-height: 200px; }
.table-loading { display: flex; justify-content: center; padding: 60px 0; }
.three-col-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
.three-col-table th, .three-col-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid var(--color-border-2);
  vertical-align: top;
}
.three-col-table th { font-weight: 600; background: var(--color-bg-2); font-size: 13px; }
.col-status { width: 60px; text-align: center; }
.col-slot { width: 15%; min-width: 120px; }
.col-materials { width: 35%; }
.col-outline { width: 35%; }
.col-actions { width: 100px; text-align: center; }
.status-dot {
  display: inline-block;
  width: 10px; height: 10px;
  border-radius: 50%;
}
.status-dot.full { background: #22c55e; }
.status-dot.partial { background: #f59e0b; }
.status-dot.empty { background: #ef4444; }
.status-check { margin-left: 4px; color: #22c55e; font-weight: bold; }
tr.full .col-slot { border-left: 3px solid #22c55e; }
tr.partial .col-slot { border-left: 3px solid #f59e0b; }
tr.empty .col-slot { border-left: 3px solid #ef4444; }
.slot-name { font-weight: 600; }
.slot-desc { font-size: 12px; color: var(--color-text-3); margin-top: 2px; }
.material-item {
  margin-bottom: 6px;
  font-size: 13px;
  line-height: 1.4;
}
.source-tag {
  display: inline-block;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 11px;
  margin-right: 4px;
}
.src-knowledge_base { background: #dbeafe; color: #1d4ed8; }
.src-user_input { background: #dcfce7; color: #15803d; }
.src-web_search { background: #fef3c7; color: #a16207; }
.src-ai_inferred { background: #f3e8ff; color: #7c3aed; }
.material-text { color: var(--color-text-2); }
.material-file {
  color: var(--color-primary, #165dff);
  cursor: pointer;
  font-size: 12px;
  word-break: break-all;
}
.material-file:hover { text-decoration: underline; }
.material-preview {
  margin-top: 6px;
  padding: 8px 10px;
  background: #f9fafb;
  border: 1px solid #e5e6eb;
  border-radius: 6px;
  max-height: 200px;
  overflow-y: auto;
}
.material-full-text {
  margin: 0;
  font-family: inherit;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  color: #4e5969;
}
.more-hint { font-size: 12px; color: var(--color-text-3); margin-top: 4px; }
.outline-item { margin-bottom: 6px; font-size: 13px; }
.outline-order { color: var(--color-primary); margin-right: 4px; font-weight: 500; }
.outline-point { color: var(--color-text-1); }
.empty-hint { font-size: 13px; color: var(--color-text-3); font-style: italic; }
.workbench-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  justify-content: center;
  padding: 20px;
  border-top: 1px solid var(--color-border-2);
}
.footer-hint { font-size: 13px; color: var(--color-text-3); }
</style>