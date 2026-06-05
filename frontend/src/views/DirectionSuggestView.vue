<template>
  <div class="direction-suggest-view">
    <a-page-header title="选择写作方向" @back="$router.push('/mcp-search')">
      <template #extra>
        <a-steps :current="2" :max="4" style="width: 300px">
          <a-step>检索</a-step>
          <a-step>方向</a-step>
          <a-step>框架</a-step>
          <a-step>数据</a-step>
        </a-steps>
      </template>
    </a-page-header>

    <!-- 资料信息卡片 -->
    <a-card class="info-card">
      <template #title>
        <div class="card-title">
          <icon-folder />
          <span>当前资料</span>
        </div>
      </template>
      <a-space direction="vertical" style="width: 100%" :size="8">
        <div class="info-row">
          <span class="info-label">关键词</span>
          <span class="info-value">{{ appStore.mcpResult?.topic || '-' }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">资料数量</span>
          <span class="info-value">{{ appStore.mcpResult?.file_count || 0 }} 篇</span>
        </div>
        <div class="info-row">
          <span class="info-label">来源文件</span>
          <span class="info-value">
            <a-tag v-for="(f, i) in appStore.mcpResult?.source_files || []" :key="i" size="small">{{ f }}</a-tag>
          </span>
        </div>
      </a-space>
    </a-card>

    <!-- 身份定位提示 -->
    <a-card v-if="personaInfo" class="persona-card">
      <template #title>
        <div class="card-title">
          <icon-user />
          <span>身份定位</span>
        </div>
      </template>
      <template #extra>
        <a-button type="text" size="small" @click="$router.push('/persona')">
          <icon-settings /> 编辑
        </a-button>
      </template>
      <div class="persona-grid" v-if="parsedPersona">
        <div class="persona-item">
          <span class="persona-label">我是谁</span>
          <span class="persona-value">{{ parsedPersona.who_am_i || '-' }}</span>
        </div>
        <div class="persona-item">
          <span class="persona-label">目标读者</span>
          <span class="persona-value">{{ parsedPersona.target_audience || '-' }}</span>
        </div>
        <div class="persona-item">
          <span class="persona-label">专业领域</span>
          <span class="persona-value">{{ parsedPersona.expertise || '-' }}</span>
        </div>
        <div class="persona-item">
          <span class="persona-label">写作风格</span>
          <span class="persona-value">{{ parsedPersona.style || '-' }}</span>
        </div>
      </div>
      <div v-else class="persona-content" v-html="renderedPersona"></div>
    </a-card>

    <!-- 方向建议列表 -->
    <a-card class="direction-card">
      <template #title>
        <div class="card-title">
          <icon-bulb />
          <span>写作方向建议</span>
        </div>
      </template>
      <template #extra>
        <a-typography-text type="secondary" style="font-size: 13px">
          根据资料内容分析，为您推荐以下写作方向
        </a-typography-text>
      </template>

      <a-spin :loading="loading">
        <div class="direction-list">
          <div
            v-for="(dir, index) in directions"
            :key="index"
            class="direction-item"
            :class="{ selected: selectedDirection === index }"
            @click="selectDirection(index)"
          >
            <div class="direction-header">
              <div class="direction-rank">{{ index + 1 }}</div>
              <div class="direction-info">
                <h3>{{ dir.name }}</h3>
                <p class="direction-desc">{{ dir.description }}</p>
              </div>
              <a-tag v-if="dir.confidence_label" :color="dir.confidence_color" class="coverage-tag" size="medium">
                {{ dir.confidence_label }}
              </a-tag>
              <a-tag :color="getCoverageColor(dir.coverage)" class="coverage-tag">
                资料覆盖度: {{ (dir.coverage * 100).toFixed(0) }}%
              </a-tag>
            </div>

            <div class="direction-details">
              <div class="detail-row">
                <span class="detail-label">适合框架：</span>
                <span class="detail-value">
                  <a-tag v-for="fw in dir.frameworks" :key="fw" size="small" color="arcoblue">{{ fw }}</a-tag>
                </span>
              </div>
              <div class="detail-row">
                <span class="detail-label">资料覆盖：</span>
                <span class="detail-value">{{ dir.coveredCount }}/{{ dir.totalCount }} 篇资料相关</span>
              </div>
              <div class="detail-row ai-reason" v-if="dir.reason">
                <icon-bulb style="color: #165DFF; flex-shrink: 0" />
                <span class="reason-text">{{ dir.reason }}</span>
              </div>
              <div class="detail-row topic-need" v-if="appStore.mcpResult?.topic_needed">
                <span class="detail-label">选题补充：</span>
                <span class="detail-value supplement">{{ appStore.mcpResult.topic_needed }}</span>
              </div>
              <div class="detail-row" v-if="dir.needsSupplement && dir.needsSupplement.length > 0">
                <span class="detail-label">需补充：</span>
                <span class="detail-value supplement">{{ dir.needsSupplement.join('、') }}</span>
              </div>
            </div>

            <!-- 进度条 -->
            <div class="coverage-bar">
              <div class="progress-track">
                <div class="progress-fill" :style="{ width: (dir.coverage * 100).toFixed(0) + '%', backgroundColor: getCoverageGradient(dir.coverage) }"></div>
              </div>
              <span class="coverage-text">{{ (dir.coverage * 100).toFixed(0) }}%</span>
            </div>
          </div>
        </div>

        <!-- 自定义方向 -->
        <div class="custom-direction">
          <a-divider>以上都不合适？</a-divider>
          <a-textarea
            v-model="customDirection"
            placeholder="输入您想要的写作方向，例如：从技术+商业双重视角分析 Agent 的发展趋势..."
            :auto-size="{ minRows: 2, maxRows: 4 }"
            @change="selectCustomDirection"
          />
        </div>
      </a-spin>
    </a-card>

    <a-button
      type="primary"
      size="large"
      long
      :disabled="selectedDirection === null && !customDirection.trim()"
      @click="handleNext"
      class="submit-btn"
    >
      <icon-arrow-right />
      下一步：完善内容
    </a-button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { IconFolder, IconBulb, IconArrowRight, IconUser, IconSettings } from '@arco-design/web-vue/es/icon'
import { useAppStore } from '../stores/app'
import { analyzeDirections, getPersonaInfo } from '../utils/api'
import { marked } from 'marked'

const router = useRouter()
const appStore = useAppStore()
const loading = ref(false)
const directions = ref([])
const selectedDirection = ref(null)
const customDirection = ref('')
const personaInfo = ref(null)
const parsedPersona = ref(null)

const renderedPersona = computed(() => {
  if (!personaInfo.value) return ''
  return marked.parse(personaInfo.value)
})

const getCoverageColor = (coverage) => {
  if (coverage >= 0.7) return 'green'
  if (coverage >= 0.4) return 'orange'
  return 'gray'
}

const getCoverageGradient = (coverage) => {
  if (coverage >= 0.7) return '#00B42A'
  if (coverage >= 0.4) return '#F7BA2A'
  return '#C9CDD4'
}

const selectDirection = (index) => {
  selectedDirection.value = index
  customDirection.value = ''
}

const selectCustomDirection = () => {
  if (customDirection.value.trim()) {
    selectedDirection.value = null
  }
}

const handleNext = () => {
  if (customDirection.value.trim()) {
    // 自定义方向
    appStore.selectedDirection = {
      name: customDirection.value.trim(),
      type: 'custom',
      coverage: 0,
    }
  } else if (selectedDirection.value !== null) {
    appStore.selectedDirection = directions.value[selectedDirection.value]
  } else {
    Message.warning('请选择一个写作方向')
    return
  }
  // 选择方向后进入数据完善页面
  router.push('/data-input')
}

onMounted(async () => {
  loading.value = true
  try {
    const mcpResult = appStore.mcpResult

    // 新流程：从题材推荐页面过来，需要先根据选中的题材检索原文
    if (!mcpResult?.summary && mcpResult?.topic_name) {
      const topicName = mcpResult.topic_name
      const topicDesc = mcpResult.topic_description || ''

      // 调用 MCP 搜索获取原文总结
      const folders = appStore.selectedFolders || []
      if (!folders.length) {
        const settings = localStorage.getItem('archgen_settings')
        if (settings) {
          try {
            const parsed = JSON.parse(settings)
            folders.push(...(parsed.knowledgeFolders || []).filter(f => f.status === 'connected').map(f => f.path))
          } catch (e) {}
        }
      }

      if (!folders.length) {
        Message.error('缺少知识库文件夹，请先在设置中绑定')
        router.push('/mcp-search')
        return
      }

      const { mcpSearch } = await import('../utils/api')
      const searchRes = await mcpSearch(topicName, folders)
      if (searchRes.data.code === 0) {
        mcpResult.summary = searchRes.data.data.summary
        mcpResult.source_files = searchRes.data.data.source_files || []
        mcpResult.file_count = searchRes.data.data.file_count || 0
        mcpResult.topic = topicName
      } else {
        // 搜索失败，使用题材描述作为替代
        mcpResult.summary = topicDesc || topicName
        mcpResult.source_files = []
        mcpResult.file_count = 0
        mcpResult.topic = topicName
      }
    }

    if (!mcpResult || !mcpResult.summary) {
      Message.error('缺少检索结果，请返回重新检索')
      router.push('/mcp-search')
      return
    }

    const res = await analyzeDirections(mcpResult.summary)
    if (res.data.code === 0) {
      directions.value = res.data.data
    } else {
      directions.value = [
        {
          name: '综合分析报告',
          description: '从多个维度全面分析该主题',
          coverage: 0.6,
          coveredCount: Math.floor((mcpResult.file_count || 0) * 0.6),
          totalCount: mcpResult.file_count || 0,
          frameworks: ['主张型分析', '系统架构分析'],
          needsSupplement: ['具体数据支撑'],
        },
      ]
    }
    
    // 加载身份定位信息
    try {
      const personaRes = await getPersonaInfo()
      if (personaRes.data.code === 0) {
        personaInfo.value = personaRes.data.data.content || ''
        if (personaRes.data.data.parsed) {
          parsedPersona.value = personaRes.data.data.parsed
        }
      }
    } catch (e) {
      // 身份定位未设置时不报错
    }
  } catch (error) {
    Message.error('方向分析失败: ' + error.message)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.direction-suggest-view {
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
.info-card {
  margin-bottom: 20px;
}
.info-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.info-label {
  font-size: 13px;
  color: #86909c;
  min-width: 70px;
}
.info-value {
  font-size: 14px;
  color: #333;
}
.persona-card {
  margin-bottom: 20px;
  border: 1px solid #e5e6eb;
}
.persona-content {
  line-height: 1.8;
  font-size: 14px;
  color: #4e5969;
  max-height: 300px;
  overflow-y: auto;
  padding: 4px;
}
.persona-content :deep(h1), .persona-content :deep(h2), .persona-content :deep(h3) {
  margin: 12px 0 8px;
  font-size: 15px;
}
.persona-content :deep(ul), .persona-content :deep(ol) {
  padding-left: 20px;
}
.persona-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
.persona-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.persona-label {
  font-size: 12px;
  color: #86909c;
}
.persona-value {
  font-size: 14px;
  color: #333;
  line-height: 1.5;
}
.direction-card {
  margin-bottom: 20px;
}
.direction-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.direction-item {
  padding: 16px;
  border: 2px solid #f0f0f0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}
.direction-item:hover {
  border-color: #3498db;
  background: #f8f9fa;
}
.direction-item.selected {
  border-color: #3498db;
  background: #e8f4fd;
}
.direction-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}
.direction-rank {
  width: 30px;
  height: 30px;
  background: linear-gradient(135deg, #3498db 0%, #2c3e50 100%);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  flex-shrink: 0;
}
.direction-info {
  flex: 1;
}
.direction-info h3 {
  margin: 0 0 4px 0;
  font-size: 16px;
  color: #2c3e50;
}
.direction-desc {
  margin: 0;
  font-size: 13px;
  color: #666;
  line-height: 1.5;
}
.coverage-tag {
  flex-shrink: 0;
}
.direction-details {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}
.detail-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
}
.detail-label {
  color: #86909c;
  min-width: 70px;
  flex-shrink: 0;
}
.detail-value {
  color: #333;
}
.supplement {
  color: #F53F3F;
}
.ai-reason {
  background: #f0f7ff;
  border-radius: 6px;
  padding: 8px 12px;
  margin-top: 4px;
}
.reason-text {
  color: #4e5969;
  font-size: 12px;
  line-height: 1.6;
}
.coverage-bar {
  margin-top: 8px;
}
.progress-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}
.progress-track {
  flex: 1;
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}
.coverage-text {
  font-size: 13px;
  color: #666;
  min-width: 40px;
  text-align: right;
}
.custom-direction {
  margin-top: 20px;
}
.submit-btn {
  margin-top: 20px;
  height: 48px;
  font-size: 16px;
}
</style>
