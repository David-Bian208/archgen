import { createApp } from 'vue'
import App from './App.vue'
import { escapeText, decodeHTMLEntities } from './utils/filters'

const app = createApp(App)

// V3.6 新增：全局注册文本安全过滤器
app.config.globalProperties.$escape = escapeText

// V3.8 新增：全局注册 HTML 实体解码器
app.config.globalProperties.$decodeHTML = decodeHTMLEntities

app.mount('#app')
