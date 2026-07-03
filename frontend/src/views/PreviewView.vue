<template>
  <div class="preview-view">
    <a-page-header title="预览效果" @back="$router.push('/data-input')">
      <template #extra>
        <a-steps :current="3" :max="4" style="width: 300px">
          <a-step>输入</a-step>
          <a-step>框架</a-step>
          <a-step>数据</a-step>
          <a-step>生成</a-step>
        </a-steps>
      </template>
    </a-page-header>

    <a-space class="toolbar">
      <a-button type="primary" @click="handleGenerate">
        <icon-download />
        生成 PNG 下载
      </a-button>
      <a-button @click="handleEdit">
        <icon-edit />
        返回编辑数据
      </a-button>
      <a-button @click="handleDownloadHtml">
        <icon-code />
        下载 HTML
      </a-button>
    </a-space>

    <a-card class="preview-card">
      <!-- LLM 生成的 HTML 信息图预览，保持 v-html -->
      <div class="preview-container" v-html="appStore.previewHtml"></div>
    </a-card>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { IconDownload, IconEdit, IconCode } from '@arco-design/web-vue/es/icon'
import { useAppStore } from '../stores/app'
import { generateDiagram } from '../utils/api'

const appStore = useAppStore()
const router = useRouter()

const handleGenerate = async () => {
  try {
    const response = await generateDiagram({
      frameworkKey: appStore.selectedFramework.key,
      text: appStore.inputText,
      style: appStore.style,
      size: appStore.size,
    })
    const url = URL.createObjectURL(response.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `${appStore.selectedFramework.name}.png`
    a.click()
    URL.revokeObjectURL(url)
    Message.success('下载成功!')
    appStore.outputImageUrl = url
    router.push('/output')
  } catch (error) {
    Message.error('生成失败: ' + error.message)
  }
}

const handleEdit = () => {
  router.push('/data-input')
}

const handleDownloadHtml = () => {
  const blob = new Blob([appStore.previewHtml], { type: 'text/html' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${appStore.selectedFramework.name}.html`
  a.click()
  URL.revokeObjectURL(url)
  Message.success('HTML 下载成功!')
}
</script>

<style scoped>
.preview-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}
.toolbar {
  margin-bottom: 20px;
}
.preview-card {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
.preview-container {
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}
.preview-container :deep(.diagram-container) {
  margin: 0 auto;
  max-width: 100%;
}
</style>
