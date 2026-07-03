import { ref, reactive, computed, watch, nextTick, h, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import {
  generateInfographic as apiGenerateInfographic,
  reviseInfographic as apiReviseInfographic,
} from '../utils/api'
import { useWorkflowState } from './useWorkflowState'

// ==================== 模块级单例状态 ====================
// 以下 ref/reactive/computed 声明在模块作用域中，
// 使 useStep7_Images() 的所有调用者共享同一组状态实例

// ==================== 配图状态 ====================
const infographicHtml = ref('')
const infographicGenerating = ref(false)
const infographicRevising = ref(false)
const infographicFeedback = ref('')
const generatedImageUrl = ref('')
const imageGenerating = ref(false)

export function useStep7_Images() {
  const route = useRoute()
  const router = useRouter()

  const {
    currentStep,
    selectedFramework,
    articleResult,
  } = useWorkflowState()

  // ==================== 配图 ====================

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

  return {
    // ==== refs ====
    infographicHtml,
    infographicGenerating,
    infographicRevising,
    infographicFeedback,
    generatedImageUrl,
    imageGenerating,
    // ==== functions ====
    goToGenerateImage,
    handleGenerateInfographic,
    handleReviseInfographic,
    openInfographicInNewTab,
    downloadInfographicAsImage,
  }
}
