<template>
  <div class="topic-suggest-view">
    <a-page-header title="写作题材推荐" @back="$router.push('/mcp-search')">
      <template #extra>
        <a-typography-text type="secondary" style="font-size: 13px">
          根据检索到的资料，推荐适合写的写作方向
        </a-typography-text>
      </template>
    </a-page-header>

    <!-- 资料概览 -->
    <a-card class="info-card">
      <template #title>
        <div class="card-title">
          <icon-file />
          <span>资料概览</span>
        </div>
      </template>
      <a-space direction="vertical" style="width: 100%" :size="8">
        <div v-if="suggestionSummary" class="summary-text">{{ suggestionSummary }}</div>
        <div class="info-row" style="flex-direction: column; align-items: flex-start; gap: 4px">
          <span class="info-label">知识库路径</span>
          <div class="info-value">
            <a-tag v-for="(f, i) in scannedFolders" :key="i" size="small" color="arcoblue">{{ f }}</a-tag>
          </div>
        </div>
        <div class="info-row">
          <span class="info-label">扫描到文件</span>
          <span class="info-value">{{ fileCount }} 篇</span>
        </div>
        <div class="info-row" v-if="sourceFiles.length">
          <span class="info-label">来源文件</span>
          <span class="info-value">
            <a-tag v-for="(f, i) in sourceFiles.slice(0, 20)" :key="i" size="small">{{ f }}</a-tag>
            <a-tag v-if="sourceFiles.length > 20" size="small" color="gray">+{{ sourceFiles.length - 20 }}</a-tag>
          </span>
        </div>
      </a-space>
    </a-card>

    <!-- 题材推荐列表 -->
    <a-card class="topic-card">
      <template #title>
        <div class="card-title">
          <icon-bulb />
          <span>推荐写作方向（{{ topics.length }} 个）</span>
        </div>
      </template>
      <template #extra>
        <a-button type="text" size="small" @click="refreshTopics" :disabled="loading || topics.length === 0">
          🔄 换一批
        </a-button>
      </template>

      <a-spin :loading="loading">
        <div v-if="topics.length" class="topic-list">
          <div
            v-for="(t, i) in topics"
            :key="i"
            class="topic-item"
            :class="{ selected: selectedTopic === i }"
            @click="selectedTopic = i"
          >
            <div class="topic-header">
              <div class="topic-name">{{ t.name }}</div>
              <a-tag v-if="selectedTopic === i" color="arcoblue" size="small">已选</a-tag>
            </div>
            <div class="topic-desc">{{ t.description }}</div>
            <div class="topic-meta">
              <div class="meta-item">
                <span class="meta-label">覆盖度</span>
                <div class="progress-track">
                  <div class="progress-fill" :style="{ width: (t.coverage * 100).toFixed(0) + '%' }"></div>
                </div>
                <span class="meta-value">{{ (t.coverage * 100).toFixed(0) }}%</span>
              </div>
            </div>
            <div class="topic-reason">
              <icon-bulb style="color: #F7BA2A; margin-right: 4px; font-size: 14px" />
              <span>{{ t.reason }}</span>
            </div>
            <div v-if="t.needed" class="topic-needed">
              <span class="needed-label">需要补充：</span>
              <span>{{ t.needed }}</span>
            </div>
            
            <!-- 每个方向的 3 分制评估 -->
            <div v-if="t.direction_score || t.deficiency_score || t.overall_score" style="margin-top: 12px; padding-top: 12px; border-top: 1px dashed #e5e6eb">
              <a-row :gutter="12">
                <a-col :span="8">
                  <div style="text-align: center; padding: 8px; background: #f8f9ff; border-radius: 6px">
                    <div style="font-size: 12px; color: #86909c; margin-bottom: 4px">方向适合度</div>
                    <div style="font-size: 20px; font-weight: 600" :style="{ color: t.direction_score >= 80 ? '#00b42a' : t.direction_score >= 60 ? '#f7ba1e' : '#f53f3f' }">
                      {{ t.direction_score || 0 }}<span style="font-size: 12px; font-weight: 400">分</span>
                    </div>
                    <div style="font-size: 11px; color: #86909c; margin-top: 4px; line-height: 1.4; text-align: left">
                      {{ t.direction_analysis || '暂无分析' }}
                    </div>
                  </div>
                </a-col>
                <a-col :span="8">
                  <div style="text-align: center; padding: 8px; background: #f8f9ff; border-radius: 6px">
                    <div style="font-size: 12px; color: #86909c; margin-bottom: 4px">内容完整度</div>
                    <div style="font-size: 20px; font-weight: 600" :style="{ color: t.deficiency_score >= 80 ? '#00b42a' : t.deficiency_score >= 50 ? '#f7ba1e' : '#f53f3f' }">
                      {{ t.deficiency_score || 0 }}<span style="font-size: 12px; font-weight: 400">分</span>
                    </div>
                    <div style="font-size: 11px; color: #86909c; margin-top: 4px; text-align: left">
                      <div v-for="(detail, di) in (t.deficiency_details || []).slice(0, 2)" :key="di" style="margin-bottom: 2px; line-height: 1.3">
                        <a-tag v-if="detail.severity === 'high'" size="mini" color="red">高</a-tag>
                        <a-tag v-else-if="detail.severity === 'medium'" size="mini" color="orange">中</a-tag>
                        <a-tag v-else size="mini" color="arcoblue">低</a-tag>
                        <span style="font-size: 11px">{{ detail.item }}</span>
                      </div>
                    </div>
                  </div>
                </a-col>
                <a-col :span="8">
                  <div style="text-align: center; padding: 8px; background: #f8f9ff; border-radius: 6px">
                    <div style="font-size: 12px; color: #86909c; margin-bottom: 4px">综合评分</div>
                    <div style="font-size: 20px; font-weight: 600" :style="{ color: t.overall_score >= 80 ? '#00b42a' : t.overall_score >= 60 ? '#f7ba1e' : '#f53f3f' }">
                      {{ t.overall_score || 0 }}<span style="font-size: 12px; font-weight: 400">分</span>
                    </div>
                    <div style="margin-top: 4px">
                      <a-tag v-if="(t.overall_score || 0) >= 80" color="green" size="mini">可直接生成</a-tag>
                      <a-tag v-else-if="(t.overall_score || 0) >= 60" color="orange" size="mini">建议补充</a-tag>
                      <a-tag v-else color="red" size="mini">素材不足</a-tag>
                    </div>
                  </div>
                </a-col>
              </a-row>
            </div>
          </div>
        </div>
        <a-empty v-else description="暂无推荐方向" />
      </a-spin>
    </a-card>

    <!-- 底部操作栏 -->
    <div class="action-bar" v-if="topics.length">
      <a-space>
        <a-button type="primary" size="large" :disabled="selectedTopic === null" @click="handleNext">
          <icon-arrow-right />
          选择此方向，开始检索原文
        </a-button>
      </a-space>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { IconFile, IconBulb, IconArrowRight } from '@arco-design/web-vue/es/icon'
import { useAppStore } from '../stores/app'
import { mcpSuggest, evaluateCompleteness, createWorkflowSession } from '../utils/api'

const router = useRouter()
const route = useRoute()
const appStore = useAppStore()

const loading = ref(false)
const topics = ref([])
const selectedTopic = ref(null)
const suggestionSummary = ref('')
const sourceFiles = ref([])
const scannedFolders = ref([])
const fileCount = ref(0)
const completenessResult = ref(null)
const evalLoading = ref(false)
const sessionId = ref('')

onMounted(async () => {
  loading.value = true
  try {
    const folders = route.query.folders ? JSON.parse(route.query.folders) : []
    const topic = route.query.topic || ''
    const categories = route.query.categories ? JSON.parse(route.query.categories) : []
    const timeRange = route.query.timeRange || 'all'
    const startDate = route.query.startDate || ''
    const endDate = route.query.endDate || ''

    if (!folders.length) {
      Message.error('缺少知识库文件夹信息')
      router.push('/mcp-search')
      return
    }

    const res = await mcpSuggest({
      topic,
      folders,
      categories,
      time_range: timeRange,
      start_date: startDate,
      end_date: endDate,
    })

    if (res.data.code === 0) {
      topics.value = res.data.data.topics || []
      suggestionSummary.value = res.data.data.summary || ''
      sourceFiles.value = res.data.data.source_files || []
      scannedFolders.value = folders
      fileCount.value = res.data.data.file_count || 0

      // 自动跑完整度评估
      try {
        const sessionRes = await createWorkflowSession()
        sessionId.value = sessionRes.data.data.session_id
        const evalRes = await evaluateCompleteness(sessionId.value, suggestionSummary.value)
        if (evalRes.data.code === 0) {
          const rawData = evalRes.data.data
          let completeness = rawData.completeness || 0
          if (completeness > 0 && completeness <= 1) {
            completeness = Math.round(completeness * 100)
          }
          completenessResult.value = { ...rawData, completeness }
        }
      } catch (e) {
        console.warn('自动评估失败:', e)
      }
    } else {
      Message.error(res.data.msg || '分析失败')
      router.push('/mcp-search')
    }
  } catch (error) {
    Message.error('题材分析失败: ' + error.message)
    router.push('/mcp-search')
  } finally {
    loading.value = false
  }
})

const handleNext = async () => {
  if (selectedTopic.value === null) return

  const topic = topics.value[selectedTopic.value]
  if (!topic) return

  appStore.selectedTopic = topic
  appStore.mcpResult = {
    summary: suggestionSummary.value,
    source_files: sourceFiles.value,
    file_count: sourceFiles.value.length,
    topic_name: topic.name,
    topic_description: topic.description,
    topic_needed: topic.needed,
  }

  Message.success(`已选择「${topic.name}」，进入多段式工作流...`)
  // 跳转到新的多段式工作流页面，传递 MCP 摘要和 sessionId
  const params = new URLSearchParams({
    summary: suggestionSummary.value,
    files: JSON.stringify(sourceFiles.value),
    topic: topic.name,
  })
  if (sessionId.value) {
    params.set('sessionId', sessionId.value)
  }
  router.push(`/workflow?${params.toString()}`)
}

// 换一批：重新推荐题材
const refreshTopics = async () => {
  if (loading.value || topics.value.length === 0) return
  loading.value = true
  try {
    const folders = scannedFolders.value
    const topic = route.query.topic || ''
    const categories = route.query.categories ? JSON.parse(route.query.categories) : []
    const timeRange = route.query.timeRange || 'all'
    const startDate = route.query.startDate || ''
    const endDate = route.query.endDate || ''

    const res = await mcpSuggest({
      topic,
      folders,
      categories,
      time_range: timeRange,
      start_date: startDate,
      end_date: endDate,
    })

    if (res.data.code === 0) {
      topics.value = res.data.data.topics || []
      selectedTopic.value = null
      if (topics.value.length === 0) {
        Message.warning('暂无推荐方向，请再试一次')
      } else {
        Message.success(`已换一批，共 ${topics.value.length} 个方向`)
      }
    } else {
      Message.error(res.data.msg || '分析失败')
    }
  } catch (error) {
    Message.error('分析失败: ' + error.message)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.topic-suggest-view {
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
.summary-text {
  font-size: 14px;
  color: #4e5969;
  line-height: 1.6;
  background: #f7f8fa;
  padding: 12px;
  border-radius: 6px;
}
.info-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.info-label {
  font-size: 13px;
  color: #86909c;
  white-space: nowrap;
}
.info-value {
  font-size: 14px;
  color: #333;
}
.topic-card {
  margin-bottom: 20px;
}
.topic-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.topic-item {
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
}
.topic-item:hover {
  border-color: #3498db;
  background: #f7f8fa;
}
.topic-item.selected {
  border-color: #3498db;
  background: #e8f3ff;
}
.topic-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.topic-name {
  font-size: 16px;
  font-weight: 600;
  color: #1d2129;
}
.topic-desc {
  font-size: 14px;
  color: #4e5969;
  margin-bottom: 12px;
}
.topic-meta {
  margin-bottom: 8px;
}
.meta-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.meta-label {
  font-size: 12px;
  color: #86909c;
  white-space: nowrap;
}
.progress-track {
  flex: 1;
  height: 6px;
  background: #e5e6eb;
  border-radius: 3px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3498db, #165DFF);
  border-radius: 3px;
  transition: width 0.3s;
}
.meta-value {
  font-size: 13px;
  font-weight: 500;
  color: #165DFF;
  white-space: nowrap;
}
.topic-reason {
  display: flex;
  align-items: flex-start;
  font-size: 13px;
  color: #86909c;
  margin-top: 8px;
}
.topic-needed {
  font-size: 13px;
  color: #F7BA2A;
  margin-top: 4px;
}
.needed-label {
  font-weight: 500;
}
.action-bar {
  display: flex;
  justify-content: center;
  padding: 16px 0;
}
</style>
