<template>
  <div class="analytics-dashboard">
    <a-page-header title="数据看板" subtitle="ArchGen v2.0 内容补充分析">
      <template #extra>
        <a-space>
          <a-select v-model="days" :options="dayOptions" @change="loadOverview" style="width: 120px" />
          <a-button type="primary" @click="loadOverview">
            <template #icon><icon-refresh /></template>
            刷新
          </a-button>
        </a-space>
      </template>
    </a-page-header>

    <a-spin :loading="loading" style="width: 100%">
      <!-- 核心指标卡片 -->
      <a-row :gutter="16" style="margin-top: 20px">
        <a-col :span="6">
          <a-card>
            <a-statistic title="总事件数" :value="overview.total_events" :precision="0">
              <template #suffix>次</template>
            </a-statistic>
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card>
            <a-statistic title="总会话数" :value="overview.total_sessions" :precision="0">
              <template #suffix>个</template>
            </a-statistic>
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card>
            <a-statistic title="平均确认率" :value="overview.avg_confirm_rate" :precision="2">
              <template #suffix>%</template>
            </a-statistic>
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card>
            <a-statistic title="平均降级次数" :value="overview.avg_degradation_count" :precision="2">
              <template #suffix>次</template>
            </a-statistic>
          </a-card>
        </a-col>
      </a-row>

      <!-- 次要指标 -->
      <a-row :gutter="16" style="margin-top: 16px">
        <a-col :span="12">
          <a-card title="缓存命中率">
            <a-progress :percent="overview.cache_hit_rate * 100" :show-text="true" />
            <a-typography-text type="secondary" size="small">{{ (overview.cache_hit_rate * 100).toFixed(1) }}% 的请求命中缓存</a-typography-text>
          </a-card>
        </a-col>
        <a-col :span="12">
          <a-card title="重新评估率">
            <a-progress :percent="overview.reevaluate_rate * 100" :show-text="true" status="warning" />
            <a-typography-text type="secondary" size="small">{{ (overview.reevaluate_rate * 100).toFixed(1) }}% 的补充触发了重新评估</a-typography-text>
          </a-card>
        </a-col>
      </a-row>

      <!-- 知识级别分布 -->
      <a-card title="知识级别分布" style="margin-top: 16px">
        <a-row :gutter="16">
          <a-col :span="5" v-for="(count, level) in overview.level_distribution" :key="level">
            <a-statistic :title="level" :value="count" :precision="0">
              <template #prefix>
                <a-tag :color="levelColors[level]">{{ level }}</a-tag>
              </template>
            </a-statistic>
          </a-col>
        </a-row>
        <a-divider />
        <a-row :gutter="8">
          <a-col :span="5" v-for="(count, level) in overview.level_distribution" :key="level">
            <a-progress :percent="calcPercentage(count)" :show-text="true" :color="levelColors[level]" />
          </a-col>
        </a-row>
      </a-card>

      <!-- 事件列表 -->
      <a-card title="最近事件" style="margin-top: 16px">
        <a-table :data="events" :columns="columns" :pagination="{ pageSize: 10 }" size="small">
          <template #knowledge_level="{ record }">
            <a-tag :color="levelColors[record.knowledge_level]">{{ record.knowledge_level }}</a-tag>
          </template>
          <template #user_action="{ record }">
            <a-tag v-if="record.user_action" :color="actionColors[record.user_action]">{{ record.user_action }}</a-tag>
            <span v-else>-</span>
          </template>
          <template #timestamp="{ record }">
            {{ formatTime(record.timestamp) }}
          </template>
        </a-table>
      </a-card>
    </a-spin>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { IconRefresh } from '@arco-design/web-vue/es/icon'
import { getAnalyticsOverview, getAnalyticsEvents } from '../utils/api'
import { Message } from '@arco-design/web-vue'

const days = ref(7)
const dayOptions = [
  { label: '最近 7 天', value: 7 },
  { label: '最近 14 天', value: 14 },
  { label: '最近 30 天', value: 30 },
]

const loading = ref(false)
const overview = ref({
  total_events: 0,
  total_sessions: 0,
  level_distribution: { L0: 0, L1: 0, L2: 0, L3: 0, L4: 0 },
  avg_confirm_rate: 0,
  avg_degradation_count: 0,
  cache_hit_rate: 0,
  reevaluate_rate: 0,
})

const events = ref([])

const levelColors = {
  L0: 'green',
  L1: 'blue',
  L2: 'orange',
  L3: 'gray',
  L4: 'gray',
}

const actionColors = {
  confirm: 'green',
  edit: 'blue',
  degrade: 'orange',
  cancel: 'red',
}

const columns = [
  { title: '时间', dataIndex: 'timestamp', slotName: 'timestamp', width: 180 },
  { title: '会话 ID', dataIndex: 'session_id', width: 120, ellipsis: true },
  { title: '事件类型', dataIndex: 'event_type', width: 150 },
  { title: '话题', dataIndex: 'topic', width: 120, ellipsis: true },
  { title: '知识级别', dataIndex: 'knowledge_level', slotName: 'knowledge_level', width: 100 },
  { title: '用户操作', dataIndex: 'user_action', slotName: 'user_action', width: 100 },
  { title: '内容长度', dataIndex: 'content_length', width: 100 },
]

function calcPercentage(count) {
  const total = Object.values(overview.value.level_distribution).reduce((a, b) => a + b, 0)
  return total > 0 ? Math.round((count / total) * 100) : 0
}

function formatTime(timestamp) {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function loadOverview() {
  loading.value = true
  try {
    const res = await getAnalyticsOverview(days.value)
    if (res.data.code === 0) {
      overview.value = res.data.data
    } else {
      Message.error(res.data.msg || '获取分析数据失败')
    }
  } catch (e) {
    console.error('获取分析数据失败:', e)
    Message.error('获取分析数据失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function loadEvents() {
  try {
    const res = await getAnalyticsEvents('', 50)
    if (res.data.code === 0) {
      events.value = res.data.data.events || []
    }
  } catch (e) {
    console.error('获取事件列表失败:', e)
  }
}

onMounted(() => {
  loadOverview()
  loadEvents()
})
</script>

<style scoped>
.analytics-dashboard {
  padding: 20px;
}
</style>
