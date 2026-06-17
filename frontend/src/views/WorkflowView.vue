<template>
  <div class="workflow-view">
    <a-page-header title="智能写作工作流" @back="$router.push('/mcp-search')">
    </a-page-header>

    <!-- 进度条 -->
    <div class="progress-bar">
      <a-steps :current="currentStep" direction="horizontal" size="small" style="max-width: 100%; margin: 0 auto">
        <a-step title="扫描" />
        <a-step title="评估" />
        <a-step title="方向+框架" />
        <a-step title="补充" />
        <a-step title="检测" />
        <a-step title="结构推荐" />
        <a-step title="提纲" />
        <a-step title="完整文章" />
      </a-steps>
    </div>

    <!-- 主内容区 -->
    <div class="content-area">
      <a-spin dot :loading="loading" tip="加载中...">
        <!-- Step 0: MCP扫描结果展示 -->
        <div v-if="currentStep === 0" class="step-content">
          <a-card title="MCP 扫描完成">
            <template #extra>
              <a-tag color="green">{{ mcpFiles.length }} 个文件</a-tag>
            </template>
            <div class="mcp-summary">
              <a-typography-text type="secondary">摘要预览：</a-typography-text>
              <div class="summary-text">{{ mcpSummary ? mcpSummary.substring(0, 500) + '...' : '无摘要' }}</div>
            </div>
            <a-space style="margin-top: 16px">
              <a-button type="primary" @click="goToCompletenessEval">
                开始完整度评估
              </a-button>
              <a-button @click="$router.push('/mcp-search')">
                返回重新搜索
              </a-button>
            </a-space>
          </a-card>
        </div>

        <!-- Step 1: 完整度评估 -->
        <div v-if="currentStep === 1" class="step-content">
          <!-- 编辑主题和参考资料信息 -->
          <a-card style="margin-bottom: 16px">
            <template #title>
              <icon-book /> 写作主题与参考资料
            </template>
            <a-descriptions :column="2" size="small">
              <a-descriptions-item label="写作主题">
                {{ appStore.selectedTopic?.name || mcpTopic || '未指定' }}
              </a-descriptions-item>
              <a-descriptions-item label="参考资料数量">
                {{ mcpFiles?.length || 0 }} 篇
              </a-descriptions-item>
              <a-descriptions-item label="资料概览" :span="2">
                <a-typography-text type="secondary">
                  {{ mcpSummary?.substring(0, 200) || '暂无资料' }}{{ mcpSummary && mcpSummary.length > 200 ? '...' : '' }}
                </a-typography-text>
              </a-descriptions-item>
              <a-descriptions-item label="来源文件" :span="2" v-if="mcpFiles?.length">
                <a-space wrap>
                  <a-tag v-for="(f, i) in mcpFiles.slice(0, 5)" :key="i">
                    {{ f.substring(0, 30) }}{{ f.length > 30 ? '...' : '' }}
                  </a-tag>
                  <a-tag v-if="mcpFiles.length > 5">+{{ mcpFiles.length - 5 }} 更多</a-tag>
                </a-space>
              </a-descriptions-item>
            </a-descriptions>
          </a-card>

          <a-card title="信息完整度评估">
            <!-- 加载中 -->
            <div v-if="loading" style="text-align: center; padding: 80px 0">
              <a-spin :size="50" dot tip="正在评估信息完整度..." />
            </div>

            <!-- 未评估：显示空状态 + 触发按钮 -->
            <div v-else-if="!completenessResult" style="text-align: center; padding: 60px 0">
              <a-empty description="尚未评估">
                <template #image>
                  <icon-file style="font-size: 64px; color: #c9cdd4" />
                </template>
              </a-empty>
              <a-button type="primary" size="large" @click="goToCompletenessEval" style="margin-top: 16px">
                <icon-scan /> 开始完整度评估
              </a-button>
            </div>

            <!-- 评估结果已加载 -->
            <div v-else>
              <!-- 完整度统一处理为 0-100 的整数 -->
              <a-progress 
                :percent="displayCompleteness / 100" 
                :color="getCompletenessColor(displayCompleteness)" 
                :stroke-width="12"
                :show-text="false"
              />
              <div style="margin-top: 12px">
                <a-tag :color="getCompletenessColor(displayCompleteness)" size="large">
                  信息完整度：{{ displayCompleteness }}%
                </a-tag>
              </div>

              <a-descriptions :column="2" style="margin-top: 16px" bordered>
                <a-descriptions-item label="核心概念清晰度">
                  {{ completenessResult.dimensions?.concept_clarity || 'N/A' }}%
                </a-descriptions-item>
                <a-descriptions-item label="应用场景具体性">
                  {{ completenessResult.dimensions?.scenario_specificity || 'N/A' }}%
                </a-descriptions-item>
                <a-descriptions-item label="案例/数据丰富度">
                  {{ completenessResult.dimensions?.case_richness || 'N/A' }}%
                </a-descriptions-item>
                <a-descriptions-item label="目标读者明确性">
                  {{ completenessResult.dimensions?.audience_clarity || 'N/A' }}%
                </a-descriptions-item>
              </a-descriptions>

              <a-alert type="warning" style="margin-top: 16px">
                <template #title> 完整度评估说明</template>
                注意：MCP 搜索的「匹配度」评估的是<strong>主题相关性</strong>（文章是否匹配知识库），而这里的「完整度」评估的是<strong>素材充分性</strong>（是否足够支撑一篇高质量文章）。如果完整度偏低，建议先补充素材。
              </a-alert>

              <a-alert type="info" style="margin-top: 12px">
                <template #title>📋 补充策略</template>
                {{ completenessResult.supplement_strategy || '无需额外补充' }}
              </a-alert>

              <div v-if="completenessResult.missing_critical?.length" style="margin-top: 16px">
                <a-typography-text strong style="color: #f53f3f"> 关键缺失项（建议优先补充）：</a-typography-text>
                <a-list :data="completenessResult.missing_critical" size="small" style="margin-top: 8px">
                  <template #item="{ item, index }">
                    <a-list-item :style="{ padding: '12px 16px', borderRadius: '4px', background: isSupplemented(index) ? '#f7f8fa' : '#fff2f0' }">
                      <div v-if="isSupplemented(index)">
                        <icon-check-circle-fill style="color: #00b42a; margin-right: 8px; font-size: 16px" />
                        <div style="flex: 1">
                          <div style="font-size: 14px">{{ item }}</div>
                          <div v-if="getSupplementContent(index)" style="margin-top: 6px; padding: 8px; background: #fff; border-radius: 4px; font-size: 13px; color: #4e5969; line-height: 1.6; max-height: 80px; overflow-y: auto">
                            {{ getSupplementContent(index) }}
                          </div>
                        </div>
                        <a-button type="primary" text size="mini" style="margin-left: 8px" @click="openEditSupplementModal(index)">
                          编辑
                        </a-button>
                      </div>
                      <div v-else>
                        <icon-close-circle-fill style="color: #f53f3f; margin-right: 8px; font-size: 16px" />
                        <div style="flex: 1; font-size: 14px">{{ item }}</div>
                        <a-space size="mini" style="margin-left: 8px">
                          <a-button type="primary" size="mini" @click="openUnifiedSupplementModal(index)">
                            🤖 AI-Pulse + 推断
                          </a-button>
                          <a-button size="mini" @click="openManualSupplement(index)">
                            手动补充
                          </a-button>
                        </a-space>
                      </div>
                    </a-list-item>
                  </template>
                </a-list>
              </div>

              <div v-if="completenessResult.missing_optional?.length" style="margin-top: 12px">
                <a-typography-text type="secondary">
                  可选缺失项（AI可尝试推断）：{{ (completenessResult.missing_optional || []).join('、') }}
                </a-typography-text>
              </div>

              <!-- 检查是否所有关键缺失项都已补充 -->
              <div v-if="allCriticalSupplemented" style="margin-top: 16px">
                <a-alert type="success" style="margin-bottom: 16px">
                  <template #title>✅ 所有关键缺失项已补充完毕</template>
                  信息已充足，可以点击按钮进入下一步
                </a-alert>
                <a-space style="margin-top: 16px">
                  <a-button type="primary" status="success" size="large" @click="goToDirections">
                     下一步：推荐写作方向
                  </a-button>
                  <a-button size="large" @click="skipToOutline">
                    直接生成提纲
                  </a-button>
                </a-space>
              </div>

              <div v-else>
                <a-space style="margin-top: 20px" wrap>
                  <!-- 5A: 信息充足 -->
                  <a-button v-if="displayCompleteness >= 80" type="primary" status="success" size="large" @click="skipToOutline">
                    ✅ 信息充足，直接生成提纲
                  </a-button>

                  <!-- 5B/5C: 需要补充 -->
                  <div v-if="displayCompleteness < 80" style="width: 100%">
                    <a-alert :type="completenessResult.mode === 'framework' ? 'error' : 'warning'" style="width: 100%; margin-bottom: 16px">
                      <template #title>
                        {{ completenessResult.mode_label || '需要补充关键信息' }}
                      </template>
                      <template #default>
                        <div v-if="completenessResult.mode === 'framework'">
                          知识库信息严重不足，将采用框架构建模式。建议补充关键信息后重新评估。
                        </div>
                        <div v-else-if="completenessResult.mode && completenessResult.mode.startsWith('degraded')">
                          部分信息缺失，将采用{{ (completenessResult.mode_label || '').replace('模式', '') }}模式生成内容。
                        </div>
                        <div v-else>
                          {{ displayCompleteness >= 60 ? '建议补充关键信息以提升文章质量' : '信息不足，必须补充后才能生成高质量内容' }}
                        </div>
                        <ul v-if="completenessResult.suggestions?.length" style="margin: 8px 0 0 16px; padding: 0">
                          <li v-for="(s, i) in completenessResult.suggestions" :key="i" style="margin-bottom: 4px; font-size: 13px">
                            {{ s }}
                          </li>
                        </ul>
                      </template>
                    </a-alert>

                    <a-alert type="info" style="width: 100%; margin-bottom: 16px">
                      <template #title> 操作提示</template>
                      逐项补充：点击上方各缺失项的「AI-Pulse + 推断」或「手动补充」按钮<br>
                      一键补充：点击下方按钮，批量检索并补充所有缺失项
                    </a-alert>

                    <a-space size="large" style="width: 100%" wrap>
                      <a-button type="primary" size="large" :loading="batchUnifiedLoading" @click="batchUnifiedSupplement">
                        🤖 一键 AI-Pulse 检索 + 推断全部缺失项
                      </a-button>
                      <a-button size="large" @click="batchManualSupplement">
                         一键手动补充
                      </a-button>
                      <a-button v-if="displayCompleteness >= 60" size="large" @click="skipToOutline">
                        ⏭️ 跳过，直接生成（质量可能较低）
                      </a-button>
                    </a-space>
                  </div>
                </a-space>
              </div>
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

        <!-- Step 2: 推荐写作方向 -->
        <div v-if="currentStep === 2" class="step-content">
          <a-card>
            <template #title>
              <a-space>
                <span>推荐写作方向</span>
                <a-button type="text" size="mini" @click="refreshDirection" :disabled="directionsLoading">
                   换一批
                </a-button>
                <a-tag>共 {{ directions.length }} 个方向</a-tag>
              </a-space>
            </template>

            <!-- 加载中状态 -->
            <div v-if="directionsLoading" style="text-align: center; padding: 40px">
              <a-spin :size="50" dot tip="AI 正在分析推荐写作方向..." />
            </div>

            <!-- 空数据状态 -->
            <div v-else-if="directions.length === 0" style="text-align: center; padding: 40px; color: #86909c">
              <a-empty description="暂无推荐方向，请点击「换一批」重试" />
            </div>

            <!-- 方向列表 -->
            <div v-else>
              <div v-for="(d, i) in directions" :key="i" class="direction-card">
              <a-card :bordered="true" hoverable>
                <template #title>
                  <span style="font-size: 16px">
                    <span v-if="i === 0">🥇 </span>
                    <span v-else-if="i === 1">🥈 </span>
                    <span v-else-if="i === 2">🥉 </span>
                    {{ d.name }}
                  </span>
                  <a-tag :color="getCoverageColor(d.coverage)" style="margin-left: 8px">
                    匹配度 {{ (d.coverage * 100).toFixed(0) }}%
                  </a-tag>
                </template>
                <div class="direction-desc">{{ d.description }}</div>
                <div class="direction-reason">
                  <a-typography-text type="secondary">推荐理由：{{ d.reason }}</a-typography-text>
                </div>
                
                <!-- 关键缺失项 -->
                <div v-if="d.missing_critical?.length" class="missing-items">
                  <a-typography-text strong style="color: #f53f3f">关键缺失项（补充后将提升质量）：</a-typography-text>
                  <a-list :data="d.missing_critical" size="mini">
                    <template #item="{ item }">
                      <a-list-item>
                        <icon-close-circle-fill style="color: #f53f3f; margin-right: 4px; font-size: 12px" />
                        <a-typography-text style="font-size: 13px">{{ item }}</a-typography-text>
                      </a-list-item>
                    </template>
                  </a-list>
                </div>
                
                <!-- 其他缺失项 -->
                <div v-if="d.missing_optional?.length" class="missing-items-optional">
                  <a-typography-text type="secondary" style="font-size: 13px">
                    其他缺失项（AI可尝试推断）：{{ d.missing_optional.join('、') }}
                  </a-typography-text>
                </div>

                <a-button type="primary" status="success" style="margin-top: 12px" @click="selectDirection(d)">
                  选择此方向，加载框架
                </a-button>
              </a-card>
              
              <!-- 选中该方向后，显示推荐框架 -->
              <div v-if="selectedDirection?.name === d.name && (frameworks.length > 0 || frameworksBanner)" style="margin-top: 16px">
                <a-alert type="info" style="margin-bottom: 12px">
                  <template #title>🎯 已选择方向：{{ d.name }}，以下是推荐框架</template>
                </a-alert>
                
                <a-alert v-if="frameworksBanner" 
                  :type="frameworksMode === 'rejected' ? 'error' : 'warning'" 
                  style="margin-bottom: 12px">
                  <template #title>{{ frameworksMode === 'rejected' ? '推荐失败' : '降级推荐提示' }}</template>
                  <div style="font-size: 13px; line-height: 1.6">{{ frameworksBanner }}</div>
                </a-alert>
                
                <div v-if="frameworks.length > 0" style="margin-bottom: 12px; display: flex; justify-content: flex-end">
                  <a-button size="small" :loading="frameworksLoading" @click="regenerateFrameworks">
                    🔄 重新推荐
                  </a-button>
                </div>
                
                <a-spin v-if="frameworksLoading" :size="50" dot tip="正在重新推荐..." />
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
                          🎯 方向对齐 {{ ((f.direction_alignment_score ?? f.match_score) * 100).toFixed(0) }}%
                        </a-tag>
                        <a-tag color="arcoblue" size="small" style="margin-left: 4px">
                          综合 {{ (f.match_score * 100).toFixed(0) }}%
                        </a-tag>
                      </template>
                      <div v-if="f.warning" 
                        :style="{
                          marginBottom: '8px', 
                          padding: '8px 10px', 
                          background: getAlignmentBgColor(f.direction_alignment_score ?? f.match_score),
                          border: `1px solid ${getAlignmentBorderColor(f.direction_alignment_score ?? f.match_score)}`,
                          borderRadius: '4px',
                          fontSize: '12px',
                          color: getAlignmentTextColor(f.direction_alignment_score ?? f.match_score),
                          lineHeight: '1.6'
                        }">
                        {{ f.warning }}
                      </div>
                      <div style="font-size: 13px">{{ f.description }}</div>
                      <div v-if="f.direction_alignment_reason" style="margin-top: 8px">
                        <a-link size="mini" @click="expandedWarnings[j] = !expandedWarnings[j]" style="font-size: 12px">
                          {{ expandedWarnings[j] ? '收起' : '展开' }}方向对齐推理 ({{ expandedWarnings[j] ? '▲' : '▼' }})
                        </a-link>
                        <div v-if="expandedWarnings[j]" style="margin-top: 6px; padding: 6px 8px; background: #f0f7ff; border-radius: 4px; font-size: 12px; color: #165dff; line-height: 1.6">
                          🎯 <strong>方向对齐说明：</strong>{{ f.direction_alignment_reason }}
                        </div>
                      </div>
                      <a-typography-text type="secondary" style="margin-top: 8px; display: block; font-size: 12px">
                        适合原因：{{ f.reason }}
                      </a-typography-text>
                      <div v-if="f.needs_supplement?.length" style="margin-top: 8px">
                        <a-typography-text type="secondary" style="font-size: 12px">
                          使用该框架还需要：{{ f.needs_supplement.join('、') }}
                        </a-typography-text>
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
              </div>
            </div>
            </div>
          </a-card>
        </div>

        <!-- Step 3: 补充 - 完善分析内容 -->
        <div v-if="currentStep === 3" class="step-content">
          <a-card title="补充分析内容">
            <!-- 原文状态展示 -->
            <a-alert type="info" style="margin-bottom: 16px">
              <template #title>📄 原文核心信息</template>
              <div style="max-height: 120px; overflow-y: auto; font-size: 13px; line-height: 1.6; white-space: pre-wrap">
                {{ mcpSummary || '暂无MCP摘要信息' }}
              </div>
            </a-alert>

            <!-- 当前状态 + 检测结果（建设清单风格） -->
            <a-card :bordered="true" style="margin-bottom: 16px; background: #f7f8fa">
              <template #title>
                <a-space>
                  <span>当前信息状态</span>
                  <a-button 
                    type="text" 
                    size="mini" 
                    :loading="preCheckLoading" 
                    @click="runPreCheck"
                  >
                    🔄 重新检测
                  </a-button>
                </a-space>
              </template>
              <div style="font-size: 13px; line-height: 1.8">
                <!-- ✅ 已具备 -->
                <div style="margin-bottom: 12px">
                  <div style="font-weight: 600; color: #00b42a; margin-bottom: 6px">✅ 已具备</div>
                  <div style="padding-left: 16px">
                    <div>• <strong>方向：</strong>{{ selectedDirection?.name || '未选择' }}</div>
                    <div>• <strong>框架：</strong>{{ selectedFramework?.name || '未选择' }}</div>
                  </div>
                </div>
                
                <!-- 预检测结果 -->
                <div v-if="preCheckResult">
                  <!-- 有问题需要细化 -->
                  <div v-if="preCheckResult.issues && preCheckResult.issues.length > 0">
                    <div style="font-weight: 600; color: #1d2129; margin-bottom: 8px"> 还需细化</div>
                    <div style="padding-left: 16px">
                      <div v-for="(issue, ii) in preCheckResult.issues" :key="ii" style="margin-bottom: 8px; padding: 8px; background: #fff; border-radius: 4px; border-left: 3px solid #e5e6eb">
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px">
                          <div style="display: flex; align-items: center; gap: 6px">
                            <span :style="{ fontSize: '14px' }">{{ issue.type === 'error' ? '🔴' : issue.type === 'warning' ? '🟡' : '🟢' }}</span>
                            <strong style="font-size: 13px">{{ issue.title }}</strong>
                          </div>
                          <a-tag v-if="issue.type === 'error'" size="mini" color="red">高优</a-tag>
                          <a-tag v-else-if="issue.type === 'warning'" size="mini" color="orange">中优</a-tag>
                          <a-tag v-else size="mini" color="green">优化</a-tag>
                        </div>
                        <div style="font-size: 12px; color: #86909c; margin-bottom: 4px">{{ issue.description }}</div>
                        <div style="display: flex; gap: 4px; flex-wrap: wrap">
                          <a-button v-if="issue.can_auto_fix" size="mini" type="outline" @click="fixIssue(ii)">
                             AI修复
                          </a-button>
                          <a-button v-else size="mini" type="outline" @click="showIssueDetail(issue)">
                            查看详情
                          </a-button>
                        </div>
                      </div>
                    </div>
                    
                    <!-- 完整度提示（不再用红色分数） -->
                    <div style="margin-top: 12px; padding-top: 8px; border-top: 1px dashed #e5e6eb; font-size: 12px; color: #86909c">
                      内容完整度：{{ (preCheckResult.score / 100 * 100).toFixed(0) }}%（{{ preCheckResult.issues.filter(i => i.type === 'error').length }}项需优先处理）
                    </div>
                  </div>
                  
                  <!-- 没问题 -->
                  <div v-else>
                    <a-typography-text type="success">✅ 信息充足，可直接生成提纲</a-typography-text>
                  </div>
                </div>
                
                <div v-else-if="!preCheckLoading" style="margin-top: 8px">
                  <a-button type="text" size="mini" @click="runPreCheck">
                    📋 点击检测缺失项
                  </a-button>
                </div>
              </div>
            </a-card>

            <!-- AI 一键补充缺失项 -->
            <div v-if="preCheckResult?.issues && preCheckResult.issues.some(i => i.type !== 'pass')" style="margin-bottom: 16px">
              <a-button 
                type="primary" 
                status="success" 
                long 
                :loading="aiAutoSupplementLoading"
                @click="aiAutoSupplementAllMissing"
              >
                🤖 AI 智能补充全部
              </a-button>
            </div>

            <!-- 补充表单 -->
            <a-form :model="supplement2Form" layout="vertical">
              <a-form-item label="补充方式">
                <a-radio-group v-model="supplement2Method">
                  <a-radio value="file">从知识库选择文件</a-radio>
                  <a-radio value="text">粘贴补充文本</a-radio>
                </a-radio-group>
              </a-form-item>

              <a-form-item v-if="supplement2Method === 'file'" label="选择文件">
                <a-tree-select
                  v-model="supplement2File"
                  :data="kbTreeData"
                  placeholder="选择要补充的文件..."
                  tree-checkable
                  allow-search
                />
              </a-form-item>

              <a-form-item v-if="supplement2Method === 'text'" label="补充文本">
                <a-textarea
                  v-model="supplement2Text"
                  placeholder="补充核心痛点、解决方案、避坑指南等分析内容..."
                  :auto-size="{ minRows: 4, maxRows: 10 }"
                />
              </a-form-item>

              <a-form-item label="核心痛点">
                <a-textarea v-model="supplement2Form.painPoint" placeholder="用户/读者面临的核心问题是什么？" :auto-size="{ minRows: 2, maxRows: 4 }" />
              </a-form-item>
              <a-form-item label="解决方案">
                <a-textarea v-model="supplement2Form.solution" placeholder="你推荐的解决方案是什么？" :auto-size="{ minRows: 2, maxRows: 4 }" />
              </a-form-item>
              <a-form-item label="避坑指南">
                <a-textarea v-model="supplement2Form.pitfalls" placeholder="常见错误或需要注意的事项..." :auto-size="{ minRows: 2, maxRows: 4 }" />
              </a-form-item>
            </a-form>

            <a-space style="margin-top: 16px; width: 100%; justify-content: space-between">
              <a-space>
                <a-button type="primary" status="success" :loading="supplementLoading" @click="submitSupplement2">
                  确认补充
                </a-button>
                <a-button @click="skipSupplement2">跳过补充，直接进入检测</a-button>
              </a-space>
            </a-space>
          </a-card>
        </div>

        <!-- Step 4: 方向检测 -->
        <div v-if="currentStep === 4" class="step-content">
          <a-card title="方向检测">
            <a-alert type="info" style="margin-bottom: 16px">
              <template #title>检测内容是否偏离选定方向</template>
              方向：{{ selectedDirection?.name }}
            </a-alert>

            <div v-if="checkingDirection" style="text-align: center; padding: 40px">
              <a-spin :size="50" dot tip="正在检测..." />
            </div>

            <div v-else-if="directionCheckResult">
              <div style="margin-bottom: 16px; text-align: center">
                <a-button 
                  type="primary" 
                  status="warning" 
                  :loading="aiSupplementAllLoading"
                  @click="aiSupplementAllIssues"
                >
                  🤖 一键AI补充所有问题
                </a-button>
              </div>
              
              <div v-for="(issue, i) in directionCheckResult" :key="i" class="issue-card" style="margin-bottom: 12px">
                <a-card :bordered="true" :type="issue.type === 'error' ? 'danger' : issue.type === 'warning' ? 'warning' : 'normal'">
                  <template #title>
                    <a-space>
                      <span v-if="issue.type === 'error'">🔴</span>
                      <span v-else-if="issue.type === 'warning'">🟡</span>
                      <span v-else>🟢</span>
                      <span>{{ issue.title }}</span>
                      <a-tag :color="issue.type === 'error' ? 'red' : issue.type === 'warning' ? 'orange' : 'green'" size="small">
                        {{ issue.type === 'error' ? '错误' : issue.type === 'warning' ? '警告' : '通过' }}
                      </a-tag>
                    </a-space>
                  </template>
                  <div style="font-size: 13px; line-height: 1.6">{{ issue.description }}</div>
                  
                  <div style="margin-top: 12px">
                    <a-space>
                      <a-button size="small" status="primary" @click="editSingleIssue(i)">
                        编辑
                      </a-button>
                      <a-button v-if="issue.type !== 'pass'" size="small" @click="ignoreIssue(i)">忽略</a-button>
                    </a-space>
                    <div v-if="editingIssueIndex === i" style="margin-top: 12px; padding: 12px; background: #f7f8fa; border-radius: 4px">
                      <a-textarea 
                        v-model="editingIssueContent" 
                        :placeholder="`针对「${issue.title}」补充内容...`"
                        :auto-size="{ minRows: 3, maxRows: 8 }"
                        style="margin-bottom: 8px"
                      />
                      <a-space>
                        <a-button type="primary" size="small" :loading="editingIssueLoading" @click="confirmSingleIssue(i)">
                          确认补充
                        </a-button>
                        <a-button size="small" status="success" :loading="aiSingleIssueLoading" @click="aiGenerateSingleIssue(i)">
                          🤖 AI 智能补充
                        </a-button>
                        <a-button size="small" @click="cancelEditIssue">取消</a-button>
                      </a-space>
                    </div>
                  </div>
                </a-card>
              </div>

              <div style="margin-top: 16px; text-align: center">
                <a-button 
                  type="primary" 
                  status="success" 
                  :disabled="hasErrors"
                  @click="currentStep = 5"
                >
                  全部通过，进入下一步 →
                </a-button>
                <div v-if="hasErrors" style="margin-top: 8px; color: #f53f3f; font-size: 13px">
                  请先修复所有错误项
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

        <!-- Step 5: 推荐内容结构 -->
        <div v-if="currentStep === 5" class="step-content">
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
              <div v-for="(s, i) in structures" :key="i" class="structure-card" style="margin-bottom: 12px">
                <a-card :bordered="true" hoverable>
                  <template #title>
                    <span v-if="i === 0">🥇 </span>
                    <span v-else-if="i === 1"> </span>
                    <span v-else-if="i === 2">🥉 </span>
                    {{ s.name }}
                  </template>
                  <div style="font-size: 13px; line-height: 1.6">{{ s.description }}</div>
                  <div v-if="s.needs_supplement?.length" style="margin-top: 8px">
                    <a-typography-text type="secondary" style="font-size: 13px">
                      需要补充：{{ s.needs_supplement.join('、') }}
                    </a-typography-text>
                  </div>
                  <a-button type="primary" status="success" style="margin-top: 12px" @click="selectStructure(s)">
                    选择此结构
                  </a-button>
                </a-card>
              </div>
            </div>
          </a-card>
        </div>

        <!-- Step 6: 写作提纲展示 -->
        <div v-if="currentStep === 6" class="step-content">
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
                      </div>
                      <div style="color: #4e5969; line-height: 1.6; padding-left: 20px">
                        💡 {{ item.fill_guidance }}
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

        <!-- Step 7: 完整文章生成 -->
        <div v-if="currentStep === 7" class="step-content">
          <a-card title="完整文章">
            <div v-if="articleResult">
              <div style="margin-bottom: 24px">
                <h3 style="color: #1d2129; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 2px solid #e5e6eb">
                  📄 {{ articleResult.title || '完整文章' }}
                </h3>
                <div style="text-align: center; margin-bottom: 16px">
                  <a-space>
                    <a-button type="primary" status="success" :loading="articleOneClickLoading" @click="articleOneClickRegenerate">
                      🤖 一键重新生成全文
                    </a-button>
                    <a-button type="primary" @click="exportArticle">
                      📥 导出文章
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
import { ref, reactive, onMounted, onUnmounted, computed, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { useAppStore } from '../stores/app'
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
} from '@arco-design/web-vue/es/icon'
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
  readFolderFile,
  addSupplement as apiAddSupplement,
  confirmSupplement as apiConfirmSupplement,
  listSupplements as apiListSupplements,
} from '../utils/api'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()

const loading = ref(false)
const currentStep = ref(0)
const sessionId = ref('')
const mcpSummary = ref('')
const mcpFiles = ref([])
const kbTreeData = ref([])
const mcpTopic = ref('')

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

// 旧版状态（保留兼容）
const supplementModalMethod = ref('text')
const supplementModalFile = ref([])
const supplementModalText = ref('')
const aiSupplementing = ref(false)
const extractingFileContent = ref(false)
const extractedFileContent = ref(false)
const extractedFileCount = ref(0)

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
const supplement2Form = reactive({
  painPoint: '',
  solution: '',
  pitfalls: '',
})

// 预检测相关状态
const preCheckResult = ref(null)
const preCheckLoading = ref(false)
const aiAutoSupplementLoading = ref(false)
const supplementLoading = ref(false)

// 方向检测
const checkingDirection = ref(false)
const directionCheckResult = ref(null)
const fixingIssueIndex = ref(-1)
const editingIssueIndex = ref(-1)
const editingIssueContent = ref('')
const editingIssueLoading = ref(false)
const aiSingleIssueLoading = ref(false)
const hasErrors = computed(() => {
  if (!directionCheckResult.value) return false
  return directionCheckResult.value.some(issue => issue.type === 'error')
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
const articleAiDialogIndex = ref(-1)
const articleAiInput = ref('')
const articleAiKbFiles = ref([])
const articleAiUploadFiles = ref([])
const articleAiLoading = ref(false)
const articleAiResult = ref('')
const articleOneClickLoading = ref(false)

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

  // 创建会话
  try {
    const res = await createWorkflowSession()
    if (!isMounted) return
    sessionId.value = res.data.data.session_id
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
})

onUnmounted(() => {
  // 清理：防止异步操作在组件卸载后执行
})

// 监听步骤变化，进入步骤4时自动触发方向检测，进入步骤5时自动加载结构推荐
watch(currentStep, async (newStep) => {
  if (newStep === 4 && !directionCheckResult.value && !checkingDirection.value) {
    await runDirectionCheck()
  }
  if (newStep === 5 && structures.value.length === 0) {
    await goToStructures()
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
      
      loading.value = false
      
      setTimeout(() => {
        currentStep.value = 1
        Message.success('完整度评估完成')
      }, 100)
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
  
  // 立即切换到方向页面（显示加载状态）
  currentStep.value = 2
  loading.value = true
  directions.value = []
  directionsLoading.value = true
  
  try {
    const res = await analyzeDirectionsV2(sessionId.value, mcpSummary.value)
    console.log(' 方向推荐响应:', res.data)
    
    if (res.data.code === 0 && res.data.data?.length > 0) {
      directions.value = res.data.data
      Message.success(`方向推荐完成，共 ${directions.value.length} 个方向`)
    } else if (res.data.code === 0 && (!res.data.data || res.data.data.length === 0)) {
      Message.warning('暂无推荐方向，请补充更多信息后重试')
      // 保持在方向页面，但显示空状态
    } else {
      Message.error('方向推荐失败: ' + (res.data.msg || '未知错误'))
    }
  } catch (e) {
    console.error('🔴 方向推荐异常:', e)
    Message.error('方向推荐失败: ' + e.message)
  } finally {
    loading.value = false
    directionsLoading.value = false
  }
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

function selectDirection(d) {
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
  
  // 异步加载框架
  loadFrameworks()
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

function selectFramework(f) {
  console.log('========================================')
  console.log('🔴 [DEBUG] selectFramework 被调用')
  console.log(' 选择框架:', f.name)
  console.log(' 当前步骤:', currentStep.value)
  console.log('========================================')
  
  // 先设置框架，确保数据立即可用
  selectedFramework.value = f
  
  // 按需检索 API 案例（不再预加载）
  // preloadApiCases()  // 已移除：改为按需检索
  
  // 立即切换到补充页面 (Step 3 - 合并后的补充步骤)
  currentStep.value = 3
  
  // 自动触发预检测，显示缺失项清单
  setTimeout(() => runPreCheck(), 100)
  
  Message.success(`已选择「${f.name}」框架，正在检测缺失项...`)
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
    for (const issue of preCheckResult.value.issues) {
      if (issue.type === 'pass') continue
      const res = await apiInferSupplement(sessionId.value, `自动补充：${issue.title}`, {
        mcp_summary: mcpSummary.value || '',
      })
      if (res.data.code === 0 && res.data.data?.content) {
        supplement2Text.value += (supplement2Text.value ? '\n\n' : '') + `【${issue.title}】\n${res.data.data.content}`
      }
    }
    Message.success('AI 智能补充完成')
    await runPreCheck()
  } catch (e) {
    Message.error('AI 智能补充失败: ' + e.message)
  } finally {
    aiAutoSupplementLoading.value = false
  }
}

// 建设清单：AI 修复单个问题
async function fixIssue(idx) {
  const issue = preCheckResult.value?.issues?.[idx]
  if (!issue) return
  
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
  
  const res = await apiInferSupplement(sessionId.value, `自动补充：${supplementItem}`, {
    mcp_summary: mcpSummary.value || '',
  })
  if (res.data.code === 0 && res.data.data?.content) {
    supplement2Text.value += (supplement2Text.value ? '\n\n' : '') + `【${supplementItem}】\n${res.data.data.content}`
    Message.success(`已补充：${supplementItem}`)
    await runPreCheck()
  } else {
    Message.error('补充失败')
  }
}

// 建设清单：显示问题详情
function showIssueDetail(issue) {
  Message.info({
    content: `${issue.title}\n\n${issue.description}\n\n建议：${issue.suggestion}`,
    duration: 5000,
  })
}

async function submitSupplement2() {
  console.log('========================================')
  console.log('🔴 [DEBUG] submitSupplement2 被调用')
  console.log('🔴 当前状态:', { currentStep: currentStep.value, supplementLoading: supplementLoading.value })
  console.log('🔴 selectedFramework:', selectedFramework.value)
  console.log('========================================')
  
  if (!selectedFramework.value) {
    Message.error('未选择框架，请先返回选择框架')
    return
  }
  
  let supplementInfo = { ...supplement2Form }
  if (supplement2Method.value === 'text') {
    supplementInfo.text = supplement2Text.value
  } else {
    supplementInfo.files = supplement2File.value
  }

  supplementLoading.value = true
  try {
    await supplementStep2(sessionId.value, selectedFramework.value.name, supplementInfo)
    supplementLoading.value = false
    currentStep.value = 4
    Message.success('补充已保存，正在进行方向检测...')
  } catch (e) {
    supplementLoading.value = false
    Message.error('操作失败: ' + e.message)
  }
}

async function skipSupplement2() {
  if (!selectedFramework.value) {
    Message.error('未选择框架，请先返回选择框架')
    return
  }
  
  supplementLoading.value = true
  try {
    await supplementStep2(sessionId.value, selectedFramework.value.name, {})
    supplementLoading.value = false
    currentStep.value = 4
    Message.info('已跳过补充，正在进行方向检测...')
  } catch (e) {
    supplementLoading.value = false
    Message.error('操作失败: ' + e.message)
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
    directionCheckResult.value = res.data.data.issues || res.data.data
    Message.success('方向检测完成')
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
  currentStep.value = 4
  directionCheckResult.value = null
  Message.info('已返回补充页面')
}

async function goToStructures() {
  console.log('========================================')
  console.log('🔴 [DEBUG] goToStructures 被调用')
  console.log('🔴 当前状态:', { currentStep: currentStep.value, loading: loading.value })
  console.log('========================================')
  structuresLoading.value = true
  try {
    const res = await recommendStructures(
      sessionId.value,
      selectedDirection.value?.name || '',
      selectedFramework.value?.name || '',
      supplement2Form,
      mcpSummary.value,
    )
    structures.value = res.data.data
    Message.success('结构推荐完成')
  } catch (e) {
    Message.error('结构推荐失败: ' + e.message)
  } finally {
    structuresLoading.value = false
    setTimeout(() => {
      currentStep.value = 5
      Message.success('已切换到结构推荐页面')
    }, 100)
  }
}

function selectStructure(s) {
  console.log('========================================')
  console.log('🔴 [DEBUG] selectStructure 被调用')
  console.log('🔴 选择结构:', s.name)
  console.log(' 当前状态:', { currentStep: currentStep.value, loading: loading.value })
  console.log('========================================')
  selectedStructure.value = s
  currentStep.value = 6
  loadOutline()
  Message.info(`已选择「${s.name}」结构，正在生成提纲...`)
}

function goBackToStructures() {
  currentStep.value = 5
  outlineResult.value = null
  Message.info('已返回结构推荐')
}

async function loadOutline() {
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
          console.error('🔴 提纲JSON解析失败:', e)
        }
      }
      outlineResult.value = outlineData
      loading.value = false
      setTimeout(() => {
        currentStep.value = 6
        Message.success('提纲生成完成')
      }, 100)
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
  const sectionsObj = outlineResult.value.sections
  const sectionsArray = Object.values(sectionsObj).filter(s => s.materials?.needs?.length > 0)
  if (sectionsArray.length === 0) {
    Message.info('暂无需要补充的素材')
    return
  }
  outlineOneClickLoading.value = true
  try {
    for (const section of sectionsArray) {
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
    Message.success(`已为 ${sectionsArray.length} 个段落完成 AI 补充`)
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
  currentStep.value = 7
  generateArticle()
  Message.info('正在生成完整文章...')
}

async function generateArticle() {
  if (!outlineResult.value) {
    await loadOutline()
  }
  loading.value = true
  try {
    const outlineSections = outlineResult.value?.sections || []
    const res = await generateFullArticle(sessionId.value, outlineSections)
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
        currentStep.value = 7
        Message.success('完整文章生成完成')
      }, 100)
    } else {
      Message.error('生成失败: ' + (res.data.msg || '未知错误'))
      loading.value = false
    }
  } catch (e) {
    loading.value = false
    Message.error('生成失败: ' + e.message)
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
  currentStep.value = 6
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
    
    // Step 4: 设置选中的框架并保持在补充页面
    selectedFramework.value = framework
    // 自动预检测缺失项
    setTimeout(() => {
      currentStep.value = 3
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

.ai-pulse-cases {
  .case-title {
    font-weight: 500;
    font-size: 14px;
    margin-bottom: 4px;
  }
  
  .case-summary {
    font-size: 12px;
    color: #86909c;
    margin-bottom: 6px;
    line-height: 1.5;
  }
  
  .case-meta {
    display: flex;
    gap: 6px;
    align-items: center;
  }
}
</style>
