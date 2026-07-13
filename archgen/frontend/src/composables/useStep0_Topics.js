import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { useSession } from './useSession'
import { mcpSuggest as apiMcpSuggest, supplementStep1 } from '../utils/api'
// 延迟引用：在运行时由 useStep2_Framework 初始化
let _loadFrameworksFn = null
export function setLoadFrameworksRef(fn) { _loadFrameworksFn = fn }

// ==================== 模块级单例状态 ====================

const { sessionId, currentStep, collapsedSteps } = useSession()

// 基础状态
const mcpSummary = ref('')
const mcpFiles = ref([])
const kbTreeData = ref([])
const mcpTopic = ref('')

// 话题推荐
const topics = ref([])
const topicsLoading = ref(false)
const scannedFolders = ref([])
const fileCount = ref(0)

// 方向推荐
const directionsLoading = ref(false)
const selectedDirection = ref(null)

// route 在 useStep0_Topics() 内初始化
let _route = null

// ==================== 辅助函数 ====================

function convertToTreeData(items) {
  return (items || []).map(item => ({
    key: item.path,
    title: item.name,
    isLeaf: item.type === 'file',
    children: item.type === 'folder' && item.children ? convertToTreeData(item.children) : undefined,
  }))
}

// ==================== 核心函数 ====================

async function loadTopics() {
  topicsLoading.value = true
  try {
    const folders = scannedFolders.value.length > 0
      ? scannedFolders.value
      : (_route?.query?.folders ? JSON.parse(_route.query.folders) : [])

    if (!folders.length) {
      Message.warning('缺少知识库文件夹信息')
      return
    }

    const res = await apiMcpSuggest({
      session_id: sessionId.value,
      topic: _route?.query?.topic || '',
      folders,
      categories: _route?.query?.categories ? JSON.parse(_route.query.categories) : [],
      time_range: _route?.query?.timeRange || 'all',
      start_date: _route?.query?.startDate || '',
      end_date: _route?.query?.endDate || '',
    })

    if (res.data.code === 0) {
      topics.value = (res.data.data.topics || []).map(t => {
        const coverage = t.coverage || 0.5
        const evalData = t.evaluation || {
          direction_score: Math.round(coverage * 100),
          deficiency_score: Math.round((1 - coverage) * 100),
          overall_score: Math.round(coverage * 100),
          direction_analysis: t.reason || '',
          supplement_strategy: coverage >= 0.7 ? '信息充足' : coverage >= 0.4 ? '需补充关键信息' : '素材严重不足'
        }
        // 保留后端客观计算的字段
        if (!evalData.deficiency_details || !evalData.deficiency_details.length) {
          evalData.deficiency_details = t.deficiency_details || (t.needed ? [{ item: t.needed, severity: 'medium', explanation: t.needed }] : [])
        }
        if (!evalData.satisfied_details || !evalData.satisfied_details.length) {
          evalData.satisfied_details = t.satisfied_details || []
        }
        if (!evalData.signal_report || !Object.keys(evalData.signal_report).length) {
          evalData.signal_report = t.signal_report || {}
        }
        return {
          ...t,
          ...evalData,
          evaluation: evalData
        }
      })
      mcpSummary.value = res.data.data.summary || ''
      if (mcpSummary.value) {
        localStorage.setItem('archgen_mcp_summary', mcpSummary.value)
      }
      mcpFiles.value = res.data.data.source_files || []
      fileCount.value = res.data.data.file_count || 0
      scannedFolders.value = folders
    } else {
      Message.error(res.data.msg || '话题推荐失败')
    }
  } catch (e) {
    Message.error('话题推荐失败: ' + e.message)
  } finally {
    topicsLoading.value = false
  }
}

async function refreshTopics() {
  selectedDirection.value = null
  await loadTopics()
  Message.success('已刷新选题推荐')
}

function toggleStepCollapse(stepIndex) {
  collapsedSteps.value[stepIndex] = !collapsedSteps.value[stepIndex]
}

// 选择方向并前进
async function selectDirectionAndAdvance(t) {
  selectedDirection.value = { name: t.name, description: t.description }
  mcpTopic.value = t.name
  Message.success(`已选择「${t.name}」，正在加载框架...`)
  try {
    await supplementStep1(sessionId.value, t.name, {})
  } catch (e) {
    console.warn('保存方向到 session 失败:', e)
  }
  currentStep.value = 1
}

async function selectDirection(d) {
  selectedDirection.value = d
  directionsLoading.value = true
  Message.info(`已选择「${d.name}」，正在推荐框架...`)
  try {
    await supplementStep1(sessionId.value, d.name, {})
  } catch (e) {
    Message.error('保存方向失败: ' + e.message)
    return
  }
  if (_loadFrameworksFn) {
    _loadFrameworksFn()
  }
}

// ==================== 导出 ====================

export function useStep0_Topics() {
  _route = useRoute()
  return {
    topics,
    topicsLoading,
    scannedFolders,
    fileCount,
    mcpSummary,
    mcpFiles,
    kbTreeData,
    mcpTopic,
    directionsLoading,
    selectedDirection,
    loadTopics,
    refreshTopics,
    toggleStepCollapse,
    selectDirectionAndAdvance,
    selectDirection,
    convertToTreeData,
  }
}
