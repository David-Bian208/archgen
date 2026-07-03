import { ref, reactive, computed, watch, nextTick } from 'vue'
import { Message } from '@arco-design/web-vue'
import { marked } from 'marked'
import { useSession } from './useSession'
import { setLoadFrameworksRef, selectedDirection, mcpSummary, mcpFiles } from './useStep0_Topics'
import {
  matchFrameworksV2,
  supplementStep2,
  checkWorkflowDirection,
  fillFramework as apiFillFramework,
  aiInferSupplement as apiInferSupplement,
  recommendStructures,
  supplementStep3,
  generateWorkflowOutline,
  evaluateCompleteness,
} from '../utils/api'

// ==================== 模块级单例状态 ====================

const { sessionId, currentStep, loading } = useSession()

// 完整度评估
const completenessResult = ref(null)

const completenessPercent = computed(() => {
  if (!completenessResult.value) return 0
  const raw = completenessResult.value.completeness || 0
  if (raw <= 1 && raw > 0) {
    return Math.round(raw * 100)
  }
  return Math.min(Math.max(Math.round(raw), 0), 100)
})

// ==================== 补充内容状态 ====================
const supplementContents = ref({})

function isSupplemented(index) {
  return supplementContents.value[index] !== undefined
}

function getSupplementContent(index) {
  return supplementContents.value[index]?.content || ''
}

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

const allCriticalSupplemented = computed(() => {
  if (!completenessResult.value) return false
  const missingCritical = completenessResult.value.missing_critical || []
  if (missingCritical.length === 0) return false
  return missingCritical.every((_, idx) => isSupplemented(idx))
})

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
const supplementLoading = ref(false)
const supplementConfirmed = ref(false)
const isFirstScan = ref(true)
const scanStatus = ref('')
const lastSupplementMeta = ref(null)

// ==================== 补充对话框状态 ====================
const supplementDialogVisible = ref(false)
const supplementDialogItem = ref({ title: '', issueIdx: -1 })
const step2SupplementDialogVisible = ref(false)
const step2SupplementDialogRef = ref(null)
const supplementDialogRef = ref(null)

// ==================== 检测相关 refs ====================
const checkingDirection = ref(false)
const directionCheckResult = ref(null)
const directionCheckMeta = ref({ force_passed: false, ready_for_next: true, check_count: 0, overall_score: 0 })
const fixedCheckIssues = ref({})

const hasErrors = computed(() => {
  if (!directionCheckResult.value) return false
  if (directionCheckMeta.value.force_passed) return false
  if (directionCheckMeta.value.ready_for_next === false) return true
  return directionCheckResult.value.some(issue => issue.level === 'block' || issue.type === 'error')
})

const blockIssues = computed(() => {
  if (!directionCheckResult.value) return []
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

const outlineCompletenessStatus = computed(() => {
  if (!outlineResult.value?.sections) return 'red'
  const sections = outlineResult.value.sections
  const anchoredCount = Object.values(sections).filter(s => s.source_tag === 'anchored').length
  const missingCount = outlineResult.value.missing_items?.length || 0
  if (anchoredCount >= 4 && missingCount <= 1) return 'green'
  if (anchoredCount >= 2 && missingCount <= 3) return 'yellow'
  return 'red'
})

// ==================== 工具函数 ====================

const _timeoutIds = []

function $setTimeout(fn, delay, ...args) {
  const id = window.setTimeout(fn, delay, ...args)
  _timeoutIds.push(id)
  return id
}

// ==================== 副作用 ====================

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

// ==================== 核心方法 ====================

// 预检测
async function runPreCheck() {
  if (preCheckLoading.value) return
  preCheckLoading.value = true
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
      preCheckResult.value = {
        score: res.data.data.overall_score || 0,
        issues: (res.data.data.issues || []).filter(issue => issue.type !== 'pass'),
        ready_for_next: res.data.data.ready_for_next || false,
      }
      Message.success('预检测完成')
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
            mcp_summary: mcpSummary.value,
            kb_file_list: mcpFiles.value,
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

async function handleStep2SupplementSubmit({ userPrompt, userFiles }) {
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
        mcp_summary: mcpSummary.value,
        kb_file_list: mcpFiles.value,
        user_prompt: effectivePrompt,
        user_files: userFiles || [],
        existing_content: supplement2Text.value || '',
      }
    )
    if (res.data.code === 0 && res.data.data) {
      lastSupplementMeta.value = {
        inference_note: res.data.data.inference_note || '',
        supplement_type: res.data.data.supplement_type || 'infer',
        confidence: res.data.data.confidence || 0.7,
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
  $setTimeout(() => {
    runPreCheck()
  }, 500)
}

function confirmSupplementAndProceed() {
  if (!supplement2Text.value) {
    Message.warning('请先补充内容')
    return
  }
  supplementConfirmed.value = true
  Message.success('补充已确认，正在加载框架推荐...')
  currentStep.value = 2
  loadFrameworks()
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
        mcp_summary: mcpSummary.value,
        kb_file_list: mcpFiles.value,
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
  console.warn('[Dev-Stub] doFixIssue not implemented in useStep2_Framework:', { idx, userPrompt, userFiles })
  return null
}

function isCheckIssueFixed(idx) {
  return fixedCheckIssues.value[idx] !== undefined
}

function getCheckIssueFixContent(idx) {
  return fixedCheckIssues.value[idx]?.content || ''
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
  currentStep.value = 2.5
}

function goBackToStep3() {
  currentStep.value = 2
  directionCheckResult.value = null
  directionCheckMeta.value = { force_passed: false, ready_for_next: true, check_count: 0, overall_score: 0 }
  Message.info('已返回框架选择页面，请重新选择')
}

async function skipSupplement2() {
  pendingSupplementData.value = {}
  supplementLoading.value = false
  supplementConfirmed.value = true
  lastSupplementMeta.value = null
  Message.info('已跳过补充，正在加载框架推荐...')
  currentStep.value = 2
  await loadFrameworks()
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
  Message.success('补充已保存，正在加载框架推荐...')
  currentStep.value = 2
  await loadFrameworks()
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

// 重新评估完整度
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

// ==================== 初始化延迟引用 ====================

// 让 useStep0_Topics 能调用 loadFrameworks
setLoadFrameworksRef(loadFrameworks)

// ==================== 导出 ====================

export function useStep2_Framework() {
  return {
    // ==== refs ====
    completenessResult,
    supplementContents,
    frameworks,
    frameworksMode,
    selectedFramework,
    frameworksBanner,
    frameworksLoading,
    expandedWarnings,
    supplement2Form,
    supplement2Text,
    supplement2Method,
    supplement2File,
    supplement2UploadFiles,
    supplement2KbFiles,
    supplement2Html,
    pendingSupplementData,
    supplementConfirmed,
    lastSupplementMeta,
    isFirstScan,
    scanStatus,
    supplementLoading,
    frameworkFillLoading,
    analysisBody,
    slotCoverage,
    preCheckResult,
    preCheckLoading,
    expandedIssues,
    directionCheckResult,
    directionCheckMeta,
    checkingDirection,
    fixedCheckIssues,
    aiPulseLoading,
    aiPulseCases,
    aiPulseSelectedCases,
    aiPulseKeywords,
    preloadingApiCases,
    preloadedApiCases,
    structures,
    structuresLoading,
    selectedStructure,
    outlineResult,
    supplementDialogVisible,
    supplementDialogItem,
    step2SupplementDialogVisible,
    step2SupplementDialogRef,
    supplementDialogRef,
    // ==== computed ====
    completenessPercent,
    manualCompleteness,
    displayCompleteness,
    allCriticalSupplemented,
    blockIssues,
    suggestIssues,
    hasErrors,
    outlineCompletenessStatus,
    // ==== functions ====
    $setTimeout,
    isSupplemented,
    getSupplementContent,
    isCheckIssueFixed,
    getCheckIssueFixContent,
    runPreCheck,
    handleFirstScan,
    openStep2SupplementDialog,
    handleStep2SupplementSubmit,
    handleStep2SupplementConfirm,
    confirmSupplementAndProceed,
    openSupplementDialog,
    handleSupplementSubmit,
    handleSupplementConfirm,
    skipSupplement2,
    submitSupplement2,
    loadFrameworks,
    regenerateFrameworks,
    selectFramework,
    handleFrameworkFill,
    goToCheck,
    goBackToStep3,
    runDirectionCheck,
    goToOutlineFromDetection,
    skipSuggestionsAndContinue,
    goToStructures,
    selectStructure,
    goBackToStructures,
    loadOutline,
    regenerateOutline,
    reEvaluateCompleteness,
  }
}
