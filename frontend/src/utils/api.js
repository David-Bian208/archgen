import axios from 'axios'
import { Message } from '@arco-design/web-vue'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,  // 120秒超时（LLM 调用最长可达 60-120 秒）
})

// 请求拦截器：添加时间戳防缓存
api.interceptors.request.use(
  config => config,
  error => Promise.reject(error)
)

// 响应拦截器：自动检测业务错误
api.interceptors.response.use(
  response => {
    const body = response.data
    // 如果后端返回标准格式 { code, msg, data }，自动检测错误
    if (body && typeof body.code === 'number' && body.code !== 0) {
      console.error('[API] 业务错误:', body.code, body.msg)
      Message.error(body.msg || '请求失败')
      return Promise.reject(new Error(body.msg || '请求失败'))
    }
    return response  // 保持原始 Axios 响应，不自动解包
  },
  error => {
    if (error.code === 'ECONNABORTED') {
      console.warn('[API] 请求超时:', error.message)
      Message.warning('请求超时，AI 处理时间较长，请稍后重试')
    } else if (error.response) {
      const status = error.response.status
      if (status === 500) {
        console.error('[API] 服务器错误:', error.response.data)
      } else if (status === 404) {
        console.warn('[API] 接口不存在:', error.config?.url)
      }
    } else if (error.request) {
      console.error('[API] 网络错误，请检查后端服务')
    }
    return Promise.reject(error)
  }
)

export function getCategories() {
  return api.get('/categories')
}

export function classifyByText(text) {
  return api.post('/classify/intent', { text })
}

// Alias for backward compatibility
export const classifyIntent = classifyByText

export function getKbCategories() {
  return api.get('/kb/categories')
}

export function getKbFiles(category) {
  return api.get('/kb/files', { params: { category } })
}

export function readKbFile(filePath) {
  return api.post('/kb/read', { file_path: filePath })
}

// ===== 本地文件夹接口 =====

export function verifyFolder(path) {
  return api.post('/folders/verify', { path })
}

export function listFolderFiles(path) {
  return api.post('/folders/list', { path })
}

export function readFolderFile(folderPath, filePath) {
  return api.post('/folders/read', { folder_path: folderPath, file_path: filePath })
}

export function matchFrameworks(text, category, topN = 5, mcpSummary = '') {
  return api.post('/frameworks/match', { text, category, top_n: topN, mcp_summary: mcpSummary })
}

export function getFramework(frameworkKey) {
  return api.get(`/frameworks/detail/${frameworkKey}`)
}

export function getAllFrameworks(text, mcpSummary) {
  return api.post('/frameworks', { text: text || '', mcp_summary: mcpSummary || '' })
}

export function preflightCheck(text, frameworkKey) {
  return api.post('/data/preflight', { text, framework_key: frameworkKey })
}

export function autopopulateData(text, frameworkKey) {
  return api.post('/data/autopopulate', { text, framework_key: frameworkKey })
}

export function aiGenerateField(frameworkKey, fieldKey, fieldLabel, existingData, sourceText) {
  return api.post('/data/ai_generate', {
    framework_key: frameworkKey,
    field_key: fieldKey,
    field_label: fieldLabel,
    existing_data: existingData,
    source_text: sourceText,
  })
}

export function checkDataCompleteness(data, frameworkKey) {
  return api.post('/data/check', { data, framework_key: frameworkKey })
}

// Alias for backward compatibility
export const getDataCheck = checkDataCompleteness

// V4: 从槽位结构 AI 推荐配图框架
export function suggestFramework(slots) {
  return api.post('/framework/suggest-from-slots', { slots })
}

export function generateDiagram(formData) {
  const fd = new FormData()
  fd.append('framework_key', formData.frameworkKey)
  fd.append('text', formData.text)
  fd.append('style', formData.style)
  fd.append('size', formData.size)
  return api.post('/generate', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
  })
}

export function generatePreview(frameworkKey, data, sourceText, style = 'minimal', size = 'default') {
  return api.post('/generate/preview', { framework_key: frameworkKey, data, source_text: sourceText, style, size })
}

// 新版配图：LLM 直接生成 HTML 信息图
export function generateInfographic(frameworkName, articleContent, personaContext = '') {
  return api.post('/generate/infographic', {
    framework_name: frameworkName,
    article_content: articleContent,
    persona_context: personaContext,
  })
}

// 新版配图迭代：基于反馈重新生成
export function reviseInfographic(currentHtml, feedback, frameworkName = '', articleContent = '') {
  return api.post('/generate/infographic/revise', {
    current_html: currentHtml,
    feedback,
    framework_name: frameworkName,
    article_content: articleContent,
  })
}

export async function downloadBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  window.URL.revokeObjectURL(url)
  document.body.removeChild(a)
}

export function getStyles() {
  return api.get('/styles')
}

export function getSizes() {
  return api.get('/sizes')
}

export function getHealth() {
  return api.get('/health')
}

// MCP 检索
export function mcpSearch(topic, folders) {
  return api.post('/mcp/search', { topic, folders })
}

// MCP 题材推荐
export function mcpSuggest(params) {
  return api.post('/mcp/suggest', params)
}

// MCP 按主题匹配文件并返回内容（纯关键词匹配 + 文件读取，不调 LLM）
export function mcpMatchFiles(params) {
  return api.post('/mcp/match-files', params)
}

// MCP 分类列表（用于筛选）
export function getMcpCategories() {
  return api.get('/categories')
}

// 方向建议分析
export function analyzeDirections(summary) {
  return api.post('/directions/analyze', { summary })
}

// 题材选中后生成原文
export function generateFromTopic(topicName, folders, params) {
  return api.post('/mcp/search', { topic: topicName, folders, ...params })
}

// 内容结构生成
export function generateContentStructure(directionName, summary, topicNeeded = '') {
  return api.post('/content/structure', { 
    direction_name: directionName, 
    summary,
    topic_needed: topicNeeded,
  })
}

// AI 生成单个段落
export function aiGenerateSection(directionName, sectionTitle, sectionHint, sourceText, existingSections, outline = '', analysisType = '', analysisSuggestion = '', topicNeeded = '', sessionId = '') {
  return api.post('/content/ai_generate', {
    direction_name: directionName,
    section_title: sectionTitle,
    section_hint: sectionHint,
    source_text: sourceText,
    existing_sections: existingSections,
    section_outline: outline,
    analysis_type: analysisType,
    analysis_suggestion: analysisSuggestion,
    topic_needed: topicNeeded,
    session_id: sessionId,
  })
}

// 生成 3 个提纲版本
export function generateOutlineVersions(directionName, sectionKey, sectionTitle, sectionHint, summary, topicNeeded = '') {
  return api.post('/content/outline_versions', {
    direction_name: directionName,
    section_key: sectionKey,
    section_title: sectionTitle,
    section_hint: sectionHint,
    summary,
    topic_needed: topicNeeded,
  })
}

// 方向性检测
export function checkDirection(sectionTitle, sectionOutline, generatedContent) {
  return api.post('/content/check_direction', {
    section_title: sectionTitle,
    section_outline: sectionOutline,
    generated_content: generatedContent,
  })
}

// AI 重写段落（支持用户补充指令）
export function aiRewriteSection(directionName, sectionTitle, sectionOutline, userFeedback, sourceText, existingSections, sessionId = '') {
  return api.post('/content/ai_rewrite', {
    direction_name: directionName,
    section_title: sectionTitle,
    section_outline: sectionOutline,
    user_feedback: userFeedback,
    source_text: sourceText,
    existing_sections: existingSections,
    session_id: sessionId,
  })
}

// AI 一键生成全文
export function aiGenerateFullContent(directionName, structure, sourceText, sessionId = '') {
  return api.post('/content/ai_generate_full', {
    direction_name: directionName,
    structure,
    source_text: sourceText,
    session_id: sessionId,
  })
}

// 智能补全全文
export function smartFillContent(directionName, structure, sourceText, analysis) {
  return api.post('/content/smart_fill', {
    direction_name: directionName,
    structure,
    source_text: sourceText,
    analysis,
  })
}

// ===== 身份定位管理 =====

export function getPersonaInfo() {
  return api.get('/persona/info')
}

export function setPersonaPath(filePath) {
  return api.post('/persona/set_path', { file_path: filePath })
}

export function savePersona(content) {
  return api.post('/persona/save', { content })
}

export function parsePersona(filePath = '') {
  return api.post('/persona/parse', { file_path: filePath })
}

// ===== 多段式工作流 =====

export function createWorkflowSession() {
  return api.post('/workflow/session/create')
}

export function getWorkflowSessionStatus(sessionId) {
  return api.post('/workflow/session/status', { session_id: sessionId })
}

export function evaluateCompleteness(sessionId, mcpSummary) {
  return api.post('/workflow/completeness/evaluate', {
    session_id: sessionId,
    mcp_summary: mcpSummary,
  })
}

export function analyzeDirectionsV2(sessionId, mcpSummary, mcpFiles = []) {
  return api.post('/workflow/directions/analyze', {
    session_id: sessionId,
    mcp_summary: mcpSummary,
    mcp_files: mcpFiles,
  })
}

export function evaluateCustomDirection(sessionId, direction) {
  return api.post('/workflow/directions/evaluate', {
    session_id: sessionId,
    direction,
  })
}

export function supplementStep1(sessionId, direction, supplementInfo) {
  return api.post('/workflow/supplement/1', {
    session_id: sessionId,
    direction,
    supplement_info: supplementInfo,
  })
}

export function matchFrameworksV2(sessionId, direction, supplement1, mcpSummary) {
  return api.post('/workflow/frameworks/match', {
    session_id: sessionId,
    direction,
    supplement_1: supplement1,
    mcp_summary: mcpSummary,
  })
}

export function supplementStep2(sessionId, framework, supplementInfo) {
  return api.post('/workflow/supplement/2', {
    session_id: sessionId,
    framework,
    supplement_info: supplementInfo,
  })
}

// 推荐写作角度
export function recommendAngles({ sessionId, topic, mcpSummary, materialSummary }) {
  return api.post('/workflow/angle/recommend', {
    session_id: sessionId,
    topic,
    mcp_summary: mcpSummary || '',
    material_summary: materialSummary || '',
  })
}

// 框架填充（C 步骤）
export function fillFramework(sessionId, frameworkKey, frameworkName, direction, supplement2, mcpSummary) {
  return api.post('/workflow/framework/fill', {
    session_id: sessionId,
    framework_key: frameworkKey,
    framework_name: frameworkName,
    direction,
    supplement_2: supplement2,
    mcp_summary: mcpSummary,
  })
}

// 槽位内容预览
export function slotContentPreview(sessionId, slotKey, slotLabel, slotDescription, topic, direction) {
  return api.post('/workflow/slot/content_preview', {
    session_id: sessionId,
    slot_key: slotKey,
    slot_label: slotLabel,
    slot_description: slotDescription || '',
    topic: topic || '',
    direction: direction || '',
  })
}

export function fillFrameworkSlot(sessionId, slotKey, supplementInput = '', confirmedSources = []) {
  return api.post('/workflow/slot/fill', {
    session_id: sessionId,
    slot_key: slotKey,
    supplement_input: supplementInput,
    confirmed_sources: confirmedSources,
  })
}

export function uploadSlotSource(sessionId, slotKey, content, filename = 'upload.txt', fileType = 'text') {
  return api.post('/workflow/slot/upload_source', {
    session_id: sessionId,
    slot_key: slotKey,
    content: content,
    filename: filename,
    file_type: fileType,
  })
}

export function batchFillFrameworkSlots(sessionId) {
  return api.post('/workflow/slot/batch_fill', {
    session_id: sessionId,
  })
}

export function getFrameworkSlots(frameworkKey, sessionId = '') {
  const params = sessionId ? { session_id: sessionId } : {}
  return api.get(`/frameworks/${frameworkKey}/slots`, { params })
}

export function searchSlotFragments(sessionId, keywords, direction) {
  return api.post('/workflow/slot/search', {
    session_id: sessionId,
    keywords: keywords,
    direction: direction,
  })
}

export function checkCoherence(sessionId) {
  return api.post('/workflow/direction/check', {
    session_id: sessionId,
    check_mode: 'coherence',
  })
}

export function checkWorkflowDirection(sessionId, direction, framework, supplement, mcpSummary, kbFileList = [], supplement1, analysisBody = '') {
  return api.post('/workflow/direction/check', {
    session_id: sessionId,
    direction,
    framework,
    supplement_1: supplement1 || { text: mcpSummary || '' },
    supplement_2: supplement,
    mcp_summary: mcpSummary,
    kb_file_list: kbFileList,
    analysis_body: analysisBody,
  })
}

export function fixWorkflowDirection(sessionId, issue, supplement, mcpSummary, direction, framework, supplement1) {
  return api.post('/workflow/direction/fix', {
    session_id: sessionId,
    issue,
    supplement_1: supplement1 || { text: mcpSummary || '' },
    supplement_2: supplement,
    mcp_summary: mcpSummary,
    direction,
    framework,
  })
}

export function recommendStructures(sessionId, direction, framework, supplement, mcpSummary, supplement1) {
  return api.post('/workflow/structures/recommend', {
    session_id: sessionId,
    direction,
    framework,
    supplement_1: supplement1 || { text: mcpSummary || '' },
    supplement_2: supplement,
    mcp_summary: mcpSummary,
  })
}

export function supplementStep3(sessionId, structure, supplementInfo) {
  return api.post('/workflow/supplement/3', {
    session_id: sessionId,
    structure,
    supplement_info: supplementInfo,
  })
}

export function generateWorkflowOutline(sessionId) {
  return api.post('/workflow/outline/generate', {
    session_id: sessionId,
  })
}

export function generateFullArticle(sessionId, outlineSections, options = {}) {
  const { target_word_count = 2000, step5_supplements = '', step6_materials = [] } = options
  return api.post('/workflow/article/generate', {
    session_id: sessionId,
    outline_sections: outlineSections,
    target_word_count: target_word_count,
    step5_supplements: step5_supplements,
    step6_materials: step6_materials,
  }, {
    timeout: 300000,  // 文章生成需要较长时间，设置5分钟超时
  }).catch(err => {
    console.error('文章生成API调用失败:', err)
    throw err
  })
}

export function aiAutoSupplement(sessionId, missingItem, mcpSummary, selectedCases = [], kbContext = '') {
  return api.post('/workflow/supplement/ai-auto', {
    session_id: sessionId,
    missing_item: missingItem,
    mcp_summary: mcpSummary,
    selected_cases: selectedCases,
    kb_context: kbContext,
  })
}

export function aiPulseSupplement(sessionId, missingItem, keywords) {
  return api.post('/workflow/supplement/ai-pulse', {
    session_id: sessionId,
    missing_item: missingItem,
    keywords: keywords || [],
  })
}

export function aiInferSupplement(sessionId, missingItem, params = {}) {
  const {
    cases = [],
    mcp_summary = '',
    existing_content = '',
    kb_file_list = [],
    user_prompt = '',
    user_files = [],
    useKB = false,
    selectedKBFiles = [],
    useWebSearch = false,
    webSearchKeyword = '',
  } = params
  return api.post('/workflow/supplement/ai-infer', {
    session_id: sessionId,
    missing_item: missingItem,
    mcp_summary: mcp_summary || '',
    selected_cases: cases,
    existing_content: existing_content || '',
    kb_file_list: kb_file_list,
    user_prompt: user_prompt || '',
    user_files: user_files || [],
    kb_files: useKB ? selectedKBFiles : [],
    use_web_search: useWebSearch,
    web_search_keyword: webSearchKeyword || '',
  })
}

// ===== 知识库自学习：补充内容管理 =====

export function addSupplement(sessionId, supplementType, dimension, content, source = 'manual', sourceDetail = {}, domainTags = []) {
  return api.post('/workflow/supplement/add', {
    session_id: sessionId,
    type: supplementType,
    dimension,
    content,
    source,
    source_detail: sourceDetail,
    domain_tags: domainTags,
  })
}

export function confirmSupplement(sessionId, supplementId) {
  return api.post('/workflow/supplement/confirm', {
    session_id: sessionId,
    supplement_id: supplementId,
  })
}

export function listSupplements(sessionId, confirmedOnly = false) {
  return api.post('/workflow/supplement/list', {
    session_id: sessionId,
    confirmed_only: confirmedOnly,
  })
}

export function exportSupplementsToDomain(sessionId, domainTag, supplementIds = null) {
  return api.post('/workflow/supplement/export', {
    session_id: sessionId,
    domain_tag: domainTag,
    supplement_ids: supplementIds,
  })
}

export function recordSessionMetadata(sessionId, domainTag = '', generationMode = '', userSatisfaction = null, exportedToDomain = false) {
  return api.post('/workflow/session/metadata', {
    session_id: sessionId,
    domain_tag: domainTag,
    generation_mode: generationMode,
    user_satisfaction: userSatisfaction,
    exported_to_domain: exportedToDomain,
  })
}

export function cleanupExpiredSupplements(days = 30) {
  return api.post('/workflow/supplement/cleanup', { days })
}

// ===== P2: source_tag 硬约束 & 4 阶段 LLM Pipeline =====

export function validateSourceTags(content, strictMode = true) {
  return api.post('/content/validate_source_tags', {
    content,
    strict_mode: strictMode,
  })
}

export function pipelineGenerate(stage, params) {
  return api.post('/content/pipeline/generate', {
    stage,
    ...params,
  })
}

export function pipelineFullWorkflow(articleText, directionList, persona, enableValidation = true) {
  return api.post('/content/pipeline/full_workflow', {
    article_text: articleText,
    direction_list: directionList,
    persona,
    enable_source_validation: enableValidation,
  })
}

// ===== ArchGen v2.0: 知识评估 + 降级链 =====

export function smartSupplement(sessionId, topic, context, missingItems = [], missingItem = {}, forceLevel = null, retrievalResults = []) {
  return api.post('/workflow/supplement/smart', {
    session_id: sessionId,
    topic,
    context,
    missing_items: missingItems,
    missing_item: missingItem,
    force_level: forceLevel,
    retrieval_results: retrievalResults,
  })
}

export function degradeSupplement(sessionId, currentLevel, topic, context, missingItem = {}) {
  return api.post('/workflow/supplement/degrade', {
    session_id: sessionId,
    current_level: currentLevel,
    topic,
    context,
    missing_item: missingItem,
  })
}

export function clearAssessmentCache(sessionId, cacheKey = null) {
  return api.post('/workflow/supplement/clear-cache', {
    session_id: sessionId,
    cache_key: cacheKey,
  })
}

// Step 3 起草模式：基于通用知识生成参考草稿（不走降级链）
export function supplementDraft(sessionId, direction, framework, missingItem = '', userHint = '') {
  return api.post('/workflow/supplement/draft', {
    session_id: sessionId,
    direction: direction,
    framework: framework,
    missing_item: missingItem,
    user_hint: userHint,
  })
}

// ===== 埋点与数据看板 =====

export function recordAnalyticsEvent(eventData) {
  return api.post('/analytics/event', eventData)
}

export function getAnalyticsEvents(sessionId = '', limit = 100) {
  const params = sessionId ? `?session_id=${sessionId}&limit=${limit}` : `?limit=${limit}`
  return api.get(`/analytics/events${params}`)
}

export function getSessionSummary(sessionId) {
  return api.get(`/analytics/session/${sessionId}`)
}

export function getAnalyticsOverview(days = 7) {
  return api.get(`/analytics/overview?days=${days}`)
}

// ===== A/B 测试 =====

export function assignABTest(sessionId, experimentKey = 'degradation_alert') {
  return api.post('/ab-test/assign', {
    session_id: sessionId,
    experiment_key: experimentKey,
  })
}

export function getABExperiments() {
  return api.get('/ab-test/experiments')
}

export function startABExperiment(experimentKey, startDate = null, endDate = null) {
  return api.post('/ab-test/start', {
    experiment_key: experimentKey,
    start_date: startDate,
    end_date: endDate,
  })
}

export function pauseABExperiment(experimentKey) {
  return api.post('/ab-test/pause', { experiment_key: experimentKey })
}

export function stopABExperiment(experimentKey) {
  return api.post('/ab-test/stop', { experiment_key: experimentKey })
}

export function calculateSignificance(groupA, groupB) {
  return api.post('/ab-test/significance', { group_a: groupA, group_b: groupB })
}


// ====================================================================
// V4.0 三列分析工作台 — 新增 API
// ====================================================================

/**
 * V4 SSE 流式：AI 流式推理生成槽位清单
 * @param {string} sessionId
 * @param {string} topic - 创作主题
 * @param {string} materialPoolSummary - 素材池概览文本
 * @param {object} callbacks - { onThinking(text), onSlot(slot), onDone(slots), onError(msg) }
 * @returns {Promise<AbortController>} - 用于中断流式连接
 */
export function generateSlots(sessionId, topic, materialPoolSummary, callbacks) {
  console.log('📡 generateSlots 被调用:', { sessionId, topic, materialPoolSummary })
  const controller = new AbortController()

  fetch('/api/workflow/slot/generate_slots', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      topic,
      material_pool_summary: materialPoolSummary || '',
    }),
    signal: controller.signal,
  }).then(async (response) => {
    console.log('📡 generateSlots fetch 响应:', { ok: response.ok, status: response.status })
    if (!response.ok) {
      callbacks.onError?.(`HTTP ${response.status}`)
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            console.log('📡 收到 SSE 数据:', data)
            if (data.type === 'thinking') {
              callbacks.onThinking?.(data.text)
            } else if (data.type === 'slot') {
              callbacks.onSlot?.({
                slot_key: data.slot_key,
                label: data.label,
                description: data.description,
              })
            } else if (data.type === 'done') {
              callbacks.onDone?.(data.slots)
            } else if (data.type === 'error') {
              callbacks.onError?.(data.msg)
            }
          } catch (e) {
            // 忽略 JSON 解析错误（可能是不完整的数据行）
          }
        }
      }
    }
  }).catch((err) => {
    console.error('📡 generateSlots fetch 错误:', err)
    if (err.name !== 'AbortError') {
      callbacks.onError?.(err.message)
    }
  })

  return controller
}

/**
 * V4 生成槽位间关系图谱
 */
export function getSlotRelations(sessionId, confirmedSlots) {
  return api.post('/workflow/slot/slot_relations', {
    session_id: sessionId,
    confirmed_slots: confirmedSlots,
  })
}

/**
 * V4 素材匹配：将素材池分配到槽位
 */
export function matchMaterials(sessionId, confirmedSlots) {
  return api.post('/workflow/slot/match_materials', {
    session_id: sessionId,
    confirmed_slots: confirmedSlots,
  })
}

/**
 * V4 生成单槽位提纲
 */
export function generateSlotOutline(sessionId, slotKey, topic, materials, writingPlan = '') {
  return api.post('/workflow/slot/generate_outline', {
    session_id: sessionId,
    slot_key: slotKey,
    topic,
    materials: materials || [],
    writing_plan: writingPlan,
  })
}

/**
 * V4 批量填充（素材+提纲并行）
 */
export function batchFillV4(sessionId, confirmedSlots) {
  return api.post('/workflow/slot/batch_fill_v4', {
    session_id: sessionId,
    confirmed_slots: confirmedSlots,
  })
}

/**
 * V4 追问 AI（支持槽位确认阶段 + 编辑面板）
 */
export function askFollowup(sessionId, context, slotKey, question, history = []) {
  return api.post('/workflow/slot/ask_followup', {
    session_id: sessionId,
    context: context,         // 'slot_confirmation' | 'edit_panel'
    slot_key: slotKey || '',
    question,
    history: history || [],
  })
}

/**
 * V4 素材可行性预检：统计每个槽位素材覆盖度 + AI 替换建议
 */
export function preCheckMaterials(sessionId, confirmedSlots) {
  return api.post('/workflow/slot/pre_check_materials', {
    session_id: sessionId,
    confirmed_slots: confirmedSlots,
  })
}

/**
 * V4 素材池统一构建：进入 Step 3 时调用
 */
export function buildMaterialPool(sessionId, mcpSummary = '', mcpFiles = []) {
  return api.post('/workflow/slot/build_material_pool', {
    session_id: sessionId,
    mcp_summary: mcpSummary || '',
    mcp_files: mcpFiles || [],
  })
}

export default api
