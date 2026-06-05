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
  },
  {
    path: '/frameworks',
    name: 'FrameworkSelect',
    component: () => import('./views/FrameworkSelectView.vue'),
  },
  {
    path: '/structured-form',
    name: 'StructuredForm',
    component: () => import('./views/StructuredFormView.vue'),
  },
  {
    path: '/data-input',
    name: 'DataInput',
    component: () => import('./views/DataInputView.vue'),
  },
  {
    path: '/text-preview',
    name: 'TextPreview',
    component: () => import('./views/TextPreviewView.vue'),
  },
  {
    path: '/mcp-search',
    name: 'MCPSearch',
    component: () => import('./views/MCPSearchView.vue'),
  },
  {
    path: '/topic-suggest',
    name: 'TopicSuggest',
    component: () => import('./views/TopicSuggestView.vue'),
  },
  {
    path: '/preview',
    name: 'Preview',
    component: () => import('./views/PreviewView.vue'),
  },
  {
    path: '/output',
    name: 'Output',
    component: () => import('./views/OutputView.vue'),
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
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
