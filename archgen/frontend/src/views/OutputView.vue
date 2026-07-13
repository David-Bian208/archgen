<template>
  <div class="output-view">
    <a-result status="success" title="架构图生成成功！">
      <template #subtitle>
        <p>你的 {{ appStore.selectedFramework?.name }} 已生成完毕</p>
      </template>
      <template #extra>
        <a-space>
          <a-button type="primary" @click="handleDownload">
            <icon-download />
            下载 PNG
          </a-button>
          <a-button @click="handleNewAnalysis">
            <icon-plus />
            新建分析
          </a-button>
        </a-space>
      </template>
    </a-result>

    <a-card v-if="appStore.outputImageUrl" class="output-card">
      <img :src="appStore.outputImageUrl" alt="生成的架构图" class="output-image" />
    </a-card>

    <a-card class="info-card">
      <template #title>
        <div class="info-title">
          <icon-info-circle />
          <span>分析信息</span>
        </div>
      </template>
      <a-descriptions :column="2" bordered>
        <a-descriptions-item label="框架">
          {{ appStore.selectedFramework?.name }}
        </a-descriptions-item>
        <a-descriptions-item label="业务领域">
          {{ getCategoryName(appStore.category) }}
        </a-descriptions-item>
        <a-descriptions-item label="样式风格">
          {{ appStore.style }}
        </a-descriptions-item>
        <a-descriptions-item label="输出尺寸">
          {{ appStore.size }}
        </a-descriptions-item>
      </a-descriptions>
    </a-card>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { IconDownload, IconPlus, IconInfoCircle } from '@arco-design/web-vue/es/icon'
import { useAppStore } from '../stores/app'

const appStore = useAppStore()
const router = useRouter()

const categoryNames = {
  business: '商业分析',
  finance: '财务分析',
  product: '产品设计',
  operations: '运营优化',
  personal: '个人成长',
  risk: '风险管理',
  project: '项目管理',
}

const getCategoryName = (key) => categoryNames[key] || key

const handleDownload = () => {
  const a = document.createElement('a')
  a.href = appStore.outputImageUrl
  a.download = `${appStore.selectedFramework.name}.png`
  a.click()
}

const handleNewAnalysis = () => {
  appStore.reset()
  router.push('/')
}
</script>

<style scoped>
.output-view {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
}
.output-card {
  margin-top: 20px;
  text-align: center;
}
.output-image {
  max-width: 100%;
  border-radius: 8px;
}
.info-card {
  margin-top: 20px;
}
.info-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
