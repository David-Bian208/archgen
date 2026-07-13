<template>
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
</template>

<script setup>
import { useWorkflowState } from '../../composables/useWorkflowState'

const {
  // 弹窗可见性
  supplementModalVisible, batchAiPulseModalVisible, batchManualModalVisible,
  editModalVisible, unifiedModalVisible, batchResultModalVisible, draftModalVisible,

  // 弹窗数据项
  currentSupplementItem, currentSupplementIndex, unifiedModalItem, unifiedModalItemIndex,
  draftModalItem, draftModalItemIndex,

  // 补充弹窗（分步骤工作流）
  supplementStep, supplementApiLoading, supplementApiCases, supplementApiSelectedCases,
  supplementInferLoading, supplementInferResult, supplementSaving,
  allSupplementApiCasesSelected, anySupplementApiCaseSelected, selectedSupplementCasesSummary,

  // 批量操作
  batchAiPulseResults, batchManualTexts, batchResults,

  // 编辑弹窗
  editOriginalContent, editNewContent, editAiSuggestion, editAiLoading, editSaving,

  // 统一补充弹窗
  unifiedModalStep, unifiedApiCases, unifiedApiSelected, unifiedApiLoading,
  unifiedInferLoading, unifiedInferResult, unifiedSaving,

  // 草稿弹窗
  draftContent, draftLoading, draftSaving,

  // 其他
  completenessResult,

  // ==== modal handler functions ====
  toggleSupplementApiSelectAll, goToStep2, goToStep2NoCases, goToStep3,
  confirmSupplementStep3, closeSupplementModal, openEditSupplementModal,
  aiAssistEdit, applyAiSuggestion, saveEditedSupplement, closeEditModal,
  reEvaluateCompleteness, confirmBatchAiPulse, confirmBatchManual,
  toggleUnifiedSelectAll, goToUnifiedInfer, goToUnifiedInferNoCases,
  confirmUnifiedSupplement, closeUnifiedModal, openDraftModal,
  confirmDraftSupplement, closeDraftModal, closeBatchResultModal,
} = useWorkflowState()
</script>
