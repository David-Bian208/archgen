<template>
  <div class="smart-supplement-card">
    <!-- 来源标签 -->
    <div class="source-tag" :style="{ backgroundColor: tagColor + '20', color: tagColor, borderColor: tagColor + '40' }">
      {{ tagText }}
    </div>

    <!-- 拒补模式：显示原因 + 引导问题 -->
    <div v-if="mode === 'refuse'" class="refusal-content">
      <a-alert type="error" style="margin-top: 12px" :show-icon="true">
        {{ alertMessage || '未检索到相关资料' }}
      </a-alert>
      <div v-if="reason" class="refusal-reason">
        <a-typography-text type="secondary" size="small">{{ reason }}</a-typography-text>
      </div>
      <div v-if="questions?.length" class="refusal-questions">
        <a-typography-text strong style="margin-top: 12px; display: block; margin-bottom: 8px">引导问题：</a-typography-text>
        <a-list :data="questions" :bordered="false">
          <template #item="{ item, index }">
            <a-list-item style="padding: 12px 0; border-bottom: 1px dashed #e5e6eb">
              <div class="question-item">
                <span class="question-index">{{ index + 1 }}</span>
                <div class="question-content">
                  <div class="question-text">{{ item.question }}</div>
                  <div v-if="item.hint" class="question-hint">{{ item.hint }}</div>
                </div>
              </div>
            </a-list-item>
          </template>
        </a-list>
      </div>
    </div>

    <!-- 降级提示 Alert（L1-L4 显示） -->
    <a-alert v-else-if="alertMessage" type="warning" style="margin-top: 12px" :show-icon="false">
      {{ alertMessage }}
    </a-alert>

    <!-- L0/L1: 内容展示 -->
    <div v-if="(knowledgeLevel === 'L0' || knowledgeLevel === 'L1') && content" class="supplement-content">
      <div class="content-text">{{ content }}</div>
      <div v-if="evidenceQuote" class="evidence-quote">
        <a-typography-text type="secondary" size="small">原文引用：{{ evidenceQuote }}</a-typography-text>
      </div>
      <div v-if="gapHint" class="gap-hint">
        <a-tag color="orange">📌 {{ gapHint }}</a-tag>
      </div>
    </div>

    <!-- L2: 问题展示 -->
    <div v-else-if="knowledgeLevel === 'L2' && questions?.length" class="questions-list">
      <a-typography-text strong style="margin-bottom: 12px; display: block">引导问题：</a-typography-text>
      <a-list :data="questions" :bordered="false">
        <template #item="{ item, index }">
          <a-list-item style="padding: 12px 0; border-bottom: 1px dashed #e5e6eb">
            <div class="question-item">
              <span class="question-index">{{ index + 1 }}</span>
              <div class="question-content">
                <div class="question-text">{{ item.question }}</div>
                <div v-if="item.hint" class="question-hint">{{ item.hint }}</div>
              </div>
            </div>
          </a-list-item>
        </template>
      </a-list>
    </div>

    <!-- L3: 类比展示 -->
    <div v-else-if="knowledgeLevel === 'L3' && analogy" class="analogy-content">
      <a-typography-text strong style="margin-bottom: 8px; display: block">类比推导：</a-typography-text>
      <div class="analogy-text">{{ analogy }}</div>
      <div v-if="analogyExplanation" class="analogy-explanation">
        <a-typography-text type="secondary" size="small">说明：{{ analogyExplanation }}</a-typography-text>
      </div>
    </div>

    <!-- L4: 框架展示 -->
    <div v-else-if="knowledgeLevel === 'L4' && framework?.dimensions?.length" class="framework-content">
      <a-typography-text strong style="margin-bottom: 12px; display: block">逻辑框架：</a-typography-text>
      <a-list :data="framework.dimensions" :bordered="false">
        <template #item="{ item, index }">
          <a-list-item style="padding: 12px 0; border-bottom: 1px dashed #e5e6eb">
            <div class="framework-item">
              <span class="framework-index">{{ index + 1 }}</span>
              <div class="framework-content-item">
                <div class="framework-name">{{ item.name }}</div>
                <div v-if="item.hint" class="framework-hint">{{ item.hint }}</div>
              </div>
            </div>
          </a-list-item>
        </template>
      </a-list>
    </div>

    <!-- 降级按钮 -->
    <div v-if="canDegrade && mode !== 'refuse'" class="degrade-actions">
      <a-button type="outline" size="small" @click="$emit('degrade')">
        <template #icon><icon-arrow-down /></template>
        不满意？降级一级重新生成
      </a-button>
    </div>

    <!-- 操作按钮（拒补模式不显示） -->
    <div v-if="mode !== 'refuse'" class="supplement-actions">
      <a-space>
        <a-button type="primary" size="small" @click="$emit('confirm')">
          <template #icon><icon-check /></template>
          确认使用
        </a-button>
        <a-button size="small" @click="$emit('edit')">
          <template #icon><icon-edit /></template>
          编辑
        </a-button>
      </a-space>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { IconCheck, IconEdit, IconArrowDown } from '@arco-design/web-vue/es/icon'

const props = defineProps({
  knowledgeLevel: {
    type: String,
    default: 'L1',
  },
  mode: {
    type: String,
    default: '',  // 'refuse' = 拒补模式
  },
  reason: {
    type: String,
    default: '',
  },
  content: {
    type: String,
    default: '',
  },
  questions: {
    type: Array,
    default: () => [],
  },
  analogy: {
    type: String,
    default: '',
  },
  analogyExplanation: {
    type: String,
    default: '',
  },
  framework: {
    type: Object,
    default: () => ({ dimensions: [] }),
  },
  alertMessage: {
    type: String,
    default: '',
  },
  sourceTag: {
    type: Object,
    default: () => ({ text: '', color: 'blue' }),
  },
  evidenceQuote: {
    type: String,
    default: '',
  },
  gapHint: {
    type: String,
    default: '',
  },
  canDegrade: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['confirm', 'edit', 'degrade'])

const tagText = computed(() => props.sourceTag?.text || '⚠️ 通用模式（需补充细节）')
const tagColor = computed(() => props.sourceTag?.color || 'blue')
</script>

<style scoped>
.smart-supplement-card {
  padding: 16px;
  background: #f7f8fa;
  border-radius: 8px;
  border: 1px solid #e5e6eb;
}

.source-tag {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  border: 1px solid;
}

.supplement-content {
  margin-top: 12px;
}

.refusal-content {
  margin-top: 12px;
}

.refusal-reason {
  margin-top: 8px;
  padding: 8px 12px;
  background: #fff;
  border-radius: 4px;
}

.refusal-questions {
  margin-top: 12px;
}

.content-text {
  font-size: 14px;
  line-height: 1.8;
  white-space: pre-wrap;
}

.evidence-quote {
  margin-top: 12px;
  padding: 8px 12px;
  background: #fff;
  border-radius: 4px;
  border-left: 3px solid #00b42a;
}

.gap-hint {
  margin-top: 12px;
}

.questions-list {
  margin-top: 12px;
}

.question-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.question-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #165dff;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.question-content {
  flex: 1;
}

.question-text {
  font-size: 14px;
  font-weight: 500;
  line-height: 1.6;
}

.question-hint {
  margin-top: 4px;
  font-size: 12px;
  color: #86909c;
}

.analogy-content {
  margin-top: 12px;
}

.analogy-text {
  font-size: 14px;
  line-height: 1.8;
  white-space: pre-wrap;
}

.analogy-explanation {
  margin-top: 8px;
  padding: 8px 12px;
  background: #fff;
  border-radius: 4px;
  border-left: 3px solid #f7ba1e;
}

.framework-content {
  margin-top: 12px;
}

.framework-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.framework-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #f7ba1e;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.framework-content-item {
  flex: 1;
}

.framework-name {
  font-size: 14px;
  font-weight: 500;
}

.framework-hint {
  margin-top: 4px;
  font-size: 12px;
  color: #86909c;
}

.degrade-actions {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px dashed #e5e6eb;
}

.supplement-actions {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #e5e6eb;
}
</style>
