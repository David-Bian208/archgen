<template>
  <div class="ab-test-manager">
    <a-page-header title="A/B 测试管理" subtitle="ArchGen v2.0 实验配置">
      <template #extra>
        <a-button type="primary" @click="loadExperiments">
          <template #icon><icon-refresh /></template>
          刷新
        </a-button>
      </template>
    </a-page-header>

    <a-spin :loading="loading" style="width: 100%">
      <!-- 实验列表 -->
      <a-card v-for="(exp, key) in experiments" :key="key" style="margin-top: 16px">
        <template #title>
          <a-space>
            <span>{{ exp.name }}</span>
            <a-tag :color="statusColors[exp.status]">{{ statusLabels[exp.status] }}</a-tag>
          </a-space>
        </template>
        <template #extra>
          <a-space>
            <a-button v-if="exp.status === 'draft'" type="primary" size="small" @click="startExperiment(key)">
              启动
            </a-button>
            <a-button v-if="exp.status === 'running'" size="small" @click="pauseExperiment(key)">
              暂停
            </a-button>
            <a-button v-if="exp.status === 'running'" status="danger" size="small" @click="stopExperiment(key)">
              停止
            </a-button>
          </a-space>
        </template>

        <a-descriptions :column="2" bordered>
          <a-descriptions-item label="描述">{{ exp.description }}</a-descriptions-item>
          <a-descriptions-item label="流量分配">{{ exp.traffic_split }}% / {{ 100 - exp.traffic_split }}%</a-descriptions-item>
          <a-descriptions-item label="开始日期">{{ exp.start_date || '-' }}</a-descriptions-item>
          <a-descriptions-item label="结束日期">{{ exp.end_date || '-' }}</a-descriptions-item>
        </a-descriptions>

        <!-- 实验组配置 -->
        <a-divider orientation="left">实验组配置</a-divider>
        <a-row :gutter="16">
          <a-col :span="12" v-for="(group, groupKey) in exp.groups" :key="groupKey">
            <a-card :title="`${groupKey}组 - ${group.name}`" size="small">
              <a-descriptions :column="1" size="small">
                <a-descriptions-item v-for="(value, prop) in group" :key="prop" :label="prop">
                  {{ value }}
                </a-descriptions-item>
              </a-descriptions>
            </a-card>
          </a-col>
        </a-row>
      </a-card>

      <!-- 显著性计算器 -->
      <a-card title="统计显著性计算器" style="margin-top: 16px">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-card title="A 组（对照组）" size="small">
              <a-form :model="groupA" layout="vertical">
                <a-form-item label="成功数">
                  <a-input-number v-model="groupA.success" :min="0" />
                </a-form-item>
                <a-form-item label="总数">
                  <a-input-number v-model="groupA.total" :min="1" />
                </a-form-item>
              </a-form>
            </a-card>
          </a-col>
          <a-col :span="12">
            <a-card title="B 组（实验组）" size="small">
              <a-form :model="groupB" layout="vertical">
                <a-form-item label="成功数">
                  <a-input-number v-model="groupB.success" :min="0" />
                </a-form-item>
                <a-form-item label="总数">
                  <a-input-number v-model="groupB.total" :min="1" />
                </a-form-item>
              </a-form>
            </a-card>
          </a-col>
        </a-row>
        <a-button type="primary" style="margin-top: 16px" @click="calculateSignificance">
          计算显著性
        </a-button>

        <!-- 结果展示 -->
        <a-alert v-if="significanceResult" style="margin-top: 16px" :type="significanceResult.significant ? 'success' : 'warning'">
          <template #title>
            {{ significanceResult.recommendation }}
          </template>
          <p>p 值：{{ significanceResult.p_value }}</p>
          <p>A 组成功率：{{ (significanceResult.group_a_rate * 100).toFixed(2) }}%</p>
          <p>B 组成功率：{{ (significanceResult.group_b_rate * 100).toFixed(2) }}%</p>
          <p>显著性：{{ significanceResult.significant ? '显著' : '不显著' }}</p>
        </a-alert>
      </a-card>
    </a-spin>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { IconRefresh } from '@arco-design/web-vue/es/icon'
import { getABExperiments, startABExperiment, pauseABExperiment, stopABExperiment, calculateSignificance as apiCalculateSignificance } from '../utils/api'
import { Message, Modal } from '@arco-design/web-vue'

const loading = ref(false)
const experiments = ref({})

const statusColors = {
  draft: 'gray',
  running: 'green',
  paused: 'orange',
  completed: 'blue',
}

const statusLabels = {
  draft: '草稿',
  running: '运行中',
  paused: '已暂停',
  completed: '已完成',
}

const groupA = reactive({ success: 100, total: 120 })
const groupB = reactive({ success: 90, total: 115 })
const significanceResult = ref(null)

async function loadExperiments() {
  loading.value = true
  try {
    const res = await getABExperiments()
    if (res.data.code === 0) {
      experiments.value = res.data.data.experiments || {}
    } else {
      Message.error(res.data.msg || '获取实验配置失败')
    }
  } catch (e) {
    console.error('获取实验配置失败:', e)
    Message.error('获取实验配置失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function startExperiment(key) {
  Modal.confirm({
    title: '确认启动实验',
    content: `确定要启动实验 ${key} 吗？`,
    onOk: async () => {
      try {
        const res = await startABExperiment(key)
        if (res.data.code === 0) {
          Message.success(res.data.data.message)
          loadExperiments()
        } else {
          Message.error(res.data.msg || '启动失败')
        }
      } catch (e) {
        Message.error('启动失败: ' + e.message)
      }
    },
  })
}

async function pauseExperiment(key) {
  Modal.confirm({
    title: '确认暂停实验',
    content: `确定要暂停实验 ${key} 吗？`,
    onOk: async () => {
      try {
        const res = await pauseABExperiment(key)
        if (res.data.code === 0) {
          Message.success(res.data.data.message)
          loadExperiments()
        } else {
          Message.error(res.data.msg || '暂停失败')
        }
      } catch (e) {
        Message.error('暂停失败: ' + e.message)
      }
    },
  })
}

async function stopExperiment(key) {
  Modal.confirm({
    title: '确认停止实验',
    content: `确定要停止实验 ${key} 吗？此操作不可撤销。`,
    okButtonProps: { status: 'danger' },
    onOk: async () => {
      try {
        const res = await stopABExperiment(key)
        if (res.data.code === 0) {
          Message.success(res.data.data.message)
          loadExperiments()
        } else {
          Message.error(res.data.msg || '停止失败')
        }
      } catch (e) {
        Message.error('停止失败: ' + e.message)
      }
    },
  })
}

async function calculateSignificance() {
  try {
    const res = await apiCalculateSignificance(groupA, groupB)
    if (res.data.code === 0) {
      significanceResult.value = res.data.data
    } else {
      Message.error(res.data.msg || '计算失败')
    }
  } catch (e) {
    Message.error('计算失败: ' + e.message)
  }
}

onMounted(() => {
  loadExperiments()
})
</script>

<style scoped>
.ab-test-manager {
  padding: 20px;
}
</style>
