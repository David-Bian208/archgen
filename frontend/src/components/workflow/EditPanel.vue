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

          <!-- 补充素材 -->
          <div class="panel-section">
            <div class="section-title">📎 补充素材</div>
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
                  {{ truncateText(mat.text, 120) }}
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

          <!-- 追问 AI - 完整对话样式 -->
          <div class="panel-section">
            <div class="followup-panel">
              <div class="followup-header">
                <span class="followup-title">💬 追问 AI</span>
                <span class="followup-hint">基于当前素材搜索</span>
              </div>
              
              <!-- 对话历史 -->
              <div v-if="localFollowupHistory.length" class="followup-history">
                <div v-for="(item, i) in localFollowupHistory" :key="i" class="followup-bubble">
                  <div class="bubble-q">
                    <span class="bubble-label">你问：</span>
                    {{ item.q }}
                  </div>
                  <div class="bubble-a">
                    <span class="bubble-label">AI 答：</span>
                    {{ item.a }}
                  </div>
                </div>
              </div>
              
              <!-- 输入区域 -->
              <div class="followup-input-area">
                <a-textarea
                  v-model="followupInput"
                  placeholder="输入你的问题，例如：为什么匹配这个素材？提纲如何调整？..."
                  :auto-size="{ minRows: 3, maxRows: 6 }"
                  @press-enter="onAskFollowup"
                />
                <div class="followup-toolbar">
                  <div class="toolbar-left">
                    <a-radio-group v-model="searchScope" type="button" size="mini">
                      <a-radio value="all">全库搜索</a-radio>
                      <a-radio value="folder">指定文件夹</a-radio>
                      <a-radio value="file">指定文件</a-radio>
                    </a-radio-group>
                  </div>
                  <div class="toolbar-right">
                    <a-space>
                      <a-upload 
                        :show-file-list="false" 
                        accept="image/*"
                        :before-upload="handleImageUpload"
                      >
                        <a-button type="text" size="small">📷 图片</a-button>
                      </a-upload>
                      <a-button 
                        type="primary" 
                        size="small" 
                        :disabled="!followupInput.trim()"
                        @click="onAskFollowup"
                      >
                        发送
                      </a-button>
                    </a-space>
                  </div>
                </div>
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
import { ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'

const props = defineProps({
  slotKey: { type: String, default: '' },
  slotLabel: { type: String, default: '' },
  materials: { type: Array, default: () => [] },
  outline: { type: Array, default: () => [] },
  writingPlan: { type: String, default: '' },
  followupHistory: { type: Array, default: () => [] },
})

const emit = defineEmits([
  'close', 'save-plan', 'add-material', 'update-outline', 'ask-followup',
])

const visible = ref(true)
const localWritingPlan = ref('')
const localOutline = ref([])
const newMaterialText = ref('')
const followupInput = ref('')
const localFollowupHistory = ref([])
const searchScope = ref('all')
const expandedMats = ref({})  // 展开的素材 { index: boolean }

function toggleMatExpand(idx) {
  expandedMats.value[idx] = !expandedMats.value[idx]
}

watch(() => props.writingPlan, (v) => { localWritingPlan.value = v || '' }, { immediate: true })
watch(() => props.outline, (v) => { localOutline.value = v ? [...v] : [] }, { immediate: true })
watch(() => props.followupHistory, (v) => { localFollowupHistory.value = v || [] }, { immediate: true })

function sourceIcon(type) {
  const map = { knowledge_base: '📄', user_input: '✏️', web_search: '🌐', ai_inferred: '🤖' }
  return map[type] || '📎'
}

function truncateText(text, maxLen) {
  if (!text) return ''
  return text.length > maxLen ? text.slice(0, maxLen) + '...' : text
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

function onAskFollowup() {
  const q = followupInput.value.trim()
  if (!q) return
  emit('ask-followup', q, searchScope.value)
  localFollowupHistory.value = [...localFollowupHistory.value, { q, a: '思考中...' }]
  followupInput.value = ''
}

function handleImageUpload(file) {
  // TODO: OCR 图片提取文字后追加到输入框
  Message.info('图片上传功能待完善，将提取图片文字后追加到输入框')
  return false
}

function onClose() {
  visible.value = false
  setTimeout(() => emit('close'), 300)
}

function onSaveAll() {
  if (localWritingPlan.value !== props.writingPlan) {
    savePlan()
  }
  Message.success('保存成功')
  onClose()
}
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
  width: 420px;
  height: 100%;
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

/* 追问面板 - 完整对话样式 */
.followup-panel {
  border: 1px solid var(--color-border-2);
  border-radius: 8px;
  overflow: hidden;
}
.followup-header {
  padding: 10px 12px;
  background: var(--color-bg-2);
  border-bottom: 1px solid var(--color-border-2);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.followup-title { font-size: 14px; font-weight: 600; }
.followup-hint { font-size: 12px; color: var(--color-text-3); }
.followup-history {
  padding: 12px;
  max-height: 250px;
  overflow-y: auto;
}
.followup-bubble { margin-bottom: 16px; }
.bubble-q {
  font-size: 13px;
  color: var(--color-text-2);
  margin-bottom: 4px;
}
.bubble-a {
  font-size: 14px;
  color: var(--color-text-1);
  line-height: 1.6;
  padding: 10px 12px;
  background: var(--color-bg-2);
  border-radius: 6px;
}
.bubble-label { font-weight: 600; }
.followup-input-area {
  padding: 12px;
  border-top: 1px solid var(--color-border-2);
}
.followup-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}
.toolbar-left { font-size: 12px; }

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
