<template>
  <div class="stream-slots-panel">
    <!-- 流式推理文本区 -->
    <div class="stream-thinking">
      <div class="stream-header">
        <span class="stream-icon">{{ streamDone ? '✅' : '💡' }}</span>
        <span>{{ streamDone ? 'AI 分析完成' : 'AI 正在分析...' }}</span>
        <a-button v-if="!streamDone" type="text" size="mini" status="warning" @click="$emit('stop-stream')">
          停止生成
        </a-button>
      </div>
      <div class="stream-content">
        <pre class="stream-text">{{ streamingText || '等待 AI 响应...' }}</pre>
      </div>
    </div>

    <!-- 槽位间关系图谱（可折叠） -->
    <div v-if="slotRelations && slotRelations.relations?.length" class="relations-graph">
      <div class="relations-header" @click="showRelations = !showRelations">
        <span>🔗 槽位关系图</span>
        <span class="collapse-icon">{{ showRelations ? '▾' : '▸' }}</span>
      </div>
      <div v-if="showRelations" class="relations-body">
        <p class="graph-desc">{{ slotRelations.graph_description }}</p>
        <div class="relations-list">
          <div v-for="(rel, i) in slotRelations.relations" :key="i" class="relation-item">
            <span class="rel-from">{{ getSlotLabel(rel.from) }}</span>
            <span class="rel-arrow">→</span>
            <span class="rel-to">{{ getSlotLabel(rel.to) }}</span>
            <span class="rel-label">{{ rel.label }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 合并后：槽位清单 + 素材覆盖 + 提纲（二级行） -->
    <div v-if="streamDone" class="slots-editor">
      <div class="slots-header">
        <span class="slots-title">📋 槽位清单（{{ slots.length }} 个）</span>
        <div class="slots-header-actions">
          <template v-if="slotsLocked">
            <a-button size="small" type="outline" @click="slotsLocked = false">
              ✏️ 编辑槽位
            </a-button>
          </template>
          <template v-else>
            <a-button size="small" type="primary" @click="slotsLocked = true">
              ✅ 确认修改
            </a-button>
            <a-button size="small" type="outline" :loading="batchOutlineLoading"
              :disabled="!canBatchGenerate"
              @click="batchGenerateOutlines">
              🪄 一键生成提纲
            </a-button>
            <a-button size="small" type="primary" :ghost="true"
              :disabled="!canBatchAdopt"
              @click="batchAdoptOutlines">
              ✅ 全部采纳
            </a-button>
          </template>
          <span class="slots-hint">
            🟢 {{ fullCount }}个充足 
            <span v-if="partialCount > 0">| 🟡 {{ partialCount }}个偏少</span>
            <span v-if="emptyCount > 0">| 🔴 {{ emptyCount }}个为空</span>
          </span>
        </div>
      </div>

      <!-- 卡片式槽位列表：每个槽位3列（行1：名称/目标/提纲；行2：展开素材） -->
      <div class="slot-cards">
        <div v-for="slot in slots" :key="slot.slot_key"
          :class="['slot-card', `card-${preCheckResults[slot.slot_key]?.level || 'empty'}`]">

          <!-- 行1：3列（槽位名 / 章节目标 / 提纲） -->
          <div class="slot-card-row1">
            <!-- 列1：槽位名称 -->
            <div class="card-col col-name">
              <div class="col-label">#{{ slot.slot_key.replace('slot_', '') }}</div>
              <span v-if="slotsLocked" class="locked-text locked-label">{{ slot.label }}</span>
              <a-input v-else class="slot-label-input" :model-value="slot.label" size="small"
                @click.stop @change="(v) => $emit('update-slot', slot.slot_key, { label: v })" />
            </div>

            <!-- 列2：章节目标 -->
            <div class="card-col col-goal">
              <div class="col-label">章节目标</div>
              <span v-if="slotsLocked" class="locked-text locked-goal">{{ slot.description || '未设置' }}</span>
              <a-input v-else class="slot-goal-input" :model-value="slot.description || ''" size="small"
                placeholder="本章要达到的效果" @click.stop
                @change="(v) => $emit('update-slot', slot.slot_key, { description: v })" />
            </div>

            <!-- 列3：提纲（含素材标记，可展开） -->
            <div class="card-col col-outline">
              <div class="col-header">
                <span class="col-label">
                  📝 提纲要点
                  <span class="expand-toggle" @click.stop="toggleExpand(slot.slot_key)">
                    {{ expandedSlots[slot.slot_key] ? '▴' : '▾' }}
                  </span>
                </span>
                <div class="col-actions" v-if="!slotsLocked">
                  <a-button v-if="!slotOutlines[slot.slot_key]?.length && preCheckResults[slot.slot_key]?.count > 0"
                    size="mini" type="outline" :loading="previewLoading[slot.slot_key]"
                    @click.stop="requestOutline(slot.slot_key)">
                    🪄 生成提纲
                  </a-button>
                  <a-button v-if="slotPreviews[slot.slot_key]"
                    size="mini" type="primary" @click.stop="applyOutline(slot.slot_key)">
                    ✅ 采纳提纲
                  </a-button>
                  <a-button type="text" size="mini" status="danger" @click.stop="confirmDelete(slot.slot_key)">
                    🗑️
                  </a-button>
                </div>
              </div>

              <!-- 提纲列表（无素材标记，素材在第二行展示） -->
              <div v-if="slotOutlines[slot.slot_key]?.length" class="outline-compact-list">
                <div v-for="(item, oi) in slotOutlines[slot.slot_key].slice(0, 4)" :key="oi" class="outline-compact-item">
                  <span class="oci-num">{{ item.order || oi + 1 }}.</span>
                  <span class="oci-text">{{ item.point || item.text || item.content || '' }}</span>
                </div>
                <div v-if="slotOutlines[slot.slot_key].length > 4" class="oci-more"
                  @click.stop="toggleExpand(slot.slot_key)">
                  ...还有 {{ slotOutlines[slot.slot_key].length - 4 }} 条（点击展开）
                </div>
              </div>

              <!-- AI 生成的提纲预览（未采纳） -->
              <div v-if="slotPreviews[slot.slot_key]" class="outline-gen-result">
                <div class="ogr-title">AI建议提纲：</div>
                <div v-for="(line, li) in (slotPreviews[slot.slot_key] || '').split('\n').filter(l => l.trim())" :key="li" class="ogr-line">
                  {{ line }}
                </div>
              </div>

              <!-- 无提纲也无素材时 -->
              <div v-if="!slotOutlines[slot.slot_key]?.length && !slotPreviews[slot.slot_key] && preCheckResults[slot.slot_key]?.count === 0" class="outline-empty-hint">
                先补充素材再生成提纲
              </div>
            </div>
          </div>

          <!-- 行2：素材列表（紧凑模式） -->
          <div class="slot-card-row2">
            <span class="mat-badge mat-badge-lg">
              {{ preCheckResults[slot.slot_key]?.level === 'full' ? '🟢' : preCheckResults[slot.slot_key]?.level === 'partial' ? '🟡' : '🔴' }}
              {{ preCheckResults[slot.slot_key]?.count ?? 0 }} 条素材（{{ preCheckResults[slot.slot_key]?.matched_files?.length ?? 0 }} 个文件）
            </span>
            <div v-if="preCheckResults[slot.slot_key]?.matched_files?.length" class="matched-files-inline">
              <span v-for="(mf, fi) in preCheckResults[slot.slot_key].matched_files.slice(0, 12)" :key="fi" class="mf-chip">
                {{ mf.source_type === 'knowledge_base' ? '📄' : mf.source_type === 'ai_inferred' ? '🤖' : mf.source_type === 'mcp_summary' ? '📝' : '📌' }}
                {{ mf.filename || '未知' }}
              </span>
              <span v-if="preCheckResults[slot.slot_key].matched_files.length > 12" class="mf-more">
                +{{ preCheckResults[slot.slot_key].matched_files.length - 12 }}
              </span>
            </div>
            <span v-else class="no-mat-hint">暂无匹配素材</span>
          </div>

          <!-- AI 补充建议 -->
          <div v-if="slotSuggestions[slot.slot_key]" class="slot-card-suggestion">
            <span class="suggestion-label">💡 AI建议：</span>
            <span class="suggestion-text">{{ slotSuggestions[slot.slot_key] }}</span>
          </div>

          <!-- 展开：完整提纲编辑 -->
          <div v-if="expandedSlots[slot.slot_key]" class="slot-card-outline">
            <div class="section-outline-full">
              <div class="section-title">📋 完整提纲（可编辑）</div>
              <div v-if="slotOutlines[slot.slot_key]?.length" class="outline-full-list">
                <div v-for="(item, oi) in slotOutlines[slot.slot_key]" :key="oi" class="outline-full-item">
                  <span class="ofi-num">{{ item.order || oi + 1 }}.</span>
                  <a-input class="ofi-input" size="small"
                    :model-value="item.point || item.text || item.content || ''"
                    @click.stop
                    @change="(v) => updateOutlinePoint(slot.slot_key, oi, v)" />
                </div>
              </div>
              <div v-else class="outline-empty">暂无提纲</div>
            </div>
          </div>
        </div>
      </div>

      <div class="slot-actions">
        <a-button type="dashed" size="small" @click="addNewSlot">+ 新增槽位</a-button>
        <span class="slot-sep"></span>
        <a-button type="primary" size="small" @click="$emit('confirm-slots')">✔️ 确认槽位，开始填充</a-button>
      </div>

      <!-- 素材补充搜索 -->
      <div class="followup-panel">
        <div class="followup-header">
          <span class="followup-title">🔍 素材补充搜索</span>
          <span class="followup-hint">搜关键词，从素材池中找匹配素材</span>
        </div>

        <!-- 输入区域 -->
        <div class="followup-input-area">
          <a-textarea
            v-model="searchQuestion"
            placeholder="输入关键词，如「中小企业案例」「技术趋势」..."
            :auto-size="{ minRows: 2, maxRows: 4 }"
            @press-enter="handleSearchMaterials"
          />
          <div class="followup-toolbar">
            <div class="toolbar-right" style="flex:1;display:flex;justify-content:flex-end">
              <a-button size="small" type="primary" @click="handleSearchMaterials" :loading="asking">
                🔍 搜索素材
              </a-button>
            </div>
          </div>

          <!-- 搜索结果 -->
          <div v-if="searchResults.length" class="search-results">
            <div class="search-results-header">
              找到 {{ searchResults.length }} 条匹配素材：
            </div>
            <div v-for="(mat, i) in searchResults" :key="i" class="search-result-item">
              <span class="source-tag-sm">{{ sourceIcon(mat.source_type) }}</span>
              <span class="search-result-name">{{ mat.source_name || mat.filename || '素材' }}</span>
              <span class="search-result-preview">{{ mat.text }}</span>
              <a-select size="mini" placeholder="添加到槽位" style="width:120px;margin-left:8px" @change="(v) => addSearchResultToSlot(mat, v)">
                <a-option v-for="s in allSlotKeys" :key="s" :value="s">{{ slotLabels[s] || s }}</a-option>
              </a-select>
            </div>
          </div>
          <div v-else-if="searchDone" class="search-results">
            <div class="search-no-result">未找到匹配素材，试试其他关键词</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 预检加载中提示 -->
    <div v-if="preCheckRunning" class="precheck-loading">
      <a-spin /> 正在检查素材覆盖度...
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import { slotContentPreview } from '../../utils/api'

const props = defineProps({
  phase: { type: String, default: 'streaming' },
  streamingText: { type: String, default: '' },
  streamDone: { type: Boolean, default: false },
  slots: { type: Array, default: () => [] },
  slotRelations: { type: Object, default: null },
  preCheckResults: { type: Object, default: () => ({}) },
  preCheckRunning: { type: Boolean, default: false },
  slotOutlines: { type: Object, default: () => ({}) },
  sessionId: { type: String, default: '' },
  topic: { type: String, default: '' },
  selectedDirection: { type: Object, default: null },
  slotSuggestions: { type: Object, default: () => ({}) },  // AI 补充建议 { slotKey: text }
  slotMaterials: { type: Object, default: () => ({}) },     // 素材池 { slotKey: [materials] }
})

const emit = defineEmits([
  'update-slot', 'remove-slot', 'add-slot',
  'confirm-slots', 'stop-stream', 'add-material-to-slot',
  'run-pre-check', 'adopt-alternative', 'update-outline',
])

const showRelations = ref(true)
const asking = ref(false)
const searchQuestion = ref('')
const searchResults = ref([])
const searchDone = ref(false)
const expandedSlots = ref({})  // 展开/收起状态
const slotPreviews = ref({})  // 槽位提纲预览（AI生成未采纳）
const previewLoading = ref({})  // 预览加载状态
const batchOutlineLoading = ref(false)  // 一键生成加载状态
const slotsLocked = ref(false)  // 槽位锁定状态

// 是否有可一键生成的槽位（有素材但无提纲）
const canBatchGenerate = computed(() => {
  return props.slots.some(s => {
    const key = s.slot_key
    const pr = props.preCheckResults[key]
    const hasMaterial = pr?.count > 0
    const hasOutline = props.slotOutlines[key]?.length > 0
    return hasMaterial && !hasOutline && !slotPreviews.value[key]
  })
})

// 是否有可全部采纳的（有AI建议提纲待采纳）
const canBatchAdopt = computed(() => {
  return Object.keys(slotPreviews.value).some(k => slotPreviews.value[k])
})

// 预检计算
const hasPreCheckResults = computed(() => Object.keys(props.preCheckResults).length > 0)
const fullCount = computed(() => Object.values(props.preCheckResults).filter(r => r.level === 'full').length)
const partialCount = computed(() => Object.values(props.preCheckResults).filter(r => r.level === 'partial').length)
const emptyCount = computed(() => Object.values(props.preCheckResults).filter(r => r.level === 'empty').length)

// 流式完成后自动触发预检
watch(() => props.streamDone, (done) => {
  if (done && props.slots.length > 0 && !hasPreCheckResults.value && !props.preCheckRunning) {
    emit('run-pre-check', props.slots)
  }
})

function toggleExpand(slotKey) {
  expandedSlots[slotKey] = !expandedSlots[slotKey]
}

// 更新单个提纲要点
function updateOutlinePoint(slotKey, index, newText) {
  const list = props.slotOutlines[slotKey]
  if (!list || !list[index]) return
  list[index].point = newText
  list[index].text = newText
  emit('update-outline', slotKey, list)
}

function getSlotLabel(key) {
  const found = props.slots.find(s => s.slot_key === key)
  return found ? found.label : key
}

function confirmDelete(slotKey) {
  const ok = window.confirm(`确定删除槽位「${getSlotLabel(slotKey)}」？`)
  if (ok) emit('remove-slot', slotKey)
}

function addNewSlot() {
  const num = props.slots.length + 1
  emit('add-slot', `新增槽位${num}`, `自定义补充维度${num}`)
}

async function handleImageUpload(file) {
  alert('图片OCR功能：需后端提取文字后传入素材池')
  return false
}

// 生成提纲预览（调用 AI 生成 3-5 个提纲要点）
async function requestOutline(slotKey) {
  const slot = props.slots.find(s => s.slot_key === slotKey)
  if (!slot) return
  previewLoading.value[slotKey] = true
  try {
    const res = await slotContentPreview(
      props.sessionId,
      slotKey,
      slot.label,
      slot.description || '',
      props.topic || '',
      (props.selectedDirection?.name || '')
    )
    if (res.data?.code === 0) {
      slotPreviews.value[slotKey] = res.data.data.preview
    }
  } catch (e) {
    console.warn('提纲生成失败:', e)
  } finally {
    previewLoading.value[slotKey] = false
  }
}


// 采纳 AI 生成的提纲（拆分为要点列表）
function applyOutline(slotKey) {
  const text = slotPreviews.value[slotKey]
  if (!text) return
  // 按行拆分，过滤空行
  const lines = text.split('\n').filter(l => l.trim()).map((line, i) => ({
    order: i + 1,
    point: line.replace(/^\d+[\.\、\s]+/, '').trim(),
  }))
  if (lines.length === 0) return
  emit('update-outline', slotKey, lines)
  // 清除 AI 预览，展示采纳后的提纲
  delete slotPreviews.value[slotKey]
  // 锁定槽位
  slotsLocked.value = true
  Message.success('提纲已采纳，槽位已锁定')
}

// 一键生成所有槽位的提纲
async function batchGenerateOutlines() {
  batchOutlineLoading.value = true
  const slotsToGenerate = props.slots.filter(s => {
    const key = s.slot_key
    const pr = props.preCheckResults[key]
    return pr?.count > 0 && !props.slotOutlines[key]?.length && !slotPreviews.value[key]
  })
  
  if (slotsToGenerate.length === 0) {
    Message.info('所有槽位已有提纲或AI建议，无需生成')
    batchOutlineLoading.value = false
    return
  }
  
  let successCount = 0
  for (const slot of slotsToGenerate) {
    await requestOutline(slot.slot_key)
    if (slotPreviews.value[slot.slot_key]) successCount++
    // 小延迟避免请求过快
    await new Promise(r => setTimeout(r, 300))
  }
  
  batchOutlineLoading.value = false
  Message.success(`提纲生成完成：${successCount}/${slotsToGenerate.length} 个槽位成功`)
}

// 全部采纳 AI 建议提纲
function batchAdoptOutlines() {
  const keys = Object.keys(slotPreviews.value).filter(k => slotPreviews.value[k])
  if (keys.length === 0) {
    Message.info('暂无待采纳的提纲')
    return
  }
  let count = 0
  for (const key of keys) {
    const text = slotPreviews.value[key]
    if (!text) continue
    const lines = text.split('\n').filter(l => l.trim()).map((line, i) => ({
      order: i + 1,
      point: line.replace(/^\d+[\.\、\s]+/, '').trim(),
    }))
    if (lines.length > 0) {
      emit('update-outline', key, lines)
      delete slotPreviews.value[key]
      count++
    }
  }
  Message.success(`已采纳 ${count} 个槽位的提纲`)
  slotsLocked.value = true
}

// 素材来源图标
function sourceIcon(type) {
  const map = { knowledge_base: '📄', aipulse: '📡', web_search: '🌐', user_upload: '🖐️' }
  return map[type] || '📄'
}

// 所有槽位列表
const allSlotKeys = computed(() => props.slots.map(s => s.slot_key))
const slotLabels = computed(() => {
  const m = {}
  props.slots.forEach(s => { m[s.slot_key] = s.label || s.slot_key })
  return m
})

// 素材补充搜索
function handleSearchMaterials() {
  const q = searchQuestion.value.trim()
  if (!q) return
  asking.value = true
  searchDone.value = false
  searchResults.value = []

  // 从所有槽位的素材池中搜索匹配关键词
  const kw = q.toLowerCase()
  const found = []
  const seen = new Set()
  for (const [slotKey, mats] of Object.entries(props.slotMaterials)) {
    for (const m of mats) {
      const text = (m.text || '').toLowerCase()
      const name = (m.source_name || m.filename || '').toLowerCase()
      if ((text.includes(kw) || name.includes(kw)) && !seen.has(text.slice(0, 80))) {
        found.push({ ...m, _slotKey: slotKey })
        seen.add(text.slice(0, 80))
      }
      if (found.length >= 10) break
    }
    if (found.length >= 10) break
  }

  searchResults.value = found
  searchDone.value = true
  asking.value = false
}

// 将搜索结果添加到指定槽位
function addSearchResultToSlot(mat, targetSlotKey) {
  emit('add-material-to-slot', targetSlotKey, mat.text, mat.source_name || mat.filename || '素材', mat.source_type)
  Message.success(`已添加到 ${slotLabels.value[targetSlotKey] || targetSlotKey}`)
  // 从结果中移除
  searchResults.value = searchResults.value.filter(m => m !== mat)
}
</script>

<style scoped lang="less">
.stream-slots-panel { width: 100%; }

/* -------------------------- 流式推理头部 -------------------------- */
.stream-thinking {
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  margin-bottom: 16px;
  overflow: hidden;
}
.stream-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: #f6ffed;
  border-bottom: 1px solid #b7eb8f;
  font-size: 14px;
  font-weight: 600;
}
.stream-icon { font-size: 16px; }
.stream-content { padding: 14px; }
.stream-text {
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.7;
  color: #434343;
}

/* -------------------------- 关系图 -------------------------- */
.relations-graph {
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  margin-bottom: 16px;
  overflow: hidden;
}
.relations-header {
  padding: 10px 14px;
  background: #fafafa;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.relations-body { padding: 14px; }
.graph-desc { font-size: 13px; color: #666; margin: 0 0 10px 0; }
.relations-list { display: flex; flex-wrap: wrap; gap: 10px 20px; }
.relation-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  background: #f5f5f5;
  border-radius: 4px;
  font-size: 12px;
}
.rel-from, .rel-to { font-weight: 500; }
.rel-arrow { color: #1890ff; font-weight: 700; }
.rel-label { color: #888; }

/* -------------------------- 合并表格 -------------------------- */
.slots-editor {
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  overflow: hidden;
}
.slots-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: #fafafa;
  border-bottom: 1px solid #e8e8e8;
}
.slots-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.slots-title { font-size: 14px; font-weight: 600; }
.slots-hint { font-size: 12px; color: #666; }

/* ===== 卡片式槽位列表 ===== */
.slot-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.slot-card {
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  overflow: hidden;
  transition: box-shadow .2s;
}
.slot-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,.06); }
.card-full { border-left: 4px solid #52c41a; }
.card-partial { border-left: 4px solid #faad14; }
.card-empty { border-left: 4px solid #ff4d4f; }

/* Row 1: 3 列（名称/目标/提纲）不等分布局 */
.slot-card-row1 {
  display: flex;
  align-items: stretch;
  gap: 12px;
  padding: 12px 14px;
  background: #fff;
  border-bottom: 1px solid #f5f5f5;
  overflow: hidden;
  min-width: 0;
}
.card-col { min-width: 0; display: flex; flex-direction: column; }
.col-name { flex: 1; }
.col-goal { flex: 2; }
.col-outline { flex: 3.5; }
.locked-text {
  font-size: 13px;
  color: #1d2129;
  line-height: 1.5;
  padding: 4px 0;
}
.locked-label { font-weight: 600; font-size: 14px; }
.locked-goal { color: #4e5969; }
.col-label {
  font-size: 11px;
  color: #999;
  margin-bottom: 4px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
}
.expand-toggle {
  color: #165dff;
  cursor: pointer;
  font-size: 10px;
  font-weight: 600;
}
.col-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.col-actions { display: flex; gap: 4px; align-items: center; }

/* 提纲紧凑列表（含标记） */
.outline-compact-list { display: flex; flex-direction: column; gap: 3px; }
.outline-compact-item {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  font-size: 12px;
  line-height: 1.5;
}
.oci-num { color: #165dff; font-weight: 500; flex-shrink: 0; }
.oci-text { flex: 1; color: #434343; word-break: break-all; overflow-wrap: break-word; line-height: 1.5; }
.oci-more {
  font-size: 11px;
  color: #165dff;
  cursor: pointer;
  padding: 2px 0;
}
.outline-empty-hint { font-size: 12px; color: #bbb; padding: 4px 0; }

/* 展开区：完整提纲编辑 */
.section-outline-full { width: 100%; }
.section-title { font-size: 12px; font-weight: 600; color: #666; margin-bottom: 8px; }
.outline-full-list { display: flex; flex-direction: column; gap: 5px; }
.outline-full-item {
  display: flex;
  align-items: flex-start;
  gap: 6px;
}
.ofi-num { color: #165dff; font-weight: 500; padding: 2px 0; flex-shrink: 0; }
.ofi-input { flex: 1; }

/* Row 2: 素材列表（紧凑模式，旧，保留避免报错） */
.slot-card-row2 {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  background: #fafbfc;
  flex-wrap: wrap;
}
.mat-badge-lg {
  flex-shrink: 0;
  padding: 3px 10px;
  font-size: 12px;
}
.matched-files-inline {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  flex: 1;
}
.mf-chip {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 8px;
  background: #fff;
  border: 1px solid #e5e6eb;
  border-radius: 10px;
  font-size: 11px;
  color: #555;
  white-space: nowrap;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.mf-more {
  font-size: 11px;
  color: #999;
  padding: 0 4px;
}
.no-mat-hint { color: #ccc; font-size: 12px; }
.no-preview-hint { font-size: 12px; color: #ccc; }

/* AI 补充建议行 */
.slot-card-suggestion {
  padding: 8px 14px;
  background: #f0f5ff;
  border-top: 1px dashed #b3d8ff;
  font-size: 12px;
  color: #1d2129;
  line-height: 1.6;
}
.suggestion-label {
  font-weight: 600;
  color: #165dff;
  margin-right: 6px;
}
.suggestion-text { color: #4e5969; }

/* 提纲预览区域 */
.outline-preview-area { flex: 1; display: flex; flex-direction: column; gap: 6px; }
.outline-mini-list { display: flex; flex-direction: column; gap: 2px; }
.outline-mini-item { font-size: 12px; color: #333; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.omi-num { color: #165dff; font-weight: 600; margin-right: 4px; }
.omi-text { color: #333; }
.outline-mini-more { font-size: 11px; color: #999; }
.outline-gen-area { display: flex; flex-direction: column; gap: 4px; align-items: flex-start; }
.outline-gen-hint { font-size: 11px; color: #bbb; }
.outline-gen-result { background: #f0f5ff; border-radius: 6px; padding: 8px; margin-top: 4px; }
.ogr-title { font-size: 11px; font-weight: 600; color: #165dff; margin-bottom: 4px; }
.ogr-line { font-size: 12px; color: #333; padding: 2px 0; line-height: 1.5; }

/* 内容预览文本行 */
.preview-text-auto { font-size: 12px; color: #666; line-height: 1.5; word-break: break-all; }

/* 素材 chip 完整显示文件名 */
.mf-chip {
  max-width: none;
  white-space: nowrap;
}

/* 展开提纲 */
.slot-card-outline {
  padding: 12px 14px 12px 30px;
  background: #f9fafb;
  border-top: 1px dashed #e0e0e0;
}

/* preview text inside card */
.slot-preview-text {
  margin-top: 6px;
  padding: 8px 10px;
  background: #f0f5ff;
  border-radius: 6px;
  border-left: 3px solid #1890ff;
  font-size: 12px;
  color: #333;
  line-height: 1.6;
  white-space: pre-wrap;
  max-height: 120px;
  overflow-y: auto;
}

.slot-label-input, .slot-desc-input { width: 100%; }

/* ===== 旧表格样式清理 ===== */

.expand-arrow { display: none; }

.mat-badge {
  display: inline-block;
  padding: 2px 8px;
  background: #f5f5f5;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
}

/* 匹配素材文件列表（上下结构） */
.matched-files-block {
  margin-top: 8px;
  padding: 6px 8px;
  background: #fafafa;
  border-radius: 6px;
}
.files-block-title {
  font-size: 11px;
  color: #999;
  margin-bottom: 4px;
  font-weight: 500;
}
.matched-file-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 0;
  font-size: 11px;
  border-bottom: 1px solid #f0f0f0;
}
.matched-file-row:last-child { border-bottom: none; }
.file-src-icon { font-size: 13px; flex-shrink: 0; }
.file-name-full {
  font-size: 11px;
  color: #555;
  word-break: break-all;
  line-height: 1.3;
}
.matched-files {
  margin-top: 6px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.matched-file-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #555;
  line-height: 1.4;
}
.file-more {
  font-size: 11px;
  color: #1890ff;
  cursor: pointer;
  margin-top: 2px;
}
.mat-suggest {
  margin-left: 10px;
  font-size: 12px;
  color: #1890ff;
}
.alt-chip {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 6px;
  background: #e6f7ff;
  border-radius: 10px;
  cursor: pointer;
}
.alt-chip:hover { background: #bae7ff; }
.mat-empty-hint { font-size: 12px; color: #999; font-style: italic; margin-left: 10px; }

/* 二级行 - 提纲 */
.row-detail { background: #fcfcfc; }
.row-detail td { padding: 12px 12px 12px 76px; border-bottom: 1px solid #f0f0f0; }
.detail-outline { color: #555; }
.outline-title { font-size: 12px; font-weight: 600; margin-bottom: 8px; color: #888; }
.outline-list { display: flex; flex-direction: column; gap: 6px; }
.outline-item { display: flex; gap: 6px; font-size: 12px; line-height: 1.6; }
.oi-num { color: #999; font-weight: 500; min-width: 20px; }
.oi-text { flex: 1; }
.outline-empty { font-size: 12px; color: #bbb; font-style: italic; }

.slot-actions {
  padding: 14px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
}
.slot-sep { flex: 1; }

/* -------------------------- 追问面板 -------------------------- */
.followup-panel {
  border-top: 1px solid #e8e8e8;
  margin-top: 4px;
}
.followup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: #f0f5ff;
  border-bottom: 1px solid #adc6ff;
}
.followup-title { font-size: 14px; font-weight: 600; }
.followup-hint { font-size: 12px; color: #666; }

.followup-history {
  max-height: 280px;
  overflow-y: auto;
  padding: 12px 14px;
  border-bottom: 1px solid #f0f0f0;
}
.followup-bubble { margin-bottom: 12px; }
.bubble-q, .bubble-a {
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.6;
}
.bubble-q { background: #e6f7ff; margin-bottom: 6px; }
.bubble-a { background: #f6ffed; }
.bubble-label { font-weight: 600; color: #1890ff; margin-right: 6px; }
.bubble-a .bubble-label { color: #52c41a; }

.followup-input-area { padding: 14px; }
.followup-toolbar {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
}

/* 素材搜索结果 */
.search-results {
  margin-top: 12px;
  border-top: 1px solid #f0f0f0;
  padding-top: 10px;
}
.search-results-header {
  font-size: 13px;
  color: #666;
  margin-bottom: 8px;
}
.search-result-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  background: #fafafa;
  border-radius: 4px;
  margin-bottom: 6px;
  font-size: 12px;
}
.search-result-name {
  font-weight: 600;
  color: #333;
  min-width: 80px;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.search-result-preview {
  color: #86909c;
  flex: 1;
  line-height: 1.5;
  word-break: break-all;
}
.search-no-result {
  color: #86909c;
  font-size: 13px;
  text-align: center;
  padding: 12px;
}

.precheck-loading {
  text-align: center;
  padding: 20px;
  color: #999;
}
</style>
