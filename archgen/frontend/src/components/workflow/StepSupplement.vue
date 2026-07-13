<template>
  <div class="step-content">
    <a-card>
      <!-- ===== 顶部：标题 ===== -->
      <div class="section-title">
        <span class="title-icon">📝</span>
        <span class="title-text">写作方向</span>
      </div>

      <!-- 选题方向 -->
      <a-alert type="info" style="margin-bottom: 20px; font-size: 14px">
        <template #title>
          <span style="font-weight: 600">选题方向：</span>{{ props.selectedDirection?.name || '未选择' }}
        </template>
      </a-alert>

      <!-- ===== 素材管理区 ===== -->
      <div class="section-title" style="margin-top: 24px">
        <span class="title-icon">📦</span>
        <span class="title-text">当前素材（{{ totalItemCount > 0 ? totalItemCount + ' 条' : '0 条' }}）</span>
      </div>

      <a-card :bordered="true" style="margin-bottom: 20px; background: #fafbfc">
        <!-- MCP 摘要（可折叠） -->
        <div v-if="props.mcpSummary" style="margin-bottom: 16px">
          <a-space style="margin-bottom: 4px">
            <a-typography-text type="secondary" style="font-size: 12px">MCP 素材摘要</a-typography-text>
            <a-tag v-if="summaryExpanded" size="mini" color="arcoblue" @click="summaryExpanded = !summaryExpanded" style="cursor: pointer">收起</a-tag>
            <a-tag v-else size="mini" @click="summaryExpanded = !summaryExpanded" style="cursor: pointer">展开</a-tag>
          </a-space>
          <div
            class="mcp-summary-box"
            :class="{ 'summary-collapsed': !summaryExpanded }"
          >
            {{ props.mcpSummary }}
          </div>
        </div>

        <!-- 按类型分组的素材列表（网格布局） -->
        <div v-for="(group, groupKey) in groupedFiles" :key="groupKey" style="margin-bottom: 12px">
          <div style="font-size: 12px; font-weight: 600; margin-bottom: 6px; color: #4e5969">
            <span v-if="groupKey === 'kb'">📂 知识库文件（{{ group.items.length }} 篇）</span>
            <span v-else-if="groupKey === 'radar'">📡 雷达匹配 — 选题方向相关（{{ group.items.length }} 篇）</span>
            <span v-else-if="groupKey === 'inference'">🤖 AI 推断补充（{{ group.items.length }} 条）</span>
            <span v-else-if="groupKey === 'ai_pulse'">🌐 联网检索（{{ group.items.length }} 条）</span>
            <span v-else-if="groupKey === 'ai_supplement'">🆕 AI 补充素材（{{ group.items.length }} 篇）</span>
            <span v-else-if="groupKey === 'upload'">📎 上传附件（{{ group.items.length }} 个）</span>
          </div>
          <div class="file-grid-container" :class="'grid-' + groupKey">
            <div
              v-for="(item, idx) in group.items"
              :key="idx"
              class="file-grid-item"
              :class="'item-' + groupKey"
              :title="item.name || item.title || item.content"
            >
              <span class="file-grid-icon">
                <span v-if="groupKey === 'kb'">📄</span>
                <span v-else-if="groupKey === 'radar'">📡</span>
                <span v-else-if="groupKey === 'inference'">💡</span>
                <span v-else-if="groupKey === 'ai_pulse'">🌐</span>
                <span v-else-if="groupKey === 'ai_supplement'">🆕</span>
                <span v-else>📎</span>
              </span>
              <a-link class="file-grid-name" @click="previewItem(groupKey, idx)">
                {{ truncateFileName(item.name || item.title || item.content || '', 30) }}
              </a-link>
              <a-button
                type="text"
                size="mini"
                status="danger"
                class="file-grid-delete"
                @click.stop="removeItem(groupKey, idx)"
              >
                ×
              </a-button>
            </div>
          </div>
        </div>

        <div v-if="totalItemCount === 0" style="color: #86909c; font-size: 13px; text-align: center; padding: 12px">
          暂无素材，请点击 AI 智能补充
        </div>

        <!-- 操作按钮（同行） -->
        <div style="margin-top: 20px; text-align: center">
          <a-space size="large">
            <a-button
              type="primary"
              size="large"
              @click="props.openStep2SupplementDialog"
            >
              🚀 AI 智能补充
            </a-button>
            <a-button
              type="outline"
              size="large"
              status="success"
              :loading="props.aiSupplementMaterialsLoading"
              @click="props.aiSupplementMaterials"
            >
              📥 AI 补充素材
            </a-button>
            <a-button
              type="outline"
              size="large"
              status="warning"
              :loading="props.preCheckLoading"
              @click="props.runPreCheck"
            >
              {{ preCheckButtonText }}
            </a-button>
          </a-space>
          <div style="font-size: 12px; color: #86909c; margin-top: 6px">
            可以拖拽文件、粘贴截图，也可以直接输入需求。补充内容会追加到素材池，不会替换已有素材。
          </div>
        </div>
      </a-card>

      <!-- ===== 补充内容展示（AI 补充后） ===== -->
      <div v-if="props.supplement2Text" style="margin-top: 20px">
        <a-card :bordered="true" style="border-left: 3px solid #165dff">
          <template #title>
            <a-space>
              <span>📄 已补充内容</span>
              <a-tag color="arcoblue" size="small">{{ props.supplementConfirmed ? '已确认' : '待确认' }}</a-tag>
            </a-space>
          </template>
          <div class="supplement-rich-text" style="font-size: 14px; line-height: 1.8; max-height: 400px; overflow-y: auto" v-html="props.supplement2Html"></div>
        </a-card>
      </div>

      <!-- 检测结果 -->
      <div v-if="props.preCheckResult && !props.preCheckLoading" style="margin-top: 16px">

        <!-- ===== 📡 素材雷达面板（来自选题阶段） ===== -->
        <div v-if="props.preCheckResult.radar_basis" class="radar-basis-panel">
          <div class="radar-basis-header">
            📡 素材雷达（来自选题阶段）
            <span class="radar-basis-score">
              {{ props.preCheckResult.radar_basis.signal_report?.good_count || 0 }}/{{ props.preCheckResult.radar_basis.signal_report?.total_count || 5 }} 就绪
            </span>
          </div>
          <div class="radar-signal-grid">
            <div
              v-for="s in props.preCheckResult.radar_basis.signal_details"
              :key="s.label"
              class="radar-signal-item"
              :class="{ 'radar-signal-ok': s.ok, 'radar-signal-ng': !s.ok }"
            >
              <span class="radar-signal-icon">{{ s.ok ? '✅' : '⚠️' }}</span>
              <span class="radar-signal-label">{{ s.label }}</span>
              <span class="radar-signal-detail">{{ s.detail }}</span>
            </div>
          </div>
          <div v-if="props.preCheckResult.radar_basis.deficiency_details?.length" class="radar-deficiency-list">
            <div class="radar-deficiency-title">待补充项：</div>
            <div v-for="d in props.preCheckResult.radar_basis.deficiency_details" :key="d.item" class="radar-deficiency-item">
              • <strong>{{ d.item }}</strong>：{{ d.explanation }}
            </div>
          </div>
        </div>

        <!-- ===== 💡 写作建议 ===== -->
        <div v-if="props.preCheckResult.writing_suggestions?.length" class="writing-suggestions-panel">
          <div class="suggestions-header" @click="suggestionsExpanded = !suggestionsExpanded" style="cursor: pointer">
            💡 写作建议 ({{ props.preCheckResult.writing_suggestions.length }})
            <span style="font-size: 12px; color: #86909c; margin-left: 8px">{{ suggestionsExpanded ? '收起' : '展开' }}</span>
          </div>
          <div v-if="suggestionsExpanded" class="suggestions-list">
            <div v-for="(sug, si) in props.preCheckResult.writing_suggestions" :key="si" class="suggestion-item">
              {{ si + 1 }}. {{ sug }}
            </div>
          </div>
        </div>

        <!-- ===== 已有补充状态提示 ===== -->
        <a-alert
          v-if="props.preCheckResult.all_recurring"
          type="success"
          style="margin-bottom: 12px"
          :title="'AI补充已应用，内容完整性良好'"
        />

        <div v-if="props.preCheckResult.issues && props.preCheckResult.issues.length > 0" class="issues-block">
          <div style="font-weight: 600; color: #1d2129; margin-bottom: 8px">
            {{ props.preCheckResult.all_recurring ? '💡 优化建议' : '⚠️ 还需细化' }}
          </div>
          <div
            v-for="(issue, ii) in props.preCheckResult.issues"
            :key="ii"
            class="issue-card"
            :style="{
              opacity: issue.recurring ? 0.75 : 1,
              borderLeft: issue.recurring ? '3px solid #c9cdd4' : '3px solid #f53f3f',
            }"
          >
            <div class="issue-header">
              <span>{{ issue.recurring ? '↻' : issue.type === 'error' ? '🔴' : issue.type === 'warning' ? '🟡' : '🟢' }}</span>
              <strong>{{ issue.title }}</strong>
              <a-tag v-if="issue.recurring" size="mini" color="gray">已补充</a-tag>
              <a-tag v-else-if="issue.type === 'error'" size="mini" color="red">高优</a-tag>
              <a-tag v-else-if="issue.type === 'warning'" size="mini" color="orange">中优</a-tag>
            </div>
            <div class="issue-desc" v-html="renderMarkdown(issue.description)"></div>
          </div>

          <!-- 完整度 — 按 status 分支渲染 -->
          <div style="margin-top: 12px; padding-top: 8px; border-top: 1px dashed #e5e6eb; font-size: 12px; color: #86909c">
            <template v-if="props.preCheckResult.all_recurring">
              ✅ 补充已应用，可以直接进入下一步
            </template>
            <template v-else-if="props.preCheckResult.status === 'initializing'">
              素材基础评分：{{ props.preCheckResult.score }}（来自选题雷达）
            </template>
            <template v-else-if="props.preCheckResult.status === 'pending'">
              {{ props.preCheckResult.writing_progress || '已检测到分析内容，需选定写作角度后进行质量评估' }}
            </template>
            <template v-else>
              内容完整度：{{ props.preCheckResult.score }}%
              （{{ props.preCheckResult.issues.filter(i => i.type === 'error').length }}项需优先处理）
            </template>
          </div>
        </div>

        <!-- 没问题 -->
        <div v-else style="padding: 20px 24px; background: linear-gradient(135deg, #00b42a 0%, #009a24 100%); border-radius: 8px; color: #fff; text-align: center; font-size: 16px; font-weight: 500; box-shadow: 0 2px 8px rgba(0, 180, 42, 0.2);">
          <div style="font-size: 24px; margin-bottom: 6px;">✅</div>
          <div>信息充足，可直接进入槽位工作台</div>
        </div>
      </div>

      <!-- ===== 预览弹窗 ===== -->
      <a-modal
        v-model:visible="previewModalVisible"
        :title="previewTitle"
        width="700px"
        :footer="false"
      >
        <div style="max-height: 60vh; overflow-y: auto; font-size: 14px; line-height: 1.8; white-space: pre-wrap">
          {{ previewContent }}
        </div>
      </a-modal>

      <!-- ===== 底部操作 ===== -->
      <div style="margin-top: 32px; text-align: center; padding: 20px; border-top: 1px solid #e5e6eb">
        <a-space size="large">
          <a-button
            type="primary"
            size="large"
            status="success"
            :disabled="totalItemCount === 0"
            @click="props.confirmSupplementAndProceed"
          >
            ✅ 确认补充完毕，进入槽位工作台
          </a-button>
          <a-button
            size="large"
            @click="props.skipSupplement2"
          >
            ⏭ 跳过，直接进入
          </a-button>
        </a-space>
        <div v-if="totalItemCount === 0" style="margin-top: 8px; font-size: 12px; color: #c9cdd4">
          请先添加素材或点击跳过
        </div>
        <div v-if="props.supplementConfirmed" style="margin-top: 8px; font-size: 12px; color: #00b42a">
          ✅ 补充已确认
        </div>
      </div>

      <!-- ===== AI 补充对话框 ===== -->
      <SupplementDialog
        :ref="setStep2DialogRef"
        :visible="props.step2SupplementDialogVisible"
        @update:visible="$emit('update:step2-supplement-dialog-visible', $event)"
        item-title="内容补充"
        :kb-tree-data="props.kbTreeData"
        :issues="props.preCheckResult?.issues || []"
        @submit="props.handleStep2SupplementSubmit"
        @confirm="props.handleStep2SupplementConfirm"
      />
    </a-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { marked } from 'marked'
import SupplementDialog from '../SupplementDialog.vue'

const props = defineProps({
  mcpSummary: { type: String, default: '' },
  mcpFiles: { type: Array, default: () => [] },
  selectedDirection: { type: Object, default: null },
  preCheckLoading: { type: Boolean, default: false },
  preCheckResult: { type: Object, default: null },
  supplement2Text: { type: String, default: '' },
  supplement2Html: { type: String, default: '' },
  supplementConfirmed: { type: Boolean, default: false },
  pendingSupplementData: { type: Object, default: null },
  expandedIssues: { type: Object, default: () => ({ has: () => false }) },
  kbTreeData: { type: Array, default: () => [] },
  materialPool: { type: Array, default: () => [] },
  step2SupplementDialogVisible: { type: Boolean, default: false },
  runPreCheck: { type: Function, default: () => {} },
  confirmSupplementAndProceed: { type: Function, default: () => {} },
  skipSupplement2: { type: Function, default: () => {} },
  handleStep2SupplementSubmit: { type: Function, default: () => {} },
  handleStep2SupplementConfirm: { type: Function, default: () => {} },
  openStep2SupplementDialog: { type: Function, default: () => {} },
  openSupplementDialog: { type: Function, default: () => {} },
  toggleIssueExpand: { type: Function, default: () => {} },
  aiSupplementMaterials: { type: Function, default: () => {} },
  aiSupplementMaterialsLoading: { type: Boolean, default: false },
})

const suggestionsExpanded = ref(true)

const preCheckButtonText = computed(() => {
  const st = props.preCheckResult?.status
  if (st === 'initializing' || !st) return '🔍 扫描素材库'
  if (st === 'pending') return '📦 核验素材库存'
  return '📊 评估内容质量'
})

function renderMarkdown(text) {
  if (!text) return ''
  try {
    return marked.parse(text, { breaks: true, async: false })
  } catch {
    return text.replace(/\n/g, '<br>')
  }
}

const emit = defineEmits([
  'update:step2-supplement-dialog-visible',
  'remove-material',  // { type: 'kb'|'inference'|'ai_pulse', idx: number }
])

const step2SupplementDialogRef = ref(null)
const previewModalVisible = ref(false)
const previewTitle = ref('')
const previewContent = ref('')
const summaryExpanded = ref(false)

// 本地状态：可管理的素材池（合并 mcpFiles + materialPool）
const localMaterials = ref([])

// 初始化本地素材（从 props 合并）
watch([() => props.mcpFiles, () => props.materialPool], ([newFiles, newPool]) => {
  const merged = []
  // 知识库文件
  if (newFiles?.length > 0) {
    merged.push(...newFiles.map(f => ({
      type: 'kb',
      name: typeof f === 'string' ? f : f.name,
      content: typeof f === 'string' ? '' : f.content,
      source: f,
    })))
  }
  // AI 补充的素材池
  if (newPool?.length > 0) {
    merged.push(...newPool.map(item => ({
      type: item.type === 'kb_file' ? 'kb' : item.type === 'radar_matched' ? 'radar' : item.type === 'ai_pulse' ? 'ai_pulse' : item.type === 'ai_supplement' ? 'ai_supplement' : 'inference',
      name: item.name || item.title,
      content: item.content || item.summary,
      source: item,
    })))
  }
  localMaterials.value = merged
}, { immediate: true, deep: true })

// 按类型分组展示
const groupedFiles = computed(() => {
  const groups = {
    kb: { items: [] },
    radar: { items: [] },
    inference: { items: [] },
    ai_pulse: { items: [] },
    ai_supplement: { items: [], label: '🤖 AI 补充素材', icon: '🆕' },
    upload: { items: [] },
  }
  for (const item of localMaterials.value) {
    if (groups[item.type]) {
      groups[item.type].items.push(item)
    }
  }
  // 过滤空组
  return Object.fromEntries(Object.entries(groups).filter(([_, g]) => g.items.length > 0))
})

const totalItemCount = computed(() => localMaterials.value.length)

function setStep2DialogRef(el) {
  step2SupplementDialogRef.value = el
}

function previewItem(type, idx) {
  const group = groupedFiles.value[type]
  if (!group) return
  const item = group.items[idx]
  if (!item) return
  if (type === 'kb') {
    previewTitle.value = item.name || '知识库文件'
    previewContent.value = item.content || '（暂无内容预览）'
  } else if (type === 'radar') {
    previewTitle.value = item.name || '雷达匹配文档'
    previewContent.value = item.content || ''
  } else if (type === 'inference') {
    previewTitle.value = 'AI 推断补充'
    previewContent.value = item.content || ''
  } else if (type === 'ai_pulse') {
    previewTitle.value = item.name || 'AI-Pulse 文章'
    previewContent.value = item.content || ''
  }
  previewModalVisible.value = true
}

function removeItem(type, idx) {
  let counter = 0
  for (let i = 0; i < localMaterials.value.length; i++) {
    if (localMaterials.value[i].type === type) {
      if (counter === idx) {
        localMaterials.value.splice(i, 1)
        emit('remove-material', { type, idx })
        return
      }
      counter++
    }
  }
}

function truncateFileName(name, maxLen) {
  if (!name) return ''
  name = String(name)
  if (name.length <= maxLen) return name
  const ext = name.lastIndexOf('.') > 0 ? name.slice(name.lastIndexOf('.')) : ''
  const base = name.slice(0, name.lastIndexOf('.') > 0 ? name.lastIndexOf('.') : name.length)
  return base.slice(0, maxLen - ext.length - 3) + '...' + ext
}

// 暴露 ref 给父组件
defineExpose({ step2SupplementDialogRef })

// 旧函数（兼容）
function previewFile(idx) {
  previewItem('kb', idx)
}
function removeFile(idx) {
  removeItem('kb', idx)
}
function previewPoolMaterial(idx) {
  // 向后兼容
}

// 进入页面后，延迟自动检测（等 props 稳定）
onMounted(() => {
  if (props.mcpSummary && !props.preCheckResult && !props.preCheckLoading && typeof props.runPreCheck === 'function') {
    // 延迟执行，避免在组件挂载过程中触发异步导致状态异常
    setTimeout(() => {
      try { props.runPreCheck() } catch (e) { console.warn('自动检测失败:', e) }
    }, 500)
  }
})
</script>

<style scoped>
.radar-basis-panel {
  background: linear-gradient(135deg, #f0f5ff 0%, #e8f4f8 100%);
  border: 1px solid #d0e1fd;
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 16px;
}
.radar-basis-header {
  font-weight: 600;
  font-size: 14px;
  color: #1d2129;
  margin-bottom: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.radar-basis-score {
  font-size: 12px;
  color: #165dff;
  background: #e8f0ff;
  padding: 2px 10px;
  border-radius: 12px;
}
.radar-signal-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}
.radar-signal-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
}
.radar-signal-ok {
  background: #e8faf0;
  color: #00b42a;
}
.radar-signal-ng {
  background: #fff7e8;
  color: #ff7d00;
}
.radar-signal-icon { font-size: 14px; }
.radar-signal-label { font-weight: 500; }
.radar-signal-detail { color: #86909c; font-size: 11px; }

.radar-deficiency-list {
  background: #fff;
  border-radius: 6px;
  padding: 10px 14px;
  font-size: 12px;
  color: #4e5969;
}
.radar-deficiency-title { font-weight: 600; margin-bottom: 4px; color: #ff7d00; }
.radar-deficiency-item { margin-top: 3px; line-height: 1.6; }

.writing-suggestions-panel {
  background: #fafbfc;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 14px;
}
.suggestions-header {
  font-weight: 600;
  font-size: 13px;
  color: #1d2129;
  user-select: none;
}
.suggestions-list { margin-top: 8px; }
.suggestion-item {
  font-size: 12px;
  color: #4e5969;
  line-height: 1.8;
  padding-left: 4px;
}
</style>

<style scoped>
.step-content {
  min-height: 400px;
  width: 100%;
  max-width: 100%;
}

.step-content :deep(.arco-card) {
  width: 100%;
  max-width: 100%;
}

/* 区块大标题 */
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.title-icon {
  font-size: 22px;
}

.title-text {
  font-size: 18px;
  font-weight: 700;
  color: #1d2129;
}

/* MCP 摘要 */
.mcp-summary-box {
  max-height: 300px;
  overflow-y: auto;
  font-size: 13px;
  line-height: 1.6;
  color: #4e5969;
  white-space: pre-wrap;
  padding: 10px 12px;
  background: #fff;
  border-radius: 6px;
  border: 1px solid #e5e6eb;
  margin-top: 6px;
  transition: max-height 0.25s ease;
}

.mcp-summary-box.summary-collapsed {
  max-height: 72px;
  overflow-y: hidden;
}

/* 文件网格列表 */
.file-grid-container {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px 8px;
}

.file-grid-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 8px;
  background: #fff;
  border-radius: 6px;
  border: 1px solid #e5e6eb;
  font-size: 12px;
  transition: all 0.15s;
}

.file-grid-item:hover {
  border-color: #165dff;
  background: #f0f7ff;
}

.file-grid-icon {
  font-size: 14px;
  flex-shrink: 0;
}

.file-grid-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
}

.file-grid-delete {
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.15s;
  padding: 0 4px;
  min-width: 20px;
  height: 20px;
  line-height: 20px;
}

.file-grid-item:hover .file-grid-delete {
  opacity: 1;
}

/* 不同类型的配色 */
.file-grid-item.item-kb {
  border-left: 3px solid #00b42a;
}
.file-grid-item.item-kb:hover {
  border-color: #00b42a;
  background: #e8ffef;
}

.file-grid-item.item-inference {
  border-left: 3px solid #165dff;
}
.file-grid-item.item-inference:hover {
  border-color: #165dff;
  background: #e8f3ff;
}

.file-grid-item.item-ai_pulse {
  border-left: 3px solid #ff7d00;
}
.file-grid-item.item-ai_pulse:hover {
  border-color: #ff7d00;
  background: #fff7e8;
}

.file-grid-item.item-upload {
  border-left: 3px solid #f53f3f;
}
.file-grid-item.item-upload:hover {
  border-color: #f53f3f;
  background: #ffe8e8;
}

/* 旧列表样式（保留删除） */
.file-list {
  max-height: 250px;
  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  transition: background 0.15s;
}

.file-item:hover {
  background: #f0f7ff;
}

.file-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.file-name {
  flex: 1;
  font-size: 13px;
  word-break: break-all;
}

.file-delete-btn {
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.15s;
}

.file-item:hover .file-delete-btn {
  opacity: 1;
}

/* 检测结果 */
.issues-block {
  background: #fffbe6;
  border: 1px solid #ffe58f;
  border-radius: 8px;
  padding: 16px;
}

.issue-card {
  margin-bottom: 8px;
  padding: 10px 12px;
  background: #fff;
  border-radius: 6px;
}

.issue-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  flex-wrap: wrap;
}

.issue-desc {
  font-size: 12px;
  color: #86909c;
  margin-top: 4px;
  padding-left: 22px;
}

/* marked 富文本 */
.supplement-rich-text h1,
.supplement-rich-text h2,
.supplement-rich-text h3 {
  margin: 12px 0 8px;
  font-weight: 600;
  color: #1d2129;
}
.supplement-rich-text p {
  margin: 6px 0;
  line-height: 1.8;
}
.supplement-rich-text ul,
.supplement-rich-text ol {
  margin: 6px 0;
  padding-left: 20px;
}
.supplement-rich-text li {
  margin: 4px 0;
  line-height: 1.6;
}
.supplement-rich-text strong {
  font-weight: 600;
  color: #1d2129;
}
.supplement-rich-text code {
  padding: 2px 6px;
  background: #f7f8fa;
  border-radius: 3px;
  font-size: 13px;
  color: #f53f3f;
}
.supplement-rich-text pre {
  margin: 8px 0;
  padding: 12px;
  background: #f7f8fa;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 13px;
}
.supplement-rich-text blockquote {
  margin: 8px 0;
  padding: 8px 16px;
  border-left: 4px solid #165dff;
  background: #f0f7ff;
  color: #4e5969;
}
</style>
