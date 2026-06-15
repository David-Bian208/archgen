<template>
  <div class="data-input-view">
    <a-page-header title="完善分析内容" @back="$router.push('/directions')">
      <template #extra>
        <a-steps :current="2" :max="5" style="width: 300px">
          <a-step>检索</a-step>
          <a-step>方向</a-step>
          <a-step>内容</a-step>
          <a-step>框架</a-step>
          <a-step>表单</a-step>
        </a-steps>
      </template>
    </a-page-header>

    <!-- 资料信息 -->
    <a-card class="info-card">
      <template #title>
        <div class="card-title">
          <icon-folder />
          <span>当前资料</span>
        </div>
      </template>
      <a-space direction="vertical" style="width: 100%" :size="8">
        <div class="info-row">
          <span class="info-label">方向</span>
          <span class="info-value"><a-tag color="blue">{{ appStore.selectedDirection?.name || '未选择' }}</a-tag></span>
        </div>
        <div class="info-row">
          <span class="info-label">资料数量</span>
          <span class="info-value">{{ appStore.mcpResult?.file_count || 0 }} 篇</span>
        </div>
      </a-space>
    </a-card>

    <!-- 三栏布局：原文 | 编辑 | 预览 -->
    <div class="main-layout">
      <!-- 左栏：编辑区 -->
      <div class="edit-pane">
        <a-card class="edit-card">
          <template #title>
            <div class="card-title">
              <icon-edit />
              <span>撰写内容</span>
            </div>
          </template>
          <template #extra>
            <a-space>
              <a-tooltip content="原文充足的段落直接用原文，不足的AI生成，每段生成后可确认修改">
                <a-button type="primary" size="small" @click="handleSmartFill" :loading="smartFilling">
                  <icon-robot /> 原文+AI混合生成（推荐）
                </a-button>
              </a-tooltip>
              <a-tooltip content="基于写作提纲逐段生成全文，适合快速查看整体效果">
                <a-button type="text" size="small" @click="handleAiFillAll" :loading="aiFilling">
                  <icon-robot /> AI基于提纲生成全文
                </a-button>
              </a-tooltip>
            </a-space>
          </template>

          <a-spin :loading="loading">
            <!-- 引言 -->
            <div v-if="structure.intro" class="section-block" :class="sectionBorderClass('intro')">
              <div class="section-header">
                <div class="section-title-row">
                <a-tag color="arcoblue">引言</a-tag>
                <span class="section-title">{{ structure.intro.title }}</span>
                <span class="word-count">建议 {{ structure.intro.word_count }} 字</span>
                <a-tag v-if="structure.intro.analysis_type" :color="structure.intro.analysis_color" size="small">
                  {{ structure.intro.analysis_label }}
                </a-tag>
                <a-tooltip :content="getConfidenceTooltip(structure.intro.confidence)">
                  <a-tag v-if="structure.intro.confidence" :color="getConfidenceColor(structure.intro.confidence)" size="small" style="margin-left: 4px">
                    {{ getConfidenceEmoji(structure.intro.confidence) }} {{ getConfidenceLabel(structure.intro.confidence) }}
                  </a-tag>
                </a-tooltip>
                <a-button v-if="sectionContents.intro && !directionResults['intro']" type="text" size="mini" @click="handleCheckDirection('intro', structure.intro.title, structure.intro.outline)" :loading="checkingDirections['intro']" style="margin-left: 8px">
                  <icon-check-circle /> 检测方向
                </a-button>
              </div>
                <a-button type="text" size="mini" @click="handleAiFillIntro" :loading="aiFillingSections['intro']">
                  <icon-robot /> AI 帮我写
                </a-button>
              </div>
              <a-alert type="info" :show-icon="false" class="ai-hint">
                <template #icon>
                  <icon-bulb style="color: #165DFF" />
                </template>
                {{ structure.intro.hint }}
              </a-alert>
              <div v-if="structure.intro.analysis_suggestion" class="analysis-suggestion">
                <icon-bulb style="color: #F7BA2A" />
                <span>{{ structure.intro.analysis_suggestion }}</span>
              </div>
              <div class="outline-box" v-if="structure.intro.outline">
                <div class="outline-label">写作提纲</div>
                <!-- 结构化提纲 -->
                <div v-if="typeof structure.intro.outline === 'object'" class="outline-structured">
                  <div class="outline-item" v-if="structure.intro.outline.core_point">
                    <span class="outline-item-label">核心观点：</span>
                    <span>{{ structure.intro.outline.core_point }}</span>
                  </div>
                  <div class="outline-item" v-if="structure.intro.outline.evidence">
                    <span class="outline-item-label">论据支撑：</span>
                    <span>{{ structure.intro.outline.evidence }}</span>
                  </div>
                  <div class="outline-item" v-if="structure.intro.outline.angle">
                    <span class="outline-item-label">写作角度：</span>
                    <span>{{ structure.intro.outline.angle }}</span>
                  </div>
                  <div class="outline-item" v-if="structure.intro.outline.materials">
                    <span class="outline-item-label">可用素材：</span>
                    <span>{{ structure.intro.outline.materials }}</span>
                  </div>
                  <div class="outline-item" v-if="structure.intro.outline.notes">
                    <span class="outline-item-label">注意事项：</span>
                    <span>{{ structure.intro.outline.notes }}</span>
                  </div>
                </div>
                <!-- 兼容旧格式（字符串） -->
                <div class="outline-content" v-else>{{ structure.intro.outline }}</div>
              </div>
              <a-textarea
                v-model="sectionContents.intro"
                placeholder="在此撰写引言内容..."
                :auto-size="{ minRows: 3, maxRows: 8 }"
                class="section-textarea"
              />
              <!-- P3: 方向性检测结果与操作 -->
              <div class="direction-check" v-if="directionResults['intro']">
                <div class="direction-header">
                  <a-tag :color="directionResults['intro'].severity_color" size="medium">
                    {{ directionResults['intro'].severity_label }}
                  </a-tag>
                  <span class="coverage-rate">覆盖率 {{ Math.round(directionResults['intro'].coverage_rate * 100) }}%</span>
                </div>
                <div v-if="directionResults['intro'].issues.length > 0" class="direction-issues">
                  <div v-for="(issue, i) in directionResults['intro'].issues" :key="i" class="issue-item">
                    <icon-close-circle style="color: #F53F3F" />
                    <span>{{ issue }}</span>
                  </div>
                </div>
                <div class="direction-actions">
                  <a-button type="primary" size="small" @click="openRewriteDialog('intro', structure.intro.title)">
                    <icon-edit /> 重写该段落
                  </a-button>
                  <a-popconfirm content="确认方向正确，保留当前内容？" @ok="Message.success('已确认')">
                    <a-button size="small">确认保留</a-button>
                  </a-popconfirm>
                </div>
              </div>
            </div>

            <!-- 补充知识库展示（P0-2：用户可见的补充内容） -->
            <div class="supplement-kb-section" v-if="supplementList.length > 0">
              <a-alert type="success" :show-icon="false" style="margin-bottom: 16px">
                <template #icon><icon-check-circle style="color: #00B42A" /></template>
                <template #title>
                  知识库已补充 {{ supplementList.length }} 条内容，AI 生成时将使用这些内容
                </template>
              </a-alert>
              <a-list :data="supplementList" :bordered="true" size="small" class="supplement-list">
                <template #item="{ item }">
                  <a-list-item>
                    <div class="supplement-item">
                      <a-tag size="small" :color="getSourceColor(item.source)">
                        {{ getSourceIcon(item.source) }} {{ getSourceLabel(item.source) }}
                      </a-tag>
                      <span class="supplement-dimension">{{ item.dimension }}</span>
                      <div class="supplement-content">{{ item.content }}</div>
                    </div>
                  </a-list-item>
                </template>
              </a-list>
            </div>

            <!-- 主体段落 -->
            <div v-for="(section, index) in structure.sections" :key="index" class="section-block" :class="sectionBorderClass(`section_${index}`)">
              <div class="section-header">
                <div class="section-title-row">
                <a-tag color="orangered">第{{ index + 1 }}部分</a-tag>
                <span class="section-title">{{ section.title }}</span>
                <span class="word-count">建议 {{ section.word_count }} 字</span>
                <a-tag v-if="section.analysis_type" :color="section.analysis_color" size="small">
                  {{ section.analysis_label }}
                </a-tag>
                <a-tooltip :content="getConfidenceTooltip(section.confidence)">
                  <a-tag v-if="section.confidence" :color="getConfidenceColor(section.confidence)" size="small" style="margin-left: 4px">
                    {{ getConfidenceEmoji(section.confidence) }} {{ getConfidenceLabel(section.confidence) }}
                  </a-tag>
                </a-tooltip>
                <a-button v-if="sectionContents[`section_${index}`] && !directionResults[`section_${index}`]" type="text" size="mini" @click="handleCheckDirection(`section_${index}`, section.title, section.outline)" :loading="checkingDirections[`section_${index}`]" style="margin-left: 8px">
                  <icon-check-circle /> 检测方向
                </a-button>
              </div>
                <a-button type="text" size="mini" @click="handleAiFillSection(index)" :loading="aiFillingSections[`section_${index}`]">
                  <icon-robot /> AI 帮我写
                </a-button>
              </div>
              <a-alert type="info" :show-icon="false" class="ai-hint">
                <template #icon>
                  <icon-bulb style="color: #165DFF" />
                </template>
                {{ section.hint }}
              </a-alert>
              <div v-if="section.analysis_suggestion" class="analysis-suggestion">
                <icon-bulb style="color: #F7BA2A" />
                <span>{{ section.analysis_suggestion }}</span>
              </div>
              <div class="outline-box" v-if="section.outline">
                <div class="outline-label">写作提纲</div>
                <div v-if="typeof section.outline === 'object'" class="outline-structured">
                  <div class="outline-item" v-if="section.outline.core_point">
                    <span class="outline-item-label">核心观点：</span>
                    <span>{{ section.outline.core_point }}</span>
                  </div>
                  <div class="outline-item" v-if="section.outline.evidence">
                    <span class="outline-item-label">论据支撑：</span>
                    <span>{{ section.outline.evidence }}</span>
                  </div>
                  <div class="outline-item" v-if="section.outline.angle">
                    <span class="outline-item-label">写作角度：</span>
                    <span>{{ section.outline.angle }}</span>
                  </div>
                  <div class="outline-item" v-if="section.outline.materials">
                    <span class="outline-item-label">可用素材：</span>
                    <span>{{ section.outline.materials }}</span>
                  </div>
                  <div class="outline-item" v-if="section.outline.notes">
                    <span class="outline-item-label">注意事项：</span>
                    <span>{{ section.outline.notes }}</span>
                  </div>
                </div>
                <div class="outline-content" v-else>{{ section.outline }}</div>
              </div>
              <a-textarea
                v-model="sectionContents[`section_${index}`]"
                placeholder="在此撰写该部分内容..."
                :auto-size="{ minRows: 4, maxRows: 12 }"
                class="section-textarea"
              />
              <!-- P3: 方向性检测结果与操作 -->
              <div class="direction-check" v-if="directionResults[`section_${index}`]">
                <div class="direction-header">
                  <a-tag :color="directionResults[`section_${index}`].severity_color" size="medium">
                    {{ directionResults[`section_${index}`].severity_label }}
                  </a-tag>
                  <span class="coverage-rate">覆盖率 {{ Math.round(directionResults[`section_${index}`].coverage_rate * 100) }}%</span>
                </div>
                <div v-if="directionResults[`section_${index}`].issues.length > 0" class="direction-issues">
                  <div v-for="(issue, i) in directionResults[`section_${index}`].issues" :key="i" class="issue-item">
                    <icon-close-circle style="color: #F53F3F" />
                    <span>{{ issue }}</span>
                  </div>
                </div>
                <div class="direction-actions">
                  <a-button type="primary" size="small" @click="openRewriteDialog(`section_${index}`, section.title)">
                    <icon-edit /> 重写该段落
                  </a-button>
                  <a-popconfirm content="确认方向正确，保留当前内容？" @ok="Message.success('已确认')">
                    <a-button size="small">确认保留</a-button>
                  </a-popconfirm>
                </div>
              </div>
            </div>

            <!-- 结论 -->
            <div v-if="structure.conclusion" class="section-block conclusion-block" :class="sectionBorderClass('conclusion')">
              <div class="section-header">
                <div class="section-title-row">
                  <a-tag color="green">结论</a-tag>
                  <span class="section-title">{{ structure.conclusion.title }}</span>
                  <span class="word-count">建议 {{ structure.conclusion.word_count }} 字</span>
                  <a-tag v-if="structure.conclusion.analysis_type" :color="structure.conclusion.analysis_color" size="small">
                    {{ structure.conclusion.analysis_label }}
                  </a-tag>
                  <a-tooltip :content="getConfidenceTooltip(structure.conclusion.confidence)">
                    <a-tag v-if="structure.conclusion.confidence" :color="getConfidenceColor(structure.conclusion.confidence)" size="small" style="margin-left: 4px">
                      {{ getConfidenceEmoji(structure.conclusion.confidence) }} {{ getConfidenceLabel(structure.conclusion.confidence) }}
                    </a-tag>
                  </a-tooltip>
                </div>
                <a-button type="text" size="mini" @click="handleAiFillConclusion" :loading="aiFillingSections['conclusion']">
                  <icon-robot /> AI 帮我写
                </a-button>
              </div>
              <a-alert type="info" :show-icon="false" class="ai-hint">
                <template #icon>
                  <icon-bulb style="color: #165DFF" />
                </template>
                {{ structure.conclusion.hint }}
              </a-alert>
              <div v-if="structure.conclusion.analysis_suggestion" class="analysis-suggestion">
                <icon-bulb style="color: #F7BA2A" />
                <span>{{ structure.conclusion.analysis_suggestion }}</span>
              </div>
              <div class="outline-box" v-if="structure.conclusion.outline">
                <div class="outline-label">写作提纲</div>
                <div v-if="typeof structure.conclusion.outline === 'object'" class="outline-structured">
                  <div class="outline-item" v-if="structure.conclusion.outline.core_point">
                    <span class="outline-item-label">核心观点：</span>
                    <span>{{ structure.conclusion.outline.core_point }}</span>
                  </div>
                  <div class="outline-item" v-if="structure.conclusion.outline.evidence">
                    <span class="outline-item-label">论据支撑：</span>
                    <span>{{ structure.conclusion.outline.evidence }}</span>
                  </div>
                  <div class="outline-item" v-if="structure.conclusion.outline.angle">
                    <span class="outline-item-label">写作角度：</span>
                    <span>{{ structure.conclusion.outline.angle }}</span>
                  </div>
                  <div class="outline-item" v-if="structure.conclusion.outline.materials">
                    <span class="outline-item-label">可用素材：</span>
                    <span>{{ structure.conclusion.outline.materials }}</span>
                  </div>
                  <div class="outline-item" v-if="structure.conclusion.outline.notes">
                    <span class="outline-item-label">注意事项：</span>
                    <span>{{ structure.conclusion.outline.notes }}</span>
                  </div>
                </div>
                <div class="outline-content" v-else>{{ structure.conclusion.outline }}</div>
              </div>
              <a-textarea
                v-model="sectionContents.conclusion"
                placeholder="在此撰写结论内容..."
                :auto-size="{ minRows: 3, maxRows: 8 }"
                class="section-textarea"
              />
              <!-- P3: 方向性检测结果与操作 -->
              <div class="direction-check" v-if="directionResults['conclusion']">
                <div class="direction-header">
                  <a-tag :color="directionResults['conclusion'].severity_color" size="medium">
                    {{ directionResults['conclusion'].severity_label }}
                  </a-tag>
                  <span class="coverage-rate">覆盖率 {{ Math.round(directionResults['conclusion'].coverage_rate * 100) }}%</span>
                </div>
                <div v-if="directionResults['conclusion'].issues.length > 0" class="direction-issues">
                  <div v-for="(issue, i) in directionResults['conclusion'].issues" :key="i" class="issue-item">
                    <icon-close-circle style="color: #F53F3F" />
                    <span>{{ issue }}</span>
                  </div>
                </div>
                <div class="direction-actions">
                  <a-button type="primary" size="small" @click="openRewriteDialog('conclusion', structure.conclusion.title)">
                    <icon-edit /> 重写该段落
                  </a-button>
                  <a-popconfirm content="确认方向正确，保留当前内容？" @ok="Message.success('已确认')">
                    <a-button size="small">确认保留</a-button>
                  </a-popconfirm>
                </div>
              </div>
            </div>
          </a-spin>
        </a-card>
      </div>

      <!-- 右栏：全文预览 + 原文 -->
      <div class="preview-pane">
        <!-- 全文预览 -->
        <a-card class="preview-card">
          <template #title>
            <div class="card-title">
              <icon-eye />
              <span>全文预览</span>
            </div>
          </template>
          <template #extra>
            <a-tag v-if="hasContent" color="green">{{ totalWords }} 字</a-tag>
          </template>
          <div class="preview-content">
            <div v-if="!hasContent" class="preview-empty">
              <icon-file style="font-size: 48px; color: #e5e6eb" />
              <p>开始撰写内容，预览将实时更新</p>
            </div>
            <div v-else class="markdown-body" v-html="renderedPreview"></div>
          </div>
        </a-card>

        <!-- 原文参考（可折叠） -->
        <a-card class="original-card">
          <template #title>
            <div class="card-title">
              <icon-file />
              <span>原文参考</span>
            </div>
          </template>
          <template #extra>
            <a-button type="text" size="mini" @click="originalCollapsed = !originalCollapsed">
              <icon-up v-if="!originalCollapsed" />
              <icon-down v-if="originalCollapsed" />
              {{ originalCollapsed ? '展开' : '收起' }}
            </a-button>
          </template>
          <div v-show="!originalCollapsed" class="original-content" v-html="renderedOriginal"></div>
        </a-card>
      </div>
    </div>

    <!-- 操作按钮 -->
    <a-space direction="vertical" style="width: 100%">
      <a-button
        type="primary"
        size="large"
        long
        :disabled="!hasContent"
        @click="handleNextWithCheck"
        class="submit-btn"
      >
        <icon-arrow-right />
        下一步：选择分析框架
      </a-button>
      <a-typography-text type="secondary" style="text-align: center; display: block; font-size: 12px">
        完善内容后，系统将为您推荐最适合的分析框架
      </a-typography-text>
    </a-space>

    <!-- P3: 重写对话框 -->
    <a-modal v-model:visible="showRewriteModal" title="重写该段落" width="600px" @ok="handleConfirmRewrite" @cancel="showRewriteModal = false">
      <template #footer>
        <a-space>
          <a-button @click="showRewriteModal = false">取消</a-button>
          <a-button type="primary" @click="handleConfirmRewrite" :loading="!!rewritingSection">
            <icon-edit /> 确认重写
          </a-button>
        </a-space>
      </template>
      <div class="rewrite-dialog-content">
        <p>请告诉 AI 这个段落应该往哪个方向调整：</p>
        <a-textarea
          v-model="userFeedbackText"
          placeholder="比如：不要讲太多理论，重点描述数据是怎么在各个模块之间流动的，最好有具体例子"
          :auto-size="{ minRows: 4, maxRows: 8 }"
        />
        <p class="rewrite-hint">AI 将按照你的指令重写该段落，原提纲作为参考。</p>
      </div>
    </a-modal>

    <!-- P4: 预览对比对话框 -->
    <a-modal v-model:visible="showPreviewDialog" title="📊 优化预览" width="800px" :footer="false">
      <div class="preview-compare">
        <div class="preview-col">
          <h4>优化前</h4>
          <div class="preview-box">{{ previewOldContent }}</div>
        </div>
        <div class="preview-col">
          <h4>优化后</h4>
          <div class="preview-box">{{ previewNewContent }}</div>
        </div>
      </div>
      <div class="preview-actions">
        <a-space>
          <a-button @click="handlePreviewCancel">取消（保留原内容）</a-button>
          <a-button type="primary" @click="handlePreviewConfirm">确认保存</a-button>
        </a-space>
      </div>
    </a-modal>

    <!-- P5: 未确认段落警告对话框 -->
    <a-modal v-model:visible="showUnsavedWarning" title="⚠️ 还有段落未检测" width="500px" :footer="false">
      <div class="warning-dialog">
        <p>以下 {{ uncheckedSections.length }} 个段落未进行方向性检测</p>
        <p>建议先检测方向，确保内容质量。</p>
        <div class="warning-actions">
          <a-space>
            <a-button @click="showUnsavedWarning = false">返回检测</a-button>
            <a-button type="primary" @click="handleForceNext">确认保存（不检测）</a-button>
          </a-space>
        </div>
      </div>
    </a-modal>

    <!-- P5: 优化报告对话框 -->
    <a-modal v-model:visible="showOptimizationReport" title="📊 优化报告" width="500px" :footer="false">
      <div class="optimization-report">
        <div class="report-item">
          <span class="report-label">检测出方向性问题</span>
          <span class="report-value warning">{{ optimizationReport?.total_issues || 0 }} 个</span>
        </div>
        <div class="report-item">
          <span class="report-label">已优化段落</span>
          <span class="report-value success">{{ optimizationReport?.optimized_count || 0 }} 段</span>
        </div>
        <div class="report-item">
          <span class="report-label">保留原样</span>
          <span class="report-value">{{ optimizationReport?.kept_count || 0 }} 段</span>
        </div>
        <div class="report-actions">
          <a-button type="primary" long @click="showOptimizationReport = false; proceedToNext()">
            继续下一步
          </a-button>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { IconFolder, IconEdit, IconArrowRight, IconUp, IconDown, IconRobot, IconBulb, IconFile, IconEye, IconCheckCircle, IconCloseCircle } from '@arco-design/web-vue/es/icon'
import { useAppStore } from '../stores/app'
import { marked } from 'marked'
import { generateContentStructure, aiGenerateSection, aiGenerateFullContent, smartFillContent, generateOutlineVersions, checkDirection, aiRewriteSection, listSupplements as apiListSupplements } from '../utils/api'

const appStore = useAppStore()
const router = useRouter()
const loading = ref(false)
const originalCollapsed = ref(true)
const sectionContents = ref({})
const aiFilling = ref(false)
const aiFillingSections = ref({})
const smartFilling = ref(false)

// 获取 sessionId（从 sessionStorage 获取）
const sessionId = ref(sessionStorage.getItem('sessionId') || '')

// P3/P4/P5 状态
const directionResults = ref({})  // { section_key: { severity, issues, suggestion, ... } }
const rewritingSection = ref(null)
const userFeedbackText = ref('')
const showRewriteModal = ref(false)
const rewriteTargetKey = ref('')
const showPreviewDialog = ref(false)
const previewOldContent = ref('')
const previewNewContent = ref('')
const previewTargetKey = ref('')
const checkingDirections = ref({})
const optimizationReport = ref(null)  // { total_issues, optimized_count, kept_count }
const showOptimizationReport = ref(false)
const showUnsavedWarning = ref(false)
const uncheckedSections = ref([])

const originalSummary = computed(() => appStore.mcpResult?.summary || appStore.inputText || '')
const directionName = computed(() => appStore.selectedDirection?.name || '综合分析报告')
const topicNeeded = computed(() => appStore.mcpResult?.topic_needed || '')

// P0-1: 段落边框颜色（基于检测结果）
const sectionBorderClass = (key) => {
  if (checkingDirections.value[key]) return 'section-checking'
  if (!directionResults.value[key]) return ''
  const severity = directionResults.value[key].severity
  if (severity === 'none') return 'section-aligned'
  if (severity === 'minor') return 'section-minor'
  if (severity === 'medium') return 'section-medium'
  return 'section-severe'
}

// 置信度标注辅助函数
const getConfidenceEmoji = (confidence) => {
  const map = { high: '✅', medium: '⚠️', low: '❓' }
  return map[confidence] || '❓'
}

const getConfidenceLabel = (confidence) => {
  const map = { high: '高置信', medium: '中置信', low: '低置信' }
  return map[confidence] || '低置信'
}

const getConfidenceColor = (confidence) => {
  const map = { high: 'green', medium: 'orange', low: 'red' }
  return map[confidence] || 'red'
}

const getConfidenceTooltip = (confidence) => {
  const map = {
    high: '高置信度：基于原文充足内容，内容可靠性高',
    medium: '中置信度：原文部分充足，部分基于逻辑推演',
    low: '低置信度：原文不足，内容基于逻辑推演，请谨慎使用',
  }
  return map[confidence] || ''
}

// 补充知识库列表（用户可见的已保存补充内容）
const supplementList = ref([])
const supplementLoading = ref(false)

const loadSupplementList = async () => {
  if (!sessionId.value) return
  supplementLoading.value = true
  try {
    const res = await apiListSupplements(sessionId.value, true) // true = only confirmed
    if (res.data.code === 0) {
      supplementList.value = res.data.data.supplements || []
    }
  } catch (e) {
    console.warn('加载补充列表失败:', e)
  } finally {
    supplementLoading.value = false
  }
}

const getSourceLabel = (source) => {
  const map = { 'ai-pulse': 'AI-Pulse', 'manual': '手动补充', 'file': '文件提取' }
  return map[source] || source
}

const getSourceIcon = (source) => {
  const map = { 'ai-pulse': '🤖', 'manual': '✏️', 'file': '' }
  return map[source] || '📌'
}

const getSourceColor = (source) => {
  const map = { 'ai-pulse': 'blue', 'manual': 'orange', 'file': 'purple' }
  return map[source] || 'gray'
}

const renderedOriginal = computed(() => {
  if (!originalSummary.value) return ''
  return marked.parse(originalSummary.value)
})

const structure = ref({
  intro: null,
  sections: [],
  conclusion: null,
})

const hasContent = computed(() => {
  return Object.values(sectionContents.value).some(v => v && v.trim())
})

const totalWords = computed(() => {
  let count = 0
  Object.values(sectionContents.value).forEach(v => {
    if (v && v.trim()) count += v.trim().length
  })
  return count
})

const buildFullContent = () => {
  const parts = []
  if (structure.value.intro && sectionContents.value.intro?.trim()) {
    parts.push(`## ${structure.value.intro.title}\n\n${sectionContents.value.intro.trim()}`)
  }
  structure.value.sections.forEach((section, index) => {
    const key = `section_${index}`
    if (sectionContents.value[key]?.trim()) {
      parts.push(`## ${section.title}\n\n${sectionContents.value[key].trim()}`)
    }
  })
  if (structure.value.conclusion && sectionContents.value.conclusion?.trim()) {
    parts.push(`## ${structure.value.conclusion.title}\n\n${sectionContents.value.conclusion.trim()}`)
  }
  return parts.join('\n\n')
}

const renderedPreview = computed(() => {
  const content = buildFullContent()
  if (!content) return ''
  return marked.parse(content)
})

const loadStructure = async () => {
  loading.value = true
  try {
    const res = await generateContentStructure(directionName.value, originalSummary.value, topicNeeded.value)
    if (res.data.code === 0) {
      structure.value = res.data.data
      // 初始化 sectionContents 为空（提纲仅供参考，内容需 AI 生成或手动填写）
      const contents = {}
      contents.intro = ''
      res.data.data.sections.forEach((sec, i) => {
        contents[`section_${i}`] = ''
      })
      contents.conclusion = ''
      sectionContents.value = contents
      
      // 统计分析类型
      const summary = []
      if (res.data.data.intro?.analysis_type === 'use_original') summary.push('引言：原文充足')
      res.data.data.sections.forEach((sec, i) => {
        if (sec.analysis_type === 'use_original') summary.push(`${sec.title}：原文充足`)
      })
      if (res.data.data.conclusion?.analysis_type === 'use_original') summary.push('结论：原文充足')
      
      if (summary.length > 0) {
        Message.info(`已生成写作提纲。${summary.join('，')}，可直接参考原文撰写`)
      } else {
        Message.success('已生成写作提纲，请确认后点击"AI 生成"撰写内容')
      }
    }
  } catch (error) {
    Message.error('加载内容结构失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

const handleAiFillIntro = async () => {
  const key = 'intro'
  if (aiFillingSections.value[key]) return
  const intro = structure.value.intro
  if (!intro) return

  aiFillingSections.value[key] = true
  try {
    Message.info(`正在生成「${intro.title}」...`)
    const existingSections = {}
    for (const [k, v] of Object.entries(sectionContents.value)) {
      if (k !== key && v && v.trim()) {
        existingSections[k] = v.trim()
      }
    }
    const res = await aiGenerateSection(
      directionName.value,
      intro.title,
      intro.hint,
      originalSummary.value,
      existingSections,
      intro.outline || '',
      intro.analysis_type || '',
      intro.analysis_suggestion || '',
      topicNeeded.value,
      sessionId.value,
    )
    if (res.data.code === 0) {
      let content = res.data.data.content
      content = content.replace(/^```(?:markdown)?\s*/gm, '').replace(/```$/gm, '').trim()
      content = content.replace(/^##\s+.+\n+/gm, '')
      sectionContents.value[key] = content
      Message.success(`「${intro.title}」已生成，请确认并修改`)
      
      // P0-1: 自动生成后自动检测方向
      if (intro.outline) {
        setTimeout(() => {
          handleCheckDirection(key, intro.title, intro.outline)
        }, 800)
      }
    } else {
      Message.error('AI 生成失败: ' + res.data.msg)
    }
  } catch (error) {
    Message.error('AI 生成失败: ' + error.message)
  } finally {
    aiFillingSections.value[key] = false
  }
}

const handleAiFillConclusion = async () => {
  const key = 'conclusion'
  if (aiFillingSections.value[key]) return
  const conclusion = structure.value.conclusion
  if (!conclusion) return

  aiFillingSections.value[key] = true
  try {
    Message.info(`正在生成「${conclusion.title}」...`)
    const existingSections = {}
    for (const [k, v] of Object.entries(sectionContents.value)) {
      if (k !== key && v && v.trim()) {
        existingSections[k] = v.trim()
      }
    }
    const res = await aiGenerateSection(
      directionName.value,
      conclusion.title,
      conclusion.hint,
      originalSummary.value,
      existingSections,
      conclusion.outline || '',
      conclusion.analysis_type || '',
      conclusion.analysis_suggestion || '',
      topicNeeded.value,
      sessionId.value,
    )
    if (res.data.code === 0) {
      let content = res.data.data.content
      content = content.replace(/^```(?:markdown)?\s*/gm, '').replace(/```$/gm, '').trim()
      content = content.replace(/^##\s+.+\n+/gm, '')
      sectionContents.value[key] = content
      Message.success(`「${conclusion.title}」已生成，请确认并修改`)
      
      // P0-1: 自动生成后自动检测方向
      if (conclusion.outline) {
        setTimeout(() => {
          handleCheckDirection(key, conclusion.title, conclusion.outline)
        }, 800)
      }
    } else {
      Message.error('AI 生成失败: ' + res.data.msg)
    }
  } catch (error) {
    Message.error('AI 生成失败: ' + error.message)
  } finally {
    aiFillingSections.value[key] = false
  }
}

const handleAiFillSection = async (index) => {
  const key = `section_${index}`
  if (aiFillingSections.value[key]) return

  const section = structure.value.sections[index]
  if (!section) return

  aiFillingSections.value[key] = true
  try {
    Message.info(`正在生成「${section.title}」...`)
    // 收集已有段落作为上下文
    const existingSections = {}
    for (const [k, v] of Object.entries(sectionContents.value)) {
      if (k !== key && v && v.trim()) {
        existingSections[k] = v.trim()
      }
    }
    const res = await aiGenerateSection(
      directionName.value,
      section.title,
      section.hint,
      originalSummary.value,
      existingSections,
      section.outline || '',
      section.analysis_type || '',
      section.analysis_suggestion || '',
      topicNeeded.value,
      sessionId.value,
    )
    if (res.data.code === 0) {
      let content = res.data.data.content
      // 清理 Markdown 代码块标记
      content = content.replace(/^```(?:markdown)?\s*/gm, '').replace(/```$/gm, '').trim()
      // 去除段落开头的标题（如果 AI 输出了）
      content = content.replace(/^##\s+.+\n+/gm, '')
      sectionContents.value[key] = content
      Message.success(`「${section.title}」已生成，请确认并修改`)
      
      // P0-1: 自动生成后自动检测方向
      if (section.outline) {
        setTimeout(() => {
          handleCheckDirection(key, section.title, section.outline)
        }, 800)
      }
    } else {
      Message.error('AI 生成失败: ' + res.data.msg)
    }
  } catch (error) {
    Message.error('AI 生成失败: ' + error.message)
  } finally {
    aiFillingSections.value[key] = false
  }
}

const handleAiFillAll = async () => {
  if (aiFilling.value) return
  aiFilling.value = true
  try {
    Message.info('AI 正在生成全文，请稍候...')
    const res = await aiGenerateFullContent(directionName.value, structure.value, originalSummary.value, sessionId.value)
    if (res.data.code === 0) {
      let fullContent = res.data.data.content
      // 清理 Markdown 代码块标记
      fullContent = fullContent.replace(/^```(?:markdown)?\s*/gm, '').replace(/```$/gm, '').trim()
      // 解析各段落内容并分配到对应 section
      const sections = structure.value.sections || []
      const lines = fullContent.split('\n')
      let currentKey = null
      let currentParts = []
      const parsed = {}

      // 简单解析：按 ## 标题分段落
      for (const line of lines) {
        const headingMatch = line.match(/^##\s+(.+)$/)
        if (headingMatch) {
          // 保存上一个段落
          if (currentKey && currentParts.length > 0) {
            parsed[currentKey] = currentParts.join('\n').trim()
          }
          // 匹配标题找到对应 key
          const title = headingMatch[1].trim()
          const introTitle = structure.value.intro?.title
          const conclusionTitle = structure.value.conclusion?.title
          if (introTitle && title.includes(introTitle)) {
            currentKey = 'intro'
          } else if (conclusionTitle && title.includes(conclusionTitle)) {
            currentKey = 'conclusion'
          } else {
            const secIndex = sections.findIndex(s => title.includes(s.title))
            currentKey = secIndex >= 0 ? `section_${secIndex}` : null
          }
          currentParts = []
        } else if (currentKey && line.trim()) {
          currentParts.push(line)
        }
      }
      // 保存最后一个段落
      if (currentKey && currentParts.length > 0) {
        parsed[currentKey] = currentParts.join('\n').trim()
      }
      // 将解析结果填充到表单
      for (const [k, v] of Object.entries(parsed)) {
        if (sectionContents.value[k] !== undefined) {
          sectionContents.value[k] = v
        }
      }
      
      // P0-1: 全文生成后自动检测方向
      const allKeys = ['intro']
      structure.value.sections.forEach((sec, i) => allKeys.push(`section_${i}`))
      allKeys.push('conclusion')
      allKeys.forEach(key => {
        if (sectionContents.value[key]?.trim()) {
          let sectionInfo = null
          if (key === 'intro') sectionInfo = structure.value.intro
          else if (key === 'conclusion') sectionInfo = structure.value.conclusion
          else {
            const idx = parseInt(key.replace('section_', ''))
            sectionInfo = structure.value.sections[idx]
          }
          if (sectionInfo?.outline) {
            setTimeout(() => {
              handleCheckDirection(key, sectionInfo.title, sectionInfo.outline)
            }, 1500)
          }
        }
      })
      
      Message.success('全文已生成，请逐段确认和修改')
    } else {
      Message.error('AI 生成失败: ' + res.data.msg)
    }
  } catch (error) {
    Message.error('AI 生成失败: ' + error.message)
  } finally {
    aiFilling.value = false
  }
}

const handleNext = () => {
  const content = buildFullContent()
  if (!content.trim()) {
    Message.warning('请至少完成一个段落')
    return
  }
  appStore.inputText = content.trim()
  Message.success('内容已保存，正在为您匹配分析框架...')
  router.push('/frameworks')
}

// 构建分析对象，用于传递给智能补全接口
const buildAnalysisObject = () => {
  const analysis = {}
  if (structure.value.intro) {
    analysis.intro = {
      type: structure.value.intro.analysis_type || 'add_new',
      suggestion: structure.value.intro.analysis_suggestion || ''
    }
  }
  structure.value.sections.forEach((sec, i) => {
    analysis[`section_${i}`] = {
      type: sec.analysis_type || 'add_new',
      suggestion: sec.analysis_suggestion || ''
    }
  })
  if (structure.value.conclusion) {
    analysis.conclusion = {
      type: structure.value.conclusion.analysis_type || 'add_new',
      suggestion: structure.value.conclusion.analysis_suggestion || ''
    }
  }
  return analysis
}

const handleSmartFill = async () => {
  if (smartFilling.value) return
  smartFilling.value = true
  try {
    Message.info('正在智能补全全文，请稍候...')
    
    const analysis = buildAnalysisObject()
    const res = await smartFillContent(
      directionName.value,
      structure.value,
      originalSummary.value,
      analysis
    )
    if (res.data.code === 0) {
      const { sections, ai_generated, original_used } = res.data.data
      sectionContents.value = sections
      Message.success(`补全完成！AI 生成 ${ai_generated} 段，原文 ${original_used} 段`)
    } else {
      Message.error('智能补全失败: ' + res.data.msg)
    }
  } catch (error) {
    Message.error('智能补全失败: ' + error.message)
  } finally {
    smartFilling.value = false
  }
}

onMounted(() => {
  loadStructure()
  loadSupplementList()
})

// P3: 运行方向性检测（单个段落）
const handleCheckDirection = async (key, sectionTitle, sectionOutline) => {
  const content = sectionContents.value[key]
  if (!content || !content.trim()) {
    Message.warning('请先撰写或生成该段落内容')
    return
  }
  
  // 将结构化提纲转换为字符串
  let outlineStr = ''
  if (typeof sectionOutline === 'object' && sectionOutline !== null) {
    const parts = []
    if (sectionOutline.core_point) parts.push(`核心观点：${sectionOutline.core_point}`)
    if (sectionOutline.evidence) parts.push(`论据支撑：${sectionOutline.evidence}`)
    if (sectionOutline.angle) parts.push(`写作角度：${sectionOutline.angle}`)
    if (sectionOutline.materials) parts.push(`可用素材：${sectionOutline.materials}`)
    if (sectionOutline.notes) parts.push(`注意事项：${sectionOutline.notes}`)
    outlineStr = parts.join('\n')
  } else {
    outlineStr = sectionOutline || ''
  }
  
  checkingDirections.value[key] = true
  try {
    const res = await checkDirection(sectionTitle, outlineStr, content)
    if (res.data.code === 0) {
      directionResults.value[key] = res.data.data
      const d = res.data.data
      if (d.severity === 'none') {
        Message.success(`${sectionTitle}：${d.severity_label}（覆盖率 ${Math.round(d.coverage_rate * 100)}%）`)
      } else {
        Message.warning(`${sectionTitle}：${d.severity_label}`)
      }
    }
  } catch (error) {
    Message.error('检测失败: ' + error.message)
  } finally {
    checkingDirections.value[key] = false
  }
}

// P3: 打开重写对话框
const openRewriteDialog = (key, sectionTitle) => {
  rewriteTargetKey.value = key
  userFeedbackText.value = ''
  showRewriteModal.value = true
}

// P3: 确认重写（带用户反馈）
const handleConfirmRewrite = async () => {
  const key = rewriteTargetKey.value
  const feedback = userFeedbackText.value.trim()

  // 找到对应的 section 信息
  let sectionInfo = null
  if (key === 'intro') {
    sectionInfo = structure.value.intro
  } else if (key === 'conclusion') {
    sectionInfo = structure.value.conclusion
  } else {
    const idx = parseInt(key.replace('section_', ''))
    sectionInfo = structure.value.sections[idx]
  }
  if (!sectionInfo) return

  // 保存旧内容用于预览对比（P4）
  const oldContent = sectionContents.value[key] || ''

  rewritingSection.value = key
  showRewriteModal.value = false
  try {
    Message.info(`正在重写「${sectionInfo.title}」...`)
    const existingSections = {}
    for (const [k, v] of Object.entries(sectionContents.value)) {
      if (k !== key && v && v.trim()) {
        existingSections[k] = v.trim()
      }
    }
    const res = await aiRewriteSection(
      directionName.value,
      sectionInfo.title,
      sectionInfo.outline || '',
      feedback,
      originalSummary.value,
      existingSections,
      sessionId.value,
    )
    if (res.data.code === 0) {
      let newContent = res.data.data.content
      newContent = newContent.replace(/^```(?:markdown)?\s*/gm, '').replace(/```$/gm, '').trim()
      newContent = newContent.replace(/^##\s+.+\n+/gm, '')

      // P4: 显示预览对比
      previewOldContent.value = oldContent
      previewNewContent.value = newContent
      previewTargetKey.value = key
      showPreviewDialog.value = true
    } else {
      Message.error('重写失败: ' + res.data.msg)
    }
  } catch (error) {
    Message.error('重写失败: ' + error.message)
  } finally {
    rewritingSection.value = null
  }
}

// P4: 确认保存预览中的新内容
const handlePreviewConfirm = () => {
  sectionContents.value[previewTargetKey.value] = previewNewContent.value
  showPreviewDialog.value = false
  Message.success('已保存新内容')

  // 自动运行方向性检测
  const key = previewTargetKey.value
  let sectionInfo = null
  if (key === 'intro') {
    sectionInfo = structure.value.intro
  } else if (key === 'conclusion') {
    sectionInfo = structure.value.conclusion
  } else {
    const idx = parseInt(key.replace('section_', ''))
    sectionInfo = structure.value.sections[idx]
  }
  if (sectionInfo && sectionInfo.outline) {
    setTimeout(() => handleCheckDirection(key, sectionInfo.title, sectionInfo.outline), 500)
  }
}

// P4: 取消预览，保留旧内容
const handlePreviewCancel = () => {
  showPreviewDialog.value = false
  Message.info('已取消，保留原内容')
}

// P5: 生成优化报告
const generateOptimizationReport = () => {
  let totalIssues = 0
  let optimizedCount = 0
  let keptCount = 0

  // 统计检测结果
  Object.entries(directionResults.value).forEach(([key, result]) => {
    if (result.severity !== 'none') {
      totalIssues++
    }
    // 如果该段落有内容，认为已优化
    if (sectionContents.value[key] && sectionContents.value[key].trim()) {
      optimizedCount++
    } else {
      keptCount++
    }
  })

  optimizationReport.value = {
    total_issues: totalIssues,
    optimized_count: optimizedCount,
    kept_count: keptCount,
  }
  showOptimizationReport.value = true
}

// P5: 检查未确认段落，弹出警告
const handleNextWithCheck = () => {
  // 收集未检测或未确认的段落
  const allKeys = ['intro']
  structure.value.sections.forEach((sec, i) => {
    allKeys.push(`section_${i}`)
  })
  allKeys.push('conclusion')

  const unchecked = []
  allKeys.forEach(key => {
    if (!directionResults.value[key]) {
      let title = ''
      if (key === 'intro') title = structure.value.intro?.title || '引言'
      else if (key === 'conclusion') title = structure.value.conclusion?.title || '结论'
      else {
        const idx = parseInt(key.replace('section_', ''))
        title = structure.value.sections[idx]?.title || `第${idx + 1}部分`
      }
      if (title && sectionContents.value[key]?.trim()) {
        unchecked.push(title)
      }
    }
  })

  if (unchecked.length > 0) {
    uncheckedSections.value = unchecked
    showUnsavedWarning.value = true
  } else {
    // 没有未确认的段落，生成优化报告并跳转
    generateOptimizationReport()
    proceedToNext()
  }
}

const handleForceNext = () => {
  showUnsavedWarning.value = false
  generateOptimizationReport()
  proceedToNext()
}

const proceedToNext = () => {
  const content = buildFullContent()
  if (!content.trim()) {
    Message.warning('请至少完成一个段落')
    return
  }
  // 将优化报告附加到 appStore
  if (optimizationReport.value) {
    appStore.optimimizationReport = optimizationReport.value
  }
  appStore.inputText = content.trim()
  Message.success('内容已保存，正在为您匹配分析框架...')
  router.push('/frameworks')
}
</script>

<style scoped>
.data-input-view {
  max-width: 1600px;
  margin: 0 auto;
  padding: 20px;
}
.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}
.info-card {
  margin-bottom: 16px;
}
.info-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.info-label {
  font-size: 13px;
  color: #86909c;
  min-width: 70px;
}
.info-value {
  font-size: 14px;
  color: #333;
}

/* 三栏布局 */
.main-layout {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
  min-height: 500px;
}
.edit-pane {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  max-height: 800px;
}
.edit-card {
  height: 100%;
}
.preview-pane {
  width: 480px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.preview-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.preview-content {
  flex: 1;
  overflow-y: auto;
  min-height: 200px;
  max-height: 500px;
  padding: 4px;
}
.preview-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #c9cdd4;
}
.preview-empty p {
  margin-top: 12px;
  font-size: 13px;
}
.markdown-body {
  line-height: 1.8;
  font-size: 13px;
  color: #1d2129;
}
.markdown-body :deep(h1), .markdown-body :deep(h2), .markdown-body :deep(h3) {
  margin: 16px 0 8px;
  font-size: 15px;
}
.markdown-body :deep(ul), .markdown-body :deep(ol) {
  padding-left: 20px;
}
.markdown-body :deep(p) {
  margin: 8px 0;
}
.original-card {
  max-height: 300px;
  display: flex;
  flex-direction: column;
}
.original-content {
  line-height: 1.8;
  font-size: 12px;
  color: #4e5969;
  max-height: 250px;
  overflow-y: auto;
  padding: 4px;
}
.original-content :deep(h1), .original-content :deep(h2), .original-content :deep(h3) {
  margin: 10px 0 6px;
  font-size: 13px;
}
.original-content :deep(ul), .original-content :deep(ol) {
  padding-left: 16px;
}

/* 段落区块 */
.section-block {
  margin-bottom: 24px;
  padding-bottom: 24px;
  border-bottom: 1px solid #f0f0f0;
  transition: border-left-color 0.3s ease;
  border-left: 3px solid transparent;
}
.section-block.section-checking {
  border-left-color: #165dff;
}
.section-block.section-aligned {
  border-left-color: #00b42a;
}
.section-block.section-minor {
  border-left-color: #f7ba2a;
}
.section-block.section-medium {
  border-left-color: #ff7d00;
}
.section-block.section-severe {
  border-left-color: #f53f3f;
}
.section-block:last-child {
  border-bottom: none;
}

/* P0-2: 补充知识库展示样式 */
.supplement-kb-section {
  margin-bottom: 24px;
  padding: 16px;
  background: linear-gradient(135deg, #f6ffed 0%, #e6f7ff 100%);
  border-radius: 8px;
  border: 1px solid #b7eb8f;
}
.supplement-list {
  background: transparent;
}
.supplement-item {
  width: 100%;
  padding: 8px 0;
}
.supplement-dimension {
  display: inline-block;
  margin-left: 8px;
  font-size: 13px;
  color: #4e5969;
  font-weight: 500;
}
.supplement-content {
  margin-top: 6px;
  font-size: 13px;
  color: #1d2129;
  line-height: 1.6;
  white-space: pre-wrap;
  max-height: 120px;
  overflow-y: auto;
  background: rgba(255, 255, 255, 0.6);
  padding: 8px 12px;
  border-radius: 4px;
}
.conclusion-block {
  border-top: 2px solid #00b42a;
  padding-top: 16px;
}
.section-header {
  margin-bottom: 8px;
}
.section-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #1d2129;
}
.word-count {
  font-size: 12px;
  color: #86909c;
}
.ai-hint {
  margin-bottom: 12px;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.6;
  background: #f0f7ff;
  border-color: #d4e8ff;
}
.analysis-suggestion {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 10px 14px;
  margin-bottom: 12px;
  background: #fffbe6;
  border: 1px solid #ffe58f;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.6;
  color: #614700;
}
.outline-box {
  margin-bottom: 12px;
  padding: 12px 14px;
  background: #f7f8fa;
  border: 1px solid #e5e6eb;
  border-radius: 6px;
}
.outline-label {
  font-size: 12px;
  color: #86909c;
  margin-bottom: 6px;
  font-weight: 500;
}
.outline-content {
  font-size: 13px;
  line-height: 1.7;
  color: #4e5969;
  white-space: pre-wrap;
}
.outline-structured {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.outline-item {
  display: flex;
  gap: 6px;
  font-size: 13px;
  line-height: 1.7;
  color: #4e5969;
}
.outline-item-label {
  font-weight: 600;
  color: #1d2129;
  min-width: 70px;
  flex-shrink: 0;
}
.section-textarea {
  font-size: 14px;
  line-height: 1.8;
}

.submit-btn {
  height: 48px;
  font-size: 16px;
}

/* P3: 方向性检测 */
.direction-check {
  margin-top: 12px;
  padding: 12px 14px;
  background: #fff7f0;
  border: 1px solid #ffe7ba;
  border-radius: 8px;
}
.direction-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.coverage-rate {
  font-size: 12px;
  color: #86909c;
}
.direction-issues {
  margin-bottom: 10px;
}
.issue-item {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-bottom: 4px;
  font-size: 13px;
  color: #f53f3f;
}
.direction-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

/* P3: 重写对话框 */
.rewrite-dialog-content p {
  margin-bottom: 10px;
  color: #4e5969;
}
.rewrite-hint {
  margin-top: 10px;
  font-size: 12px;
  color: #86909c;
  font-style: italic;
}

/* P4: 预览对比 */
.preview-compare {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}
.preview-col {
  flex: 1;
  min-width: 0;
}
.preview-col h4 {
  margin: 0 0 8px;
  font-size: 14px;
  color: #4e5969;
}
.preview-box {
  padding: 12px;
  background: #f7f8fa;
  border: 1px solid #e5e6eb;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.7;
  max-height: 300px;
  overflow-y: auto;
  white-space: pre-wrap;
}
.preview-actions {
  display: flex;
  justify-content: center;
  padding-top: 12px;
  border-top: 1px solid #e5e6eb;
}

/* P5: 未确认警告 */
.warning-dialog p {
  margin-bottom: 10px;
  color: #4e5969;
}
.unchecked-list {
  margin: 10px 0;
  padding-left: 20px;
  color: #f53f3f;
}
.unchecked-list li {
  margin-bottom: 4px;
}
.warning-hint {
  font-size: 12px;
  color: #86909c;
  margin-bottom: 16px;
}
.warning-actions {
  display: flex;
  justify-content: center;
}

/* P5: 优化报告 */
.optimization-report {
  padding: 16px 0;
}
.report-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}
.report-item:last-of-type {
  border-bottom: none;
}
.report-label {
  font-size: 14px;
  color: #4e5969;
}
.report-value {
  font-size: 18px;
  font-weight: 600;
  color: #1d2129;
}
.report-value.warning {
  color: #f7ba2a;
}
.report-value.success {
  color: #00b42a;
}
.report-actions {
  margin-top: 20px;
}
</style>
