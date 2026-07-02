<template>
  <div class="workflow-view">
    <a-page-header title="智能写作工作流" @back="$router.push('/mcp-search')">
    </a-page-header>

    <!-- 竖排步骤列表 -->
    <div class="step-summary-list">
      <div 
        v-for="(name, index) in stepNames" 
        :key="index" 
        class="step-summary-item"
        :class="{ 
          'is-completed': index < currentStep, 
          'is-current': index === currentStep, 
          'is-future': index > currentStep 
        }"
      >
        <div class="step-summary-header" @click="toggleStepCollapse(index)">
          <span class="step-status-icon">
            <template v-if="index < currentStep">✅</template>
            <template v-else-if="index === currentStep">🔄</template>
            <template v-else>○</template>
          </span>
          <span class="step-name">{{ name }}</span>
          <span v-if="index < currentStep && stepSummaries[index] && !collapsedSteps[index]" class="step-summary-text">
            ：{{ stepSummaries[index] }}
          </span>
          <span v-if="index < currentStep && stepSummaries[index]" class="step-collapse-icon">
            {{ collapsedSteps[index] ? '▶' : '▼' }}
          </span>
        </div>
        <!-- 展开详情区域 -->
        <div v-if="collapsedSteps[index] && index < currentStep && stepDetails[index]" class="step-detail-content">
          {{ stepDetails[index] }}
        </div>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="content-area">
      <a-spin dot :loading="loading" tip="加载中...">
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

        <!-- 关键缺失项补充弹窗（分步骤工作流） -->
        <a-modal
          v-model:visible="supplementModalVisible"
          :title="`补充缺失项：${currentSupplementItem || ''}`"
          width="800px"
          :footer="null"
          @cancel="closeSupplementModal"
        >
          <div v-if="currentSupplementItem" class="supplement-modal-content">
            <!-- 步骤指示器 -->
            <a-steps :current="supplementStep" style="margin-bottom: 24px">
              <a-step title="API 检索" description="从外部知识库获取案例" />
              <a-step title="上下文推断" description="AI 结合 MCP + API 案例生成补充" />
              <a-step title="确认使用" description="编辑确认后保存" />
            </a-steps>

            <!-- Step 1: API 检索 -->
            <div v-if="supplementStep === 1">
              <a-alert type="info" style="margin-bottom: 16px">
                <template #title>第 1 步：从 AI-Pulse 检索外部案例</template>
                正在为「{{ currentSupplementItem }}」搜索相关案例...
              </a-alert>
              <div v-if="supplementApiLoading" style="text-align: center; padding: 30px">
                <a-spin :size="50" dot tip="正在检索外部知识库..." />
                <div style="margin-top: 12px; font-size: 13px; color: #86909c">
                  首次检索可能需要 10-20 秒，请耐心等待...
                </div>
              </div>

              <div v-if="supplementApiCases.length > 0" style="margin-top: 16px">
                <a-alert type="success" style="margin-bottom: 12px">
                  <template #title>✅ 找到 {{ supplementApiCases.length }} 个相关案例</template>
                  <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 4px">
                    <span>请勾选需要补充到文章的案例</span>
                    <a-button type="text" size="mini" @click="toggleSupplementApiSelectAll">
                      {{ allSupplementApiCasesSelected ? '取消全选' : '全选' }}
                    </a-button>
                  </div>
                </a-alert>
                <a-list :data="supplementApiCases" :bordered="false" size="small" style="max-height: 300px; overflow-y: auto">
                  <template #item="{ item, index }">
                    <a-list-item>
                      <a-checkbox :checked="supplementApiSelectedCases[index]" @change="(checked) => supplementApiSelectedCases[index] = checked" style="width: 100%">
                        <div class="ai-pulse-case">
                          <div class="case-title">{{ item.title }}</div>
                          <div class="case-summary">{{ item.summary?.substring(0, 100) }}...</div>
                          <div class="case-meta">
                            <a-tag size="small" color="blue">{{ item.source }}</a-tag>
                            <a-tag size="small" color="green">评分: {{ item.score }}</a-tag>
                            <a-tag v-if="item.category" size="small">{{ item.category }}</a-tag>
                          </div>
                        </div>
                      </a-checkbox>
                    </a-list-item>
                  </template>
                </a-list>
                <a-space style="margin-top: 16px; width: 100%; justify-content: space-between">
                  <a-button @click="closeSupplementModal">取消</a-button>
                  <a-button type="primary" @click="goToStep2" :disabled="!anySupplementApiCaseSelected">
                    确认选中，进入下一步 →
                  </a-button>
                </a-space>
              </div>

              <div v-if="supplementApiCases.length === 0 && !supplementApiLoading" style="margin-top: 16px">
                <a-alert type="warning">
                  <template #title>未找到相关案例</template>
                  AI-Pulse 未返回匹配的案例（可能因为外部服务暂不可用或关键词不匹配）。您可以选择手动补充或跳过此步直接推断。
                </a-alert>
                <a-space style="margin-top: 16px; width: 100%; justify-content: space-between">
                  <a-button @click="closeSupplementModal">取消</a-button>
                  <a-button type="primary" @click="goToStep2NoCases">
                    跳过 API 检索，直接推断 →
                  </a-button>
                </a-space>
              </div>
            </div>

            <!-- Step 2: 上下文推断 -->
            <div v-if="supplementStep === 2">
              <!-- 加载中状态 -->
              <div v-if="supplementInferLoading">
                <a-alert type="info" style="margin-bottom: 16px">
                  <template #title>第 2 步：AI 上下文推断</template>
                  <div v-if="selectedSupplementCasesSummary">
                    已选中 {{ selectedSupplementCasesSummary.count }} 个 API 案例，AI 正在结合 MCP + 案例生成补充内容...
                  </div>
                  <div v-else>
                    AI 正在基于 MCP 摘要生成推断内容...
                  </div>
                </a-alert>
                <div style="text-align: center; padding: 20px">
                  <a-spin :size="50" dot tip="AI 正在推断生成..." />
                </div>
              </div>

              <!-- 推断完成状态 -->
              <div v-if="supplementInferResult">
                <a-alert type="success" style="margin-bottom: 12px">
                  <template #title>✅ 推断完成</template>
                  <a-typography-text type="secondary" style="font-size: 12px">
                    推断依据：{{ supplementInferResult.inference_note }}
                  </a-typography-text>
                </a-alert>
                <a-form layout="vertical">
                  <a-form-item label="推断结果（可编辑）">
                    <a-textarea
                      v-model="supplementInferResult.content"
                      :auto-size="{ minRows: 8, maxRows: 15 }"
                      placeholder="AI 推断的补充内容..."
                    />
                    <a-typography-text type="secondary" style="font-size: 12px; margin-top: 4px; display: block">
                      提示：您可以直接编辑内容，确保准确后再确认
                    </a-typography-text>
                  </a-form-item>
                </a-form>
                <a-space style="margin-top: 16px; width: 100%; justify-content: space-between">
                  <a-button @click="supplementStep = 1" :disabled="supplementSaving">← 返回上一步</a-button>
                  <a-button type="primary" @click="goToStep3" :loading="supplementSaving">
                    确认内容，进入下一步 →
                  </a-button>
                </a-space>
              </div>
            </div>

            <!-- Step 3: 确认使用 -->
            <div v-if="supplementStep === 3">
              <a-alert type="success" style="margin-bottom: 16px">
                <template #title>第 3 步：确认补充内容</template>
                请确认以下补充内容，确认后将标记该缺失项为已补充。
              </a-alert>
              <a-card :bordered="true" style="background: #f7f8fa">
                <a-typography-title :heading="6" style="margin-bottom: 8px">
                  补充内容：
                </a-typography-title>
                <div style="white-space: pre-wrap; line-height: 1.8; font-size: 14px">
                  {{ supplementInferResult?.content || '无内容' }}
                </div>
              </a-card>

              <div v-if="selectedSupplementCasesSummary" style="margin-top: 16px">
                <a-typography-title :heading="6" style="margin-bottom: 8px">
                  引用的 API 案例（{{ selectedSupplementCasesSummary.count }} 个）：
                </a-typography-title>
                <a-list :data="selectedSupplementCasesSummary.cases" :bordered="false" size="small">
                  <template #item="{ item }">
                    <a-list-item>
                      <a-tag color="blue">{{ item.source }}</a-tag>
                      <span style="margin-left: 8px; font-size: 13px">{{ item.title }}</span>
                    </a-list-item>
                  </template>
                </a-list>
              </div>

              <a-space style="margin-top: 20px; width: 100%; justify-content: space-between">
                <a-button @click="supplementStep = 2">← 返回编辑</a-button>
                <a-button type="primary" status="success" long @click="confirmSupplementStep3" :loading="supplementSaving">
                  ✅ 确认使用，保存补充内容
                </a-button>
              </a-space>
            </div>
          </div>
        </a-modal>

        <!-- 批量 AI-Pulse 检索弹窗 -->
        <a-modal
          v-model:visible="batchAiPulseModalVisible"
          title="一键 AI-Pulse 检索结果"
          width="900px"
          :footer="null"
        >
          <a-alert type="success" style="margin-bottom: 16px">
            <template #title>所有缺失项已检索完毕</template>
            请查看每个缺失项的检索结果，确认后点击底部按钮保存到知识库。
          </a-alert>
          <div style="max-height: 500px; overflow-y: auto">
            <div v-for="(result, ri) in batchAiPulseResults" :key="ri" style="margin-bottom: 16px; padding: 16px; border: 1px solid #e5e6eb; border-radius: 4px; background: #fff">
              <div style="font-weight: 600; margin-bottom: 8px; color: #1d2129">
                {{ result.item }}
              </div>
              <div v-if="result.loading" style="padding: 12px; text-align: center; color: #86909c">
                <a-spin size="small" dot tip="检索中..." />
              </div>
              <div v-else-if="result.cases.length === 0" style="padding: 12px; color: #c9cdd4">
                未找到相关案例
              </div>
              <div v-else style="padding: 8px; background: #f7f8fa; border-radius: 4px">
                <a-tag color="green" size="small">找到 {{ result.cases.length }} 个案例</a-tag>
                <div v-for="(c, ci) in result.cases" :key="ci" style="margin-top: 8px; font-size: 13px; color: #4e5969; line-height: 1.6">
                  <strong>{{ c.title }}</strong>
                  <div>{{ c.summary?.substring(0, 80) }}...</div>
                  <div style="margin-top: 2px">
                    <a-tag size="mini" color="blue">{{ c.source }}</a-tag>
                    <a-tag size="mini" color="green">评分: {{ c.score }}</a-tag>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <a-space style="margin-top: 16px; width: 100%; justify-content: space-between">
            <a-button @click="batchAiPulseModalVisible = false">取消</a-button>
            <a-button type="primary" status="success" @click="confirmBatchAiPulse">
              确认全部保存到知识库
            </a-button>
          </a-space>
        </a-modal>

        <!-- 批量手动补充弹窗 -->
        <a-modal
          v-model:visible="batchManualModalVisible"
          title="一键手动补充"
          width="900px"
          :footer="null"
        >
          <a-alert type="info" style="margin-bottom: 16px">
            <template #title>为每个缺失项输入补充内容</template>
            留空的缺失项将被跳过。
          </a-alert>
          <div style="max-height: 500px; overflow-y: auto">
            <div v-for="(missingItem, mi) in (completenessResult?.missing_critical || [])" :key="mi" style="margin-bottom: 16px; padding: 16px; border: 1px solid #e5e6eb; border-radius: 4px; background: #fff">
              <div style="font-weight: 600; margin-bottom: 8px; color: #1d2129">
                {{ missingItem }}
              </div>
              <a-textarea
                v-model="batchManualTexts[mi]"
                :auto-size="{ minRows: 3, maxRows: 6 }"
                placeholder="请输入补充内容..."
              />
            </div>
          </div>
          <a-space style="margin-top: 16px; width: 100%; justify-content: space-between">
            <a-button @click="batchManualModalVisible = false">取消</a-button>
            <a-button type="primary" status="success" @click="confirmBatchManual">
              确认全部保存
            </a-button>
          </a-space>
        </a-modal>

        <!-- 需求2：编辑弹窗（左右分栏 + AI辅助） -->
        <a-modal
          v-model:visible="editModalVisible"
          :title="`编辑补充：${currentSupplementItem}`"
          width="1200px"
          :footer="null"
          @cancel="closeEditModal"
        >
          <div v-if="editModalVisible">
            <a-alert type="info" style="margin-bottom: 16px">
              <template #title>编辑模式</template>
              左侧为原有内容（只读），右侧为编辑区。可使用 AI 辅助优化内容。
            </a-alert>
            
            <a-row :gutter="16">
              <!-- 左侧：原有内容（只读） -->
              <a-col :span="12">
                <a-card title="原有内容" :bordered="true" style="background: #f7f8fa">
                  <div style="white-space: pre-wrap; line-height: 1.8; font-size: 14px; max-height: 500px; overflow-y: auto">
                    {{ editOriginalContent || '暂无原有内容' }}
                  </div>
                </a-card>
              </a-col>
              
              <!-- 右侧：编辑区 -->
              <a-col :span="12">
                <a-card title="编辑区" :bordered="true">
                  <a-textarea
                    v-model="editNewContent"
                    :auto-size="{ minRows: 15, maxRows: 25 }"
                    placeholder="在此编辑补充内容..."
                    style="margin-bottom: 12px"
                  />
                  
                  <!-- AI 辅助区域 -->
                  <a-divider orientation="left">AI 辅助</a-divider>
                  <a-space direction="vertical" style="width: 100%">
                    <a-button 
                      type="primary" 
                      :loading="editAiLoading" 
                      @click="aiAssistEdit"
                      :disabled="!editOriginalContent"
                    >
                      🤖 AI 优化建议
                    </a-button>
                    
                    <div v-if="editAiSuggestion" style="margin-top: 12px">
                      <a-card :bordered="true" size="small" style="background: #e8f3ff">
                        <template #title>
                          <a-space>
                            <icon-robot />
                            AI 优化建议
                          </a-space>
                        </template>
                        <div style="white-space: pre-wrap; line-height: 1.8; font-size: 13px; max-height: 300px; overflow-y: auto">
                          {{ editAiSuggestion }}
                        </div>
                        <a-button 
                          type="primary" 
                          size="small" 
                          style="margin-top: 12px" 
                          @click="applyAiSuggestion"
                        >
                          应用此建议到编辑区
                        </a-button>
                      </a-card>
                    </div>
                  </a-space>
                </a-card>
              </a-col>
            </a-row>
            
            <a-space style="margin-top: 16px; width: 100%; justify-content: flex-end">
              <a-button @click="closeEditModal">取消</a-button>
              <a-button type="primary" status="success" @click="saveEditedSupplement" :loading="editSaving">
                保存编辑
              </a-button>
            </a-space>
          </div>
        </a-modal>

        <!-- 需求1：统一补充弹窗（API检索 + AI推断） -->
        <a-modal
          v-model:visible="unifiedModalVisible"
          :title="`补充缺失项：${unifiedModalItem}`"
          width="900px"
          :footer="null"
          @cancel="closeUnifiedModal"
        >
          <div v-if="unifiedModalItem" class="supplement-modal-content">
            <!-- 步骤指示器 -->
            <a-steps :current="unifiedModalStep - 1" style="margin-bottom: 24px">
              <a-step title="API 检索" description="从外部知识库获取案例" />
              <a-step title="AI 推断" description="AI 结合 API 案例 + MCP 生成补充" />
              <a-step title="确认使用" description="编辑确认后保存" />
            </a-steps>

            <!-- Step 1: API 检索 -->
            <div v-if="unifiedModalStep === 1">
              <a-alert type="info" style="margin-bottom: 16px">
                <template #title>第 1 步：从 AI-Pulse 检索外部案例</template>
                正在为「{{ unifiedModalItem }}」搜索相关案例...
              </a-alert>
              
              <div v-if="unifiedApiLoading" style="text-align: center; padding: 30px">
                <a-spin :size="50" dot tip="正在检索外部知识库..." />
                <div style="margin-top: 12px; font-size: 13px; color: #86909c">
                  首次检索可能需要 10-20 秒，请耐心等待...
                </div>
              </div>

              <div v-if="unifiedApiCases.length > 0 && !unifiedApiLoading" style="margin-top: 16px">
                <a-alert type="success" style="margin-bottom: 12px">
                  <template #title>✅ 找到 {{ unifiedApiCases.length }} 个相关案例</template>
                  <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 4px">
                    <span>请勾选需要用于推断的案例</span>
                    <a-button type="text" size="mini" @click="toggleUnifiedSelectAll">
                      {{ unifiedApiSelected.every(Boolean) ? '取消全选' : '全选' }}
                    </a-button>
                  </div>
                </a-alert>
                <a-list :data="unifiedApiCases" :bordered="false" size="small" style="max-height: 300px; overflow-y: auto">
                  <template #item="{ item: apiItem, index }">
                    <a-list-item>
                      <a-checkbox :checked="unifiedApiSelected[index]" @change="(checked) => unifiedApiSelected[index] = checked" style="width: 100%">
                        <div class="ai-pulse-case">
                          <div class="case-title">{{ apiItem.title }}</div>
                          <div class="case-summary">{{ apiItem.summary?.substring(0, 100) }}...</div>
                          <div class="case-meta">
                            <a-tag size="small" color="blue">{{ apiItem.source }}</a-tag>
                            <a-tag size="small" color="green">评分: {{ apiItem.score }}</a-tag>
                          </div>
                        </div>
                      </a-checkbox>
                    </a-list-item>
                  </template>
                </a-list>
                <a-space style="margin-top: 16px; width: 100%; justify-content: space-between">
                  <a-button @click="closeUnifiedModal">取消</a-button>
                  <a-button type="primary" @click="goToUnifiedInfer" :disabled="!unifiedApiSelected.some(Boolean)">
                    使用选中案例，进入 AI 推断 →
                  </a-button>
                </a-space>
              </div>

              <div v-if="unifiedApiCases.length === 0 && !unifiedApiLoading" style="margin-top: 16px">
                <a-alert type="warning">
                  <template #title>未找到相关案例</template>
                  AI-Pulse 未返回匹配的案例。您可以选择直接使用 AI 推断（基于 MCP 摘要），或手动补充。
                </a-alert>
                <a-space style="margin-top: 16px; width: 100%; justify-content: space-between">
                  <a-button @click="closeUnifiedModal">取消</a-button>
                  <a-button type="primary" @click="goToUnifiedInferNoCases">
                    跳过 API，直接 AI 推断 →
                  </a-button>
                </a-space>
              </div>
            </div>

            <!-- Step 2: AI 推断 -->
            <div v-if="unifiedModalStep === 2">
              <!-- 加载中状态 -->
              <div v-if="unifiedInferLoading">
                <a-alert type="info" style="margin-bottom: 16px">
                  <template #title>第 2 步：AI 上下文推断</template>
                  <div v-if="unifiedApiCases.filter((_, i) => unifiedApiSelected[i]).length > 0">
                    AI 正在结合 {{ unifiedApiCases.filter((_, i) => unifiedApiSelected[i]).length }} 个 API 案例 + MCP 生成补充内容...
                  </div>
                  <div v-else>
                    AI 正在基于 MCP 摘要生成推断内容...
                  </div>
                </a-alert>
                <div style="text-align: center; padding: 20px">
                  <a-spin :size="50" dot tip="AI 正在推断生成..." />
                </div>
              </div>

              <!-- 推断完成状态 -->
              <div v-if="unifiedInferResult && !unifiedInferLoading">
                <a-alert type="success" style="margin-bottom: 12px">
                  <template #title>✅ 推断完成</template>
                  <a-typography-text type="secondary" style="font-size: 12px">
                    推断依据：{{ unifiedInferResult.inference_note }}
                  </a-typography-text>
                </a-alert>
                <a-form layout="vertical">
                  <a-form-item label="推断结果（可编辑）">
                    <a-textarea
                      v-model="unifiedInferResult.content"
                      :auto-size="{ minRows: 8, maxRows: 15 }"
                      placeholder="AI 推断的补充内容..."
                    />
                    <a-typography-text type="secondary" style="font-size: 12px; margin-top: 4px; display: block">
                      提示：您可以直接编辑内容，确保准确后再确认
                    </a-typography-text>
                  </a-form-item>
                </a-form>
                <a-space style="margin-top: 16px; width: 100%; justify-content: space-between">
                  <a-button @click="unifiedModalStep = 1" :disabled="unifiedSaving">← 返回上一步</a-button>
                  <a-button type="primary" @click="unifiedModalStep = 3" :loading="unifiedSaving">
                    确认内容，进入下一步 →
                  </a-button>
                </a-space>
              </div>
            </div>

            <!-- Step 3: 确认使用 -->
            <div v-if="unifiedModalStep === 3">
              <a-alert type="success" style="margin-bottom: 16px">
                <template #title>第 3 步：确认补充内容</template>
                请确认以下补充内容，确认后将标记该缺失项为已补充。
              </a-alert>
              <a-card :bordered="true" style="background: #f7f8fa">
                <a-typography-title :heading="6" style="margin-bottom: 8px">
                  补充内容：
                </a-typography-title>
                <div style="white-space: pre-wrap; line-height: 1.8; font-size: 14px">
                  {{ unifiedInferResult?.content || '无内容' }}
                </div>
              </a-card>

              <div v-if="unifiedApiCases.filter((_, i) => unifiedApiSelected[i]).length > 0" style="margin-top: 16px">
                <a-typography-title :heading="6" style="margin-bottom: 8px">
                  引用的 API 案例（{{ unifiedApiCases.filter((_, i) => unifiedApiSelected[i]).length }} 个）：
                </a-typography-title>
                <a-list :data="unifiedApiCases.filter((_, i) => unifiedApiSelected[i])" :bordered="false" size="small">
                  <template #item="{ item: apiItem }">
                    <a-list-item>
                      <a-tag color="blue">{{ apiItem.source }}</a-tag>
                      <span style="margin-left: 8px; font-size: 13px">{{ apiItem.title }}</span>
                    </a-list-item>
                  </template>
                </a-list>
              </div>

              <a-space style="margin-top: 16px; width: 100%; justify-content: space-between">
                <a-button @click="unifiedModalStep = 2" :disabled="unifiedSaving">← 返回编辑</a-button>
                <a-button type="primary" status="success" @click="confirmUnifiedSupplement" :loading="unifiedSaving">
                  确认使用，保存到知识库
                </a-button>
              </a-space>
            </div>
          </div>
        </a-modal>

        <!-- 批量统一补充结果弹窗（图1：显示来源） -->
        <a-modal
          v-model:visible="batchResultModalVisible"
          title="✅ 补充完成"
          width="800px"
          :footer="null"
        >
          <a-alert type="success" style="margin-bottom: 16px">
            <template #title>已补充 {{ batchResults.length }} 项内容</template>
            以下为您自动补充的内容及来源说明，确认后可继续下一步
          </a-alert>
          <div style="max-height: 400px; overflow-y: auto">
            <div v-for="(r, ri) in batchResults" :key="ri" style="margin-bottom: 16px; padding: 16px; border: 1px solid #e5e6eb; border-radius: 4px">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px">
                <div style="font-weight: 600; color: #1d2129">
                  {{ r.item }}
                </div>
                <a-tag :color="r.method === 'ai-pulse+infer' ? 'blue' : 'orange'" size="large">
                  {{ r.method === 'ai-pulse+infer' ? '🔍 API + AI 推断' : ' 纯 AI 推理' }}
                </a-tag>
              </div>
              <div style="padding: 8px; background: #f7f8fa; border-radius: 4px; font-size: 13px; line-height: 1.6; max-height: 150px; overflow-y: auto; white-space: pre-wrap">
                {{ r.content }}
              </div>
              <div v-if="r.note" style="margin-top: 8px; font-size: 12px; color: #86909c">
                推断依据：{{ r.note }}
              </div>
              <div v-if="r.method === 'ai-pulse+infer'" style="margin-top: 4px; font-size: 12px; color: #165dff">
                引用了 {{ r.apiCount }} 个 API 案例
              </div>
            </div>
          </div>
          <a-space style="margin-top: 16px; width: 100%; justify-content: space-between">
            <a-button @click="batchResultModalVisible = false">关闭</a-button>
            <a-button type="primary" status="success" @click="closeBatchResultModal">
              确认，进入下一步 →
            </a-button>
          </a-space>
        </a-modal>

        <!-- 草稿模式弹窗（Step 3 起草用） -->
        <a-modal
          v-model:visible="draftModalVisible"
          :title="`起草补充：${draftModalItem}`"
          width="800px"
          :footer="null"
        >
          <a-alert type="warning" style="margin-bottom: 16px">
            <template #title>⚠️ AI 参考草稿</template>
            以下为 AI 基于通用模式的推导参考，请核实后使用。
          </a-alert>
          
          <!-- 加载中 -->
          <div v-if="draftLoading" style="text-align: center; padding: 40px">
            <a-spin :size="50" dot tip="AI 正在生成参考草稿..." />
          </div>
          
          <!-- 草稿内容 -->
          <div v-else>
            <a-textarea
              v-model="draftContent"
              :auto-size="{ minRows: 12, maxRows: 20 }"
              placeholder="AI 参考草稿..."
            />
            <a-typography-text type="secondary" style="font-size: 12px; margin-top: 8px; display: block">
              提示：您可以直接编辑内容，确保准确后再确认使用
            </a-typography-text>
            <a-space style="margin-top: 16px; width: 100%; justify-content: space-between">
              <a-button @click="closeDraftModal">取消</a-button>
              <a-button type="primary" status="success" @click="confirmDraftSupplement" :loading="draftSaving">
                确认使用，保存到知识库
              </a-button>
            </a-space>
          </div>
        </a-modal>

        <!-- Step 2: 三列分析工作台 -->
        <div v-if="currentStep === 2" class="step-content">
          <ThreeColumnWorkbench
            :phase="phase"
            :streaming-thinking="streamingThinking"
            :stream-done="streamDone"
            :confirmed-slots="confirmedSlots"
            :slot-materials="slotMaterials"
            :slot-outlines="slotOutlines"
            :writing-plans="writingPlans"
            :slot-relations-data="slotRelations"
            :editing-slot="editingSlot"
            :show-edit-panel="showEditPanel"
            :followup-history="followupHistory"
            :all-slots-confirmed="allSlotsConfirmed"
            :pre-check-results="preCheckResults"
            :pre-check-running="preCheckRunning"
            @update-slot="(k, u) => updateSlot(k, u)"
            @remove-slot="removeSlot"
            @add-slot="addSlot"
            @confirm-slots="confirmAndFill"
            @stop-stream="stopStream"
            @open-edit-panel="openEditPanel"
            @close-edit-panel="closeEditPanel"
            @save-plan="saveWritingPlan"
            @add-material="addMaterialToSlot"
            @ask-followup="askFollowupQuestion"
            @run-pre-check="runSlotPreCheck"
            @adopt-alternative="adoptAlternative"
            @proceed-to-article="currentStep = 3"
          />
        </div>

        <!-- Step 1: 补充 - 完善分析内容 -->
        <div v-if="currentStep === 1" class="step-content">
          <StepSupplement
            ref="step2SupplementDialogRef"
            :mcp-summary="mcpSummary"
            :mcp-files="mcpFiles"
            :selected-direction="selectedDirection"
            :selected-framework="selectedFramework"
            :pre-check-loading="preCheckLoading"
            :pre-check-result="preCheckResult"
            :supplement2-text="supplement2Text"
            :supplement2-html="supplement2Html"
            :supplement-confirmed="supplementConfirmed"
            :pending-supplement-data="pendingSupplementData"
            :expanded-issues="expandedIssues"
            :kb-tree-data="kbTreeData"
            :material-pool="materialPool"
            :step2-supplement-dialog-visible="step2SupplementDialogVisible"
            :run-pre-check="runPreCheck"
            :confirm-supplement-and-proceed="confirmSupplementAndProceed"
            :skip-supplement2="skipSupplement2"
            :handle-step2-supplement-submit="handleStep2SupplementSubmit"
            :handle-step2-supplement-confirm="handleStep2SupplementConfirm"
            :open-step2-supplement-dialog="openStep2SupplementDialog"
            :open-supplement-dialog="openSupplementDialog"
            :toggle-issue-expand="toggleIssueExpand"
            @update:step2-supplement-dialog-visible="step2SupplementDialogVisible = $event"
          />
        </div>

        <!-- Step 3: 检测 - 方向/结构一致性检测 -->
        <div v-if="currentStep === 3" class="step-content">
          <a-card title="交付审核（门卫模式）">
            <a-alert type="info" style="margin-bottom: 16px">
              <template #title>抓大放小：只拦方向错误/内容为空/事实冲突</template>
              方向：{{ selectedDirection?.name }} | 框架：{{ selectedFramework?.name }}
            </a-alert>

            <div v-if="checkingDirection" style="text-align: center; padding: 40px">
              <a-spin :size="50" dot tip="正在审核..." />
            </div>

            <div v-else-if="directionCheckResult">
              <!-- 3次强制放行提示 -->
              <a-alert v-if="directionCheckMeta.force_passed" type="warning" style="margin-bottom: 16px">
                <template #title>⚠️ 系统检测 3 次未通过，已自动放行</template>
                建议手动检查后继续，或返回补充内容
              </a-alert>

              <!-- 阻断区：必须修复才能继续 -->
              <div v-if="blockIssues.length > 0" style="margin-bottom: 20px">
                <div :style="{ fontSize: '15px', fontWeight: 600, marginBottom: '12px', color: directionCheckMeta.force_passed ? '#ff7d00' : '#f53f3f' }">
                  {{ directionCheckMeta.force_passed ? '⚠️ 以下问题未修复（已强制放行）' : ' 需要修复（' + blockIssues.length + ' 项阻塞）' }}
                </div>
                <div v-for="(issue, i) in blockIssues" :key="'block-'+i" class="issue-card" style="margin-bottom: 12px">
                  <a-card :bordered="true" type="danger">
                    <template #title>
                      <a-space>
                        <span>🔴</span>
                        <span>{{ issue.title }}</span>
                        <a-tag color="red" size="small">阻塞</a-tag>
                      </a-space>
                    </template>
                    <div style="font-size: 13px; line-height: 1.6">{{ issue.description }}</div>
                    
                    <div style="margin-top: 12px">
                      <a-space>
                        <!-- 结构性问题：回退重选 -->
                        <a-button 
                          v-if="issue.category === 'direction' || issue.category === 'framework'"
                          size="small" 
                          status="warning"
                          @click="goBackToStep3"
                        >
                          回退重选
                        </a-button>
                        <!-- 内容级阻塞：编辑补充 -->
                        <a-button 
                          v-else
                          size="small" 
                          status="primary" 
                          @click="editSingleIssue(directionCheckResult.indexOf(issue))"
                        >
                          编辑补充
                        </a-button>
                        <a-button size="small" status="success" :loading="aiSingleIssueLoading" @click="aiGenerateSingleIssue(directionCheckResult.indexOf(issue))">
                          🤖 AI 补充
                        </a-button>
                      </a-space>
                      <div v-if="editingIssueIndex === directionCheckResult.indexOf(issue)" style="margin-top: 12px; padding: 12px; background: #f7f8fa; border-radius: 4px">
                        <a-textarea 
                          v-model="editingIssueContent" 
                          :placeholder="`针对「${issue.title}」补充内容...`"
                          :auto-size="{ minRows: 3, maxRows: 8 }"
                          style="margin-bottom: 8px"
                        />
                        <a-space>
                          <a-button type="primary" size="small" :loading="editingIssueLoading" @click="confirmSingleIssue(directionCheckResult.indexOf(issue))">
                            确认补充
                          </a-button>
                          <a-button size="small" @click="cancelEditIssue">取消</a-button>
                        </a-space>
                      </div>
                    </div>
                  </a-card>
                </div>
              </div>

              <!-- 建议区：不阻塞，可跳过 -->
              <div v-if="suggestIssues.length > 0" style="margin-bottom: 20px">
                <div style="font-size: 15px; font-weight: 600; color: #ff9a2e; margin-bottom: 12px">
                  💡 建议优化（{{ suggestIssues.length }} 项，不阻塞）
                </div>
                <div v-for="(issue, i) in suggestIssues" :key="'suggest-'+i" class="issue-card" style="margin-bottom: 12px">
                  <a-card :bordered="true" type="warning">
                    <template #title>
                      <a-space>
                        <span></span>
                        <span>{{ issue.title }}</span>
                        <a-tag color="orange" size="small">建议</a-tag>
                      </a-space>
                    </template>
                    <div style="font-size: 13px; line-height: 1.6">{{ issue.description }}</div>
                    
                    <div style="margin-top: 12px">
                      <a-space>
                        <a-button size="small" status="success" :loading="aiSingleIssueLoading" @click="aiGenerateSingleIssue(directionCheckResult.indexOf(issue))">
                          🤖 AI 补充
                        </a-button>
                      </a-space>
                    </div>
                  </a-card>
                </div>
              </div>

              <!-- 底部操作按钮 -->
              <div style="margin-top: 16px; text-align: center">
                <a-space>
                  <a-button 
                    type="primary" 
                    status="success" 
                    :disabled="hasErrors"
                    @click="currentStep = 5"
                  >
                    进入下一步 →
                  </a-button>
                  <a-button 
                    v-if="suggestIssues.length > 0"
                    status="warning"
                    @click="skipSuggestionsAndContinue"
                  >
                    跳过建议，继续 →
                  </a-button>
                </a-space>
                <div v-if="hasErrors" style="margin-top: 8px; color: #f53f3f; font-size: 13px">
                  请先修复所有阻塞项
                </div>
              </div>
            </div>

            <div v-else style="text-align: center; padding: 40px">
              <a-empty description="检测已自动触发，如未显示结果请重试" />
              <a-button type="primary" @click="runDirectionCheck" style="margin-top: 16px">
                重新检测
              </a-button>
            </div>
          </a-card>
        </div>

        <!-- Step 4: 结构推荐 -->
        <div v-if="currentStep === 4" class="step-content">
          <a-card title="推荐内容结构">
            <a-alert type="info" style="margin-bottom: 16px">
              <template #title>AI 推荐的文章结构</template>
              基于选定方向和框架，为您推荐以下结构：
            </a-alert>

            <div v-if="structuresLoading" style="text-align: center; padding: 40px">
              <a-spin :size="50" dot tip="正在推荐结构..." />
            </div>

            <div v-else-if="structures.length === 0" style="text-align: center; padding: 40px">
              <a-empty description="暂无推荐结构，请返回重试" />
            </div>

            <div v-else>
              <!-- 全局推荐横幅 -->
              <a-alert v-if="structures[0] && structures[0].confidence" type="info" style="margin-bottom: 16px; background: #e8f7ff; border-color: #b3d9ff">
                <template #message>
                  <div style="font-size: 13px">
                    💡 AI 推荐：<strong>{{ structures[0].name }}</strong>
                    <span v-if="structures[0].reason" style="margin-left: 8px; color: #86909c">{{ structures[0].reason }}</span>
                  </div>
                </template>
              </a-alert>

              <div v-for="(s, i) in structures" :key="i" class="structure-card" style="margin-bottom: 12px">
                <a-card :bordered="true" hoverable>
                  <template #title>
                    <span v-if="i === 0">🥇 </span>
                    <span v-else-if="i === 1"> </span>
                    <span v-else-if="i === 2">🥉 </span>
                    {{ s.name }}
                    <a-tag v-if="s.confidence === 'high'" color="green" style="margin-left: 8px">高匹配</a-tag>
                    <a-tag v-else-if="s.confidence === 'medium'" color="orange" style="margin-left: 8px">中匹配</a-tag>
                    <a-tag v-else color="gray" style="margin-left: 8px">低匹配</a-tag>
                    <a-tag :color="getCoverageColor(s.match_score || 0.7)" style="margin-left: 4px">
                      匹配 {{ ((s.match_score || 0.7) * 100).toFixed(0) }}%
                    </a-tag>
                  </template>
                  <div style="font-size: 13px; line-height: 1.6">{{ s.description }}</div>
                  
                  <!-- 单行推理信息 -->
                  <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #e5e6eb; font-size: 12px; color: #86909c; display: flex; flex-wrap: wrap; gap: 12px; align-items: center">
                    <span v-if="s.reason"> {{ s.reason }}</span>
                    <span v-if="s.source === 'general_knowledge'" style="color: #ff7d00">⚠️ 基于通用知识</span>
                  </div>
                  
                  <!-- 结构分段提示（如果有 sections） -->
                  <div v-if="s.sections?.length" style="margin-top: 8px; font-size: 12px; color: #86909c">
                    分段建议：{{ s.sections.map(sec => sec.name).join(' → ') }}
                  </div>
                  
                  <!-- 需要补充 -->
                  <div v-if="s.missing_content?.length || s.needs_supplement?.length" style="margin-top: 8px; font-size: 12px; color: #f53f3f">
                    需要补充：{{ [...(s.missing_content || []), ...(s.needs_supplement || [])].join('、') }}
                  </div>
                  
                  <a-button type="primary" status="success" style="margin-top: 12px" @click="selectStructure(s)">
                    选择此结构
                  </a-button>
                </a-card>
              </div>
            </div>
          </a-card>
        </div>

        <!-- Step 5: 提纲生成 -->
        <div v-if="currentStep === 5" class="step-content">
          <a-card title="写作提纲">
            <div v-if="outlineResult" class="outline-result">
              <!-- v2 格式：具名 section (对象) + source_tag + missing_items -->
              <div v-if="typeof outlineResult === 'object' && outlineResult !== null && !Array.isArray(outlineResult) && outlineResult.sections && typeof outlineResult.sections === 'object' && !Array.isArray(outlineResult.sections)">
                <div style="margin-bottom: 24px">
                  <h3 style="color: #1d2129; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 2px solid #e5e6eb">
                    📝 {{ outlineResult.title || '写作提纲' }}
                  </h3>
                  
                  <a-alert v-if="outlineResult.alignment_warning" type="warning" style="margin-bottom: 16px">
                    <template #title>跑题风险提示</template>
                    <div style="font-size: 13px; line-height: 1.6">{{ outlineResult.alignment_warning }}</div>
                  </a-alert>
                  
                  <div v-if="outlineResult.direction_alignment_score !== undefined" style="margin-bottom: 12px; display: flex; gap: 8px; align-items: center">
                    <a-tag size="large" :color="getAlignmentTagColor(outlineResult.direction_alignment_score)">
                      🎯 方向对齐 {{ (outlineResult.direction_alignment_score * 100).toFixed(0) }}%
                    </a-tag>
                    <a-link v-if="outlineResult.direction_alignment_reason" size="mini" @click="showOutlineAlignmentReason = !showOutlineAlignmentReason" style="font-size: 12px">
                      {{ showOutlineAlignmentReason ? '收起' : '展开' }}对齐说明
                    </a-link>
                  </div>
                  <div v-if="showOutlineAlignmentReason && outlineResult.direction_alignment_reason" style="margin-bottom: 16px; padding: 8px 12px; background: #f0f7ff; border-radius: 4px; font-size: 12px; color: #165dff; line-height: 1.6">
                    🎯 <strong>方向对齐说明：</strong>{{ outlineResult.direction_alignment_reason }}
                  </div>
                  
                  <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px">
                    <a-tag size="large" :color="getCompletenessStatusColor(outlineCompletenessStatus)">
                      {{ getCompletenessStatusLabel(outlineCompletenessStatus) }}
                    </a-tag>
                    <a-space>
                      <a-button :loading="loading" @click="loadOutline">
                        🔄 重新生成提纲
                      </a-button>
                      <a-button type="primary" status="success" :loading="outlineOneClickLoading" @click="outlineOneClickAiSupplement">
                        🤖 一键 AI 补充所有需补充素材
                      </a-button>
                    </a-space>
                  </div>
                  
                  <div v-if="outlineResult.missing_items?.length" style="margin-bottom: 20px; padding: 16px; background: #fff7e8; border-radius: 8px; border: 1px solid #ffbb96">
                    <div style="font-weight: 600; color: #d46b08; margin-bottom: 8px">⚠️ 需补充的字段（共 {{ outlineResult.missing_items.length }} 项）</div>
                    <div v-for="(item, idx) in outlineResult.missing_items" :key="idx" style="margin-bottom: 8px; padding: 10px; background: #fff; border-radius: 6px; font-size: 13px">
                      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px">
                        <span style="font-size: 12px; color: #86909c">{{ idx + 1 }}.</span>
                        <strong style="color: #4e5969">{{ item.field }}</strong>
                        <a-tag v-if="outlineResult.global_supplements?.[item.field]" size="mini" color="green">已补充</a-tag>
                      </div>
                      <div style="color: #4e5969; line-height: 1.6; padding-left: 20px; margin-bottom: 8px">
                        💡 {{ item.fill_guidance }}
                      </div>
                      <div v-if="outlineResult.global_supplements?.[item.field]" style="padding: 10px; background: #f7f8fa; border-radius: 4px; font-size: 13px; line-height: 1.7; color: #1d2129; border-left: 3px solid #00b42a">
                        <div style="font-size: 12px; color: #86909c; margin-bottom: 4px">🤖 AI 补充内容：</div>
                        <a-textarea
                          v-model="outlineResult.global_supplements[item.field]"
                          :auto-size="{ minRows: 2, maxRows: 6 }"
                          style="width: 100%"
                        />
                      </div>
                    </div>
                  </div>
                </div>
                
                <div v-for="(section, key) in outlineResult.sections" :key="key" class="section-card" style="margin-bottom: 16px; padding: 16px; background: #f7f8fa; border-radius: 8px"
                     :style="{ borderLeft: `4px solid ${getSourceTagColor(section.source_tag)}` }">
                  <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px">
                    <h4 style="color: #1d2129; margin: 0; font-size: 15px">
                      <span :style="{ color: getSourceTagColor(section.source_tag) }">{{ getSectionNumber(key) }}.</span> {{ section.title }}
                    </h4>
                    <a-tag v-if="section.source_tag" size="small" :color="getSourceTagTagColor(section.source_tag)">
                      {{ getSourceTagLabel(section.source_tag) }}
                    </a-tag>
                  </div>
                  <div v-if="section.content" style="margin-bottom: 8px; font-size: 13px; color: #4e5969; line-height: 1.6">
                    {{ section.content }}
                  </div>
                  
                  <div v-if="section.key_points?.length" style="margin-bottom: 12px">
                    <div style="font-weight: 600; color: #86909c; margin-bottom: 6px; font-size: 13px">核心要点：</div>
                    <ul style="margin: 0; padding-left: 20px; color: #4e5969; line-height: 1.8">
                      <li v-for="(point, pIdx) in section.key_points" :key="pIdx">{{ point }}</li>
                    </ul>
                  </div>
                  
                  <!-- 该版块关联的缺失项（按 section 分组） -->
                  <div v-if="getSectionMissingItems(key)?.length" style="margin-bottom: 12px; padding: 12px; background: #fff7e8; border-radius: 6px; border: 1px solid #ffbb96">
                    <div style="font-weight: 600; color: #d46b08; margin-bottom: 8px; font-size: 13px">⚠️ 本版块需补充（共 {{ getSectionMissingItems(key).length }} 项）</div>
                    <div v-for="(item, idx) in getSectionMissingItems(key)" :key="idx" style="margin-bottom: 8px; padding: 8px; background: #fff; border-radius: 4px; font-size: 13px">
                      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px">
                        <strong style="color: #4e5969">{{ item.field }}</strong>
                        <a-tag v-if="outlineResult.global_supplements?.[item.field]" size="mini" color="green">已补充</a-tag>
                      </div>
                      <div style="color: #4e5969; line-height: 1.5; padding-left: 4px; margin-bottom: 6px">
                        💡 {{ item.fill_guidance }}
                      </div>
                      <div v-if="outlineResult.global_supplements?.[item.field]" style="padding: 8px; background: #f7f8fa; border-radius: 4px; font-size: 13px; line-height: 1.6; color: #1d2129; border-left: 3px solid #00b42a">
                        <div style="font-size: 12px; color: #86909c; margin-bottom: 4px">🤖 AI 补充内容：</div>
                        <a-textarea
                          v-model="outlineResult.global_supplements[item.field]"
                          :auto-size="{ minRows: 2, maxRows: 6 }"
                          style="width: 100%"
                        />
                      </div>
                    </div>
                  </div>
                  
                  <div v-if="section.materials" style="display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 8px">
                    <div v-if="section.materials.has?.length" style="flex: 1; min-width: 200px">
                      <div style="font-weight: 600; color: #00b42a; margin-bottom: 4px; font-size: 13px">✅ 已有素材：</div>
                      <ul style="margin: 0; padding-left: 18px; color: #4e5969; font-size: 13px">
                        <li v-for="(mat, mIdx) in section.materials.has" :key="mIdx">{{ mat }}</li>
                      </ul>
                    </div>
                    <div v-if="section.materials.needs?.length" style="flex: 1; min-width: 200px">
                      <div style="font-weight: 600; color: #f53f3f; margin-bottom: 4px; font-size: 13px"> 需补充：</div>
                      <ul style="margin: 0; padding-left: 18px; color: #4e5969; font-size: 13px">
                        <li v-for="(mat, mIdx) in section.materials.needs" :key="mIdx">{{ mat }}</li>
                      </ul>
                    </div>
                  </div>
                  
                  <div v-if="section.word_count_estimate" style="text-align: right; color: #86909c; font-size: 12px">
                    预估字数：{{ section.word_count_estimate }} 字
                  </div>

                  <div style="margin-top: 12px; padding-top: 12px; border-top: 1px dashed #e5e6eb">
                    <a-button size="mini" type="text" @click="toggleSectionAiDialog(key)">
                      🤖 AI 补充素材
                    </a-button>
                    <div v-if="sectionAiDialogIndex === key" style="margin-top: 8px; padding: 12px; background: #f7f8fa; border-radius: 6px">
                      <div style="font-size: 12px; color: #86909c; margin-bottom: 8px">
                        输入补充需求，可同时选择知识库文件和上传文件作为参考
                      </div>
                      <a-textarea
                        v-model="sectionAiInput"
                        placeholder="输入补充需求，或留空由AI自动补充..."
                        :auto-size="{ minRows: 2, maxRows: 4 }"
                        style="margin-bottom: 8px"
                      />
                      <div style="display: flex; gap: 8px; margin-bottom: 8px; flex-wrap: wrap">
                        <div style="flex: 1; min-width: 200px">
                          <a-tree-select
                            v-model="sectionAiKbFiles"
                            :data="kbTreeData"
                            placeholder=" 知识库文件（可选）"
                            tree-checkable
                            allow-search
                            style="width: 100%"
                          />
                        </div>
                        <div style="flex: 1; min-width: 200px">
                          <a-upload
                            :auto-upload="false"
                            :show-file-list="true"
                            :limit="3"
                            @change="handleSectionAiUpload"
                            style="width: 100%"
                          >
                            <template #upload-button>
                              <a-button style="width: 100%">📁 上传参考文件</a-button>
                            </template>
                          </a-upload>
                        </div>
                      </div>
                      <a-space>
                        <a-button type="primary" size="small" :loading="sectionAiLoading" @click="aiSupplementSectionByKey(key)">
                          🤖 生成
                        </a-button>
                        <a-button size="small" @click="toggleSectionAiDialog(-1)">取消</a-button>
                      </a-space>
                      <div v-if="sectionAiResult" style="margin-top: 8px; padding: 8px; background: #e8f7ed; border-radius: 4px; font-size: 13px; line-height: 1.6; white-space: pre-wrap">
                        {{ sectionAiResult }}
                        <div style="margin-top: 8px">
                          <a-button size="mini" type="primary" @click="acceptSectionAiSuggestionByKey(key)">采纳</a-button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else style="background: #f7f8fa; padding: 16px; border-radius: 8px">
                <pre style="white-space: pre-wrap; line-height: 1.8; font-size: 14px; margin: 0">{{ typeof outlineResult === 'string' ? outlineResult : JSON.stringify(outlineResult, null, 2) }}</pre>
              </div>

              <!-- 字数选择 -->
              <div style="margin-top: 20px; padding: 16px; background: #f7f8fa; border-radius: 8px; border: 1px solid #e5e6eb">
                <div style="font-size: 13px; font-weight: 600; color: #1d2129; margin-bottom: 12px">📏 目标字数</div>
                <a-radio-group v-model="targetWordCount" type="button" size="large">
                  <a-radio :value="1000">1000字</a-radio>
                  <a-radio :value="1500">1500字</a-radio>
                  <a-radio :value="2000">2000字</a-radio>
                  <a-radio :value="3000">3000字</a-radio>
                  <a-radio :value="5000">5000字</a-radio>
                </a-radio-group>
                <div style="margin-top: 8px; font-size: 12px; color: #86909c">选择文章的目标字数，AI 将根据此字数生成内容</div>
              </div>

              <a-space style="margin-top: 24px">
                <a-button type="primary" status="success" @click="goToGenerateArticle">
                  📝 确认生成完整文章
                </a-button>
                <a-button type="primary" @click="exportOutline">
                  📥 导出提纲
                </a-button>
                <a-button @click="goBackToStructures">
                  ← 返回结构推荐
                </a-button>
              </a-space>
            </div>
            <div v-else-if="loading" style="text-align: center; padding: 40px">
              <a-spin :size="50" dot tip="正在生成提纲..." />
            </div>
            <div v-else style="text-align: center; padding: 40px">
              <a-empty description="暂无提纲">
                <template #image>
                  <icon-file style="font-size: 64px; color: #c9cdd4" />
                </template>
              </a-empty>
              <a-button type="primary" size="large" @click="loadOutline" style="margin-top: 16px">
                重新生成
              </a-button>
              <a-button @click="goBackToStructures" style="margin-top: 16px; margin-left: 8px">
                ← 返回结构推荐
              </a-button>
            </div>
          </a-card>
        </div>

        <!-- Step 6: 文章生成 -->
        <div v-if="currentStep === 6" class="step-content">
          <a-card title="完整文章">
            <div v-if="articleResult">
              <div style="margin-bottom: 24px">
                <h3 style="color: #1d2129; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 2px solid #e5e6eb">
                   {{ articleResult.title || '完整文章' }}
                </h3>
                <div style="display: flex; justify-content: center; gap: 32px; margin-bottom: 16px; padding: 12px; background: #f0f9ff; border-radius: 6px; font-size: 14px; color: #4e5969">
                  <span> 正文：<strong style="color: #1d2129">{{ totalWordCount }}</strong> 字</span>
                  <span>🎙️ 朗读：约 <strong style="color: #1d2129">{{ readingTime }}</strong> 分钟</span>
                </div>
                <div style="text-align: center; margin-bottom: 16px">
                  <a-space>
                    <a-button type="primary" status="success" :loading="articleOneClickLoading" @click="articleOneClickRegenerate">
                      🤖 一键重新生成全文
                    </a-button>
                    <a-button type="primary" @click="exportArticle">
                      📥 导出文章
                    </a-button>
                    <a-button type="primary" status="warning" @click="goToGenerateImage">
                      🖼️ 生成配图
                    </a-button>
                    <a-button @click="currentStep = 6">
                      ← 返回提纲
                    </a-button>
                  </a-space>
                </div>
              </div>

              <div v-for="(para, idx) in articleResult.paragraphs" :key="idx" style="margin-bottom: 16px; padding: 16px; border-left: 3px solid #3491fa; background: #f7f8fa; border-radius: 6px">
                <h4 style="color: #1d2129; margin-bottom: 12px">
                  {{ idx + 1 }}. {{ para.title }}
                </h4>
                <div style="font-size: 14px; line-height: 1.8; white-space: pre-wrap; color: #4e5969">
                  {{ para.content }}
                </div>
                <div style="text-align: right; color: #86909c; font-size: 12px; margin-top: 8px">
                  预估字数：{{ para.word_count || 0 }} 字
                </div>

                <div style="margin-top: 12px; padding-top: 12px; border-top: 1px dashed #e5e6eb">
                  <a-button size="mini" type="text" @click="toggleArticleAiDialog(idx)">
                    🤖 AI 调整本段
                  </a-button>
                  <div v-if="articleAiDialogIndex === idx" style="margin-top: 8px; padding: 12px; background: #fff; border-radius: 6px">
                    <div style="font-size: 12px; color: #86909c; margin-bottom: 8px">
                      输入调整需求，可同时选择知识库文件和上传文件作为参考
                    </div>
                    <a-textarea
                      v-model="articleAiInput"
                      placeholder="输入调整需求，或留空由AI自动调整..."
                      :auto-size="{ minRows: 2, maxRows: 4 }"
                      style="margin-bottom: 8px"
                    />
                    <div style="display: flex; gap: 8px; margin-bottom: 8px; flex-wrap: wrap">
                      <div style="flex: 1; min-width: 200px">
                        <a-tree-select
                          v-model="articleAiKbFiles"
                          :data="kbTreeData"
                          placeholder=" 知识库文件（可选）"
                          tree-checkable
                          allow-search
                          style="width: 100%"
                        />
                      </div>
                      <div style="flex: 1; min-width: 200px">
                        <a-upload
                          :auto-upload="false"
                          :show-file-list="true"
                          :limit="3"
                          @change="handleArticleAiUpload"
                          style="width: 100%"
                        >
                          <template #upload-button>
                            <a-button style="width: 100%">📁 上传参考文件</a-button>
                          </template>
                        </a-upload>
                      </div>
                    </div>
                    <a-space>
                      <a-button type="primary" size="small" :loading="articleAiLoading" @click="aiAdjustArticleParagraph(idx)">
                        🤖 重新生成
                      </a-button>
                      <a-button size="small" @click="toggleArticleAiDialog(-1)">取消</a-button>
                    </a-space>
                    <div v-if="articleAiResult" style="margin-top: 8px; padding: 8px; background: #e8f7ed; border-radius: 4px; font-size: 13px; line-height: 1.6; white-space: pre-wrap">
                      {{ articleAiResult }}
                      <div style="margin-top: 8px">
                        <a-button size="mini" type="primary" @click="acceptArticleAiSuggestion(idx)">采纳替换</a-button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div v-else-if="loading" style="text-align: center; padding: 40px">
              <a-spin :size="50" dot tip="正在生成完整文章..." />
            </div>
            <div v-else style="text-align: center; padding: 40px">
              <a-empty description="暂无文章内容">
                <template #image>
                  <icon-file style="font-size: 64px; color: #c9cdd4" />
                </template>
              </a-empty>
              <a-button type="primary" size="large" @click="goToGenerateArticle" style="margin-top: 16px">
                生成完整文章
              </a-button>
            </div>
          </a-card>
        </div>

        <!-- Step 7: 配图生成 -->
        <div v-if="currentStep === 7" class="step-content">
          <a-card title="生成配图">
            <div v-if="generatedImageUrl">
              <div style="text-align: center; margin-bottom: 24px">
                <a-space>
                  <a-button type="primary" @click="downloadGeneratedImage">
                     下载图片
                  </a-button>
                  <a-button @click="currentStep = 7">
                    ← 返回文章
                  </a-button>
                </a-space>
              </div>
              <div class="generated-image-container">
                <img :src="generatedImageUrl" class="generated-image" alt="生成的配图" />
              </div>
            </div>
            <div v-else-if="imageGenerating" style="text-align: center; padding: 60px 0">
              <a-spin :size="50" dot tip="正在生成配图..." />
              <div style="margin-top: 16px; color: #86909c; font-size: 13px">
                正在将文章内容转为可视化图片，请稍候...
              </div>
            </div>
            <div v-else style="text-align: center; padding: 60px 0">
              <a-empty description="尚未生成配图" />
              <div style="margin-top: 16px; padding: 16px; background: #f7f8fa; border-radius: 8px; max-width: 500px; margin-left: auto; margin-right: auto">
                <a-typography-text type="secondary" size="small">
                  将根据选中的框架和文章内容生成可视化配图
                </a-typography-text>
              </div>
              <a-space style="margin-top: 24px">
                <a-button type="primary" size="large" :loading="imageGenerating" @click="handleGenerateImage">
                  🖼️ 生成配图
                </a-button>
                <a-button size="large" @click="currentStep = 7">
                  ← 返回文章
                </a-button>
              </a-space>
            </div>
          </a-card>
        </div>
      </a-spin>
    </div>

    <!-- P1 预留：保存到领域知识库弹窗 -->
    <a-modal
      v-model:visible="showExportModal"
      title="保存到领域知识库？"
      :ok-text="exportingToDomain ? '保存中...' : '保存到知识库'"
      :ok-loading="exportingToDomain"
      @ok="handleExportToDomain"
      @cancel="skipExport"
    >
      <p>
        是否将本次补充内容保存到
        <a-select v-model="exportDomainTag" style="width: 180px; margin: 0 4px" :options="domainOptions" placeholder="选择领域" />
        领域知识库？
      </p>
      <p class="text-gray-500" style="font-size: 13px; margin-top: 8px">
        保存后，未来同类项目可自动复用这些内容
      </p>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed, nextTick, watch, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Message, Modal } from '@arco-design/web-vue'
import { useAppStore } from '../stores/app'
import { marked } from 'marked'
import {
  IconSearch,
  IconExclamationCircleFill,
  IconCloseCircleFill,
  IconCheckCircleFill,
  IconRobot,
  IconScan,
  IconArrowRight,
  IconFile,
  IconBook,
  IconBulb,
  IconRefresh,
} from '@arco-design/web-vue/es/icon'
import ThreeColumnWorkbench from '../components/workflow/ThreeColumnWorkbench.vue'
import StepSupplement from '../components/workflow/StepSupplement.vue'
import { useStep3Workbench } from '../composables/useStep3_Workbench'
import { useSession } from '../composables/useSession'
import {
  createWorkflowSession,
  getWorkflowSessionStatus,
  evaluateCompleteness,
  analyzeDirectionsV2,
  supplementStep1,
  matchFrameworksV2,
  supplementStep2,
  checkWorkflowDirection,
  fixWorkflowDirection,
  recommendStructures,
  supplementStep3,
  generateWorkflowOutline,
  generateFullArticle,
  listFolderFiles,
  aiAutoSupplement as apiAiAutoSupplement,
  aiPulseSupplement as apiAiPulseSupplement,
  aiInferSupplement as apiInferSupplement,
  smartSupplement as apiSmartSupplement,
  degradeSupplement as apiDegradeSupplement,
  supplementDraft as apiSupplementDraft,
  recordAnalyticsEvent,
  readFolderFile,
  addSupplement as apiAddSupplement,
  confirmSupplement as apiConfirmSupplement,
  listSupplements as apiListSupplements,
  generateDiagram as apiGenerateDiagram,
  mcpSuggest as apiMcpSuggest,
  mcpMatchFiles as apiMcpMatchFiles,
  mcpSearch as apiMcpSearch,
} from '../utils/api'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()

const loading = ref(false)
const { currentStep, sessionId } = useSession()
const collapsedSteps = ref({})
const mcpSummary = ref('')
const mcpFiles = ref([])
const kbTreeData = ref([])
const mcpTopic = ref('')

// V4.0 三列工作台
const {
  phase, streamingThinking, streamDone, confirmedSlots,
  slotMaterials, slotOutlines, writingPlans, slotRelations,
  editingSlot, showEditPanel, followupHistory, allSlotsConfirmed,
  preCheckResults, preCheckRunning,
  startStreamSlots, stopStream, updateSlot, removeSlot, addSlot,
  confirmAndFill, openEditPanel, closeEditPanel, saveWritingPlan,
  addMaterialToSlot, askFollowupQuestion, runPreCheck: runSlotPreCheck, adoptAlternative,
} = useStep3Workbench()

// 话题推荐
const topics = ref([])
const topicsLoading = ref(false)
const scannedFolders = ref([])
const fileCount = ref(0)

// 完整度评估
const completenessResult = ref(null)

// 显示用的完整度（处理后端可能返回的 0-1 小数格式）
// 返回 0-100 的整数百分比
const completenessPercent = computed(() => {
  if (!completenessResult.value) return 0
  const raw = completenessResult.value.completeness || 0
  // 确保返回 0-100 的整数
  if (raw <= 1 && raw > 0) {
    return Math.round(raw * 100)
  }
  // 已经是百分比格式，限制在 0-100 范围内
  return Math.min(Math.max(Math.round(raw), 0), 100)
})

// 补充后手动更新完整度 - 根据已补充的项数计算
const manualCompleteness = computed(() => {
  if (!completenessResult.value) return completenessPercent.value
  const missingCritical = completenessResult.value.missing_critical || []
  const total = missingCritical.length
  if (total === 0) return completenessPercent.value
  
  const supplemented = missingCritical.filter((_, idx) => isSupplemented(idx)).length
  const ratio = supplemented / total
  // 基于后端返回的完整度，加上补充带来的提升
  const baseCompleteness = completenessPercent.value
  const bonus = Math.round(ratio * (100 - baseCompleteness) * 0.5) // 补充最多提升50%
  return Math.min(baseCompleteness + bonus, 100)
})

// 显示用的完整度 - 优先使用手动计算的（如果有补充）
const displayCompleteness = computed(() => {
  if (!completenessResult.value) return 0
  const supplemented = completenessResult.value.missing_critical?.filter((_, idx) => isSupplemented(idx)).length || 0
  if (supplemented > 0) {
    return manualCompleteness.value
  }
  return completenessPercent.value
})

// 方向推荐
const directions = ref([])
const selectedDirection = ref(null)
const directionsLoading = ref(false)

// 关键缺失项补充弹窗（分步骤工作流）
const supplementModalVisible = ref(false)
const currentSupplementItem = ref('')
const currentSupplementIndex = ref(-1)
const isEditMode = ref(false)

// 需求2：编辑弹窗状态（左右分栏 + AI辅助）
const editModalVisible = ref(false)
const editOriginalContent = ref('')
const editNewContent = ref('')
const editAiSuggestion = ref('')
const editAiLoading = ref(false)
const editSaving = ref(false)

// 需求3：框架补充 AI 建议
const frameworkAiSuggestion = ref('')
const frameworkAiLoading = ref(false)
const frameworkSelectedIndex = ref(-1)

// 需求4：检测问题 AI 帮助
const issueAiHelp = ref({}) // { issueIndex: { suggestion, loading } }

// 需求5：结构补充 AI 辅助
const structureAiSuggestion = ref('')
const structureAiLoading = ref(false)

// 分步骤工作流状态
const supplementStep = ref(1) // 1=API检索 2=上下文推断 3=确认
const supplementApiLoading = ref(false)
const supplementApiCases = ref([])
const supplementApiSelectedCases = ref([])
const supplementInferLoading = ref(false)
const supplementInferResult = ref(null) // { content, inference_note }
const supplementSaving = ref(false)

// 批量操作状态
const batchAiPulseLoading = ref(false)
const batchManualLoading = ref(false)
const batchUnifiedLoading = ref(false)
const batchAiPulseModalVisible = ref(false)
const batchManualModalVisible = ref(false)
const batchAiPulseResults = ref([]) // [{ item, cases, saving }]
const batchManualTexts = ref({}) // { index: text }

// 统一补充弹窗状态（需求1：合并 API检索 + 推断）
const unifiedModalVisible = ref(false)
const unifiedModalStep = ref(1) // 1=API检索, 2=推断, 3=确认
const unifiedModalItem = ref('')
const unifiedModalItemIndex = ref(-1)
const unifiedApiCases = ref([])
const unifiedApiSelected = ref([])
const unifiedApiLoading = ref(false)
const unifiedInferLoading = ref(false)
const unifiedInferResult = ref(null)
const unifiedSaving = ref(false)

// 草稿模式状态（Step 3 起草用）
const draftModalVisible = ref(false)
const draftModalItem = ref('')
const draftModalItemIndex = ref(-1)
const draftContent = ref('')
const draftLoading = ref(false)
const draftSaving = ref(false)

// 旧版状态（保留兼容）
const supplementModalMethod = ref('text')
const supplementModalFile = ref([])
const supplementModalText = ref('')
const aiSupplementing = ref(false)
const extractingFileContent = ref(false)
const extractedFileContent = ref(false)
const extractedFileCount = ref(0)

// ArchGen v2.0: 智能补充状态
const smartSupplementResult = ref(null) // 存储智能补充结果
const smartSupplementLoading = ref(false)
const currentKnowledgeLevel = ref('L1') // 当前知识级别
const canDegrade = ref(false) // 是否可以降级
const degradationCount = ref(0) // 已降级次数
const maxDegradationCount = 2 // 最大降级次数

// 关键缺失项补充状态跟踪
const supplementContents = ref({}) // { index: { content, method, time } }

function isSupplemented(index) {
  return supplementContents.value[index] !== undefined
}

function getSupplementContent(index) {
  return supplementContents.value[index]?.content || ''
}

// 分步骤工作流：计算属性
const allSupplementApiCasesSelected = computed(() => {
  return supplementApiCases.value.length > 0 && supplementApiSelectedCases.value.length === supplementApiCases.value.length && supplementApiSelectedCases.value.every(v => v)
})

const anySupplementApiCaseSelected = computed(() => {
  return supplementApiSelectedCases.value.some(v => v)
})

const selectedSupplementCasesSummary = computed(() => {
  if (!supplementApiCases.value.length) return null
  const selected = supplementApiCases.value.filter((_, i) => supplementApiSelectedCases.value[i])
  if (!selected.length) return null
  return {
    count: selected.length,
    cases: selected.map(c => ({ title: c.title, source: c.source })),
  }
})

// 判断是否所有关键缺失项都已补充
const allCriticalSupplemented = computed(() => {
  if (!completenessResult.value) return false
  const missingCritical = completenessResult.value.missing_critical || []
  if (missingCritical.length === 0) return false
  return missingCritical.every((_, idx) => isSupplemented(idx))
})

// 步骤总结文案
const stepSummaries = computed(() => {
  const summaries = {}
  
  // Step 0: 选题
  if (selectedDirection.value?.name) {
    summaries[0] = selectedDirection.value.name
  } else if (topics.value.length > 0) {
    summaries[0] = `${topics.value.length} 个推荐方向`
  }
  
  // Step 1: 补充
  if (completenessResult.value?.missing_critical) {
    const supplemented = completenessResult.value.missing_critical.filter((_, idx) => isSupplemented(idx)).length
    summaries[1] = supplemented > 0 ? `补充了${supplemented}项` : ''
  }
  
  // Step 2: 框架
  if (selectedFramework.value?.name) {
    summaries[2] = selectedFramework.value.name
  }
  
  // Step 3: 检测
  if (directionCheckResult.value && Array.isArray(directionCheckResult.value)) {
    const problemCount = directionCheckResult.value.filter(issue => issue.type !== 'pass').length
    summaries[3] = problemCount > 0 ? `${problemCount}个问题` : '通过'
  }
  
  // Step 4: 结构
  if (selectedStructure.value?.name) {
    summaries[4] = selectedStructure.value.name
  }
  
  // Step 5: 提纲
  if (outlineResult.value?.sections) {
    summaries[5] = `${outlineResult.value.sections.length} 个章节`
  }
  
  // Step 6: 文章
  if (articleResult.value?.paragraphs) {
    const wordCount = articleResult.value.paragraphs.reduce((sum, p) => sum + (p.word_count || 0), 0)
    summaries[6] = wordCount > 0 ? `${wordCount} 字` : ''
  }
  
  // Step 7: 配图
  if (generatedImageUrl.value) {
    summaries[7] = '已生成'
  }
  
  return summaries
})

// 步骤详细内容（展开时显示）
const stepDetails = computed(() => {
  const details = {}
  
  // Step 0: 选题
  if (selectedDirection.value?.name) {
    details[0] = `已选题：「${selectedDirection.value.name}」`
    if (selectedDirection.value.description) {
      details[0] += `\n说明：${selectedDirection.value.description}`
    }
  }
  
  // Step 1: 补充
  if (completenessResult.value?.missing_critical) {
    const total = completenessResult.value.missing_critical.length
    const done = completenessResult.value.missing_critical.filter((_, idx) => isSupplemented(idx)).length
    details[1] = `补充进度：${done}/${total} 项`
    if (completenessResult.value.supplement_strategy) {
      details[1] += `\n策略：${completenessResult.value.supplement_strategy}`
    }
  }
  
  // Step 2: 框架
  if (selectedFramework.value?.name) {
    details[2] = `已选框架：「${selectedFramework.value.name}」`
    if (selectedFramework.value.description) {
      details[2] += `\n说明：${selectedFramework.value.description}`
    }
  }
  
  // Step 3: 检测
  if (directionCheckResult.value && Array.isArray(directionCheckResult.value)) {
    const passCount = directionCheckResult.value.filter(i => i.type === 'pass').length
    const warnCount = directionCheckResult.value.filter(i => i.type === 'warning').length
    const failCount = directionCheckResult.value.filter(i => i.type === 'fail').length
    details[3] = `通过 ${passCount} 项，警告 ${warnCount} 项，未通过 ${failCount} 项`
    const firstFail = directionCheckResult.value.find(i => i.type !== 'pass')
    if (firstFail) {
      details[3] += `\n主要问题：${firstFail.message || ''}`
    }
  }
  
  // Step 4: 结构
  if (selectedStructure.value?.name) {
    details[4] = `已选结构：「${selectedStructure.value.name}」`
    if (selectedStructure.value.description) {
      details[4] += `\n说明：${selectedStructure.value.description}`
    }
  }
  
  // Step 5: 提纲
  if (outlineResult.value?.sections) {
    const sections = outlineResult.value.sections
    details[5] = `共 ${sections.length} 个章节`
    sections.forEach((s, i) => {
      details[5] += `\n  ${i + 1}. ${s.title || s.name || ''}`
    })
  }
  
  // Step 6: 文章
  if (articleResult.value) {
    const title = articleResult.value.title || ''
    const paragraphs = articleResult.value.paragraphs || []
    const wordCount = paragraphs.reduce((sum, p) => sum + (p.word_count || 0), 0)
    details[6] = `标题：${title}`
    details[6] += `\n段落数：${paragraphs.length} 个`
    details[6] += `\n总字数：${wordCount} 字`
  }
  
  // Step 7: 配图
  if (generatedImageUrl.value) {
    details[7] = '配图已生成'
    if (selectedFramework.value?.name) {
      details[7] += `\n框架：${selectedFramework.value.name}`
    }
  }
  
  return details
})

// 步骤名称（V4 三列工作台：5 步）
const stepNames = ['选题', '补充', '分析工作台', '文章', '配图']

// 切换步骤折叠状态
function toggleStepCollapse(stepIndex) {
  collapsedSteps.value[stepIndex] = !collapsedSteps.value[stepIndex]
}

// 分步骤工作流：打开补充弹窗（触发 API 检索）
async function openSupplementModal(index) {
  const items = completenessResult.value.missing_critical || []
  if (index >= items.length) return
  
  currentSupplementItem.value = items[index]
  currentSupplementIndex.value = index
  supplementModalVisible.value = true
  supplementStep.value = 1
  
  // 重置状态
  supplementApiCases.value = []
  supplementApiSelectedCases.value = []
  supplementInferResult.value = null
  
  // 检查是否已通过批量检索获取过结果
  const batchResult = batchAiPulseResults.value.find(r => r.item === currentSupplementItem.value)
  if (batchResult && !batchResult.loading && batchResult.cases) {
    // 直接使用批量检索结果，避免重复搜索
    supplementApiCases.value = batchResult.cases
    supplementApiSelectedCases.value = batchResult.cases.map(() => false)
    // 如果批量搜索没找到结果，跳过API步骤直接进入推断
    if (batchResult.cases.length === 0) {
      Message.info('该缺失项已通过批量检索搜索过，未找到相关案例，直接进入 AI 推断...')
      supplementStep.value = 2
      await goToStep2NoCases()
      return
    }
  } else {
    // 没有批量结果，执行单独检索
    await runSupplementApiSearch()
  }
}

// Step 1: API 检索
async function runSupplementApiSearch() {
  supplementApiLoading.value = true
  try {
    const keyword = currentSupplementItem.value.substring(0, 10)
    const res = await apiAiPulseSupplement(sessionId.value, currentSupplementItem.value, [keyword])
    console.log('AI-Pulse API 响应:', res.data)
    if (res.data.code === 0) {
      const cases = res.data.data?.cases || []
      console.log('解析到的案例数:', cases.length)
      supplementApiCases.value = cases
      supplementApiSelectedCases.value = cases.map(() => false)
    } else {
      console.warn('API 返回错误:', res.data.msg)
    }
  } catch (err) {
    console.error('API 检索失败:', err)
    Message.error('API 检索失败: ' + err.message)
  } finally {
    supplementApiLoading.value = false
    console.log('API 检索完成，案例数:', supplementApiCases.value.length)
  }
}

// 手动补充：直接打开文本输入弹窗
function openManualSupplement(index) {
  const items = completenessResult.value.missing_critical || []
  if (index >= items.length) return
  
  currentSupplementItem.value = items[index]
  currentSupplementIndex.value = index
  isEditMode.value = false
  supplementModalMethod.value = 'text'
  supplementModalText.value = ''
  supplementModalVisible.value = true
}

const toggleSupplementApiSelectAll = () => {
  const newState = !allSupplementApiCasesSelected.value
  supplementApiSelectedCases.value = Array(supplementApiCases.value.length).fill(newState)
}

// Step 1 → Step 2: 确认选中案例，进入推断
async function goToStep2() {
  supplementStep.value = 2
  supplementInferLoading.value = true
  
  try {
    // 获取已选案例
    const selectedCases = supplementApiCases.value.filter((_, i) => supplementApiSelectedCases.value[i])
    
    // 调用后端推断 API
    const res = await apiAiAutoSupplement(
      sessionId.value,
      currentSupplementItem.value,
      mcpSummary.value,
      selectedCases.map(c => ({ title: c.title, summary: c.summary, source: c.source })),
    )
    
    if (res.data.code === 0) {
      supplementInferResult.value = {
        content: res.data.data.content || '',
        inference_note: res.data.data.inference_note || '基于 MCP 摘要和 API 案例推断',
      }
    } else {
      Message.error('AI 推断失败: ' + (res.data.msg || '未知错误'))
    }
  } catch (e) {
    Message.error('AI 推断失败: ' + e.message)
  } finally {
    supplementInferLoading.value = false
  }
}

// Step 1 → Step 2（无 API 案例，直接推断）
async function goToStep2NoCases() {
  supplementStep.value = 2
  supplementInferLoading.value = true
  
  try {
    const res = await apiAiAutoSupplement(
      sessionId.value,
      currentSupplementItem.value,
      mcpSummary.value,
      [], // 无 API 案例
    )
    
    if (res.data.code === 0) {
      supplementInferResult.value = {
        content: res.data.data.content || '',
        inference_note: res.data.data.inference_note || '仅基于 MCP 摘要推断（无 API 案例）',
      }
    } else {
      Message.error('AI 推断失败: ' + (res.data.msg || '未知错误'))
    }
  } catch (e) {
    Message.error('AI 推断失败: ' + e.message)
  } finally {
    supplementInferLoading.value = false
  }
}

// Step 2 → Step 3: 确认内容
function goToStep3() {
  if (!supplementInferResult.value?.content) {
    Message.warning('推断结果为空，请重试')
    return
  }
  supplementStep.value = 3
}

// Step 3: 确认使用，保存补充内容
async function confirmSupplementStep3() {
  if (!supplementInferResult.value?.content) {
    Message.warning('内容为空，无法保存')
    return
  }
  
  supplementSaving.value = true
  try {
    // 保存到知识库
    const res = await apiAddSupplement(
      sessionId.value,
      'supplement',
      currentSupplementItem.value,
      supplementInferResult.value.content,
      'ai-auto',
      { inference_note: supplementInferResult.value.inference_note },
      [],
    )
    
    if (res.data.code === 0) {
      // 确认补充
      const suppId = res.data.data.supplement_id
      await apiConfirmSupplement(sessionId.value, suppId)
      
      // 标记缺失项为已补充
      supplementContents.value[currentSupplementIndex.value] = {
        content: supplementInferResult.value.content,
        method: 'ai-auto',
        time: new Date().toLocaleString(),
      }
      
      Message.success('补充内容已保存！')
      supplementModalVisible.value = false
      
      // 重新评估完整度
      await reEvaluateCompleteness()
    } else {
      Message.error('保存失败: ' + (res.data.msg || '未知错误'))
    }
  } catch (e) {
    Message.error('保存失败: ' + e.message)
  } finally {
    supplementSaving.value = false
  }
}

function closeSupplementModal() {
  supplementModalVisible.value = false
  supplementStep.value = 1
  supplementApiCases.value = []
  supplementApiSelectedCases.value = []
  supplementInferResult.value = null
}

// ===== 需求2：编辑弹窗（左右分栏 + AI辅助） =====

// 需求2：打开编辑弹窗（显示原有内容 + 左右分栏）
function openEditSupplementModal(index) {
  console.log('========================================')
  console.log('🔴 [DEBUG] openEditSupplementModal 被调用')
  console.log('🔴 编辑索引:', index)
  console.log('========================================')
  
  const items = completenessResult.value.missing_critical || []
  if (index >= items.length) return
  
  currentSupplementItem.value = items[index]
  currentSupplementIndex.value = index
  
  // 获取原有内容
  editOriginalContent.value = getSupplementContent(index)
  editNewContent.value = editOriginalContent.value
  editAiSuggestion.value = ''
  
  editModalVisible.value = true
  Message.info('编辑模式：左侧为原有内容，右侧为编辑区')
}

// 需求2：AI 辅助编辑（基于原有内容 + 上下文生成优化建议）
async function aiAssistEdit() {
  console.log('========================================')
  console.log('🔴 [DEBUG] aiAssistEdit 被调用')
  console.log('🔴 缺失项:', currentSupplementItem.value)
  console.log('========================================')
  
  editAiLoading.value = true
  try {
    // 调用 AI 生成优化建议
    const res = await apiInferSupplement(sessionId.value, currentSupplementItem.value, {
      existing_content: editOriginalContent.value,
      mcp_summary: mcpSummary.value,
    })
    
    if (res.data.code === 0 && res.data.data?.content) {
      editAiSuggestion.value = res.data.data.content
      Message.success('AI 优化建议已生成')
    } else {
      Message.error('AI 辅助失败: ' + (res.data.msg || '未知错误'))
    }
  } catch (e) {
    console.error('AI 辅助异常:', e)
    Message.error('AI 辅助失败: ' + e.message)
  } finally {
    editAiLoading.value = false
  }
}

// 需求2：应用 AI 建议（将 AI 建议填充到编辑区）
function applyAiSuggestion() {
  editNewContent.value = editAiSuggestion.value
  Message.success('已应用 AI 建议')
}

// 需求2：保存编辑
async function saveEditedSupplement() {
  console.log('========================================')
  console.log(' [DEBUG] saveEditedSupplement 被调用')
  console.log('🔴 新内容长度:', editNewContent.value.length)
  console.log('========================================')
  
  if (!editNewContent.value.trim()) {
    Message.warning('编辑内容不能为空')
    return
  }
  
  editSaving.value = true
  try {
    const idx = currentSupplementIndex.value
    const addRes = await apiAddSupplement(
      sessionId.value,
      'text',
      currentSupplementItem.value,
      editNewContent.value,
      'manual-edit',
      { original_content: editOriginalContent.value },
      [],
    )
    const suppId = addRes.data.data.supplement_id
    await apiConfirmSupplement(sessionId.value, suppId)
    
    // 更新本地状态
    supplementContents.value[idx] = {
      content: editNewContent.value.substring(0, 100) + '...',
      method: 'manual-edit',
      time: new Date().toLocaleString(),
    }
    
    editModalVisible.value = false
    Message.success('编辑已保存')
    
    // 重新评估完整度
    await reEvaluateCompleteness()
  } catch (e) {
    console.error('保存失败:', e)
    Message.error('保存失败: ' + e.message)
  } finally {
    editSaving.value = false
  }
}

// 需求2：关闭编辑弹窗
function closeEditModal() {
  editModalVisible.value = false
  editOriginalContent.value = ''
  editNewContent.value = ''
  editAiSuggestion.value = ''
}

// ===== 结束编辑弹窗功能 =====

// 补充1
const supplement1Method = ref('form')
const supplement1File = ref([])
const supplement1Text = ref('')
const supplement1Form = reactive({
  targetAudience: '',
  scenarios: [],
  expectedBenefit: '',
  otherInfo: '',
})
const supplement1Result = ref(null)

// 框架推荐
const frameworks = ref([])
const selectedFramework = ref(null)
const frameworksMode = ref('premium')
const frameworksBanner = ref('')
const frameworksLoading = ref(false)
const expandedWarnings = ref({})

// 补充2
const supplement2Method = ref('text')
const supplement2File = ref([])
const supplement2Text = ref('')
const pendingSupplementData = ref(null)
const supplement2Form = reactive({
  painPoint: '',
  solution: '',
  pitfalls: '',
})

// 补充2 衍生状态
const supplement2Html = computed(() => {
  if (!supplement2Text.value) return ''
  try { return marked.parse(supplement2Text.value, { breaks: true, async: false }) }
  catch (e) { return supplement2Text.value }
})
const supplementConfirmed = ref(false)
const materialPool = ref([])
const step2SupplementDialogVisible = ref(false)
const step2SupplementDialogRef = ref(null)
const lastSupplementMeta = ref(null)

// 预检测相关状态
const preCheckResult = ref(null)
const preCheckLoading = ref(false)
const expandedIssues = ref(new Set())
const aiAutoSupplementLoading = ref(false)
const supplementLoading = ref(false)
const supplementAllLoading = ref(false)

// 方向检测
const checkingDirection = ref(false)
const directionCheckResult = ref(null)
const directionCheckMeta = ref({ force_passed: false, ready_for_next: true, check_count: 0, overall_score: 0 })
const fixingIssueIndex = ref(-1)
const editingIssueIndex = ref(-1)
const editingIssueContent = ref('')
const editingIssueLoading = ref(false)
const aiSingleIssueLoading = ref(false)
const hasErrors = computed(() => {
  if (!directionCheckResult.value) return false
  // 强制放行时不阻塞
  if (directionCheckMeta.value.force_passed) return false
  // 门卫模式：只有 block 级别才阻塞
  return directionCheckResult.value.some(issue => issue.level === 'block' || issue.type === 'error')
})

// 分两区：阻塞项 vs 建议项
const blockIssues = computed(() => {
  if (!directionCheckResult.value) return []
  return directionCheckResult.value.filter(issue => issue.level === 'block' || issue.type === 'error')
})

const suggestIssues = computed(() => {
  if (!directionCheckResult.value) return []
  return directionCheckResult.value.filter(issue => issue.level === 'suggest' || (issue.type === 'warning' && issue.level !== 'block'))
})

// AI-Pulse 补充
const aiPulseLoading = ref(false)
const aiPulseCases = ref([])
const aiPulseSelectedCases = ref([])
const aiPulseKeywords = ref([])

// P0-2: 预加载 AI-Pulse 案例（基于方向名称，广度覆盖）
const preloadingApiCases = ref(false)
const preloadedApiCases = ref([])

const preloadApiCases = async () => {
  if (preloadedApiCases.value.length > 0) return
  if (!selectedDirection.value) return
  preloadingApiCases.value = true
  try {
    // 基于方向名称搜索（广度覆盖）
    const directionName = selectedDirection.value.name || 'AI'
    const res = await apiAiPulseSupplement(sessionId.value, directionName, [directionName.substring(0, 10)])
    if (res.data.code === 0) {
      const cases = res.data.data.cases || []
      preloadedApiCases.value = cases
      
      if (cases.length > 0) {
        let savedCount = 0
        for (const c of cases) {
          const caseText = `【${c.title}】\n来源：${c.source}\n评分：${c.score}\n摘要：${c.summary}\n链接：${c.url}`
          try {
            const addRes = await apiAddSupplement(
              sessionId.value,
              'case',
              c.category || directionName,
              caseText,
              'ai-pulse',
              { title: c.title, source: c.source, score: c.score, url: c.url },
              c.tags || [],
            )
            const suppId = addRes.data.data.supplement_id
            await apiConfirmSupplement(sessionId.value, suppId)
            savedCount++
          } catch (e) {
            console.warn('预保存 AI-Pulse 案例失败:', e)
          }
        }
        if (savedCount > 0) {
          Message.success(`已预加载 ${savedCount} 个相关案例，AI 补充时将自动使用`)
        }
      }
    }
  } catch (err) {
    console.warn('预加载 AI-Pulse 案例失败:', err)
  } finally {
    preloadingApiCases.value = false
  }
}

// 结构推荐
const structures = ref([])
const structuresLoading = ref(false)
const selectedStructure = ref(null)

// 提纲
const outlineResult = ref(null)
const showOutlineAlignmentReason = ref(false)
const targetWordCount = ref(2000) // 默认2000字

// 提纲段落 AI 补充
const sectionAiDialogIndex = ref(-1)
const sectionAiInput = ref('')
const sectionAiLoading = ref(false)
const sectionAiResult = ref('')
const outlineOneClickLoading = ref(false)

const sectionAiKbFiles = ref([])
const sectionAiUploadFiles = ref([])

// 完整文章
const articleResult = ref(null)

// 正文字数统计（所有段落字数之和）
const totalWordCount = computed(() => {
  if (!articleResult.value?.paragraphs) return 0
  return articleResult.value.paragraphs.reduce((sum, p) => sum + (p.word_count || 0), 0)
})

// 朗读时间（按每分钟 300 字计算）
const readingTime = computed(() => {
  const minutes = Math.ceil(totalWordCount.value / 300)
  return minutes < 1 ? 1 : minutes
})

const articleAiDialogIndex = ref(-1)
const articleAiInput = ref('')
const articleAiKbFiles = ref([])
const articleAiUploadFiles = ref([])
const articleAiLoading = ref(false)
const articleAiResult = ref('')
const articleOneClickLoading = ref(false)

// 生成配图
const generatedImageUrl = ref('')
const imageGenerating = ref(false)

// 知识库收藏弹窗（P1 预留）
const showExportModal = ref(false)
const exportDomainTag = ref('')
const exportingToDomain = ref(false)

const domainOptions = [
  { label: 'AI 效率工具', value: 'ai-efficiency' },
  { label: '商业分析', value: 'business-analysis' },
  { label: '产品设计', value: 'product-design' },
  { label: '运营优化', value: 'operations' },
  { label: '个人成长', value: 'personal-growth' },
  { label: '其他', value: 'other' },
]

onMounted(async () => {
  let isMounted = true

  // 从路由参数获取 MCP 摘要和文件列表
  mcpSummary.value = route.query.summary || ''
  const rawFiles = route.query.files || '[]'
  try {
    mcpFiles.value = JSON.parse(rawFiles)
  } catch (e) {
    mcpFiles.value = []
  }

  const existingSessionId = route.query.sessionId || ''

  // 从 MCPSearchView 进入: 创建 session, 读取 MCP 素材
  if (route.query.folders && !existingSessionId) {
    try {
      const res = await createWorkflowSession()
      if (!isMounted) return
      sessionId.value = res.data.data.session_id

      // 解析 folders 参数
      let folders = []
      try {
        folders = JSON.parse(route.query.folders || '[]')
      } catch (e) { folders = [] }

      // 设置主题
      const topicName = route.query.topic || ''
      if (topicName) {
        mcpTopic.value = topicName
        selectedDirection.value = { name: topicName }
        try {
          await supplementStep1(sessionId.value, topicName, {})
          console.log('✅ 方向已保存到后端 session:', topicName)
        } catch (e) {
          console.warn('保存方向失败:', e)
        }
      }

      // 读取 MCP 选中文件夹的内容，填充素材
      if (folders.length > 0) {
        try {
          if (topicName) {
            // 有主题：使用 apiMcpMatchFiles 获取主题相关的文件及内容
            const matchRes = await apiMcpMatchFiles({
              topic: topicName,
              folders,
            })
            if (matchRes.data?.code === 0 && matchRes.data.data) {
              const matchData = matchRes.data.data
              mcpFiles.value = (matchData.matched_files || []).map(f => ({
                name: f.name || '',
                content: f.content || '',
              }))
              mcpSummary.value = `已搜索「${topicName}」相关素材 ${matchData.total || mcpFiles.value.length} 篇`
              console.log('📂 MCP 匹配素材已加载:', { topic: topicName, matched: mcpFiles.value.length, total: matchData.total })
            } else {
              // 降级：读取所有文件
              const allFiles = []
              for (const folder of folders) {
                try {
                  const folderRes = await listFolderFiles(folder)
                  if (folderRes.data?.code === 0 && folderRes.data.data) {
                    allFiles.push(...folderRes.data.data.map(f => (typeof f === 'string' ? f : f.path || f.name || '')))
                  }
                } catch (e) { /* skip */ }
              }
              mcpFiles.value = allFiles
              mcpSummary.value = `已选择 ${folders.length} 个文件夹，共 ${allFiles.length} 个文件（后端搜索降级）`
            }
          } else {
            // 无主题：读取所有文件
            const allFiles = []
            const sampleContents = []
            for (const folder of folders) {
              try {
                const folderRes = await listFolderFiles(folder)
                if (folderRes.data?.code === 0 && folderRes.data.data) {
                  const files = folderRes.data.data || []
                  allFiles.push(...files.map(f => (typeof f === 'string' ? f : f.path || f.name || '')))
                  // 读取前 3 个文件内容作为摘要
                  const textFiles = files.filter(f => {
                    const name = (f.name || f.path || '').toLowerCase()
                    return name.endsWith('.md') || name.endsWith('.txt') || name.endsWith('.json')
                  }).slice(0, 3)
                  for (const f of textFiles) {
                    try {
                      const filePath = typeof f === 'string' ? f : f.path
                      const contentRes = await readFolderFile(folder, filePath)
                      if (contentRes.data?.code === 0 && contentRes.data.data?.content) {
                        const text = contentRes.data.data.content.slice(0, 800)
                        sampleContents.push(text)
                      }
                    } catch (e) { /* skip single file read errors */ }
                  }
                }
              } catch (e) { console.warn('读取文件夹失败:', folder, e) }
            }
            mcpFiles.value = allFiles
            if (sampleContents.length > 0) {
              mcpSummary.value = sampleContents.join('\n\n')
            } else {
              mcpSummary.value = `已选择 ${folders.length} 个文件夹，共 ${allFiles.length} 个文件`
            }
            console.log('📂 MCP 素材已加载:', { files: allFiles.length, summaryLen: mcpSummary.value.length })
          }
        } catch (e) {
          console.error('加载 MCP 素材失败:', e)
        }
      }

      // 有主题则直接进入 Step 1（补充），否则 Step 0（选题）
      currentStep.value = topicName ? 1 : 0
      if (!topicName) {
        await loadTopics()
      }
    } catch (e) {
      if (isMounted) Message.error('创建会话失败: ' + e.message)
      return
    }
    // 加载知识库文件树
    const settings = JSON.parse(localStorage.getItem('archgen_settings') || '{}')
    const kbPath = settings.knowledgeBasePath || '/home/admin/Desktop/AI 博主'
    try {
      const res = await listFolderFiles(kbPath)
      if (!isMounted) return
      if (res.data.code === 0) {
        kbTreeData.value = convertToTreeData(res.data.data)
      }
    } catch (e) {
      console.error('加载知识库文件失败:', e)
    }
    return
  }

  if (existingSessionId) {
    // 从 TopicSuggestView 跳转过来，使用已有的 session
    sessionId.value = existingSessionId
    // 设置已选择的主题（方向）
    const topicName = route.query.topic || ''
    if (topicName) {
      mcpTopic.value = topicName
      selectedDirection.value = { name: topicName }
      // 保存方向到后端 session
      try {
        await supplementStep1(sessionId.value, topicName, {})
        console.log('✅ 方向已保存到后端 session:', topicName)
        // 预加载框架推荐
        loadFrameworks()
      } catch (e) {
        console.warn('保存方向到 session 失败:', e)
      }
    }
    // 现有 session，从 Step 1（框架）开始
    currentStep.value = 1
  }

  // 加载知识库文件树
  const settings = JSON.parse(localStorage.getItem('archgen_settings') || '{}')
  const kbPath = settings.knowledgeBasePath || '/home/admin/Desktop/AI 博主'
  try {
    const res = await listFolderFiles(kbPath)
    if (!isMounted) return
    if (res.data.code === 0) {
      kbTreeData.value = convertToTreeData(res.data.data)
    }
  } catch (e) {
    console.error('加载知识库文件失败:', e)
  }

  // 恢复后端 session 中的框架信息（防止页面刷新后丢失）
  try {
    const sessionRes = await getWorkflowSessionStatus(sessionId.value)
    if (sessionRes.data.code === 0 && sessionRes.data.data?.step2?.selected_framework) {
      const fwData = sessionRes.data.data.step2.selected_framework
      // 后端可能返回字符串或对象
      if (typeof fwData === 'string') {
        // 旧格式：只有名称字符串
        selectedFramework.value = {
          name: fwData,
          key: FRAMEWORK_NAME_TO_KEY[fwData] || null,
        }
      } else if (typeof fwData === 'object') {
        // 新格式：包含 name 和 key
        selectedFramework.value = {
          name: fwData.name || '',
          key: fwData.key || FRAMEWORK_NAME_TO_KEY[fwData.name] || null,
        }
      }
      console.log('✅ 从后端 session 恢复框架:', selectedFramework.value)
    }
  } catch (e) {
    console.warn('恢复框架信息失败:', e)
  }
})

onUnmounted(() => {
  // 清理：防止异步操作在组件卸载后执行
})

// 监听步骤变化，进入步骤2时自动触发槽位流式推理
watch(currentStep, (newStep) => {
  // V4.0: 进入三列分析工作台时自动启动流式推理
  if (newStep === 2) {
    phase.value = 'init'
    const topic = selectedDirection.value?.name || mcpTopic.value || 'AI 写作'
    const summary = mcpSummary.value || ''
    console.log('🚀 开始调用 startStreamSlots:', { topic, summary, sessionId: sessionId.value })
    startStreamSlots(topic, summary)
  }
})

function convertToTreeData(items) {
  return (items || []).map(item => ({
    key: item.path,
    title: item.name,
    isLeaf: item.type === 'file',
    children: item.type === 'folder' && item.children ? convertToTreeData(item.children) : undefined,
  }))
}

function getCompletenessColor(score) {
  if (score >= 80) return '#00b42a'
  if (score >= 60) return '#f7ba1e'
  return '#f53f3f'
}

function getScoreColor(score) {
  if (score >= 80) return '#00b42a'
  if (score >= 60) return '#f7ba1e'
  return '#f53f3f'
}

function getScoreTagColor(score) {
  if (score >= 80) return 'green'
  if (score >= 60) return 'orange'
  return 'red'
}

function getScoreLabel(score) {
  if (score >= 80) return '素材充足'
  if (score >= 60) return '需补充后推进'
  return '素材不足'
}

function getReverseScoreColor(score) {
  // 缺失度越高越红，越低越绿（反向）
  if (score >= 80) return '#f53f3f'
  if (score >= 50) return '#f7ba1e'
  return '#00b42a'
}

function getCoverageColor(coverage) {
  if (coverage >= 0.7) return 'green'
  if (coverage >= 0.5) return 'arcoblue'
  return 'gray'
}

function getIssueColor(type) {
  if (type === 'pass') return '#00b42a'
  if (type === 'warning') return '#f7ba1e'
  return '#f53f3f'
}

function getIssueTagColor(type) {
  if (type === 'pass') return 'green'
  if (type === 'warning') return 'warning'
  return 'red'
}

function getSourceTagColor(tag) {
  switch(tag) {
    case 'anchored': return '#00b42a'
    case 'derived': return '#165dff'
    case 'missing': return '#f53f3f'
    default: return '#86909c'
  }
}

function getAlignmentColor(score) {
  const s = Number(score) || 0
  if (s >= 0.8) return '#00b42a'
  if (s >= 0.7) return '#86c34a'
  if (s >= 0.6) return '#f7ba1e'
  return '#c9cdd4'
}

function getAlignmentTagColor(score) {
  const s = Number(score) || 0
  if (s >= 0.8) return 'green'
  if (s >= 0.7) return 'arcoblue'
  if (s >= 0.6) return 'orange'
  return 'gray'
}

function getAlignmentBgColor(score) {
  const s = Number(score) || 0
  if (s >= 0.8) return '#f6ffed'
  if (s >= 0.7) return '#e8f7ed'
  if (s >= 0.6) return '#fff7e6'
  return '#f7f8fa'
}

function getAlignmentBorderColor(score) {
  const s = Number(score) || 0
  if (s >= 0.8) return '#b7eb8f'
  if (s >= 0.7) return '#c8e6c9'
  if (s >= 0.6) return '#ffd591'
  return '#e5e6eb'
}

function getAlignmentTextColor(score) {
  const s = Number(score) || 0
  if (s >= 0.8) return '#52c41a'
  if (s >= 0.7) return '#5ba43b'
  if (s >= 0.6) return '#d46b08'
  return '#86909c'
}

function getSourceTagTagColor(tag) {
  switch(tag) {
    case 'anchored': return 'green'
    case 'derived': return 'arcoblue'
    case 'missing': return 'red'
    default: return 'gray'
  }
}

function getSourceTagLabel(tag) {
  switch(tag) {
    case 'anchored': return '✓ 已锚定'
    case 'derived': return '→ AI推断'
    case 'missing': return '✗ 缺失'
    default: return '未知'
  }
}

function getSectionNumber(key) {
  const order = ['hook', 'problem', 'breakdown', 'solution', 'action']
  return order.indexOf(key) + 1
}

function getSectionMissingItems(sectionKey) {
  if (!outlineResult.value?.missing_items) return []
  return outlineResult.value.missing_items.filter(item => item.section === sectionKey)
}

const outlineCompletenessStatus = computed(() => {
  if (!outlineResult.value?.sections) return 'red'
  const sections = outlineResult.value.sections
  const anchoredCount = Object.values(sections).filter(s => s.source_tag === 'anchored').length
  const missingCount = outlineResult.value.missing_items?.length || 0
  if (anchoredCount >= 4 && missingCount <= 1) return 'green'
  if (anchoredCount >= 2 && missingCount <= 3) return 'yellow'
  return 'red'
})

function getCompletenessStatusColor(status) {
  switch(status) {
    case 'green': return '#00b42a'
    case 'yellow': return '#f7ba1e'
    case 'red': return '#f53f3f'
    default: return '#86909c'
  }
}

function getCompletenessStatusLabel(status) {
  switch(status) {
    case 'green': return '🟢 结构完整'
    case 'yellow': return '🟡 部分缺失'
    case 'red': return '🔴 严重缺失'
    default: return '未知状态'
  }
}

async function loadTopics() {
  topicsLoading.value = true
  try {
    const folders = scannedFolders.value.length > 0
      ? scannedFolders.value
      : (route.query.folders ? JSON.parse(route.query.folders) : [])

    if (!folders.length) {
      Message.warning('缺少知识库文件夹信息')
      return
    }

    const res = await apiMcpSuggest({
      topic: route.query.topic || '',
      folders,
      categories: route.query.categories ? JSON.parse(route.query.categories) : [],
      time_range: route.query.timeRange || 'all',
      start_date: route.query.startDate || '',
      end_date: route.query.endDate || '',
    })

    if (res.data.code === 0) {
      // 话题数据 + 补充评估分数（后端可能不返回，用已有字段推导）
      topics.value = (res.data.data.topics || []).map(t => {
        const coverage = t.coverage || 0.5
        const evalData = t.evaluation || {
          direction_score: Math.round(coverage * 100),
          deficiency_score: Math.round((1 - coverage) * 100),
          overall_score: Math.round(coverage * 100),
          direction_analysis: t.reason || '',
          deficiency_details: t.needed ? [{ item: t.needed, severity: 'medium', explanation: t.needed }] : [],
          supplement_strategy: coverage >= 0.7 ? '信息充足' : coverage >= 0.4 ? '需补充关键信息' : '素材严重不足'
        }
        return {
          ...t,
          ...evalData,
          evaluation: evalData
        }
      })
      mcpSummary.value = res.data.data.summary || ''
      mcpFiles.value = res.data.data.source_files || []
      fileCount.value = res.data.data.file_count || 0
      scannedFolders.value = folders
    } else {
      Message.error(res.data.msg || '话题推荐失败')
    }
  } catch (e) {
    Message.error('话题推荐失败: ' + e.message)
  } finally {
    topicsLoading.value = false
  }
}

async function refreshTopics() {
  // 清除当前选中的方向
  selectedDirection.value = null
  // 重新加载选题
  await loadTopics()
  Message.success('已刷新选题推荐')
}

async function goToCompletenessEval() {
  console.log('========================================')
  console.log('🔴 [DEBUG] goToCompletenessEval 被调用')
  console.log('🔴 当前状态:', { currentStep: currentStep.value, loading: loading.value, sessionId: sessionId.value })
  console.log('========================================')
  
  if (!sessionId.value) {
    Message.error('会话未初始化，请刷新页面重试')
    return
  }

  loading.value = true
  try {
    console.log(' 开始完整度评估, sessionId:', sessionId.value)
    const res = await evaluateCompleteness(sessionId.value, mcpSummary.value)
    console.log('📥 评估响应:', JSON.stringify(res.data).substring(0, 500))

    if (res.data.code === 0) {
      const rawData = res.data.data
      let completeness = rawData.completeness || 0
      if (completeness > 0 && completeness <= 1) {
        completeness = Math.round(completeness * 100)
      }
      completenessResult.value = { ...rawData, completeness }
      
      // 评估完成后，直接加载方向推荐
      Message.success('完整度评估完成，正在推荐写作方向...')
      loadDirectionsInternal()
    } else {
      loading.value = false
      Message.error('评估失败: ' + (res.data.msg || '未知错误'))
    }
  } catch (e) {
    console.error('评估异常:', e)
    loading.value = false
    Message.error('评估失败: ' + e.message)
  }
}

// 内部加载方向（与 goToDirections 相同逻辑，但不从外部入口调用）
async function loadDirectionsInternal() {
  if (!sessionId.value) {
    loading.value = false
    return
  }
  
  currentStep.value = 1
  directions.value = []
  directionsLoading.value = true
  
  try {
    const res = await analyzeDirectionsV2(sessionId.value, mcpSummary.value)
    if (res.data.code === 0) {
      const data = res.data.data
      if (data.directions && data.directions.length > 0) {
        directions.value = data.directions
        Message.success(`方向推荐完成，共 ${directions.value.length} 个方向`)
      } else if (Array.isArray(data) && data.length > 0) {
        directions.value = data
        Message.success(`方向推荐完成，共 ${directions.value.length} 个方向`)
      } else {
        Message.warning('暂无推荐方向，请补充更多信息后重试')
      }
    } else {
      Message.error('方向推荐失败: ' + (res.data.msg || '未知错误'))
    }
  } catch (e) {
    console.error('方向推荐异常:', e)
    Message.error('方向推荐失败: ' + e.message)
  } finally {
    loading.value = false
    directionsLoading.value = false
  }
}

// 重新评估完整度（补充后调用）
async function reEvaluateCompleteness() {
  if (!sessionId.value) return
  
  try {
    const res = await evaluateCompleteness(sessionId.value, mcpSummary.value)
    if (res.data.code === 0) {
      const oldCompleteness = completenessResult.value?.completeness || 0
      const newData = res.data.data
      // 后端返回的 completeness 已经是 0-100 的整数（如 55）
      // 确保它是整数格式
      let newCompleteness = newData.completeness || 0
      // 如果后端返回的是 0-1 的小数，转换为百分比
      if (newCompleteness > 0 && newCompleteness <= 1) {
        newCompleteness = Math.round(newCompleteness * 100)
      }
      
      // 更新完整度结果，保持所有字段
      completenessResult.value = { ...newData, completeness: newCompleteness }
      
      Message.success(`完整度已从 ${oldCompleteness}% 更新至 ${newCompleteness}%`)
      
      // 检查是否所有关键缺失项都已补充
      const missingCritical = completenessResult.value.missing_critical || []
      const allSupplemented = missingCritical.every((_, idx) => isSupplemented(idx))
      
      if (allSupplemented && missingCritical.length > 0) {
        Message.success('所有关键缺失项已补充完毕！')
        // 不自动跳转，让用户手动点击下一步
      } else if (newCompleteness >= 80) {
        Message.info('信息已充足，可以直接生成提纲！')
      }
    }
  } catch (e) {
    console.warn('重新评估完整度失败:', e)
  }
}

async function goToDirections() {
  console.log('========================================')
  console.log('🔴 [DEBUG] goToDirections 被调用')
  console.log('🔴 当前状态:', { currentStep: currentStep.value, loading: loading.value })
  console.log('========================================')
  
  if (!sessionId.value) {
    Message.error('会话未初始化，请刷新页面')
    return
  }
  
  // 如果还没有评估结果，先跑评估再加载方向
  if (!completenessResult.value) {
    loading.value = true
    try {
      const res = await evaluateCompleteness(sessionId.value, mcpSummary.value)
      if (res.data.code === 0) {
        const rawData = res.data.data
        let completeness = rawData.completeness || 0
        if (completeness > 0 && completeness <= 1) {
          completeness = Math.round(completeness * 100)
        }
        completenessResult.value = { ...rawData, completeness }
      }
    } catch (e) {
      console.warn('自动评估失败，继续加载方向:', e)
    }
  }
  
  // 加载方向推荐（await 确保评估完成后再渲染）
  await loadDirectionsInternal()
}

// 换一批：重新推荐方向（使用时间戳避免重复）
async function refreshDirection() {
  if (directionsLoading.value) return
  directionsLoading.value = true
  
  // 使用时间戳作为随机种子，确保后端返回不同结果
  const timestamp = new Date().getTime()
  
  try {
    const res = await analyzeDirectionsV2(sessionId.value, mcpSummary.value, { timestamp })
    if (res.data.code === 0) {
      directions.value = res.data.data || []
      if (directions.value.length === 0) {
        Message.warning('暂无推荐方向，请再试一次')
      } else {
        Message.success(`已换一批，共 ${directions.value.length} 个方向`)
      }
    } else {
      Message.error('换一批失败: ' + (res.data.msg || '未知错误'))
    }
  } catch (e) {
    Message.error('换一批失败: ' + e.message)
  } finally {
    directionsLoading.value = false
  }
}

// 5A/5B/5C 模式选择
async function openModeModal(mode) {
  if (mode === 'manual') {
    // 手动补充：打开第一个缺失项的补充弹窗
    const firstMissingIndex = completenessResult.value.missing_critical?.findIndex((_, idx) => !isSupplemented(idx)) ?? -1
    if (firstMissingIndex >= 0) {
      openSupplementModal(firstMissingIndex)
    } else {
      Message.info('所有关键缺失项已补充完毕')
    }
  } else if (mode === 'ai-pulse') {
    // AI-Pulse 补充
    aiPulseLoading.value = true
    aiPulseCases.value = []
    aiPulseSelectedCases.value = []
    
    // 提取关键词（从缺失项描述中）
    const missingItems = completenessResult.value.missing_critical || completenessResult.value.missing_optional || []
    aiPulseKeywords.value = missingItems.slice(0, 3).map(item => {
      // 简单提取关键词（取前 10 个字符）
      return typeof item === 'string' ? item.substring(0, 10) : item.description?.substring(0, 10) || 'AI'
    })
    
    try {
      const res = await apiAiPulseSupplement(sessionId.value, missingItems[0] || 'AI 效率', aiPulseKeywords.value)
      if (res.data.code === 0) {
        aiPulseCases.value = res.data.data.cases || []
        if (aiPulseCases.value.length === 0) {
          Message.warning('未找到相关案例，请尝试其他关键词')
        } else {
          // 找到案例，打开弹窗让用户勾选
          currentSupplementItem.value = 'AI-Pulse 推荐案例'
          supplementModalVisible.value = true
          Message.success(`找到 ${aiPulseCases.value.length} 个相关案例，请勾选后保存`)
        }
      } else {
        Message.error(res.data.msg || 'AI-Pulse 请求失败')
      }
    } catch (err) {
      console.error('AI-Pulse 请求失败:', err)
      Message.error('AI-Pulse 服务不可用，请稍后重试')
    } finally {
      aiPulseLoading.value = false
    }
  }
}

function confirmAiPulseCases() {
  const selected = aiPulseCases.value.filter((_, idx) => aiPulseSelectedCases.value[idx])
  
  if (selected.length === 0) {
    Message.warning('请至少选择一个案例')
    return
  }
  
  // 将选中的案例格式化为补充内容，填入 textarea
  const caseTexts = selected.map(c =>
    `【${c.title}】\n来源：${c.source}\n评分：${c.score}\n摘要：${c.summary}\n链接：${c.url}`
  )
  
  supplementModalText.value = caseTexts.join('\n\n---\n\n')
  supplementModalFile.value = []
  extractedFileContent.value = true
  extractedFileCount.value = selected.length
  
  // 隐藏 AI-Pulse 区域，显示 textarea
  aiPulseCases.value = []
  aiPulseSelectedCases.value = []
  
  Message.success(`已补充 ${selected.length} 个案例，请确认后点击确定`)
}

async function onSupplementFileChange(files) {
  if (!files || files.length === 0) {
    extractedFileContent.value = false
    supplementModalText.value = ''
    return
  }

  extractingFileContent.value = true
  extractedFileCount.value = files.length

  try {
    let allContent = ''

    // 读取所有选中文件的内容
    for (const filePath of files) {
      try {
        const res = await readFolderFile('', filePath)
        if (res.data.code === 0) {
          const content = res.data.data.content || ''
          allContent += `\n--- 文件: ${filePath} ---\n${content.substring(0, 5000)}`
        }
      } catch (e) {
        console.warn(`读取文件失败: ${filePath}`, e)
      }
    }

    if (!allContent.trim()) {
      Message.warning('无法读取文件内容，请尝试手动输入')
      supplementModalText.value = ''
      extractingFileContent.value = false
      return
    }

    // 使用 AI 从文件内容中提取与缺失项相关的部分
    const extractRes = await apiAiAutoSupplement(
      sessionId.value,
      `请从以下文件内容中提取与「${currentSupplementItem.value}」相关的信息：\n\n${allContent}`,
      `【文件原始内容】\n${allContent}`,
    )
    const extractData = extractRes.data.data
    supplementModalText.value = extractData.content || allContent
    extractedFileContent.value = true
    Message.success(`已从 ${files.length} 个文件中提取内容`)
  } catch (e) {
    Message.error('文件内容提取失败: ' + e.message)
    supplementModalText.value = ''
  } finally {
    extractingFileContent.value = false
  }
}

async function confirmSupplementModal() {
  if (supplementModalMethod.value === 'text' && !supplementModalText.value.trim()) {
    Message.warning('请输入补充内容')
    return
  }
  if (supplementModalMethod.value === 'file' && supplementModalFile.value.length === 0) {
    Message.warning('请选择文件')
    return
  }

  try {
    // 确定补充类型和维度
    const itemText = currentSupplementItem.value || ''
    let supplementType = 'case'
    if (itemText.includes('画像') || itemText.includes('受众') || itemText.includes('用户')) {
      supplementType = 'persona'
    } else if (itemText.includes('数据') || itemText.includes('统计') || itemText.includes('指标')) {
      supplementType = 'data'
    }
    const dimension = itemText || '其他'

    // 调用后端 API 添加补充
    const sourceMap = { text: 'manual', file: 'file', 'ai-pulse': 'ai-pulse' }
    const addRes = await apiAddSupplement(
      sessionId.value,
      supplementType,
      dimension,
      supplementModalText.value,
      sourceMap[supplementModalMethod.value] || 'manual',
    )

    const supplementId = addRes.data.data.supplement_id

    // 确认补充（LLM 将能感知到）
    await apiConfirmSupplement(sessionId.value, supplementId)
  } catch (e) {
    console.warn('补充内容持久化失败，仅本地保存:', e)
  }

  // 保存补充内容到跟踪对象（本地 UI 状态）
  supplementContents.value[currentSupplementIndex.value] = {
    content: supplementModalText.value,
    method: supplementModalMethod.value,
    files: supplementModalFile.value,
    time: new Date().toLocaleString(),
  }

  // 同步到 completenessResult 用于持久化
  if (!completenessResult.value.supplementedItems) {
    completenessResult.value.supplementedItems = []
  }
  if (!completenessResult.value.supplementedItems.includes(currentSupplementIndex.value)) {
    completenessResult.value.supplementedItems.push(currentSupplementIndex.value)
  }

  supplementModalVisible.value = false
  const msg = isEditMode.value ? '补充内容已更新' : '补充已保存，AI 将使用该信息'
  Message.success(msg)
}

async function aiAutoSupplement() {
  if (!currentSupplementItem.value) return
  aiSupplementing.value = true

  try {
    // 从后端获取所有已确认的补充内容（作为绑定的知识库上下文）
    let kbContext = ''
    try {
      const res = await apiListSupplements(sessionId.value, true)
      if (res.data.code === 0) {
        const supplements = res.data.data.supplements || []
        if (supplements.length > 0) {
          kbContext = supplements.map(s =>
            `【${s.dimension}】(${s.source === 'ai-pulse' ? 'AI-Pulse' : '手动补充'})：${s.content}`
          ).join('\n\n')
        }
      }
    } catch (e) {
      console.warn('获取知识库内容失败:', e)
    }

    // 调用后端 AI 自动补充（整合 AI-Pulse API + 知识库 + 上下文）
    const res = await apiAiAutoSupplement(
      sessionId.value,
      currentSupplementItem.value,
      mcpSummary.value,
      [],  // selected_cases - 后端会自动调用 AI-Pulse API 检索
      kbContext,  // 绑定的知识库内容
    )
    const data = res.data.data
    supplementModalText.value = data.content || ''
    
    // 根据来源显示不同提示
    const sourceMap = {
      'ai-pulse+kb': '已整合 AI-Pulse 检索案例 + 知识库内容生成',
      'ai-pulse': '已整合 AI-Pulse 检索案例生成',
      'kb': '已整合知识库内容生成',
      'ai_inference': 'AI-Pulse 和知识库均无匹配内容，已基于 AI 上下文推理生成',
    }
    const sourceText = sourceMap[data.source] || 'AI 补充完成'
    Message.success(sourceText)
  } catch (e) {
    Message.error('AI 补充失败: ' + e.message)
  } finally {
    aiSupplementing.value = false
  }
}

// ===== ArchGen v2.0: 智能补充函数 =====

async function smartSupplement(topic, missingItem = {}, missingItems = [], forceLevel = null) {
  // 智能补充：集成知识评估 + 降级链
  // Args:
  //   topic: 话题/维度名称
  //   missingItem: 缺失项详情
  //   missingItems: 所有缺失项列表
  //   forceLevel: 强制级别（用于降级，null = 自动评估）
  smartSupplementLoading.value = true
  
  try {
    // Step 1: 先调用 AI-Pulse 检索（获取实际检索结果）
    let retrievalResults = []
    try {
      const keyword = typeof topic === 'string' ? topic.substring(0, 10) : 'AI'
      const apiRes = await apiAiPulseSupplement(sessionId.value, topic, [keyword])
      if (apiRes.data.code === 0) {
        retrievalResults = apiRes.data.data?.cases || []
      }
    } catch (e) {
      console.warn(`AI-Pulse 检索 "${topic}" 失败:`, e)
    }
    
    // 构建上下文（文章 + 大纲 + MCP 摘要）
    const context = `
MCP 摘要：
${mcpSummary.value || '无'}

已选择方向：${selectedDirection.value?.name || '无'}
已选择框架：${selectedFramework.value?.name || '无'}
`
    
    const res = await apiSmartSupplement(
      sessionId.value,
      topic,
      context,
      missingItems,
      missingItem,
      forceLevel,
      retrievalResults,  // 传入实际检索结果
    )
    
    if (res.data.code === 0) {
      const data = res.data.data
      smartSupplementResult.value = data
      currentKnowledgeLevel.value = data.knowledge_level || 'L1'
      canDegrade.value = data.can_degrade !== false && degradationCount.value < maxDegradationCount
      
      // 拒补模式处理
      if (data.mode === 'refuse') {
        Message.warning(data.alert_message || '未检索到相关资料，建议手动补充')
        return data
      }
      
      // 根据知识级别显示不同提示
      const levelMessages = {
        L0: '✅ 知识充足，已生成具体内容',
        L1: '⚠️ 基于通用模式推导，部分内容需要你补充',
        L2: '❓ AI 知识有限，已生成引导问题',
        L3: '🔗 基于类比推导，请验证后使用',
        L4: '📐 已提供逻辑框架，请填写具体内容',
      }
      Message.success(levelMessages[data.knowledge_level] || '智能补充完成')
      
      // 埋点采集
      recordAnalyticsEvent({
        session_id: sessionId.value,
        event_type: 'supplement_complete',
        topic: topic,
        knowledge_level: data.knowledge_level,
        assessment_confidence: data.assessment_confidence || 'medium',
        assessment_cached: data.assessment_cached || false,
        content_length: (data.content || '').length,
        has_evidence: !!data.evidence_quote,
        has_gap_hint: !!data.gap_hint,
        questions_count: (data.questions || []).length,
        reevaluate: data.reevaluate || false,
        can_degrade: data.can_degrade !== false,
        user_action: null,
        degradation_count: degradationCount.value,
      }).catch(err => console.error('埋点采集失败:', err))
      
      return data
    } else {
      Message.error(res.data.msg || '智能补充失败')
      return null
    }
  } catch (e) {
    console.error('智能补充失败:', e)
    Message.error('智能补充失败: ' + e.message)
    return null
  } finally {
    smartSupplementLoading.value = false
  }
}

async function selectDirectionAndAdvance(t) {
  // 选择方向并自动进入下一步
  selectedDirection.value = { name: t.name, description: t.description }
  mcpTopic.value = t.name
  
  Message.success(`已选择「${t.name}」，正在加载框架...`)
  
  // 保存方向到后端 session
  try {
    await supplementStep1(sessionId.value, t.name, {})
  } catch (e) {
    console.warn('保存方向到 session 失败:', e)
  }
  
  // 加载主题匹配的文件（从文件夹中按主题关键词过滤）
  try {
    const folders = JSON.parse(route.query.folders || '[]')
    if (folders.length > 0) {
      const matchRes = await apiMcpMatchFiles({
        topic: t.name,
        folders,
      })
      if (matchRes.data?.code === 0 && matchRes.data.data) {
        const matchData = matchRes.data.data
        mcpFiles.value = (matchData.matched_files || []).map(f => ({
          name: f.name || '',
          content: f.content || '',
        }))
        mcpSummary.value = `已搜索「${t.name}」相关素材 ${matchData.total || mcpFiles.value.length} 篇`
        console.log('📂 主题匹配素材已加载:', { topic: t.name, matched: mcpFiles.value.length, total: matchData.total })
      }
    }
  } catch (e) {
    console.warn('加载主题匹配素材失败:', e)
  }
  
  // 自动进入补充步骤
  currentStep.value = 1
}

async function degradeSupplement() {
  // 用户对当前级别不满意，降级一级重新生成
  if (!canDegrade.value || !smartSupplementResult.value) return
  
  smartSupplementLoading.value = true
  
  try {
    const topic = currentSupplementItem.value?.dimension || currentSupplementItem.value?.label || ''
    const context = `
MCP 摘要：
${mcpSummary.value || '无'}

已选择方向：${selectedDirection.value?.name || '无'}
已选择框架：${selectedFramework.value?.name || '无'}
`
    
    const res = await apiDegradeSupplement(
      sessionId.value,
      currentKnowledgeLevel.value,
      topic,
      context,
      currentSupplementItem.value || {},
    )
    
    if (res.data.code === 0) {
      const data = res.data.data
      smartSupplementResult.value = data
      currentKnowledgeLevel.value = data.knowledge_level || 'L1'
      degradationCount.value += 1
      canDegrade.value = data.can_degrade !== false && degradationCount.value < maxDegradationCount
      
      Message.warning(`已降级到 ${data.knowledge_level}，${data.alert_message || '请查看内容'}`)
      
      // 埋点采集
      recordAnalyticsEvent({
        session_id: sessionId.value,
        event_type: 'degrade',
        topic: topic,
        knowledge_level: data.knowledge_level,
        assessment_confidence: 'medium',
        assessment_cached: false,
        content_length: (data.content || '').length,
        has_evidence: !!data.evidence_quote,
        has_gap_hint: !!data.gap_hint,
        questions_count: (data.questions || []).length,
        reevaluate: data.reevaluate || false,
        can_degrade: data.can_degrade !== false,
        user_action: 'degrade',
        degradation_count: degradationCount.value,
      }).catch(err => console.error('埋点采集失败:', err))
      
      return data
    } else {
      Message.error(res.data.msg || '降级补充失败')
      return null
    }
  } catch (e) {
    console.error('降级补充失败:', e)
    Message.error('降级补充失败: ' + e.message)
    return null
  } finally {
    smartSupplementLoading.value = false
  }
}

async function selectDirection(d) {
  console.log('========================================')
  console.log(' [DEBUG] selectDirection 被调用')
  console.log(' 选择方向:', d.name)
  console.log(' 当前步骤:', currentStep.value)
  console.log('========================================')
  
  // 选择方向后保持在 Step 2，框架会内联显示
  selectedDirection.value = d
  // 不改变 currentStep，保持在 Step 2
  directionsLoading.value = true
  Message.info(`已选择「${d.name}」，正在推荐框架...`)
  
  // 先保存方向到后端session
  try {
    await supplementStep1(sessionId.value, d.name, {})
    console.log('✅ 方向已保存到后端session')
  } catch (e) {
    console.error(' 保存方向失败:', e)
    Message.error('保存方向失败: ' + e.message)
    return
  }
  
  // 保存成功后再异步加载框架
  loadFrameworks()
}

function showEvidenceQuote(item) {
  Modal.info({
    title: '原文引用',
    content: () => h('div', { style: 'white-space: pre-wrap; line-height: 1.8; font-size: 13px' }, item.evidence_quote || '暂无原文引用'),
    width: 500,
  })
}

async function loadFrameworks() {
  console.log(' [DEBUG] loadFrameworks 开始，当前步骤:', currentStep.value)
  
  try {
    const res = await matchFrameworksV2(sessionId.value, selectedDirection.value?.name || '', mcpSummary.value)
    if (res.data.code === 0) {
      const payload = res.data.data || {}
      let fwList = []
      if (Array.isArray(payload)) {
        fwList = payload
        frameworksMode.value = 'premium'
        frameworksBanner.value = ''
      } else {
        fwList = payload.frameworks || []
        frameworksMode.value = payload.mode || 'premium'
        frameworksBanner.value = payload.banner || ''
      }
      frameworks.value = fwList
      console.log(' 框架加载成功，共', frameworks.value.length, '个框架, mode=', frameworksMode.value)
      if (frameworksMode.value === 'rejected') {
        Message.warning('未能找到对齐方向的框架，请查看提示')
      } else if (frameworksMode.value === 'fallback') {
        Message.warning(`已降级推荐 ${fwList.length} 个框架，建议人工评估`)
      } else {
        Message.success(`框架推荐完成，共 ${fwList.length} 个框架`)
      }
    } else {
      console.warn(' 框架加载失败:', res.data.msg)
      Message.warning(res.data.msg || '暂无推荐框架，请重试')
      frameworks.value = []
      frameworksBanner.value = res.data.msg || ''
      frameworksMode.value = 'rejected'
    }
  } catch (e) {
    console.error(' 框架加载失败:', e)
    Message.error('框架推荐失败: ' + e.message)
  } finally {
    directionsLoading.value = false
  }
}

async function regenerateFrameworks() {
  if (!selectedDirection.value) {
    Message.warning('请先选择方向')
    return
  }
  frameworksLoading.value = true
  frameworks.value = []
  frameworksBanner.value = ''
  await loadFrameworks()
  frameworksLoading.value = false
}

async function selectFramework(f) {
  console.log('========================================')
  console.log('🔴 [DEBUG] selectFramework 被调用')
  console.log(' 选择框架:', f.name)
  console.log(' 当前步骤:', currentStep.value)
  console.log('========================================')
  
  // 先设置框架，确保数据立即可用
  selectedFramework.value = f
  
  // 按需检索 API 案例（不再预加载）
  // preloadApiCases()  // 已移除：改为按需检索
  
  // 保存框架 + 补充数据到后端session
  try {
    const supplementData = pendingSupplementData.value || {}
    await supplementStep2(sessionId.value, f, supplementData)
    console.log('✅ 框架+补充数据已保存到后端session:', f.name)
  } catch (e) {
    console.error(' 保存框架失败:', e)
    Message.error('保存框架失败: ' + e.message)
    return
  }
  
  // 切换到检测页面 (Step 3)
  currentStep.value = 3
  
  // 自动触发预检测，显示缺失项清单
  setTimeout(() => runPreCheck(), 100)
  
  Message.success(`已选择「${f.name}」框架，正在检测...`)
}

async function runPreCheck() {
  if (preCheckLoading.value) return
  preCheckLoading.value = true
  try {
    // 合并 supplement2Form 和 supplement2Text，确保 AI 补充的内容也传给后端
    const supplementData = { ...supplement2Form }
    if (supplement2Text.value) {
      supplementData.text = supplement2Text.value
    }
    
    const res = await checkWorkflowDirection(
      sessionId.value,
      selectedDirection.value?.name || '',
      selectedFramework.value?.name || '',
      supplementData,
      mcpSummary.value,
    )
    if (res.data.code === 0 && res.data.data) {
      preCheckResult.value = {
        score: res.data.data.overall_score || 0,
        issues: (res.data.data.issues || []).filter(issue => issue.type !== 'pass'),
        ready_for_next: res.data.data.ready_for_next || false,
      }
      Message.success('预检测完成')
    }
  } catch (e) {
    Message.error('预检测失败: ' + e.message)
  } finally {
    preCheckLoading.value = false
  }
}

async function aiAutoSupplementAllMissing() {
  if (aiAutoSupplementLoading.value || !preCheckResult.value?.issues?.length) return
  aiAutoSupplementLoading.value = true
  try {
    let thickenCount = 0
    let needConfirmItems = []
    
    // 第一遍：分类处理
    for (const issue of preCheckResult.value.issues) {
      if (issue.type === 'pass') continue
      
      const res = await apiInferSupplement(sessionId.value, `自动补充：${issue.title}`, {
        mcp_summary: mcpSummary.value || '',
      })
      
      if (res.data.code === 0 && res.data.data?.content) {
        const supplementType = res.data.data.supplement_type || 'infer'
        const confidence = res.data.data.confidence || 0.7
        
        // 根据 supplement_type 生成标记
        const typeTag = supplementType === 'thicken' ? '增厚补充'
                    : supplementType === 'fill' ? '补全补充'
                    : '推断补充'

        // 增厚类：自动采纳（风险低）
        if (supplementType === 'thicken' && confidence >= 0.7) {
          supplement2Text.value += (supplement2Text.value ? '\n\n' : '') + `【${issue.title}】\n[${typeTag}] ${res.data.data.content}`
          thickenCount++
        } else {
          // 补全/推断类：收集后弹窗确认
          needConfirmItems.push({
            issue,
            content: res.data.data.content,
            typeTag,
            type: supplementType,
            confidence,
            note: res.data.data.inference_note || '',
          })
        }
      }
    }
    
    // 第二遍：处理需要确认的项
    if (needConfirmItems.length > 0) {
      const confirmResult = await showSupplementConfirmDialog(needConfirmItems)
      if (confirmResult.accepted.length > 0) {
        for (const item of confirmResult.accepted) {
          supplement2Text.value += (supplement2Text.value ? '\n\n' : '') + `【${item.issue.title}】\n[${item.typeTag}] ${item.content}`
        }
      }
    }
    
    // 显示总结
    if (thickenCount > 0) {
      Message.success(`已自动采纳 ${thickenCount} 项增厚内容`)
    }
    if (needConfirmItems.length > 0) {
      Message.info(`还有 ${needConfirmItems.length} 项需确认的补充已处理`)
    }
    
    await runPreCheck()
  } catch (e) {
    Message.error('AI 智能补充失败: ' + e.message)
  } finally {
    aiAutoSupplementLoading.value = false
  }
}

// 补充确认弹窗
function showSupplementConfirmDialog(items) {
  return new Promise((resolve) => {
    const accepted = []
    
    // 使用 Arco Design 的 Modal 确认
    const modal = Modal.confirm({
      title: 'AI 补充内容确认',
      width: 900,
      content: () => h('div', { style: 'padding-right: 12px' }, [
        h('p', { style: 'margin-bottom: 12px; color: #86909c' },
          `检测到 ${items.length} 项补充内容可能改变文章走向，请逐项确认：`),
        h('div', { style: 'max-height: 500px; overflow-y: auto' },
          items.map((item, idx) => h('div', {
            key: idx,
            style: 'padding: 14px; margin-bottom: 10px; background: #f7f8fa; border-radius: 6px; border-left: 4px solid ' +
                   (item.type === 'fill' ? '#f53f3f' : item.type === 'infer' ? '#ff7d00' : '#00b42a')
          }, [
            h('div', { style: 'display: flex; justify-content: space-between; margin-bottom: 8px' }, [
              h('strong', { style: 'font-size: 14px; color: #1d2129' }, `【${item.issue.title}】`),
              h('span', { style: 'font-size: 12px; color: #86909c' },
                ` ${item.typeTag || (item.type === 'fill' ? '补全' : item.type === 'infer' ? '推断' : '增厚')}`),
            ]),
            h('div', { style: 'padding: 10px; background: #fff; border-radius: 4px; font-size: 13px; line-height: 1.7; color: #1d2129; margin-bottom: 8px' },
              item.content.slice(0, 300) + (item.content.length > 300 ? '...' : '')),
            h('div', { style: 'font-size: 12px; color: #86909c; font-style: italic' },
              `置信度：${(item.confidence * 100).toFixed(0)}% | ${item.note || '无额外说明'}`),
          ])),
        ),
      ]),
      okText: `采纳选中的 ${items.length} 项`,
      cancelText: '全部跳过',
      onOk: () => {
        resolve({ accepted: items })
      },
      onCancel: () => {
        resolve({ accepted: [] })
      },
    })
  })
}

// 建设清单：AI 修复单个问题
async function fixIssue(idx) {
  const issue = preCheckResult.value?.issues?.[idx]
  if (!issue) {
    Message.warning('未找到该问题，请刷新页面重试')
    return
  }
  
  if (!issue.can_auto_fix) {
    Message.info('该问题需要手动补充，请使用"手动补充"功能')
    return
  }
  
  // 根据问题类别调用对应的 AI 补充接口
  const categoryMap = {
    cases: '具体案例',
    data: '关键数据支撑',
    direction: '方向对齐',
    structure: '结构优化',
    value: '可落地实操内容',
  }
  const supplementItem = categoryMap[issue.category] || issue.title
  
  if (issue.category === 'direction') {
    Message.warning('方向偏离建议：请重新审视选定方向与内容的一致性')
    return
  }
  
  Message.loading({ content: 'AI 正在分析并补充...', duration: 0 })
  
  try {
    const res = await apiInferSupplement(sessionId.value, `自动补充：${supplementItem}`, {
      mcp_summary: mcpSummary.value || '',
    })

    if (res.data.code === 0 && res.data.data?.content) {
      const supplementType = res.data.data.supplement_type || 'infer'
      const typeTag = supplementType === 'thicken' ? '增厚补充'
                  : supplementType === 'fill' ? '补全补充'
                  : '推断补充'
      supplement2Text.value += (supplement2Text.value ? '\n\n' : '') + `【${supplementItem}】\n[${typeTag}] ${res.data.data.content}`
      Message.success(`已补充：${supplementItem}`)
      await runPreCheck()
    } else {
      Message.error('补充失败：AI 未能生成有效内容')
    }
  } catch (e) {
    Message.error('补充失败: ' + (e.message || '未知错误'))
  }
}

// 建设清单：切换问题展开/收起
function toggleIssueExpand(index) {
  if (expandedIssues.value.has(index)) {
    expandedIssues.value.delete(index)
  } else {
    expandedIssues.value.add(index)
  }
}

// 保存补充数据并进入框架选择
async function submitSupplement2() {
  // 收集补充表单数据到临时变量
  const supplementInfo = {}
  if (supplement2Text.value) supplementInfo.text = supplement2Text.value
  if (supplement2UploadFiles.value && supplement2UploadFiles.value.length > 0) {
    supplementInfo.upload_files = supplement2UploadFiles.value
  }
  if (supplement2KbFiles.value && supplement2KbFiles.value.length > 0) {
    supplementInfo.kb_files = supplement2KbFiles.value
  }
  if (supplement2File.value && supplement2File.value.length > 0) {
    supplementInfo.files = supplement2File.value
  }

  pendingSupplementData.value = supplementInfo
  supplementLoading.value = false
  Message.success('补充已保存，正在加载框架推荐...')
  currentStep.value = 2
  await loadFrameworks()
}

// 跳过补充，直接进入框架选择
async function skipSupplement2() {
  pendingSupplementData.value = {}
  supplementLoading.value = false
  supplementConfirmed.value = true
  Message.info('已跳过补充，正在启动分析工作台...')
  currentStep.value = 2
}

// 确认补充完毕，进入下一步
function confirmSupplementAndProceed() {
  if (!supplement2Text.value) {
    Message.warning('请先补充内容')
    return
  }
  supplementConfirmed.value = true
  Message.success('补充已确认，正在启动分析工作台...')
  currentStep.value = 2
}

// 打开 Step 2 补充对话框
function openStep2SupplementDialog() {
  step2SupplementDialogVisible.value = true
}

// 提交 Step 2 补充（调用后端 AI 推断）
async function handleStep2SupplementSubmit({ userPrompt, userFiles, useKB, selectedKBFiles, useWebSearch, webSearchKeyword }) {
  supplementLoading.value = true
  try {
    if (!preCheckResult.value) {
      await runPreCheck()
    }
    let missingItems = '分析内容待补充'
    if (preCheckResult.value?.issues) {
      const items = preCheckResult.value.issues
        .filter(i => i.type !== 'pass')
        .map(i => i.title)
      if (items.length > 0) {
        missingItems = '需要补充以下内容项：' + items.join('、')
      }
    }
    let effectivePrompt = userPrompt || ''
    if (!effectivePrompt && preCheckResult.value?.issues) {
      const missingTitles = preCheckResult.value.issues
        .filter(i => i.type !== 'pass')
        .map(i => i.title)
      if (missingTitles.length > 0) {
        effectivePrompt = `请根据检测到的缺失项（${missingTitles.join('、')}），自动推断补充内容`
      } else {
        effectivePrompt = '请根据检测到的缺失项，自动推断补充内容'
      }
    }
    step2SupplementDialogRef.value?.step2SupplementDialogRef?.setProgressStep?.(1)
    const res = await apiInferSupplement(
      sessionId.value,
      missingItems,
      {
        mcp_summary: mcpSummary.value || '',
        kb_file_list: mcpFiles.value || [],
        user_prompt: effectivePrompt,
        user_files: userFiles || [],
        existing_content: supplement2Text.value || '',
        useKB: useKB || false,
        selectedKBFiles: selectedKBFiles || [],
        useWebSearch: useWebSearch || false,
        webSearchKeyword: webSearchKeyword || '',
      }
    )
    if (res.data.code === 0 && res.data.data) {
      lastSupplementMeta.value = {
        inference_note: res.data.data.inference_note || '',
        supplement_type: res.data.data.supplement_type || 'infer',
        confidence: res.data.data.confidence || 0.7,
        matched_materials: res.data.data.matched_materials || { kb_files: [], ai_pulse_articles: [] },
      }
      step2SupplementDialogRef.value?.step2SupplementDialogRef?.setGeneratedContent?.(res.data.data.content)
    } else {
      Message.error(res.data.msg || '补充失败')
      step2SupplementDialogRef.value?.step2SupplementDialogRef?.setError?.()
    }
  } catch (e) {
    console.error('Step 2 supplement error:', e)
    Message.error('补充失败，请重试')
    step2SupplementDialogRef.value?.step2SupplementDialogRef?.setError?.()
  } finally {
    supplementLoading.value = false
  }
}

// 确认 Step 2 补充内容
function handleStep2SupplementConfirm({ content, userFiles }) {
  const supplementInfo = {}
  if (content) supplementInfo.text = content
  if (userFiles && userFiles.length > 0) supplementInfo.upload_files = userFiles
  if (lastSupplementMeta.value) {
    if (lastSupplementMeta.value.inference_note) supplementInfo.inference_note = lastSupplementMeta.value.inference_note
    supplementInfo.supplement_type = lastSupplementMeta.value.supplement_type
    supplementInfo.confidence = lastSupplementMeta.value.confidence
  }
  if (mcpFiles.value && mcpFiles.value.length > 0) {
    supplementInfo.files = mcpFiles.value.slice(0, 10)
  }
  supplement2Text.value = content || ''
  pendingSupplementData.value = supplementInfo
  supplementConfirmed.value = false
  Message.success('补充已保存，请确认后继续')

  // 方案 B：将匹配素材追加到素材池
  const meta = lastSupplementMeta.value
  if (meta?.matched_materials) {
    const ts = Date.now()
    if (content) {
      materialPool.value.push({ type: 'inference', content, ts })
    }
    for (const f of (meta.matched_materials.kb_files || [])) {
      materialPool.value.push({ type: 'kb_file', path: f.path, name: f.name, content: f.content, ts })
    }
    for (const a of (meta.matched_materials.ai_pulse_articles || [])) {
      materialPool.value.push({ type: 'ai_pulse', title: a.title, source: a.source, summary: a.summary, url: a.url, ts })
    }
    console.log(' 素材池已更新:', materialPool.value.length, '条')
  }

  // 补充后：将所有现有 issues 标记为 recurring
  if (preCheckResult.value?.issues?.length) {
    preCheckResult.value = {
      ...preCheckResult.value,
      issues: preCheckResult.value.issues.map(i => ({ ...i, recurring: true, type: 'suggestion' })),
      all_recurring: true,
      score: Math.max(preCheckResult.value.score, 60),
    }
  }
}

// 打开单个问题补充对话框
function openSupplementDialog(idx) {
  const issue = preCheckResult.value?.issues?.[idx]
  if (!issue) return
  // 复用 Step 2 对话框
  step2SupplementDialogVisible.value = true
}

function scrollToPreCheck() {
  // 滚动到预检测结果区域
  const preCheckEl = document.querySelector('.pre-check-result')
  if (preCheckEl) {
    preCheckEl.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

async function runDirectionCheck() {
  console.log('========================================')
  console.log(' [DEBUG] runDirectionCheck 被调用')
  console.log(' 当前状态:', { currentStep: currentStep.value, checkingDirection: checkingDirection.value })
  console.log(' 补充表单:', JSON.stringify(supplement2Form))
  console.log(' 补充文本:', supplement2Text.value ? supplement2Text.value.substring(0, 100) + '...' : '空')
  console.log('========================================')
  checkingDirection.value = true
  try {
    // 合并 supplement2Form 和 supplement2Text，确保 AI 补充的内容也传给后端
    const supplementData = { ...supplement2Form }
    if (supplement2Text.value) {
      supplementData.text = supplement2Text.value
    }
    
    console.log(' 发送给后端的补充数据:', JSON.stringify(supplementData).substring(0, 200))
    
    const res = await checkWorkflowDirection(
      sessionId.value,
      selectedDirection.value?.name || '',
      selectedFramework.value?.name || '',
      supplementData,
      mcpSummary.value,
    )
    // 门卫模式：保存完整返回对象（包含 force_passed, ready_for_next 等）
    directionCheckResult.value = res.data.data.issues || []
    // 同时保存元数据到单独的ref
    directionCheckMeta.value = {
      force_passed: res.data.data.force_passed || false,
      ready_for_next: res.data.data.ready_for_next !== false,
      check_count: res.data.data.check_count || 0,
      overall_score: res.data.data.overall_score || 0,
    }
    Message.success('审核完成')
  } catch (e) {
    Message.error('检测失败: ' + e.message)
  } finally {
    checkingDirection.value = false
  }
}

async function aiFixIssue(index, issue) {
  console.log('========================================')
  console.log('🔴 [DEBUG] aiFixIssue 被调用')
  console.log('🔴 修复问题:', issue.title)
  console.log('🔴 当前状态:', { currentStep: currentStep.value, loading: loading.value })
  console.log('========================================')
  fixingIssueIndex.value = index
  loading.value = true
  try {
    const res = await fixWorkflowDirection(
      sessionId.value,
      issue,
      supplement2Form,
      mcpSummary.value,
      selectedDirection.value?.name || '',
      selectedFramework.value?.name || '',
    )
    loading.value = false
    fixingIssueIndex.value = -1
    Message.success('AI 修改完成: ' + res.data.data.fix_description)
    await runDirectionCheck()
  } catch (e) {
    loading.value = false
    fixingIssueIndex.value = -1
    Message.error('AI 修改失败: ' + e.message)
  }
}

function ignoreIssue(index) {
  if (!directionCheckResult.value || !directionCheckResult.value[index]) return
  const issue = directionCheckResult.value[index]
  issue.type = 'pass'
  issue.title = issue.title + ' (已忽略)'
  Message.info('已忽略该问题')
}

function editSingleIssue(index) {
  editingIssueIndex.value = index
  editingIssueContent.value = ''
}

function cancelEditIssue() {
  editingIssueIndex.value = -1
  editingIssueContent.value = ''
}

async function confirmSingleIssue(index) {
  if (!editingIssueContent.value.trim()) {
    Message.warning('请输入补充内容')
    return
  }
  editingIssueLoading.value = true
  try {
    // 将补充内容追加到 supplement2Text
    const issue = directionCheckResult.value[index]
    const prefix = `【${issue.title}】\n`
    if (!supplement2Text.value.includes(prefix)) {
      supplement2Text.value += (supplement2Text.value ? '\n\n' : '') + prefix + editingIssueContent.value
    } else {
      Message.warning('该内容已存在')
      editingIssueLoading.value = false
      return
    }
    editingIssueLoading.value = false
    cancelEditIssue()
    Message.success('补充已保存')
    // 自动重新检测
    await runDirectionCheck()
  } catch (e) {
    editingIssueLoading.value = false
    Message.error('操作失败: ' + e.message)
  }
}

async function aiGenerateSingleIssue(index) {
  const issue = directionCheckResult.value[index]
  if (!issue) return
  aiSingleIssueLoading.value = true
  try {
    const res = await apiInferSupplement(sessionId.value, issue.title, {
      mcp_summary: mcpSummary.value || '',
      existing_content: supplement2Text.value || '',
    })
    if (res.data.code === 0 && res.data.data?.content) {
      editingIssueContent.value = res.data.data.content
      Message.success('AI 补充内容已生成，可编辑后确认')
    } else {
      Message.error('AI 生成失败: ' + (res.data.msg || '未知错误'))
    }
  } catch (e) {
    Message.error('AI 生成失败: ' + e.message)
  } finally {
    aiSingleIssueLoading.value = false
  }
}

function goBackToSupplement() {
  console.log('========================================')
  console.log('🔴 [DEBUG] goBackToSupplement 被调用')
  console.log('🔴 当前状态:', { currentStep: currentStep.value })
  console.log('========================================')
  currentStep.value = 1
  directionCheckResult.value = null
  Message.info('已返回补充页面')
}

// 门卫模式：跳过建议，进入下一步（带风险提示）
function skipSuggestionsAndContinue() {
  const suggestCount = suggestIssues.value.length
  if (suggestCount === 0) {
    currentStep.value = 4
    return
  }
  Message.warning(`⚠️ 有 ${suggestCount} 个优化建议未处理，可能影响文章质量`)
  setTimeout(() => {
    currentStep.value = 4
  }, 1500)
}

// 结构性问题：回退到框架步骤重选
function goBackToStep3() {
  currentStep.value = 2
  directionCheckResult.value = null
  directionCheckMeta.value = { force_passed: false, ready_for_next: true, check_count: 0, overall_score: 0 }
  Message.info('已返回框架选择页面，请重新选择')
}

async function goToStructures() {
  console.log('========================================')
  console.log('🔴 [DEBUG] goToStructures 被调用')
  console.log('🔴 当前状态:', { currentStep: currentStep.value, loading: loading.value })
  console.log('========================================')
  structuresLoading.value = true
  try {
    // 合并 supplement2Form 和 supplement2Text，确保 AI 补充的内容也传给后端
    const supplementData = { ...supplement2Form }
    if (supplement2Text.value) {
      supplementData.text = supplement2Text.value
    }
    const res = await recommendStructures(
      sessionId.value,
      selectedDirection.value?.name || '',
      selectedFramework.value?.name || '',
      supplementData,
      mcpSummary.value,
    )
    const data = res.data.data
    // 兼容新旧格式
    if (data && data.structures) {
      structures.value = data.structures
    } else if (Array.isArray(data)) {
      structures.value = data
    } else {
      structures.value = []
    }
    Message.success('结构推荐完成')
  } catch (e) {
    Message.error('结构推荐失败: ' + e.message)
  } finally {
    structuresLoading.value = false
    setTimeout(() => {
      currentStep.value = 4
      Message.success('已切换到结构推荐页面')
    }, 100)
  }
}

async function selectStructure(s) {
  console.log('========================================')
  console.log('🔴 [DEBUG] selectStructure 被调用')
  console.log('🔴 选择结构:', s.name)
  console.log(' 当前状态:', { currentStep: currentStep.value, loading: loading.value })
  console.log('========================================')
  selectedStructure.value = s
  Message.info(`已选择「${s.name}」结构，正在保存...`)
  
  // 先保存结构到后端session
  try {
    await supplementStep3(sessionId.value, s.name, {})
    console.log('✅ 结构已保存到后端session')
  } catch (e) {
    console.error(' 保存结构失败:', e)
    Message.error('保存结构失败: ' + e.message)
    return
  }
  
  // 保存成功后再生成提纲
  currentStep.value = 5
  loadOutline()
  Message.info(`已选择「${s.name}」结构，正在生成提纲...`)
}

function goBackToStructures() {
  currentStep.value = 4
  outlineResult.value = null
  Message.info('已返回结构推荐')
}

async function loadOutline(switchToStep = 5) {
  loading.value = true
  try {
    const res = await generateWorkflowOutline(sessionId.value)
    if (res.data.code === 0) {
      // 解析后端返回的JSON字符串或对象
      let outlineData = res.data.data
      if (typeof outlineData === 'string') {
        try {
          outlineData = JSON.parse(outlineData)
        } catch (e) {
          console.error(' 提纲JSON解析失败:', e)
        }
      }
      outlineResult.value = outlineData
      
      // 初始化缺失项到全局补充区（供一键补充使用）
      if (outlineData.missing_items?.length > 0) {
        if (!outlineData.global_supplements) {
          outlineData.global_supplements = {}
        }
        for (const item of outlineData.missing_items) {
          outlineData.global_supplements[item.field] = ''
        }
      }
      
      loading.value = false
      if (switchToStep !== null) {
        setTimeout(() => {
          currentStep.value = switchToStep
          Message.success('提纲生成完成')
        }, 100)
      }
    } else {
      loading.value = false
      Message.error('提纲生成失败: ' + (res.data.msg || '未知错误'))
    }
  } catch (e) {
    console.error(' 提纲生成异常:', e)
    loading.value = false
    Message.error('提纲生成失败: ' + e.message)
  }
}

async function regenerateOutline() {
  await loadOutline()
}

function toggleSectionAiDialog(key) {
  if (sectionAiDialogIndex.value === key) {
    sectionAiDialogIndex.value = -1
    sectionAiInput.value = ''
    sectionAiResult.value = ''
  } else {
    sectionAiDialogIndex.value = key
    sectionAiInput.value = ''
    sectionAiResult.value = ''
  }
}

async function aiSupplementSectionByKey(key) {
  const section = outlineResult.value?.sections?.[key]
  if (!section) return
  sectionAiLoading.value = true
  sectionAiResult.value = ''
  try {
    const context = [
      `段落标题：${section.title}`,
      section.key_points?.length ? `核心要点：${section.key_points.join('；')}` : '',
      section.materials?.needs?.length ? `需补充素材：${section.materials.needs.join('；')}` : '',
      sectionAiInput.value ? `用户需求：${sectionAiInput.value}` : '',
      sectionAiKbFiles.value?.length ? `参考知识库文件：${sectionAiKbFiles.value.join(', ')}` : '',
      sectionAiUploadFiles.value?.length ? `参考上传文件：${sectionAiUploadFiles.value.map(f => f.name || f).join(', ')}` : '',
    ].filter(Boolean).join('\n')
    const res = await apiInferSupplement(sessionId.value, section.title, {
      mcp_summary: mcpSummary.value || '',
      existing_content: context,
    })
    if (res.data.code === 0 && res.data.data?.content) {
      sectionAiResult.value = res.data.data.content
      Message.success('AI 补充内容已生成')
    } else {
      Message.error('AI 生成失败: ' + (res.data.msg || '未知错误'))
    }
  } catch (e) {
    Message.error('AI 生成失败: ' + e.message)
  } finally {
    sectionAiLoading.value = false
  }
}

async function outlineOneClickAiSupplement() {
  if (!outlineResult.value?.sections) return
  
  // 检查是否有全局缺失项需要补充
  const missingItems = outlineResult.value.missing_items || []
  
  // 检查是否有段落级需要补充的素材
  const sectionsObj = outlineResult.value.sections
  const sectionsWithNeeds = Object.values(sectionsObj).filter(s => s.materials?.needs?.length > 0)
  
  // 如果两者都没有，才显示"暂无需要补充的素材"
  if (missingItems.length === 0 && sectionsWithNeeds.length === 0) {
    Message.info('暂无需要补充的素材')
    return
  }
  
  outlineOneClickLoading.value = true
  try {
    // 初始化全局补充区
    if (!outlineResult.value.global_supplements) {
      outlineResult.value.global_supplements = {}
    }
    
    // 先处理全局缺失项
    if (missingItems.length > 0) {
      for (const item of missingItems) {
        const context = [
          `缺失字段：${item.field}`,
          `补充建议：${item.fill_guidance}`,
        ].join('\n')
        const res = await apiInferSupplement(sessionId.value, `补充：${item.field}`, {
          mcp_summary: mcpSummary.value || '',
          existing_content: context,
        })
        if (res.data.code === 0 && res.data.data?.content) {
          outlineResult.value.global_supplements[item.field] = res.data.data.content
        }
      }
      Message.success(`已为 ${missingItems.length} 个全局缺失项完成 AI 补充`)
    }
    
    // 再处理段落级需要补充的素材
    if (sectionsWithNeeds.length > 0) {
      for (const section of sectionsWithNeeds) {
        const context = [
          `段落标题：${section.title}`,
          section.key_points?.length ? `核心要点：${section.key_points.join('；')}` : '',
          `需补充素材：${section.materials.needs.join('；')}`,
        ].join('\n')
        const res = await apiInferSupplement(sessionId.value, section.title, {
          mcp_summary: mcpSummary.value || '',
          existing_content: context,
        })
        if (res.data.code === 0 && res.data.data?.content) {
          if (!section.materials.has) section.materials.has = []
          section.materials.has.push(res.data.data.content)
        }
      }
      Message.success(`已为 ${sectionsWithNeeds.length} 个段落完成 AI 补充`)
    }
  } catch (e) {
    Message.error('一键补充失败: ' + e.message)
  } finally {
    outlineOneClickLoading.value = false
  }
}

function acceptSectionAiSuggestionByKey(key) {
  if (!sectionAiResult.value || !outlineResult.value?.sections?.[key]) return
  const section = outlineResult.value.sections[key]
  if (!section.materials) section.materials = { has: [], needs: [] }
  if (!section.materials.has) section.materials.has = []
  section.materials.has.push(sectionAiResult.value)
  sectionAiDialogIndex.value = -1
  sectionAiInput.value = ''
  sectionAiResult.value = ''
  sectionAiKbFiles.value = []
  sectionAiUploadFiles.value = []
  Message.success('素材已采纳')
}

function handleSectionAiUpload(fileList) {
  sectionAiUploadFiles.value = fileList || []
}

function goToGenerateArticle() {
  currentStep.value = 6
  generateArticle()
  Message.info('正在生成完整文章...')
}

async function generateArticle() {
  if (!outlineResult.value) {
    await loadOutline(null)  // 作为工具函数调用，不切换步骤
  }
  loading.value = true
  try {
    const outlineSections = outlineResult.value?.sections || []
    
    // 收集 Step 5 检测页的补充内容
    const step5Supplements = supplement2Text.value || ''
    
    // 收集 Step 6 提纲页各版块的补充素材
    const step6Materials = []
    if (outlineResult.value.sections && typeof outlineResult.value.sections === 'object') {
      for (const [key, section] of Object.entries(outlineResult.value.sections)) {
        if (section.materials?.has?.length > 0) {
          step6Materials.push({
            section_key: key,
            title: section.title,
            materials: section.materials.has,
          })
        }
      }
    }
    
    const res = await generateFullArticle(sessionId.value, outlineSections, {
      target_word_count: targetWordCount.value,
      step5_supplements: step5Supplements,
      step6_materials: step6Materials,
    })
    if (res.data.code === 0 && res.data.data) {
      let articleData = res.data.data
      if (typeof articleData === 'string') {
        try {
          articleData = JSON.parse(articleData)
        } catch {
          articleData = { title: '完整文章', paragraphs: [{ title: '正文', content: articleData, word_count: 0 }] }
        }
      }
      articleResult.value = articleData
      loading.value = false
      setTimeout(() => {
        currentStep.value = 6
        Message.success('完整文章生成完成')
      }, 100)
    } else {
      console.error('文章生成失败 - 后端返回错误:', res.data)
      Message.error('生成失败: ' + (res.data.msg || '未知错误'))
      loading.value = false
    }
  } catch (e) {
    console.error('文章生成异常:', e)
    Message.error('生成失败: ' + (e.message || '未知错误'))
    loading.value = false
  }
}

function toggleArticleAiDialog(idx) {
  if (articleAiDialogIndex.value === idx) {
    articleAiDialogIndex.value = -1
    articleAiInput.value = ''
    articleAiResult.value = ''
    articleAiKbFiles.value = []
    articleAiUploadFiles.value = []
  } else {
    articleAiDialogIndex.value = idx
    articleAiInput.value = ''
    articleAiResult.value = ''
    articleAiKbFiles.value = []
    articleAiUploadFiles.value = []
  }
}

function handleArticleAiUpload(fileList) {
  articleAiUploadFiles.value = fileList || []
}

async function aiAdjustArticleParagraph(idx) {
  const para = articleResult.value?.paragraphs?.[idx]
  if (!para) return
  articleAiLoading.value = true
  articleAiResult.value = ''
  try {
    const context = [
      `段落标题：${para.title}`,
      `当前内容：${para.content?.substring(0, 500)}...`,
      articleAiInput.value ? `用户调整需求：${articleAiInput.value}` : '',
      articleAiKbFiles.value?.length ? `参考知识库文件：${articleAiKbFiles.value.join(', ')}` : '',
      articleAiUploadFiles.value?.length ? `参考上传文件：${articleAiUploadFiles.value.map(f => f.name || f).join(', ')}` : '',
    ].filter(Boolean).join('\n')
    const res = await apiInferSupplement(sessionId.value, para.title, {
      mcp_summary: mcpSummary.value || '',
      existing_content: context,
    })
    if (res.data.code === 0 && res.data.data?.content) {
      articleAiResult.value = res.data.data.content
      Message.success('AI 调整内容已生成')
    } else {
      Message.error('AI 生成失败: ' + (res.data.msg || '未知错误'))
    }
  } catch (e) {
    Message.error('AI 生成失败: ' + e.message)
  } finally {
    articleAiLoading.value = false
  }
}

function acceptArticleAiSuggestion(idx) {
  if (!articleAiResult.value || !articleResult.value?.paragraphs?.[idx]) return
  articleResult.value.paragraphs[idx].content = articleAiResult.value
  articleAiDialogIndex.value = -1
  articleAiInput.value = ''
  articleAiResult.value = ''
  articleAiKbFiles.value = []
  articleAiUploadFiles.value = []
  Message.success('段落已替换')
}

async function articleOneClickRegenerate() {
  if (!articleResult.value?.paragraphs) return
  articleOneClickLoading.value = true
  try {
    const paragraphs = articleResult.value.paragraphs
    for (let i = 0; i < paragraphs.length; i++) {
      const para = paragraphs[i]
      const context = [
        `段落标题：${para.title}`,
        `核心要点：基于提纲生成`,
      ].join('\n')
      const res = await apiInferSupplement(sessionId.value, para.title, {
        mcp_summary: mcpSummary.value || '',
        existing_content: context,
      })
      if (res.data.code === 0 && res.data.data?.content) {
        paragraphs[i].content = res.data.data.content
      }
    }
    Message.success(`已重新生成 ${paragraphs.length} 个段落`)
  } catch (e) {
    Message.error('一键重新生成失败: ' + e.message)
  } finally {
    articleOneClickLoading.value = false
  }
}

function exportArticle() {
  if (!articleResult.value) {
    Message.warning('暂无文章可导出')
    return
  }
  let text = `# ${articleResult.value.title}\n\n`
  articleResult.value.paragraphs?.forEach((para, i) => {
    text += `## ${i + 1}. ${para.title}\n\n${para.content}\n\n`
  })
  const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${articleResult.value.title || '完整文章'}.md`
  a.click()
  URL.revokeObjectURL(url)
  Message.success('文章已导出')
}

async function skipToOutline() {
  console.log(' skipToOutline 被点击调用, currentStep:', currentStep.value)
  currentStep.value = 5
  await loadOutline()
}

// ===== 批量操作 =====

// 一键调用 AI-Pulse 检索全部缺失项
async function batchAiPulseSupplement() {
  const missingItems = completenessResult.value.missing_critical || []
  if (missingItems.length === 0) {
    Message.warning('没有需要补充的缺失项')
    return
  }

  batchAiPulseLoading.value = true
  batchAiPulseResults.value = []

  // 为每个缺失项调用 API 检索
  for (let i = 0; i < missingItems.length; i++) {
    const item = missingItems[i]
    batchAiPulseResults.value.push({ item, cases: [], loading: true })

    try {
      const keyword = typeof item === 'string' ? item.substring(0, 10) : 'AI'
      const res = await apiAiPulseSupplement(sessionId.value, item, [keyword])
      if (res.data.code === 0) {
        batchAiPulseResults.value[i].cases = res.data.data?.cases || []
      }
    } catch (e) {
      console.warn(`检索 "${item}" 失败:`, e)
      batchAiPulseResults.value[i].cases = []
    }
    batchAiPulseResults.value[i].loading = false
  }

  batchAiPulseLoading.value = false
  batchAiPulseModalVisible.value = true
  Message.success(`检索完成，${missingItems.length} 个缺失项已检索完毕`)
}

// 保存批量检索结果到知识库
async function confirmBatchAiPulse() {
  let savedCount = 0
  for (let i = 0; i < batchAiPulseResults.value.length; i++) {
    const result = batchAiPulseResults.value[i]
    if (result.cases.length === 0) continue

    for (const c of result.cases) {
      const caseText = `【${c.title}】\n来源：${c.source}\n评分：${c.score}\n摘要：${c.summary}\n链接：${c.url}`
      try {
        const addRes = await apiAddSupplement(
          sessionId.value,
          'case',
          result.item,
          caseText,
          'ai-pulse',
          { title: c.title, source: c.source, score: c.score, url: c.url },
          c.tags || [],
        )
        const suppId = addRes.data.data.supplement_id
        await apiConfirmSupplement(sessionId.value, suppId)
        savedCount++
      } catch (e) {
        console.warn(`保存案例 "${c.title}" 失败:`, e)
      }
    }

    // 标记该缺失项为已补充
    const missingItems = completenessResult.value.missing_critical || []
    const idx = missingItems.indexOf(result.item)
    if (idx >= 0) {
      supplementContents.value[idx] = {
        content: `${result.cases.length} 个 AI-Pulse 案例`,
        method: 'ai-pulse',
        time: new Date().toLocaleString(),
      }
    }
  }

  batchAiPulseModalVisible.value = false
  Message.success(`已保存 ${savedCount} 个案例到知识库`)
  
  // 重新评估完整度
  await reEvaluateCompleteness()
}

// 一键手动补充
function batchManualSupplement() {
  console.log('========================================')
  console.log('🔴 batchManualSupplement 被点击调用')
  console.log('batchManualLoading:', batchManualLoading.value)
  console.log('completenessResult:', completenessResult.value)
  console.log('missing_critical:', completenessResult.value?.missing_critical)
  console.log('========================================')
  
  const missingItems = completenessResult.value.missing_critical || []
  if (missingItems.length === 0) {
    console.log('⚠️ missing_critical 为空，无法打开弹窗')
    Message.warning('没有需要补充的缺失项')
    return
  }

  // 初始化所有缺失项的文本框
  batchManualTexts.value = {}
  missingItems.forEach((item, i) => {
    if (!batchManualTexts.value[i]) {
      batchManualTexts.value[i] = ''
    }
  })

  console.log('✅ 准备打开弹窗，batchManualModalVisible 设为 true')
  batchManualModalVisible.value = true
}

async function confirmBatchManual() {
  const missingItems = completenessResult.value.missing_critical || []
  let savedCount = 0

  for (const [indexStr, text] of Object.entries(batchManualTexts.value)) {
    if (!text.trim()) continue
    const idx = parseInt(indexStr)
    const item = missingItems[idx]

    try {
      const res = await apiAddSupplement(
        sessionId.value,
        'supplement',
        item,
        text,
        'manual',
        {},
        [],
      )
      const suppId = res.data.data.supplement_id
      await apiConfirmSupplement(sessionId.value, suppId)

      supplementContents.value[idx] = {
        content: text.substring(0, 100) + (text.length > 100 ? '...' : ''),
        method: 'manual',
        time: new Date().toLocaleString(),
      }
      savedCount++
    } catch (e) {
      console.warn(`保存 "${item}" 失败:`, e)
    }
  }

  batchManualModalVisible.value = false
  Message.success(`已保存 ${savedCount} 项补充内容`)
  
  // 重新评估完整度
  await reEvaluateCompleteness()
}

// 一键补充所有关键缺失项（使用 smartSupplement + 实际检索）
async function supplementAllCritical() {
  const missingItems = completenessResult.value.missing_critical || []
  const unSupplementedItems = missingItems.filter((_, idx) => !isSupplemented(idx))
  
  console.log('[一键补充调试] missingItems:', missingItems)
  console.log('[一键补充调试] supplementContents:', supplementContents.value)
  console.log('[一键补充调试] unSupplementedItems:', unSupplementedItems)
  
  if (unSupplementedItems.length === 0) {
    Message.warning('没有需要补充的缺失项')
    return
  }
  
  supplementAllLoading.value = true
  
  try {
    // 构建上下文
    const context = `
MCP 摘要：
${mcpSummary.value || '无'}

已选择方向：${selectedDirection.value?.name || '无'}
已选择框架：${selectedFramework.value?.name || '无'}
`
    
    // 第一步：对每个缺失项执行检索 + smartSupplement
    const supplementResults = []
    const refusalResults = []
    
    for (const item of unSupplementedItems) {
      try {
        // Step 1: 先调用 AI-Pulse 检索
        const keyword = typeof item === 'string' ? item.substring(0, 10) : (item.label || item.dimension || 'AI')
        let retrievalResults = []
        try {
          const apiRes = await apiAiPulseSupplement(sessionId.value, item, [keyword])
          if (apiRes.data.code === 0) {
            retrievalResults = apiRes.data.data?.cases || []
          }
        } catch (e) {
          console.warn(`AI-Pulse 检索 "${item}" 失败:`, e)
        }
        
        // Step 2: 使用 smartSupplement（传入检索结果）
        const topic = typeof item === 'string' ? item : (item.label || item.dimension || '')
        const smartRes = await apiSmartSupplement(
          sessionId.value,
          topic,
          context,
          missingItems,
          item,
          null,  // forceLevel
          retrievalResults,
        )
        
        console.log(`[一键补充-debug] item=${topic}, code=${smartRes.data.code}, data=`, smartRes.data.data)
        
        if (smartRes.data.code === 0) {
          const data = smartRes.data.data
          
          // 拒补模式
          if (data.mode === 'refuse') {
            refusalResults.push({
              item: item,
              alertMessage: data.alert_message || '未检索到相关资料',
              questions: data.questions || [],
              index: missingItems.indexOf(item),
            })
            console.log(`[一键补充-debug] ${topic} -> 拒补模式`)
            continue
          }
          
          // 根据不同知识级别提取内容
          let content = ''
          let sourceType = ''
          let confidence = 0.7
          
          const levelInfo = {
            L0: { tag: '知识充足', color: '#00b42a' },
            L1: { tag: '通用模式推导', color: '#165dff' },
            L2: { tag: '引导问题', color: '#ff7d00' },
            L3: { tag: '类比推导', color: '#722ed1' },
            L4: { tag: '逻辑框架', color: '#f53f3f' },
          }
          const info = levelInfo[data.knowledge_level] || { tag: data.knowledge_level, color: '#86909c' }
          sourceType = info.tag
          
          if (data.content) {
            content = data.content
          } else if (data.questions?.length) {
            content = data.questions.map((q, i) => `${i + 1}. ${q.question}${q.hint ? '（' + q.hint + '）' : ''}`).join('\n')
          } else if (data.analogy) {
            content = data.analogy
          } else if (data.framework?.dimensions?.length) {
            content = data.framework.dimensions.map((d, i) => `${i + 1}. ${d.name}: ${d.hint || ''}`).join('\n')
          }
          
          console.log(`[一键补充-debug] ${topic} -> content长度=${content.length}, knowledge_level=${data.knowledge_level}`)
          
          if (content) {
            supplementResults.push({
              item: item,
              content: content,
              confidence: confidence,
              sourceType: sourceType,
              sourceColor: info.color,
              knowledgeLevel: data.knowledge_level,
              casesCount: retrievalResults.length,
              inferenceNote: data.assessment_reason || '',
              index: missingItems.indexOf(item),
            })
          }
        } else {
          console.warn(`[一键补充-debug] ${topic} -> API返回错误: code=${smartRes.data.code}, msg=${smartRes.data.msg}`)
        }
      } catch (e) {
        console.warn(`处理 "${item}" 补充失败:`, e)
      }
    }
    
    supplementAllLoading.value = false
    
    console.log(`[一键补充-debug] 最终结果: supplementResults=${supplementResults.length}, refusalResults=${refusalResults.length}`)
    
    if (supplementResults.length === 0 && refusalResults.length === 0) {
      Message.error('未能生成任何补充内容，请重试')
      return
    }
    
    // 第二步：弹窗确认
    const confirmResult = await showSupplementAllConfirmDialogV2(supplementResults, refusalResults)
    
    // 第三步：保存用户确认的补充内容
    if (confirmResult.accepted.length > 0) {
      let successCount = 0
      for (const result of confirmResult.accepted) {
        try {
          const addRes = await apiAddSupplement(
            sessionId.value,
            'supplement',
            result.item,
            result.content,
            result.sourceType || 'smart',
            { 
              inference_note: result.inferenceNote, 
              cases_count: result.casesCount,
              confidence: result.confidence,
              knowledge_level: result.knowledgeLevel,
            },
            [],
          )
          const suppId = addRes.data.data.supplement_id
          await apiConfirmSupplement(sessionId.value, suppId)
          
          const contentStr = typeof result.content === 'string' ? result.content : JSON.stringify(result.content)
          supplementContents.value[result.index] = {
            content: contentStr.substring(0, 100) + (contentStr.length > 100 ? '...' : ''),
            method: result.sourceType || 'smart',
            time: new Date().toLocaleString(),
          }
          successCount++
        } catch (e) {
          console.warn(`保存 "${result.item}" 失败:`, e)
        }
      }
      
      const skippedCount = confirmResult.skipped.length
      Message.success(`已保存 ${successCount} 项补充${skippedCount > 0 ? `，跳过 ${skippedCount} 项` : ''}`)
      
      // 重新评估完整度
      await reEvaluateCompleteness()
    } else {
      Message.info('已取消所有补充')
    }
    
  } catch (e) {
    Message.error('一键补充失败: ' + e.message)
  } finally {
    supplementAllLoading.value = false
  }
}

// 一键补充确认弹窗
function showSupplementAllConfirmDialog(results) {
  return new Promise((resolve) => {
    const accepted = []
    const skipped = []
    
    // 使用 Arco Design 的 Modal 确认
    const modal = Modal.confirm({
      title: '一键补充结果预览',
      width: '900px',
      content: () => h('div', { style: 'max-height: 500px; overflow-y: auto; padding-right: 12px' }, [
        h('p', { style: 'margin-bottom: 16px; color: #86909c; font-size: 13px' }, 
          `已生成 ${results.length} 项补充内容，请逐项确认是否采纳：`),
        results.map((result, idx) => h('div', {
          key: idx,
          style: 'padding: 14px; margin-bottom: 10px; background: #f7f8fa; border-radius: 6px; border-left: 4px solid ' + 
                 (result.sourceType === 'API+AI推断' ? '#165dff' : '#ff7d00')
        }, [
          // 标题行
          h('div', { style: 'display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px' }, [
            h('strong', { style: 'font-size: 14px; color: #1d2129' }, `【${result.item}】`),
            h('div', { style: 'display: flex; gap: 6px; align-items: center' }, [
              h('span', { 
                style: 'padding: 2px 8px; border-radius: 12px; font-size: 11px; background: ' + 
                       (result.sourceType === 'API+AI推断' ? '#e8f3ff; color: #165dff' : '#fff7e6; color: #ff7d00') 
              }, result.sourceType === 'API+AI推断' ? '🔍 API+AI推断' : '🤖 纯AI推理'),
              h('span', { 
                style: 'padding: 2px 8px; border-radius: 12px; font-size: 11px; background: ' + 
                       (result.confidence >= 0.8 ? '#f0f9f4; color: #00b42a' : result.confidence >= 0.6 ? '#fff7e6; color: #ff7d00' : '#fff2f0; color: #f53f3f') 
              }, `置信度 ${(result.confidence * 100).toFixed(0)}%`),
            ]),
          ]),
          // 案例数量提示
          result.casesCount > 0 ? h('div', { style: 'font-size: 12px; color: #86909c; margin-bottom: 6px' }, 
            `基于 ${result.casesCount} 个外部案例生成`) : null,
          // 内容预览
          h('div', { style: 'padding: 8px 12px; background: #fff; border-radius: 4px; font-size: 13px; line-height: 1.6; color: #4e5969; max-height: 100px; overflow-y: auto; margin-bottom: 6px' }, 
            (() => {
              const text = typeof result.content === 'string' ? result.content : JSON.stringify(result.content)
              return text.slice(0, 200) + (text.length > 200 ? '...' : '')
            })()),
          // 推断说明
          result.inferenceNote ? h('div', { style: 'font-size: 12px; color: #86909c; font-style: italic' }, 
            (() => {
              const note = typeof result.inferenceNote === 'string' ? result.inferenceNote : JSON.stringify(result.inferenceNote)
              return `注：${note.slice(0, 100)}${note.length > 100 ? '...' : ''}`
            })()) : null,
        ])),
      ]),
      okText: `采纳全部 (${results.length} 项)`,
      cancelText: '全部跳过',
      onOk: () => {
        resolve({ accepted: results, skipped: [] })
      },
      onCancel: () => {
        resolve({ accepted: [], skipped: results })
      },
    })
  })
}

// 新版一键补充确认弹窗（支持补充结果 + 拒补结果）
function showSupplementAllConfirmDialogV2(supplementResults, refusalResults) {
  return new Promise((resolve) => {
    const allItems = []
    const refusalMap = new Map()
    
    // 标记拒补项
    for (const r of refusalResults) {
      refusalMap.set(r.item, r)
    }
    
    // 构建可补充项列表
    for (const r of supplementResults) {
      allItems.push({ ...r, status: 'supplement', key: r.index })
    }
    // 构建拒补项列表
    for (const r of refusalResults) {
      allItems.push({ ...r, status: 'refusal', key: 'refusal_' + r.index })
    }
    
    const accepted = []
    const skipped = []
    
    const modal = Modal.confirm({
      title: `一键补充结果（${supplementResults.length} 项可补充，${refusalResults.length} 项需手动）`,
      width: '900px',
      content: () => h('div', { style: 'max-height: 500px; overflow-y: auto; padding-right: 12px' }, [
        // 补充结果
        supplementResults.length > 0 ? h('div', null, [
          h('p', { style: 'margin-bottom: 12px; color: #00b42a; font-size: 13px; font-weight: 500' },
            `✅ 以下 ${supplementResults.length} 项已生成补充内容，请确认是否采纳：`),
          supplementResults.map((result, idx) => h('div', {
            key: idx,
            style: 'padding: 14px; margin-bottom: 10px; background: #f7f8fa; border-radius: 6px; border-left: 4px solid ' + (result.sourceColor || '#165dff')
          }, [
            h('div', { style: 'display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px' }, [
              h('strong', { style: 'font-size: 14px; color: #1d2129' }, `【${result.item}】`),
              h('span', {
                style: 'padding: 2px 8px; border-radius: 12px; font-size: 11px; background: #e8f3ff; color: #165dff'
              }, result.sourceType),
            ]),
            result.casesCount > 0 ? h('div', { style: 'font-size: 12px; color: #86909c; margin-bottom: 6px' },
              `基于 ${result.casesCount} 个外部案例`) : null,
            h('div', { style: 'padding: 8px 12px; background: #fff; border-radius: 4px; font-size: 13px; line-height: 1.6; color: #4e5969; max-height: 100px; overflow-y: auto; margin-bottom: 6px' },
              (() => {
                const text = typeof result.content === 'string' ? result.content : JSON.stringify(result.content)
                return text.slice(0, 200) + (text.length > 200 ? '...' : '')
              })()),
            result.inferenceNote ? h('div', { style: 'font-size: 12px; color: #86909c; font-style: italic' },
              (() => {
                const note = typeof result.inferenceNote === 'string' ? result.inferenceNote : JSON.stringify(result.inferenceNote)
                return `注：${note.slice(0, 100)}${note.length > 100 ? '...' : ''}`
              })()) : null,
          ])),
        ]) : null,
        
        // 拒补结果
        refusalResults.length > 0 ? h('div', { style: 'margin-top: 16px' }, [
          h('p', { style: 'margin-bottom: 12px; color: #f53f3f; font-size: 13px; font-weight: 500' },
            `❌ 以下 ${refusalResults.length} 项未检索到资料，无法自动补充：`),
          refusalResults.map((r, idx) => h('div', {
            key: idx,
            style: 'padding: 12px; margin-bottom: 8px; background: #fff2f0; border-radius: 6px; border-left: 4px solid #f53f3f'
          }, [
            h('strong', { style: 'font-size: 14px; color: #1d2129' }, `【${r.item}】`),
            h('div', { style: 'margin-top: 6px; font-size: 13px; color: #f53f3f' }, r.alertMessage),
            r.questions?.length > 0 ? h('div', { style: 'margin-top: 8px; font-size: 12px; color: #86909c' },
              '引导问题：' + r.questions.map(q => q.question).join('；')) : null,
          ])),
        ]) : null,
      ]),
      okText: supplementResults.length > 0 ? `采纳可补充的 ${supplementResults.length} 项` : '我知道了',
      cancelText: '全部跳过',
      onOk: () => {
        resolve({ accepted: supplementResults, skipped: refusalResults })
      },
      onCancel: () => {
        resolve({ accepted: [], skipped: allItems })
      },
    })
  })
}

// ===== 需求1：统一补充功能（合并 API检索 + 推断） =====

// 统一弹窗：打开单个缺失项的补充
async function openUnifiedSupplementModal(index) {
  console.log('========================================')
  console.log(' [DEBUG] openUnifiedSupplementModal 被调用')
  console.log('🔴 缺失项索引:', index)
  console.log('========================================')
  
  const missingItems = completenessResult.value.missing_critical || []
  if (!missingItems[index]) {
    Message.warning('缺失项不存在')
    return
  }
  
  unifiedModalItemIndex.value = index
  unifiedModalItem.value = missingItems[index]
  unifiedModalStep.value = 1
  unifiedApiCases.value = []
  unifiedApiSelected.value = []
  unifiedInferResult.value = null
  unifiedModalVisible.value = true
  
  // 自动开始 API 检索
  await unifiedApiSearch()
}

// 统一弹窗：API 检索
async function unifiedApiSearch() {
  unifiedApiLoading.value = true
  try {
    const keyword = typeof unifiedModalItem.value === 'string' ? unifiedModalItem.value.substring(0, 10) : 'AI'
    const res = await apiAiPulseSupplement(sessionId.value, unifiedModalItem.value, [keyword])
    if (res.data.code === 0) {
      unifiedApiCases.value = res.data.data?.cases || []
      unifiedApiSelected.value = unifiedApiCases.value.map(() => true) // 默认全选
    }
  } catch (e) {
    console.warn('API 检索失败:', e)
    unifiedApiCases.value = []
  } finally {
    unifiedApiLoading.value = false
  }
}

// 统一弹窗：全选/取消全选
function toggleUnifiedSelectAll() {
  const allSelected = unifiedApiSelected.value.every(Boolean)
  unifiedApiSelected.value = unifiedApiCases.value.map(() => !allSelected)
}

// 统一弹窗：进入推断步骤
async function goToUnifiedInfer() {
  const selectedCases = unifiedApiCases.value.filter((_, i) => unifiedApiSelected.value[i])
  
  unifiedModalStep.value = 2
  unifiedInferLoading.value = true
  unifiedInferResult.value = null
  
  try {
    const res = await apiInferSupplement(sessionId.value, unifiedModalItem.value, {
      cases: selectedCases,
      mcp_summary: mcpSummary.value,
    })
    if (res.data.code === 0) {
      unifiedInferResult.value = res.data.data
    } else {
      Message.error('推断失败: ' + (res.data.msg || '未知错误'))
    }
  } catch (e) {
    console.error('推断异常:', e)
    Message.error('推断失败: ' + e.message)
  } finally {
    unifiedInferLoading.value = false
  }
}

// 统一弹窗：跳过 API，直接推断
async function goToUnifiedInferNoCases() {
  unifiedModalStep.value = 2
  unifiedInferLoading.value = true
  unifiedInferResult.value = null
  
  try {
    const res = await apiInferSupplement(sessionId.value, unifiedModalItem.value, {
      cases: [],
      mcp_summary: mcpSummary.value,
    })
    if (res.data.code === 0) {
      unifiedInferResult.value = res.data.data
    } else {
      Message.error('推断失败: ' + (res.data.msg || '未知错误'))
    }
  } catch (e) {
    console.error('推断异常:', e)
    Message.error('推断失败: ' + e.message)
  } finally {
    unifiedInferLoading.value = false
  }
}

// 统一弹窗：确认并保存
async function confirmUnifiedSupplement() {
  if (!unifiedInferResult.value?.content) {
    Message.warning('没有可保存的内容')
    return
  }
  
  unifiedSaving.value = true
  try {
    // 保存到知识库
    const addRes = await apiAddSupplement(
      sessionId.value,
      'text',
      unifiedModalItem.value,
      unifiedInferResult.value.content,
      'ai-infer',
      { inference_note: unifiedInferResult.value.inference_note },
      [],
    )
    const suppId = addRes.data.data.supplement_id
    await apiConfirmSupplement(sessionId.value, suppId)
    
    // 标记为已补充
    const idx = unifiedModalItemIndex.value
    if (idx >= 0) {
      supplementContents.value[idx] = {
        content: unifiedInferResult.value.content.substring(0, 100) + '...',
        method: 'ai-infer',
        time: new Date().toLocaleString(),
      }
    }
    
    unifiedModalVisible.value = false
    Message.success('已保存补充内容')
    
    // 重新评估完整度
    await reEvaluateCompleteness()
  } catch (e) {
    console.error('保存失败:', e)
    Message.error('保存失败: ' + e.message)
  } finally {
    unifiedSaving.value = false
  }
}

// 统一弹窗：关闭
function closeUnifiedModal() {
  unifiedModalVisible.value = false
  unifiedModalStep.value = 1
  unifiedApiCases.value = []
  unifiedApiSelected.value = []
  unifiedInferResult.value = null
}

// ===== 草稿模式函数（Step 3 起草用） =====

// 打开草稿弹窗
async function openDraftModal(index) {
  const missingItems = completenessResult.value.missing_critical || []
  if (!missingItems[index]) {
    Message.warning('缺失项不存在')
    return
  }
  
  draftModalItemIndex.value = index
  draftModalItem.value = missingItems[index]
  draftContent.value = ''
  draftModalVisible.value = true
  draftLoading.value = true
  
  try {
    const res = await apiSupplementDraft(
      sessionId.value,
      selectedDirection.value?.name || '',
      selectedFramework.value?.name || '',
      missingItems[index],
      '',
    )
    if (res.data.code === 0) {
      // 去除开头的警告语，因为弹窗已经有 alert 了
      let text = res.data.data.text || ''
      const warningPrefix = '️ 以下为AI基于通用模式的推导参考，请核实后使用。'
      if (text.startsWith(warningPrefix)) {
        text = text.substring(warningPrefix.length).trim()
      }
      draftContent.value = text
    } else {
      // 失败时不关闭弹窗，显示错误提示，用户可以手动编辑或取消
      draftContent.value = `草稿生成失败：${res.data.msg || '未知错误'}\n\n你可以手动在下方输入框中补充内容，或点击取消。`
    }
  } catch (e) {
    console.error('草稿生成异常:', e)
    // 异常时也不关闭弹窗
    draftContent.value = `草稿生成异常：${e.message}\n\n你可以手动在下方输入框中补充内容，或点击取消。`
  } finally {
    draftLoading.value = false
  }
}

// 确认草稿补充
async function confirmDraftSupplement() {
  if (!draftContent.value) {
    Message.warning('没有可保存的内容')
    return
  }
  
  draftSaving.value = true
  try {
    // 保存到知识库，标记为 ai-draft
    const addRes = await apiAddSupplement(
      sessionId.value,
      'text',
      draftModalItem.value,
      draftContent.value,
      'ai-draft',
      {},
      [],
    )
    const suppId = addRes.data.data.supplement_id
    
    // 标记为已补充
    const confirmRes = await apiConfirmSupplement(sessionId.value, suppId, true)
    if (confirmRes.data.code === 0) {
      Message.success('已保存，标记为「用户确认草稿」')
      closeDraftModal()
      reEvaluateCompleteness()
    } else {
      Message.error('保存失败: ' + (confirmRes.data.msg || '未知错误'))
    }
  } catch (e) {
    console.error('保存草稿异常:', e)
    Message.error('保存失败: ' + e.message)
  } finally {
    draftSaving.value = false
  }
}

// 关闭草稿弹窗
function closeDraftModal() {
  draftModalVisible.value = false
  draftContent.value = ''
  draftModalItem.value = ''
  draftModalItemIndex.value = -1
}

// ===== 结束草稿模式函数 =====

// 批量统一补充结果弹窗
const batchResultModalVisible = ref(false)
const batchResults = ref([]) // [{ item, content, method, apiCount, note }]

// 批量统一补充（所有缺失项：API检索 + AI推断）
async function batchUnifiedSupplement() {
  console.log('========================================')
  console.log(' [DEBUG] batchUnifiedSupplement 被调用')
  console.log('========================================')
  
  const missingItems = completenessResult.value.missing_critical || []
  if (missingItems.length === 0) {
    Message.warning('没有需要补充的缺失项')
    return
  }
  
  batchUnifiedLoading.value = true
  Message.info(`正在为 ${missingItems.length} 个缺失项进行 AI-Pulse 检索 + 推断...`)
  
  let savedCount = 0
  let skippedCount = 0
  
  batchResults.value = []
  
  for (let i = 0; i < missingItems.length; i++) {
    const item = missingItems[i]
    const keyword = typeof item === 'string' ? item.substring(0, 10) : 'AI'
    
    try {
      // Step 1: API 检索
      let apiCases = []
      try {
        const res = await apiAiPulseSupplement(sessionId.value, item, [keyword])
        if (res.data.code === 0) {
          apiCases = res.data.data?.cases || []
        }
      } catch (e) {
        console.warn(`缺失项 "${item}" API 检索失败，将使用纯 AI 推断`)
      }
      
      // Step 2: AI 推断
      const inferRes = await apiInferSupplement(sessionId.value, item, {
        cases: apiCases,
        mcp_summary: mcpSummary.value,
      })
      
      if (inferRes.data.code === 0 && inferRes.data.data?.content) {
        const content = inferRes.data.data.content
        const method = apiCases.length > 0 ? 'ai-pulse+infer' : 'ai-infer'
        const apiCount = apiCases.length
        
        // Step 3: 自动保存
        const addRes = await apiAddSupplement(
          sessionId.value,
          'text',
          item,
          content,
          method,
          { inference_note: inferRes.data.data.inference_note, api_count: apiCount },
          [],
        )
        const suppId = addRes.data.data.supplement_id
        await apiConfirmSupplement(sessionId.value, suppId)
        
        supplementContents.value[i] = {
          content: content.substring(0, 100) + '...',
          method: method,
          time: new Date().toLocaleString(),
        }
        
        batchResults.value.push({
          item: item,
          content: content,
          method: method,
          apiCount: apiCount,
          note: inferRes.data.data.inference_note || '',
        })
        savedCount++
      } else {
        skippedCount++
      }
    } catch (e) {
      console.error(`缺失项 "${item}" 处理失败:`, e)
      skippedCount++
    }
  }
  
  batchUnifiedLoading.value = false
  
  if (savedCount > 0) {
    batchResultModalVisible.value = true
  } else {
    Message.warning('所有缺失项均无法自动补充，请尝试手动补充')
  }
}

// 关闭批量结果弹窗并继续
function closeBatchResultModal() {
  batchResultModalVisible.value = false
  reEvaluateCompleteness()
}

// ===== 结束统一补充功能 =====

async function confirmOutline() {
  // P1 预留：显示收藏弹窗
  showExportModal.value = true
}

// ===== 需求3：框架 AI 建议 =====
async function getFrameworkAiSuggestion(framework) {
  console.log('🔴 [DEBUG] getFrameworkAiSuggestion 被调用')
  frameworkAiLoading.value = true
  frameworkSelectedIndex.value = frameworks.value.indexOf(framework)
  try {
    const res = await apiInferSupplement(sessionId.value, framework.name, {
      cases: [],
      mcp_summary: mcpSummary.value,
    })
    if (res.data.code === 0 && res.data.data?.content) {
      frameworkAiSuggestion.value = res.data.data.content
      Message.success('AI 框架建议已生成')
    } else {
      Message.error('AI 建议生成失败: ' + (res.data.msg || '未知错误'))
    }
  } catch (e) {
    console.error('AI 框架建议异常:', e)
    Message.error('AI 建议生成失败: ' + e.message)
  } finally {
    frameworkAiLoading.value = false
  }
}

// ===== 图3：框架 AI 补充 =====
async function applyFrameworkAiSuggestion(framework) {
  console.log('🔴 [DEBUG] applyFrameworkAiSuggestion 被调用')
  
  if (!frameworkAiSuggestion.value) {
    Message.warning('没有可保存的 AI 建议')
    return
  }
  
  loading.value = true
  try {
    // Step 1: 保存补充内容到知识库
    const addRes = await apiAddSupplement(
      sessionId.value,
      'framework',
      framework.name,
      frameworkAiSuggestion.value,
      'ai-framework',
      { inference_note: frameworkAiSuggestion.value },
      [],
    )
    const suppId = addRes.data.data.supplement_id
    await apiConfirmSupplement(sessionId.value, suppId)
    
    // Step 2: 标记该框架的补充项为已补充
    const needsSupplement = framework.needs_supplement || []
    needsSupplement.forEach((item, idx) => {
      supplementContents.value[idx] = {
        content: frameworkAiSuggestion.value.substring(0, 100) + '...',
        method: 'ai-framework',
        time: new Date().toLocaleString(),
      }
    })
    
    // Step 3: 重新评估完整度
    await reEvaluateCompleteness()
    
    // Step 1: 设置选中的框架并保持在补充页面
    selectedFramework.value = framework
    // 自动预检测缺失项
    setTimeout(() => {
      currentStep.value = 1
      runPreCheck()
      Message.success(`「${framework.name}」AI 补充完成，已自动保存`)
    }, 100)
  } catch (e) {
    console.error('框架 AI 补充失败:', e)
    Message.error('AI 补充失败: ' + e.message)
  } finally {
    loading.value = false
    frameworkAiSuggestion.value = ''
  }
}

// ===== 需求4：检测问题 AI 帮助 =====
async function getIssueAiHelp(issue, index) {
  console.log('🔴 [DEBUG] getIssueAiHelp 被调用')
  if (!issueAiHelp.value[index]) {
    issueAiHelp.value[index] = { loading: true, suggestion: '' }
  } else {
    issueAiHelp.value[index].loading = true
  }
  
  try {
    const res = await apiInferSupplement(sessionId.value, `检测问题：${issue.title}`, {
      cases: [],
      mcp_summary: `${mcpSummary.value}\n\n【问题描述】${issue.description}\n【当前建议】${issue.suggestion}`,
    })
    if (res.data.code === 0 && res.data.data?.content) {
      issueAiHelp.value[index].suggestion = res.data.data.content
      issueAiHelp.value[index].loading = false
      Message.success('AI 详细分析已生成')
    } else {
      issueAiHelp.value[index].loading = false
      Message.error('AI 分析失败: ' + (res.data.msg || '未知错误'))
    }
  } catch (e) {
    console.error('AI 详细分析异常:', e)
    issueAiHelp.value[index].loading = false
    Message.error('AI 分析失败: ' + e.message)
  }
}

// ===== 需求5：结构 AI 辅助 =====
async function getStructureAiSuggestion() {
  console.log('🔴 [DEBUG] getStructureAiSuggestion 被调用')
  structureAiLoading.value = true
  try {
    const needsSupplement = selectedStructure.value.needs_supplement?.join('、') || ''
    const res = await apiInferSupplement(sessionId.value, `结构补充：${selectedStructure.value.name}`, {
      cases: [],
      mcp_summary: `${mcpSummary.value}\n\n【结构名称】${selectedStructure.value.name}\n【需要补充】${needsSupplement}`,
    })
    if (res.data.code === 0 && res.data.data?.content) {
      structureAiSuggestion.value = res.data.data.content
      Message.success('AI 结构建议已生成')
    } else {
      Message.error('AI 建议生成失败: ' + (res.data.msg || '未知错误'))
    }
  } catch (e) {
    console.error('AI 结构建议异常:', e)
    Message.error('AI 建议生成失败: ' + e.message)
  } finally {
    structureAiLoading.value = false
  }
}

// ===== 图4：AI 智能补充全部问题 =====
const aiSupplementAllLoading = ref(false)

async function aiSupplementAllIssues() {
  console.log(' [DEBUG] aiSupplementAllIssues 被调用')
  
  if (!directionCheckResult.value || !Array.isArray(directionCheckResult.value)) {
    Message.warning('请先进行方向检测')
    return
  }
  
  const problems = directionCheckResult.value.filter(issue => issue.type !== 'pass')
  if (problems.length === 0) {
    Message.success('没有需要补充的问题')
    return
  }
  
  aiSupplementAllLoading.value = true
  Message.info(`正在为 ${problems.length} 个问题生成 AI 补充内容...`)
  
  let savedCount = 0
  
  for (const issue of problems) {
    try {
      // 调用 AI 推断生成补充内容
      const res = await apiInferSupplement(sessionId.value, `检测问题修复：${issue.title}`, {
        cases: [],
        mcp_summary: `${mcpSummary.value}\n\n【问题描述】${issue.description}\n【建议】${issue.suggestion || ''}`,
      })
      
      if (res.data.code === 0 && res.data.data?.content) {
        // 将补充内容追加到 supplement2Text 中，而不是调用 apiAddSupplement
        supplement2Text.value += (supplement2Text.value ? '\n\n' : '') + `【${issue.title}】\n${res.data.data.content}`
        savedCount++
      }
    } catch (e) {
      console.error(`问题 "${issue.title}" 修复失败:`, e)
    }
  }
  
  aiSupplementAllLoading.value = false
  
  if (savedCount > 0) {
    Message.success(`完成！${savedCount} 个问题已自动修复`)
    // 打印补充后的完整文本（前200字符）
    console.log('========================================')
    console.log(' [DEBUG] 补充完成，supplement2Text 内容:')
    console.log(supplement2Text.value ? supplement2Text.value.substring(0, 300) : '(空)')
    console.log('========================================')
    // 补充完成后重新检测方向，更新页面显示
    await runDirectionCheck()
    console.log('🔴 重新检测后的结果:', directionCheckResult.value?.length, '项')
    if (directionCheckResult.value) {
      console.log('🔴 检测结果类型:', directionCheckResult.value.map(i => i.type).join(', '))
    }
  } else {
    Message.warning('所有问题均无法自动修复，请手动补充')
  }
}

function exportOutline() {
  Message.info('导出功能开发中')
}

async function handleExportToDomain() {
  if (!exportDomainTag.value) {
    Message.warning('请选择领域')
    return
  }

  exportingToDomain.value = true
  try {
    const { exportSupplementsToDomain } = await import('../utils/api')
    const res = await exportSupplementsToDomain(sessionId.value, exportDomainTag.value)
    Message.success(res.data.data.message || '领域知识库功能开发中，已记录您的选择')
  } catch (e) {
    console.error('导出到领域库失败:', e)
    Message.error('导出失败')
  } finally {
    exportingToDomain.value = false
    showExportModal.value = false

    // 跳转到预览页
    router.push({
      name: 'Preview',
      query: {
        sessionId: sessionId.value,
        direction: selectedDirection.value?.name,
        framework: selectedFramework.value?.name,
        structure: selectedStructure.value?.name,
      },
    })
  }
}

function skipExport() {
  showExportModal.value = false
  // 跳转到预览页
  router.push({
    name: 'Preview',
    query: {
      sessionId: sessionId.value,
      direction: selectedDirection.value?.name,
      framework: selectedFramework.value?.name,
      structure: selectedStructure.value?.name,
    },
  })
}

// ===== 生成配图 =====

// 框架名称到 key 的映射表
const FRAMEWORK_NAME_TO_KEY = {
  'SWOT 分析': 'swot',
  '商业模式画布': 'business_canvas',
  'PESTEL 分析': 'pestel',
  '用户旅程图': 'user_journey',
  '时间矩阵': 'time_matrix',
  '主张论证': 'claim',
  '因果分析': 'causal',
  '系统思考': 'system',
  '对比分析': 'comparison',
  '流程步骤': 'process',
}

// 从框架对象推导 key
function deriveFrameworkKey(framework) {
  console.log('[deriveFrameworkKey] 输入:', framework)
  if (!framework) {
    console.warn('[deriveFrameworkKey] 框架为空')
    return null
  }
  // 优先使用已有的 key
  if (framework.key) {
    console.log('[deriveFrameworkKey] 使用已有 key:', framework.key)
    return framework.key
  }
  // 从 name 精确匹配
  if (framework.name) {
    const key = FRAMEWORK_NAME_TO_KEY[framework.name]
    if (key) {
      console.log('[deriveFrameworkKey] 从 name 精确匹配:', framework.name, '->', key)
      return key
    }
    // 模糊匹配：检查 name 是否包含映射表中的任何 key 名称
    for (const [name, k] of Object.entries(FRAMEWORK_NAME_TO_KEY)) {
      if (framework.name.includes(name) || name.includes(framework.name)) {
        console.log('[deriveFrameworkKey] 从 name 模糊匹配:', framework.name, '->', k)
        return k
      }
    }
    console.warn('[deriveFrameworkKey] name 未匹配:', framework.name)
  }
  console.warn('[deriveFrameworkKey] 框架对象缺少 key 和 name 字段')
  return null
}

function goToGenerateImage() {
  if (!articleResult.value) {
    Message.warning('请先生成完整文章')
    return
  }
  generatedImageUrl.value = ''
  currentStep.value = 7
}

async function handleGenerateImage() {
  if (!articleResult.value) {
    Message.error('没有可生成图片的文章内容')
    return
  }
  
  imageGenerating.value = true
  
  try {
    // 将文章内容拼接为完整文本
    const fullText = articleResult.value.paragraphs
      .map(p => `## ${p.title}\n\n${p.content}`)
      .join('\n\n')
    
    // 推导框架 key：优先从 selectedFramework，其次从文章元数据
    let frameworkKey = deriveFrameworkKey(selectedFramework.value)
    
    // 如果推导失败，尝试从文章结果中获取
    if (!frameworkKey && articleResult.value.framework_key) {
      frameworkKey = articleResult.value.framework_key
    }
    
    // 最终回退到 swot（仅作保底，实际应该能推导出来）
    if (!frameworkKey) {
      console.warn('[图片生成] 无法推导框架 key，使用默认 swot')
      frameworkKey = 'swot'
    }
    
    console.log(`[图片生成] 使用框架: ${frameworkKey}`)
    
    const response = await apiGenerateDiagram({
      frameworkKey: frameworkKey,
      text: fullText,
      style: 'minimal',
      size: 'default',
    })
    
    const url = URL.createObjectURL(response.data)
    generatedImageUrl.value = url
    Message.success('配图生成成功！')
  } catch (e) {
    console.error('生成配图失败:', e)
    Message.error('生成配图失败: ' + (e.message || '未知错误'))
  } finally {
    imageGenerating.value = false
  }
}

function downloadGeneratedImage() {
  if (!generatedImageUrl.value) return
  
  const a = document.createElement('a')
  a.href = generatedImageUrl.value
  a.download = `${articleResult.value?.title || 'article'}_配图.png`
  a.click()
  Message.success('下载成功！')
}
</script>

<style scoped>
.workflow-view {
  width: 100%;
  max-width: 100%;
  margin: 0;
  padding: 20px 40px;
}

.progress-bar {
  margin-bottom: 24px;
  padding: 16px;
  background: #fff;
  border-radius: 8px;
}

.step-summary-list {
  margin-bottom: 24px;
  padding: 16px;
  background: #fff;
  border-radius: 8px;
}

.step-summary-item {
  padding: 12px 16px;
  margin-bottom: 8px;
  border-radius: 6px;
  transition: all 0.3s;
}

.step-summary-item:last-child {
  margin-bottom: 0;
}

.step-summary-item.is-completed {
  background: #f0f9ff;
  border-left: 3px solid #52c41a;
}

.step-summary-item.is-current {
  background: #e6f7ff;
  border-left: 3px solid #1890ff;
}

.step-summary-item.is-future {
  background: #f5f5f5;
  border-left: 3px solid #d9d9d9;
  opacity: 0.6;
}

.step-summary-header {
  display: flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.step-status-icon {
  margin-right: 8px;
  font-size: 16px;
}

.step-name {
  font-weight: 500;
  color: #262626;
}

.step-summary-text {
  margin-left: 8px;
  color: #595959;
  font-size: 14px;
}

.step-collapse-icon {
  margin-left: auto;
  color: #8c8c8c;
  font-size: 12px;
}

.step-summary-content {
  margin-top: 12px;
  padding: 12px;
  background: #fff;
  border-radius: 4px;
}

/* 步骤展开详情 */
.step-detail-content {
  margin-top: 8px;
  padding: 12px;
  background: #fff;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.8;
  color: #595959;
  white-space: pre-wrap;
}

.content-area {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
}

/* 补充页面特殊样式 - 满屏宽度 */
.step-content {
  min-height: 400px;
  width: 100%;
  max-width: 100%;
}

.step-content :deep(.arco-card) {
  width: 100%;
  max-width: 100%;
}

.mcp-summary {
  margin-top: 12px;
}

.summary-text {
  margin-top: 8px;
  padding: 12px;
  background: #f7f8fa;
  border-radius: 4px;
  line-height: 1.6;
  font-size: 14px;
}

.direction-card {
  margin-bottom: 16px;
}

.direction-desc {
  margin-top: 8px;
  font-size: 14px;
  line-height: 1.6;
}

.direction-reason {
  margin-top: 8px;
  font-size: 13px;
}

.missing-items {
  margin-top: 12px;
  padding: 8px;
  background: #fff2f0;
  border-radius: 4px;
}

.missing-items-optional {
  margin-top: 8px;
}

.framework-card,
.structure-card {
  margin-bottom: 16px;
}

.check-issue {
  margin-top: 12px;
}

.quick-form {
  max-width: 600px;
}

.outline-result {
  margin-top: 16px;
}

.section-detail {
  padding: 8px 0;
}

.ai-pulse-cases .case-title {
  font-weight: 500;
  font-size: 14px;
  margin-bottom: 4px;
}

.ai-pulse-cases .case-summary {
  font-size: 12px;
  color: #86909c;
  margin-bottom: 6px;
  line-height: 1.5;
}

.ai-pulse-cases .case-meta {
  display: flex;
  gap: 6px;
  align-items: center;
}

/* 生成配图容器样式 */
.generated-image-container {
  text-align: center;
  padding: 20px;
  background: #f7f8fa;
  border-radius: 8px;
  max-height: 70vh;
  overflow-y: auto;
  overflow-x: hidden;
}

.generated-image {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: inline-block;
}

/* 选题列表样式 */
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

/* 不同等级选题的样式区分 */
.topic-item.topic-excellent {
  border-color: #00b42a;
  background: linear-gradient(135deg, #f6ffed 0%, #ffffff 100%);
}

.topic-item.topic-excellent:hover {
  box-shadow: 0 4px 16px rgba(0, 180, 42, 0.2);
}

.topic-item.topic-good {
  border-color: #ff7d00;
  background: linear-gradient(135deg, #fff7e6 0%, #ffffff 100%);
}

.topic-item.topic-good:hover {
  box-shadow: 0 4px 16px rgba(255, 125, 0, 0.2);
}

.topic-item.topic-poor {
  border-color: #f53f3f;
  background: linear-gradient(135deg, #fff2f0 0%, #ffffff 100%);
}

.topic-item.topic-poor:hover {
  box-shadow: 0 4px 16px rgba(245, 63, 63, 0.2);
}

.topic-item.selected {
  border-color: #165dff !important;
  background: linear-gradient(135deg, #e8f3ff 0%, #ffffff 100%) !important;
  box-shadow: 0 0 0 3px rgba(22, 93, 255, 0.1);
}

/* 选题标题 */
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

/* 选题描述 */
.topic-desc {
  font-size: 14px;
  color: #4e5969;
  margin-bottom: 12px;
  line-height: 1.6;
}

/* 选题元信息 */
.topic-meta {
  margin-bottom: 12px;
}

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

/* 选题原因 */
.topic-reason {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  font-size: 13px;
  color: #4e5969;
  margin-bottom: 8px;
  line-height: 1.6;
}

/* 需要补充 */
.topic-needed {
  font-size: 13px;
  color: #f53f3f;
  padding: 8px 12px;
  background: #fff2f0;
  border-radius: 6px;
  margin-bottom: 12px;
}

.needed-label {
  font-weight: 600;
}

/* 评分卡片统一样式 */
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

.score-unit {
  font-size: 16px;
  font-weight: 500;
}

.score-desc {
  font-size: 12px;
  color: #4e5969;
  line-height: 1.6;
  text-align: left;
  flex: 1;
}

.score-details {
  flex: 1;
  text-align: left;
}

.detail-item {
  margin-bottom: 4px;
  line-height: 1.5;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #4e5969;
}

.score-tag {
  margin-top: auto;
  display: flex;
  justify-content: center;
}
</style>
