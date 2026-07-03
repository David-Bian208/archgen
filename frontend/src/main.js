import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ArcoVue from '@arco-design/web-vue'
import { Message } from '@arco-design/web-vue'
import router from './router'
import App from './App.vue'
import '@arco-design/web-vue/dist/arco.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ArcoVue)

// 全局错误处理器：捕获 Vue 运行时错误，统一日志 + 用户提示
app.config.errorHandler = (err, instance, info) => {
  console.error('[Global Error]', err, info)
  try {
    Message.error('系统异常，请刷新重试')
  } catch (_) {
    // 静默降级
  }
}

app.mount('#app')
