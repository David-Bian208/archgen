<template>
  <div class="settings-view">
    <a-page-header title="设置" @back="$router.push('/')">
    </a-page-header>

    <a-tabs default-active-key="kb">
      <a-tab-pane key="kb" title="知识库设置">
        <a-card>
          <template #title>
            <div class="card-title">
              <icon-folder />
              <span>本地文件夹绑定</span>
            </div>
          </template>

          <a-alert type="info" :show-icon="false" class="tip-alert">
            <template #title>将电脑本地文件夹绑定为知识库，可以从中选择文件进行分析</template>
          </a-alert>

          <div class="folder-list">
            <div class="folder-item" v-for="(folder, index) in settings.knowledgeFolders" :key="index">
              <div class="folder-info">
                <icon-folder class="folder-icon" />
                <div class="folder-details">
                  <div class="folder-path">{{ folder.path }}</div>
                  <div class="folder-status" :class="folder.status">
                    {{ folder.status === 'connected' ? '已连接' : folder.status === 'error' ? '连接失败' : '未验证' }}
                    <span v-if="folder.error" class="folder-error">{{ folder.error }}</span>
                  </div>
                </div>
              </div>
              <a-space>
                <a-button type="text" size="small" @click="verifyFolder(index)">
                  <icon-refresh />
                </a-button>
                <a-button type="text" size="small" status="danger" @click="removeFolder(index)">
                  <icon-delete />
                </a-button>
              </a-space>
            </div>

            <a-empty v-if="settings.knowledgeFolders.length === 0" description="暂无绑定的文件夹" />
          </div>

          <a-divider />

          <a-space class="add-folder-row">
            <a-input
              v-model="newFolderPath"
              placeholder="输入文件夹路径，例如: /Users/name/Documents/knowledge"
              style="width: 500px"
              @pressEnter="addFolder"
            />
            <a-button type="primary" @click="addFolder" :disabled="!newFolderPath.trim()">
              <icon-plus />
              添加文件夹
            </a-button>
          </a-space>

          <div class="folder-help">
            <a-typography-text type="secondary" style="font-size: 12px">
              <icon-info-circle />
              支持本地任意文件夹路径。添加后，系统将读取该文件夹中的 Markdown、TXT、PDF 和图片文件。
            </a-typography-text>
          </div>
        </a-card>

        <a-card style="margin-top: 20px">
          <template #title>
            <div class="card-title">
              <icon-list />
              <span>知识库文件</span>
            </div>
          </template>

          <a-spin :loading="kbLoading">
            <div v-if="kbTreeData.length > 0" class="kb-tree-container">
              <a-tree
                :data="kbTreeData"
                :default-expand-all="true"
                block-node
                @select="onTreeSelect"
              >
                <template #icon="{ node }">
                  <icon-folder v-if="node && node.type === 'folder'" style="color: #3498db" />
                  <icon-file v-else-if="node" :style="{ color: getFileColor(node.title || '') }" />
                </template>
              </a-tree>
            </div>
            <a-empty v-else-if="!kbLoading" description="请先添加并验证知识库文件夹" />
            <div v-if="kbLoading" class="loading-progress">
              <a-progress :percent="loadProgress" status="active" />
              <a-typography-text type="secondary" style="font-size: 12px; margin-top: 8px; display: block">
                正在扫描文件夹结构...
              </a-typography-text>
            </div>
          </a-spin>
        </a-card>
      </a-tab-pane>

      <a-tab-pane key="llm" title="AI 设置">
        <a-card>
          <template #title>
            <div class="card-title">
              <icon-robot />
              <span>LLM API 配置</span>
            </div>
          </template>

          <a-form :model="settings.llm" layout="vertical">
            <a-form-item label="API Provider">
              <a-select v-model="settings.llm.provider">
                <a-option value="deepseek">DeepSeek</a-option>
                <a-option value="openai">OpenAI</a-option>
                <a-option value="qwen">通义千问</a-option>
              </a-select>
            </a-form-item>
            <a-form-item label="API Key">
              <a-input-password v-model="settings.llm.apiKey" placeholder="输入你的 API Key" />
            </a-form-item>
            <a-form-item label="Base URL">
              <a-input v-model="settings.llm.baseUrl" placeholder="https://api.deepseek.com/v1" />
            </a-form-item>
            <a-form-item label="Model">
              <a-input v-model="settings.llm.model" placeholder="deepseek-chat" />
            </a-form-item>
          </a-form>

          <a-button type="primary" @click="saveLlmSettings">
            <icon-save />
            保存设置
          </a-button>
        </a-card>
      </a-tab-pane>

      <a-tab-pane key="output" title="输出设置">
        <a-card>
          <template #title>
            <div class="card-title">
              <icon-image />
              <span>输出目录</span>
            </div>
          </template>

          <a-form :model="settings" layout="vertical">
            <a-form-item label="输出目录路径">
              <a-input v-model="settings.outputDir" placeholder="输出文件保存路径" />
            </a-form-item>
            <a-form-item label="默认样式">
              <a-select v-model="settings.defaultStyle">
                <a-option value="minimal">极简风格</a-option>
                <a-option value="business">商务风格</a-option>
                <a-option value="tech">科技风格</a-option>
              </a-select>
            </a-form-item>
            <a-form-item label="默认尺寸">
              <a-select v-model="settings.defaultSize">
                <a-option value="default">默认 (1200x800)</a-option>
                <a-option value="wechat">公众号 (1080x1920)</a-option>
                <a-option value="xiaohongshu">小红书 (1080x1440)</a-option>
                <a-option value="ppt">PPT (1920x1080)</a-option>
              </a-select>
            </a-form-item>
          </a-form>

          <a-button type="primary" @click="saveOutputSettings">
            <icon-save />
            保存设置
          </a-button>
        </a-card>
      </a-tab-pane>
      <a-tab-pane key="persona" title="身份定位">
        <a-card>
          <template #title>
            <div class="card-title">
              <icon-user />
              <span>身份定位文件</span>
            </div>
          </template>

          <a-alert type="info" :show-icon="false" class="tip-alert">
            <template #title>设置你的写作身份定位（我是谁、我的受众、风格偏好等），AI 将根据此信息调整内容风格和推荐方向</template>
          </a-alert>

          <a-space direction="vertical" style="width: 100%" :size="12">
            <div>
              <div style="font-size: 14px; font-weight: 500; margin-bottom: 8px">Markdown 文件路径</div>
              <a-input
                v-model="personaPath"
                placeholder="输入身份定位 Markdown 文件路径，例如: /home/admin/Desktop/persona.md"
                style="width: 100%"
              />
              <a-typography-text type="secondary" style="font-size: 12px; display: block; margin-top: 4px">
                支持 .md / .markdown 格式。文件内容示例：# 我是谁\n## 我的受众\n## 我的风格...
              </a-typography-text>
            </div>
          </a-space>

          <a-space style="margin-top: 12px">
            <a-button v-if="!personaSaved" type="primary" @click="savePersonaPath">
              <icon-save />
              保存身份定位路径
            </a-button>
            <a-button v-else type="primary" status="success" @click="savePersonaPath">
              <icon-check-circle-fill />
              已保存身份定位路径
            </a-button>
            <a-button @click="handleParsePersona" :loading="personaParsing" :disabled="!personaPath.trim()">
              <icon-robot /> 解析身份定位
            </a-button>
          </a-space>

          <!-- 复杂度警告 -->
          <a-alert v-if="complexityWarning" type="warning" :show-icon="true" closable style="margin-top: 12px">
            {{ complexityWarning }}
          </a-alert>

          <!-- 解析结果预览 - 六维度展示 -->
          <div v-if="parsedPersona" class="persona-result">
            <h4>✅ 六维身份模型：</h4>
            
            <!-- 核心驱动 -->
            <div class="persona-dimension" v-if="parsedPersona.why">
              <div class="dimension-header">
                <span class="dimension-icon"></span>
                <strong>核心驱动 (Why)</strong>
              </div>
              <div class="dimension-content">{{ parsedPersona.why }}</div>
            </div>

            <!-- 认知过滤 -->
            <div class="persona-dimension" v-if="parsedPersona.filter">
              <div class="dimension-header">
                <span class="dimension-icon">🔍</span>
                <strong>认知过滤 (Filter)</strong>
              </div>
              <div class="dimension-content">{{ parsedPersona.filter }}</div>
            </div>

            <!-- 受众画像 -->
            <div class="persona-dimension" v-if="parsedPersona.who">
              <div class="dimension-header">
                <span class="dimension-icon">👥</span>
                <strong>受众画像 (Who)</strong>
              </div>
              <div class="dimension-content">
                <div v-if="parsedPersona.who.profile"><strong>画像：</strong>{{ parsedPersona.who.profile }}</div>
                <div v-if="parsedPersona.who.pain_points && parsedPersona.who.pain_points.length > 0">
                  <strong>痛点：</strong>
                  <span v-for="(p, i) in parsedPersona.who.pain_points" :key="i">{{ p }}{{ i < parsedPersona.who.pain_points.length - 1 ? '、' : '' }}</span>
                </div>
                <div v-if="parsedPersona.who.empathy_phrases && parsedPersona.who.empathy_phrases.length > 0">
                  <strong>共情话术：</strong>
                  <span v-for="(p, i) in parsedPersona.who.empathy_phrases" :key="i">{{ p }}{{ i < parsedPersona.who.empathy_phrases.length - 1 ? ' | ' : '' }}</span>
                </div>
              </div>
            </div>

            <!-- 能力边界 -->
            <div class="persona-dimension" v-if="parsedPersona.edge">
              <div class="dimension-header">
                <span class="dimension-icon">📐</span>
                <strong>能力边界 (Edge)</strong>
              </div>
              <div class="dimension-content">
                <div v-if="parsedPersona.edge.focus"><strong>专注：</strong>{{ parsedPersona.edge.focus }}</div>
                <div v-if="parsedPersona.edge.avoid"><strong>回避：</strong>{{ parsedPersona.edge.avoid }}</div>
              </div>
            </div>

            <!-- 表达范式 -->
            <div class="persona-dimension" v-if="parsedPersona.voice">
              <div class="dimension-header">
                <span class="dimension-icon">✍️</span>
                <strong>表达范式 (Voice)</strong>
              </div>
              <div class="dimension-content">
                <div v-if="parsedPersona.voice.tone"><strong>语气：</strong>{{ parsedPersona.voice.tone }}</div>
                <div v-if="parsedPersona.voice.structure"><strong>结构：</strong>{{ parsedPersona.voice.structure }}</div>
                <div v-if="parsedPersona.voice.ratio"><strong>比例：</strong>{{ parsedPersona.voice.ratio }}</div>
                <div v-if="parsedPersona.voice.forbidden"><strong>禁用：</strong>{{ parsedPersona.voice.forbidden }}</div>
              </div>
            </div>

            <!-- 价值标准 -->
            <div class="persona-dimension" v-if="parsedPersona.value">
              <div class="dimension-header">
                <span class="dimension-icon">💎</span>
                <strong>价值标准 (Value)</strong>
              </div>
              <div class="dimension-content">
                <div v-if="parsedPersona.value.gold_standard"><strong>金标准：</strong>{{ parsedPersona.value.gold_standard }}</div>
                <div v-if="parsedPersona.value.checklist && parsedPersona.value.checklist.length > 0">
                  <strong>检查清单：</strong>
                  <ul class="checklist">
                    <li v-for="(c, i) in parsedPersona.value.checklist" :key="i">{{ c }}</li>
                  </ul>
                </div>
              </div>
            </div>

            <!-- 兼容旧格式：简单四字段 -->
            <div v-if="!parsedPersona.why && !parsedPersona.who" class="persona-legacy">
              <div class="persona-item" v-if="parsedPersona.role || parsedPersona.who_am_i">
                <strong>我是谁：</strong>{{ parsedPersona.role || parsedPersona.who_am_i }}
              </div>
              <div class="persona-item" v-if="parsedPersona.target_audience">
                <strong>目标读者：</strong>{{ parsedPersona.target_audience }}
              </div>
              <div class="persona-item" v-if="parsedPersona.domain || parsedPersona.expertise">
                <strong>专业领域：</strong>{{ parsedPersona.domain || parsedPersona.expertise }}
              </div>
              <div class="persona-item" v-if="parsedPersona.style">
                <strong>写作风格：</strong>{{ parsedPersona.style }}
              </div>
            </div>

            <!-- 整体描述 -->
            <div class="persona-summary" v-if="parsedPersona.summary">
              <strong>📋 整体描述（将传给内容生成LLM）：</strong>
              <div>{{ parsedPersona.summary }}</div>
            </div>

            <a-button type="primary" status="success" @click="confirmPersona" style="margin-top: 12px">
              确认使用此身份定位
            </a-button>
          </div>

          <a-divider />

          <a-typography-text type="secondary" style="font-size: 12px">
            <icon-info-circle />
            身份定位文件用于指导 AI 生成更符合你个人风格的内容。如果未设置，AI 将使用通用风格。
          </a-typography-text>
        </a-card>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import {
  IconFolder,
  IconPlus,
  IconDelete,
  IconRefresh,
  IconInfoCircle,
  IconFile,
  IconRobot,
  IconSave,
  IconCheckCircleFill,
  IconImage,
  IconList,
  IconUser,
} from '@arco-design/web-vue/es/icon'
import { useAppStore } from '../stores/app'
import { verifyFolder as apiVerifyFolder, listFolderFiles, readFolderFile, setPersonaPath, parsePersona, getPersonaInfo } from '../utils/api'

const router = useRouter()
const appStore = useAppStore()

const settings = ref({
  knowledgeFolders: [],
  llm: {
    provider: 'deepseek',
    apiKey: '',
    baseUrl: 'https://api.deepseek.com/v1',
    model: 'deepseek-chat',
  },
  outputDir: 'output',
  defaultStyle: 'minimal',
  defaultSize: 'default',
})

const newFolderPath = ref('')
const personaPath = ref('')
const kbTreeData = ref([])
const kbLoading = ref(false)
const loadProgress = ref(0)
const personaParsing = ref(false)
const parsedPersona = ref(null)
const complexityWarning = ref('')
const personaSaved = ref(false) // 是否已保存身份定位路径

onMounted(async () => {
  loadSettings()
  loadKbFiles()
  
  // 恢复身份定位路径
  const cachedPersonaPath = localStorage.getItem('archgen_persona_path')
  if (cachedPersonaPath) {
    personaPath.value = cachedPersonaPath
    personaSaved.value = true
  }

  // 每次打开设置页面，从后端重新获取最新解析结果
  // 优先使用后端缓存/解析，保证数据最新
  try {
    const res = await getPersonaInfo()
    if (res.data.code === 0 && res.data.data.parsed) {
      const parsed = res.data.data.parsed
      parsedPersona.value = parsed
      appStore.personaInfo = parsed
      // 同步到 localStorage 缓存
      localStorage.setItem('archgen_parsed_persona', JSON.stringify(parsed))
    } else if (cachedPersonaPath && personaSaved.value) {
      // 如果后端没有解析结果，但路径已保存，自动触发解析
      await handleParsePersona()
    }
  } catch (e) {
    console.error('获取身份定位信息失败:', e)
    // 降级：尝试从 localStorage 恢复
    const cachedParsedPersona = localStorage.getItem('archgen_parsed_persona')
    if (cachedParsedPersona) {
      try {
        parsedPersona.value = JSON.parse(cachedParsedPersona)
        appStore.personaInfo = parsedPersona.value
      } catch (e2) {
        console.error('加载本地缓存失败:', e2)
      }
    }
  }
})

const loadSettings = () => {
  const saved = localStorage.getItem('archgen_settings')
  if (saved) {
    try {
      const parsed = JSON.parse(saved)
      settings.value = { ...settings.value, ...parsed }
    } catch (e) {
      console.error('加载设置失败:', e)
    }
  }
}

const saveSettings = () => {
  localStorage.setItem('archgen_settings', JSON.stringify(settings.value))
}

const addFolder = () => {
  if (!newFolderPath.value.trim()) {
    Message.warning('请输入文件夹路径')
    return
  }

  const path = newFolderPath.value.trim()
  const exists = settings.value.knowledgeFolders.some(f => f.path === path)
  if (exists) {
    Message.warning('该文件夹已添加')
    return
  }

  settings.value.knowledgeFolders.push({
    path,
    status: 'verifying',
  })
  newFolderPath.value = ''
  saveSettings()
  Message.info('文件夹已添加，正在验证...')
  verifyFolder(settings.value.knowledgeFolders.length - 1)
}

const verifyFolder = async (index) => {
  const folder = settings.value.knowledgeFolders[index]
  folder.status = 'verifying'

  try {
    const result = await apiVerifyFolder(folder.path)
    if (result.data.code === 0) {
      folder.status = 'connected'
      folder.error = ''
      Message.success('文件夹连接成功')
      saveSettings()
      loadKbFiles()
    } else {
      folder.status = 'error'
      folder.error = result.data.msg || '验证失败'
      Message.error('文件夹连接失败: ' + (result.data.msg || '未知错误'))
      saveSettings()
    }
  } catch (error) {
    folder.status = 'error'
    folder.error = error.message
    Message.error('文件夹连接失败: ' + error.message)
    saveSettings()
  }
}

const removeFolder = (index) => {
  settings.value.knowledgeFolders.splice(index, 1)
  saveSettings()
  kbTreeData.value = []
  Message.success('已移除文件夹')
}

const buildTreeData = (treeNodes, folderPath) => {
  return treeNodes.map(node => {
    if (node.type === 'folder') {
      return {
        key: node.path,
        title: node.name,
        type: 'folder',
        file_count: node.file_count,
        children: buildTreeData(node.children || [], folderPath),
      }
    }
    return {
      key: node.path,
      title: node.name,
      type: 'file',
      size: node.size,
      folder_path: folderPath,
      full_path: node.full_path,
    }
  })
}

const loadKbFiles = async () => {
  if (settings.value.knowledgeFolders.length === 0) {
    kbTreeData.value = []
    return
  }

  kbLoading.value = true
  loadProgress.value = 0
  try {
    const connectedFolders = settings.value.knowledgeFolders.filter(f => f.status === 'connected')
    const total = connectedFolders.length
    const allTreeData = []
    let done = 0

    for (const folder of connectedFolders) {
      loadProgress.value = Math.round((done / total) * 90)
      try {
        const result = await listFolderFiles(folder.path)
        if (result.data.code === 0 && result.data.data) {
          const treeData = buildTreeData(result.data.data, folder.path)
          allTreeData.push({
            key: folder.path,
            title: folder.path.split('/').pop() || folder.path,
            type: 'folder',
            children: treeData,
          })
        }
      } catch (e) {
        console.error(`加载文件夹 ${folder.path} 失败:`, e)
      }
      done++
    }

    loadProgress.value = 100
    kbTreeData.value = allTreeData
  } catch (error) {
    console.error('加载文件夹树失败:', error)
    Message.error('加载文件失败: ' + error.message)
  } finally {
    kbLoading.value = false
    setTimeout(() => { loadProgress.value = 0 }, 500)
  }
}

const onTreeSelect = async (selectedKeys, extra) => {
  const node = extra.selectedNodes[0]
  if (!node || node.type === 'folder') return

  try {
    const filePath = node.key
    const folderPath = node.folder_path
    const result = await readFolderFile(folderPath, filePath)
    if (result.data.code === 0) {
      appStore.inputText = result.data.data.content
      appStore.kbFile = {
        name: node.title,
        path: filePath,
        folderPath: folderPath,
      }
      Message.success(`已加载: ${node.title}`)
      router.push('/')
    } else {
      Message.error('读取失败: ' + result.data.msg)
    }
  } catch (error) {
    Message.error('读取失败: ' + error.message)
  }
}

const getFileColor = (name) => {
  if (/\.(jpg|jpeg|png|gif|webp)$/i.test(name)) return '#27ae60'
  if (/\.(md|txt|markdown)$/i.test(name)) return '#3498db'
  if (/\.pdf$/i.test(name)) return '#e74c3c'
  return '#666'
}

const formatSize = (bytes) => {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const saveLlmSettings = () => {
  saveSettings()
  Message.success('AI 设置已保存')
}

const saveOutputSettings = () => {
  saveSettings()
  Message.success('输出设置已保存')
}

const savePersonaPath = async () => {
  if (!personaPath.value.trim()) {
    Message.warning('请输入文件路径')
    return
  }
  // 持久化路径到 localStorage
  localStorage.setItem('archgen_persona_path', personaPath.value.trim())
  personaSaved.value = true
  try {
    const res = await setPersonaPath(personaPath.value.trim())
    if (res.data.code === 0) {
      Message.success('身份定位路径已保存，正在解析...')
      // 保存后自动解析
      await handleParsePersona()
    } else {
      Message.error(res.data.msg)
    }
  } catch (error) {
    Message.error('保存失败: ' + error.message)
  }
}

const handleParsePersona = async () => {
  if (!personaPath.value.trim()) {
    Message.warning('请输入身份定位文件路径')
    return
  }
  personaParsing.value = true
  complexityWarning.value = ''
  try {
    const res = await parsePersona(personaPath.value.trim())
    if (res.data.code === 0) {
      const responseData = res.data.data
      const raw = responseData.parsed || responseData
      
      // 设置复杂度警告
      complexityWarning.value = responseData.complexity_warning || ''
      if (raw.complexity_note) {
        complexityWarning.value = raw.complexity_note
      }
      
      // 六维模型直接使用后端返回的结构
      parsedPersona.value = {
        why: raw.why || '',
        filter: raw.filter || '',
        who: raw.who || {},
        edge: raw.edge || {},
        voice: raw.voice || {},
        value: raw.value || {},
        summary: raw.summary || '',
        raw_summary: raw.raw_summary || '',
        // 兼容旧格式
        role: raw.who_am_i || raw.role || '',
        target_audience: raw.target_audience || '',
        domain: raw.expertise || raw.domain || '',
        style: raw.style || '',
      }
      Message.success('身份定位解析成功')
    } else {
      Message.error('解析失败: ' + res.data.msg)
    }
  } catch (error) {
    Message.error('解析失败: ' + error.message)
  } finally {
    personaParsing.value = false
  }
}

const confirmPersona = () => {
  if (!parsedPersona.value) {
    Message.warning('请先解析身份定位')
    return
  }
  appStore.personaInfo = parsedPersona.value
  localStorage.setItem('archgen_persona', JSON.stringify(parsedPersona.value))
  Message.success('身份定位已确认，将在内容生成中使用')
}

// 加载缓存的身份定位
const loadPersona = () => {
  const cached = localStorage.getItem('archgen_persona')
  if (cached) {
    try {
      const parsed = JSON.parse(cached)
      parsedPersona.value = parsed
      appStore.personaInfo = parsed
    } catch (e) {
      console.error('加载身份定位缓存失败:', e)
    }
  }
}
</script>

<style scoped>
.settings-view {
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
.tip-alert {
  margin-bottom: 20px;
}
.folder-list {
  margin-bottom: 20px;
}
.folder-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 8px;
}
.folder-info {
  display: flex;
  align-items: center;
  gap: 12px;
}
.folder-icon {
  font-size: 24px;
  color: #3498db;
}
.folder-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.folder-path {
  font-size: 14px;
  color: #333;
}
.folder-status {
  font-size: 12px;
}
.folder-error {
  margin-left: 8px;
  color: #e74c3c;
}
.folder-status.connected {
  color: #27ae60;
}
.folder-status.error {
  color: #e74c3c;
}
.folder-status.verifying {
  color: #f39c12;
}
.add-folder-row {
  width: 100%;
}
.folder-help {
  margin-top: 12px;
}
.kb-file-list {
  max-height: 400px;
  overflow-y: auto;
}
.kb-tree-container {
  max-height: 500px;
  overflow-y: auto;
  padding: 10px;
  background: #fafafa;
  border-radius: 8px;
}
.tree-node-title {
  font-size: 14px;
}
.tree-node-meta {
  font-size: 12px;
  color: #999;
  margin-left: 6px;
}
.persona-result {
  margin-top: 16px;
  padding: 16px;
  background: #f0f7ff;
  border: 1px solid #b3d8ff;
  border-radius: 8px;
}
.persona-result h4 {
  margin: 0 0 12px;
  font-size: 14px;
  color: #1d2129;
}
.persona-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}
.persona-item {
  padding: 10px 12px;
  background: #fff;
  border: 1px solid #e5e6eb;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.6;
  color: #4e5969;
}
.persona-item strong {
  color: #1d2129;
  display: block;
  margin-bottom: 4px;
}
/* 六维度展示 */
.persona-dimension {
  margin-bottom: 12px;
  padding: 12px 14px;
  background: #fff;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  border-left: 3px solid #165dff;
}
.dimension-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.dimension-icon {
  font-size: 16px;
}
.dimension-header strong {
  font-size: 14px;
  color: #1d2129;
}
.dimension-content {
  font-size: 13px;
  line-height: 1.7;
  color: #4e5969;
}
.dimension-content strong {
  color: #1d2129;
}
.dimension-content ul.checklist {
  margin: 4px 0;
  padding-left: 18px;
}
.dimension-content ul.checklist li {
  margin-bottom: 2px;
}
.persona-legacy {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-bottom: 12px;
}
.persona-summary {
  margin-top: 16px;
  padding: 14px;
  background: #f7f8fa;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.7;
  color: #4e5969;
}
.persona-summary strong {
  display: block;
  margin-bottom: 6px;
  color: #1d2129;
  font-size: 14px;
}
</style>
