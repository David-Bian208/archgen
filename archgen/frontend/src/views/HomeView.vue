<template>
  <div class="home-view">
    <div class="hero">
      <h1>ArchGen</h1>
      <p>逻辑框架可视化引擎</p>
    </div>

    <!-- MCP 检索入口 -->
    <a-card class="mcp-entry-card" hoverable @click="$router.push('/mcp-search')">
      <div class="mcp-entry">
        <div class="mcp-icon">
          <icon-search style="font-size: 32px; color: #3498db" />
        </div>
        <div class="mcp-text">
          <div class="mcp-title">MCP 知识库检索</div>
          <div class="mcp-desc">从已绑定的知识库文件夹中智能检索相关内容</div>
        </div>
        <icon-arrow-right style="font-size: 20px; color: #999" />
      </div>
    </a-card>

    <!-- 身份定位入口 -->
    <a-card class="persona-entry-card" hoverable @click="$router.push('/persona')">
      <div class="mcp-entry">
        <div class="mcp-icon">
          <icon-user style="font-size: 32px; color: #9b59b6" />
        </div>
        <div class="mcp-text">
          <div class="mcp-title">身份定位</div>
          <div class="mcp-desc">设置写作身份、受众、风格偏好</div>
        </div>
        <icon-arrow-right style="font-size: 20px; color: #999" />
      </div>
    </a-card>

    <a-card class="input-card">
      <template #title>
        <div class="card-title">
          <icon-edit />
          <span>输入你的分析需求</span>
        </div>
      </template>

      <a-textarea
        v-model="appStore.inputText"
        placeholder="例如：分析腾讯的商业模式&#10;或者：评估我们公司的竞争优势&#10;或者：规划个人时间管理方案"
        :auto-size="{ minRows: 6, maxRows: 12 }"
        class="input-textarea"
      />

      <div class="upload-section">
        <a-divider>或上传文件/图片</a-divider>
        <a-upload
          :custom-request="handleUpload"
          :show-file-list="true"
          :limit="5"
          accept=".md,.txt,.markdown,.jpg,.jpeg,.png,.gif,.webp,.pdf"
          draggable
          multiple
        >
          <template #upload-button>
            <div class="upload-area">
              <icon-upload />
              <span>点击或拖拽上传文件</span>
              <span class="upload-hint">支持 Markdown、TXT、图片 (JPG/PNG/GIF)、PDF</span>
            </div>
          </template>
        </a-upload>

        <div class="uploaded-files" v-if="uploadedFiles.length > 0">
          <div class="uploaded-file" v-for="(file, index) in uploadedFiles" :key="index">
            <span class="file-name">{{ file.name }}</span>
            <span class="file-size">{{ formatSize(file.size) }}</span>
            <a-button type="text" size="mini" @click="removeFile(index)">
              <icon-delete />
            </a-button>
          </div>
        </div>
      </div>

      <div class="settings-row">
        <a-space>
          <a-select v-model="appStore.style" style="width: 150px">
            <a-option value="minimal">极简风格</a-option>
            <a-option value="business">商务风格</a-option>
            <a-option value="tech">科技风格</a-option>
          </a-select>
          <a-select v-model="appStore.size" style="width: 180px">
            <a-option value="default">默认 (1200x800)</a-option>
            <a-option value="wechat">公众号 (1080x1920)</a-option>
            <a-option value="xiaohongshu">小红书 (1080x1440)</a-option>
            <a-option value="ppt">PPT (1920x1080)</a-option>
          </a-select>
        </a-space>
      </div>

      <a-button
        type="primary"
        size="large"
        long
        :loading="loading"
        :disabled="!hasInput"
        @click="handleNext"
        class="submit-btn"
      >
        <icon-arrow-right />
        下一步：选择框架
      </a-button>
    </a-card>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { IconEdit, IconUpload, IconArrowRight, IconDelete, IconSearch, IconUser } from '@arco-design/web-vue/es/icon'
import { useAppStore } from '../stores/app'
import { classifyIntent } from '../utils/api'

const appStore = useAppStore()
const router = useRouter()
const loading = ref(false)
const uploadedFiles = ref([])

const hasInput = computed(() => {
  return appStore.inputText.trim() || uploadedFiles.value.length > 0
})

const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const handleUpload = ({ fileItem }) => {
  uploadedFiles.value.push(fileItem.file)

  const isImage = /\.(jpg|jpeg|png|gif|webp)$/i.test(fileItem.name)
  const isText = /\.(md|txt|markdown)$/i.test(fileItem.name)

  if (isText) {
    const reader = new FileReader()
    reader.onload = (e) => {
      appStore.inputText += (appStore.inputText ? '\n\n---\n\n' : '') + e.target.result
      Message.success(`已上传文本: ${fileItem.name}`)
    }
    reader.readAsText(fileItem.file)
  } else if (isImage) {
    const reader = new FileReader()
    reader.onload = (e) => {
      appStore.inputText += (appStore.inputText ? '\n\n---\n\n' : '') + `[图片: ${fileItem.name}]`
      appStore.uploadedImage = e.target.result
      appStore.uploadedImageName = fileItem.name
      Message.success(`已上传图片: ${fileItem.name}`)
    }
    reader.readAsDataURL(fileItem.file)
  } else {
    Message.success(`已上传: ${fileItem.name}`)
  }
}

const removeFile = (index) => {
  uploadedFiles.value.splice(index, 1)
}

const handleNext = async () => {
  if (!hasInput.value) {
    Message.warning('请先输入需求或上传文件')
    return
  }

  loading.value = true
  try {
    const result = await classifyIntent(appStore.inputText)
    if (result.data.code === 0) {
      appStore.category = result.data.data.primary
      appStore.categoryConfidence = result.data.data.confidence
      appStore.categoryAlternatives = result.data.data.alternatives || []
    }
    router.push('/frameworks')
  } catch (error) {
    Message.error('分类失败: ' + error.message)
    router.push('/frameworks')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.home-view {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}
.hero {
  text-align: center;
  margin-bottom: 30px;
}
.hero h1 {
  font-size: 36px;
  background: linear-gradient(135deg, #3498db 0%, #2c3e50 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0;
}
.hero p {
  color: #666;
  font-size: 16px;
  margin-top: 8px;
}
.input-card {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
}
.input-textarea {
  font-size: 15px;
  line-height: 1.6;
}
.upload-section {
  margin: 20px 0;
}
.upload-area {
  padding: 30px;
  text-align: center;
  border: 2px dashed #d9d9d9;
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.3s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: #666;
}
.upload-area:hover {
  border-color: #3498db;
}
.upload-hint {
  font-size: 12px;
  color: #999;
}
.uploaded-files {
  margin-top: 10px;
}
.uploaded-file {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #f8f9fa;
  border-radius: 4px;
  margin-bottom: 6px;
  font-size: 13px;
}
.file-name {
  flex: 1;
  color: #333;
}
.file-size {
  color: #999;
  font-size: 12px;
}
.settings-row {
  margin: 20px 0;
}
.submit-btn {
  margin-top: 20px;
  height: 48px;
  font-size: 16px;
}
.mcp-entry-card {
  margin-bottom: 16px;
  cursor: pointer;
  border: 2px dashed #3498db;
  background: #f8fbff;
}
.mcp-entry-card:hover {
  border-color: #2980b9;
  background: #eef6ff;
}
.mcp-entry {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 0;
}
.mcp-text {
  flex: 1;
}
.mcp-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}
.mcp-desc {
  font-size: 13px;
  color: #999;
  margin-top: 2px;
}
.persona-entry-card {
  margin-bottom: 16px;
  cursor: pointer;
  border: 2px dashed #9b59b6;
  background: #fdf8ff;
}
.persona-entry-card:hover {
  border-color: #8e44ad;
  background: #f5eefc;
}
</style>
