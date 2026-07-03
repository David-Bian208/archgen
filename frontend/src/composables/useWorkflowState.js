import { ref, reactive, computed, watch, nextTick, h, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Message, Modal } from '@arco-design/web-vue'
import { marked } from 'marked'
import { useAppStore } from '../stores/app'
import {
  createWorkflowSession,
  getWorkflowSessionStatus,
  evaluateCompleteness,
  analyzeDirectionsV2,
  supplementStep1,
  matchFrameworksV2,
  supplementStep2,
  checkWorkflowDirection,
  fixWorkflowDirection,
  recommendStructures,
  supplementStep3,
  generateWorkflowOutline,
  generateFullArticle,
  listFolderFiles,
  aiAutoSupplement as apiAiAutoSupplement,
  aiPulseSupplement as apiAiPulseSupplement,
  aiInferSupplement as apiInferSupplement,
  smartSupplement as apiSmartSupplement,
  degradeSupplement as apiDegradeSupplement,
  supplementDraft as apiSupplementDraft,
  recordAnalyticsEvent,
  readFolderFile,
  addSupplement as apiAddSupplement,
  confirmSupplement as apiConfirmSupplement,
  listSupplements as apiListSupplements,
  generateDiagram as apiGenerateDiagram,
  generateInfographic as apiGenerateInfographic,
  reviseInfographic as apiReviseInfographic,
  mcpSuggest as apiMcpSuggest,
  fillFramework as apiFillFramework,
  getFrameworkSlots,
} from '../utils/api'

import { useSession } from './useSession'
const { sessionId, currentStep, loading } = useSession()

// ==================== 模块级单例状态 ====================
// 设计决策：useWorkflowState 使用模块级单例模式（而非工厂模式）。
// 理由：此 composable 被唯一的 WorkflowView.vue 挂载，整个 SPA 生命周期内
// 只存在一个实例。Vue 3 的 Composables 推荐工厂模式用于多实例场景，
// 但在本项目中单例是正确的选择——它确保所有子组件共享同一份工作流状态。
// 如果将来需要支持多个并行工作流，再改为工厂模式。
//
// sessionId / currentStep / loading 来自 useSession 单例

// ==================== 基础状态 ====================
const collapsedSteps = ref({})
const mcpSummary = ref('')
const mcpFiles = ref([])
const kbTreeData = ref([])
const mcpTopic = ref('')

// ==================== 话题推荐 ====================
const topics = ref([])
const topicsLoading = ref(false)
const scannedFolders = ref([])
const fileCount = ref(0)

// ==================== 完整度评估 ====================
const completenessResult = ref(null)

const completenessPercent = computed(() => {
  if (!completenessResult.value) return 0
  const raw = completenessResult.value.completeness || 0
  if (raw <= 1 && raw > 0) {
    return Math.round(raw * 100)
  }
  return Math.min(Math.max(Math.round(raw), 0), 100)
})

const manualCompleteness = computed(() => {
  if (!completenessResult.value) return completenessPercent.value
  const missingCritical = completenessResult.value.missing_critical || []
  const total = missingCritical.length
  if (total === 0) return completenessPercent.value
  const supplemented = missingCritical.filter((_, idx) => isSupplemented(idx)).length
  const ratio = supplemented / total
  const baseCompleteness = completenessPercent.value
  const bonus = Math.round(ratio * (100 - baseCompleteness) * 0.5)
  return Math.min(baseCompleteness + bonus, 100)
})

const displayCompleteness = computed(() => {
  if (!completenessResult.value) return 0
  const supplemented = completenessResult.value.missing_critical?.filter((_, idx) => isSupplemented(idx)).length || 0
  if (supplemented > 0) {
    return manualCompleteness.value
  }
  return completenessPercent.value
})

const supplementContents = ref({})

function isSupplemented(index) {
  return supplementContents.value[index] !== undefined
}

function getSupplementContent(index) {
  return supplementContents.value[index]?.content || ''
}

// ==================== 方向推荐 ====================
const directions = ref([])
const selectedDirection = ref(null)
const directionsLoading = ref(false)

// ==================== 关键缺失项补充弹窗 ====================
const supplementModalVisible = ref(false)
const currentSupplementItem = ref('')
const currentSupplementIndex = ref(-1)
const isEditMode = ref(false)

// ==================== 编辑弹窗 ====================
const editModalVisible = ref(false)
const editOriginalContent = ref('')
const editNewContent = ref('')
const editAiSuggestion = ref('')
const editAiLoading = ref(false)
const editSaving = ref(false)

// ==================== 框架补充 AI 建议 ====================
const frameworkAiSuggestion = ref('')
const frameworkAiLoading = ref(false)
const frameworkSelectedIndex = ref(-1)

// ==================== 检测问题 AI 帮助 ====================
const issueAiHelp = ref({})

// ==================== 结构补充 AI 辅助 ====================
const structureAiSuggestion = ref('')
const structureAiLoading = ref(false)

// ==================== 分步骤工作流 ====================
const supplementStep = ref(1)
const supplementApiLoading = ref(false)
const supplementApiCases = ref([])
const supplementApiSelectedCases = ref([])
const supplementInferLoading = ref(false)
const supplementInferResult = ref(null)
const supplementSaving = ref(false)

// ==================== 批量操作 ====================
const batchAiPulseLoading = ref(false)
const batchManualLoading = ref(false)
const batchUnifiedLoading = ref(false)
const batchAiPulseModalVisible = ref(false)
const batchManualModalVisible = ref(false)
const batchAiPulseResults = ref([])
const batchManualTexts = ref({})

// ==================== 统一补充弹窗 ====================
const unifiedModalVisible = ref(false)
const unifiedModalStep = ref(1)
const unifiedModalItem = ref('')
const unifiedModalItemIndex = ref(-1)
const unifiedApiCases = ref([])
const unifiedApiSelected = ref([])
const unifiedApiLoading = ref(false)
const unifiedInferLoading = ref(false)
const unifiedInferResult = ref(null)
const unifiedSaving = ref(false)

// ==================== 草稿模式 ====================
const draftModalVisible = ref(false)
const draftModalItem = ref('')
const draftModalItemIndex = ref(-1)
const draftContent = ref('')
const draftLoading = ref(false)
const draftSaving = ref(false)

// ==================== 旧版补充状态 ====================
const supplementModalMethod = ref('text')
const supplementModalFile = ref([])
const supplementModalText = ref('')
const aiSupplementing = ref(false)
const extractingFileContent = ref(false)
const extractedFileContent = ref(false)
const extractedFileCount = ref(0)

// ==================== 智能补充状态 ====================
const smartSupplementResult = ref(null)
const smartSupplementLoading = ref(false)
const currentKnowledgeLevel = ref('L1')
const canDegrade = ref(false)
const degradationCount = ref(0)

// ==================== 补充对话框状态 ====================
const supplementDialogVisible = ref(false)
const supplementDialogItem = ref({ title: '', issueIdx: -1 })
const step2SupplementDialogVisible = ref(false)
const step2SupplementDialogRef = ref(null)
const supplementDialogRef = ref(null)

// ==================== 补充内容状态 ====================
const supplementConfirmed = ref(false)
const isFirstScan = ref(true)
const scanStatus = ref('')

// ==================== 补充1状态 ====================
const supplement1Method = ref('form')
const supplement1File = ref([])
const supplement1Text = ref('')
const supplement1Form = reactive({
  targetAudience: '',
  scenarios: [],
  expectedBenefit: '',
  otherInfo: '',
})
const supplement1Result = ref(null)

// ==================== 框架推荐状态 ====================
const frameworks = ref([])
const selectedFramework = ref(null)
const frameworksMode = ref('premium')
const frameworksBanner = ref('')
const frameworksLoading = ref(false)
const expandedWarnings = ref({})

// ==================== 补充2状态 ====================
const supplement2Method = ref('text')
const supplement2File = ref([])
const supplement2Text = ref('')
const supplement2UploadFiles = ref([])
const supplement2KbFiles = ref([])
const pendingSupplementData = ref(null)
const supplement2Html = ref('')

// ==================== 素材池（方案 B：做加法） ====================
const materialPool = ref([])  // [{ type: 'inference', content: '...', ts }, { type: 'kb_file', path: '...', name: '...', content: '...', ts }, { type: 'ai_pulse', title: '...', source: '...', summary: '...', url: '...', ts }]

// ==================== 补充2 分析状态 ====================
const analysisBody = ref('')
const slotCoverage = ref({})
const frameworkFillLoading = ref(false)
const supplement2Form = reactive({
  painPoint: '',
  solution: '',
  pitfalls: '',
})

// ==================== 预检测状态 ====================
const preCheckResult = ref(null)
const preCheckLoading = ref(false)
const expandedIssues = ref(new Set())
const aiAutoSupplementLoading = ref(false)
const supplementLoading = ref(false)
const supplementAllLoading = ref(false)

// 槽位缺口匹配：把 preCheck issues 按关键词分发给各个槽位
// 需要外部传入 slotDefs（由 useStep3_Workbench 提供），否则返回空对象
const slotGapMatches = computed(() => {
  return {} // slotDefs 由 FrameworkWorkbench 传入，此处占位
})

// 用这个函数在 WorkflowView 中重新计算带 slotDefs 的缺口匹配
function computeSlotGapMatches(slotDefs) {
  if (!preCheckResult.value?.issues || !slotDefs) return {}
  const result = {}
  for (const [key, def] of Object.entries(slotDefs)) {
    const name = def.label || def.name || key
    const keywords = name.split(/[与和\s]+/).filter(k => k.length >= 2).map(k => k.toLowerCase())
    const matchedIssues = preCheckResult.value.issues.filter(issue => {
      const text = `${issue.title || ''} ${issue.description || ''} ${issue.explanation || ''}`.toLowerCase()
      return keywords.some(kw => text.includes(kw))
    })
    result[key] = {
      hasExisting: matchedIssues.filter(i => i.impact === 'positive').length > 0,
      gaps: [...new Set(matchedIssues.filter(i => i.impact !== 'positive').map(i => i.title || i.description))]
    }
  }
  return result
}

// ==================== 补充元数据 ====================
const lastSupplementMeta = ref(null)

// ==================== 检测页状态 ====================
const fixedCheckIssues = ref({})

// ==================== 检测相关 refs ====================
const checkingDirection = ref(false)
const directionCheckResult = ref(null)
const directionCheckMeta = ref({ force_passed: false, ready_for_next: true, check_count: 0, overall_score: 0 })
const fixingIssueIndex = ref(-1)
const editingIssueIndex = ref(-1)
const editingIssueContent = ref('')
const editingIssueLoading = ref(-1)
const aiSingleIssueLoading = ref(-1)

const hasErrors = computed(() => {
  if (!directionCheckResult.value) return false
  if (directionCheckMeta.value.force_passed) return false
  // ready_for_next 为 false 时也视为有错误（pending 状态不可继续）
  if (directionCheckMeta.value.ready_for_next === false) return true
  return directionCheckResult.value.some(issue => issue.level === 'block' || issue.type === 'error')
})

const blockIssues = computed(() => {
  if (!directionCheckResult.value) return []
  // 包含 level=block、type=error 以及 category=pending（后端前置拦截的待处理状态）
  return directionCheckResult.value.filter(issue => 
    issue.level === 'block' || issue.type === 'error' || issue.category === 'pending'
  )
})

const suggestIssues = computed(() => {
  if (!directionCheckResult.value) return []
  return directionCheckResult.value.filter(issue => issue.level === 'suggest' || (issue.type === 'warning' && issue.level !== 'block'))
})

// ==================== AI-Pulse 状态 ====================
const aiPulseLoading = ref(false)
const aiPulseCases = ref([])
const aiPulseSelectedCases = ref([])
const aiPulseKeywords = ref([])
const preloadingApiCases = ref(false)
const preloadedApiCases = ref([])

// ==================== 结构推荐状态 ====================
const structures = ref([])
const structuresLoading = ref(false)
const selectedStructure = ref(null)

// ==================== 提纲状态 ====================
const outlineResult = ref(null)
const showOutlineAlignmentReason = ref(false)
const targetWordCount = ref(2000)

const sectionAiDialogIndex = ref(-1)
const sectionAiInput = ref('')
const sectionAiLoading = ref(false)
const sectionAiResult = ref('')
const outlineOneClickLoading = ref(false)
const sectionAiKbFiles = ref([])
const sectionAiUploadFiles = ref([])

// ==================== 文章状态 ====================
const articleResult = ref(null)

const totalWordCount = computed(() => {
  if (!articleResult.value?.paragraphs) return 0
  return articleResult.value.paragraphs.reduce((sum, p) => sum + (p.word_count || 0), 0)
})

const readingTime = computed(() => {
  const minutes = Math.ceil(totalWordCount.value / 300)
  return minutes < 1 ? 1 : minutes
})

const articleAiDialogIndex = ref(-1)
const articleAiInput = ref('')
const articleAiKbFiles = ref([])
const articleAiUploadFiles = ref([])
const articleAiLoading = ref(false)
const articleAiResult = ref('')
const articleOneClickLoading = ref(false)

// ==================== 配图状态 ====================
const infographicHtml = ref('')
const infographicGenerating = ref(false)
const infographicRevising = ref(false)
const infographicFeedback = ref('')
const generatedImageUrl = ref('')
const imageGenerating = ref(false)

// ==================== 知识库收藏弹窗 ====================
const showExportModal = ref(false)
const exportDomainTag = ref('')
const exportingToDomain = ref(false)

// ==================== 批量统一结果 ====================
const batchResultModalVisible = ref(false)
const batchResults = ref([])

// ==================== AI 补充全部 ====================
const aiSupplementAllLoading = ref(false)

// ==================== 步骤相关计算属性 ====================

const allSupplementApiCasesSelected = computed(() => {
  return supplementApiCases.value.length > 0 && supplementApiSelectedCases.value.length === supplementApiCases.value.length && supplementApiSelectedCases.value.every(v => v)
})

const anySupplementApiCaseSelected = computed(() => {
  return supplementApiSelectedCases.value.some(v => v)
})

const selectedSupplementCasesSummary = computed(() => {
  if (!supplementApiCases.value.length) return null
  const selected = supplementApiCases.value.filter((_, i) => supplementApiSelectedCases.value[i])
  if (!selected.length) return null
  return {
    count: selected.length,
    cases: selected.map(c => ({ title: c.title, source: c.source })),
  }
})

const allCriticalSupplemented = computed(() => {
  if (!completenessResult.value) return false
  const missingCritical = completenessResult.value.missing_critical || []
  if (missingCritical.length === 0) return false
  return missingCritical.every((_, idx) => isSupplemented(idx))
})

const stepSummaries = computed(() => {
  const summaries = {}
  if (selectedDirection.value?.name) {
    summaries[0] = selectedDirection.value.name
  } else if (topics.value.length > 0) {
    summaries[0] = `${topics.value.length} 个推荐方向`
  }
  if (completenessResult.value?.missing_critical) {
    const supplemented = completenessResult.value.missing_critical.filter((_, idx) => isSupplemented(idx)).length
    summaries[1] = supplemented > 0 ? `补充了${supplemented}项` : ''
  } else if (supplement2Text.value) {
    const preview = supplement2Text.value.substring(0, 30)
    summaries[1] = `已补充：${preview}${supplement2Text.value.length > 30 ? '...' : ''}`
  }
  if (selectedFramework.value?.name) {
    summaries[2] = selectedFramework.value.name
  }
  if (directionCheckResult.value && Array.isArray(directionCheckResult.value)) {
    const problemCount = directionCheckResult.value.filter(issue => issue.type !== 'pass').length
    summaries[3] = problemCount > 0 ? `${problemCount}个问题` : '通过'
  }
  if (selectedStructure.value?.name) {
    summaries[4] = selectedStructure.value.name
  }
  if (outlineResult.value?.sections) {
    summaries[5] = `${outlineResult.value.sections.length} 个章节`
  }
  if (articleResult.value?.paragraphs) {
    const wordCount = articleResult.value.paragraphs.reduce((sum, p) => sum + (p.word_count || 0), 0)
    summaries[6] = wordCount > 0 ? `${wordCount} 字` : ''
  }
  if (infographicHtml.value) {
    summaries[7] = '已生成'
  }
  return summaries
})

const stepDetails = computed(() => {
  const details = {
    0: '未选题',
    1: '补充未开始',
    2: '未选框架',
    3: '未检测',
    4: '未选结构',
    5: '未生成提纲',
    6: '未生成文章',
    7: '未配图',
  }
  if (selectedDirection.value?.name) {
    details[0] = `已选题：「${selectedDirection.value.name}」`
    if (selectedDirection.value.description) {
      details[0] += `\n说明：${selectedDirection.value.description}`
    }
  }
  if (completenessResult.value?.missing_critical) {
    const total = completenessResult.value.missing_critical.length
    const done = completenessResult.value.missing_critical.filter((_, idx) => isSupplemented(idx)).length
    details[1] = `补充进度：${done}/${total} 项`
    if (completenessResult.value.supplement_strategy) {
      details[1] += `\n策略：${completenessResult.value.supplement_strategy}`
    }
  } else if (supplement2Text.value) {
    details[1] = `已通过 AI 补充完成（${supplement2Text.value.length} 字）\n\n${supplement2Text.value}`
  }
  if (selectedFramework.value?.name) {
    details[2] = `已选框架：「${selectedFramework.value.name}」`
    if (selectedFramework.value.description) {
      details[2] += `\n说明：${selectedFramework.value.description}`
    }
  }
  if (directionCheckResult.value && Array.isArray(directionCheckResult.value)) {
    const passCount = directionCheckResult.value.filter(i => i.type === 'pass').length
    const warnCount = directionCheckResult.value.filter(i => i.type === 'warning').length
    const failCount = directionCheckResult.value.filter(i => i.type === 'fail').length
    details[3] = `通过 ${passCount} 项，警告 ${warnCount} 项，未通过 ${failCount} 项`
    const firstFail = directionCheckResult.value.find(i => i.type !== 'pass')
    if (firstFail) {
      details[3] += `\n主要问题：${firstFail.message || ''}`
    }
  }
  if (selectedStructure.value?.name) {
    details[4] = `已选结构：「${selectedStructure.value.name}」`
    if (selectedStructure.value.description) {
      details[4] += `\n说明：${selectedStructure.value.description}`
    }
  }
  if (outlineResult.value?.sections) {
    const sections = outlineResult.value.sections
    details[5] = `共 ${sections.length} 个章节`
    sections.forEach((s, i) => {
      details[5] += `\n  ${i + 1}. ${s.title || s.name || ''}`
    })
  }
  if (articleResult.value) {
    const title = articleResult.value.title || ''
    const paragraphs = articleResult.value.paragraphs || []
    const wordCount = paragraphs.reduce((sum, p) => sum + (p.word_count || 0), 0)
    details[6] = `标题：${title}`
    details[6] += `\n段落数：${paragraphs.length} 个`
    details[6] += `\n总字数：${wordCount} 字`
  }
  if (infographicHtml.value) {
    details[7] = '配图已生成'
    if (selectedFramework.value?.name) {
      details[7] += `\n框架：${selectedFramework.value.name}`
    }
  }
  return details
})

const outlineCompletenessStatus = computed(() => {
  if (!outlineResult.value?.sections) return 'red'
  const sections = outlineResult.value.sections
  const anchoredCount = Object.values(sections).filter(s => s.source_tag === 'anchored').length
  const missingCount = outlineResult.value.missing_items?.length || 0
  if (anchoredCount >= 4 && missingCount <= 1) return 'green'
  if (anchoredCount >= 2 && missingCount <= 3) return 'yellow'
  return 'red'
})

/**
 * ============================================================
 *  共享状态合约  (Shared State Contract)
 * ============================================================
 *
 * 以下变量被多个 Step 组件共享读写。修改前必须检查所有使用方。
 *
 * ── 🔴 核心 ──
 *
 * @property {string} sessionId
 *   来源:    createWorkflowSession()
 *   消费方:  所有 API 调用
 *   约束:   创建后不修改
 *
 * @property {string} mcpSummary
 *   来源:    MCP 搜索 → scanKnowledgeBase()
 *   消费方:  DirectionSuggest, FrameworkSelect, Supplement, Generate
 *   约束:   Markdown 文本，可为空
 *
 * ── 🔴 Step 1-2 ──
 *
 * @property {{name:string}|null} selectedDirection
 *   来源:    analyzeDirectionsV2 API → selectDirection()
 *   消费方:  FrameworkSelect, Supplement
 *   约束:   name 非空
 *
 * @property {{key:string, name:string, ...}|null} selectedFramework
 *   来源:    matchFrameworksV2 → selectFramework()
 *   消费方:  Supplement, Workbench, Generate, sessionStorage
 *   约束:   必须包含 key。动态框架由后端自动生成 key+field_keywords
 *
 * @property {Array<object>} frameworks
 *   来源:    matchFrameworksV2 API
 *   消费方:  FrameworkSelect
 *   约束:   每项必须: key + name + field_keywords
 *
 * ── 🔴 补充（最高危区域）──
 *
 * @property {string} supplement2Text
 *   来源:    supplementStep2() API → 用户编辑
 *   消费方:  StepContent(富文本), sessionStorage(持久化), marked.parse()
 *   约束:   始终为 string。严禁写入对象/null。改此字段→同步检查 supplement2Html
 *
 * @property {string} supplement2Html
 *   来源:    watch(supplement2Text) → marked.parse() 自动转换
 *   消费方:  StepContent(v-html)
 *   约束:   禁止手动赋值，仅由 watcher 更新
 *
 * ── 🟡 检测 ──
 *
 * @property {Array|null} preCheckResult
 *   来源:    checkWorkflowDirection() API
 *   消费方:  StepContent, runPreCheck()
 *   约束:   [{title,type,level,detail}] 或 null
 *
 * @property {Array|null} directionCheckResult
 *   来源:    checkWorkflowDirection() API
 *   消费方:  StepCheck, goToCheck()
 *   约束:   [{title,type,level,category,detail,recurring?}] 或 null
 *
 * ── 🟢 生成 ──
 *
 * @property {object|null} outlineResult
 *   来源:    generateWorkflowOutline() API
 *   消费方:  StepOutline
 *
 * @property {object|null} articleResult
 *   来源:    generateFullArticle() API
 *   消费方:  StepArticle
 *
 * ============================================================
 *  修改规则:
 *    1. 改形状 → 搜所有"消费方"，逐个更新
 *    2. 改类型 → 加 defensive parse，防旧 session 崩溃
 *    3. 加字段 → 标注为可选，消费方全部用 ?.
 * ============================================================
 */

export function useWorkflowState() {
  const route = useRoute()
  const router = useRouter()
  const appStore = useAppStore()

  watch(supplement2Text, (val) => {
    if (!val) {
      supplement2Html.value = ''
      return
    }
    try {
      supplement2Html.value = marked.parse(val, { breaks: true, async: false })
    } catch (e) {
      console.error('marked 渲染失败:', e)
      supplement2Html.value = val
    }
  }, { immediate: true })

  function isCheckIssueFixed(idx) {
    return fixedCheckIssues.value[idx] !== undefined
  }
  function getCheckIssueFixContent(idx) {
    return fixedCheckIssues.value[idx]?.content || ''
  }

  const domainOptions = [
    { label: 'AI 效率工具', value: 'ai-efficiency' },
    { label: '商业分析', value: 'business-analysis' },
    { label: '产品设计', value: 'product-design' },
    { label: '运营优化', value: 'operations' },
    { label: '个人成长', value: 'personal-growth' },
    { label: '其他', value: 'other' },
  ]

  const stepNames = ['选题', '补充', '框架', '检测', '结构', '提纲', '文章', '配图']

  // ==================== 框架名称映射 ====================

  const FRAMEWORK_NAME_TO_KEY = {
    'SWOT 分析': 'swot',
    '商业模式画布': 'business_canvas',
    'PESTEL 分析': 'pestel',
    '用户旅程图': 'user_journey',
    '时间矩阵': 'time_matrix',
    '主张论证': 'claim',
    '因果分析': 'causal',
    '系统思考': 'system',
    '对比分析': 'comparison',
    '流程步骤': 'process',
  }

  // ==================== 工具函数 ====================

  const _timeoutIds = []

  function $setTimeout(fn, delay, ...args) {
    const id = window.setTimeout(fn, delay, ...args)
    _timeoutIds.push(id)
    return id
  }

  function convertToTreeData(items) {
    return (items || []).map(item => ({
      key: item.path,
      title: item.name,
      isLeaf: item.type === 'file',
      children: item.type === 'folder' && item.children ? convertToTreeData(item.children) : undefined,
    }))
  }

  function deriveFrameworkKey(framework) {
    if (!framework) {
      console.warn('[deriveFrameworkKey] 框架为空')
      return null
    }
    if (framework.key) {
      return framework.key
    }
    if (framework.name) {
      const key = FRAMEWORK_NAME_TO_KEY[framework.name]
      if (key) return key
      for (const [name, k] of Object.entries(FRAMEWORK_NAME_TO_KEY)) {
        if (framework.name.includes(name) || name.includes(framework.name)) {
          return k
        }
      }
      return framework.name.toLowerCase().replace(/\s+/g, '_')
    }
    return null
  }

  // ==================== 颜色辅助函数 ====================

  function getAlignmentColor(score) {
    const s = Number(score) || 0
    if (s >= 0.8) return '#00b42a'
    if (s >= 0.7) return '#86c34a'
    if (s >= 0.6) return '#f7ba1e'
    return '#c9cdd4'
  }

  function getAlignmentTagColor(score) {
    const s = Number(score) || 0
    if (s >= 0.8) return 'green'
    if (s >= 0.7) return 'arcoblue'
    if (s >= 0.6) return 'orange'
    return 'gray'
  }

  function getAlignmentBgColor(score) {
    const s = Number(score) || 0
    if (s >= 0.8) return '#f6ffed'
    if (s >= 0.7) return '#e8f7ed'
    if (s >= 0.6) return '#fff7e6'
    return '#f7f8fa'
  }

  function getAlignmentBorderColor(score) {
    const s = Number(score) || 0
    if (s >= 0.8) return '#b7eb8f'
    if (s >= 0.7) return '#c8e6c9'
    if (s >= 0.6) return '#ffd591'
    return '#e5e6eb'
  }

  function getAlignmentTextColor(score) {
    const s = Number(score) || 0
    if (s >= 0.8) return '#52c41a'
    if (s >= 0.7) return '#5ba43b'
    if (s >= 0.6) return '#d46b08'
    return '#86909c'
  }

  function getCoverageColor(coverage) {
    if (coverage >= 0.7) return 'green'
    if (coverage >= 0.5) return 'arcoblue'
    return 'gray'
  }

  function getIssueColor(type) {
    if (type === 'pass') return '#00b42a'
    if (type === 'warning') return '#f7ba1e'
    return '#f53f3f'
  }

  function getIssueTagColor(type) {
    if (type === 'pass') return 'green'
    if (type === 'warning') return 'warning'
    return 'red'
  }

  function getSourceTagColor(tag) {
    switch(tag) {
      case 'anchored': return '#00b42a'
      case 'derived': return '#165dff'
      case 'missing': return '#f53f3f'
      default: return '#86909c'
    }
  }

  function getSourceTagTagColor(tag) {
    switch(tag) {
      case 'anchored': return 'green'
      case 'derived': return 'arcoblue'
      case 'missing': return 'red'
      default: return 'gray'
    }
  }

  function getSourceTagLabel(tag) {
    switch(tag) {
      case 'anchored': return '✓ 已锚定'
      case 'derived': return '→ AI推断'
      case 'missing': return '✗ 缺失'
      default: return '未知'
    }
  }

  function getSectionNumber(key) {
    const order = ['hook', 'problem', 'breakdown', 'solution', 'action']
    return order.indexOf(key) + 1
  }

  function getSectionMissingItems(sectionKey) {
    if (!outlineResult.value?.missing_items) return []
    return outlineResult.value.missing_items.filter(item => item.section === sectionKey)
  }

  function getCompletenessStatusColor(status) {
    switch(status) {
      case 'green': return '#00b42a'
      case 'yellow': return '#f7ba1e'
      case 'red': return '#f53f3f'
      default: return '#86909c'
    }
  }

  function getCompletenessStatusLabel(status) {
    switch(status) {
      case 'green': return '🟢 结构完整'
      case 'yellow': return '🟡 部分缺失'
      case 'red': return '🔴 严重缺失'
      default: return '未知状态'
    }
  }

  function getCompletenessColor(score) {
    if (score >= 80) return '#00b42a'
    if (score >= 60) return '#f7ba1e'
    return '#f53f3f'
  }

  function getScoreColor(score) {
    if (score >= 80) return '#00b42a'
    if (score >= 60) return '#f7ba1e'
    return '#f53f3f'
  }

  function getScoreTagColor(score) {
    if (score >= 80) return 'green'
    if (score >= 60) return 'orange'
    return 'red'
  }

  function getScoreLabel(score) {
    if (score >= 80) return '素材充足'
    if (score >= 60) return '需补充后推进'
    return '素材不足'
  }

  function getReverseScoreColor(score) {
    if (score >= 80) return '#f53f3f'
    if (score >= 50) return '#f7ba1e'
    return '#00b42a'
  }

  // ==================== 保存工作流状态 ====================

  function saveWorkflowState() {
    try {
      const state = {
        sessionId: sessionId.value,
        currentStep: currentStep.value,
        supplement2Text: supplement2Text.value?.substring(0, 5000),
        selectedDirection: selectedDirection.value ? { name: selectedDirection.value.name } : null,
        selectedFramework: selectedFramework.value ? { name: selectedFramework.value.name } : null,
        savedAt: Date.now(),
      }
      sessionStorage.setItem('archgen_workflow_state', JSON.stringify(state))
    } catch (e) {
      // silent fail
    }
  }

  // ==================== 核心方法 ====================

  // 话题相关
  async function loadTopics() {
    topicsLoading.value = true
    try {
      const folders = scannedFolders.value.length > 0
        ? scannedFolders.value
        : (route.query.folders ? JSON.parse(route.query.folders) : [])

      if (!folders.length) {
        Message.warning('缺少知识库文件夹信息')
        return
      }

      const res = await apiMcpSuggest({
        topic: route.query.topic || '',
        folders,
        categories: route.query.categories ? JSON.parse(route.query.categories) : [],
        time_range: route.query.timeRange || 'all',
        start_date: route.query.startDate || '',
        end_date: route.query.endDate || '',
      })

      if (res.data.code === 0) {
        topics.value = (res.data.data.topics || []).map(t => {
          const coverage = t.coverage || 0.5
          const evalData = t.evaluation || {
            direction_score: Math.round(coverage * 100),
            deficiency_score: Math.round((1 - coverage) * 100),
            overall_score: Math.round(coverage * 100),
            direction_analysis: t.reason || '',
            deficiency_details: t.needed ? [{ item: t.needed, severity: 'medium', explanation: t.needed }] : [],
            supplement_strategy: coverage >= 0.7 ? '信息充足' : coverage >= 0.4 ? '需补充关键信息' : '素材严重不足'
          }
          return {
            ...t,
            ...evalData,
            evaluation: evalData
          }
        })
        mcpSummary.value = res.data.data.summary || ''
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
    loadFrameworks()
  }

  // 补充相关
  // 记录上一次检测的问题标题，用于判断问题是否重复出现
  const _previousIssueTitles = ref([])

  async function runPreCheck() {
    if (preCheckLoading.value) return
    preCheckLoading.value = true
    // 保存旧问题标题，用于对比
    const oldTitles = (preCheckResult.value?.issues || []).map(i => i.title)
    _previousIssueTitles.value = oldTitles
    try {
      const supplementData = { ...supplement2Form }
      if (supplement2Text.value) {
        supplementData.text = supplement2Text.value
      }
      const res = await checkWorkflowDirection(
        sessionId.value,
        selectedDirection.value?.name || '',
        selectedFramework.value?.name || '',
        supplementData,
        mcpSummary.value,
        mcpFiles.value,
        { text: supplement2Text.value || '' },
        analysisBody.value,
      )
      if (res.data.code === 0 && res.data.data) {
        const newIssues = (res.data.data.issues || []).filter(issue => issue.type !== 'pass')
        // 标记重复问题：若新问题标题与旧问题相同，说明补充后仍未解决
        const enrichedIssues = newIssues.map(issue => {
          const isRecurring = oldTitles.length > 0 && oldTitles.includes(issue.title)
          return {
            ...issue,
            recurring: isRecurring,
            // 重复问题自动降级为非阻塞（信任补充内容至少部分解决了问题）
            type: isRecurring ? 'suggestion' : issue.type,
          }
        })
        preCheckResult.value = {
          score: res.data.data.overall_score || 0,
          issues: enrichedIssues,
          ready_for_next: res.data.data.ready_for_next || false,
          // 如果所有问题都是重复出现的，则放宽准出条件
          all_recurring: enrichedIssues.length > 0 && enrichedIssues.every(i => i.recurring),
        }
        if (preCheckResult.value.all_recurring) {
          Message.success('预检测完成 — 补充已应用，仅有少量优化建议')
        } else {
          Message.success('预检测完成')
        }
      }
    } catch (e) {
      Message.error('预检测失败: ' + e.message)
    } finally {
      preCheckLoading.value = false
    }
  }

  async function handleFirstScan() {
    isFirstScan.value = false
    supplementLoading.value = true
    scanStatus.value = 'scanning'
    await runPreCheck()
    if (preCheckResult.value?.issues?.length > 0) {
      const missingTitles = preCheckResult.value.issues
        .filter(i => i.type !== 'pass')
        .map(i => i.title)
      if (missingTitles.length > 0) {
        scanStatus.value = 'supplementing'
        const missingItems = '需要补充以下内容项：' + missingTitles.join('、')
        const effectivePrompt = `请根据检测到的缺失项（${missingTitles.join('、')}），自动推断补充内容`
        try {
          const res = await apiInferSupplement(
            sessionId.value,
            missingItems,
            {
              mcp_summary: mcpSummary.value || '',
              kb_file_list: mcpFiles.value || [],
              user_prompt: effectivePrompt,
              user_files: [],
              existing_content: '',
            }
          )
          if (res.data.code === 0 && res.data.data) {
            const content = res.data.data.content || ''
            lastSupplementMeta.value = {
              inference_note: res.data.data.inference_note || '自动推断补充',
              supplement_type: res.data.data.supplement_type || 'infer',
              confidence: res.data.data.confidence || 0.7,
            }
            const supplementInfo = {
              text: content,
              inference_note: lastSupplementMeta.value.inference_note,
              supplement_type: lastSupplementMeta.value.supplement_type,
              confidence: lastSupplementMeta.value.confidence,
              files: mcpFiles.value?.slice(0, 10) || [],
            }
            supplement2Text.value = content
            pendingSupplementData.value = supplementInfo
            supplementConfirmed.value = false
            Message.success('自动补充完成，正在重新扫描...')
            scanStatus.value = 'rescanning'
            await runPreCheck()
            scanStatus.value = 'done'
            Message.success('补充完成，请确认后继续')
          } else {
            Message.warning('自动补充未返回内容，请手动补充')
          }
        } catch (e) {
          console.error('自动补充失败:', e)
          Message.error('自动补充失败，请手动补充')
        }
      }
    }
    scanStatus.value = ''
    supplementLoading.value = false
  }

  function openStep2SupplementDialog() {
    step2SupplementDialogVisible.value = true
  }

  async function handleStep2SupplementSubmit({ userPrompt, userFiles, useKB, selectedKBFiles, useWebSearch, webSearchKeyword }) {
    supplementLoading.value = true
    try {
      if (!preCheckResult.value) {
        await runPreCheck()
      }
      let missingItems = '分析内容待补充'
      if (preCheckResult.value?.issues) {
        const items = preCheckResult.value.issues
          .filter(i => i.type !== 'pass')
          .map(i => i.title)
        if (items.length > 0) {
          missingItems = '需要补充以下内容项：' + items.join('、')
        }
      }
      let effectivePrompt = userPrompt || ''
      if (!effectivePrompt && preCheckResult.value?.issues) {
        const missingTitles = preCheckResult.value.issues
          .filter(i => i.type !== 'pass')
          .map(i => i.title)
        if (missingTitles.length > 0) {
          effectivePrompt = `请根据检测到的缺失项（${missingTitles.join('、')}），自动推断补充内容`
        } else {
          effectivePrompt = '请根据检测到的缺失项，自动推断补充内容'
        }
      }
      step2SupplementDialogRef.value?.setProgressStep(1)
      const res = await apiInferSupplement(
        sessionId.value,
        missingItems,
        {
          mcp_summary: mcpSummary.value || '',
          kb_file_list: mcpFiles.value || [],
          user_prompt: effectivePrompt,
          user_files: userFiles || [],
          existing_content: supplement2Text.value || '',
          // 方案 B：传递 KB 和联网搜索参数
          useKB: useKB || false,
          selectedKBFiles: selectedKBFiles || [],
          useWebSearch: useWebSearch || false,
          webSearchKeyword: webSearchKeyword || '',
        }
      )
      if (res.data.code === 0 && res.data.data) {
        lastSupplementMeta.value = {
          inference_note: res.data.data.inference_note || '',
          supplement_type: res.data.data.supplement_type || 'infer',
          confidence: res.data.data.confidence || 0.7,
          matched_materials: res.data.data.matched_materials || { kb_files: [], ai_pulse_articles: [] },
        }
        step2SupplementDialogRef.value?.setGeneratedContent(res.data.data.content)
      } else {
        Message.error(res.data.msg || '补充失败')
        step2SupplementDialogRef.value?.setError()
      }
    } catch (e) {
      console.error('Step 2 supplement error:', e)
      Message.error('补充失败，请重试')
      step2SupplementDialogRef.value?.setError()
    } finally {
      supplementLoading.value = false
    }
  }

  function handleStep2SupplementConfirm({ content, userFiles }) {
    const supplementInfo = {}
    if (content) supplementInfo.text = content
    if (userFiles && userFiles.length > 0) supplementInfo.upload_files = userFiles
    if (lastSupplementMeta.value) {
      if (lastSupplementMeta.value.inference_note) supplementInfo.inference_note = lastSupplementMeta.value.inference_note
      supplementInfo.supplement_type = lastSupplementMeta.value.supplement_type
      supplementInfo.confidence = lastSupplementMeta.value.confidence
    }
    if (mcpFiles.value && mcpFiles.value.length > 0) {
      supplementInfo.files = mcpFiles.value.slice(0, 10)
    }
    supplement2Text.value = content || ''
    pendingSupplementData.value = supplementInfo
    supplementConfirmed.value = false
    Message.success('补充已保存，请确认后继续')
    
    // 方案 B：将匹配素材追加到素材池
    const meta = lastSupplementMeta.value
    if (meta?.matched_materials) {
      const ts = Date.now()
      // 追加推断文字
      if (content) {
        materialPool.value.push({ type: 'inference', content, ts })
      }
      // 追加知识库匹配文件
      for (const f of (meta.matched_materials.kb_files || [])) {
        materialPool.value.push({ type: 'kb_file', path: f.path, name: f.name, content: f.content, ts })
      }
      // 追加 AI-Pulse 文章
      for (const a of (meta.matched_materials.ai_pulse_articles || [])) {
        materialPool.value.push({ type: 'ai_pulse', title: a.title, source: a.source, summary: a.summary, url: a.url, ts })
      }
      console.log('📦 素材池已更新:', materialPool.value.length, '条')
    }
    
    // 补充后：将所有现有 issues 标记为 recurring（信任补充内容解决了问题）
    if (preCheckResult.value?.issues?.length) {
      preCheckResult.value = {
        ...preCheckResult.value,
        issues: preCheckResult.value.issues.map(i => ({ ...i, recurring: true, type: 'suggestion' })),
        all_recurring: true,
        score: Math.max(preCheckResult.value.score, 60),
      }
    }
  }

  function confirmSupplementAndProceed() {
    if (!supplement2Text.value) {
      Message.warning('请先补充内容')
      return
    }
    supplementConfirmed.value = true
    Message.success('补充已确认，正在启动分析工作台...')
    currentStep.value = 2
  }

  function openSupplementDialog(idx, source = 'check') {
    let issue
    if (source === 'step2') {
      issue = preCheckResult.value?.issues?.[idx]
    } else {
      issue = directionCheckResult.value?.[idx]
    }
    if (!issue) return
    supplementDialogItem.value = { title: issue.title, issueIdx: idx, source }
    supplementDialogVisible.value = true
  }

  async function handleSupplementSubmit({ userPrompt, userFiles }) {
    const issueIdx = supplementDialogItem.value.issueIdx
    const source = supplementDialogItem.value.source || 'check'
    let issue
    if (source === 'step2') {
      issue = preCheckResult.value?.issues?.[issueIdx]
    } else {
      issue = directionCheckResult.value?.[issueIdx]
    }
    if (!issue) return
    try {
      supplementDialogRef.value?.setProgressStep(1)
      let effectivePrompt = userPrompt || issue.title
      if (!effectivePrompt) effectivePrompt = `请补充${issue.title}相关内容`
      const res = await apiInferSupplement(
        sessionId.value,
        issue.title,
        {
          mcp_summary: mcpSummary.value || '',
          kb_file_list: mcpFiles.value || [],
          user_prompt: effectivePrompt,
          user_files: userFiles || [],
          existing_content: supplement2Text.value || '',
        }
      )
      if (res.data.code === 0 && res.data.data) {
        supplementDialogRef.value?.setGeneratedContent(res.data.data.content)
      } else {
        Message.error(res.data.msg || '补充失败')
        supplementDialogRef.value?.setError()
      }
    } catch (e) {
      console.error('Supplement submit error:', e)
      Message.error('补充失败，请重试')
      supplementDialogRef.value?.setError()
    }
  }

  function handleSupplementConfirm({ content, userFiles }) {
    const issueIdx = supplementDialogItem.value.issueIdx
    const source = supplementDialogItem.value.source || 'check'
    if (source === 'step2') {
      doFixIssueStub(issueIdx, content, userFiles)
    } else {
      const issue = directionCheckResult.value?.[issueIdx]
      if (issue) {
        const prefix = `【${issue.title}】\n`
        if (!supplement2Text.value.includes(prefix)) {
          supplement2Text.value += (supplement2Text.value ? '\n\n' : '') + prefix + content
        }
        fixedCheckIssues.value[issueIdx] = {
          content: content.substring(0, 100) + '...',
          time: new Date().toLocaleString(),
        }
      }
      runDirectionCheck()
    }
    Message.success('修复已应用')
  }

  // doFixIssue 存根 - 实现位于 WorkflowView.vue
  async function doFixIssueStub(idx, userPrompt, userFiles) {
    console.warn('[Dev-Stub] doFixIssue not implemented in useWorkflowState:', { idx, userPrompt, userFiles })
    return null
  }

  // 框架相关
  async function loadFrameworks() {
    frameworksLoading.value = true
    try {
      const res = await matchFrameworksV2(sessionId.value, selectedDirection.value?.name || '', mcpSummary.value)
      if (res.data.code === 0) {
        const payload = res.data.data || {}
        let fwList = []
        if (Array.isArray(payload)) {
          fwList = payload
          frameworksMode.value = 'premium'
          frameworksBanner.value = ''
        } else {
          fwList = payload.frameworks || []
          frameworksMode.value = payload.mode || 'premium'
          frameworksBanner.value = payload.banner || ''
        }
        frameworks.value = fwList
        if (frameworksMode.value === 'rejected') {
          Message.warning('未能找到对齐方向的框架，请查看提示')
        } else if (frameworksMode.value === 'fallback') {
          Message.warning(`已降级推荐 ${fwList.length} 个框架，建议人工评估`)
        } else {
          Message.success(`框架推荐完成，共 ${fwList.length} 个框架`)
        }
      } else {
        Message.warning(res.data.msg || '暂无推荐框架，请重试')
        frameworks.value = []
        frameworksBanner.value = res.data.msg || ''
        frameworksMode.value = 'rejected'
      }
    } catch (e) {
      Message.error('框架推荐失败: ' + e.message)
    } finally {
      frameworksLoading.value = false
    }
  }

  async function regenerateFrameworks() {
    if (!selectedDirection.value) {
      Message.warning('请先选择方向')
      return
    }
    frameworksLoading.value = true
    frameworks.value = []
    frameworksBanner.value = ''
    await loadFrameworks()
    frameworksLoading.value = false
  }

  async function selectFramework(f) {
    selectedFramework.value = f
    try {
      const supplementData = pendingSupplementData.value || {}
      await supplementStep2(sessionId.value, f, supplementData)
    } catch (e) {
      Message.error('保存框架失败: ' + e.message)
      return
    }
    Message.success(`已选择「${f.name}」框架，请在下方进行框架填充`)
  }

  async function handleFrameworkFill() {
    if (frameworkFillLoading.value) return
    if (!selectedFramework.value) {
      Message.warning('请先选择框架')
      return
    }
    frameworkFillLoading.value = true
    try {
      const frameworkKey = selectedFramework.value.key || selectedFramework.value.name
      const supplementData = pendingSupplementData.value?.text || supplement2Text.value || ''
      const res = await apiFillFramework(
        sessionId.value,
        frameworkKey,
        selectedFramework.value.name,
        selectedDirection.value?.name || '',
        supplementData,
        mcpSummary.value,
      )
      if (res.data.code === 0 && res.data.data) {
        analysisBody.value = res.data.data.analysis_body || ''
        slotCoverage.value = res.data.data.slot_coverage || {}
        Message.success(`框架填充完成（${res.data.data.word_count || 0} 字）`)
      } else {
        Message.error(res.data.msg || '框架填充失败')
      }
    } catch (e) {
      Message.error('框架填充失败: ' + e.message)
    } finally {
      frameworkFillLoading.value = false
    }
  }

  function goToCheck() {
    currentStep.value = 2.5  // V2: 进入框架工作台，而非旧版 Step 3 检测
  }

  function goBackToStep3() {
    currentStep.value = 2
    directionCheckResult.value = null
    directionCheckMeta.value = { force_passed: false, ready_for_next: true, check_count: 0, overall_score: 0 }
    Message.info('已返回框架选择页面，请重新选择')
  }

  // 补充确认
  async function confirmOutline() {
    showExportModal.value = true
  }

  async function skipSupplement2() {
    pendingSupplementData.value = {}
    supplementLoading.value = false
    supplementConfirmed.value = true
    lastSupplementMeta.value = null
    Message.info('已跳过补充，正在启动分析工作台...')
    currentStep.value = 2
  }

  async function submitSupplement2() {
    const supplementInfo = {}
    if (supplement2Text.value) supplementInfo.text = supplement2Text.value
    if (supplement2UploadFiles.value && supplement2UploadFiles.value.length > 0) {
      supplementInfo.upload_files = supplement2UploadFiles.value
    }
    if (supplement2KbFiles.value && supplement2KbFiles.value.length > 0) {
      supplementInfo.kb_files = supplement2KbFiles.value
    }
    if (supplement2File.value && supplement2File.value.length > 0) {
      supplementInfo.files = supplement2File.value
    }
    pendingSupplementData.value = supplementInfo
    supplementLoading.value = false
    lastSupplementMeta.value = null
    Message.success('补充已保存，正在启动分析工作台...')
    currentStep.value = 2
  }

  // 检测相关
  async function runDirectionCheck() {
    checkingDirection.value = true
    try {
      const supplementData = { ...supplement2Form }
      if (supplement2Text.value) {
        supplementData.text = supplement2Text.value
      }
      const res = await checkWorkflowDirection(
        sessionId.value,
        selectedDirection.value?.name || '',
        selectedFramework.value?.name || '',
        supplementData,
        mcpSummary.value,
        mcpFiles.value,
        { text: supplement2Text.value || '' },
        analysisBody.value,
      )
      directionCheckResult.value = res.data.data.issues || []
      directionCheckMeta.value = {
        force_passed: res.data.data.force_passed || false,
        ready_for_next: res.data.data.ready_for_next !== false,
        check_count: res.data.data.check_count || 0,
        overall_score: res.data.data.overall_score || 0,
      }
      Message.success('审核完成')
    } catch (e) {
      Message.error('检测失败: ' + e.message)
    } finally {
      checkingDirection.value = false
    }
  }

  async function goToOutlineFromDetection() {
    if (structures.value.length === 0) {
      await loadFrameworks()
    }
    if (structures.value.length > 0) {
      await selectStructure(structures.value[0])
    } else {
      currentStep.value = 5
      Message.warning('没有可用结构推荐，请返回重试')
    }
  }

  function skipSuggestionsAndContinue() {
    const suggestCount = suggestIssues.value.length
    if (suggestCount === 0) {
      currentStep.value = 4
      return
    }
    Message.warning(`⚠️ 有 ${suggestCount} 个优化建议未处理，可能影响文章质量`)
    $setTimeout(() => {
      currentStep.value = 4
    }, 1500)
  }

  // 结构相关
  async function goToStructures() {
    structuresLoading.value = true
    try {
      const supplementData = { ...supplement2Form }
      if (supplement2Text.value) {
        supplementData.text = supplement2Text.value
      }
      const res = await recommendStructures(
        sessionId.value,
        selectedDirection.value?.name || '',
        selectedFramework.value?.name || '',
        supplementData,
        mcpSummary.value,
        { text: supplement2Text.value || '' },
      )
      const data = res.data.data
      if (data && data.structures) {
        structures.value = data.structures
      } else if (Array.isArray(data)) {
        structures.value = data
      } else {
        structures.value = []
      }
      Message.success('结构推荐完成')
    } catch (e) {
      Message.error('结构推荐失败: ' + e.message)
    } finally {
      structuresLoading.value = false
      $setTimeout(() => {
        currentStep.value = 4
        Message.success('已切换到结构推荐页面')
      }, 100)
    }
  }

  async function selectStructure(s) {
    selectedStructure.value = s
    Message.info(`已选择「${s.name}」结构，正在保存...`)
    try {
      await supplementStep3(sessionId.value, s.name, {})
    } catch (e) {
      Message.error('保存结构失败: ' + e.message)
      return
    }
    currentStep.value = 5
    await loadOutline()
    Message.info(`已选择「${s.name}」结构，正在生成提纲...`)
  }

  function goBackToStructures() {
    currentStep.value = 4
    outlineResult.value = null
    Message.info('已返回结构推荐')
  }

  // 提纲相关
  async function loadOutline(switchToStep = 5) {
    loading.value = true
    try {
      const res = await generateWorkflowOutline(sessionId.value)
      if (res.data.code === 0) {
        let outlineData = res.data.data
        if (typeof outlineData === 'string') {
          try {
            outlineData = JSON.parse(outlineData)
          } catch (e) {
            console.error('提纲JSON解析失败:', e)
          }
        }
        if (outlineData.missing_items?.length > 0) {
          if (!outlineData.global_supplements) {
            outlineData.global_supplements = {}
          }
          for (const item of outlineData.missing_items) {
            outlineData.global_supplements[item.field] = ''
          }
        }
        outlineResult.value = outlineData
        await nextTick()
        loading.value = false
        if (switchToStep !== null) {
          await nextTick()
          currentStep.value = switchToStep
          Message.success('提纲生成完成')
        }
      } else {
        loading.value = false
        Message.error('提纲生成失败: ' + (res.data.msg || '未知错误'))
      }
    } catch (e) {
      loading.value = false
      Message.error('提纲生成失败: ' + e.message)
    }
  }

  async function regenerateOutline() {
    await loadOutline()
  }

  function toggleSectionAiDialog(key) {
    if (sectionAiDialogIndex.value === key) {
      sectionAiDialogIndex.value = -1
      sectionAiInput.value = ''
      sectionAiResult.value = ''
    } else {
      sectionAiDialogIndex.value = key
      sectionAiInput.value = ''
      sectionAiResult.value = ''
    }
  }

  async function aiSupplementSectionByKey(key) {
    const section = outlineResult.value?.sections?.[key]
    if (!section) return
    sectionAiLoading.value = true
    sectionAiResult.value = ''
    try {
      const context = [
        `段落标题：${section.title}`,
        section.key_points?.length ? `核心要点：${section.key_points.join('；')}` : '',
        section.materials?.needs?.length ? `需补充素材：${section.materials.needs.join('；')}` : '',
        sectionAiInput.value ? `用户需求：${sectionAiInput.value}` : '',
        sectionAiKbFiles.value?.length ? `参考知识库文件：${sectionAiKbFiles.value.join(', ')}` : '',
        sectionAiUploadFiles.value?.length ? `参考上传文件：${sectionAiUploadFiles.value.map(f => f.name || f).join(', ')}` : '',
      ].filter(Boolean).join('\n')
      const res = await apiInferSupplement(sessionId.value, section.title, {
        mcp_summary: mcpSummary.value || '',
        existing_content: context,
      })
      if (res.data.code === 0 && res.data.data?.content) {
        sectionAiResult.value = res.data.data.content
        Message.success('AI 补充内容已生成')
      } else {
        Message.error('AI 生成失败: ' + (res.data.msg || '未知错误'))
      }
    } catch (e) {
      Message.error('AI 生成失败: ' + e.message)
    } finally {
      sectionAiLoading.value = false
    }
  }

  function acceptSectionAiSuggestionByKey(key) {
    if (!sectionAiResult.value || !outlineResult.value?.sections?.[key]) return
    const section = outlineResult.value.sections[key]
    if (!section.materials) section.materials = { has: [], needs: [] }
    if (!section.materials.has) section.materials.has = []
    section.materials.has.push(sectionAiResult.value)
    sectionAiDialogIndex.value = -1
    sectionAiInput.value = ''
    sectionAiResult.value = ''
    sectionAiKbFiles.value = []
    sectionAiUploadFiles.value = []
    Message.success('素材已采纳')
  }

  function handleSectionAiUpload(fileList) {
    sectionAiUploadFiles.value = fileList || []
  }

  async function outlineOneClickAiSupplement() {
    if (!outlineResult.value?.sections) return
    const missingItems = outlineResult.value.missing_items || []
    const sectionsObj = outlineResult.value.sections
    const sectionsWithNeeds = Object.values(sectionsObj).filter(s => s.materials?.needs?.length > 0)
    if (missingItems.length === 0 && sectionsWithNeeds.length === 0) {
      Message.info('暂无需要补充的素材')
      return
    }
    outlineOneClickLoading.value = true
    try {
      if (!outlineResult.value.global_supplements) {
        outlineResult.value.global_supplements = {}
      }
      if (missingItems.length > 0) {
        for (const item of missingItems) {
          const context = [
            `缺失字段：${item.field}`,
            `补充建议：${item.fill_guidance}`,
          ].join('\n')
          const res = await apiInferSupplement(sessionId.value, `补充：${item.field}`, {
            mcp_summary: mcpSummary.value || '',
            existing_content: context,
          })
          if (res.data.code === 0 && res.data.data?.content) {
            outlineResult.value.global_supplements[item.field] = res.data.data.content
          }
        }
        Message.success(`已为 ${missingItems.length} 个全局缺失项完成 AI 补充`)
      }
      if (sectionsWithNeeds.length > 0) {
        for (const section of sectionsWithNeeds) {
          const context = [
            `段落标题：${section.title}`,
            section.key_points?.length ? `核心要点：${section.key_points.join('；')}` : '',
            `需补充素材：${section.materials.needs.join('；')}`,
          ].join('\n')
          const res = await apiInferSupplement(sessionId.value, section.title, {
            mcp_summary: mcpSummary.value || '',
            existing_content: context,
          })
          if (res.data.code === 0 && res.data.data?.content) {
            if (!section.materials.has) section.materials.has = []
            section.materials.has.push(res.data.data.content)
          }
        }
        Message.success(`已为 ${sectionsWithNeeds.length} 个段落完成 AI 补充`)
      }
    } catch (e) {
      Message.error('一键补充失败: ' + e.message)
    } finally {
      outlineOneClickLoading.value = false
    }
  }

  // 文章相关
  function goToGenerateArticle() {
    loading.value = true
    currentStep.value = 6
    generateArticle()
    Message.info('正在生成完整文章...')
  }

  async function generateArticle() {
    if (!outlineResult.value) {
      await loadOutline(null)
    }
    loading.value = true
    try {
      const outlineSections = outlineResult.value?.sections || []
      const step5Supplements = supplement2Text.value || ''
      const step6Materials = []
      if (outlineResult.value.sections && typeof outlineResult.value.sections === 'object') {
        for (const [key, section] of Object.entries(outlineResult.value.sections)) {
          if (section.materials?.has?.length > 0) {
            step6Materials.push({
              section_key: key,
              title: section.title,
              materials: section.materials.has,
            })
          }
        }
      }
      const res = await generateFullArticle(sessionId.value, outlineSections, {
        target_word_count: targetWordCount.value,
        step5_supplements: step5Supplements,
        step6_materials: step6Materials,
      })
      if (res.data.code === 0 && res.data.data) {
        let articleData = res.data.data
        if (typeof articleData === 'string') {
          try {
            articleData = JSON.parse(articleData)
          } catch {
            articleData = { title: '完整文章', paragraphs: [{ title: '正文', content: articleData, word_count: 0 }] }
          }
        }
        articleResult.value = articleData
        loading.value = false
        $setTimeout(() => {
          currentStep.value = 6
          Message.success('完整文章生成完成')
        }, 100)
      } else {
        Message.error('生成失败: ' + (res.data.msg || '未知错误'))
        loading.value = false
      }
    } catch (e) {
      Message.error('生成失败: ' + (e.message || '未知错误'))
      loading.value = false
    }
  }

  function toggleArticleAiDialog(idx) {
    if (articleAiDialogIndex.value === idx) {
      articleAiDialogIndex.value = -1
      articleAiInput.value = ''
      articleAiResult.value = ''
      articleAiKbFiles.value = []
      articleAiUploadFiles.value = []
    } else {
      articleAiDialogIndex.value = idx
      articleAiInput.value = ''
      articleAiResult.value = ''
      articleAiKbFiles.value = []
      articleAiUploadFiles.value = []
    }
  }

  function handleArticleAiUpload(fileList) {
    articleAiUploadFiles.value = fileList || []
  }

  async function aiAdjustArticleParagraph(idx) {
    const para = articleResult.value?.paragraphs?.[idx]
    if (!para) return
    articleAiLoading.value = true
    articleAiResult.value = ''
    try {
      const context = [
        `段落标题：${para.title}`,
        `当前内容：${para.content?.substring(0, 500)}...`,
        articleAiInput.value ? `用户调整需求：${articleAiInput.value}` : '',
        articleAiKbFiles.value?.length ? `参考知识库文件：${articleAiKbFiles.value.join(', ')}` : '',
        articleAiUploadFiles.value?.length ? `参考上传文件：${articleAiUploadFiles.value.map(f => f.name || f).join(', ')}` : '',
      ].filter(Boolean).join('\n')
      const res = await apiInferSupplement(sessionId.value, para.title, {
        mcp_summary: mcpSummary.value || '',
        existing_content: context,
      })
      if (res.data.code === 0 && res.data.data?.content) {
        articleAiResult.value = res.data.data.content
        Message.success('AI 调整内容已生成')
      } else {
        Message.error('AI 生成失败: ' + (res.data.msg || '未知错误'))
      }
    } catch (e) {
      Message.error('AI 生成失败: ' + e.message)
    } finally {
      articleAiLoading.value = false
    }
  }

  function acceptArticleAiSuggestion(idx) {
    if (!articleAiResult.value || !articleResult.value?.paragraphs?.[idx]) return
    articleResult.value.paragraphs[idx].content = articleAiResult.value
    articleAiDialogIndex.value = -1
    articleAiInput.value = ''
    articleAiResult.value = ''
    articleAiKbFiles.value = []
    articleAiUploadFiles.value = []
    Message.success('段落已替换')
  }

  async function articleOneClickRegenerate() {
    if (!articleResult.value?.paragraphs) return
    articleOneClickLoading.value = true
    try {
      const paragraphs = articleResult.value.paragraphs
      for (let i = 0; i < paragraphs.length; i++) {
        const para = paragraphs[i]
        const context = [
          `段落标题：${para.title}`,
          `核心要点：基于提纲生成`,
        ].join('\n')
        const res = await apiInferSupplement(sessionId.value, para.title, {
          mcp_summary: mcpSummary.value || '',
          existing_content: context,
        })
        if (res.data.code === 0 && res.data.data?.content) {
          paragraphs[i].content = res.data.data.content
        }
      }
      Message.success(`已重新生成 ${paragraphs.length} 个段落`)
    } catch (e) {
      Message.error('一键重新生成失败: ' + e.message)
    } finally {
      articleOneClickLoading.value = false
    }
  }

  function exportArticle() {
    if (!articleResult.value) {
      Message.warning('暂无文章可导出')
      return
    }
    let text = `# ${articleResult.value.title}\n\n`
    articleResult.value.paragraphs?.forEach((para, i) => {
      text += `## ${i + 1}. ${para.title}\n\n${para.content}\n\n`
    })
    const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${articleResult.value.title || '完整文章'}.md`
    a.click()
    URL.revokeObjectURL(url)
    Message.success('文章已导出')
  }

  // 配图相关
  function goToGenerateImage() {
    if (!articleResult.value) {
      Message.warning('请先生成完整文章')
      return
    }
    infographicHtml.value = ''
    infographicFeedback.value = ''
    currentStep.value = 7
  }

  async function handleGenerateInfographic() {
    if (!articleResult.value) {
      Message.error('没有可生成图片的文章内容')
      return
    }
    infographicGenerating.value = true
    try {
      const fullText = articleResult.value.paragraphs
        .map(p => `## ${p.title}\n\n${p.content}`)
        .join('\n\n')
      const frameworkName = selectedFramework.value?.name || '通用分析'
      const resp = await apiGenerateInfographic(frameworkName, fullText)
      if (resp.data.code === 0 && resp.data.data.html) {
        infographicHtml.value = resp.data.data.html
        Message.success('信息图生成成功！可在下方预览，不满意可输入反馈重新生成')
      } else {
        Message.error(resp.data.msg || '生成失败')
      }
    } catch (e) {
      Message.error('生成失败: ' + (e.message || '未知错误'))
    } finally {
      infographicGenerating.value = false
    }
  }

  async function handleReviseInfographic() {
    if (!infographicFeedback.value.trim()) return
    if (!infographicHtml.value) return
    infographicRevising.value = true
    try {
      const fullText = articleResult.value?.paragraphs
        ?.map(p => `## ${p.title}\n\n${p.content}`)
        .join('\n\n') || ''
      const frameworkName = selectedFramework.value?.name || ''
      const resp = await apiReviseInfographic(
        infographicHtml.value,
        infographicFeedback.value.trim(),
        frameworkName,
        fullText,
      )
      if (resp.data.code === 0 && resp.data.data.html) {
        infographicHtml.value = resp.data.data.html
        infographicFeedback.value = ''
        Message.success('已根据反馈重新生成！')
      } else {
        Message.error(resp.data.msg || '修改失败')
      }
    } catch (e) {
      Message.error('修改失败: ' + e.message)
    } finally {
      infographicRevising.value = false
    }
  }

  function openInfographicInNewTab() {
    if (!infographicHtml.value) return
    const blob = new Blob([infographicHtml.value], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank')
  }

  async function downloadInfographicAsImage() {
    if (!infographicHtml.value) return
    imageGenerating.value = true
    try {
      if (!window.html2canvas) {
        await new Promise((resolve, reject) => {
          const script = document.createElement('script')
          script.src = 'https://html2canvas.hertzen.com/dist/html2canvas.min.js'
          script.onload = resolve
          script.onerror = reject
          document.head.appendChild(script)
        })
      }
      const iframe = document.createElement('iframe')
      iframe.style.position = 'fixed'
      iframe.style.top = '-9999px'
      iframe.style.left = '-9999px'
      iframe.style.width = '1200px'
      iframe.style.height = '3000px'
      document.body.appendChild(iframe)
      const iframeDoc = iframe.contentDocument || iframe.contentWindow.document
      iframeDoc.write(infographicHtml.value)
      iframeDoc.close()
      await new Promise(r => setTimeout(r, 2000))
      const canvas = await window.html2canvas(iframeDoc.body, {
        scale: 2,
        useCORS: true,
        allowTaint: true,
        width: 1200,
        windowWidth: 1200,
      })
      document.body.removeChild(iframe)
      const a = document.createElement('a')
      a.href = canvas.toDataURL('image/png')
      a.download = `${articleResult.value?.title || 'article'}_配图.png`
      a.click()
      Message.success('下载成功！')
    } catch (e) {
      console.error('下载失败:', e)
      Message.warning('自动截图失败，已打开新窗口，请手动截图保存')
      openInfographicInNewTab()
    } finally {
      imageGenerating.value = false
    }
  }

  // 检测页问题修复
  function editSingleIssue(index) {
    editingIssueIndex.value = index
    editingIssueContent.value = ''
  }

  function cancelEditIssue() {
    editingIssueIndex.value = -1
    editingIssueContent.value = ''
  }

  async function confirmSingleIssue(index) {
    if (!editingIssueContent.value.trim()) {
      Message.warning('请输入补充内容')
      return
    }
    editingIssueLoading.value = index
    try {
      const issue = directionCheckResult.value[index]
      const prefix = `【${issue.title}】\n`
      if (!supplement2Text.value.includes(prefix)) {
        supplement2Text.value += (supplement2Text.value ? '\n\n' : '') + prefix + editingIssueContent.value
      } else {
        Message.warning('该内容已存在')
        editingIssueLoading.value = -1
        return
      }
      editingIssueLoading.value = -1
      cancelEditIssue()
      Message.success('补充已保存')
      await runDirectionCheck()
    } catch (e) {
      editingIssueLoading.value = -1
      Message.error('操作失败: ' + e.message)
    }
  }

  async function aiGenerateSingleIssue(index) {
    const issue = directionCheckResult.value[index]
    if (!issue) return
    aiSingleIssueLoading.value = index
    try {
      const res = await inferWithDirection(sessionId.value, issue.title, {
        existing_content: supplement2Text.value || '',
      })
      if (res.data.code === 0 && res.data.data?.content) {
        editingIssueContent.value = res.data.data.content
        editingIssueIndex.value = index
        Message.success('AI 补充内容已生成，可编辑后确认')
      } else {
        Message.error('AI 生成失败: ' + (res.data.msg || '未知错误'))
      }
    } catch (e) {
      Message.error('AI 生成失败: ' + e.message)
    } finally {
      aiSingleIssueLoading.value = -1
    }
  }

  function goBackToSupplement() {
    currentStep.value = 1
    directionCheckResult.value = null
    Message.info('已返回补充页面')
  }

  async function aiFixIssue(index, issue) {
    fixingIssueIndex.value = index
    loading.value = true
    try {
      const res = await fixWorkflowDirection(
        sessionId.value,
        issue,
        supplement2Form,
        mcpSummary.value,
        selectedDirection.value?.name || '',
        selectedFramework.value?.name || '',
        { text: supplement2Text.value || '' },
      )
      loading.value = false
      fixingIssueIndex.value = -1
      Message.success('AI 修改完成: ' + res.data.data.fix_description)
      await runDirectionCheck()
    } catch (e) {
      loading.value = false
      fixingIssueIndex.value = -1
      Message.error('AI 修改失败: ' + e.message)
    }
  }

  // ===== Modal handler functions (migrated from WorkflowView.vue) =====

  const toggleSupplementApiSelectAll = () => {
    const newState = !allSupplementApiCasesSelected.value
    supplementApiSelectedCases.value = Array(supplementApiCases.value.length).fill(newState)
  }

  async function goToStep2() {
    supplementStep.value = 2
    supplementInferLoading.value = true

    try {
      const selectedCases = supplementApiCases.value.filter((_, i) => supplementApiSelectedCases.value[i])

      const res = await apiAiAutoSupplement(
        sessionId.value,
        currentSupplementItem.value,
        mcpSummary.value,
        selectedCases.map(c => ({ title: c.title, summary: c.summary, source: c.source })),
      )

      if (res.data.code === 0) {
        supplementInferResult.value = {
          content: res.data.data.content || '',
          inference_note: res.data.data.inference_note || '基于 MCP 摘要和 API 案例推断',
        }
      } else {
        Message.error('AI 推断失败: ' + (res.data.msg || '未知错误'))
      }
    } catch (e) {
      Message.error('AI 推断失败: ' + e.message)
    } finally {
      supplementInferLoading.value = false
    }
  }

  async function goToStep2NoCases() {
    supplementStep.value = 2
    supplementInferLoading.value = true

    try {
      const res = await apiAiAutoSupplement(
        sessionId.value,
        currentSupplementItem.value,
        mcpSummary.value,
        [],
      )

      if (res.data.code === 0) {
        supplementInferResult.value = {
          content: res.data.data.content || '',
          inference_note: res.data.data.inference_note || '仅基于 MCP 摘要推断（无 API 案例）',
        }
      } else {
        Message.error('AI 推断失败: ' + (res.data.msg || '未知错误'))
      }
    } catch (e) {
      Message.error('AI 推断失败: ' + e.message)
    } finally {
      supplementInferLoading.value = false
    }
  }

  function goToStep3() {
    if (!supplementInferResult.value?.content) {
      Message.warning('推断结果为空，请重试')
      return
    }
    supplementStep.value = 3
  }

  async function confirmSupplementStep3() {
    if (!supplementInferResult.value?.content) {
      Message.warning('内容为空，无法保存')
      return
    }

    supplementSaving.value = true
    try {
      const res = await apiAddSupplement(
        sessionId.value,
        'supplement',
        currentSupplementItem.value,
        supplementInferResult.value.content,
        'ai-auto',
        { inference_note: supplementInferResult.value.inference_note },
        [],
      )

      if (res.data.code === 0) {
        const suppId = res.data.data.supplement_id
        await apiConfirmSupplement(sessionId.value, suppId)

        supplementContents.value[currentSupplementIndex.value] = {
          content: supplementInferResult.value.content,
          method: 'ai-auto',
          time: new Date().toLocaleString(),
        }

        Message.success('补充内容已保存！')
        supplementModalVisible.value = false

        await reEvaluateCompleteness()
      } else {
        Message.error('保存失败: ' + (res.data.msg || '未知错误'))
      }
    } catch (e) {
      Message.error('保存失败: ' + e.message)
    } finally {
      supplementSaving.value = false
    }
  }

  function closeSupplementModal() {
    supplementModalVisible.value = false
    supplementStep.value = 1
    supplementApiCases.value = []
    supplementApiSelectedCases.value = []
    supplementInferResult.value = null
  }

  function openEditSupplementModal(index) {
    const items = completenessResult.value.missing_critical || []
    if (index >= items.length) return

    currentSupplementItem.value = items[index]
    currentSupplementIndex.value = index

    editOriginalContent.value = getSupplementContent(index)
    editNewContent.value = editOriginalContent.value
    editAiSuggestion.value = ''

    editModalVisible.value = true
    Message.info('编辑模式：左侧为原有内容，右侧为编辑区')
  }

  async function aiAssistEdit() {
    editAiLoading.value = true
    try {
      const res = await apiInferSupplement(sessionId.value, currentSupplementItem.value, {
        existing_content: editOriginalContent.value,
        mcp_summary: mcpSummary.value,
      })

      if (res.data.code === 0 && res.data.data?.content) {
        editAiSuggestion.value = res.data.data.content
        Message.success('AI 优化建议已生成')
      } else {
        Message.error('AI 辅助失败: ' + (res.data.msg || '未知错误'))
      }
    } catch (e) {
      console.error('AI 辅助异常:', e)
      Message.error('AI 辅助失败: ' + e.message)
    } finally {
      editAiLoading.value = false
    }
  }

  function applyAiSuggestion() {
    editNewContent.value = editAiSuggestion.value
    Message.success('已应用 AI 建议')
  }

  async function saveEditedSupplement() {
    if (!editNewContent.value.trim()) {
      Message.warning('编辑内容不能为空')
      return
    }

    editSaving.value = true
    try {
      const idx = currentSupplementIndex.value
      const addRes = await apiAddSupplement(
        sessionId.value,
        'text',
        currentSupplementItem.value,
        editNewContent.value,
        'manual-edit',
        { original_content: editOriginalContent.value },
        [],
      )
      const suppId = addRes.data.data.supplement_id
      await apiConfirmSupplement(sessionId.value, suppId)

      supplementContents.value[idx] = {
        content: editNewContent.value.substring(0, 100) + '...',
        method: 'manual-edit',
        time: new Date().toLocaleString(),
      }

      editModalVisible.value = false
      Message.success('编辑已保存')

      await reEvaluateCompleteness()
    } catch (e) {
      console.error('保存失败:', e)
      Message.error('保存失败: ' + e.message)
    } finally {
      editSaving.value = false
    }
  }

  function closeEditModal() {
    editModalVisible.value = false
    editOriginalContent.value = ''
    editNewContent.value = ''
    editAiSuggestion.value = ''
  }

  async function reEvaluateCompleteness() {
    if (!sessionId.value) return

    try {
      const res = await evaluateCompleteness(sessionId.value, mcpSummary.value)
      if (res.data.code === 0) {
        const oldCompleteness = completenessResult.value?.completeness || 0
        const newData = res.data.data
        let newCompleteness = newData.completeness || 0
        if (newCompleteness > 0 && newCompleteness <= 1) {
          newCompleteness = Math.round(newCompleteness * 100)
        }

        completenessResult.value = { ...newData, completeness: newCompleteness }

        Message.success(`完整度已从 ${oldCompleteness}% 更新至 ${newCompleteness}%`)

        const missingCritical = completenessResult.value.missing_critical || []
        const allSupplemented = missingCritical.every((_, idx) => isSupplemented(idx))

        if (allSupplemented && missingCritical.length > 0) {
          Message.success('所有关键缺失项已补充完毕！')
        } else if (newCompleteness >= 80) {
          Message.info('信息已充足，可以直接生成提纲！')
        }
      }
    } catch (e) {
      console.warn('重新评估完整度失败:', e)
    }
  }

  async function confirmBatchAiPulse() {
    let savedCount = 0
    for (let i = 0; i < batchAiPulseResults.value.length; i++) {
      const result = batchAiPulseResults.value[i]
      if (result.cases.length === 0) continue

      for (const c of result.cases) {
        const caseText = `【${c.title}】\n来源：${c.source}\n评分：${c.score}\n摘要：${c.summary}\n链接：${c.url}`
        try {
          const addRes = await apiAddSupplement(
            sessionId.value,
            'case',
            result.item,
            caseText,
            'ai-pulse',
            { title: c.title, source: c.source, score: c.score, url: c.url },
            c.tags || [],
          )
          const suppId = addRes.data.data.supplement_id
          await apiConfirmSupplement(sessionId.value, suppId)
          savedCount++
        } catch (e) {
          console.warn(`保存案例 "${c.title}" 失败:`, e)
        }
      }

      const missingItems = completenessResult.value.missing_critical || []
      const idx = missingItems.indexOf(result.item)
      if (idx >= 0) {
        supplementContents.value[idx] = {
          content: `${result.cases.length} 个 AI-Pulse 案例`,
          method: 'ai-pulse',
          time: new Date().toLocaleString(),
        }
      }
    }

    batchAiPulseModalVisible.value = false
    Message.success(`已保存 ${savedCount} 个案例到知识库`)

    await reEvaluateCompleteness()
  }

  async function confirmBatchManual() {
    const missingItems = completenessResult.value.missing_critical || []
    let savedCount = 0

    for (const [indexStr, text] of Object.entries(batchManualTexts.value)) {
      if (!text.trim()) continue
      const idx = parseInt(indexStr)
      const item = missingItems[idx]

      try {
        const res = await apiAddSupplement(
          sessionId.value,
          'supplement',
          item,
          text,
          'manual',
          {},
          [],
        )
        const suppId = res.data.data.supplement_id
        await apiConfirmSupplement(sessionId.value, suppId)

        supplementContents.value[idx] = {
          content: text.substring(0, 100) + (text.length > 100 ? '...' : ''),
          method: 'manual',
          time: new Date().toLocaleString(),
        }
        savedCount++
      } catch (e) {
        console.warn(`保存 "${item}" 失败:`, e)
      }
    }

    batchManualModalVisible.value = false
    Message.success(`已保存 ${savedCount} 项补充内容`)

    await reEvaluateCompleteness()
  }

  function toggleUnifiedSelectAll() {
    const allSelected = unifiedApiSelected.value.every(Boolean)
    unifiedApiSelected.value = unifiedApiCases.value.map(() => !allSelected)
  }

  async function goToUnifiedInfer() {
    const selectedCases = unifiedApiCases.value.filter((_, i) => unifiedApiSelected.value[i])

    unifiedModalStep.value = 2
    unifiedInferLoading.value = true
    unifiedInferResult.value = null

    try {
      const res = await apiInferSupplement(sessionId.value, unifiedModalItem.value, {
        cases: selectedCases,
        mcp_summary: mcpSummary.value,
      })
      if (res.data.code === 0) {
        unifiedInferResult.value = res.data.data
      } else {
        Message.error('推断失败: ' + (res.data.msg || '未知错误'))
      }
    } catch (e) {
      console.error('推断异常:', e)
      Message.error('推断失败: ' + e.message)
    } finally {
      unifiedInferLoading.value = false
    }
  }

  async function goToUnifiedInferNoCases() {
    unifiedModalStep.value = 2
    unifiedInferLoading.value = true
    unifiedInferResult.value = null

    try {
      const res = await apiInferSupplement(sessionId.value, unifiedModalItem.value, {
        cases: [],
        mcp_summary: mcpSummary.value,
      })
      if (res.data.code === 0) {
        unifiedInferResult.value = res.data.data
      } else {
        Message.error('推断失败: ' + (res.data.msg || '未知错误'))
      }
    } catch (e) {
      console.error('推断异常:', e)
      Message.error('推断失败: ' + e.message)
    } finally {
      unifiedInferLoading.value = false
    }
  }

  async function confirmUnifiedSupplement() {
    if (!unifiedInferResult.value?.content) {
      Message.warning('没有可保存的内容')
      return
    }

    unifiedSaving.value = true
    try {
      const addRes = await apiAddSupplement(
        sessionId.value,
        'text',
        unifiedModalItem.value,
        unifiedInferResult.value.content,
        'ai-infer',
        { inference_note: unifiedInferResult.value.inference_note },
        [],
      )
      const suppId = addRes.data.data.supplement_id
      await apiConfirmSupplement(sessionId.value, suppId)

      const idx = unifiedModalItemIndex.value
      if (idx >= 0) {
        supplementContents.value[idx] = {
          content: unifiedInferResult.value.content.substring(0, 100) + '...',
          method: 'ai-infer',
          time: new Date().toLocaleString(),
        }
      }

      unifiedModalVisible.value = false
      Message.success('已保存补充内容')

      await reEvaluateCompleteness()
    } catch (e) {
      console.error('保存失败:', e)
      Message.error('保存失败: ' + e.message)
    } finally {
      unifiedSaving.value = false
    }
  }

  function closeUnifiedModal() {
    unifiedModalVisible.value = false
    unifiedModalStep.value = 1
    unifiedApiCases.value = []
    unifiedApiSelected.value = []
    unifiedInferResult.value = null
  }

  async function openDraftModal(index) {
    const missingItems = completenessResult.value.missing_critical || []
    if (!missingItems[index]) {
      Message.warning('缺失项不存在')
      return
    }

    draftModalItemIndex.value = index
    draftModalItem.value = missingItems[index]
    draftContent.value = ''
    draftModalVisible.value = true
    draftLoading.value = true

    try {
      const res = await apiSupplementDraft(
        sessionId.value,
        selectedDirection.value?.name || '',
        selectedFramework.value?.name || '',
        missingItems[index],
        '',
      )
      if (res.data.code === 0) {
        let text = res.data.data.text || ''
        const warningPrefix = '️ 以下为AI基于通用模式的推导参考，请核实后使用。'
        if (text.startsWith(warningPrefix)) {
          text = text.substring(warningPrefix.length).trim()
        }
        draftContent.value = text
      } else {
        draftContent.value = `草稿生成失败：${res.data.msg || '未知错误'}\n\n你可以手动在下方输入框中补充内容，或点击取消。`
      }
    } catch (e) {
      console.error('草稿生成异常:', e)
      draftContent.value = `草稿生成异常：${e.message}\n\n你可以手动在下方输入框中补充内容，或点击取消。`
    } finally {
      draftLoading.value = false
    }
  }

  async function confirmDraftSupplement() {
    if (!draftContent.value) {
      Message.warning('没有可保存的内容')
      return
    }

    draftSaving.value = true
    try {
      const addRes = await apiAddSupplement(
        sessionId.value,
        'text',
        draftModalItem.value,
        draftContent.value,
        'ai-draft',
        {},
        [],
      )
      const suppId = addRes.data.data.supplement_id

      const confirmRes = await apiConfirmSupplement(sessionId.value, suppId, true)
      if (confirmRes.data.code === 0) {
        Message.success('已保存，标记为「用户确认草稿」')
        closeDraftModal()
        reEvaluateCompleteness()
      } else {
        Message.error('保存失败: ' + (confirmRes.data.msg || '未知错误'))
      }
    } catch (e) {
      console.error('保存草稿异常:', e)
      Message.error('保存失败: ' + e.message)
    } finally {
      draftSaving.value = false
    }
  }

  function closeDraftModal() {
    draftModalVisible.value = false
    draftContent.value = ''
    draftModalItem.value = ''
    draftModalItemIndex.value = -1
  }

  function closeBatchResultModal() {
    batchResultModalVisible.value = false
    reEvaluateCompleteness()
  }

  return {
    // ==== refs ====
    loading, currentStep, collapsedSteps, sessionId, mcpSummary, mcpFiles,
    kbTreeData, mcpTopic, topics, topicsLoading, scannedFolders, fileCount,
    completenessResult, supplementContents, directions, selectedDirection,
    directionsLoading, supplementModalVisible, currentSupplementItem,
    currentSupplementIndex, isEditMode, editModalVisible, editOriginalContent,
    editNewContent, editAiSuggestion, editAiLoading, editSaving,
    frameworkAiSuggestion, frameworkAiLoading, frameworkSelectedIndex,
    issueAiHelp, structureAiSuggestion, structureAiLoading, supplementStep,
    supplementApiLoading, supplementApiCases, supplementApiSelectedCases,
    supplementInferLoading, supplementInferResult, supplementSaving,
    batchAiPulseLoading, batchManualLoading, batchUnifiedLoading,
    batchAiPulseModalVisible, batchManualModalVisible, batchAiPulseResults,
    batchManualTexts, unifiedModalVisible, unifiedModalStep, unifiedModalItem,
    unifiedModalItemIndex, unifiedApiCases, unifiedApiSelected, unifiedApiLoading,
    unifiedInferLoading, unifiedInferResult, unifiedSaving,
    draftModalVisible, draftModalItem, draftModalItemIndex, draftContent,
    draftLoading, draftSaving, supplementModalMethod, supplementModalFile,
    supplementModalText, aiSupplementing, extractingFileContent,
    extractedFileContent, extractedFileCount, smartSupplementResult,
    smartSupplementLoading, currentKnowledgeLevel, canDegrade, degradationCount,
    supplementDialogVisible, supplementDialogItem, step2SupplementDialogVisible,
    step2SupplementDialogRef, supplementDialogRef, supplementConfirmed,
    isFirstScan, scanStatus, supplement1Method, supplement1File, supplement1Result,
    supplement1Text, supplement2Method, supplement2File, supplement2Text,
    supplement2Html, supplement2UploadFiles, supplement2KbFiles,
    directionsLoading, batchResultModalVisible, batchResults, checkingDirection,
    preCheckLoading, preCheckResult, preloadedApiCases, preloadingApiCases,
    frameworks, frameworksLoading, frameworksBanner, frameworksMode,
    selectedFramework, frameworkFillLoading, analysisBody, slotCoverage,
    directionCheckResult, directionCheckMeta, fixedCheckIssues, structures,
    structuresLoading, selectedStructure, outlineResult, sectionAiDialogIndex,
    sectionAiInput, sectionAiKbFiles, sectionAiLoading, sectionAiResult,
    sectionAiUploadFiles, articleResult, articleAiDialogIndex, articleAiInput,
    articleAiKbFiles, articleAiLoading, articleAiResult, articleAiUploadFiles,
    imageGenerating, generatedImageUrl, infographicHtml, infographicGenerating,
    infographicRevising, infographicFeedback, editingIssueIndex,
    editingIssueContent, editingIssueLoading, aiSingleIssueLoading,
    fixingIssueIndex, aiAutoSupplementLoading, aiPulseLoading, aiPulseCases,
    aiPulseKeywords, aiPulseSelectedCases, aiSupplementAllLoading,
    supplementAllLoading, outlineOneClickLoading, articleOneClickLoading,
    showOutlineAlignmentReason, supplementLoading, expandedIssues,
    expandedWarnings, aiPulseCases, supplementDialogRef, step2SupplementDialogRef,
    exportDomainTag, exportingToDomain, showExportModal,
    pendingSupplementData, lastSupplementMeta, preCheckResult, targetWordCount,
    materialPool,
    // ==== computed ====
    completenessPercent, manualCompleteness, displayCompleteness,
    allCriticalSupplemented, allSupplementApiCasesSelected,
    anySupplementApiCaseSelected, stepDetails, stepSummaries,
    blockIssues, suggestIssues, hasErrors, outlineCompletenessStatus,
    readingTime, totalWordCount, selectedSupplementCasesSummary,
    slotGapMatches, computeSlotGapMatches,
    // ==== functions ====
    // ==== topics ====
    topics, topicsLoading, scannedFolders, fileCount,
    loadTopics, refreshTopics, toggleStepCollapse, selectDirectionAndAdvance,
    selectDirection, runPreCheck, handleFirstScan, openStep2SupplementDialog,
    handleStep2SupplementSubmit, handleStep2SupplementConfirm,
    confirmSupplementAndProceed, openSupplementDialog,
    handleSupplementSubmit, handleSupplementConfirm, isSupplemented,
    getSupplementContent, loadFrameworks, regenerateFrameworks, selectFramework,
    handleFrameworkFill, goToCheck, goBackToStep3, confirmOutline,
    skipSupplement2, submitSupplement2, runDirectionCheck,
    goToOutlineFromDetection, skipSuggestionsAndContinue, goToStructures,
    selectStructure, goBackToStructures, loadOutline, regenerateOutline,
    toggleSectionAiDialog, aiSupplementSectionByKey,
    acceptSectionAiSuggestionByKey, handleSectionAiUpload,
    outlineOneClickAiSupplement, goToGenerateArticle, generateArticle,
    toggleArticleAiDialog, handleArticleAiUpload, aiAdjustArticleParagraph,
    acceptArticleAiSuggestion, articleOneClickRegenerate, exportArticle,
    goToGenerateImage, handleGenerateInfographic, handleReviseInfographic,
    openInfographicInNewTab, downloadInfographicAsImage, editSingleIssue,
    cancelEditIssue, confirmSingleIssue, aiGenerateSingleIssue,
    goBackToSupplement, aiFixIssue, isCheckIssueFixed, getCheckIssueFixContent,
    convertToTreeData, deriveFrameworkKey, saveWorkflowState,
    getCompletenessColor, getScoreColor, getScoreTagColor, getScoreLabel,
    getReverseScoreColor, getCoverageColor, getIssueColor, getIssueTagColor,
    getSourceTagColor, getSourceTagTagColor, getSourceTagLabel,
    getSectionNumber, getSectionMissingItems, getCompletenessStatusColor,
    getCompletenessStatusLabel, getAlignmentColor, getAlignmentTagColor,
    getAlignmentBgColor, getAlignmentBorderColor, getAlignmentTextColor,
    // ==== modal handler functions ====
    toggleSupplementApiSelectAll, goToStep2, goToStep2NoCases, goToStep3,
    confirmSupplementStep3, closeSupplementModal, openEditSupplementModal,
    aiAssistEdit, applyAiSuggestion, saveEditedSupplement, closeEditModal,
    reEvaluateCompleteness, confirmBatchAiPulse, confirmBatchManual,
    toggleUnifiedSelectAll, goToUnifiedInfer, goToUnifiedInferNoCases,
    confirmUnifiedSupplement, closeUnifiedModal, openDraftModal,
    confirmDraftSupplement, closeDraftModal, closeBatchResultModal,
    $setTimeout,
  }
}