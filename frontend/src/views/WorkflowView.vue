<template>
  <div class="workflow-view">
    <a-page-header title="智能写作工作流" @back="$router.push('/mcp-search')">
    </a-page-header>

    <!-- 进度条 -->
    <div class="progress-bar">
      <a-steps :current="currentStep" direction="horizontal" size="small" style="max-width: 100%; margin: 0 auto">
        <a-step title="扫描" />
        <a-step title="评估" />
        <a-step title="方向" />
        <a-step title="补充1" />
        <a-step title="框架" />
        <a-step title="补充2" />
        <a-step title="检测" />
        <a-step title="结构" />
        <a-step title="补充3" />
        <a-step title="提纲" />
      </a-steps>
    </div>

    <!-- 主内容区 -->
    <div class="content-area">
      <a-spin :loading="loading">
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
          <a-card title="信息完整度评估">
            <!-- 加载中 -->
            <div v-if="loading" style="text-align: center; padding: 80px 0">
              <a-spin dot size="large" tip="正在评估信息完整度..." />
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
            <template v-else>
              <a-progress :percent="completenessResult.completeness" :color="getCompletenessColor(completenessResult.completeness)" :stroke-width="12" />
              <div style="margin-top: 12px">
                <a-tag :color="getCompletenessColor(completenessResult.completeness)" size="large">
                  信息完整度：{{ completenessResult.completeness }}%
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
                      <!-- 已补充：显示绿色勾+补充内容 -->
                      <template v-if="isSupplemented(index)">
                        <icon-check-circle-fill style="color: #00b42a; margin-right: 8px; font-size: 16px" />
                        <div style="flex: 1">
                          <div style="font-size: 14px">{{ item }}</div>
                          <div v-if="getSupplementContent(index)" style="margin-top: 6px; padding: 8px; background: #fff; border-radius: 4px; font-size: 13px; color: #4e5969; line-height: 1.6; max-height: 80px; overflow-y: auto">
                            {{ getSupplementContent(index) }}
                          </div>
                        </div>
                        <a-button type="primary" text size="mini" style="margin-left: 8px" @click="openSupplementModal(index, true)">
                          编辑
                        </a-button>
                      </template>
                      <!-- 未补充：显示红色叉+去补充按钮 -->
                      <template v-else>
                        <icon-close-circle-fill style="color: #f53f3f; margin-right: 8px; font-size: 16px" />
                        <div style="flex: 1; font-size: 14px">{{ item }}</div>
                        <a-button type="primary" size="mini" style="margin-left: 8px" @click="openSupplementModal(index)">
                          去补充
                        </a-button>
                      </template>
                    </a-list-item>
                  </template>
                </a-list>
              </div>

              <div v-if="completenessResult.missing_optional?.length" style="margin-top: 12px">
                <a-typography-text type="secondary">
                  可选缺失项（AI可尝试推断）：{{ completenessResult.missing_optional.join('、') }}
                </a-typography-text>
              </div>

              <a-space style="margin-top: 20px" wrap>
                <!-- 5A: 信息充足 -->
                <a-button v-if="completenessResult.completeness >= 80" type="primary" status="success" size="large" @click="skipToOutline">
                  ✅ 信息充足，直接生成提纲
                </a-button>

                <!-- 5B/5C: 需要补充 -->
                <template v-else>
                  <a-alert type="warning" style="width: 100%; margin-bottom: 16px">
                    <template #title>建议模式：5B（需要您补充）</template>
                    {{ completenessResult.completeness >= 60 ? '建议补充关键信息以提升文章质量' : '信息不足，必须补充后才能生成高质量内容' }}
                  </a-alert>

                  <a-button type="primary" size="large" @click="openModeModal('manual')">
                    ✏️ 我手动补充
                  </a-button>
                  <a-button status="warning" size="large" @click="openModeModal('ai-pulse')">
                    🤖 调用 AI-Pulse 获取
                  </a-button>
                  <a-button v-if="completenessResult.completeness >= 60" size="large" @click="skipToOutline">
                    ⏭️ 跳过，直接生成（质量可能较低）
                  </a-button>
                </template>
              </a-space>
            </template>
          </a-card>
        </div>

        <!-- 关键缺失项补充弹窗 -->
        <a-modal v-model:visible="supplementModalVisible" title="补充缺失项" width="700px" @ok="confirmSupplementModal" @cancel="closeSupplementModal">
          <div v-if="currentSupplementItem" class="supplement-modal-content">
            <a-alert type="warning" style="margin-bottom: 16px">
              <template #title>待补充内容</template>
              {{ currentSupplementItem }}
            </a-alert>

            <!-- AI 补充按钮 - 放在最上方 -->
            <a-form-item label="" style="margin-bottom: 16px">
              <a-button type="primary" long :loading="aiSupplementing" @click="aiAutoSupplement" style="margin-bottom: 16px">
                <icon-robot /> AI 根据上下文自动补充
              </a-button>
            </a-form-item>

            <a-divider orientation="left" style="margin: 12px 0">或手动补充</a-divider>

            <a-form layout="vertical">
              <a-form-item label="补充方式">
                <a-radio-group v-model="supplementModalMethod">
                  <a-radio value="text">手动输入</a-radio>
                  <a-radio value="file">从知识库选择文件</a-radio>
                </a-radio-group>
              </a-form-item>
              <a-form-item v-if="supplementModalMethod === 'text'" label="补充内容">
                <a-textarea
                  v-model="supplementModalText"
                  placeholder="请输入你想补充的内容，例如：具体的案例、数据、定义等..."
                  :auto-size="{ minRows: 5, maxRows: 10 }"
                />
              </a-form-item>
              <a-form-item v-if="supplementModalMethod === 'file'" label="选择文件">
                <a-tree-select
                  v-model="supplementModalFile"
                  :data="kbTreeData"
                  placeholder="选择包含相关内容的文件..."
                  tree-checkable
                  allow-search
                  @change="onSupplementFileChange"
                />
              </a-form-item>

              <!-- 文件选择后显示AI提取预览 -->
              <a-form-item v-if="supplementModalMethod === 'file' && supplementModalFile.length > 0" label="AI 提取预览">
                <a-spin :loading="extractingFileContent" dot>
                  <div v-if="extractedFileContent" class="extracted-content-preview">
                    <a-alert type="info" style="margin-bottom: 8px">
                      <template #title>📄 已从 {{ extractedFileCount }} 个文件中提取内容</template>
                      AI 正在分析文件内容，提取与「{{ currentSupplementItem }}」相关的信息...
                    </a-alert>
                    <a-textarea
                      v-model="supplementModalText"
                      :auto-size="{ minRows: 6, maxRows: 12 }"
                      placeholder="AI 提取的内容将显示在这里，您可以编辑后点击确定..."
                    />
                    <a-typography-text type="secondary" style="font-size: 12px; margin-top: 4px; display: block">
                      提示：提取内容基于文件全文分析，您可以直接编辑或补充
                    </a-typography-text>
                  </div>
                </a-spin>
              </a-form-item>
            </a-form>
          </div>
        </a-modal>

        <!-- Step 2: 推荐写作方向 -->
        <div v-if="currentStep === 2" class="step-content">
          <a-card title="推荐写作方向">
            <template #extra>
              <a-tag>共 {{ directions.length }} 个方向</a-tag>
            </template>
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
                  选择此方向并补充信息
                </a-button>
              </a-card>
            </div>
          </a-card>
        </div>

        <!-- Step 3: 补充1 - 方向相关信息 -->
        <div v-if="currentStep === 3" class="step-content">
          <a-card title="第 1 次补充：方向相关信息">
            <a-alert type="info" style="margin-bottom: 16px">
              <template #title>补充目标</template>
              为「{{ selectedDirection?.name }}」方向补充关键信息，帮助AI更好地理解你的需求
            </a-alert>

            <a-form :model="supplement1Form" layout="vertical">
              <a-form-item label="补充方式">
                <a-radio-group v-model="supplement1Method">
                  <a-radio value="file">从知识库选择文件</a-radio>
                  <a-radio value="text">粘贴补充文本</a-radio>
                  <a-radio value="form">填写快速表单</a-radio>
                </a-radio-group>
              </a-form-item>

              <!-- 方式1: 文件选择 -->
              <a-form-item v-if="supplement1Method === 'file'" label="选择文件">
                <a-tree-select
                  v-model="supplement1File"
                  :data="kbTreeData"
                  placeholder="选择要补充的文件..."
                  tree-checkable
                  allow-search
                />
                <a-typography-text type="secondary" style="margin-top: 8px; display: block">
                  AI 将自动从选中文件中提取相关信息
                </a-typography-text>
              </a-form-item>

              <!-- 方式2: 文本输入 -->
              <a-form-item v-if="supplement1Method === 'text'" label="补充文本">
                <a-textarea
                  v-model="supplement1Text"
                  placeholder="粘贴你想补充的信息，例如：目标读者、应用场景、预期收益等..."
                  :auto-size="{ minRows: 4, maxRows: 10 }"
                />
              </a-form-item>

              <!-- 方式3: 快速表单 -->
              <div v-if="supplement1Method === 'form'" class="quick-form">
                <a-form-item label="目标读者">
                  <a-select v-model="supplement1Form.targetAudience" placeholder="选择目标读者群体" allow-search>
                    <a-option value="企业主">企业主</a-option>
                    <a-option value="中层管理者">中层管理者</a-option>
                    <a-option value="专业人士">专业人士</a-option>
                    <a-option value="个人创作者">个人创作者</a-option>
                    <a-option value="其他">其他</a-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="核心场景">
                  <a-checkbox-group v-model="supplement1Form.scenarios">
                    <a-checkbox value="产品创作">产品创作</a-checkbox>
                    <a-checkbox value="个人成长">个人成长</a-checkbox>
                    <a-checkbox value="组织赋能">组织赋能</a-checkbox>
                    <a-checkbox value="商业决策">商业决策</a-checkbox>
                    <a-checkbox value="知识管理">知识管理</a-checkbox>
                  </a-checkbox-group>
                </a-form-item>
                <a-form-item label="预期收益">
                  <a-input v-model="supplement1Form.expectedBenefit" placeholder="例如：节省时间、提升效率、降低成本..." />
                </a-form-item>
                <a-form-item label="其他补充信息">
                  <a-textarea v-model="supplement1Form.otherInfo" placeholder="任何其他你想补充的信息..." :auto-size="{ minRows: 2, maxRows: 5 }" />
                </a-form-item>
              </div>
            </a-form>

            <a-space style="margin-top: 16px">
              <a-button type="primary" @click="submitSupplement1">确认补充，下一步</a-button>
              <a-button @click="skipSupplement1">跳过补充</a-button>
            </a-space>
          </a-card>
        </div>

        <!-- Step 4: 推荐分析框架 -->
        <div v-if="currentStep === 4" class="step-content">
          <a-card title="推荐分析框架">
            <a-alert type="info" style="margin-bottom: 16px">
              <template #title>已选定方向</template>
              {{ selectedDirection?.name }}（匹配度 {{ (selectedDirection?.coverage * 100).toFixed(0) }}%）
            </a-alert>

            <div v-for="(f, i) in frameworks" :key="i" class="framework-card">
              <a-card :bordered="true" hoverable>
                <template #title>
                  <span v-if="i === 0">🥇 </span>
                  <span v-else-if="i === 1">🥈 </span>
                  <span v-else-if="i === 2">🥉 </span>
                  {{ f.name }}
                  <a-tag :color="f.match_score > 0.7 ? 'green' : 'arcoblue'" style="margin-left: 8px">
                    匹配度 {{ (f.match_score * 100).toFixed(0) }}%
                  </a-tag>
                </template>
                <div>{{ f.description }}</div>
                <a-typography-text type="secondary" style="margin-top: 8px; display: block">
                  适合原因：{{ f.reason }}
                </a-typography-text>
                <div v-if="f.needs_supplement?.length" style="margin-top: 8px">
                  <a-typography-text type="secondary" style="font-size: 13px">
                    使用该框架还需要：{{ f.needs_supplement.join('、') }}
                  </a-typography-text>
                </div>
                <a-button type="primary" status="success" style="margin-top: 12px" @click="selectFramework(f)">
                  选择此框架
                </a-button>
              </a-card>
            </div>
          </a-card>
        </div>

        <!-- Step 5: 补充2 - 完善分析内容 -->
        <div v-if="currentStep === 5" class="step-content">
          <a-card title="第 2 次补充：完善分析内容">
            <a-alert type="info" style="margin-bottom: 16px">
              <template #title>当前信息状态</template>
              <div v-if="supplement1Result">
                ✅ 方向：{{ selectedDirection?.name }}<br>
                ✅ 目标读者：{{ supplement1Result.targetAudience || '未指定' }}<br>
                ✅ 核心场景：{{ (supplement1Result.scenarios || []).join('、') || '未指定' }}
              </div>
            </a-alert>

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

            <a-space style="margin-top: 16px">
              <a-button type="primary" @click="submitSupplement2">确认补充，进入方向检测</a-button>
              <a-button @click="skipSupplement2">跳过补充</a-button>
            </a-space>
          </a-card>
        </div>

        <!-- Step 6: 方向检测 -->
        <div v-if="currentStep === 6" class="step-content">
          <a-card title="方向检测">
            <a-alert type="info" style="margin-bottom: 16px">
              检测分析内容是否存在方向偏离、案例不足、结构混乱等问题
            </a-alert>

            <a-button type="primary" size="large" long :loading="checkingDirection" @click="runDirectionCheck">
              <icon-scan /> 一键检测
            </a-button>

            <div v-if="directionCheckResult" style="margin-top: 20px">
              <a-typography-text strong>检测结果（综合评分：{{ directionCheckResult.overall_score }}/100）</a-typography-text>
              
              <div v-for="(issue, i) in directionCheckResult.issues" :key="i" class="check-issue">
                <a-card :bordered="true" :style="{ marginTop: '12px', borderLeft: `4px solid ${getIssueColor(issue.type)}` }">
                  <template #title>
                    <span :style="{ color: getIssueColor(issue.type) }">
                      <icon-check-circle-fill v-if="issue.type === 'pass'" />
                      <icon-exclamation-circle-fill v-else-if="issue.type === 'warning'" />
                      <icon-close-circle-fill v-else />
                      {{ issue.title }}
                    </span>
                    <a-tag :color="getIssueTagColor(issue.type)" style="margin-left: 8px">
                      {{ issue.type === 'pass' ? '通过' : issue.type === 'warning' ? '建议' : '错误' }}
                    </a-tag>
                  </template>
                  <div>{{ issue.description }}</div>
                  <div v-if="issue.type !== 'pass'" style="margin-top: 8px">
                    <a-typography-text type="secondary">建议：{{ issue.suggestion }}</a-typography-text>
                  </div>
                  <div v-if="issue.type !== 'pass' && issue.can_auto_fix" style="margin-top: 8px">
                    <a-button type="primary" size="small" @click="autoFixIssue(issue)">
                      <icon-robot /> AI 自动修改
                    </a-button>
                    <a-button size="small" style="margin-left: 8px" @click="ignoreIssue(issue)">
                      忽略
                    </a-button>
                  </div>
                </a-card>
              </div>

              <a-space style="margin-top: 16px">
                <a-button v-if="directionCheckResult.ready_for_next" type="primary" status="success" @click="goToStructures">
                  确认通过，进入结构推荐
                </a-button>
                <a-button v-else type="primary" status="warning" @click="goToStructures">
                  仍有问题，但仍继续
                </a-button>
                <a-button @click="goBackToSupplement2">返回补充</a-button>
              </a-space>
            </div>
          </a-card>
        </div>

        <!-- Step 7: 推荐内容结构 -->
        <div v-if="currentStep === 7" class="step-content">
          <a-card title="推荐内容结构">
            <a-alert type="info" style="margin-bottom: 16px">
              <template #title>已选定</template>
              方向：{{ selectedDirection?.name }} | 框架：{{ selectedFramework?.name }}
            </a-alert>

            <div v-for="(s, i) in structures" :key="i" class="structure-card">
              <a-card :bordered="true" hoverable>
                <template #title>
                  <span v-if="i === 0"> </span>
                  <span v-else-if="i === 1">🥈 </span>
                  {{ s.name }}
                  <a-tag :color="s.match_score > 0.7 ? 'green' : 'arcoblue'" style="margin-left: 8px">
                    匹配度 {{ (s.match_score * 100).toFixed(0) }}%
                  </a-tag>
                </template>
                <div>{{ s.description }}</div>
                <a-typography-text type="secondary" style="margin-top: 8px; display: block">
                  适用原因：{{ s.reason }}
                </a-typography-text>
                <div v-if="s.needs_supplement?.length" style="margin-top: 8px">
                  <a-typography-text type="secondary" style="font-size: 13px">
                    使用该结构还需要：{{ s.needs_supplement.join('、') }}
                  </a-typography-text>
                </div>
                <a-button type="primary" status="success" style="margin-top: 12px" @click="selectStructure(s)">
                  选择此结构
                </a-button>
              </a-card>
            </div>
          </a-card>
        </div>

        <!-- Step 8: 补充3 - 案例/数据 -->
        <div v-if="currentStep === 8" class="step-content">
          <a-card title="第 3 次补充：案例/数据">
            <a-alert type="info" style="margin-bottom: 16px">
              <template #title>当前信息状态</template>
              ✅ 方向：{{ selectedDirection?.name }}<br>
              ✅ 框架：{{ selectedFramework?.name }}<br>
              ✅ 结构：{{ selectedStructure?.name }}
            </a-alert>

            <a-form :model="supplement3Form" layout="vertical">
              <a-form-item label="补充方式">
                <a-radio-group v-model="supplement3Method">
                  <a-radio value="file">从知识库选择文件</a-radio>
                  <a-radio value="text">粘贴补充文本</a-radio>
                </a-radio-group>
              </a-form-item>

              <a-form-item v-if="supplement3Method === 'file'" label="选择文件">
                <a-tree-select
                  v-model="supplement3File"
                  :data="kbTreeData"
                  placeholder="选择包含案例/数据的文件..."
                  tree-checkable
                  allow-search
                />
              </a-form-item>

              <a-form-item v-if="supplement3Method === 'text'" label="补充文本">
                <a-textarea
                  v-model="supplement3Text"
                  placeholder="补充真实案例、ROI数据、效果评估指标等..."
                  :auto-size="{ minRows: 4, maxRows: 10 }"
                />
              </a-form-item>

              <a-form-item label="真实案例">
                <a-textarea v-model="supplement3Form.cases" placeholder="具体案例描述（公司/团队名称、使用前后的对比、具体数据）..." :auto-size="{ minRows: 3, maxRows: 6 }" />
              </a-form-item>
              <a-form-item label="ROI/效果数据">
                <a-input v-model="supplement3Form.roiData" placeholder="例如：节省40%会议时间、提升30%效率..." />
              </a-form-item>
              <a-form-item label="效果评估指标">
                <a-input v-model="supplement3Form.metrics" placeholder="例如：用户满意度、转化率、留存率..." />
              </a-form-item>
            </a-form>

            <a-space style="margin-top: 16px">
              <a-button type="primary" @click="submitSupplement3">确认补充，生成提纲</a-button>
              <a-button @click="skipSupplement3">跳过补充，直接生成提纲</a-button>
            </a-space>
          </a-card>
        </div>

        <!-- Step 9: 生成提纲 -->
        <div v-if="currentStep === 9" class="step-content">
          <a-card title="写作提纲">
            <div v-if="outlineResult" class="outline-result">
              <a-typography-title :heading="4" style="text-align: center">
                {{ outlineResult.title }}
              </a-typography-title>
              <a-typography-text type="secondary" style="display: block; text-align: center; margin-bottom: 16px">
                共 {{ outlineResult.total_sections }} 个段落，预计 {{ outlineResult.estimated_total_words }} 字
              </a-typography-text>

              <a-collapse :default-active-key="outlineResult.sections.map((_, i) => i)">
                <a-collapse-item v-for="(section, i) in outlineResult.sections" :key="i" :header="`${i + 1}. ${section.title}`">
                  <div class="section-detail">
                    <div v-if="section.key_points?.length">
                      <a-typography-text strong>内容要点：</a-typography-text>
                      <a-list :data="section.key_points" size="mini">
                        <template #item="{ item }">
                          <a-list-item style="padding: 4px 0">{{ item }}</a-list-item>
                        </template>
                      </a-list>
                    </div>
                    <div v-if="section.materials" style="margin-top: 8px">
                      <a-typography-text strong>素材状态：</a-typography-text>
                      <div v-if="section.materials.has?.length">
                        <a-typography-text type="success" style="font-size: 13px">
                          ✅ 已有：{{ section.materials.has.join('、') }}
                        </a-typography-text>
                      </div>
                      <div v-if="section.materials.needs?.length">
                        <a-typography-text type="warning" style="font-size: 13px">
                           需要：{{ section.materials.needs.join('、') }}
                        </a-typography-text>
                      </div>
                    </div>
                    <a-typography-text type="secondary" style="font-size: 12px; display: block; margin-top: 4px">
                      预计字数：{{ section.word_count_estimate }}
                    </a-typography-text>
                  </div>
                </a-collapse-item>
              </a-collapse>
            </div>

            <a-space style="margin-top: 16px">
              <a-button type="primary" status="success" size="large" @click="confirmOutline">
                确认提纲，开始生成内容
              </a-button>
              <a-button @click="regenerateOutline">重新生成提纲</a-button>
              <a-button @click="goBackToSupplement3">返回补充</a-button>
            </a-space>
          </a-card>
        </div>
      </a-spin>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import {
  IconSearch,
  IconExclamationCircleFill,
  IconCloseCircleFill,
  IconCheckCircleFill,
  IconRobot,
  IconScan,
  IconArrowRight,
  IconFile,
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
  listFolderFiles,
  aiAutoSupplement as apiAiAutoSupplement,
  readFolderFile,
} from '../utils/api'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const currentStep = ref(0)
const sessionId = ref('')
const mcpSummary = ref('')
const mcpFiles = ref([])
const kbTreeData = ref([])

// 完整度评估
const completenessResult = ref(null)

// 方向推荐
const directions = ref([])
const selectedDirection = ref(null)

// 关键缺失项补充弹窗
const supplementModalVisible = ref(false)
const currentSupplementItem = ref('')
const currentSupplementIndex = ref(-1)
const isEditMode = ref(false) // 是否是编辑模式（已补充过）
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

// 补充2
const supplement2Method = ref('text')
const supplement2File = ref([])
const supplement2Text = ref('')
const supplement2Form = reactive({
  painPoint: '',
  solution: '',
  pitfalls: '',
})

// 方向检测
const checkingDirection = ref(false)
const directionCheckResult = ref(null)

// 结构推荐
const structures = ref([])
const selectedStructure = ref(null)

// 补充3
const supplement3Method = ref('text')
const supplement3File = ref([])
const supplement3Text = ref('')
const supplement3Form = reactive({
  cases: '',
  roiData: '',
  metrics: '',
})

// 提纲
const outlineResult = ref(null)

onMounted(async () => {
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
    sessionId.value = res.data.data.session_id
  } catch (e) {
    Message.error('创建会话失败: ' + e.message)
    return
  }

  // 加载知识库文件树
  const settings = JSON.parse(localStorage.getItem('archgen_settings') || '{}')
  const kbPath = settings.knowledgeBasePath || '/home/admin/Desktop/AI 博主'
  try {
    const res = await listFolderFiles(kbPath)
    if (res.data.code === 0) {
      kbTreeData.value = convertToTreeData(res.data.data)
    }
  } catch (e) {
    console.error('加载知识库文件失败:', e)
  }

  // 如果 MCP 摘要已传入，自动触发完整度评估
  if (mcpSummary.value) {
    currentStep.value = 1
    loading.value = true
    try {
      const res = await evaluateCompleteness(sessionId.value, mcpSummary.value)
      completenessResult.value = res.data.data
      Message.success('完整度评估完成')
    } catch (e) {
      Message.error('评估失败: ' + e.message)
    } finally {
      loading.value = false
    }
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

async function goToCompletenessEval() {
  loading.value = true
  try {
    const res = await evaluateCompleteness(sessionId.value, mcpSummary.value)
    completenessResult.value = res.data.data
    currentStep.value = 1
    Message.success('完整度评估完成')
  } catch (e) {
    Message.error('评估失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function goToDirections() {
  loading.value = true
  try {
    const res = await analyzeDirectionsV2(sessionId.value, mcpSummary.value)
    directions.value = res.data.data
    currentStep.value = 2
    Message.success('方向推荐完成')
  } catch (e) {
    Message.error('方向推荐失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

function openSupplementModal(index, editMode = false) {
  currentSupplementIndex.value = index
  currentSupplementItem.value = completenessResult.value.missing_critical[index] || ''
  isEditMode.value = editMode
  supplementModalMethod.value = 'text'
  supplementModalFile.value = []

  // 如果是编辑模式，加载已有的补充内容
  if (editMode && supplementContents.value[index]) {
    const existing = supplementContents.value[index]
    supplementModalMethod.value = existing.method || 'text'
    supplementModalText.value = existing.content || ''
    supplementModalFile.value = existing.files || []
  } else {
    supplementModalText.value = ''
  }

  supplementModalVisible.value = true
}

// 5A/5B/5C 模式选择
function openModeModal(mode) {
  if (mode === 'manual') {
    // 手动补充：打开第一个缺失项的补充弹窗
    const firstMissingIndex = completenessResult.value.missing_critical?.findIndex((_, idx) => !isSupplemented(idx)) ?? -1
    if (firstMissingIndex >= 0) {
      openSupplementModal(firstMissingIndex)
    } else {
      Message.info('所有关键缺失项已补充完毕')
    }
  } else if (mode === 'ai-pulse') {
    // AI-Pulse 补充（P1 框架，暂时提示）
    Message.info('AI-Pulse 服务开发中，敬请期待')
  }
}

function closeSupplementModal() {
  supplementModalVisible.value = false
  supplementModalText.value = ''
  supplementModalFile.value = []
  isEditMode.value = false
  extractingFileContent.value = false
  extractedFileContent.value = false
  extractedFileCount.value = 0
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

function confirmSupplementModal() {
  if (supplementModalMethod.value === 'text' && !supplementModalText.value.trim()) {
    Message.warning('请输入补充内容')
    return
  }
  if (supplementModalMethod.value === 'file' && supplementModalFile.value.length === 0) {
    Message.warning('请选择文件')
    return
  }

  // 保存补充内容到跟踪对象
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
  const msg = isEditMode.value ? '补充内容已更新' : '补充已保存'
  Message.success(msg)
}

async function aiAutoSupplement() {
  if (!currentSupplementItem.value) return
  aiSupplementing.value = true

  try {
    const res = await apiAiAutoSupplement(
      sessionId.value,
      currentSupplementItem.value,
      mcpSummary.value,
    )
    const data = res.data.data
    // 将AI生成的内容填充到文本框
    supplementModalText.value = data.content || ''
    Message.success('AI 补充完成，请确认或编辑后点击确定')
  } catch (e) {
    Message.error('AI 补充失败: ' + e.message)
  } finally {
    aiSupplementing.value = false
  }
}

function selectDirection(d) {
  selectedDirection.value = d
  currentStep.value = 3
  Message.info(`已选择「${d.name}」，请补充相关信息`)
}

async function submitSupplement1() {
  let supplementInfo = {}
  if (supplement1Method.value === 'form') {
    supplementInfo = { ...supplement1Form }
  } else if (supplement1Method.value === 'text') {
    supplementInfo = { text: supplement1Text.value }
  } else {
    supplementInfo = { files: supplement1File.value }
  }

  loading.value = true
  try {
    await supplementStep1(sessionId.value, selectedDirection.value.name, supplementInfo)
    supplement1Result.value = supplementInfo
    currentStep.value = 4
    Message.success('第1次补充已保存')

    // 自动进入框架推荐
    await loadFrameworks()
  } catch (e) {
    Message.error('补充失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function skipSupplement1() {
  loading.value = true
  try {
    await supplementStep1(sessionId.value, selectedDirection.value.name, {})
    currentStep.value = 4
    Message.info('已跳过补充')
    await loadFrameworks()
  } catch (e) {
    Message.error('操作失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function loadFrameworks() {
  try {
    const res = await matchFrameworksV2(sessionId.value, selectedDirection.value.name, supplement1Result.value || {}, mcpSummary.value)
    frameworks.value = res.data.data
    Message.success('框架推荐完成')
  } catch (e) {
    Message.error('框架推荐失败: ' + e.message)
  }
}

function selectFramework(f) {
  selectedFramework.value = f
  currentStep.value = 5
  Message.info(`已选择「${f.name}」框架，请完善分析内容`)
}

async function submitSupplement2() {
  let supplementInfo = { ...supplement2Form }
  if (supplement2Method.value === 'text') {
    supplementInfo.text = supplement2Text.value
  } else {
    supplementInfo.files = supplement2File.value
  }

  loading.value = true
  try {
    await supplementStep2(sessionId.value, selectedFramework.value.name, supplementInfo)
    currentStep.value = 6
    Message.success('第2次补充已保存，请进行方向检测')
  } catch (e) {
    Message.error('补充失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function skipSupplement2() {
  loading.value = true
  try {
    await supplementStep2(sessionId.value, selectedFramework.value.name, {})
    currentStep.value = 6
    Message.info('已跳过补充')
  } catch (e) {
    Message.error('操作失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function runDirectionCheck() {
  checkingDirection.value = true
  try {
    const res = await checkWorkflowDirection(
      sessionId.value,
      selectedDirection.value?.name || '',
      selectedFramework.value?.name || '',
      supplement1Result.value || {},
      supplement2Form,
      mcpSummary.value,
    )
    directionCheckResult.value = res.data.data
    Message.success('方向检测完成')
  } catch (e) {
    Message.error('检测失败: ' + e.message)
  } finally {
    checkingDirection.value = false
  }
}

async function autoFixIssue(issue) {
  loading.value = true
  try {
    const res = await fixWorkflowDirection(
      sessionId.value,
      issue,
      supplement1Result.value || {},
      supplement2Form,
      mcpSummary.value,
      selectedDirection.value?.name || '',
      selectedFramework.value?.name || '',
    )
    Message.success('AI 修改完成: ' + res.data.data.fix_description)
    // 重新检测
    await runDirectionCheck()
  } catch (e) {
    Message.error('AI 修改失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

function ignoreIssue(issue) {
  issue.type = 'pass'
  issue.title = issue.title + ' (已忽略)'
  Message.info('已忽略该问题')
}

function goBackToSupplement2() {
  currentStep.value = 5
  directionCheckResult.value = null
}

async function goToStructures() {
  loading.value = true
  try {
    const res = await recommendStructures(
      sessionId.value,
      selectedDirection.value?.name || '',
      selectedFramework.value?.name || '',
      supplement1Result.value || {},
      supplement2Form,
      mcpSummary.value,
    )
    structures.value = res.data.data
    currentStep.value = 7
    Message.success('结构推荐完成')
  } catch (e) {
    Message.error('结构推荐失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

function selectStructure(s) {
  selectedStructure.value = s
  currentStep.value = 8
  Message.info(`已选择「${s.name}」结构，请补充案例/数据`)
}

async function submitSupplement3() {
  let supplementInfo = { ...supplement3Form }
  if (supplement3Method.value === 'text') {
    supplementInfo.text = supplement3Text.value
  } else {
    supplementInfo.files = supplement3File.value
  }

  loading.value = true
  try {
    await supplementStep3(sessionId.value, selectedStructure.value.name, supplementInfo)
    currentStep.value = 9
    Message.success('第3次补充已保存，正在生成提纲...')
    await loadOutline()
  } catch (e) {
    Message.error('补充失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function skipSupplement3() {
  loading.value = true
  try {
    await supplementStep3(sessionId.value, selectedStructure.value?.name || '', {})
    currentStep.value = 9
    Message.info('已跳过补充，正在生成提纲...')
    await loadOutline()
  } catch (e) {
    Message.error('操作失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function loadOutline() {
  try {
    const res = await generateWorkflowOutline(sessionId.value)
    outlineResult.value = res.data.data
    Message.success('提纲生成完成')
  } catch (e) {
    Message.error('提纲生成失败: ' + e.message)
  }
}

async function regenerateOutline() {
  loading.value = true
  try {
    await loadOutline()
  } finally {
    loading.value = false
  }
}

function goBackToSupplement3() {
  currentStep.value = 8
}

function skipToOutline() {
  currentStep.value = 9
  loadOutline()
}

function confirmOutline() {
  // 将提纲传递到内容生成页面
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
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
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

.step-content {
  min-height: 400px;
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
</style>
