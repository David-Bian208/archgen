import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('./views/HomeView.vue'),
  },
  {
    path: '/directions',
    name: 'DirectionSuggest',
    component: () => import('./views/DirectionSuggestView.vue'),
    meta: { requiresSession: true },
  },
  {
    path: '/frameworks',
    name: 'FrameworkSelect',
    component: () => import('./views/FrameworkSelectView.vue'),
    meta: { requiresSession: true },
  },
  {
    path: '/structured-form',
    name: 'StructuredForm',
    component: () => import('./views/StructuredFormView.vue'),
    meta: { requiresSession: true },
  },
  {
    path: '/data-input',
    name: 'DataInput',
    component: () => import('./views/DataInputView.vue'),
    meta: { requiresSession: true },
  },
  {
    path: '/text-preview',
    name: 'TextPreview',
    component: () => import('./views/TextPreviewView.vue'),
    meta: { requiresData: true },
  },
  {
    path: '/mcp-search',
    name: 'MCPSearch',
    component: () => import('./views/MCPSearchView.vue'),
  },
  {
    path: '/preview',
    name: 'Preview',
    component: () => import('./views/PreviewView.vue'),
    meta: { requiresData: true },
  },
  {
    path: '/output',
    name: 'Output',
    component: () => import('./views/OutputView.vue'),
    meta: { requiresData: true },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('./views/SettingsView.vue'),
  },
  {
    path: '/persona',
    name: 'PersonaSettings',
    component: () => import('./views/PersonaSettingsView.vue'),
  },
  {
    path: '/workflow',
    name: 'Workflow',
    component: () => import('./views/WorkflowView.vue'),
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('./views/NotFoundView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫：防止在没有上下文的情况下进入数据依赖页面
router.beforeEach((to, from, next) => {
  // 需要 session 的页面：检查 URL 中是否有 sessionId
  if (to.meta.requiresSession) {
    const hasSession = from.query?.sessionId || to.query?.sessionId
    if (!hasSession) {
      // 静默通过——用户可能从其他入口进入，不阻断
      console.debug(`[Router] 进入 ${to.path} 无 sessionId，允许通过`)
    }
  }
  // 需要数据的页面：检查是否有来源
  if (to.meta.requiresData) {
    const hasDataRef = document.referrer || from.name
    if (!hasDataRef && from.name !== 'Workflow') {
      console.debug(`[Router] 进入 ${to.path} 无数据来源，允许通过`)
    }
  }
  next()
})

export default router
