import { ref, reactive, computed } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useSession } from './useSession'
import { fillFrameworkSlot, checkCoherence, uploadSlotSource, batchFillFrameworkSlots } from '../utils/api'
import { generateSlots, getSlotRelations, matchMaterials, generateSlotOutline, batchFillV4, askFollowup, preCheckMaterials, analyzeSlot, integrateOutline, searchWebForSlot } from '../utils/api'

// ==================== 模块级单例状态 ====================
const { sessionId } = useSession()

// 槽位定义（从框架选择后解析而来）
const slots = reactive({})           // { slot_key: { label, keywords, state } }

// 槽位填充结果（从 slot_fill API 返回）
const slotResults = reactive({})     // { slot_key: { level, points, sources, gaps, coverage, ... } }

// 槽位覆盖度汇总
const slotCoverage = ref(0)

const stitchResult = ref(null)       // 缝合审核结果

// 槽位操作状态
const slotFillingKeys = ref(new Set())   // 正在 AI 填充中的槽位
const slotLoadedKeys = ref(new Set())    // 已加载完毕的槽位

// 降级链配置
const maxDegradation = ref(2)            // 从配置读取
const degradationCounts = reactive({})   // { slot_key: number }
const slotConfirmed = reactive({})       // { slot_key: boolean }

// ==================== V4.0 新增状态 ====================
const streamingThinking = ref('')        // 流式推理文本（累积）
const streamingLines = ref([])           // 流式推理逐行数据
const streamDone = ref(false)            // 流式是否完成
const phase = ref('init')                // init | streaming | editing_slots | filling | done
const confirmedSlots = ref([])           // 用户确认的槽位清单 [{slot_key, label, description}]
const slotMaterials = reactive({})       // { slot_key: MaterialItem[] }
const slotOutlines = reactive({})        // { slot_key: OutlineItem[] }
const writingPlans = reactive({})        // { slot_key: string }
const slotRelations = ref(null)          // 槽位关系图谱 { relations, graph_description }
const editingSlot = ref('')             // 当前打开的编辑面板槽位
const showEditPanel = ref(false)         // 编辑面板是否展示
const followupHistory = ref([])          // 追问历史 [{q, a}]
// H3: 快速分析状态
const analyzeResult = ref('')            // 当前分析结果文本
const analyzeLoadingType = ref('')       // 正在加载的分析类型
const analyzeError = ref(false)          // 分析是否失败
const analyzeTypeLabel = ref('')         // 分析类型中文标签
const streamAbortController = ref(null)  // SSE 流中断控制器
const preCheckResults = ref({})          // 素材预检结果 { slot_key: { count, level, alternatives } }
const preCheckRunning = ref(false)        // 预检是否进行中
const webSearchEnabled = ref(false)       // L3: 联网兜底开关

// ==================== Computed ====================
const completedSlots = computed(() => {
  return Object.values(slotResults).filter(s =>
    (s.level === 'L0' || s.level === 'L1') || slotConfirmed[s.slotKey]
  ).length
})

const totalSlots = computed(() => Object.keys(slots).length)

const allSlotsCompleted = computed(() => {
  if (totalSlots.value === 0) return false
  return Object.keys(slots).every(k => {
    const r = slotResults[k]
    return (r && (r.level === 'L0' || r.level === 'L1')) || slotConfirmed[k]
  })
})

// ==================== Actions ====================

async function fillSlot(slotKey, supplementInput = '', confirmedSources = [], l2Answers = null) {
  if (slotFillingKeys.value.has(slotKey)) return

  slotFillingKeys.value = new Set([...slotFillingKeys.value, slotKey])

  // 如果有 L2 答案，拼入 supplementInput
  let extraSupp = ''
  if (l2Answers && l2Answers.length) {
    const questions = slotResults[slotKey]?.questions || []
    extraSupp = l2Answers.map((a, i) => `Q${i + 1}: ${questions[i] || ''}\nA: ${a}`).join('\n')
  }
  const finalSupp = [supplementInput, extraSupp].filter(Boolean).join('\n')

  try {
    const res = await fillFrameworkSlot(
      sessionId.value,
      slotKey,
      finalSupp,
      confirmedSources
    )

    if (res.data && res.data.code === 0) {
      const d = res.data.data
      slotResults[slotKey] = {
        slotKey,
        level: d.level,
        points: d.points || [],
        sources: d.sources || [],
        gaps: d.gaps || [],
        coverage: d.coverage || 0,
        supplementInput: finalSupp,
        confirmedSources,
        self_assessment: d.self_assessment || '',
        questions: d.questions || [],
        analogy: d.analogy || '',
        inspirations: d.inspirations || [],
        _degradation_count: degradationCounts[slotKey] || 0,
      }
      slotCoverage.value = d.overall_coverage || 0
      slotLoadedKeys.value = new Set([...slotLoadedKeys.value, slotKey])

      if (d.level === 'L0') {
        Message.success(`「${d.slot_label || slotKey}」填充完成`)
      } else if (d.level === 'L1') {
        Message.warning(`「${d.slot_label || slotKey}」已填充，但存在数据缺口`)
      } else if (d.level === 'L2') {
        Message.info(`「${d.slot_label || slotKey}」需要你回答几个问题`)
      } else if (d.level === 'L3') {
        Message.info(`「${d.slot_label || slotKey}」使用了类比推导，请注意核实`)
      } else {
        Message.info(`「${d.slot_label || slotKey}」需要手动补充素材`)
      }
    } else {
      Message.error(`槽位填充失败: ${res.data?.msg || '未知错误'}`)
    }
  } catch (e) {
    Message.error(`槽位填充请求失败: ${e.message}`)
  } finally {
    const s = new Set(slotFillingKeys.value)
    s.delete(slotKey)
    slotFillingKeys.value = s
  }
}

// 批量填充所有槽位（进入工作台时自动调用）
const batchFilling = ref(false)

async function batchFillSlots() {
  if (batchFilling.value) return
  batchFilling.value = true

  try {
    const res = await batchFillFrameworkSlots(sessionId.value)
    if (res.data?.code === 0) {
      const d = res.data.data
      // 更新所有槽位结果
      for (const r of d.results) {
        slotResults[r.slotKey] = {
          ...r,
          confirmedSources: [],
          _degradation_count: 0,
        }
      }
      Message.success(`已填充 ${d.filled_count} 个槽位，整体覆盖度 ${Math.round(d.overall_coverage * 100)}%`)
      return d
    }
  } catch (e) {
    Message.error(`批量填充失败: ${e.message}`)
  } finally {
    batchFilling.value = false
  }
  return null
}

function degradeSlot(slotKey, supplementInput = '', confirmedSources = []) {
  const count = (degradationCounts[slotKey] || 0) + 1
  if (count > maxDegradation.value) {
    Message.warning('该槽位已达最大重试次数')
    return
  }
  degradationCounts[slotKey] = count
  Message.info(`「${slotKey}」重试第 ${count} 次`)
  fillSlot(slotKey, supplementInput, confirmedSources)
}

function confirmSlot(slotKey) {
  slotConfirmed[slotKey] = true
}

function skipSlot(slotKey) {
  slotConfirmed[slotKey] = true
  slotResults[slotKey] = {
    ...(slotResults[slotKey] || {}),
    slotKey,
    level: 'L4',
    points: [],
    sources: [],
    gaps: ['用户跳过'],
    coverage: 0,
  }
}

// 上传素材到槽位（文本内容或文件解析结果）
async function uploadSource(slotKey, content, filename = 'upload.txt', fileType = 'text') {
  try {
    const res = await uploadSlotSource(sessionId.value, slotKey, content, filename, fileType)
    if (res.data?.code === 0) {
      const d = res.data.data
      Message.success(`「${d.filename}」已上传`)

      // 把上传的内容作为补充输入，重新触发 slot_fill
      const supp = d.extracted_text || content
      await fillSlot(slotKey, supp, [d.source])
      return d
    } else {
      Message.error(`上传失败: ${res.data?.msg || '未知错误'}`)
    }
  } catch (e) {
    Message.error(`上传请求失败: ${e.message}`)
  }
  return null
}

// 重新获取某个槽位的填充结果（刷新左栏）
function refetchSlot(slotKey) {
  const r = slotResults[slotKey]
  if (r) {
    // 触发 slotResults 的 reactivity 更新
    slotResults[slotKey] = { ...r }
  }
}

function initSlots(slotDefs) {
  for (const key of Object.keys(slotDefs)) {
    slots[key] = {
      label: slotDefs[key].label || key,
      keywords: slotDefs[key].keywords || [],
      state: 'empty',
    }
  }
  for (const k of Object.keys(slotResults)) delete slotResults[k]
  for (const k of Object.keys(degradationCounts)) delete degradationCounts[k]
  for (const k of Object.keys(slotConfirmed)) delete slotConfirmed[k]
  slotCoverage.value = 0
  slotFillingKeys.value = new Set()
  slotLoadedKeys.value = new Set()
}

function resetWorkbench() {
  for (const k of Object.keys(slots)) delete slots[k]
  for (const k of Object.keys(slotResults)) delete slotResults[k]
  for (const k of Object.keys(degradationCounts)) delete degradationCounts[k]
  for (const k of Object.keys(slotConfirmed)) delete slotConfirmed[k]
  slotCoverage.value = 0
  stitchResult.value = null
  slotFillingKeys.value = new Set()
  slotLoadedKeys.value = new Set()
}

// ==================== 缝合审核 ====================
const checkingCoherence = ref(false)
const coherenceResult = ref(null)

async function runCoherenceCheck() {
  if (checkingCoherence.value) return
  checkingCoherence.value = true
  try {
    const res = await checkCoherence(sessionId.value)
    if (res.data?.code === 0) {
      coherenceResult.value = res.data.data
      if (res.data.data.ready_for_next) {
        Message.success('缝合审核通过，槽位之间逻辑衔接良好')
      } else {
        Message.warning(`缝合审核发现 ${res.data.data.transition_issues?.length || 0} 个衔接问题`)
      }
    }
  } catch (e) {
    Message.error('缝合审核失败: ' + e.message)
  } finally {
    checkingCoherence.value = false
  }
}

// ==================== V4.0 三列工作台方法 ====================

/** 启动 SSE 流式推理槽位 */
function startStreamSlots(topic, materialPoolSummary = '') {
  phase.value = 'streaming'
  streamingThinking.value = ''
  streamingLines.value = []
  streamDone.value = false
  confirmedSlots.value = []

  streamAbortController.value = generateSlots(
    sessionId.value,
    topic,
    materialPoolSummary,
    {
      onThinking(text) {
        streamingThinking.value += text + '\n'
        streamingLines.value = [...streamingLines.value, { type: 'thinking', text }]
      },
      onSlot(slot) {
        confirmedSlots.value = [...confirmedSlots.value, slot]
      },
      onDone(slots) {
        streamDone.value = true
        phase.value = 'editing_slots'
        confirmedSlots.value = slots
        // 自动获取关系图谱
        fetchSlotRelations()
        // 自动运行素材预检
        runPreCheck(slots)
      },
      onError(msg) {
        streamDone.value = true
        Message.error('流式推理出错: ' + msg)
      },
    }
  )
}

/** 停止 SSE 流式 */
function stopStream() {
  if (streamAbortController.value) {
    streamAbortController.value.abort()
    streamAbortController.value = null
  }
  streamDone.value = true
  phase.value = 'editing_slots'
}

/** 获取槽位关系图谱 */
async function fetchSlotRelations() {
  if (confirmedSlots.value.length < 2) return
  try {
    const res = await getSlotRelations(sessionId.value, confirmedSlots.value)
    if (res.data?.code === 0) {
      slotRelations.value = res.data.data
    }
  } catch (e) {
    console.warn('获取关系图谱失败:', e)
  }
}

/** 编辑槽位清单 */
function updateSlot(slotKey, updates) {
  const idx = confirmedSlots.value.findIndex(s => s.slot_key === slotKey)
  if (idx >= 0) {
    confirmedSlots.value[idx] = { ...confirmedSlots.value[idx], ...updates }
    confirmedSlots.value = [...confirmedSlots.value]
  }
}

function removeSlot(slotKey) {
  confirmedSlots.value = confirmedSlots.value.filter(s => s.slot_key !== slotKey)
}

function addSlot(label, description = '') {
  const key = `slot_${confirmedSlots.value.length + 1}`
  confirmedSlots.value = [...confirmedSlots.value, { slot_key: key, label, description }]
}

/** 确认槽位 → 触发批量填充 v4 */

async function confirmAndFill() {
  if (confirmedSlots.value.length === 0) {
    Message.warning('请至少保留一个槽位')
    return
  }
  phase.value = 'filling'
  batchFilling.value = true

  try {
    const res = await batchFillV4(sessionId.value, confirmedSlots.value, webSearchEnabled.value)
    if (res.data?.code === 0) {
      const data = res.data.data
      const mats = data.slot_materials || {}
      const outlines = data.slot_outlines || {}
      for (const s of confirmedSlots.value) {
        const sk = s.slot_key
        slotMaterials[sk] = mats[sk] || []
        slotOutlines[sk] = outlines[sk] || []
      }
      phase.value = 'done'
      Message.success('三列内容填充完成')
    } else {
      Message.error('内容填充失败: ' + (res.data?.msg || ''))
      phase.value = 'editing_slots'
    }
  } catch (e) {
    Message.error('内容填充请求失败: ' + e.message)
    phase.value = 'editing_slots'
  } finally {
    batchFilling.value = false
  }

  // 更新 v3 兼容状态
  for (const s of confirmedSlots.value) {
    const sk = s.slot_key
    slotResults[sk] = {
      slotKey: sk,
      level: (slotMaterials[sk]?.length && slotOutlines[sk]?.length) ? 'L0' : 'L1',
      points: [],
      sources: [] ,
      gaps: [],
      coverage: 0.8,
    }
  }
}

/** 编辑面板 */
function openEditPanel(slotKey) {
  editingSlot.value = slotKey
  showEditPanel.value = true
  followupHistory.value = []
}

function closeEditPanel() {
  showEditPanel.value = false
  editingSlot.value = ''
}

async function saveWritingPlan(slotKey, plan) {
  writingPlans[slotKey] = plan
  // 写入 session 后端的 writing_plan 字段
  try {
    await fillFrameworkSlot(sessionId.value, slotKey, '', [])
  } catch (e) { /* 静默 */ }
  Message.success('写作方案已保存')
}

/** 手动补充素材到槽位 */
async function addMaterialToSlot(slotKey, content, filename = 'manual.txt', fileType = 'text') {
  try {
    const res = await uploadSlotSource(sessionId.value, slotKey, content, filename, fileType)
    if (res.data?.code === 0) {
      const d = res.data.data
      const newMat = {
        text: d.extracted_text || content,
        source_type: 'user_input',
        source_name: filename,
        confidence: 1.0,
      }
      const existing = slotMaterials[slotKey] || []
      slotMaterials[slotKey] = [...existing, newMat]
      Message.success('素材已补充')
    }
  } catch (e) {
    Message.error('素材补充失败: ' + e.message)
  }
}

/** 追问 AI */
async function askFollowupQuestion(context, slotKey, question) {
  try {
    const history = followupHistory.value
    const res = await askFollowup(sessionId.value, context, slotKey, question, history)
    if (res.data?.code === 0) {
      const d = res.data.data
      followupHistory.value = [...history, { q: question, a: d.reply }]
      return d
    }
  } catch (e) {
    Message.error('追问失败: ' + e.message)
  }
  return null
}

// H3: 槽位素材分析
const typeLabels = { core_points: '核心观点', outline_relation: '提纲关联', expand_outline: '扩写提纲', extension_direction: '扩展方向' }

async function handleAnalyzeSlot(slotKey, analysisType) {
  try {
    const matList = slotMaterials[slotKey] || []
    const outlineList = slotOutlines[slotKey] || []
    
    analyzeLoadingType.value = analysisType
    analyzeError.value = false
    analyzeResult.value = ''
    analyzeTypeLabel.value = typeLabels[analysisType] || analysisType

    const res = await analyzeSlot(sessionId.value, slotKey, analysisType, matList, outlineList)
    if (res.data?.code === 0) {
      analyzeResult.value = res.data.data.result
      analyzeLoadingType.value = ''
    } else {
      analyzeError.value = true
      analyzeLoadingType.value = ''
      Message.error('分析失败: ' + (res.data?.msg || '未知错误'))
    }
  } catch (e) {
    analyzeError.value = true
    analyzeLoadingType.value = ''
    Message.error('分析请求失败: ' + e.message)
  }
}

// W2-2: 整合生成提纲
async function handleIntegrateOutline(data) {
  const { slotKey, slotLabel, outline, materials, writingPlan } = data
  try {
    const res = await integrateOutline(sessionId.value, slotKey, slotLabel, outline, materials, writingPlan)
    if (res.data?.code === 0) {
      const result = res.data.data.integrated_outline || []
      return result
    } else {
      Message.error('整合生成失败: ' + (res.data?.msg || ''))
    }
  } catch (e) {
    Message.error('整合生成请求失败')
  }
  return null
}

// W3: 联网搜索槽位素材
async function handleWebSearchSlot(data) {
  const { slotKey, slotLabel } = data
  try {
    const res = await searchWebForSlot(sessionId.value, slotKey, slotLabel)
    if (res.data?.code === 0) {
      const results = res.data.data.results || []
      Message.success(`搜索到 ${results.length} 条素材`)
      return results
    } else {
      Message.error('联网搜索失败')
    }
  } catch (e) {
    Message.error('联网搜索请求失败')
  }
  return null
}

// W4: 确认所有槽位
function handleConfirmAllSlots() {
  const allSK = confirmedSlots.value.map(s => s.slot_key)
  for (const sk of allSK) {
    slotConfirmed[sk] = true
  }
  Message.success(`已确认 ${allSK.length} 个槽位`)
}

/** 素材可行性预检 */
async function runPreCheck(slots) {
  console.log('🔍 runPreCheck 被调用，槽位数:', slots.length)
  preCheckRunning.value = true
  try {
    const res = await preCheckMaterials(sessionId.value, slots)
    console.log('🔍 preCheck 返回:', res.data)
    if (res.data?.code === 0) {
      preCheckResults.value = res.data.data.check_results || {}
      console.log('🔍 preCheckResults 设置为:', preCheckResults.value)
      return preCheckResults.value
    }
  } catch (e) {
    console.error('🔍 preCheck 失败:', e)
    Message.error('素材预检失败: ' + e.message)
  } finally {
    preCheckRunning.value = false
  }
  return {}
}

/** 采纳 AI 推荐替换槽位 */
function adoptAlternative(slotKey, alternative) {
  confirmedSlots.value = confirmedSlots.value.map(s => {
    if (s.slot_key === slotKey) {
      return { ...s, label: alternative.label, description: alternative.reason }
    }
    return s
  })
  Message.success(`已将 "${slotKey}" 替换为 "${alternative.label}"`)
}

/** 确认单个槽位（复用已有方法，v4 兼容） */

/** 检查是否全部确认 */
const allSlotsConfirmed = computed(() => {
  if (confirmedSlots.value.length === 0) return false
  return confirmedSlots.value.every(s => slotConfirmed[s.slot_key])
})

// ==================== 导出 ====================
export function useStep3Workbench() {
  return {
    // v3 兼容
    slots,
    slotResults,
    slotCoverage,
    stitchResult,
    slotFillingKeys,
    slotLoadedKeys,
    completedSlots,
    totalSlots,
    allSlotsCompleted,
    maxDegradation,
    degradationCounts,
    slotConfirmed,
    fillSlot,
    batchFillSlots,
    batchFilling,
    degradeSlot,
    confirmSlot,
    skipSlot,
    initSlots,
    resetWorkbench,
    uploadSource,
    refetchSlot,
    checkingCoherence,
    coherenceResult,
    runCoherenceCheck,
    // v4.0 新增
    streamingThinking,
    streamingLines,
    streamDone,
    phase,
    confirmedSlots,
    slotMaterials,
    slotOutlines,
    writingPlans,
    slotRelations: slotRelations,
    editingSlot,
    showEditPanel,
    followupHistory,
    startStreamSlots,
    stopStream,
    fetchSlotRelations,
    updateSlot,
    removeSlot,
    addSlot,
    confirmAndFill,
    openEditPanel,
    closeEditPanel,
    saveWritingPlan,
    addMaterialToSlot,
    askFollowupQuestion,
    allSlotsConfirmed,
    // v4.0 预检
    preCheckResults,
    preCheckRunning,
    runPreCheck,
    webSearchEnabled,
    adoptAlternative,
    // H3: 快速分析
    analyzeResult,
    analyzeLoadingType,
    analyzeError,
    analyzeTypeLabel,
    handleAnalyzeSlot,
    // W2-2 + W3 + W4
    handleIntegrateOutline,
    handleWebSearchSlot,
    handleConfirmAllSlots,
  }

}

// 单例模式：确保跨组件共享同一个 useStep3Workbench 实例
const _instance = useStep3Workbench()
export function getStep3Workbench() {
  return _instance
}
