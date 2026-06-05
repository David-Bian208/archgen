<template>
  <div class="framework-select-view">
    <a-page-header title="选择分析框架" @back="$router.push('/')">
      <template #extra>
        <a-steps :current="3" :max="5" style="width: 300px">
          <a-step>检索</a-step>
          <a-step>方向</a-step>
          <a-step>内容</a-step>
          <a-step>框架</a-step>
          <a-step>表单</a-step>
        </a-steps>
      </template>
    </a-page-header>

    <a-card class="category-card" v-if="appStore.categoryConfidence > 0">
      <template #title>
        <div class="category-title">
          <icon-tag />
          <span>识别到的业务领域：</span>
          <a-tag color="blue">{{ getCategoryName(appStore.category) }}</a-tag>
          <span class="confidence">置信度: {{ (appStore.categoryConfidence * 100).toFixed(0) }}%</span>
        </div>
      </template>
    </a-card>

    <a-card>
      <template #title>
        <div class="card-title">
          <icon-apps />
          <span>推荐框架 (Top 10)</span>
        </div>
      </template>

      <a-spin :loading="loading">
        <a-list :data="appStore.frameworkList" class="framework-list">
          <template #item="{ item, index }">
            <a-list-item
              class="framework-item"
              :class="{ selected: selectedKey === item.key }"
              @click="selectFramework(item)"
            >
              <div class="framework-content">
                <div class="framework-header">
                  <div class="rank">{{ index + 1 }}</div>
                  <h3>{{ item.name }}</h3>
                  <a-tag color="green" class="score-tag">
                    匹配度: {{ (item.score * 100).toFixed(0) }}%
                  </a-tag>
                </div>
                <p class="framework-desc">{{ item.description }}</p>

                <!-- 完整简介 -->
                <div class="full-desc" v-if="item.full_description">
                  {{ item.full_description }}
                </div>

                <!-- 适用关键词标签 -->
                <div class="applicable-tags" v-if="item.keywords && item.keywords.length > 0">
                  <span class="tag-label">适用：</span>
                  <a-tag v-for="(kw, i) in item.keywords.slice(0, 6)" :key="i" size="small" color="arcoblue">
                    {{ kw }}
                  </a-tag>
                  <span v-if="item.keywords.length > 6" class="more-tags">+{{ item.keywords.length - 6 }}</span>
                </div>

                <!-- 使用说明和逻辑介绍（可展开） -->
                <div class="framework-guide" v-if="item.usage_guide || item.logic_description">
                  <a-button type="text" size="mini" @click.stop="toggleGuide(item.key)">
                    <icon-down :style="{ transform: expandedKeys.includes(item.key) ? 'rotate(180deg)' : '' }" />
                    使用说明
                  </a-button>
                  <div class="guide-content" v-show="expandedKeys.includes(item.key)">
                    <div class="guide-section">
                      <h4>适用场景</h4>
                      <p>{{ item.usage_guide }}</p>
                    </div>
                    <div class="guide-section">
                      <h4>分析逻辑</h4>
                      <p>{{ item.logic_description }}</p>
                    </div>
                  </div>
                </div>

                <div v-if="item.preflight" class="preflight-section">
                  <div class="preflight-summary">
                    <span class="preflight-label">可填充度</span>
                    <a-progress :percent="item.preflight.fill_rate * 100" size="mini" style="width: 120px" />
                    <span class="preflight-ratio">{{ item.preflight.anchored_count }} 锚 / {{ item.preflight.inferred_count }} 推 / {{ item.preflight.missing_count }} 空</span>
                  </div>
                  <div class="preflight-fields">
                    <a-tag v-for="(fieldInfo, fieldName) in item.preflight.fields" :key="fieldName" :color="getFieldColor(fieldInfo.status)" size="small">
                      {{ getFieldLabel(fieldName, item.key) }} ({{ statusLabel(fieldInfo.status) }})
                    </a-tag>
                  </div>
                </div>

                <div class="framework-meta">
                  <a-tag v-for="cat in item.categories" :key="cat" size="small">
                    {{ getCategoryName(cat) }}
                  </a-tag>
                  <span class="layout-tag">布局: {{ getLayoutName(item.layout_style) }}</span>
                </div>
              </div>
            </a-list-item>
          </template>
        </a-list>

        <!-- 自定义选择按钮 -->
        <div class="custom-selection">
          <a-divider>以上都不合适？</a-divider>
          <a-button type="outline" long @click="showAllFrameworks = true">
            <icon-apps />
            查看所有可用框架（按分类）
          </a-button>
        </div>
      </a-spin>
    </a-card>

    <!-- 所有框架弹窗 -->
    <a-modal
      v-model:visible="showAllFrameworks"
      title="所有可用框架"
      :width="1000"
      :footer="false"
      class="all-frameworks-modal"
    >
      <div class="modal-content">
        <a-input-search
          v-model="searchKeyword"
          placeholder="搜索框架名称或描述..."
          style="margin-bottom: 12px"
        />

        <!-- 分类 Tab 标签 -->
        <div class="category-tabs">
          <div
            class="tab-item"
            :class="{ active: activeCategory === 'all' }"
            @click="activeCategory = 'all'"
          >
            <span class="tab-label">全部</span>
            <span class="tab-count">{{ allFrameworks.length }}</span>
          </div>
          <div
            v-for="catKey in categoryOrder"
            :key="catKey"
            class="tab-item"
            :class="{ active: activeCategory === catKey }"
            @click="activeCategory = catKey"
          >
            <span class="tab-label">{{ getCategoryName(catKey) }}</span>
            <span class="tab-count">{{ getCategoryCount(catKey) }}</span>
          </div>
        </div>

        <!-- 显示当前分类下的框架 -->
        <div class="frameworks-grid">
          <div
            v-for="fw in filteredByCategory"
            :key="fw.key"
            class="framework-card"
            :class="{ selected: selectedKey === fw.key }"
            @click="selectFrameworkFromModal(fw)"
          >
            <div class="card-header">
              <h4>{{ fw.name }}</h4>
              <a-tag v-if="fw.score !== undefined" :color="getScoreColor(fw.score)" class="score-badge">
                {{ (fw.score * 100).toFixed(0) }}%
              </a-tag>
            </div>
            <p class="card-desc">{{ fw.description }}</p>

            <!-- 使用说明 -->
            <div class="card-guide" v-if="fw.usage_guide">
              <span class="guide-label">适用：</span>
              <span class="guide-text">{{ fw.usage_guide.slice(0, 80) }}...</span>
            </div>

            <!-- 字段预检信息 -->
            <div v-if="fw.preflight" class="card-preflight">
              <div class="preflight-bar">
                <span class="preflight-label">可填充度</span>
                <a-progress :percent="fw.preflight.fill_rate * 100" size="mini" style="width: 80px" />
                <span class="preflight-ratio">{{ fw.preflight.anchored_count }} 锚 / {{ fw.preflight.inferred_count }} 推 / {{ fw.preflight.missing_count }} 空</span>
              </div>
              <div class="card-fields">
                <span v-for="(fieldInfo, fieldName) in fw.preflight.fields" :key="fieldName" class="field-tag" :class="fieldInfo.status">
                  {{ getFieldLabel(fieldName, fw.key) }}
                  <span class="field-status">{{ statusLabel(fieldInfo.status) }}</span>
                </span>
              </div>
            </div>

            <div class="card-footer">
              <a-tag v-for="cat in fw.categories" :key="cat" size="mini">
                {{ getCategoryName(cat) }}
              </a-tag>
              <span class="layout-tag">布局: {{ getLayoutName(fw.layout_style) }}</span>
            </div>
          </div>
        </div>
      </div>
    </a-modal>

    <a-button
      type="primary"
      size="large"
      long
      :disabled="!selectedKey"
      @click="handleNext"
      class="submit-btn"
    >
      <icon-arrow-right />
      下一步：填写数据
    </a-button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { IconTag, IconApps, IconArrowRight, IconDown } from '@arco-design/web-vue/es/icon'
import { useAppStore } from '../stores/app'
import { matchFrameworks, getAllFrameworks } from '../utils/api'

const appStore = useAppStore()
const router = useRouter()
const loading = ref(false)
const selectedKey = ref(null)

// 框架使用说明展开状态
const expandedKeys = ref([])

// 所有框架弹窗
const showAllFrameworks = ref(false)
const allFrameworks = ref([])
const searchKeyword = ref('')
const activeCategory = ref('all')

const categoryOrder = ['business', 'finance', 'product', 'operations', 'personal', 'risk', 'project']

// 按分类筛选的框架
const filteredByCategory = computed(() => {
  let frameworks = allFrameworks.value
  
  // 搜索过滤
  if (searchKeyword.value) {
    const kw = searchKeyword.value.toLowerCase()
    frameworks = frameworks.filter(fw =>
      fw.name.toLowerCase().includes(kw) ||
      (fw.description && fw.description.toLowerCase().includes(kw)) ||
      (fw.usage_guide && fw.usage_guide.toLowerCase().includes(kw))
    )
  }
  
  // 分类过滤
  if (activeCategory.value !== 'all') {
    frameworks = frameworks.filter(fw => fw.categories.includes(activeCategory.value))
  }
  
  // 按匹配度排序
  return [...frameworks].sort((a, b) => (b.score || 0) - (a.score || 0))
})

const getCategoryCount = (catKey) => {
  return allFrameworks.value.filter(fw => fw.categories.includes(catKey)).length
}

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

const fieldLabels = {
  swot: {
    strengths: '优势',
    weaknesses: '劣势',
    opportunities: '机会',
    threats: '威胁',
    summary: '总结',
  },
  business_canvas: {
    customer_segments: '客户细分',
    value_propositions: '价值主张',
    channels: '渠道',
    customer_relationships: '客户关系',
    revenue_streams: '收入来源',
    key_resources: '核心资源',
    key_activities: '关键业务',
    key_partnerships: '合作伙伴',
    cost_structure: '成本结构',
  },
  pestel: {
    political: '政治',
    economic: '经济',
    social: '社会',
    technological: '技术',
    environmental: '环境',
    legal: '法律',
    summary: '总结',
  },
  time_matrix: {
    q1_important_urgent: '重要紧急',
    q2_important_not_urgent: '重要不紧急',
    q3_not_important_urgent: '不重要紧急',
    q4_not_important_not_urgent: '不重要不紧急',
    summary: '总结',
  },
  claim: {
    central_claim: '核心主张',
    supporting_points: '分论点',
    evidence: '证据',
    conclusion: '结论',
  },
  causal: {
    chain: '因果链',
    root_cause: '根本原因',
    final_effect: '最终结果',
  },
  system: {
    overview: '概述',
    modules: '模块',
  },
  comparison: {
    dimensions: '维度',
    items: '对比项',
  },
  process: {
    steps: '步骤',
  },
  user_journey: {
    persona: '用户角色',
    stages: '阶段',
    summary: '总结',
  },
}

const getCategoryName = (key) => categoryNames[key] || key
const getLayoutName = (key) => layoutNames[key] || key

const getFieldLabel = (fieldName, frameworkKey) => {
  const labels = fieldLabels[frameworkKey]
  return labels?.[fieldName] || fieldName
}

const getFieldColor = (status) => {
  if (status === 'anchored') return 'green'
  if (status === 'inferred') return 'orange'
  return 'gray'
}

const statusLabel = (status) => {
  if (status === 'anchored') return '锚'
  if (status === 'inferred') return '推'
  return '空'
}

const getScoreColor = (score) => {
  if (score >= 0.6) return 'green'
  if (score >= 0.3) return 'orange'
  return 'gray'
}

onMounted(async () => {
  loading.value = true
  try {
    const result = await matchFrameworks(
      appStore.inputText,
      appStore.categoryConfidence >= 0.7 ? appStore.category : null,
      10,
      appStore.mcpResult?.summary || ''
    )
    if (result.data.code === 0) {
      appStore.frameworkList = result.data.data
    }
  } catch (error) {
    Message.error('框架匹配失败: ' + error.message)
  } finally {
    loading.value = false
  }

  // 加载所有框架
  try {
    const result = await getAllFrameworks(
      appStore.inputText,
      appStore.mcpResult?.summary || ''
    )
    if (result.data.code === 0) {
      allFrameworks.value = result.data.data
    }
  } catch (error) {
    console.error('加载所有框架失败:', error)
  }
})

const toggleGuide = (key) => {
  const idx = expandedKeys.value.indexOf(key)
  if (idx > -1) {
    expandedKeys.value.splice(idx, 1)
  } else {
    expandedKeys.value.push(key)
  }
}

const selectFrameworkFromModal = (fw) => {
  selectedKey.value = fw.key
  appStore.selectedFramework = {
    key: fw.key,
    name: fw.name,
    description: fw.description,
    layout_style: fw.layout_style,
    categories: fw.categories,
    score: fw.score || 1,
    preflight: fw.preflight,
  }
  showAllFrameworks.value = false
  Message.success(`已选择：${fw.name}`)
}

const selectFramework = (item) => {
  selectedKey.value = item.key
  appStore.selectedFramework = item
}

const handleNext = () => {
  if (!selectedKey.value) {
    Message.warning('请先选择一个框架')
    return
  }
  router.push('/structured-form')
}
</script>

<style scoped>
.framework-select-view {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
}
.category-card {
  margin-bottom: 20px;
}
.category-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
.confidence {
  color: #666;
  font-size: 13px;
  margin-left: 8px;
}
.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
}
.framework-list {
  margin-top: 10px;
}
.framework-item {
  padding: 16px;
  border-radius: 8px;
  border: 2px solid #f0f0f0;
  margin-bottom: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.framework-item:hover {
  border-color: #3498db;
  background: #f8f9fa;
}
.framework-item.selected {
  border-color: #3498db;
  background: #e8f4fd;
}
.framework-header {
  display: flex;
  align-items: center;
  gap: 12px;
}
.rank {
  width: 30px;
  height: 30px;
  background: linear-gradient(135deg, #3498db 0%, #2c3e50 100%);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
}
.framework-header h3 {
  margin: 0;
  font-size: 18px;
}
.score-tag {
  margin-left: auto;
}
.framework-desc {
  color: #666;
  margin: 8px 0;
  font-size: 14px;
}
/* 完整简介 */
.full-desc {
  color: #444;
  font-size: 13px;
  line-height: 1.7;
  margin: 8px 0;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 6px;
  border-left: 3px solid #3498db;
}
/* 适用关键词标签 */
.applicable-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  margin: 8px 0;
}
.tag-label {
  font-size: 13px;
  color: #666;
  font-weight: 600;
  margin-right: 4px;
}
.more-tags {
  font-size: 12px;
  color: #999;
}
/* 框架使用说明 */
.framework-guide {
  margin: 8px 0;
}
.framework-guide .arco-btn-text {
  color: #3498db;
  font-size: 13px;
  padding: 4px 8px;
}
.guide-content {
  padding: 12px;
  background: #f0f7ff;
  border-radius: 6px;
  border-left: 3px solid #3498db;
  margin-top: 8px;
}
.guide-section {
  margin-bottom: 8px;
}
.guide-section:last-child {
  margin-bottom: 0;
}
.guide-section h4 {
  margin: 0 0 4px 0;
  font-size: 13px;
  color: #2c3e50;
}
.guide-section p {
  margin: 0;
  font-size: 13px;
  color: #555;
  line-height: 1.6;
}
/* 自定义选择 */
.custom-selection {
  margin-top: 20px;
}
/* 所有框架弹窗 */
.all-frameworks-modal :deep(.arco-modal) {
  max-height: 90vh;
}
.modal-content {
  max-height: 70vh;
  overflow-y: auto;
}
/* 分类 Tab 标签 */
.category-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 2px solid #f0f0f0;
}
.tab-item {
  padding: 6px 16px;
  border-radius: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  background: #f5f5f5;
  color: #666;
  font-size: 14px;
  transition: all 0.2s;
  user-select: none;
}
.tab-item:hover {
  background: #e8f4fd;
  color: #3498db;
}
.tab-item.active {
  background: #3498db;
  color: white;
}
.tab-count {
  font-size: 12px;
  background: rgba(255,255,255,0.3);
  padding: 1px 6px;
  border-radius: 10px;
}
.tab-item:not(.active) .tab-count {
  background: rgba(0,0,0,0.08);
}
/* 框架卡片网格 */
.frameworks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
}
/* 框架卡片 */
.framework-card {
  padding: 16px;
  border: 2px solid #f0f0f0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}
.framework-card:hover {
  border-color: #3498db;
  background: #f8f9fa;
}
.framework-card.selected {
  border-color: #3498db;
  background: #e8f4fd;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.card-header h4 {
  margin: 0;
  font-size: 16px;
  color: #2c3e50;
}
.score-badge {
  margin-left: auto;
}
.card-desc {
  color: #666;
  margin: 0 0 8px 0;
  font-size: 13px;
}
.card-guide {
  margin-bottom: 8px;
  font-size: 12px;
  color: #888;
  line-height: 1.5;
}
.guide-label {
  color: #999;
}
.guide-text {
  color: #555;
}
/* 卡片内预检信息 */
.card-preflight {
  margin: 8px 0;
  padding: 8px;
  background: #fafafa;
  border-radius: 6px;
}
.preflight-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.preflight-label {
  font-size: 12px;
  font-weight: 600;
  color: #333;
}
.preflight-ratio {
  font-size: 11px;
  color: #999;
}
.card-fields {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.field-tag {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  background: #f0f0f0;
  color: #666;
}
.field-tag.anchored {
  background: #e8f5e9;
  color: #2e7d32;
}
.field-tag.inferred {
  background: #fff3e0;
  color: #e65100;
}
.field-tag.missing {
  background: #f5f5f5;
  color: #999;
}
.field-status {
  margin-left: 2px;
  font-weight: bold;
}
.card-footer {
  display: flex;
  gap: 6px;
  align-items: center;
}
.card-footer .layout-tag {
  margin-left: auto;
  color: #666;
  font-size: 12px;
}
/* 预检区域 */
.preflight-section {
  margin: 10px 0;
  padding: 10px;
  background: #fafafa;
  border-radius: 6px;
}
.preflight-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.preflight-label {
  font-size: 13px;
  font-weight: 600;
  color: #333;
}
.preflight-ratio {
  font-size: 12px;
  color: #999;
}
.preflight-fields {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.framework-meta {
  display: flex;
  gap: 8px;
  align-items: center;
}
.layout-tag {
  margin-left: auto;
  color: #666;
  font-size: 12px;
}
.submit-btn {
  margin-top: 20px;
  height: 48px;
  font-size: 16px;
}
</style>
