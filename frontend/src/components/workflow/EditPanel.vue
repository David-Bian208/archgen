<template>
  <transition name="slide">
    <div v-if="visible" class="edit-panel-overlay" @click.self="onClose">
      <div class="edit-panel">
        <div class="panel-header">
          <span class="panel-title">✏️ 编辑槽位：{{ slotLabel }}</span>
          <a-button type="text" size="small" @click="onClose">✕</a-button>
        </div>

        <div class="panel-body">
          <!-- 写作方案 -->
          <div class="panel-section">
            <div class="section-title">📋 写作方案</div>
            <a-textarea
              :model-value="localWritingPlan"
              placeholder="描述这个槽位的写作思路，如「用对比手法，先现状再案例最后建议」..."
              :auto-size="{ minRows: 3, maxRows: 6 }"
              @change="onWritingPlanChange"
            />
            <a-button type="text" size="mini" @click="savePlan">保存方案</a-button>
          </div>

          <!-- H3: 快速分析 -->
          <div class="panel-section">
            <div class="section-title">🔍 快速分析</div>
            <div class="analyze-buttons">
              <a-button
                v-for="btn in analyzeButtons"
                :key="btn.type"
                size="small"
                :loading="analyzeLoading === btn.type"
                @click="onAnalyze(btn.type)"
              >
                {{ btn.icon }} {{ btn.label }}
              </a-button>
            </div>

            <!-- 分析结果 -->
            <div v-if="analyzeResult" class="analyze-result">
              <div class="analyze-result-header">
                <span class="analyze-result-type">{{ analyzeTypeLabel }}</span>
                <span class="analyze-retry" @click="onAnalyze(analyzeLastType, true)">
                  🔄 重新分析
                </span>
              </div>
              <div class="analyze-result-text">{{ analyzeResult }}</div>
              <div class="analyze-result-actions">
                <a-button type="primary" size="small" @click="onApplyToOutline">
                  ✅ 应用到当前提纲
                </a-button>
              </div>
            </div>
            <div v-else-if="analyzeError" class="analyze-result analyze-error">
              <span class="analyze-error-text">分析失败，请重试</span>
              <a-button size="mini" @click="onAnalyze(analyzeLastType, true)">重试</a-button>
            </div>
          </div>

          <!-- 补充素材 -->
          <div class="panel-section">
            <div class="section-title">
              📎 补充素材
              <span class="material-count-badge" :class="matCountClass">{{ matCountLabel }}</span>
            </div>
            <a-textarea
              v-model="newMaterialText"
              placeholder="输入补充文本..."
              :auto-size="{ minRows: 2, maxRows: 4 }"
            />
            <div class="material-actions">
              <a-button size="small" :disabled="!newMaterialText.trim()" @click="addTextMaterial">
                添加文本
              </a-button>
              <a-upload
                :show-file-list="false"
                :custom-request="onFileUpload"
                accept=".txt,.md,.pdf,.docx"
              >
                <a-button size="small">📁 上传文件</a-button>
              </a-upload>
              <!-- W3: 联网搜索补充 -->
              <a-button size="small" @click="onWebSearch" :loading="webSearching">
                联网搜索补充
              </a-button>
            </div>

            <!-- W3: 联网搜索结果 -->
            <div v-if="webResults.length" class="web-results">
              <div class="section-subtitle">搜索到 {{ webResults.length }} 条素材：</div>
              <div v-for="(r, i) in webResults" :key="i" class="web-result-item">
                <span class="web-result-title">{{ r.title }}</span>
                <span class="web-result-snippet">{{ r.snippet }}</span>
                <a-button size="mini" type="outline" @click="addWebResult(r)">➕ 添加</a-button>
              </div>
            </div>

            <div v-if="materials.length" class="existing-materials">
              <div class="section-subtitle">已匹配素材（{{ materials.length }} 条）：</div>
              <div v-for="(mat, i) in materials" :key="i" class="mat-item">
                <div class="mat-header">
                  <span class="source-tag-sm">{{ sourceIcon(mat.source_type) }}</span>
                  <span class="mat-filename">{{ mat.source_name || mat.filename || '素材' }}</span>
                  <span class="mat-expand" @click="toggleMatExpand(i)">
                    {{ expandedMats[i] ? '收起' : '展开全文' }}
                  </span>
                </div>
                <div v-if="expandedMats[i]" class="mat-full-text">
                  <pre>{{ mat.text }}</pre>
                </div>
                <div v-else class="mat-preview-text">
                  {{ mat.text }}
                </div>
              </div>
            </div>
          </div>

          <!-- 微调提纲 -->
          <div class="panel-section">
            <div class="section-title">🔧 微调提纲</div>
            <div v-if="!localOutline.length" class="empty-hint">暂无提纲，请先生成内容</div>
            <div v-for="(item, i) in localOutline" :key="i" class="outline-edit-item">
              <span class="outline-order">{{ i + 1 }}</span>
              <a-input
                :model-value="item.point"
                size="small"
                @change="(v) => onOutlineChange(i, v)"
              />
              <a-button type="text" size="mini" status="danger" @click="removeOutlineItem(i)">✕</a-button>
            </div>
            <a-button type="dashed" size="small" @click="addOutlineItem">+ 添加要点</a-button>
          </div>

          <!-- W2-2: 整合生成 -->
          <div class="panel-section">
            <a-button
              type="primary"
              size="small"
              long
              :loading="integrateLoading"
              :disabled="!localOutline.length"
              @click="onIntegrateOutline"
            >
              🔄 整合生成
            </a-button>
            <span class="integrate-hint">整合提纲碎片+素材为连贯内容</span>

            <!-- 整合结果预览 -->
            <div v-if="integratedOutline.length" class="integrate-result">
              <div class="integrate-result-header">
                整合结果预览（{{ integratedOutline.length }} 条要点）：
              </div>
              <div v-for="(item, i) in integratedOutline" :key="i" class="integrate-item">
                <span class="outline-order">{{ item.order || i + 1 }}</span>
                <span>{{ item.point }}</span>
              </div>
              <div class="integrate-result-actions">
                <a-button size="small" @click="applyIntegratedOutline">✅ 采用此提纲</a-button>
                <a-button size="small" @click="integratedOutline = []">✕ 放弃</a-button>
              </div>
            </div>
          </div>
        </div>

        <div class="panel-footer">
          <a-button @click="onClose">取消</a-button>
          <a-button type="primary" @click="onSaveAll">保存</a-button>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { Message } from '@arco-design/web-vue'

const props = defineProps({
  slotKey: { type: String, default: '' },
  slotLabel: { type: String, default: '' },
  materials: { type: Array, default: () => [] },
  outline: { type: Array, default: () => [] },
  writingPlan: { type: String, default: '' },
  analyzeResult: { type: String, default: '' },        // H3: 当前分析结果
  analyzeLoading: { type: String, default: '' },        // H3: 正在加载的分析类型
  analyzeError: { type: Boolean, default: false },      // H3: 分析是否失败
  analyzeTypeLabel: { type: String, default: '' },      // H3: 分析类型中文标签
})

const emit = defineEmits([
  'close', 'save-plan', 'add-material', 'update-outline', 'analyze-slot', 'apply-analyze',
  'integrate-outline', 'web-search-slot',
])

// H3: 分析按钮配置
const analyzeButtons = [
  { type: 'core_points', icon: '📊', label: '核心观点' },
  { type: 'outline_relation', icon: '📈', label: '提纲关联' },
  { type: 'expand_outline', icon: '✏️', label: '扩写提纲' },
  { type: 'extension_direction', icon: '🔗', label: '扩展方向' },
]

const typeLabels = {
  core_points: '核心观点',
  outline_relation: '提纲关联',
  expand_outline: '扩写提纲',
  extension_direction: '扩展方向',
}

const visible = ref(true)
const localWritingPlan = ref('')
const localOutline = ref([])
const newMaterialText = ref('')
const expandedMats = ref({})

// W2-2: 整合生成
const integrateLoading = ref(false)
const integratedOutline = ref([])

// W3: 联网搜索
const webSearching = ref(false)
const webResults = ref([])

// 素材评估
const matCountClass = computed(() => {
  const n = props.materials.length
  if (n >= 3) return 'mat-sufficient'
  if (n >= 1) return 'mat-partial'
  return 'mat-empty'
})
const matCountLabel = computed(() => {
  const n = props.materials.length
  if (n >= 3) return `✅ ${n} 条素材充足`
  if (n >= 1) return `🟡 ${n} 条素材偏少`
  return `🔴 无素材`
})

function toggleMatExpand(idx) {
  expandedMats.value[idx] = !expandedMats.value[idx]
}

watch(() => props.writingPlan, (v) => { localWritingPlan.value = v || '' }, { immediate: true })
watch(() => props.outline, (v) => { localOutline.value = v ? [...v] : [] }, { immediate: true })

function sourceIcon(type) {
  const map = { knowledge_base: '📄', user_input: '✏️', web_search: '🌐', ai_inferred: '🤖' }
  return map[type] || '📎'
}

function onWritingPlanChange(v) { localWritingPlan.value = v }

function savePlan() {
  emit('save-plan', localWritingPlan.value)
}

function addTextMaterial() {
  const text = newMaterialText.value.trim()
  if (!text) return
  emit('add-material', text, 'manual.md')
  newMaterialText.value = ''
  Message.success('素材已添加')
}

function onFileUpload(option) {
  const file = option.file
  if (!file) return
  const reader = new FileReader()
  reader.onload = (e) => {
    emit('add-material', e.target.result, file.name || 'upload.txt')
    Message.success(`文件 ${file.name} 已上传`)
  }
  reader.readAsText(file)
}

function onOutlineChange(index, value) {
  localOutline.value[index] = { ...localOutline.value[index], point: value }
  emit('update-outline', [...localOutline.value])
}

function removeOutlineItem(index) {
  localOutline.value = localOutline.value.filter((_, i) => i !== index)
  emit('update-outline', [...localOutline.value])
}

function addOutlineItem() {
  const newItem = { point: '新要点', order: localOutline.value.length + 1 }
  localOutline.value = [...localOutline.value, newItem]
  emit('update-outline', [...localOutline.value])
}

// H3: 触发分析
function onAnalyze(type, retry = false) {
  emit('analyze-slot', type, retry)
}

// H3: 应用分析结果到提纲
// 过滤分析结果中的引导语前缀
function cleanAnalyzeResult(text) {
  if (!text) return ''
  let cleaned = text.trim()
  const prefixes = [
    /^好的，根据您提供的素材，我提炼出以下\d*个核心观点[：:]\s*/i,
    /^好的，作为您的写作顾问，我已仔细分析了您提供的[^。]+[。.]\s*/i,
    /^好的，我来帮您分析[。，]\s*/i,
    /^好的，根据您提供的[，，]?\s*/i,
    /^好的，让我来总结[。，]?\s*/i,
    /^根据您提供的素材[，，]?\s*/i,
    /^综合以上分析[，，]\s*/i,
    /^核心观点[：:]\s*/i,
    /^\d+\.\s*/,
  ]
  for (const prefix of prefixes) {
    const match = cleaned.match(prefix)
    if (match) {
      cleaned = cleaned.slice(match[0].length).trim()
    }
  }
  return cleaned
}

function onApplyToOutline() {
  if (!props.analyzeResult) return
  const cleaned = cleanAnalyzeResult(props.analyzeResult)
  if (!cleaned) return
  const newItem = { point: cleaned, order: localOutline.value.length + 1 }
  localOutline.value = [...localOutline.value, newItem]
  emit('update-outline', [...localOutline.value])
}

// W2-2: 整合生成
async function onIntegrateOutline() {
  integrateLoading.value = true
  integratedOutline.value = []
  try {
    emit('integrate-outline', {
      slotKey: props.slotKey,
      slotLabel: props.slotLabel,
      outline: [...localOutline.value],
      materials: [...props.materials],
      writingPlan: localWritingPlan.value,
    })
  } catch (e) {
    Message.error('整合请求失败')
  } finally {
    integrateLoading.value = false
  }
}

// 外部设置整合结果（由 compose 调用）
function setIntegratedOutline(result) {
  integratedOutline.value = result || []
}

// 采用整合生成的提纲
function applyIntegratedOutline() {
  localOutline.value = integratedOutline.value.map((item, i) => ({
    ...item,
    order: i + 1,
  }))
  integratedOutline.value = []
  emit('update-outline', [...localOutline.value])
  Message.success('提纲已更新')
}

// W3: 联网搜索
async function onWebSearch() {
  webSearching.value = true
  webResults.value = []
  try {
    emit('web-search-slot', {
      slotKey: props.slotKey,
      slotLabel: props.slotLabel,
    })
  } catch (e) {
    Message.error('联网搜索失败')
  } finally {
    webSearching.value = false
  }
}

// 外部设置搜索结果（由 compose 调用）
function setWebResults(results) {
  webResults.value = results || []
}

// 添加联网搜索结果
function addWebResult(result) {
  emit('add-material', result.snippet, result.title || 'web_result')
  // 从结果列表移除
  webResults.value = webResults.value.filter(r => r !== result)
  Message.success('素材已添加')
}

function onClose() {
  visible.value = false
  setTimeout(() => emit('close'), 300)
}

function onSaveAll() {
  if (localWritingPlan.value !== props.writingPlan) {
    savePlan()
  }
  emit('update-outline', [...localOutline.value])
  onClose()
}

// 暴露函数供父组件调用（异步结果回传）
defineExpose({
  setIntegratedOutline,
  setWebResults,
})
</script>

<style scoped>
.edit-panel-overlay {
  position: fixed;
  top: 0; right: 0; bottom: 0; left: 0;
  background: rgba(0,0,0,0.3);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}
.edit-panel {
  width: min(620px, 40vw);
  min-width: 480px;
  max-height: 100vh;
  background: var(--color-bg-1);
  box-shadow: -4px 0 20px rgba(0,0,0,0.1);
  display: flex;
  flex-direction: column;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid var(--color-border-2);
}
.panel-title { font-size: 16px; font-weight: 600; }
.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}
.panel-section {
  margin-bottom: 20px;
}
.section-title { font-size: 14px; font-weight: 600; margin-bottom: 8px; }
.section-subtitle { font-size: 12px; color: var(--color-text-3); margin: 8px 0 4px; }

/* 素材统计标记 */
.material-count-badge {
  font-size: 11px;
  margin-left: 8px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}
.material-count-badge.mat-sufficient { background: #e8f7ed; color: #00b42a; }
.material-count-badge.mat-partial { background: #fff7e6; color: #ff7d00; }
.material-count-badge.mat-empty { background: #ffece8; color: #f53f3f; }

/* 联网搜索结果 */
.web-results { margin-top: 10px; border-top: 1px dashed var(--color-border-2); padding-top: 8px; }
.web-result-item {
  display: flex; align-items: flex-start; gap: 8px; padding: 6px 0;
  border-bottom: 1px solid var(--color-border-1);
}
.web-result-title { font-weight: 600; font-size: 12px; min-width: 80px; max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.web-result-snippet { flex: 1; font-size: 11px; color: var(--color-text-3); }

/* 整合生成 */
.integrate-hint { display: block; font-size: 11px; color: var(--color-text-3); margin-top: 4px; }
.integrate-result {
  margin-top: 12px;
  padding: 10px;
  background: #f0f7ff;
  border-radius: 6px;
  border: 1px solid #b4d5ff;
}
.integrate-result-header { font-size: 12px; font-weight: 600; margin-bottom: 6px; color: #165dff; }
.integrate-item { padding: 4px 0; font-size: 13px; }
.integrate-item .outline-order {
  display: inline-flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; border-radius: 50%;
  background: #165dff; color: white; font-size: 11px; margin-right: 8px;
}
.integrate-result-actions { margin-top: 10px; display: flex; gap: 8px; }
.material-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
.existing-materials { margin-top: 8px; }
.mat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
  font-size: 12px;
  padding: 6px 8px;
  background: #fafbfc;
  border-radius: 6px;
}
.mat-header {
  display: flex;
  align-items: center;
  gap: 6px;
}
.mat-filename {
  font-weight: 500;
  color: #1d2129;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mat-expand {
  color: var(--color-primary, #165dff);
  cursor: pointer;
  font-size: 11px;
  flex-shrink: 0;
  margin-left: auto;
}
.mat-expand:hover { text-decoration: underline; }
.mat-preview-text { color: #86909c; line-height: 1.4; }
.mat-full-text {
  border-top: 1px solid #e5e6eb;
  padding-top: 6px;
}
.mat-full-text pre {
  margin: 0;
  font-family: inherit;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  color: #4e5969;
  max-height: 250px;
  overflow-y: auto;
}
.source-tag-sm { flex-shrink: 0; }
.outline-edit-item {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.outline-order {
  width: 20px;
  text-align: center;
  font-weight: 600;
  color: var(--color-primary);
}
.empty-hint { font-size: 13px; color: var(--color-text-3); font-style: italic; }

/* H3: 快速分析 */
.analyze-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}
.analyze-result {
  border: 1px solid var(--color-border-2);
  border-radius: 8px;
  padding: 12px;
  margin-top: 8px;
}
.analyze-result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.analyze-result-type {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-primary);
}
.analyze-retry { font-size: 12px; color: var(--color-text-3); cursor: pointer; }
.analyze-retry:hover { color: var(--color-primary); }
.analyze-result-text {
  font-size: 13px;
  line-height: 1.6;
  color: var(--color-text-1);
  white-space: pre-wrap;
  max-height: 300px;
  overflow-y: auto;
  margin-bottom: 10px;
}
.analyze-result-actions { display: flex; gap: 8px; }
.analyze-error {
  border-color: #fca5a5;
  background: #fef2f2;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}
.analyze-error-text { color: #dc2626; }

.panel-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding: 16px;
  border-top: 1px solid var(--color-border-2);
}

/* 滑入动画 */
.slide-enter-active { transition: all 0.3s ease-out; }
.slide-leave-active { transition: all 0.3s ease-in; }
.slide-enter-from .edit-panel { transform: translateX(100%); }
.slide-leave-to .edit-panel { transform: translateX(100%); }
.slide-enter-from { background: transparent; }
.slide-leave-to { background: transparent; }
</style>
