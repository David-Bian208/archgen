<template>
  <div class="source-tag-filter">
    <a-alert v-if="validationResult" :type="validationResult.valid_count === validationResult.total_count ? 'success' : 'warning'" :show-icon="false">
      <template #title>
        来源验证结果：{{ validationResult.valid_count }} 个有效，{{ validationResult.filtered_count }} 个已过滤
      </template>
    </a-alert>

    <div class="blocks-container">
      <div 
        v-for="(block, index) in filteredBlocks" 
        :key="index" 
        class="content-block"
        :class="{'filtered-block': !block.is_valid}"
      >
        <div class="block-header">
          <a-tag :color="getSourceTagColor(block.source_tag)" size="small">
            {{ getSourceTagLabel(block.source_tag) }}
          </a-tag>
          <a-tag v-if="!block.is_valid" color="red" size="small">已过滤</a-tag>
          <a-tag v-else color="green" size="small">有效</a-tag>
        </div>

        <div class="block-content">
          <div v-if="block.is_valid" v-text="renderBlockContent(block)"></div>
          <div v-else class="filtered-warning">
            ⚠️ 此段落无有效来源标签，已过滤
            <span v-if="block.warning">{{ block.warning }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="actions">
      <a-button @click="toggleStrictMode">
        {{ strictMode ? '切换到宽松模式' : '切换到严格模式' }}
      </a-button>
      <a-button type="primary" @click="revalidate">重新验证</a-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { validateSourceTags } from '../utils/api.js'

const props = defineProps({
  content: {
    type: String,
    required: true,
  },
  strictMode: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:strictMode'])

const validationResult = ref(null)
const loading = ref(false)
const strictMode = ref(props.strictMode)

const filteredBlocks = computed(() => {
  if (!validationResult.value?.blocks) return []
  return validationResult.value.blocks
})

async function validate() {
  if (!props.content) return
  
  loading.value = true
  try {
    const res = await validateSourceTags(props.content, strictMode.value)
    if (res.data.code === 0) {
      validationResult.value = res.data.data
    }
  } catch (err) {
    console.error('source_tag 验证失败:', err)
  } finally {
    loading.value = false
  }
}

function getSourceTagLabel(tag) {
  if (!tag) return '无标签'
  if (tag.startsWith('local:')) return '知识库'
  if (tag.startsWith('ai_pulse:')) return 'AI-Pulse'
  if (tag.startsWith('user_input:')) return '用户补充'
  if (tag.startsWith('ai_inferred:')) return 'AI 推断'
  return tag
}

function getSourceTagColor(tag) {
  if (!tag) return 'gray'
  if (tag.startsWith('local:')) return 'blue'
  if (tag.startsWith('ai_pulse:')) return 'purple'
  if (tag.startsWith('user_input:')) return 'green'
  if (tag.startsWith('ai_inferred:')) return 'orange'
  return 'gray'
}

function renderBlockContent(block) {
  if (!block.rendered_content) return ''
  // 简单将 Markdown 转为 HTML（实际项目中应使用 marked 等库）
  return block.rendered_content
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\n/g, '<br>')
}

async function revalidate() {
  await validate()
}

function toggleStrictMode() {
  strictMode.value = !strictMode.value
  emit('update:strictMode', strictMode.value)
  validate()
}

// 自动验证
validate()
</script>

<style scoped>
.source-tag-filter {
  padding: 16px;
}

.blocks-container {
  margin-top: 16px;
}

.content-block {
  border: 1px solid #e5e6eb;
  border-radius: 4px;
  margin-bottom: 12px;
  padding: 12px;
  background: #fff;
}

.content-block.filtered-block {
  background: #f5f5f5;
  opacity: 0.7;
}

.block-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.block-content {
  line-height: 1.6;
}

.filtered-warning {
  color: #999;
  font-style: italic;
  padding: 8px;
  background: #fafafa;
  border-radius: 4px;
}

.actions {
  margin-top: 16px;
  display: flex;
  gap: 8px;
}
</style>
