import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const currentStep = ref(0)
  const inputText = ref('')
  const uploadedFile = ref(null)
  const uploadedImage = ref(null)
  const uploadedImageName = ref('')
  const category = ref('')
  const categoryConfidence = ref(0)
  const categoryAlternatives = ref([])
  const selectedFramework = ref(null)
  const frameworkList = ref([])
  const formData = ref({})
  const previewHtml = ref('')
  const outputImageUrl = ref('')
  const mcpResult = ref(null)
  const selectedDirection = ref(null)
  const kbFile = ref(null)
  const style = ref('minimal')
  const size = ref('default')
  const loading = ref(false)

  function reset() {
    currentStep.value = 0
    inputText.value = ''
    uploadedFile.value = null
    category.value = ''
    categoryConfidence.value = 0
    categoryAlternatives.value = []
    selectedFramework.value = null
    frameworkList.value = []
    formData.value = {}
    previewHtml.value = ''
    outputImageUrl.value = ''
    mcpResult.value = null
    selectedDirection.value = null
    loading.value = false
  }

  return {
    currentStep,
    inputText,
    uploadedFile,
    category,
    categoryConfidence,
    categoryAlternatives,
    selectedFramework,
    frameworkList,
    formData,
    previewHtml,
    outputImageUrl,
    mcpResult,
    selectedDirection,
    kbFile,
    style,
    size,
    loading,
    reset,
  }
})
