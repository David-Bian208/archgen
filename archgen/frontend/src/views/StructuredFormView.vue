<template>
  <div class="structured-form-view">
    <a-page-header title="填写分析数据" @back="$router.push('/frameworks')">
      <template #extra>
        <a-steps :current="4" :max="5" style="width: 300px">
          <a-step>检索</a-step>
          <a-step>方向</a-step>
          <a-step>内容</a-step>
          <a-step>框架</a-step>
          <a-step>表单</a-step>
        </a-steps>
      </template>
    </a-page-header>

    <!-- 框架信息卡片 -->
    <a-card class="framework-info">
      <template #title>
        <div class="info-title">
          <icon-apps />
          <span>{{ appStore.selectedFramework?.name }}</span>
          <a-tag color="blue">{{ getLayoutName(appStore.selectedFramework?.layout_style) }}</a-tag>
          <span class="fill-rate-badge" v-if="autopopResult">
            已填充 {{ autopopResult.anchored_count }} 锚 / {{ autopopResult.inferred_count }} 推 / {{ autopopResult.missing_count }} 空
          </span>
        </div>
      </template>
      <template #extra>
        <a-space>
          <a-button size="small" @click="handleRefresh" :loading="refreshing">
            <icon-refresh /> 重新萃取
          </a-button>
        </a-space>
      </template>
    </a-card>

    <!-- 结构化表单 -->
    <a-card>
      <template #title>
        <div class="card-title">
          <icon-edit />
          <span>填写表单数据</span>
        </div>
      </template>

      <a-spin :loading="refreshing">
        <a-form :model="formData" layout="vertical" class="data-form">
          <div v-for="field in fields" :key="field.key" class="form-field">
            <div class="field-header">
              <span class="field-label">{{ field.label }}</span>
              <a-button type="text" size="mini" @click="handleAiGenerate(field.key, field)" :loading="generatingFields[field.key]">
                <icon-robot /> AI 帮我写
              </a-button>
            </div>
            <div class="field-status-row">
              <span class="field-status-badge" v-if="fieldStatus[field.key]" :class="fieldStatus[field.key].status">
                <span v-if="fieldStatus[field.key].status === 'anchored'"> 原文锚点 · 从你的资料中提取</span>
                <span v-else-if="fieldStatus[field.key].status === 'inferred'"> 推测 · AI 根据上下文推理，请确认</span>
                <span v-else> 缺失 · 原文未提及，可手动补充</span>
              </span>
              <span class="field-suggestion" v-if="fieldStatus[field.key]?.suggestion">
                {{ fieldStatus[field.key].suggestion }}
              </span>
            </div>
            <a-textarea
              v-if="field.type === 'array'"
              v-model="formData[field.key]"
              :class="['data-textarea', `status-${fieldStatus[field.key]?.status || ''}`]"
              :auto-size="{ minRows: 2, maxRows: 6 }"
              :placeholder="getPlaceholder(field, fieldStatus[field.key])"
            />
            <a-input
              v-else
              v-model="formData[field.key]"
              :class="['data-input', `status-${fieldStatus[field.key]?.status || ''}`]"
              :placeholder="getPlaceholder(field, fieldStatus[field.key])"
            />
          </div>
        </a-form>
      </a-spin>

      <!-- 完整度检查 -->
      <div v-if="completenessResult" class="completeness-section">
        <a-divider />
        <a-alert v-if="completenessResult.complete" type="success" :show-icon="false">
          <template #title>数据完整度: {{ (completenessResult.completeness_score * 100).toFixed(0) }}%</template>
          <div>✅ 所有必填字段已填写，可以生成</div>
        </a-alert>
        <a-alert v-else type="info" :show-icon="false">
          <template #title>数据完整度: {{ (completenessResult.completeness_score * 100).toFixed(0) }}%</template>
          <div>
            部分字段为空，但仍可生成（空白处将显示"待补充"）
            <div class="follow-up-questions" v-if="completenessResult.follow_up_questions?.length > 0">
              <div v-for="(q, i) in completenessResult.follow_up_questions" :key="i" class="question">
                {{ q }}
              </div>
            </div>
          </div>
        </a-alert>
      </div>
    </a-card>

    <!-- 操作按钮 -->
    <a-space direction="vertical" style="width: 100%">
      <a-button
        type="primary"
        size="large"
        long
        :loading="loading"
        @click="handlePreview"
        class="submit-btn"
      >
        <icon-eye />
        预览文字分析
      </a-button>
      <a-typography-text type="secondary" style="text-align: center; display: block; font-size: 12px">
        只需至少 1 个字段有内容即可生成，空白字段会自动处理
      </a-typography-text>
    </a-space>
  </div>
</template>

<script setup>
import { ref, computed, reactive, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { IconApps, IconEdit, IconEye, IconRefresh, IconRobot } from '@arco-design/web-vue/es/icon'
import { useAppStore } from '../stores/app'
import { getDataCheck, autopopulateData, aiGenerateField } from '../utils/api'

const appStore = useAppStore()
const router = useRouter()
const loading = ref(false)
const refreshing = ref(false)
const completenessResult = ref(null)
const autopopResult = ref(null)
const fieldStatus = reactive({})
const generatingFields = reactive({})

const formData = reactive({})

const frameworkKey = computed(() => appStore.selectedFramework?.key)

const fields = computed(() => {
  const fieldConfigs = {
    swot: [
      { key: 'title', label: '分析标题', type: 'text', required: true, placeholder: '例如：腾讯 SWOT 分析' },
      { key: 'strengths', label: '优势 (Strengths)', type: 'array', required: true, placeholder: '技术领先\n用户基数大\n生态完善' },
      { key: 'weaknesses', label: '劣势 (Weaknesses)', type: 'array', required: true, placeholder: '创新速度放缓\n海外业务受阻' },
      { key: 'opportunities', label: '机会 (Opportunities)', type: 'array', required: true, placeholder: 'AI 技术发展\n产业互联网' },
      { key: 'threats', label: '威胁 (Threats)', type: 'array', required: true, placeholder: '监管趋严\n竞争加剧' },
      { key: 'summary', label: '总结建议', type: 'text', required: false, placeholder: '综合总结和建议...' },
    ],
    business_canvas: [
      { key: 'title', label: '分析标题', type: 'text', required: true, placeholder: '例如：某公司商业模式画布' },
      { key: 'customer_segments', label: '客户细分', type: 'array', required: true, placeholder: '企业客户\n个人消费者' },
      { key: 'value_propositions', label: '价值主张', type: 'array', required: true, placeholder: '降本增效\n提升体验' },
      { key: 'channels', label: '渠道通路', type: 'array', required: false, placeholder: '线上渠道\n线下门店' },
      { key: 'customer_relationships', label: '客户关系', type: 'array', required: false, placeholder: '专属客服\n自助服务' },
      { key: 'revenue_streams', label: '收入来源', type: 'array', required: true, placeholder: '订阅费\n广告收入' },
      { key: 'key_resources', label: '核心资源', type: 'array', required: false, placeholder: '技术团队\n品牌' },
      { key: 'key_activities', label: '关键业务', type: 'array', required: false, placeholder: '产品研发\n市场推广' },
      { key: 'key_partnerships', label: '合作伙伴', type: 'array', required: false, placeholder: '供应商\n渠道商' },
      { key: 'cost_structure', label: '成本结构', type: 'array', required: false, placeholder: '研发成本\n运营成本' },
    ],
    pestel: [
      { key: 'title', label: '分析标题', type: 'text', required: true, placeholder: '例如：新能源汽车行业 PESTEL 分析' },
      { key: 'political', label: '政治因素', type: 'array', required: true, placeholder: '政策支持\n补贴政策' },
      { key: 'economic', label: '经济因素', type: 'array', required: true, placeholder: '消费升级\n融资环境' },
      { key: 'social', label: '社会因素', type: 'array', required: true, placeholder: '环保意识增强' },
      { key: 'technological', label: '技术因素', type: 'array', required: true, placeholder: '电池技术进步' },
      { key: 'environmental', label: '环境因素', type: 'array', required: true, placeholder: '碳排放要求' },
      { key: 'legal', label: '法律因素', type: 'array', required: true, placeholder: '安全法规' },
      { key: 'summary', label: '总结建议', type: 'text', required: false, placeholder: '综合总结...' },
    ],
    user_journey: [
      { key: 'title', label: '分析标题', type: 'text', required: true, placeholder: '例如：电商购物用户旅程' },
      { key: 'persona', label: '用户角色', type: 'text', required: true, placeholder: '25-35岁，一二线城市白领' },
      { key: 'stages', label: '旅程阶段 (JSON 格式)', type: 'text', required: true, placeholder: '[{"order": 1, "name": "认知", "description": "看到广告"}]' },
      { key: 'summary', label: '总结建议', type: 'text', required: false, placeholder: '综合总结...' },
    ],
    time_matrix: [
      { key: 'title', label: '分析标题', type: 'text', required: true, placeholder: '例如：本周时间管理矩阵' },
      { key: 'q1_important_urgent', label: 'Q1 重要且紧急（立即做）', type: 'text', required: true, placeholder: '[{"name": "紧急项目", "description": "今天必须交付"}]' },
      { key: 'q2_important_not_urgent', label: 'Q2 重要不紧急（计划做）', type: 'text', required: true, placeholder: '[{"name": "学习新技能", "description": "本月计划"}]' },
      { key: 'q3_not_important_urgent', label: 'Q3 不重要但紧急（委派做）', type: 'text', required: false, placeholder: '[{"name": "回复邮件", "description": "可以委托助理"}]' },
      { key: 'q4_not_important_not_urgent', label: 'Q4 不重要不紧急（减少做）', type: 'text', required: false, placeholder: '[{"name": "刷社交媒体", "description": "控制时间"}]' },
      { key: 'summary', label: '总结建议', type: 'text', required: false, placeholder: '综合总结...' },
    ],
    claim: [
      { key: 'title', label: '标题', type: 'text', required: true, placeholder: '文章标题' },
      { key: 'central_claim', label: '核心主张', type: 'text', required: true, placeholder: '一句话核心观点' },
      { key: 'supporting_points', label: '分论点 (JSON)', type: 'text', required: true, placeholder: '[{"label": "分论点1", "text": "内容", "weight": 0.9}]' },
      { key: 'conclusion', label: '结论', type: 'text', required: true, placeholder: '总结性结论' },
    ],
    causal: [
      { key: 'title', label: '标题', type: 'text', required: true, placeholder: '分析标题' },
      { key: 'chain', label: '因果链条 (JSON)', type: 'text', required: true, placeholder: '[{"step": 1, "cause": "原因", "effect": "结果"}]' },
      { key: 'root_cause', label: '根本原因', type: 'text', required: true, placeholder: '最根本的原因' },
      { key: 'final_effect', label: '最终结果', type: 'text', required: true, placeholder: '最终导致的结果' },
    ],
    system: [
      { key: 'title', label: '标题', type: 'text', required: true, placeholder: '系统名称' },
      { key: 'overview', label: '系统概述', type: 'text', required: true, placeholder: '一句话概述' },
      { key: 'modules', label: '模块列表 (JSON)', type: 'text', required: true, placeholder: '[{"name": "模块", "role": "职责", "connections": []}]' },
    ],
    comparison: [
      { key: 'title', label: '标题', type: 'text', required: true, placeholder: '对比标题' },
      { key: 'dimensions', label: '对比维度 (JSON)', type: 'text', required: true, placeholder: '["性能", "成本", "易用性"]' },
      { key: 'items', label: '对比项 (JSON)', type: 'text', required: true, placeholder: '[{"name": "A", "scores": ["高", "低", "中"]}]' },
    ],
    process: [
      { key: 'title', label: '标题', type: 'text', required: true, placeholder: '流程标题' },
      { key: 'steps', label: '步骤列表 (JSON)', type: 'text', required: true, placeholder: '[{"order": 1, "title": "步骤1", "description": "描述"}]' },
    ],
  }

  return fieldConfigs[frameworkKey.value] || []
})

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

const getLayoutName = (key) => layoutNames[key] || key

const formatFieldValue = (value, fieldDef) => {
  if (!value) return ''
  if (fieldDef?.type === 'text' && fieldDef.placeholder?.includes('JSON')) {
    try {
      return JSON.stringify(value, null, 2)
    } catch {
      return String(value)
    }
  }
  if (Array.isArray(value)) {
    return value.map(item => {
      if (typeof item === 'object' && item !== null) {
        return JSON.stringify(item)
      }
      return String(item)
    }).join('\n')
  }
  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2)
  }
  return String(value)
}

const getPlaceholder = (field, status) => {
  if (!status) return field.placeholder
  if (status.status === 'anchored') return '✅ 已从原文提取，可编辑'
  if (status.status === 'inferred') return 'AI 推测，请确认或修改'
  return field.placeholder || '暂无数据，可手动输入'
}

const runAutopopulate = async () => {
  if (!frameworkKey.value) return

  const sourceText = appStore.inputText || appStore.mcpResult?.summary
  if (!sourceText) return

  refreshing.value = true
  try {
    const result = await autopopulateData(sourceText, frameworkKey.value)
    if (result.data.code === 0) {
      autopopResult.value = result.data.data
      const fwData = result.data.data.fields
      for (const [key, info] of Object.entries(fwData)) {
        const fieldDef = fields.value.find(f => f.key === key)
        if (!fieldDef) continue

        if (info.status === 'anchored') {
          const val = formatFieldValue(info.value, fieldDef)
          formData[key] = val
          fieldStatus[key] = { status: 'anchored', suggestion: info.suggestion }
        } else if (info.status === 'inferred') {
          const val = formatFieldValue(info.value, fieldDef)
          formData[key] = val
          fieldStatus[key] = { status: 'inferred', suggestion: info.suggestion }
        } else {
          formData[key] = ''
          fieldStatus[key] = { status: 'missing', suggestion: info.suggestion }
        }
      }
      Message.success(`已预填充 ${autopopResult.value.anchored_count} 个锚点字段`)
    } else {
      Message.warning('预填充失败，请手动填写')
    }
  } catch (error) {
    console.error('预填充失败:', error)
    Message.warning('预填充失败，请手动填写')
  } finally {
    refreshing.value = false
  }
}

const handleRefresh = () => {
  runAutopopulate()
}

const handleAiGenerate = async (fieldKey, field) => {
  if (generatingFields[fieldKey]) return

  const sourceText = appStore.inputText || appStore.mcpResult?.summary || ''
  const existingData = { ...formData }
  delete existingData[fieldKey]

  generatingFields[fieldKey] = true
  try {
    const result = await aiGenerateField(
      frameworkKey.value,
      fieldKey,
      field.label,
      existingData,
      sourceText
    )
    if (result.data.code === 0) {
      let content = result.data.data.content
      content = content.replace(/```(?:json)?\s*/g, '').replace(/```/g, '').trim()
      formData[fieldKey] = content
      fieldStatus[fieldKey] = { status: 'inferred', suggestion: 'AI 生成，请确认或修改' }
      Message.success(`${field.label} 已生成，请确认后使用`)
    } else {
      Message.error('AI 生成失败: ' + result.data.msg)
    }
  } catch (error) {
    Message.error('AI 生成失败: ' + error.message)
  } finally {
    generatingFields[fieldKey] = false
  }
}

const parseArrayField = (value) => {
  if (!value) return []
  return value.split('\n').filter(v => v.trim())
}

const checkDataCompleteness = async () => {
  if (!frameworkKey.value) return

  const processedData = { ...formData }
  for (const field of fields.value) {
    if (field.type === 'array') {
      processedData[field.key] = parseArrayField(formData[field.key])
    }
  }

  try {
    const result = await getDataCheck(processedData, frameworkKey.value)
    if (result.data.code === 0) {
      completenessResult.value = result.data.data
    }
  } catch (error) {
    console.error('数据检查失败:', error)
  }
}

watch(formData, () => {
  checkDataCompleteness()
}, { deep: true })

onMounted(() => {
  runAutopopulate()
})

const handlePreview = async () => {
  const hasAnyContent = Object.values(formData).some(v => v && v.trim())
  if (!hasAnyContent) {
    Message.warning('请至少填写一个字段')
    return
  }

  loading.value = true
  try {
    const processedData = { ...formData }
    for (const field of fields.value) {
      if (field.type === 'array') {
        processedData[field.key] = parseArrayField(formData[field.key])
      } else {
        try {
          processedData[field.key] = JSON.parse(formData[field.key])
        } catch {
          // 保持原值
        }
      }
    }

    appStore.formData = processedData
    router.push('/text-preview')
  } catch (error) {
    Message.error('数据解析失败: ' + error.message)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.structured-form-view {
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
.fill-rate-badge {
  font-size: 13px;
  color: #666;
  margin-left: 12px;
}
.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
}
.data-form {
  margin-top: 10px;
}
.form-field {
  margin-bottom: 16px;
}
.field-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.field-label {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}
.field-status-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
}
.field-status-badge {
  margin-right: 8px;
  font-size: 12px;
}
.field-status-badge.anchored {
  color: #52c41a;
}
.field-status-badge.inferred {
  color: #fa8c16;
}
.field-status-badge.missing {
  color: #999;
}
.field-suggestion {
  font-size: 12px;
  color: #999;
}
.data-input.status-anchored,
.data-textarea.status-anchored {
  border-color: #52c41a;
  background: #f6ffed;
}
.data-input.status-inferred,
.data-textarea.status-inferred {
  border-color: #fa8c16;
  background: #fff7e6;
}
.data-input.status-missing,
.data-textarea.status-missing {
  border-style: dashed;
  border-color: #d9d9d9;
}
.completeness-section {
  margin-top: 20px;
}
.follow-up-questions {
  margin-top: 10px;
}
.question {
  padding: 8px 12px;
  background: #fffbe6;
  border-radius: 4px;
  margin-bottom: 6px;
  font-size: 13px;
}
.submit-btn {
  height: 48px;
  font-size: 16px;
}
</style>
