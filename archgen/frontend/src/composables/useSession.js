import { ref } from 'vue'

// ==================== 模块级单例状态 ====================
const loading = ref(false)
const currentStep = ref(0)
const sessionId = ref('')
const collapsedSteps = ref([])

// ==================== 导出 ====================
export function useSession() {
  return {
    loading,
    currentStep,
    sessionId,
    collapsedSteps,
  }
}
