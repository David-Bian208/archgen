import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

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
export function aiGenerateSection(directionName, sectionTitle, sectionHint, sourceText, existingSections, outline = '', analysisType = '', analysisSuggestion = '', topicNeeded = '') {
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
export function aiRewriteSection(directionName, sectionTitle, sectionOutline, userFeedback, sourceText, existingSections) {
  return api.post('/content/ai_rewrite', {
    direction_name: directionName,
    section_title: sectionTitle,
    section_outline: sectionOutline,
    user_feedback: userFeedback,
    source_text: sourceText,
    existing_sections: existingSections,
  })
}

// AI 一键生成全文
export function aiGenerateFullContent(directionName, structure, sourceText) {
  return api.post('/content/ai_generate_full', {
    direction_name: directionName,
    structure,
    source_text: sourceText,
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

export function analyzeDirectionsV2(sessionId, mcpSummary) {
  return api.post('/workflow/directions/analyze', {
    session_id: sessionId,
    mcp_summary: mcpSummary,
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

export function checkWorkflowDirection(sessionId, direction, framework, supplement1, supplement2, mcpSummary) {
  return api.post('/workflow/direction/check', {
    session_id: sessionId,
    direction,
    framework,
    supplement_1: supplement1,
    supplement_2: supplement2,
    mcp_summary: mcpSummary,
  })
}

export function fixWorkflowDirection(sessionId, issue, supplement1, supplement2, mcpSummary, direction, framework) {
  return api.post('/workflow/direction/fix', {
    session_id: sessionId,
    issue,
    supplement_1: supplement1,
    supplement_2: supplement2,
    mcp_summary: mcpSummary,
    direction,
    framework,
  })
}

export function recommendStructures(sessionId, direction, framework, supplement1, supplement2, mcpSummary) {
  return api.post('/workflow/structures/recommend', {
    session_id: sessionId,
    direction,
    framework,
    supplement_1: supplement1,
    supplement_2: supplement2,
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

export default api
