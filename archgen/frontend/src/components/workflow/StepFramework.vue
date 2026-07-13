<template>
  <div class="step-content">
    <!-- framework selection -->
    <div v-if="currentStep === 2" class="step-content">
      <a-card>
        <template #title>
          <a-space>
            <span>框架选择</span>
            <a-tag v-if="selectedDirection?.name" color="arcoblue">{{ selectedDirection.name }}</a-tag>
            <a-button type="text" size="mini" :loading="frameworksLoading" @click="regenerateFrameworks">
              🔄 重新推荐
            </a-button>
          </a-space>
        </template>

        <!-- 加载中状态 -->
        <div v-if="frameworksLoading" style="text-align: center; padding: 40px">
          <a-spin :size="50" dot tip="AI 正在分析推荐框架..." />
        </div>

        <!-- 空框架状态 -->
        <div v-else-if="frameworks.length === 0" style="text-align: center; padding: 40px; color: #86909c">
          <a-empty description="暂无推荐框架，请点击「重新推荐」重试" />
        </div>

        <!-- 框架列表 -->
        <div v-else>
          <div v-for="(f, j) in frameworks" :key="j" class="framework-card" style="margin-bottom: 12px">
            <a-card :bordered="true" hoverable size="small" :style="{ borderLeft: `4px solid ${getAlignmentColor(f.direction_alignment_score ?? f.match_score)}` }">
              <template #title>
                <span v-if="j === 0"> </span>
                <span v-else-if="j === 1">🥈 </span>
                <span v-else-if="j === 2">🥉 </span>
                {{ f.name }}
                <a-tag v-if="f.framework_origin" size="small" color="gray" style="margin-left: 8px">
                  📚 {{ f.framework_origin }}
                </a-tag>
                <a-tag :color="getAlignmentTagColor(f.direction_alignment_score ?? f.match_score)" style="margin-left: 4px">
                  🎯 对齐 {{ ((f.direction_alignment_score ?? f.match_score) * 100).toFixed(0) }}%
                </a-tag>
              </template>
              <div style="font-size: 13px">{{ f.description }}</div>

              <!-- 单行匹配信息 -->
              <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #e5e6eb; font-size: 12px; color: #86909c; display: flex; flex-wrap: wrap; gap: 12px; align-items: center">
                <span v-if="f.reason"> {{ f.reason }}</span>
                <span v-if="f.source === 'general_knowledge'" style="color: #ff7d00">⚠️ 基于通用知识</span>
                <span v-if="f.usage_hint">📌 {{ f.usage_hint }}</span>
              </div>

              <!-- 风险提示 -->
              <div v-if="f.warning" style="margin-top: 8px; font-size: 12px; color: #ff7d00">
                {{ f.warning }}
              </div>

              <!-- 需要补充 -->
              <div v-if="f.needs_supplement?.length" style="margin-top: 4px; font-size: 12px; color: #86909c">
                还需要：{{ f.needs_supplement.join('、') }}
              </div>

              <a-button
                :type="(f.direction_alignment_score ?? f.match_score) >= 0.7 ? 'primary' : 'outline'"
                :status="(f.direction_alignment_score ?? f.match_score) >= 0.7 ? 'success' : (f.direction_alignment_score ?? f.match_score) >= 0.6 ? 'warning' : 'default'"
                size="small"
                style="margin-top: 12px"
                @click="selectFramework(f)"
              >
                {{ (f.direction_alignment_score ?? f.match_score) >= 0.7 ? '选择此框架' : (f.direction_alignment_score ?? f.match_score) >= 0.6 ? '⚠️ 谨慎选择(需转化)' : '不推荐(请选其他)' }}
              </a-button>
            </a-card>
          </div>
        </div>
      </a-card>
    </div>

    <!-- 进入工作台 -->
    <div v-if="currentStep === 2 && selectedFramework" class="step-content" style="margin-top: 16px">
      <a-card>
        <template #title>
          <a-space>
            <span>✅ 已选择框架</span>
          </a-space>
        </template>
        <div style="font-size: 13px; line-height: 1.8">
          <div style="margin-bottom: 12px; color: #4e5969">
            选定框架：<strong>{{ selectedFramework.name }}</strong>
          </div>
          <a-button type="primary" size="medium" @click="goToCheck">
            🚀 进入工作台
          </a-button>
        </div>
      </a-card>
    </div>
  </div>
</template>

<script setup>
import { useWorkflowState } from '../../composables/useWorkflowState'
const {
  // refs
  currentStep,
  selectedDirection,
  frameworksLoading,
  frameworks,
  selectedFramework,
  // functions
  regenerateFrameworks,
  selectFramework,
  goToCheck,
  // color helpers
  getAlignmentColor,
  getAlignmentTagColor,
  getAlignmentBgColor,
  getAlignmentBorderColor,
  getAlignmentTextColor,
  getCoverageColor,
} = useWorkflowState()
</script>

<style scoped>
.step-content {
  width: 100%;
}
.step-content :deep(.arco-card) {
  width: 100%;
}
</style>
