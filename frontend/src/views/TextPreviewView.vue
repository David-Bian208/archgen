<template>
  <div class="text-preview-view">
    <a-page-header title="文字分析预览" @back="$router.push('/data-input')">
      <template #extra>
        <a-steps :current="3" :max="5" style="width: 300px">
          <a-step>输入</a-step>
          <a-step>框架</a-step>
          <a-step>数据</a-step>
          <a-step>文字预览</a-step>
          <a-step>图片</a-step>
        </a-steps>
      </template>
    </a-page-header>

    <a-card class="framework-info">
      <template #title>
        <div class="info-title">
          <icon-apps />
          <span>{{ appStore.selectedFramework?.name }}</span>
          <a-tag color="blue">{{ getLayoutName(appStore.selectedFramework?.layout_style) }}</a-tag>
        </div>
      </template>
    </a-card>

    <!-- 数据质量检查 -->
    <a-card class="quality-card">
      <template #title>
        <div class="card-title">
          <icon-check-circle />
          <span>数据质量检查</span>
        </div>
      </template>

      <div class="quality-summary">
        <div class="quality-score" :class="qualityScoreClass">
          <div class="score-value">{{ qualityScore }}%</div>
          <div class="score-label">数据完整度</div>
        </div>
        <div class="quality-stats">
          <div class="stat-item">
            <span class="stat-dot green"></span>
            <span class="stat-label">已填写</span>
            <span class="stat-value">{{ filledCount }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-dot gray"></span>
            <span class="stat-label">未填写</span>
            <span class="stat-value">{{ missingCount }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">总字段数</span>
            <span class="stat-value">{{ totalFields }}</span>
          </div>
        </div>
      </div>

      <a-alert v-if="missingFields.length > 0" type="warning" style="margin-top: 16px">
        <template #title>以下字段尚未填写，可能影响架构图质量：</template>
        <ul class="missing-list">
          <li v-for="field in missingFields" :key="field.key">
            <strong>{{ field.label }}</strong> - {{ field.suggestion || '建议补充' }}
          </li>
        </ul>
        <a-button type="primary" size="small" @click="handleEdit" style="margin-top: 8px">
          返回补充数据
        </a-button>
      </a-alert>

      <a-alert v-if="qualityScore >= 70" type="success" style="margin-top: 12px">
        <template #title>数据质量良好，可以生成架构图</template>
        <div>已填写 {{ filledCount }} / {{ totalFields }} 个字段</div>
      </a-alert>
    </a-card>

    <a-card class="text-preview-card">
      <template #title>
        <div class="card-title">
          <icon-bulb />
          <span>结构化分析结果</span>
        </div>
      </template>

      <div class="text-content">
        <a-spin :loading="loading">
          <!-- 分析标题 -->
          <div class="analysis-title">
            <h2>{{ parsedData.title || '未命名分析' }}</h2>
            <a-tag color="green" v-if="appStore.category">
              {{ getCategoryName(appStore.category) }}
            </a-tag>
          </div>

          <a-divider />

          <!-- SWOT 分析 -->
          <template v-if="frameworkKey === 'swot'">
            <div class="swot-preview">
              <div class="swot-section strengths" :class="{ empty: !parsedData.strengths?.length }">
                <h3> 优势 (Strengths)</h3>
                <ul v-if="parsedData.strengths?.length">
                  <li v-for="(item, i) in parsedData.strengths" :key="i">{{ item }}</li>
                </ul>
                <span v-else class="empty-hint">待补充</span>
              </div>
              <div class="swot-section weaknesses" :class="{ empty: !parsedData.weaknesses?.length }">
                <h3>⚠️ 劣势 (Weaknesses)</h3>
                <ul v-if="parsedData.weaknesses?.length">
                  <li v-for="(item, i) in parsedData.weaknesses" :key="i">{{ item }}</li>
                </ul>
                <span v-else class="empty-hint">待补充</span>
              </div>
              <div class="swot-section opportunities" :class="{ empty: !parsedData.opportunities?.length }">
                <h3>🚀 机会 (Opportunities)</h3>
                <ul v-if="parsedData.opportunities?.length">
                  <li v-for="(item, i) in parsedData.opportunities" :key="i">{{ item }}</li>
                </ul>
                <span v-else class="empty-hint">待补充</span>
              </div>
              <div class="swot-section threats" :class="{ empty: !parsedData.threats?.length }">
                <h3>⚡ 威胁 (Threats)</h3>
                <ul v-if="parsedData.threats?.length">
                  <li v-for="(item, i) in parsedData.threats" :key="i">{{ item }}</li>
                </ul>
                <span v-else class="empty-hint">待补充</span>
              </div>
            </div>
          </template>

          <!-- 商业模式画布 -->
          <template v-else-if="frameworkKey === 'business_canvas'">
            <div class="canvas-preview">
              <div class="canvas-row">
                <div class="canvas-cell" :class="{ empty: !parsedData.key_partnerships?.length }">
                <h4>🤝 合作伙伴</h4>
                <ul v-if="parsedData.key_partnerships?.length"><li v-for="(item, i) in parsedData.key_partnerships" :key="i">{{ item }}</li></ul>
                <span v-else class="empty-hint">待补充</span>
              </div>
              <div class="canvas-cell" :class="{ empty: !parsedData.key_activities?.length }">
                <h4>关键业务</h4>
                <ul v-if="parsedData.key_activities?.length"><li v-for="(item, i) in parsedData.key_activities" :key="i">{{ item }}</li></ul>
                <span v-else class="empty-hint">待补充</span>
              </div>
              <div class="canvas-cell highlight" :class="{ empty: !parsedData.value_propositions?.length }">
                <h4>价值主张</h4>
                <ul v-if="parsedData.value_propositions?.length"><li v-for="(item, i) in parsedData.value_propositions" :key="i">{{ item }}</li></ul>
                <span v-else class="empty-hint">待补充</span>
              </div>
              <div class="canvas-cell" :class="{ empty: !parsedData.customer_relationships?.length }">
                <h4>❤️ 客户关系</h4>
                <ul v-if="parsedData.customer_relationships?.length"><li v-for="(item, i) in parsedData.customer_relationships" :key="i">{{ item }}</li></ul>
                <span v-else class="empty-hint">待补充</span>
              </div>
              <div class="canvas-cell" :class="{ empty: !parsedData.customer_segments?.length }">
                <h4>👥 客户细分</h4>
                <ul v-if="parsedData.customer_segments?.length"><li v-for="(item, i) in parsedData.customer_segments" :key="i">{{ item }}</li></ul>
                <span v-else class="empty-hint">待补充</span>
              </div>
              </div>
              <div class="canvas-row">
                <div class="canvas-cell" :class="{ empty: !parsedData.key_resources?.length }">
                <h4>📦 核心资源</h4>
                <ul v-if="parsedData.key_resources?.length"><li v-for="(item, i) in parsedData.key_resources" :key="i">{{ item }}</li></ul>
                <span v-else class="empty-hint">待补充</span>
              </div>
              <div class="canvas-cell" :class="{ empty: !parsedData.channels?.length }">
                <h4>📢 渠道通路</h4>
                <ul v-if="parsedData.channels?.length"><li v-for="(item, i) in parsedData.channels" :key="i">{{ item }}</li></ul>
                <span v-else class="empty-hint">待补充</span>
              </div>
              <div class="canvas-cell" style="flex: 2;" :class="{ empty: !parsedData.cost_structure?.length }">
                <h4>💰 成本结构</h4>
                <ul v-if="parsedData.cost_structure?.length"><li v-for="(item, i) in parsedData.cost_structure" :key="i">{{ item }}</li></ul>
                <span v-else class="empty-hint">待补充</span>
              </div>
              <div class="canvas-cell" style="flex: 2;" :class="{ empty: !parsedData.revenue_streams?.length }">
                <h4>💵 收入来源</h4>
                <ul v-if="parsedData.revenue_streams?.length"><li v-for="(item, i) in parsedData.revenue_streams" :key="i">{{ item }}</li></ul>
                <span v-else class="empty-hint">待补充</span>
              </div>
              </div>
            </div>
          </template>

          <!-- PESTEL 分析 -->
          <template v-else-if="frameworkKey === 'pestel'">
            <div class="pestel-preview">
              <div class="pestel-item" v-for="dim in pestelDimensions" :key="dim.key" :class="{ empty: !parsedData[dim.key]?.length }">
                <h4>{{ dim.icon }} {{ dim.label }}</h4>
                <ul v-if="parsedData[dim.key]?.length">
                  <li v-for="(item, i) in parsedData[dim.key]" :key="i">{{ item }}</li>
                </ul>
                <span v-else class="empty-hint">待补充</span>
              </div>
            </div>
          </template>

          <!-- 时间管理矩阵 -->
          <template v-else-if="frameworkKey === 'time_matrix'">
            <div class="time-preview">
              <div class="time-quadrant q1">
                <h4>🔥 Q1 重要且紧急（立即做）</h4>
                <ul><li v-for="(item, i) in parsedData.q1_important_urgent" :key="i"><strong>{{ item.name }}</strong> - {{ item.description }}</li></ul>
              </div>
              <div class="time-quadrant q2">
                <h4>📅 Q2 重要不紧急（计划做）</h4>
                <ul><li v-for="(item, i) in parsedData.q2_important_not_urgent" :key="i"><strong>{{ item.name }}</strong> - {{ item.description }}</li></ul>
              </div>
              <div class="time-quadrant q3">
                <h4>⚡ Q3 不重要但紧急（委派做）</h4>
                <ul><li v-for="(item, i) in parsedData.q3_not_important_urgent" :key="i"><strong>{{ item.name }}</strong> - {{ item.description }}</li></ul>
              </div>
              <div class="time-quadrant q4">
                <h4>️ Q4 不重要不紧急（减少做）</h4>
                <ul><li v-for="(item, i) in parsedData.q4_not_important_not_urgent" :key="i"><strong>{{ item.name }}</strong> - {{ item.description }}</li></ul>
              </div>
            </div>
          </template>

          <!-- 用户旅程 -->
          <template v-else-if="frameworkKey === 'user_journey'">
            <div class="journey-preview">
              <div class="persona-info">
                <strong>用户角色：</strong>{{ parsedData.persona }}
              </div>
              <div class="stage-list">
                <div class="stage-item" v-for="stage in parsedData.stages" :key="stage.order">
                  <div class="stage-header">
                    <span class="stage-num">{{ stage.order }}</span>
                    <span class="stage-name">{{ stage.name }}</span>
                    <span class="stage-emotion">{{ '⭐'.repeat(stage.emotion || 3) }}</span>
                  </div>
                  <p v-if="stage.description">{{ stage.description }}</p>
                  <div v-if="stage.touchpoints && stage.touchpoints.length" class="stage-detail">
                    <strong>触点：</strong>{{ stage.touchpoints.join('、') }}
                  </div>
                  <div v-if="stage.pain_points && stage.pain_points.length" class="stage-detail pain">
                    <strong>痛点：</strong>{{ stage.pain_points.join('、') }}
                  </div>
                </div>
              </div>
            </div>
          </template>

          <!-- 主张型 -->
          <template v-else-if="frameworkKey === 'claim'">
            <div class="claim-preview">
              <div class="central-claim" :class="{ empty: !parsedData.central_claim }">
                <h3>核心主张</h3>
                <p>{{ parsedData.central_claim || '待补充' }}</p>
              </div>
              <div class="supporting-points">
                <h3>分论点支撑</h3>
                <div class="point-item" v-for="(point, i) in parseSupportingPoints" :key="i">
                  <strong>{{ point.label || point }}</strong>
                  <p v-if="point.text">{{ point.text }}</p>
                </div>
                <span v-if="!parseSupportingPoints.length" class="empty-hint">待补充</span>
              </div>
              <div class="conclusion" :class="{ empty: !parsedData.conclusion }">
                <h3>结论</h3>
                <p>{{ parsedData.conclusion || '待补充' }}</p>
              </div>
            </div>
          </template>

          <!-- 因果分析 -->
          <template v-else-if="frameworkKey === 'causal'">
            <div class="causal-preview">
              <div class="root-cause">
                <h4>根本原因</h4>
                <p>{{ parsedData.root_cause }}</p>
              </div>
              <div class="chain-list">
                <div class="chain-item" v-for="(link, i) in parsedData.chain" :key="i">
                  <span class="chain-step">步骤 {{ link.step }}</span>
                  <span class="chain-arrow">→</span>
                  <span class="chain-cause">{{ link.cause }}</span>
                  <span class="chain-arrow">→</span>
                  <span class="chain-effect">{{ link.effect }}</span>
                </div>
              </div>
              <div class="final-effect">
                <h4>最终结果</h4>
                <p>{{ parsedData.final_effect }}</p>
              </div>
            </div>
          </template>

          <!-- 系统架构 -->
          <template v-else-if="frameworkKey === 'system'">
            <div class="system-preview">
              <div class="system-overview">
                <h4>系统概述</h4>
                <p>{{ parsedData.overview }}</p>
              </div>
              <div class="module-list">
                <div class="module-item" v-for="mod in parsedData.modules" :key="mod.name">
                  <h4>{{ mod.name }}</h4>
                  <p><strong>职责：</strong>{{ mod.role }}</p>
                  <p v-if="mod.connections"><strong>连接：</strong>{{ mod.connections.join('、') }}</p>
                </div>
              </div>
            </div>
          </template>

          <!-- 对比分析 -->
          <template v-else-if="frameworkKey === 'comparison'">
            <div class="comparison-preview">
              <table class="comparison-table">
                <thead>
                  <tr>
                    <th>维度</th>
                    <th v-for="(item, i) in parsedData.items" :key="i">{{ item.name }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(dim, i) in parsedData.dimensions" :key="i">
                    <td class="dimension">{{ dim }}</td>
                    <td v-for="(item, j) in parsedData.items" :key="j">{{ item.scores ? item.scores[i] : '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>

          <!-- 流程分析 -->
          <template v-else-if="frameworkKey === 'process'">
            <div class="process-preview">
              <div class="step-item" v-for="step in parsedData.steps" :key="step.order">
                <div class="step-header">
                  <span class="step-num">{{ step.order }}</span>
                  <h4>{{ step.title }}</h4>
                </div>
                <p>{{ step.description }}</p>
                <div v-if="step.tips && step.tips.length" class="step-tips">
                  <strong>提示：</strong>{{ step.tips.join('；') }}
                </div>
              </div>
            </div>
          </template>

          <!-- 总结 -->
          <div v-if="parsedData.summary" class="summary-section">
            <a-divider />
            <h3>📝 总结建议</h3>
            <p>{{ parsedData.summary }}</p>
          </div>
        </a-spin>
      </div>
    </a-card>

    <!-- 操作按钮 -->
    <a-space direction="vertical" style="width: 100%">
      <a-alert v-if="qualityScore < 50" type="warning" style="margin-bottom: 12px">
        <template #title>数据完整度较低，建议先补充缺失字段</template>
      </a-alert>

      <a-button
        type="primary"
        size="large"
        long
        :loading="imageLoading"
        :disabled="qualityScore < 30"
        @click="handleGenerateImage"
        class="submit-btn"
      >
        <icon-image />
        确认无误，生成架构图（PNG）
      </a-button>

      <a-alert v-if="qualityScore < 30" type="error" style="margin-top: 8px">
        <template #title>数据完整度不足 30%，无法生成架构图</template>
        <div>请至少填写 {{ Math.ceil(totalFields * 0.3) }} 个字段后再试</div>
      </a-alert>
      <a-button
        size="large"
        long
        @click="handleEdit"
      >
        <icon-edit />
        返回编辑数据
      </a-button>
    </a-space>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import {
  IconApps,
  IconBulb,
  IconImage,
  IconEdit,
  IconCheckCircle,
} from '@arco-design/web-vue/es/icon'
import { useAppStore } from '../stores/app'
import { generatePreview, generateDiagram } from '../utils/api'

const appStore = useAppStore()
const router = useRouter()
const loading = ref(false)
const imageLoading = ref(false)

const frameworkKey = computed(() => appStore.selectedFramework?.key)
const parsedData = ref({})

const categoryNames = {
  business: '商业分析',
  finance: '财务分析',
  product: '产品设计',
  operations: '运营优化',
  personal: '个人成长',
  risk: '风险管理',
  project: '项目管理',
}

const layoutNames = {
  '2x2_matrix': '2x2 矩阵',
  '9_grid': '九宫格',
  '6_columns': '6 列布局',
  timeline: '时间轴',
  center_radial: '中心辐射',
  flow_chart: '流程图',
  layered_arch: '分层架构',
  comparison_table: '对比表格',
}

const pestelDimensions = [
  { key: 'political', icon: '🏛️', label: 'Political 政治' },
  { key: 'economic', icon: '📈', label: 'Economic 经济' },
  { key: 'social', icon: '👥', label: 'Social 社会' },
  { key: 'technological', icon: '💻', label: 'Technological 技术' },
  { key: 'environmental', icon: '🌍', label: 'Environmental 环境' },
  { key: 'legal', icon: '⚖️', label: 'Legal 法律' },
]

const getCategoryName = (key) => categoryNames[key] || key
const getLayoutName = (key) => layoutNames[key] || key

const frameworkFields = {
  swot: [
    { key: 'strengths', label: '优势' },
    { key: 'weaknesses', label: '劣势' },
    { key: 'opportunities', label: '机会' },
    { key: 'threats', label: '威胁' },
  ],
  business_canvas: [
    { key: 'customer_segments', label: '客户细分' },
    { key: 'value_propositions', label: '价值主张' },
    { key: 'channels', label: '渠道通路' },
    { key: 'customer_relationships', label: '客户关系' },
    { key: 'revenue_streams', label: '收入来源' },
    { key: 'key_resources', label: '核心资源' },
    { key: 'key_activities', label: '关键业务' },
    { key: 'key_partnerships', label: '合作伙伴' },
    { key: 'cost_structure', label: '成本结构' },
  ],
  pestel: [
    { key: 'political', label: '政治' },
    { key: 'economic', label: '经济' },
    { key: 'social', label: '社会' },
    { key: 'technological', label: '技术' },
    { key: 'environmental', label: '环境' },
    { key: 'legal', label: '法律' },
  ],
  time_matrix: [
    { key: 'q1_important_urgent', label: '重要紧急' },
    { key: 'q2_important_not_urgent', label: '重要不紧急' },
    { key: 'q3_not_important_urgent', label: '不重要紧急' },
    { key: 'q4_not_important_not_urgent', label: '不重要不紧急' },
  ],
  user_journey: [
    { key: 'persona', label: '用户角色' },
    { key: 'stages', label: '旅程阶段' },
  ],
  claim: [
    { key: 'central_claim', label: '核心主张' },
    { key: 'supporting_points', label: '分论点' },
    { key: 'conclusion', label: '结论' },
  ],
  causal: [
    { key: 'root_cause', label: '根本原因' },
    { key: 'chain', label: '因果链' },
    { key: 'final_effect', label: '最终结果' },
  ],
  system: [
    { key: 'overview', label: '系统概述' },
    { key: 'modules', label: '模块列表' },
  ],
  comparison: [
    { key: 'dimensions', label: '对比维度' },
    { key: 'items', label: '对比项' },
  ],
  process: [
    { key: 'steps', label: '步骤列表' },
  ],
}

const currentFields = computed(() => frameworkFields[frameworkKey.value] || [])
const totalFields = computed(() => currentFields.value.length)

const missingFields = computed(() => {
  return currentFields.value.filter(f => {
    const val = parsedData.value[f.key]
    if (!val) return true
    if (Array.isArray(val)) return val.length === 0
    if (typeof val === 'string') return val.trim() === ''
    return false
  }).map(f => ({ ...f, suggestion: getMissingSuggestion(f.key) }))
})

const filledCount = computed(() => totalFields.value - missingFields.value.length)
const missingCount = computed(() => missingFields.value.length)

const qualityScore = computed(() => {
  if (totalFields.value === 0) return 0
  return Math.round((filledCount.value / totalFields.value) * 100)
})

const qualityScoreClass = computed(() => {
  if (qualityScore.value >= 80) return 'good'
  if (qualityScore.value >= 50) return 'warning'
  return 'bad'
})

function getMissingSuggestion(fieldKey) {
  const suggestions = {
    strengths: '请描述优势或核心竞争力',
    weaknesses: '请描述劣势或不足之处',
    opportunities: '请描述市场机会或发展趋势',
    threats: '请描述潜在威胁或风险',
    customer_segments: '请描述目标客户群体',
    value_propositions: '请描述核心价值主张',
    channels: '请描述渠道或分发方式',
    customer_relationships: '请描述客户关系维护方式',
    revenue_streams: '请描述收入来源或盈利模式',
    key_resources: '请描述核心资源',
    key_activities: '请描述关键业务活动',
    key_partnerships: '请描述重要合作伙伴',
    cost_structure: '请描述成本结构',
    political: '请描述政治因素',
    economic: '请描述经济因素',
    social: '请描述社会因素',
    technological: '请描述技术因素',
    environmental: '请描述环境因素',
    legal: '请描述法律因素',
    q1_important_urgent: '请列出重要且紧急的任务',
    q2_important_not_urgent: '请列出重要不紧急的任务',
    q3_not_important_urgent: '请列出不重要但紧急的任务',
    q4_not_important_not_urgent: '请列出不重要不紧急的任务',
    persona: '请描述目标用户角色',
    stages: '请描述用户旅程阶段',
    central_claim: '请描述核心主张或观点',
    supporting_points: '请列出支撑论点',
    conclusion: '请总结结论',
    root_cause: '请描述根本原因',
    chain: '请描述因果链条',
    final_effect: '请描述最终结果',
    overview: '请描述系统概述',
    modules: '请列出系统模块',
    dimensions: '请列出对比维度',
    items: '请列出对比对象',
    steps: '请描述流程步骤',
  }
  return suggestions[fieldKey] || '建议补充'
}

// Generic parser for array fields stored as newline-separated strings
const parseArrayField = (value) => {
  if (!value) return []
  if (Array.isArray(value)) return value
  if (typeof value === 'string') {
    // Try JSON first
    try {
      const parsed = JSON.parse(value)
      return Array.isArray(parsed) ? parsed : [parsed]
    } catch (e) {
      // Fall back to newline-separated
      return value.split('\n').filter(v => v.trim())
    }
  }
  return []
}

// Generic parser for JSON fields stored as strings
const parseJsonField = (value) => {
  if (!value) return []
  if (Array.isArray(value)) return value
  if (typeof value === 'string') {
    try {
      return JSON.parse(value)
    } catch (e) {
      return []
    }
  }
  return []
}

onMounted(() => {
  // Deep copy and parse formData to ensure proper types
  const raw = appStore.formData || {}
  console.log('[TextPreview] raw formData:', raw)
  
  const parsed = {}
  for (const [key, value] of Object.entries(raw)) {
    // Check if this field should be an array based on framework field definitions
    const fieldDef = currentFields.value.find(f => f.key === key)
    if (fieldDef?.type === 'array') {
      parsed[key] = parseArrayField(value)
    } else {
      // For text fields, keep original value but try to parse JSON if it looks like JSON
      if (typeof value === 'string' && value.trim().startsWith('[')) {
        try {
          parsed[key] = JSON.parse(value)
        } catch (e) {
          parsed[key] = value
        }
      } else {
        parsed[key] = value
      }
    }
  }
  parsedData.value = parsed
  console.log('[TextPreview] parsedData:', parsed)
  console.log('[TextPreview] selectedFramework:', appStore.selectedFramework)
})

const handleEdit = () => {
  router.push('/data-input')
}

const handleGenerateImage = async () => {
  imageLoading.value = true
  try {
    const sourceText = appStore.mcpResult?.summary || appStore.inputText
    const result = await generatePreview(
      frameworkKey.value,
      parsedData.value,
      sourceText,
      appStore.style,
      appStore.size
    )
    if (result.data.code === 0) {
      appStore.previewHtml = result.data.data.html
      router.push('/preview')
    } else {
      Message.error('预览生成失败: ' + result.data.msg)
    }
  } catch (error) {
    Message.error('预览生成失败: ' + error.message)
  } finally {
    imageLoading.value = false
  }
}
</script>

<style scoped>
.text-preview-view {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
}
.framework-info {
  margin-bottom: 20px;
}
.info-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
.quality-card {
  margin-bottom: 20px;
  border-left: 4px solid #3498db;
}
.quality-summary {
  display: flex;
  align-items: center;
  gap: 32px;
}
.quality-score {
  text-align: center;
  padding: 16px 24px;
  border-radius: 12px;
  min-width: 100px;
}
.quality-score.good {
  background: linear-gradient(135deg, #52c41a20, #73d13d20);
  border: 2px solid #52c41a;
}
.quality-score.warning {
  background: linear-gradient(135deg, #faad1420, #ffc53d20);
  border: 2px solid #faad14;
}
.quality-score.bad {
  background: linear-gradient(135deg, #ff4d4f20, #ff787520);
  border: 2px solid #ff4d4f;
}
.score-value {
  font-size: 32px;
  font-weight: bold;
  line-height: 1;
}
.quality-score.good .score-value { color: #52c41a; }
.quality-score.warning .score-value { color: #faad14; }
.quality-score.bad .score-value { color: #ff4d4f; }
.score-label {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}
.quality-stats {
  display: flex;
  gap: 24px;
}
.stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.stat-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.stat-dot.green { background: #52c41a; }
.stat-dot.gray { background: #d9d9d9; }
.stat-label {
  font-size: 13px;
  color: #666;
}
.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}
.missing-list {
  margin: 8px 0;
  padding-left: 20px;
}
.missing-list li {
  font-size: 13px;
  color: #666;
  margin-bottom: 4px;
}
.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
}
.text-content {
  padding: 10px 0;
}
.analysis-title {
  display: flex;
  align-items: center;
  gap: 12px;
}
.analysis-title h2 {
  margin: 0;
  color: #2c3e50;
}

/* SWOT Preview */
.swot-preview {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
.swot-section {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
}
.swot-section h3 {
  margin: 0 0 10px;
  font-size: 16px;
}
.swot-section ul {
  margin: 0;
  padding-left: 20px;
}
.swot-section li {
  margin-bottom: 4px;
  color: #555;
}
.swot-section.strengths {
  border-left: 3px solid #27ae60;
}
.swot-section.weaknesses {
  border-left: 3px solid #e74c3c;
}
.swot-section.opportunities {
  border-left: 3px solid #3498db;
}
.swot-section.threats {
  border-left: 3px solid #f39c12;
}
.swot-section.empty {
  opacity: 0.4;
  border-style: dashed !important;
}
.empty-hint {
  display: block;
  text-align: center;
  color: #999;
  font-size: 13px;
  font-style: italic;
  padding: 12px 0;
}

/* Canvas Preview */
.canvas-preview {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.canvas-row {
  display: flex;
  gap: 10px;
}
.canvas-cell {
  flex: 1;
  background: #f8f9fa;
  border-radius: 8px;
  padding: 12px;
}
.canvas-cell.highlight {
  background: #e8f4fd;
  border: 2px solid #3498db;
}
.canvas-cell h4 {
  margin: 0 0 8px;
  font-size: 14px;
  color: #2c3e50;
}
.canvas-cell ul {
  margin: 0;
  padding-left: 16px;
}
.canvas-cell li {
  font-size: 12px;
  color: #555;
  margin-bottom: 2px;
}

/* PESTEL Preview */
.pestel-preview {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.pestel-item {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 14px;
}
.pestel-item h4 {
  margin: 0 0 8px;
  font-size: 14px;
}
.pestel-item ul {
  margin: 0;
  padding-left: 16px;
}
.pestel-item li {
  font-size: 12px;
  color: #555;
  margin-bottom: 2px;
}

/* Time Matrix Preview */
.time-preview {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
.time-quadrant {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
}
.time-quadrant h4 {
  margin: 0 0 10px;
  font-size: 14px;
}
.time-quadrant ul {
  margin: 0;
  padding-left: 16px;
}
.time-quadrant li {
  font-size: 13px;
  color: #555;
  margin-bottom: 4px;
}
.time-quadrant.q1 {
  border-left: 3px solid #ef4444;
}
.time-quadrant.q2 {
  border-left: 3px solid #27ae60;
}
.time-quadrant.q3 {
  border-left: 3px solid #f59e0b;
}
.time-quadrant.q4 {
  border-left: 3px solid #9ca3af;
}

/* Journey Preview */
.journey-preview .persona-info {
  background: #e8f4fd;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
}
.stage-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.stage-item {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 14px;
}
.stage-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.stage-num {
  width: 28px;
  height: 28px;
  background: #3498db;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: bold;
}
.stage-name {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
}
.stage-emotion {
  margin-left: auto;
}
.stage-item p {
  margin: 0 0 8px;
  color: #666;
  font-size: 13px;
}
.stage-detail {
  font-size: 12px;
  color: #666;
  padding: 6px 10px;
  background: #f0f0f0;
  border-radius: 4px;
  margin-top: 6px;
}
.stage-detail.pain {
  background: #fef2f2;
  color: #991b1b;
}

/* Claim Preview */
.claim-preview .central-claim {
  background: #e8f4fd;
  padding: 20px;
  border-radius: 8px;
  text-align: center;
  margin-bottom: 20px;
}
.claim-preview .central-claim h3 {
  margin: 0 0 10px;
  color: #2c3e50;
}
.claim-preview .central-claim p {
  font-size: 18px;
  color: #3498db;
  margin: 0;
}
.claim-preview .supporting-points h3,
.claim-preview .conclusion h3 {
  color: #2c3e50;
}
.point-item {
  background: #f8f9fa;
  padding: 14px;
  border-radius: 8px;
  margin-bottom: 10px;
  border-left: 3px solid #3498db;
}
.point-item strong {
  display: block;
  margin-bottom: 4px;
  color: #2c3e50;
}
.point-item p {
  margin: 0;
  color: #666;
  font-size: 14px;
}
.conclusion {
  background: #f0fff4;
  padding: 16px;
  border-radius: 8px;
  margin-top: 16px;
}

/* Causal Preview */
.causal-preview .root-cause,
.causal-preview .final-effect {
  background: #f8f9fa;
  padding: 14px;
  border-radius: 8px;
  margin-bottom: 12px;
}
.causal-preview .root-cause {
  border-left: 3px solid #e74c3c;
}
.causal-preview .final-effect {
  border-left: 3px solid #27ae60;
}
.chain-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.chain-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 8px;
}
.chain-step {
  background: #3498db;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}
.chain-arrow {
  color: #999;
}
.chain-cause,
.chain-effect {
  color: #555;
  font-size: 14px;
}

/* System Preview */
.system-preview .system-overview {
  background: #e8f4fd;
  padding: 14px;
  border-radius: 8px;
  margin-bottom: 16px;
}
.module-list {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.module-item {
  background: #f8f9fa;
  padding: 14px;
  border-radius: 8px;
  border-top: 3px solid #3498db;
}
.module-item h4 {
  margin: 0 0 8px;
  color: #2c3e50;
}
.module-item p {
  margin: 4px 0;
  font-size: 13px;
  color: #666;
}

/* Comparison Preview */
.comparison-table {
  width: 100%;
  border-collapse: collapse;
}
.comparison-table th,
.comparison-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #eee;
}
.comparison-table th {
  background: #f5f7fa;
  font-weight: 600;
  color: #2c3e50;
}
.dimension {
  font-weight: 600;
  color: #3498db;
}

/* Process Preview */
.process-preview {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.step-item {
  display: flex;
  flex-direction: column;
  background: #f8f9fa;
  border-radius: 8px;
  padding: 14px;
}
.step-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.step-num {
  width: 28px;
  height: 28px;
  background: #3498db;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: bold;
}
.step-item h4 {
  margin: 0;
  color: #2c3e50;
}
.step-item p {
  margin: 0 0 8px;
  color: #666;
  font-size: 14px;
}
.step-tips {
  font-size: 12px;
  color: #666;
  padding: 6px 10px;
  background: #fffbe6;
  border-radius: 4px;
}

/* Summary */
.summary-section h3 {
  color: #2c3e50;
}
.summary-section p {
  color: #666;
  line-height: 1.8;
  font-size: 14px;
}

.submit-btn {
  height: 48px;
  font-size: 16px;
}
</style>
