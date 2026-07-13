<template>
  <!-- Step 0: 选题 -->
  <div v-if="currentStep === 0" class="step-content">
    <a-card>
      <template #title>
        <a-space>
          <span>选题推荐</span>
          <a-tag v-if="scannedFolders.length" color="arcoblue" size="small">{{ scannedFolders.length }} 个知识库</a-tag>
        </a-space>
      </template>
      <template #extra>
        <a-button type="text" size="small" @click="refreshTopics" :loading="topicsLoading">
          <IconRefresh style="margin-right: 4px" /> 换一批
        </a-button>
      </template>

      <!-- 加载中状态 -->
      <div v-if="topicsLoading" style="text-align: center; padding: 40px">
        <a-spin :size="50" dot tip="AI 正在分析推荐选题..." />
      </div>

      <!-- 话题列表 -->
      <div v-else-if="topics.length" class="topic-list">
        <div
          v-for="(t, i) in topics"
          :key="i"
          class="topic-item"
          :class="{ 
            selected: selectedDirection?.name === t.name,
            'topic-excellent': (t.overall_score || 0) >= 80,
            'topic-good': (t.overall_score || 0) >= 60 && (t.overall_score || 0) < 80,
            'topic-poor': (t.overall_score || 0) < 60
          }"
          @click="selectDirectionAndAdvance(t)"
        >
          <div class="topic-header">
            <div class="topic-name">{{ t.name }}</div>
            <a-tag v-if="selectedDirection?.name === t.name" color="arcoblue" size="small">已选</a-tag>
            <a-tag v-if="(t.overall_score || 0) >= 80" color="green" size="small">⭐ 推荐</a-tag>
            <a-tag v-else-if="(t.overall_score || 0) >= 60" color="orange" size="small">💡 良好</a-tag>
            <a-tag v-else color="red" size="small">⚠️ 待补充</a-tag>
          </div>
          <div class="topic-desc">{{ t.description }}</div>
          <div class="topic-meta">
            <div class="meta-item">
              <span class="meta-label">覆盖度</span>
              <div class="progress-track">
                <div class="progress-fill" :style="{ width: (t.coverage * 100).toFixed(0) + '%' }"></div>
              </div>
              <span class="meta-value">{{ (t.coverage * 100).toFixed(0) }}%</span>
            </div>
          </div>
          <div class="topic-reason">
            <IconBulb style="color: #F7BA2A; margin-right: 4px; font-size: 14px" />
            <span>{{ t.reason }}</span>
          </div>
          <div v-if="t.needed" class="topic-needed">
            <span class="needed-label">需要补充：</span>
            <span>{{ t.needed }}</span>
          </div>

          <!-- 3 分制评估 -->
          <div v-if="t.direction_score || t.deficiency_score || t.overall_score" style="margin-top: 12px; padding-top: 12px; border-top: 1px dashed #e5e6eb">
            <a-row :gutter="12">
              <a-col :span="8">
                <div class="score-card" :class="{ 'score-high': t.direction_score >= 80, 'score-medium': t.direction_score >= 60 && t.direction_score < 80, 'score-low': t.direction_score < 60 }">
                  <div class="score-title">方向适合度</div>
                  <div class="score-value" :style="{ color: t.direction_score >= 80 ? '#00b42a' : t.direction_score >= 60 ? '#f7ba1e' : '#f53f3f' }">
                    {{ t.direction_score || 0 }}<span class="score-unit">分</span>
                  </div>
                  <div class="score-desc">
                    {{ t.direction_analysis || '暂无分析' }}
                  </div>
                </div>
              </a-col>
              <a-col :span="8">
                <div class="score-card" :class="{ 'score-high': t.deficiency_score >= 80, 'score-medium': t.deficiency_score >= 50 && t.deficiency_score < 80, 'score-low': t.deficiency_score < 50 }">
                  <div class="score-title">内容完整度</div>
                  <div class="score-value" :style="{ color: t.deficiency_score >= 80 ? '#00b42a' : t.deficiency_score >= 50 ? '#f7ba1e' : '#f53f3f' }">
                    {{ t.deficiency_score || 0 }}<span class="score-unit">分</span>
                  </div>
                  <div class="score-details">
                    <div v-for="(detail, di) in (t.deficiency_details || []).slice(0, 2)" :key="di" class="detail-item">
                      <a-tag v-if="detail.severity === 'high'" size="small" color="red">高</a-tag>
                      <a-tag v-else-if="detail.severity === 'medium'" size="small" color="orange">中</a-tag>
                      <a-tag v-else size="small" color="arcoblue">低</a-tag>
                      <span>{{ detail.item }}</span>
                    </div>
                  </div>
                </div>
              </a-col>
              <a-col :span="8">
                <div class="score-card" :class="{ 'score-high': t.overall_score >= 80, 'score-medium': t.overall_score >= 60 && t.overall_score < 80, 'score-low': t.overall_score < 60 }">
                  <div class="score-title">综合评分</div>
                  <div class="score-value" :style="{ color: t.overall_score >= 80 ? '#00b42a' : t.overall_score >= 60 ? '#f7ba1e' : '#f53f3f' }">
                    {{ t.overall_score || 0 }}<span class="score-unit">分</span>
                  </div>
                  <div class="score-tag">
                    <a-tag v-if="(t.overall_score || 0) >= 80" color="green" size="small">可直接生成</a-tag>
                    <a-tag v-else-if="(t.overall_score || 0) >= 60" color="orange" size="small">建议补充</a-tag>
                    <a-tag v-else color="red" size="small">素材不足</a-tag>
                  </div>
                </div>
              </a-col>
            </a-row>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else style="text-align: center; padding: 40px; color: #86909c">
        <a-empty description="暂无推荐选题，请返回知识库检索页重新搜索" />
        <a-button type="primary" style="margin-top: 16px" @click="$router.push('/mcp-search')">
          返回检索
        </a-button>
      </div>
    </a-card>
  </div>
</template>

<script setup>
import { IconRefresh, IconBulb } from '@arco-design/web-vue/es/icon'
import { useWorkflowState } from '../../composables/useWorkflowState'

const {
  currentStep, scannedFolders, selectedDirection, directions, directionsLoading,
  mcpSummary, mcpFiles, mcpTopic, topics, topicsLoading,
  selectDirection, selectDirectionAndAdvance, loadTopics,
  refreshTopics, kbTreeData, completenessResult,
} = useWorkflowState()
</script>

<style scoped>
.step-content { width: 100%; }
.step-content :deep(.arco-card) { width: 100%; }

/* 话题列表 */
.topic-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.topic-item {
  border: 2px solid #e5e6eb;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #ffffff;
}

.topic-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.topic-item.topic-excellent {
  border-color: #00b42a;
  background: linear-gradient(135deg, #f6ffed 0%, #ffffff 100%);
}

.topic-item.topic-good {
  border-color: #ff7d00;
  background: linear-gradient(135deg, #fff7e6 0%, #ffffff 100%);
}

.topic-item.topic-poor {
  border-color: #f53f3f;
  background: linear-gradient(135deg, #fff2f0 0%, #ffffff 100%);
}

.topic-item.selected {
  border-color: #165dff !important;
  background: linear-gradient(135deg, #e8f3ff 0%, #ffffff 100%) !important;
  box-shadow: 0 0 0 3px rgba(22, 93, 255, 0.1);
}

.topic-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.topic-name {
  font-size: 18px;
  font-weight: 700;
  color: #1d2129;
  flex: 1;
}

.topic-desc {
  font-size: 14px;
  color: #4e5969;
  margin-bottom: 12px;
  line-height: 1.6;
}

.topic-meta { margin-bottom: 12px; }

.meta-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.meta-label {
  font-size: 13px;
  color: #86909c;
  white-space: nowrap;
}

.progress-track {
  flex: 1;
  height: 8px;
  background: #e5e6eb;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #165dff, #4080ff);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.meta-value {
  font-size: 13px;
  font-weight: 600;
  color: #165dff;
  white-space: nowrap;
}

.topic-reason {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  font-size: 13px;
  color: #4e5969;
  margin-bottom: 8px;
  line-height: 1.6;
}

.topic-needed {
  font-size: 13px;
  color: #f53f3f;
  padding: 8px 12px;
  background: #fff2f0;
  border-radius: 6px;
  margin-bottom: 12px;
}

.needed-label { font-weight: 600; }

/* 评分卡片 */
.score-card {
  text-align: center;
  padding: 16px;
  border-radius: 10px;
  min-height: 160px;
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
}

.score-card.score-high {
  background: #f6ffed;
  border: 2px solid #b7eb8f;
}

.score-card.score-medium {
  background: #fff7e6;
  border: 2px solid #ffd591;
}

.score-card.score-low {
  background: #fff2f0;
  border: 2px solid #ffccc7;
}

.score-title {
  font-size: 14px;
  color: #1d2129;
  font-weight: 600;
  margin-bottom: 8px;
}

.score-value {
  font-size: 32px;
  font-weight: 800;
  margin-bottom: 8px;
  line-height: 1;
}

.score-unit { font-size: 16px; font-weight: 500; }

.score-desc {
  font-size: 12px;
  color: #4e5969;
  line-height: 1.6;
  text-align: left;
  flex: 1;
}

.score-details { flex: 1; text-align: left; }

.detail-item {
  margin-bottom: 4px;
  line-height: 1.5;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #4e5969;
}

.score-tag { margin-top: auto; display: flex; justify-content: center; }
</style>
