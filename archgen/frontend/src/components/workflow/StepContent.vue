<template>
  <!-- Step 3: 检测 - 方向/结构一致性检测 -->
  <div v-if="currentStep === 3" class="step-content">
    <a-card title="交付审核（门卫模式）">
      <!-- pending 状态：内容为空引导 -->
      <a-alert v-if="!checkingDirection && directionCheckMeta.ready_for_next === false" type="warning" style="margin-bottom: 16px">
        <template #title>⚠️ 检测未通过 - 内容为空或素材不足</template>
        <div style="margin-bottom: 8px">
          <a-tag color="red" size="small">{{ completenessResult?.issues?.length || 0 }} 个具体问题</a-tag>
          <span v-if="Object.keys(slotCoverage || {}).length > 0" style="margin-left: 8px; font-size: 13px; color: #4e5969">
            缺失槽位：{{ Object.entries(slotCoverage).filter(([, v]) => !v).map(([k]) => k).join('、') || '未知' }}
          </span>
        </div>
        当前尚未生成分析内容，请先：
        <ol style="margin: 8px 0 0 20px; padding: 0">
          <li>返回 <strong>框架填充</strong> 页面，点击「开始框架填充」生成分析正文</li>
          <li>或直接在下方手动补充内容</li>
          <li>补充完成后点击「自动重检」或「重新检测」</li>
        </ol>
        <div style="margin-top: 12px">
          <a-button type="primary" size="small" :loading="checkingDirection" @click="runDirectionCheck">
            🔄 自动重检
          </a-button>
        </div>
      </a-alert>

      <a-alert v-else type="info" style="margin-bottom: 16px">
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
          <div v-for="(issue, idx) in blockIssues" :key="'block-'+idx" class="issue-card" style="margin-bottom: 12px">
            <a-card :bordered="true" type="danger">
              <template #title>
                <a-space>
                  <span>🔴</span>
                  <span>{{ issue.title }}</span>
                  <a-tag color="red" size="small">阻塞</a-tag>
                  <a-tag v-if="isCheckIssueFixed(directionCheckResult.indexOf(issue))" color="green" size="small">已补充</a-tag>
                </a-space>
              </template>
              <div style="font-size: 13px; line-height: 1.6">{{ issue.description }}</div>
              
              <!-- 已补充内容预览 -->
              <div v-if="isCheckIssueFixed(directionCheckResult.indexOf(issue))" style="margin-top: 8px; padding: 8px 12px; background: #f0f7ff; border-radius: 4px; border-left: 3px solid #00b42a">
                <div style="font-size: 12px; color: #4e5969; margin-bottom: 4px">💡 已补充内容：</div>
                <div style="font-size: 13px; line-height: 1.5; color: #1d2129">{{ getCheckIssueFixContent(directionCheckResult.indexOf(issue)) }}</div>
              </div>
              
              <div style="margin-top: 12px">
                <a-space>
                  <!-- pending 状态（内容为空）：返回框架填充 -->
                  <a-button 
                    v-if="issue.category === 'pending'"
                    size="small" 
                    type="primary"
                    @click="currentStep = 2"
                  >
                    ← 返回框架填充
                  </a-button>
                  <!-- 方向/框架问题：回退重选 -->
                  <a-button 
                    v-else-if="issue.category === 'direction' || issue.category === 'framework'"
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
                  <a-button size="small" status="success" :loading="aiSingleIssueLoading === directionCheckResult.indexOf(issue)" @click="aiGenerateSingleIssue(directionCheckResult.indexOf(issue))" v-if="!isCheckIssueFixed(directionCheckResult.indexOf(issue))">
                    🤖 AI 补充
                  </a-button>
                  <a-button size="small" status="success" @click="openSupplementDialog(directionCheckResult.indexOf(issue))" v-else>
                    🔄 重新补充
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
                    <a-button type="primary" size="small" :loading="editingIssueLoading === directionCheckResult.indexOf(issue)" @click="confirmSingleIssue(directionCheckResult.indexOf(issue))">
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
                  <a-tag v-if="isCheckIssueFixed(directionCheckResult.indexOf(issue))" color="green" size="small">已补充</a-tag>
                </a-space>
              </template>
              <div style="font-size: 13px; line-height: 1.6">{{ issue.description }}</div>
              
              <!-- 已补充内容预览 -->
              <div v-if="isCheckIssueFixed(directionCheckResult.indexOf(issue))" style="margin-top: 8px; padding: 8px 12px; background: #f7f9ee; border-radius: 4px; border-left: 3px solid #00b42a">
                <div style="font-size: 12px; color: #4e5969; margin-bottom: 4px">💡 已补充内容：</div>
                <div style="font-size: 13px; line-height: 1.5; color: #1d2129">{{ getCheckIssueFixContent(directionCheckResult.indexOf(issue)) }}</div>
              </div>
              
              <div style="margin-top: 12px">
                <a-space>
                  <a-button size="small" status="success" :loading="aiSingleIssueLoading === directionCheckResult.indexOf(issue)" @click="aiGenerateSingleIssue(directionCheckResult.indexOf(issue))" v-if="!isCheckIssueFixed(directionCheckResult.indexOf(issue))">
                    🤖 AI 补充
                  </a-button>
                  <a-button size="small" status="success" @click="openSupplementDialog(directionCheckResult.indexOf(issue))" v-else>
                    🔄 重新补充
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
              @click="goToOutlineFromDetection"
            >
              生成提纲 →
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
              <a-button @click="currentStep = 5">
                ← 返回提纲
              </a-button>
            </a-space>
          </div>
        </div>

        <div v-for="(para, idx) in articleResult.paragraphs" :key="idx" style="margin-bottom: 16px; padding: 16px; border-left: 3px solid #3491fa; background: #f7f8fa; border-radius: 6px">
          <h4 style="color: #1d2129; margin-bottom: 12px">
            {{ idx + 1 }}. {{ para.title }}
          </h4>
          <div style="font-size: 14px; line-height: 1.8; white-space: pre-wrap; color: #4e5969" v-html="formatArticleContent(para.content)">
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

  <!-- Step 7: 配图（Cherry 思维流：LLM 直出 HTML → 预览 → 反馈 → 迭代） -->
  <div v-if="currentStep === 7" class="step-content">
    <a-card title="生成配图">
      <!-- 已生成：HTML 预览 + 操作按钮 -->
      <template v-if="infographicHtml">
        <div style="margin-bottom: 16px; display: flex; gap: 12px; flex-wrap: wrap">
          <a-button type="primary" @click="downloadInfographicAsImage" :loading="imageGenerating">
            📥 下载为图片
          </a-button>
          <a-button @click="openInfographicInNewTab" type="outline">
            🔗 新窗口打开
          </a-button>
          <a-button @click="infographicHtml = ''; infographicFeedback = ''" type="outline" status="warning">
            🔄 重新生成
          </a-button>
          <a-button @click="currentStep = 6" type="text">
            ← 返回文章
          </a-button>
        </div>
        <!-- HTML 预览区 -->
        <div style="border: 1px solid #e5e6eb; border-radius: 8px; overflow: hidden; margin-bottom: 16px">
          <iframe
            :srcdoc="infographicHtml"
            style="width: 100%; height: 600px; border: none"
            sandbox="allow-scripts allow-same-origin"
          ></iframe>
        </div>
        <!-- 反馈输入 -->
        <a-card title="不满意？输入修改意见" size="small" style="margin-top: 16px">
          <a-textarea
            v-model="infographicFeedback"
            placeholder="例如：模块3太简单、配色太暗、标题字号加大..."
            :rows="3"
            :auto-size="{ minRows: 2, maxRows: 6 }"
            style="margin-bottom: 12px"
          />
          <a-button
            type="primary"
            :loading="infographicRevising"
            :disabled="!infographicFeedback.trim()"
            @click="handleReviseInfographic"
          >
            ✨ AI 重新生成
          </a-button>
        </a-card>
      </template>

      <!-- 生成中 -->
      <div v-else-if="infographicGenerating" style="text-align: center; padding: 60px 0">
        <a-spin :size="50" dot tip="AI 正在分析内容并生成信息图..." />
        <div style="margin-top: 16px; color: #86909c; font-size: 13px">
          正在理解框架含义，拆分模块，生成可视化配图...
        </div>
      </div>

      <!-- 初始状态 -->
      <div v-else style="text-align: center; padding: 40px 0">
        <a-empty description="尚未生成配图" />
        <div style="margin-top: 16px; padding: 16px; background: #f7f8fa; border-radius: 8px; max-width: 520px; margin-left: auto; margin-right: auto; text-align: left">
          <a-typography-text type="secondary" size="small">
            ✨ 新版配图采用 <b>Cherry 思维流</b>：AI 直接理解框架含义并生成信息图 HTML。支持多轮迭代修改——生成后可在预览区输入反馈重新生成。
          </a-typography-text>
        </div>
        <a-space style="margin-top: 24px">
          <a-button type="primary" size="large" :loading="infographicGenerating" @click="handleGenerateInfographic">
            🖼️ AI 生成配图
          </a-button>
          <a-button size="large" @click="currentStep = 6">
            ← 返回文章
          </a-button>
        </a-space>
      </div>
    </a-card>
  </div>
</template>

<script setup>
import { watch } from 'vue'
import { useWorkflowState } from '../../composables/useWorkflowState'

// 文章内容格式化：保证换行可读（与 WorkflowView.vue 保持一致）
/**
 * 格式化文章内容，按语义分组换行。
 * - LLM 已用空行分隔不同要点 → 直接转换
 * - LLM 未换行 → 每 3 个句子合并为一个可视段落
 */
function formatArticleContent(content) {
  if (!content) return ''

  // LLM 已按要求用 \n\n 分隔了不同要点，直接保留自然分段
  const hasNewlines = /\n/.test(content)
  if (hasNewlines) {
    return content.replace(/\n+/g, '<br>')
  }

  // LLM 未换行 → 按语义分组，每 3 个自然句合并为一段
  const sentences = content.split(/(?<=[。！？])/)
  const groups = []
  for (let i = 0; i < sentences.length; i += 3) {
    groups.push(sentences.slice(i, i + 3).join(''))
  }
  return groups.join('<br>')
}

const {
  // ==== Step 3: 检测 ====
  currentStep,
  selectedDirection,
  selectedFramework,
  directionCheckResult,
  directionCheckMeta,
  fixedCheckIssues,
  blockIssues,
  suggestIssues,
  hasErrors,
  checkingDirection,
  runDirectionCheck,
  completenessResult,
  slotCoverage,
  supplementConfirmed,
  goToOutlineFromDetection,
  skipSuggestionsAndContinue,
  goBackToStep3,
  openSupplementDialog,
  editingIssueIndex,
  editingIssueContent,
  editingIssueLoading,
  editSingleIssue,
  cancelEditIssue,
  confirmSingleIssue,
  aiGenerateSingleIssue,
  aiSingleIssueLoading,
  isCheckIssueFixed,
  getCheckIssueFixContent,

  // ==== Step 4: 结构推荐 ====
  structures,
  structuresLoading,
  loadOutline,
  selectStructure,
  goBackToStructures,
  getCoverageColor,

  // ==== Step 5: 提纲生成 ====
  outlineResult,
  showOutlineAlignmentReason,
  outlineOneClickLoading,
  outlineOneClickAiSupplement,
  toggleSectionAiDialog,
  aiSupplementSectionByKey,
  acceptSectionAiSuggestionByKey,
  handleSectionAiUpload,
  sectionAiDialogIndex,
  sectionAiInput,
  sectionAiLoading,
  sectionAiResult,
  sectionAiKbFiles,
  sectionAiUploadFiles,
  goToGenerateArticle,
  exportOutline,
  outlineCompletenessStatus,
  targetWordCount,
  getAlignmentTagColor,
  getCompletenessStatusColor,
  getCompletenessStatusLabel,
  getSourceTagColor,
  getSourceTagTagColor,
  getSourceTagLabel,
  getSectionNumber,
  getSectionMissingItems,

  // ==== Step 6: 文章生成 ====
  articleResult,
  articleOneClickLoading,
  articleOneClickRegenerate,
  toggleArticleAiDialog,
  aiAdjustArticleParagraph,
  acceptArticleAiSuggestion,
  handleArticleAiUpload,
  articleAiDialogIndex,
  articleAiInput,
  articleAiLoading,
  articleAiResult,
  articleAiKbFiles,
  articleAiUploadFiles,
  exportArticle,
  goToGenerateImage,
  totalWordCount,
  readingTime,

  // ==== Step 7: 配图 ====
  imageGenerating,
  generatedImageUrl,
  infographicHtml,
  infographicGenerating,
  infographicRevising,
  infographicFeedback,
  handleGenerateInfographic,
  handleReviseInfographic,
  openInfographicInNewTab,
  downloadInfographicAsImage,

  // ==== Shared ====
  kbTreeData,
  loading,
} = useWorkflowState()

// 当补充被确认后，自动触发检测
watch(supplementConfirmed, (newVal, oldVal) => {
  if (newVal === true && oldVal === false) {
    runDirectionCheck()
  }
})
</script>

<style scoped>
.step-content { width: 100%; }
.step-content :deep(.arco-card) { width: 100%; }
</style>
