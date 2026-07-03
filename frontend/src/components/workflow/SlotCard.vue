<template>
  <div
    class="slot-card"
    :class="[
      `slot-card--${status}`,
      { 'slot-card--expanded': expanded }
    ]"
  >
    <!-- 卡片头 -->
    <div class="slot-card__header" @click="expanded = !expanded">
      <div class="slot-card__title">
        <span class="slot-card__status-dot" :class="`dot--${status}`"></span>
        <span class="slot-card__name">{{ label }}</span>
        <a-tag v-if="level" :color="levelColor" size="small" class="slot-card__level">
          {{ level }}
        </a-tag>
        <a-tag v-if="maxDegradation > 0" size="small" color="arcoblue">
          重试 {{ degradationCount }}/{{ maxDegradation }}
        </a-tag>
      </div>
      <div class="slot-card__badges">
        <a-tag v-if="sources.length" color="blue" size="small">
          📄 {{ sources.length }} 来源
        </a-tag>
        <a-tag v-if="coverage > 0" :color="coverage >= 0.5 ? 'green' : 'orange'" size="small">
          {{ Math.round(coverage * 100) }}%
        </a-tag>
        <a-tag v-if="status === 'done'" color="green" size="small">已完成</a-tag>
        <a-tag v-else-if="status === 'partial'" color="orange" size="small">缺数据</a-tag>
        <a-tag v-else-if="status === 'l2'" color="orangered" size="small">引导提问</a-tag>
        <a-tag v-else-if="status === 'l3'" color="red" size="small">类比推导</a-tag>
        <a-tag v-else color="gray" size="small">待填充</a-tag>
        <a-tag v-if="confirmed" color="green" size="small">✓</a-tag>
      </div>
    </div>

    <!-- 静默扫描提示条：已有内容 + 建议补充 -->
    <div v-if="gapMatch" class="slot-card__hint-bar">
      <div v-if="gapMatch.hasExisting" class="slot-card__hint-existing">
        ✅ 已有相关内容
      </div>
      <div v-else class="slot-card__hint-no-data">
        信息待分析
      </div>
      <div v-if="gapMatch.gaps.length" class="slot-card__hint-gaps">
        ⚠️ 建议补充：
        <a-tag v-for="(g, i) in gapMatch.gaps.slice(0, 3)" :key="i"
          color="orangered" size="small" style="margin: 0 2px">
          {{ g }}
        </a-tag>
        <span v-if="gapMatch.gaps.length > 3" style="font-size: 11px; color: #86909c">
          +{{ gapMatch.gaps.length - 3 }}
        </span>
      </div>
      <div v-else class="slot-card__hint-no-data" style="color: #00b42a">
        暂无缺失
      </div>
    </div>

    <!-- 双栏布局 -->
    <div v-show="expanded" class="slot-card__dual">
      <!-- ==================== 左栏：来源链 ==================== -->
      <div class="slot-card__left">

        <!-- 来源展示（L0/L1 的 points 带来源标签） -->
        <div v-if="level === 'L0' || level === 'L1'" class="slot-card__sources-chain">
          <div class="slot-card__section-title">✅ 已有内容</div>
          <!-- enriched sources -->
          <div v-if="enrichedSources.length" class="slot-card__enriched-sources">
            <div v-for="(src, i) in enrichedSources" :key="i" class="slot-card__source-item">
              <span class="slot-card__source-tag">{{ src.tag || '📄 来源' }}</span>
              <span :class="`slot-card__conf-dot conf--${confidenceLabel(src.confidence)}`"
                :title="`置信度: ${src.confidence}`">
              </span>
              <span class="slot-card__source-name">{{ src.name }}</span>
            </div>
          </div>
          <!-- points -->
          <div class="slot-card__points">
            <div v-for="(point, i) in (result.points || [])" :key="i" class="slot-card__point">
              <span class="slot-card__point-num">{{ i + 1 }}.</span>
              <span>{{ point }}</span>
            </div>
          </div>
        </div>

        <!-- L2: 引导式提问 -->
        <div v-if="level === 'L2'" class="slot-card__l2">
          <div class="slot-card__l2-intro">
            <icon-question-circle />
            <span>AI 无法直接填此槽位，请先回答以下问题：</span>
          </div>
          <div class="slot-card__l2-questions">
            <div v-for="(q, i) in (result.questions || [])" :key="i" class="slot-card__l2-q">
              <div class="slot-card__l2-q-label">{{ i + 1 }}. {{ q }}</div>
              <a-textarea
                v-model="l2Answers[i]"
                :placeholder="'请输入...'"
                :auto-size="{ minRows: 2, maxRows: 4 }"
                :disabled="filling"
              />
            </div>
          </div>
        </div>

        <!-- L3: 类比推导 -->
        <div v-if="level === 'L3'" class="slot-card__l3">
          <div class="slot-card__l3-analogy">
            <icon-bulb />
            <span>{{ result.analogy || 'AI 通过跨领域类比生成了参考内容' }}</span>
          </div>
          <div v-if="(result.inspirations || []).length" class="slot-card__l3-inspirations">
            <div v-for="(insp, i) in result.inspirations" :key="i" class="slot-card__l3-insp">
              💡 {{ insp }}
            </div>
          </div>
        </div>

        <!-- L4: 空框架 -->
        <div v-if="level === 'L4'" class="slot-card__l4">
          <p class="slot-card__hint">AI 无法自动填充此槽位，建议补充以下维度：</p>
          <div class="slot-card__l4-dims">
            <a-tag v-for="(gap, i) in (result.gaps || ['需要手动补充素材'])" :key="i"
              color="gray" size="small" class="slot-card__gap-tag">
              {{ gap }}
            </a-tag>
          </div>
        </div>

        <!-- 空态：无 AI 分析 -->
        <div v-if="!level || level === 'L4'" class="slot-card__empty">
          <a-empty description="尚未填充此槽位">
            <template #image><icon-file /></template>
          </a-empty>
        </div>

        <!-- 缺口 -->
        <div v-if="(result.gaps || []).length && (level === 'L0' || level === 'L1')" class="slot-card__gaps">
          <div class="slot-card__section-title">⚠️ 缺口</div>
          <div class="slot-card__gaps-list">
            <a-tag v-for="(gap, i) in result.gaps" :key="i" color="orangered" size="small">
              {{ gap }}
            </a-tag>
          </div>
        </div>
      </div>

      <!-- ==================== 右栏：对话补充 ==================== -->
      <div class="slot-card__right">
        <div class="slot-card__right-title">💬 对话补充</div>

        <!-- 文本输入 -->
        <div class="slot-card__input-area">
          <a-textarea
            v-model="localSupp"
            placeholder="告诉我你想补充什么...&#10;例如：目标用户画像、行业规模数据、竞品案例"
            :auto-size="{ minRows: 3, maxRows: 8 }"
            :disabled="filling"
          />
        </div>

        <!-- 上传工具栏 -->
        <div class="slot-card__upload-bar">
          <a-button size="small" @click="handleUploadClick('file')">
            📎 文件
          </a-button>
          <a-button size="small" @click="handleUploadClick('image')">
            🖼 图片
          </a-button>
          <input
            ref="fileInput"
            type="file"
            style="display: none"
            @change="onFileSelected"
            accept=".txt,.md,.pdf,.doc,.docx,.png,.jpg,.jpeg"
          />
        </div>

        <!-- 素材标签 -->
        <div class="slot-card__sources" v-if="confirmedSources.length">
          <a-tag v-for="(src, i) in confirmedSources" :key="i"
            :color="src.type === 'file' ? 'blue' : 'green'"
            size="small" closable @close="removeSource(i)">
            {{ src.type === 'file' ? '📄' : '🔍' }} {{ src.name || src.title }}
          </a-tag>
        </div>

        <!-- 操作按钮 -->
        <div class="slot-card__actions">
          <a-button
            v-if="!level || level === 'L4'"
            type="primary" size="small" :loading="filling"
            @click="handleFill"
          >
            <template #icon><icon-robot /></template>
            AI 分析
          </a-button>

          <a-button
            v-if="level === 'L2' && hasL2Answers"
            type="primary" size="small" :loading="filling"
            @click="handleL2Submit"
          >
            <template #icon><icon-check /></template>
            提交回答
          </a-button>

          <a-button
            v-if="level === 'L3'"
            size="small" :loading="filling"
            @click="handleExpandAnalogy"
          >
            <template #icon><icon-arrow-right /></template>
            按类比展开
          </a-button>

          <a-button
            v-if="(level && level !== 'L4') && degradationCount < maxDegradation"
            size="small" status="warning" @click="handleDegrade"
          >
            <template #icon><icon-refresh /></template>
            重试
          </a-button>

          <a-button
            v-if="level === 'L0' || level === 'L1'" size="small" @click="handleFill"
          >
            <template #icon><icon-robot /></template>
            重分析
          </a-button>

          <a-button size="small" @click="handleSkip">
            {{ level === 'L4' || !level ? '跳过' : '确认(含缺口)' }}
          </a-button>

          <a-button v-if="confirmed" size="small" type="outline" status="success" disabled>
            ✓ 已确认
          </a-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import {
  IconRobot, IconFile, IconQuestionCircle, IconBulb,
  IconRefresh, IconCheck, IconArrowRight,
} from '@arco-design/web-vue/es/icon'
import { Message } from '@arco-design/web-vue'

const props = defineProps({
  slotKey: { type: String, required: true },
  label: { type: String, default: '' },
  result: { type: Object, default: () => ({}) },
  filling: { type: Boolean, default: false },
  confirmedSources: { type: Array, default: () => [] },
  degradationCount: { type: Number, default: 0 },
  maxDegradation: { type: Number, default: 2 },
  confirmed: { type: Boolean, default: false },
  gapMatch: { type: Object, default: null },
})

const emit = defineEmits([
  'fill', 'skip', 'confirm', 'remove-source',
  'degrade', 'l2-submit', 'expand-analogy', 'upload-source',
])

const expanded = ref(false)
const localSupp = ref('')
const l2Answers = ref([])
const fileInput = ref(null)

// 从 result 计算状态
const level = computed(() => props.result?.level || '')
const coverage = computed(() => props.result?.coverage || 0)
const sources = computed(() => props.result?.sources || [])
const enrichedSources = computed(() => {
  // sources 可能是原始 string[] 或已富化的 SourceItem[]
  const raw = props.result?.sources || []
  if (!raw.length) return []
  // 如果已富化（有 type 字段），直接使用
  if (raw[0] && typeof raw[0] === 'object' && raw[0].type) {
    return raw
  }
  // 如果是新版的 enriched_sources
  const enriched = props.result?.enriched_sources
  if (enriched && enriched.length) return enriched
  // 兼容：string[] 转成简单格式
  return raw.map(s => ({
    type: 'knowledge_base',
    name: typeof s === 'string' ? s : '',
    confidence: 1.0,
    tag: typeof s === 'string' ? `📄 ${s}` : '📄 来源',
  }))
})

function confidenceLabel(conf) {
  if (conf >= 0.8) return 'high'
  if (conf >= 0.4) return 'medium'
  return 'low'
}

const status = computed(() => {
  if (level.value === 'L0' || level.value === 'L1') {
    return (props.result?.gaps || []).length > 0 ? 'partial' : 'done'
  }
  if (level.value === 'L2') return 'l2'
  if (level.value === 'L3') return 'l3'
  if (level.value === 'L4') return 'empty'
  return 'empty'
})

const levelColor = computed(() => {
  const map = { L0: 'green', L1: 'arcoblue', L2: 'orangered', L3: 'red', L4: 'gray' }
  return map[level.value] || 'gray'
})

const hasL2Answers = computed(() => {
  const questions = props.result?.questions || []
  if (!questions.length) return false
  return l2Answers.value.some(a => a && a.trim())
})

watch(() => props.result?.supplementInput, (val) => {
  if (val) localSupp.value = val
}, { immediate: true })

watch(() => props.result?.questions, () => {
  l2Answers.value = []
}, { immediate: true })

function handleFill() {
  emit('fill', props.slotKey, localSupp.value, props.confirmedSources)
}

function handleSkip() {
  emit('skip', props.slotKey)
}

function handleDegrade() {
  emit('degrade', props.slotKey, localSupp.value, props.confirmedSources)
}

function handleL2Submit() {
  emit('l2-submit', props.slotKey, l2Answers.value)
}

function handleExpandAnalogy() {
  emit('expand-analogy', props.slotKey)
}

function removeSource(i) {
  emit('remove-source', props.slotKey, i)
}

function handleUploadClick(type) {
  if (type === 'file' || type === 'image') {
    fileInput.value?.click()
  }
}

function onFileSelected(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (evt) => {
    const text = evt.target?.result || ''
    const fileType = file.type.startsWith('image/') ? 'image' : 'text'
    emit('upload-source', props.slotKey, text, file.name, fileType)
  }
  reader.readAsText(file)
  // 重置 input，允许重复选同一个文件
  e.target.value = ''
}
</script>

<style scoped>
.slot-card {
  background: var(--color-bg-2, #fff);
  border: 1px solid var(--color-border-2, #e5e6eb);
  border-radius: 8px;
  margin-bottom: 12px;
  transition: all .2s;
}
.slot-card--done { border-left: 4px solid #00b42a; }
.slot-card--partial { border-left: 4px solid #ff7d00; }
.slot-card--l2 { border-left: 4px solid #ff5722; }
.slot-card--l3 { border-left: 4px solid #f53f3f; }
.slot-card--empty { border-left: 4px solid #c9cdd4; }
.slot-card--expanded { box-shadow: 0 2px 12px rgba(0,0,0,.06); }

.slot-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
}
.slot-card__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 14px;
}
.slot-card__level { font-weight: 400; }
.slot-card__status-dot {
  width: 10px; height: 10px; border-radius: 50%; display: inline-block;
}
.dot--done { background: #00b42a; }
.dot--partial { background: #ff7d00; }
.dot--l2 { background: #ff5722; }
.dot--l3 { background: #f53f3f; }
.dot--empty { background: #c9cdd4; }
.slot-card__badges { display: flex; gap: 6px; }

/* ===== 双栏布局 ===== */
.slot-card__dual {
  display: flex;
  gap: 0;
  border-top: 1px solid var(--color-border-2, #e5e6eb);
}
.slot-card__left {
  flex: 1 1 55%;
  padding: 16px;
  border-right: 1px solid var(--color-border-2, #e5e6eb);
  min-width: 0;
  overflow-y: auto;
  max-height: 500px;
}
.slot-card__right {
  flex: 1 1 45%;
  padding: 16px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.slot-card__right-title {
  font-size: 14px; font-weight: 600; color: var(--color-text-1);
}
.slot-card__input-area { width: 100%; }
.slot-card__upload-bar {
  display: flex; gap: 8px;
}
.slot-card__sources { display: flex; flex-wrap: wrap; gap: 6px; }
.slot-card__actions {
  display: flex; flex-wrap: wrap; gap: 8px;
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid var(--color-border-2, #e5e6eb);
}

/* ===== 左栏内元素 ===== */
.slot-card__section-title {
  font-size: 13px; font-weight: 600;
  color: var(--color-text-2); margin-bottom: 8px;
}
.slot-card__sources-chain { margin-bottom: 12px; }

/* 来源链条目 */
.slot-card__enriched-sources {
  display: flex; flex-direction: column; gap: 6px; margin-bottom: 10px;
}
.slot-card__source-item {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; line-height: 1.5;
}
.slot-card__source-tag {
  background: #f0f5ff; color: #165dff;
  padding: 1px 6px; border-radius: 4px;
  font-size: 11px; white-space: nowrap;
  max-width: 140px; overflow: hidden; text-overflow: ellipsis;
}
.slot-card__source-name {
  color: var(--color-text-3); flex: 1;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
/* 置信度圆点 */
.slot-card__conf-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}
.conf--high { background: #00b42a; }
.conf--medium { background: #ff7d00; }
.conf--low { background: #f53f3f; }

/* Points */
.slot-card__points { margin-bottom: 8px; }
.slot-card__point {
  font-size: 14px; line-height: 1.8; color: var(--color-text-1);
}
.slot-card__point-num { font-weight: 700; margin-right: 4px; color: var(--color-text-3); }

/* Gaps */
.slot-card__gaps { margin-bottom: 8px; }
.slot-card__gaps-list { display: flex; flex-wrap: wrap; gap: 6px; }

/* L2 */
.slot-card__l2 {
  background: #fff7e6; border-radius: 6px; padding: 12px; margin-bottom: 12px;
}
.slot-card__l2-intro {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; color: #ff7d00; margin-bottom: 10px;
}
.slot-card__l2-questions { display: flex; flex-direction: column; gap: 10px; }
.slot-card__l2-q-label {
  font-size: 13px; color: var(--color-text-2); margin-bottom: 4px;
}

/* L3 */
.slot-card__l3 {
  background: #fff2f0; border-radius: 6px; padding: 12px; margin-bottom: 12px;
}
.slot-card__l3-analogy {
  display: flex; align-items: flex-start; gap: 6px;
  font-size: 13px; color: var(--color-text-1); margin-bottom: 8px;
}
.slot-card__l3-inspirations { display: flex; flex-direction: column; gap: 4px; }
.slot-card__l3-insp { font-size: 12px; color: var(--color-text-3); }

/* L4 */
.slot-card__l4 {
  background: #f7f8fa; border-radius: 6px; padding: 12px; margin-bottom: 12px;
}
.slot-card__l4-dims { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.slot-card__hint {
  font-size: 13px; color: var(--color-text-3); margin: 0 0 4px;
}
.slot-card__gap-tag { margin-bottom: 4px; }

/* Empty */
.slot-card__empty { padding: 12px 0; }

/* 静默扫描提示条 */
.slot-card__hint-bar {
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px;
  padding: 8px 16px;
  background: #f7f8fa; border-bottom: 1px solid #e5e6eb; font-size: 12px;
}
.slot-card__hint-existing {
  color: #00b42a; font-weight: 500; white-space: nowrap;
}
.slot-card__hint-no-data {
  color: #86909c; font-weight: 400; white-space: nowrap;
}
.slot-card__hint-gaps {
  display: flex; flex-wrap: wrap; align-items: center; gap: 2px;
  color: #ff7d00; font-weight: 400;
}

/* 响应式：窄屏幕时上下排列 */
@media (max-width: 768px) {
  .slot-card__dual { flex-direction: column; }
  .slot-card__left { border-right: none; border-bottom: 1px solid var(--color-border-2); max-height: none; }
}
</style>
