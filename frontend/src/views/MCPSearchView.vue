<template>
  <div class="mcp-search">
    <a-page-header title="知识库检索" @back="$router.push('/')">
    </a-page-header>

    <!-- 搜索区 -->
    <a-card class="search-card">
      <template #title>
        <div class="card-title">
          <icon-search />
          <span>筛选条件</span>
        </div>
      </template>
      
      <a-space direction="vertical" style="width: 100%" :size="16">
        <!-- 关键词 -->
        <div>
          <a-typography-text style="font-size: 13px; color: #86909c; display: block; margin-bottom: 8px">
            关键词（可选，为空则自动推荐）
          </a-typography-text>
          <a-input-search
            v-model="topic"
            placeholder="例如：Agent、商业模式、AI 工具..."
            size="large"
          >
            <template #prefix>
              <icon-search />
            </template>
          </a-input-search>
        </div>
        
        <!-- 时间范围 -->
        <div>
          <a-typography-text style="font-size: 13px; color: #86909c; display: block; margin-bottom: 8px">
            时间范围（可选，多选）
          </a-typography-text>
          <a-checkbox-group v-model="timeFilters" :options="timeOptions" />
        </div>

        <!-- 分类筛选 -->
        <div>
          <a-typography-text style="font-size: 13px; color: #86909c; display: block; margin-bottom: 8px">
            内容分类（可选，多选，基于 AI Pulse 分类体系）
          </a-typography-text>
          <a-checkbox-group v-model="categoryFilters" :options="categoryOptions" />
        </div>
        
        <!-- 文件夹选择 -->
        <div v-if="availableFolders.length > 0">
          <a-typography-text style="font-size: 13px; color: #86909c; display: block; margin-bottom: 8px">
            检索范围（可多选）
          </a-typography-text>
          <a-checkbox-group v-model="selectedFolders" :options="folderOptions" />
        </div>

        <!-- 搜索按钮 -->
        <div>
          <a-button type="primary" size="large" long :loading="searching" @click="handleSearch">
            <icon-search /> {{ topic ? '搜索并推荐题材' : '自动推荐写作题材' }}
          </a-button>
        </div>
      </a-space>
    </a-card>

    <!-- 快捷入口 -->
    <a-card class="quick-card">
      <template #title>
        <div class="card-title">
          <icon-bulb />
          <span>快捷搜索</span>
        </div>
      </template>
      <a-space wrap>
        <a-button size="small" @click="quickSearch('Agent')">Agent</a-button>
        <a-button size="small" @click="quickSearch('商业模式')">商业模式</a-button>
        <a-button size="small" @click="quickSearch('AI 工具')">AI 工具</a-button>
        <a-button size="small" @click="quickSearch('个人成长')">个人成长</a-button>
        <a-button size="small" @click="quickSearch('产品设计')">产品设计</a-button>
      </a-space>
    </a-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { IconSearch, IconBulb } from '@arco-design/web-vue/es/icon'
import { getCategories } from '../utils/api'

const router = useRouter()

const topic = ref('')
const searching = ref(false)
const timeFilters = ref([])
const categoryFilters = ref([])

const timeOptions = [
  { label: '今天', value: 'today' },
  { label: '本周', value: 'week' },
  { label: '最近 30 天', value: 'month' },
]

const categoryOptions = ref([])

const availableFolders = computed(() => {
  const settings = localStorage.getItem('archgen_settings')
  if (settings) {
    try {
      const parsed = JSON.parse(settings)
      return (parsed.knowledgeFolders || []).filter(f => f.status === 'connected')
    } catch (e) {
      return []
    }
  }
  return []
})

const selectedFolders = ref([])
const folderOptions = computed(() => {
  return availableFolders.value.map(f => ({
    label: f.path,
    value: f.path,
  }))
})

onMounted(async () => {
  // 默认全选文件夹
  if (availableFolders.value.length > 0 && selectedFolders.value.length === 0) {
    selectedFolders.value = availableFolders.value.map(f => f.path)
  }
  
  // 加载分类列表
  try {
    const res = await getCategories()
    if (res.data.code === 0) {
      categoryOptions.value = Object.entries(res.data.data).map(([key, val]) => ({
        label: val.name,
        value: key,
      }))
    }
  } catch (e) {
    // 分类加载失败不影响使用
  }
})

const quickSearch = (kw) => {
  topic.value = kw
  handleSearch()
}

const handleSearch = async () => {
  const folders = selectedFolders.value.length > 0
    ? selectedFolders.value
    : availableFolders.value.map(f => f.path)

  if (folders.length === 0) {
    Message.warning('请先在设置页面绑定知识库文件夹')
    return
  }

  // 如果全空（无关键词、无分类、无时间筛选），直接跳转自动推荐
  if (!topic.value.trim() && categoryFilters.value.length === 0 && timeFilters.value.length === 0) {
    const params = new URLSearchParams({
      folders: JSON.stringify(folders),
    })
    router.push(`/topic-suggest?${params.toString()}`)
    return
  }

  searching.value = true

  try {
    const params = new URLSearchParams({
      topic: topic.value.trim(),
      folders: JSON.stringify(folders),
      categories: JSON.stringify(categoryFilters.value),
      timeRange: timeFilters.value[0] || 'all',
    })
    router.push(`/topic-suggest?${params.toString()}`)
  } catch (error) {
    Message.error('搜索失败: ' + error.message)
  } finally {
    searching.value = false
  }
}
</script>

<style scoped>
.mcp-search {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
}
.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}
.search-card {
  margin-bottom: 20px;
}
.quick-card {
  margin-bottom: 20px;
}
</style>
