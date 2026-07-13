<template>
  <div class="framework-workbench-v3">
    <!-- 头部：框架名 + 进度 + 操作 -->
    <div class="workbench-header">
      <div class="workbench-header__info">
        <h3 class="workbench-title">
          <icon-layers />
          {{ frameworkName || '分析框架' }}
        </h3>
        <span class="workbench-direction" v-if="direction">
          <icon-compass /> {{ direction }}
        </span>
      </div>
      <div class="workbench-header__actions">
        <a-button @click="$emit('back')">← 返回</a-button>
        <a-button
          type="primary"
          :disabled="!allSlotsCompleted"
          :loading="checkingCoherence"
          @click="runCoherenceCheck"
        >
          🔗 缝合审核
        </a-button>
      </div>
    </div>

    <!-- 进度条 -->
    <div class="workbench-progress" v-if="Object.keys(slotDefs).length">
      <a-progress
        :percent="Number((completedSlots / Math.max(1, totalSlots)) * 100)"
        :status="allSlotsCompleted ? 'success' : 'normal'"
        size="small"
      />
      <span class="progress-text">{{ completedSlots }} / {{ totalSlots }} 槽位已填充</span>
    </div>

    <!-- 加载中 -->
    <div v-if="batchFilling" class="workbench-loading">
      <a-spin dot size="large" />
      <div class="loading-text">正在批量填充所有槽位，请稍候...</div>
      <div class="loading-hint">这可能需要 30-60 秒，取决于槽位数量</div>
    </div>

    <!-- 横向表格：所有槽位 -->
    <div v-if="!batchFilling && Object.keys(slotDefs).length" class="workbench-table">
      <div class="table-header">
        <div class="col-status">状态</div>
        <div class="col-slot">槽位</div>
        <div class="col-content">已有内容</div>
        <div class="col-gaps">缺口</div>
        <div class="col-actions">操作</div>
      </div>
      <div class="table-body">
        <div
          v-for="(slotDef, slotKey) in slotDefs"
          :key="slotKey"
          class="table-row"
          :class="{ 'row--confirmed': slotConfirmed[slotKey] }"
        >
          <!-- 状态灯 -->
          <div class="col-status">
            <span class="status-dot" :class="getSlotStatus(slotKey).class" :title="getSlotStatus(slotKey).text"></span>
            <span class="level-badge" v-if="slotResults[slotKey]?.level">{{ slotResults[slotKey].level }}</span>
          </div>

          <!-- 槽位名称 -->
          <div class="col-slot">
            <div class="slot-label">{{ slotDef.label || slotKey }}</div>
            <div class="slot-keywords" v-if="slotDef.keywords?.length">
              <a-tag v-for="(kw, i) in slotDef.keywords.slice(0, 3)" :key="i" size="mini" color="arcoblue">{{ kw }}</a-tag>
            </div>
          </div>

          <!-- 已有内容 -->
          <div class="col-content">
            <!-- 来源标签 -->
            <div class="source-tags" v-if="getSources(slotKey).length">
              <span
                v-for="(src, i) in getSources(slotKey).slice(0, 3)"
                :key="i"
                class="source-tag"
                :title="src.name"
              >
                {{ src.tag }}
              </span>
              <span v-if="getSources(slotKey).length > 3" class="source-more">
                +{{ getSources(slotKey).length - 3 }}
              </span>
            </div>
            <!-- 内容要点（前2条） -->
            <div class="content-points" v-if="getPoints(slotKey).length">
              <div v-for="(p, i) in getPoints(slotKey).slice(0, 2)" :key="i" class="content-point">
                <span class="point-num">{{ i + 1 }}.</span>
                <span class="point-text">{{ p }}</span>
              </div>
            </div>
            <!-- 空状态 -->
            <div v-if="!getSources(slotKey).length && !getPoints(slotKey).length" class="content-empty">
              <icon-file />
              <span>暂无内容</span>
            </div>
          </div>

          <!-- 缺口 -->
          <div class="col-gaps">
            <div v-if="getGaps(slotKey).length" class="gap-tags">
              <a-tag
                v-for="(g, i) in getGaps(slotKey).slice(0, 3)"
                :key="i"
                color="orangered"
                size="small"
              >
                {{ g }}
              </a-tag>
              <span v-if="getGaps(slotKey).length > 3" class="gap-more">
                +{{ getGaps(slotKey).length - 3 }}
              </span>
            </div>
            <a-tag v-else color="green" size="small">✅ 完整</a-tag>
          </div>

          <!-- 操作按钮 -->
          <div class="col-actions">
            <a-space direction="vertical" size="small">
              <a-button
                size="small"
                type="outline"
                :loading="slotFillingKeys.has(slotKey)"
                @click="openEditPanel(slotKey)"
              >
                ✏️ 编辑
              </a-button>
              <a-button
                v-if="!slotConfirmed[slotKey]"
                size="small"
                status="success"
                @click="confirmSlot(slotKey)"
              >
                ✓ 确认
              </a-button>
              <a-button
                v-else
                size="small"
                disabled
              >
                ✓ 已确认
              </a-button>
            </a-space>
          </div>
        </div>
      </div>
    </div>

    <!-- 空态：无槽位定义 -->
    <div v-if="!batchFilling && !Object.keys(slotDefs).length" class="workbench-empty">
      <a-empty description="未找到框架槽位定义，请返回重新选择框架" />
    </div>

    <!-- 底部操作区 -->
    <div class="workbench-footer" v-if="Object.keys(slotDefs).length">
      <div class="workbench-footer__left">
        <a-tag v-if="allSlotsCompleted" color="green">✓ 全部槽位已填充</a-tag>
        <a-tag v-else color="orange">{{ totalSlots - completedSlots }} 个槽位待填充</a-tag>
        <a-tag v-if="coherenceResult" :color="coherenceResult.ready_for_next ? 'green' : 'red'">
          {{ coherenceResult.ready_for_next ? '✓ 审核通过' : '⚠ 有衔接问题' }}
        </a-tag>
      </div>
      <div class="workbench-footer__right">
        <a-button
          type="primary"
          :disabled="!coherenceResult || !coherenceResult.ready_for_next"
          @click="$emit('proceed-structures')"
        >
          ⏭ 生成提纲
        </a-button>
      </div>
    </div>

    <!-- 缝合审核结果 -->
    <div v-if="coherenceResult" class="workbench-coherence">
      <a-divider>缝合审核结果</a-divider>
      <a-alert
        :type="coherenceResult.ready_for_next ? 'success' : 'warning'"
        style="margin-bottom: 12px;"
      >
        {{ coherenceResult.overall_comment || (coherenceResult.ready_for_next ? '各槽位衔接良好，可以进入下一步' : '存在衔接问题，建议修正后再生成提纲') }}
      </a-alert>
      <div v-if="coherenceResult.transition_issues?.length" class="coherence-issues">
        <div v-for="(issue, i) in coherenceResult.transition_issues" :key="i" class="coherence-issue">
          <a-tag :color="issue.severity === 'major' ? 'red' : issue.severity === 'moderate' ? 'orange' : 'blue'" size="small">
            {{ issue.severity }}
          </a-tag>
          <span class="coherence-issue__slots">{{ issue.from_slot }} → {{ issue.to_slot }}</span>
          <span class="coherence-issue__desc">{{ issue.issue }}</span>
          <span class="coherence-issue__suggestion">💡 {{ issue.suggestion }}</span>
        </div>
      </div>
    </div>

    <!-- ================ 右侧滑编辑面板 ================ -->
    <div
      class="edit-panel-overlay"
      v-if="editPanelVisible"
      @click="closeEditPanel"
    ></div>
    <div class="edit-panel" :class="{ 'edit-panel--open': editPanelVisible }">
      <div class="panel-header">
        <h4>编辑槽位：{{ currentSlotLabel }}</h4>
        <a-button type="text" @click="closeEditPanel">✕</a-button>
      </div>

      <div class="panel-body">
        <!-- 已有内容预览 -->
        <div class="panel-section" v-if="getPoints(currentSlotKey).length">
          <div class="section-title">📄 当前内容</div>
          <div class="current-content">
            <div v-for="(p, i) in getPoints(currentSlotKey)" :key="i" class="content-item">
              <span class="item-num">{{ i + 1 }}.</span>
              <span class="item-text">{{ p }}</span>
            </div>
          </div>
        </div>

        <!-- 补充输入 -->
        <div class="panel-section">
          <div class="section-title">💬 补充素材</div>
          <a-textarea
            v-model="editSuppInput"
            placeholder="告诉我你想补充什么...&#10;例如：目标用户画像、行业规模数据、竞品案例"
            :auto-size="{ minRows: 4, maxRows: 8 }"
          />
          <div class="upload-bar">
            <a-button size="small" @click="handleUploadClick('file')">📎 上传文件</a-button>
            <a-button size="small" @click="handleUploadClick('image')">🖼 上传图片</a-button>
            <input
              ref="fileInput"
              type="file"
              style="display: none"
              @change="onFileSelected"
              accept=".txt,.md,.pdf,.doc,.docx,.png,.jpg,.jpeg"
            />
          </div>
        </div>

        <!-- 缺口提示 -->
        <div class="panel-section" v-if="getGaps(currentSlotKey).length">
          <div class="section-title">⚠️ 建议补充</div>
          <div class="gap-suggestions">
            <a-tag
              v-for="(g, i) in getGaps(currentSlotKey)"
              :key="i"
              color="orangered"
              size="small"
              @click="editSuppInput += ` ${g}`"
              style="cursor: pointer"
            >
              {{ g }}
            </a-tag>
          </div>
        </div>
      </div>

      <div class="panel-footer">
        <a-space>
          <a-button @click="closeEditPanel">取消</a-button>
          <a-button @click="handleSkip">跳过</a-button>
          <a-button
            type="primary"
            :loading="slotFillingKeys.has(currentSlotKey)"
            @click="handleFill"
          >
            <template #icon><icon-robot /></template>
            AI 分析
          </a-button>
        </a-space>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { IconLayers, IconCompass, IconFile, IconRobot } from '@arco-design/web-vue/es/icon'
import { useStep3Workbench } from '../../composables/useStep3_Workbench'

const props = defineProps({
  frameworkName: { type: String, default: '' },
  direction: { type: String, default: '' },
  slotDefs: { type: Object, default: () => ({}) },
  slotGapMatches: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['back', 'proceed-structures'])

const {
  slotResults,
  slotFillingKeys,
  completedSlots,
  totalSlots,
  allSlotsCompleted,
  fillSlot,
  initSlots,
  checkingCoherence,
  coherenceResult,
  runCoherenceCheck,
  maxDegradation,
  degradationCounts,
  slotConfirmed,
  confirmSlot,
  skipSlot,
  uploadSource,
  batchFillSlots,
  batchFilling,
} = useStep3Workbench()

// 初始化
initSlots(props.slotDefs)

// 进入页面后自动批量填充
onMounted(() => {
  if (Object.keys(props.slotDefs).length) {
    // 延迟一点，让页面先渲染出来
    setTimeout(() => {
      batchFillSlots()
    }, 500)
  }
})

// ================ 右侧滑面板 ================
const editPanelVisible = ref(false)
const currentSlotKey = ref('')
const editSuppInput = ref('')
const fileInput = ref(null)

const currentSlotLabel = computed(() => {
  const def = props.slotDefs[currentSlotKey.value]
  return def?.label || currentSlotKey.value
})

function openEditPanel(slotKey) {
  currentSlotKey.value = slotKey
  editSuppInput.value = slotResults[slotKey]?.supplementInput || ''
  editPanelVisible.value = true
}

function closeEditPanel() {
  editPanelVisible.value = false
  currentSlotKey.value = ''
  editSuppInput.value = ''
}

function handleFill() {
  fillSlot(currentSlotKey.value, editSuppInput.value, [])
  // 填充完成后不自动关闭，让用户看到结果
}

function handleSkip() {
  skipSlot(currentSlotKey.value)
  closeEditPanel()
}

// 文件上传
function handleUploadClick(type) {
  fileInput.value?.click()
}

function onFileSelected(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (evt) => {
    const text = evt.target?.result || ''
    const fileType = file.type.startsWith('image/') ? 'image' : 'text'
    uploadSource(currentSlotKey.value, text, file.name, fileType)
  }
  reader.readAsText(file)
  e.target.value = ''
}

// ================ 辅助函数 ================
function getSlotStatus(slotKey) {
  if (slotConfirmed[slotKey]) {
    return { class: 'status--confirmed', text: '已确认' }
  }
  const result = slotResults[slotKey]
  if (!result) {
    return { class: 'status--empty', text: '未填充' }
  }
  const gaps = result.gaps || []
  if (gaps.length === 0 && (result.points || []).length > 0) {
    return { class: 'status--full', text: '完整' }
  }
  if ((result.points || []).length > 0) {
    return { class: 'status--partial', text: '部分填充' }
  }
  return { class: 'status--empty', text: '未填充' }
}

function getSources(slotKey) {
  const r = slotResults[slotKey]
  if (!r) return []
  // 兼容 enriched_sources 和 sources 两种格式
  if (r.enriched_sources?.length) return r.enriched_sources
  if (r.sources?.length && typeof r.sources[0] === 'object') return r.sources
  if (r.sources?.length && typeof r.sources[0] === 'string') {
    return r.sources.map(s => ({ tag: s, name: s }))
  }
  return []
}

function getPoints(slotKey) {
  const r = slotResults[slotKey]
  return r?.points || []
}

function getGaps(slotKey) {
  const r = slotResults[slotKey]
  return r?.gaps || []
}
</script>

<style scoped>
.framework-workbench-v3 {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

/* ========== 头部 ========== */
.workbench-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--color-border-2);
  flex-wrap: wrap;
  gap: 12px;
}
.workbench-header__info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.workbench-title {
  font-size: 18px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
}
.workbench-direction {
  font-size: 13px;
  color: var(--color-text-3);
  display: flex;
  align-items: center;
  gap: 4px;
}
.workbench-header__actions {
  display: flex;
  gap: 8px;
}

/* ========== 进度条 ========== */
.workbench-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}
.progress-text {
  font-size: 13px;
  color: var(--color-text-2);
  white-space: nowrap;
}

/* ========== 加载中 ========== */
.workbench-loading {
  text-align: center;
  padding: 60px 20px;
}
.loading-text {
  margin-top: 16px;
  font-size: 15px;
  color: var(--color-text-1);
}
.loading-hint {
  margin-top: 8px;
  font-size: 13px;
  color: var(--color-text-3);
}

/* ========== 横向表格 ========== */
.workbench-table {
  border: 1px solid var(--color-border-2);
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 20px;
}

.table-header {
  display: grid;
  grid-template-columns: 80px 180px 1fr 160px 100px;
  gap: 0;
  background: var(--color-fill-2);
  padding: 12px 16px;
  font-weight: 600;
  font-size: 13px;
  color: var(--color-text-2);
  border-bottom: 1px solid var(--color-border-2);
}

.table-body {
  max-height: 550px;
  overflow-y: auto;
}

.table-row {
  display: grid;
  grid-template-columns: 80px 180px 1fr 160px 100px;
  gap: 0;
  padding: 16px;
  border-bottom: 1px solid var(--color-border-1);
  align-items: start;
  transition: background 0.2s;
}
.table-row:hover {
  background: var(--color-fill-1);
}
.table-row.row--confirmed {
  background: #f0fff4;
}

/* 列通用 */
.col-status, .col-slot, .col-content, .col-gaps, .col-actions {
  padding: 0 8px;
}

/* 状态列 */
.col-status {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}
.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status--full { background: #00b42a; }
.status--partial { background: #ff7d00; }
.status--empty { background: #c9cdd4; }
.status--confirmed { background: #14c9c9; }
.level-badge {
  font-size: 11px;
  color: var(--color-text-3);
}

/* 槽位列 */
.col-slot {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.slot-label {
  font-weight: 600;
  font-size: 14px;
  color: var(--color-text-1);
  line-height: 1.4;
}
.slot-keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

/* 内容列 */
.col-content {
  min-width: 0;
}
.source-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 8px;
}
.source-tag {
  background: #e8f3ff;
  color: #165dff;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.source-more {
  font-size: 11px;
  color: var(--color-text-3);
}
.content-points {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.content-point {
  display: flex;
  gap: 4px;
  font-size: 13px;
  line-height: 1.5;
}
.point-num {
  color: var(--color-text-3);
  font-weight: 600;
  flex-shrink: 0;
}
.point-text {
  color: var(--color-text-2);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.content-empty {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--color-text-4);
  font-size: 13px;
}

/* 缺口列 */
.col-gaps {
  min-width: 0;
}
.gap-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.gap-more {
  font-size: 11px;
  color: var(--color-text-3);
}

/* 操作列 */
.col-actions {
  display: flex;
  justify-content: flex-start;
}

/* ========== 底部 ========== */
.workbench-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: var(--color-bg-1);
  border: 1px solid var(--color-border-2);
  border-radius: 8px;
}
.workbench-footer__left {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* ========== 缝合审核结果 ========== */
.workbench-coherence {
  margin-top: 20px;
  padding: 16px;
  background: var(--color-bg-1);
  border: 1px solid var(--color-border-2);
  border-radius: 8px;
}
.coherence-issues {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.coherence-issue {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 10px;
  background: var(--color-bg-2);
  border-radius: 6px;
  font-size: 13px;
}
.coherence-issue__slots {
  font-weight: 600;
  color: var(--color-text-2);
}
.coherence-issue__desc {
  color: var(--color-text-1);
}
.coherence-issue__suggestion {
  color: var(--color-text-3);
  font-size: 12px;
  width: 100%;
  margin-top: 2px;
}

/* ========== 空态 ========== */
.workbench-empty {
  text-align: center;
  padding: 60px 0;
}

/* ========== 右侧滑面板 ========== */
.edit-panel-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3);
  z-index: 998;
}
.edit-panel {
  position: fixed;
  top: 0;
  right: -500px;
  width: 480px;
  height: 100vh;
  background: white;
  box-shadow: -4px 0 20px rgba(0, 0, 0, 0.15);
  z-index: 999;
  transition: right 0.3s ease;
  display: flex;
  flex-direction: column;
}
.edit-panel--open {
  right: 0;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border-2);
  flex-shrink: 0;
}
.panel-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}
.panel-section {
  margin-bottom: 24px;
}
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-1);
  margin-bottom: 12px;
}
.current-content {
  background: var(--color-fill-1);
  border-radius: 6px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.content-item {
  display: flex;
  gap: 6px;
  font-size: 13px;
  line-height: 1.5;
}
.item-num {
  color: var(--color-text-3);
  font-weight: 600;
  flex-shrink: 0;
}
.item-text {
  color: var(--color-text-2);
}
.upload-bar {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}
.gap-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.panel-footer {
  padding: 16px 20px;
  border-top: 1px solid var(--color-border-2);
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
}

/* ========== 响应式 ========== */
@media (max-width: 1024px) {
  .table-header, .table-row {
    grid-template-columns: 60px 140px 1fr 120px 90px;
  }
}
@media (max-width: 768px) {
  .workbench-table {
    overflow-x: auto;
  }
  .table-header, .table-row {
    min-width: 700px;
  }
  .edit-panel {
    width: 100%;
    right: -100%;
  }
}
</style>
