import { ref, reactive, computed, watch, nextTick, h, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import {
  recommendStructures,
  supplementStep3,
  generateWorkflowOutline,
  apiInferSupplement,
} from '../utils/api'
import { useWorkflowState } from './useWorkflowState'

// ==================== 模块级单例状态 ====================
// 以下 ref/reactive/computed 声明在模块作用域中，
// 使 useStep4_Outline() 的所有调用者共享同一组状态实例

// ==================== 步骤2 分析状态（供提纲生成使用）====================
const analysisBody = ref('')
const slotCoverage = ref({})

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

const outlineCompletenessStatus = computed(() => {
  if (!outlineResult.value?.sections) return 'red'
  const sections = outlineResult.value.sections
  const anchoredCount = Object.values(sections).filter(s => s.source_tag === 'anchored').length
  const missingCount = outlineResult.value.missing_items?.length || 0
  if (anchoredCount >= 4 && missingCount <= 1) return 'green'
  if (anchoredCount >= 2 && missingCount <= 3) return 'yellow'
  return 'red'
})

// ==================== 超时管理 ====================
const _timeoutIds = []

function $setTimeout(fn, delay, ...args) {
  const id = window.setTimeout(fn, delay, ...args)
  _timeoutIds.push(id)
  return id
}

export function useStep4_Outline() {
  const route = useRoute()
  const router = useRouter()

  const {
    sessionId,
    currentStep,
    loading,
    selectedDirection,
    selectedFramework,
    supplement2Text,
    supplement2Form,
    mcpSummary,
    mcpFiles,
    loadFrameworks,
  } = useWorkflowState()

  // ==================== 结构推荐 ====================

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

  // ==================== 提纲 ====================

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

  return {
    // ==== refs ====
    structures,
    structuresLoading,
    selectedStructure,
    analysisBody,
    slotCoverage,
    outlineResult,
    showOutlineAlignmentReason,
    targetWordCount,
    sectionAiDialogIndex,
    sectionAiInput,
    sectionAiLoading,
    sectionAiResult,
    outlineOneClickLoading,
    sectionAiKbFiles,
    sectionAiUploadFiles,
    // ==== computed ====
    outlineCompletenessStatus,
    // ==== functions ====
    goToStructures,
    selectStructure,
    goBackToStructures,
    loadOutline,
    regenerateOutline,
    goToOutlineFromDetection,
    toggleSectionAiDialog,
    aiSupplementSectionByKey,
    acceptSectionAiSuggestionByKey,
    handleSectionAiUpload,
    outlineOneClickAiSupplement,
  }
}
