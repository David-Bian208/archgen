import { ref, reactive, computed, watch, nextTick, h, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import {
  generateFullArticle,
  apiInferSupplement,
} from '../utils/api'
import { useWorkflowState } from './useWorkflowState'

// ==================== 模块级单例状态 ====================
// 以下 ref/reactive/computed 声明在模块作用域中，
// 使 useStep5_Article() 的所有调用者共享同一组状态实例

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

// ==================== 超时管理 ====================
const _timeoutIds = []

function $setTimeout(fn, delay, ...args) {
  const id = window.setTimeout(fn, delay, ...args)
  _timeoutIds.push(id)
  return id
}

export function useStep5_Article() {
  const route = useRoute()
  const router = useRouter()

  const {
    sessionId,
    currentStep,
    loading,
    supplement2Text,
    outlineResult,
    targetWordCount,
    mcpSummary,
    loadOutline,
  } = useWorkflowState()

  // ==================== 文章生成 ====================

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

  return {
    // ==== refs ====
    articleResult,
    articleAiDialogIndex,
    articleAiInput,
    articleAiKbFiles,
    articleAiUploadFiles,
    articleAiLoading,
    articleAiResult,
    articleOneClickLoading,
    // ==== computed ====
    totalWordCount,
    readingTime,
    // ==== functions ====
    goToGenerateArticle,
    generateArticle,
    toggleArticleAiDialog,
    handleArticleAiUpload,
    aiAdjustArticleParagraph,
    acceptArticleAiSuggestion,
    articleOneClickRegenerate,
    exportArticle,
  }
}
