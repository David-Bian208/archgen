<template>
  <a-modal
    v-model:visible="dialogVisible"
    :title="modalTitle"
    :width="900"
    :centered="true"
    :footer="null"
    @cancel="handleCancel"
    :maskClosable="false"
  >
    <div class="supplement-dialog">
      <!-- 检测到的问题列表 -->
      <div v-if="issues.length > 0" class="issues-section">
        <div class="issues-title">🔍 检测到以下可优化点（点击引用）</div>
        <div class="issues-list">
          <a-tag
            v-for="(issue, i) in issues"
            :key="i"
            class="issue-tag"
            :color="currentStepIndex >= 0 ? 'orangered' : ''"
            @click="toggleIssueReference(issue)"
          >
            {{ issue.title }}
          </a-tag>
        </div>
      </div>

      <!-- 三步进度指示器 -->
      <div v-if="currentStepIndex >= 0" class="progress-section">
        <div
          v-for="(step, i) in progressSteps"
          :key="i"
          class="progress-step"
          :class="{ active: currentStepIndex >= i, done: currentStepIndex > i }"
        >
          <span class="step-icon">{{ step.icon }}</span>
          <span class="step-text">{{ step.text }}</span>
          <span v-if="i < progressSteps.length - 1" class="step-divider">→</span>
        </div>
      </div>

      <!-- 主输入区（支持拖拽和粘贴） -->
      <div
        v-if="!generatedContent"
        class="input-area"
        :class="{ disabled: currentStepIndex >= 0 }"
        @drop.prevent="handleDrop"
        @dragover.prevent
        @paste="handlePaste"
      >
        <a-textarea
          ref="inputRef"
          v-model="userPrompt"
          :placeholder="placeholder"
          :auto-size="{ minRows: 4, maxRows: 8 }"
          style="width: 100%; border: none; background: transparent"
          :disabled="currentStepIndex >= 0"
        />
      </div>

      <!-- 生成内容预览区 -->
      <div v-if="generatedContent" class="preview-section">
        <div class="preview-title">📄 AI 生成内容预览</div>
        <div class="preview-content-wrapper">
          <a-textarea
            v-model="generatedContent"
            :auto-size="{ minRows: 8, maxRows: 15 }"
            style="width: 100%"
          />
        </div>
        <div class="preview-hint">
          💡 您可以直接编辑上述内容，满意后点击「确认采纳」
        </div>
      </div>

      <!-- 快速建议标签 -->
      <div v-if="!generatedContent" class="quick-tags" style="margin-top: 10px">
        <span class="tag-label">💡 快速提示：</span>
        <a-tag
          v-for="tag in quickTags"
          :key="tag"
          class="suggest-tag"
          :color="selectedTag === tag ? 'arcoblue' : ''"
          @click="toggleTag(tag)"
        >
          {{ tag }}
        </a-tag>
      </div>

      <!-- 素材来源区 -->
      <div v-if="!generatedContent" class="source-section" style="margin-top: 16px">
        <div class="source-title">📦 素材来源</div>
        <div class="source-grid">
          <!-- 知识库文件选择 -->
          <div class="source-card">
            <div class="source-card-header">
              <span class="source-label">📂 知识库文件</span>
              <a-switch v-model="useKB" size="small" />
            </div>
            <div v-if="useKB && kbTreeData.length > 0" style="margin-top: 8px">
              <a-tree-select
                v-model="selectedKBFiles"
                :data="kbTreeData"
                placeholder="选择知识库文件（可选）"
                tree-checkable
                allow-search
                style="width: 100%"
                :max-tag-count="3"
              />
            </div>
            <div v-else-if="useKB && kbTreeData.length === 0" style="margin-top: 8px; font-size: 12px; color: #86909c">
              暂无知识库数据
            </div>
          </div>

          <!-- 联网搜索 -->
          <div class="source-card">
            <div class="source-card-header">
              <span class="source-label">🌐 联网搜索</span>
              <a-switch v-model="useWebSearch" size="small" />
            </div>
            <div v-if="useWebSearch" style="margin-top: 8px">
              <div style="font-size: 12px; color: #86909c; margin-bottom: 4px">
                自动从 AI-Pulse 检索相关信源
              </div>
              <a-input
                v-model="webSearchKeyword"
                placeholder="自定义搜索词（可选，默认自动提取）"
                style="width: 100%"
                size="small"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- 上传文件区 -->
      <div v-if="!generatedContent" class="upload-section" style="margin-top: 12px">
        <div class="source-title">📎 附加素材</div>
        <div
          class="upload-zone"
          @drop.prevent="handleDrop"
          @dragover.prevent
        >
          <div class="upload-hint">
            <span class="upload-icon">📄</span>
            <span>拖拽文件到这里，或点击下方按钮上传</span>
          </div>
          <a-button size="mini" @click="triggerUpload">
            选择文件
          </a-button>
          <input
            ref="fileInputRef"
            type="file"
            multiple
            style="display: none"
            @change="handleFileSelect"
          />
        </div>

        <!-- 已附件列表 -->
        <div v-if="attachedFiles.length > 0" class="attached-files" style="margin-top: 8px">
          <div
            v-for="(file, i) in attachedFiles"
            :key="i"
            class="file-chip"
          >
            <span class="file-icon">{{ file.type === 'image' ? '🖼️' : '📄' }}</span>
            <span class="file-name">{{ file.name }}</span>
            <span class="file-size">{{ file.size || '' }}</span>
            <a-button
              type="text"
              size="mini"
              style="color: #999; padding: 0 4px"
              @click="removeFile(i)"
            >
              ✕
            </a-button>
          </div>
        </div>

        <!-- 空状态提示 -->
        <div v-else style="margin-top: 8px; font-size: 12px; color: #c9cdd4; text-align: center; padding: 8px">
          暂无附加文件
        </div>
      </div>

      <!-- 汇总信息 -->
      <div style="margin-top: 12px; padding: 8px 12px; background: #f7f8fa; border-radius: 6px; font-size: 12px; color: #86909c; display: flex; justify-content: space-between">
        <span>
          知识库 {{ useKB ? (selectedKBFiles.length > 0 ? `${selectedKBFiles.length} 个文件` : '全部文件') : '关闭' }}
        </span>
        <span>联网 {{ useWebSearch ? '开启' : '关闭' }}</span>
        <span>附件 {{ attachedFiles.length }} 个</span>
      </div>

      <!-- 底部操作按钮 -->
      <div style="margin-top: 18px; display: flex; justify-content: flex-end; gap: 10px">
        <a-button v-if="!generatedContent" @click="handleCancel">取消</a-button>
        <a-button
          v-if="!generatedContent"
          type="primary"
          :loading="currentStepIndex >= 0"
          @click="handleSubmit"
          size="large"
        >
          🤖 AI 补充
        </a-button>

        <!-- 确认阶段按钮 -->
        <a-button v-if="generatedContent" @click="handleRegenerate">🔄 重新生成</a-button>
        <a-button v-if="generatedContent" type="primary" @click="handleConfirm" size="large">
          ✅ 确认采纳
        </a-button>
      </div>
    </div>
  </a-modal>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  visible: Boolean,
  itemTitle: { type: String, default: '内容补充' },
  defaultPrompt: { type: String, default: '' },
  kbTreeData: { type: Array, default: () => [] },
  issues: { type: Array, default: () => [] },
})

const emit = defineEmits([
  'update:visible',
  'submit',           // 用户点击 AI 补充：{ userPrompt, userFiles, useKB, selectedKBFiles, useWebSearch, webSearchKeyword }
  'confirm',          // 用户点击确认采纳：{ content, userFiles }
])

const dialogVisible = computed({
  get: () => props.visible,
  set: (v) => emit('update:visible', v),
})

const modalTitle = computed(() => {
  if (generatedContent.value) {
    return `📝 预览：${props.itemTitle}`
  }
  return `📝 补充：${props.itemTitle}`
})

// 输入 refs
const inputRef = ref(null)
const fileInputRef = ref(null)
const userPrompt = ref('')
const selectedTag = ref('')
const attachedFiles = ref([])

// 素材开关
const useKB = ref(true)
const useWebSearch = ref(false)
const webSearchKeyword = ref('')
const selectedKBFiles = ref([])

// 生成内容
const generatedContent = ref('')

// 三步进度
const progressSteps = [
  { icon: '🔍', text: '检索知识库' },
  { icon: '🤖', text: 'LLM 推理' },
  { icon: '✅', text: '完成' },
]
const currentStepIndex = ref(-1)  // -1 = 未开始, 0 = step 1, 1 = step 2, 2 = step 3

const quickTags = ['补案例', '补行业案例', '补数据支撑', '精简表达', '写生动', '完善逻辑']

const placeholder = computed(() => {
  if (props.issues.length === 1) {
    return `针对「${props.issues[0].title}」补充内容，或留空让 AI 自动推断...`
  }
  if (props.issues.length > 1) {
    return `针对检测到的 ${props.issues.length} 个问题补充内容，或留空让 AI 自动推断...`
  }
  return '输入你的需求，或留空让 AI 自动推断补充内容...'
})

// 点击快速标签：追加到输入框
function toggleTag(tag) {
  if (selectedTag.value === tag) {
    selectedTag.value = ''
  } else {
    selectedTag.value = tag
    const current = userPrompt.value.trim()
    userPrompt.value = current ? `${current}；${tag}` : tag
  }
}

// 引用问题：追加到输入框
function toggleIssueReference(issue) {
  const issueTitle = issue.title || issue
  const current = userPrompt.value.trim()
  const pattern = new RegExp(`^针对「.+?」[：:]?|；针对「.+?」[：:]?`, 'g')
  let cleaned = current.replace(pattern, '').trim()
  if (cleaned) {
    userPrompt.value = `针对「${issueTitle}」补充内容：${cleaned}`
  } else {
    userPrompt.value = `针对「${issueTitle}」补充内容`
  }
}

// 处理文件拖拽
function handleDrop(e) {
  const files = e.dataTransfer?.files
  if (!files) return
  for (const file of files) {
    readFileContent(file)
  }
}

// 处理粘贴（支持图片）
function handlePaste(e) {
  const items = e.clipboardData?.items
  if (!items) return
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      const blob = item.getAsFile()
      readFileContent(blob)
    }
  }
}

// 触发文件选择
function triggerUpload() {
  fileInputRef.value?.click()
}

function handleFileSelect(e) {
  const files = e.target?.files
  if (!files) return
  for (const file of files) {
    readFileContent(file)
  }
  e.target.value = ''
}

// 读取文件内容
function readFileContent(file) {
  const ext = (file.name || '').toLowerCase()
  const isImage = file.type?.startsWith('image/')
    || ext.endsWith('.png') || ext.endsWith('.jpg') || ext.endsWith('.jpeg')
    || ext.endsWith('.gif') || ext.endsWith('.webp')

  const sizeKB = Math.round((file.size || 0) / 1024)
  const sizeStr = sizeKB > 1024 ? `${(sizeKB / 1024).toFixed(1)} MB` : `${sizeKB} KB`

  if (isImage) {
    attachedFiles.value.push({
      name: file.name || '粘贴图片',
      content: '[图片内容待 OCR 识别]',
      type: 'image',
      size: sizeStr,
    })
    return
  }

  // 文本文件：直接读取
  const reader = new FileReader()
  reader.onload = () => {
    attachedFiles.value.push({
      name: file.name || '上传文件',
      content: reader.result?.toString() || '',
      type: 'text',
      size: sizeStr,
    })
  }
  reader.readAsText(file)
}

function removeFile(idx) {
  attachedFiles.value.splice(idx, 1)
}

// 开始 AI 补充：通知父组件调用 API
async function handleSubmit() {
  currentStepIndex.value = 0  // Step 1: 检索知识库
  emit('submit', {
    userPrompt: userPrompt.value,
    userFiles: attachedFiles.value.map(f => ({
      name: f.name,
      content: f.content,
    })),
    useKB: useKB.value,
    selectedKBFiles: selectedKBFiles.value,
    useWebSearch: useWebSearch.value,
    webSearchKeyword: webSearchKeyword.value,
  })
}

// 外部调用：设置进度（父组件在调用时更新）
function setProgressStep(step) {
  currentStepIndex.value = step
}

// 外部调用：设置生成内容，进入确认阶段
function setGeneratedContent(content) {
  generatedContent.value = content
  currentStepIndex.value = 2  // 完成
}

// 外部调用：失败时重置
function setError() {
  currentStepIndex.value = -1
}

// 重新生成
function handleRegenerate() {
  generatedContent.value = ''
  currentStepIndex.value = -1
}

// 确认采纳
function handleConfirm() {
  emit('confirm', {
    content: generatedContent.value,
    userFiles: attachedFiles.value.map(f => ({
      name: f.name,
      content: f.content,
    })),
  })
  resetState()
  dialogVisible.value = false
}

function handleCancel() {
  resetState()
  dialogVisible.value = false
}

function resetState() {
  userPrompt.value = ''
  selectedTag.value = ''
  attachedFiles.value = []
  useKB.value = true
  useWebSearch.value = false
  webSearchKeyword.value = ''
  selectedKBFiles.value = []
  generatedContent.value = ''
  currentStepIndex.value = -1
}

// 关闭时重置
watch(() => props.visible, (v) => {
  if (!v) {
    resetState()
  }
})

// 暴露方法给父组件
defineExpose({
  setProgressStep,
  setGeneratedContent,
  setError,
})
</script>

<style scoped>
.supplement-dialog {
  font-size: 14px;
}

/* 问题列表区域 */
.issues-section {
  margin-bottom: 12px;
  padding: 10px 12px;
  background: #fff7e6;
  border: 1px solid #ff7d00;
  border-radius: 6px;
}

.issues-title {
  font-size: 12px;
  font-weight: 500;
  color: #ff7d00;
  margin-bottom: 8px;
}

.issues-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.issue-tag {
  cursor: pointer;
  user-select: none;
  transition: transform 0.1s;
}

.issue-tag:hover {
  transform: scale(1.05);
}

/* 三步进度指示器 */
.progress-section {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px;
  margin-bottom: 12px;
  background: #f0f7ff;
  border: 1px solid #165dff;
  border-radius: 6px;
}

.progress-step {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #86909c;
  transition: all 0.3s;
}

.progress-step.active {
  color: #165dff;
  font-weight: 500;
}

.progress-step.done {
  color: #00b42a;
}

.step-icon {
  font-size: 16px;
}

.step-divider {
  margin: 0 4px;
  color: #c9cdd4;
}

/* 输入区域 */
.input-area {
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  padding: 12px;
  background: #fafafa;
  position: relative;
  transition: border-color 0.2s;
}

.input-area:hover {
  border-color: #165dff;
}

.input-area.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 预览区域 */
.preview-section {
  border: 2px solid #165dff;
  border-radius: 8px;
  padding: 12px;
  background: #f0f7ff;
}

.preview-title {
  font-size: 13px;
  font-weight: 500;
  color: #1d2129;
  margin-bottom: 8px;
}

.preview-content-wrapper {
  background: #fff;
  border-radius: 4px;
  padding: 8px;
}

.preview-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #165dff;
  text-align: center;
}

.suggest-tag {
  cursor: pointer;
  font-size: 12px;
  margin-right: 6px;
  margin-bottom: 4px;
}

.suggest-tag:hover {
  opacity: 0.8;
}

.tag-label {
  font-size: 12px;
  color: #86909c;
  margin-right: 6px;
}

/* 素材来源区域 */
.source-section {
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  padding: 12px;
  background: #fff;
}

.source-title {
  font-size: 13px;
  font-weight: 500;
  color: #1d2129;
  margin-bottom: 10px;
}

.source-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.source-card {
  padding: 10px 12px;
  border: 1px solid #e5e6eb;
  border-radius: 6px;
  background: #fafafa;
}

.source-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.source-label {
  font-size: 13px;
  font-weight: 500;
  color: #1d2129;
}

/* 上传区域 */
.upload-section {
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  padding: 12px;
  background: #fff;
}

.upload-zone {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border: 1px dashed #c9cdd4;
  border-radius: 6px;
  background: #fafafa;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}

.upload-zone:hover {
  border-color: #165dff;
  background: #f0f7ff;
}

.upload-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #86909c;
}

.upload-icon {
  font-size: 16px;
}

/* 附件列表 */
.attached-files {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.file-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: #e8f7ff;
  border-radius: 4px;
  font-size: 12px;
  color: #165dff;
  max-width: 100%;
  overflow: hidden;
}

.file-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 160px;
}

.file-size {
  color: #86909c;
  font-size: 11px;
  margin-left: 2px;
}

.file-icon {
  font-size: 14px;
}
</style>
