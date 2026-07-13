<template>
  <div class="persona-settings-view">
    <a-page-header title="身份定位" @back="$router.push('/')">
      <template #extra>
        <a-typography-text type="secondary" style="font-size: 13px">
          设置你的写作身份定位，AI 将根据此信息调整内容风格
        </a-typography-text>
      </template>
    </a-page-header>

    <a-card class="info-card">
      <template #title>
        <div class="card-title">
          <icon-user />
          <span>身份定位文件</span>
        </div>
      </template>

      <a-space direction="vertical" style="width: 100%" :size="12">
        <div>
          <div style="font-size: 14px; font-weight: 500; margin-bottom: 8px">选择 Markdown 文件</div>
          <a-input-group compact style="display: flex">
            <a-input
              v-model="filePath"
              placeholder="选择或输入身份定位文件路径..."
              style="flex: 1"
              :disabled="loading"
            />
            <a-button @click="handleSelectFile" :loading="loading">
              <icon-folder /> 浏览
            </a-button>
          </a-input-group>
          <div style="margin-top: 6px">
            <a-space>
              <a-typography-text type="secondary" style="font-size: 12px">
                支持 .md / .markdown 文件
              </a-typography-text>
              <a-tag v-if="fileExists" color="green" size="small">已存在</a-tag>
              <a-tag v-else color="gray" size="small">未找到</a-tag>
            </a-space>
          </div>
        </div>

        <div>
          <div style="font-size: 14px; font-weight: 500; margin-bottom: 8px">编辑内容</div>
          <a-textarea
            v-model="content"
            placeholder="在此编辑你的身份定位内容，支持 Markdown 格式..."
            :auto-size="{ minRows: 20, maxRows: 40 }"
            class="markdown-editor"
          />
        </div>

        <div>
          <a-space>
            <a-button type="primary" @click="handleSave" :loading="saving">
              <icon-save /> 保存
            </a-button>
            <a-button @click="handleLoad" :loading="loading">
              <icon-refresh /> 重新加载
            </a-button>
            <a-button @click="handlePreview" v-if="content.trim()">
              <icon-eye /> 预览 Markdown
            </a-button>
          </a-space>
        </div>
      </a-space>
    </a-card>

    <!-- Markdown 预览弹窗 -->
    <a-modal
      v-model:visible="showPreview"
      title="身份定位预览"
      width="700px"
      :footer="false"
    >
      <div class="preview-body" v-text="renderedContent"></div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { IconUser, IconFolder, IconSave, IconRefresh, IconEye } from '@arco-design/web-vue/es/icon'
import { marked } from 'marked'
import { getPersonaInfo, setPersonaPath, savePersona } from '../utils/api'

const router = useRouter()
const filePath = ref('')
const content = ref('')
const fileExists = ref(false)
const loading = ref(false)
const saving = ref(false)
const showPreview = ref(false)

const renderedContent = computed(() => {
  if (!content.value) return ''
  return marked.parse(content.value, { async: false })
})

const loadInfo = async () => {
  loading.value = true
  try {
    const res = await getPersonaInfo()
    if (res.data.code === 0) {
      filePath.value = res.data.data.file_path
      content.value = res.data.data.content || ''
      fileExists.value = res.data.data.exists
    }
  } catch (error) {
    Message.error('加载失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

const handleLoad = () => {
  loadInfo()
}

const handleSelectFile = () => {
  // 在沙箱环境中，使用 prompt 让用户输入路径
  const path = prompt('请输入身份定位文件的完整路径：', filePath.value || '/home/admin/Desktop/persona.md')
  if (path && path.trim()) {
    filePath.value = path.trim()
    handleSetPath()
  }
}

const handleSetPath = async () => {
  if (!filePath.value.trim()) {
    Message.warning('请先输入文件路径')
    return
  }
  loading.value = true
  try {
    const res = await setPersonaPath(filePath.value.trim())
    if (res.data.code === 0) {
      Message.success('文件路径已设置')
      // 重新加载内容
      const infoRes = await getPersonaInfo()
      if (infoRes.data.code === 0) {
        content.value = infoRes.data.data.content || ''
        fileExists.value = infoRes.data.data.exists
      }
    } else {
      Message.error(res.data.msg)
    }
  } catch (error) {
    Message.error('设置失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

const handleSave = async () => {
  if (!content.value.trim()) {
    Message.warning('内容不能为空')
    return
  }
  saving.value = true
  try {
    const res = await savePersona(content.value)
    if (res.data.code === 0) {
      Message.success('保存成功')
      fileExists.value = true
    } else {
      Message.error(res.data.msg)
    }
  } catch (error) {
    Message.error('保存失败: ' + error.message)
  } finally {
    saving.value = false
  }
}

const handlePreview = () => {
  showPreview.value = true
}

onMounted(() => {
  loadInfo()
})
</script>

<style scoped>
.persona-settings-view {
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
.markdown-editor {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 14px;
  line-height: 1.8;
}
.preview-body {
  line-height: 1.8;
  font-size: 14px;
  color: #333;
  max-height: 600px;
  overflow-y: auto;
}
.preview-body :deep(h1), .preview-body :deep(h2), .preview-body :deep(h3) {
  margin: 16px 0 8px;
}
.preview-body :deep(ul), .preview-body :deep(ol) {
  padding-left: 24px;
}
</style>
