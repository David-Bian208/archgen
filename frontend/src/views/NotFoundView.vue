<template>
  <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 60vh; text-align: center;">
    <h1 style="font-size: 72px; color: #c9cdd4; margin: 0;">404</h1>
    <p style="font-size: 18px; color: #86909c; margin: 16px 0 24px;">页面未找到</p>
    <a-button type="primary" @click="goHome">返回首页</a-button>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
const router = useRouter()
function goHome() {
  router.push('/')
}
</script>
