<template>
  <a-layout class="app">
    <a-layout-header class="header">
      <div class="header-content">
        <div class="logo" @click="$router.push('/')">
          <h1>ArchGen</h1>
        </div>
        <div class="header-desc">逻辑框架可视化引擎</div>
        <div class="header-actions">
          <a-button type="text" @click="$router.push('/settings')">
            <icon-settings />
            设置
          </a-button>
        </div>
      </div>
    </a-layout-header>
    <a-layout-content class="content">
      <router-view />
    </a-layout-content>
    <a-layout-footer class="footer">
      ArchGen
    </a-layout-footer>
  </a-layout>
</template>

<script setup>
import { onMounted } from 'vue'
import { getHealth } from './utils/api'
import { IconSettings } from '@arco-design/web-vue/es/icon'

onMounted(async () => {
  try {
    await getHealth()
    console.log('ArchGen API 连接正常')
  } catch (error) {
    console.warn('ArchGen API 未连接，请确保后端服务运行在 :8919')
  }
})
</script>

<style scoped>
.app {
  min-height: 100vh;
  background: #f5f7fa;
}
.header {
  background: linear-gradient(135deg, #3498db 0%, #2c3e50 100%);
  padding: 0 20px;
}
.header-content {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.logo {
  cursor: pointer;
}
.logo h1 {
  color: white;
  margin: 0;
  font-size: 24px;
}
.header-desc {
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;
}
.header-actions {
  margin-left: auto;
}
.header-actions .arco-btn-text {
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
}
.header-actions .arco-btn-text:hover {
  color: white;
}
.content {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}
.footer {
  text-align: center;
  color: #999;
}
</style>
