<template>
  <div class="app-container">
    <!-- 主应用 -->
    <div class="main-app">
      <!-- 导航栏 -->
      <nav class="navbar">
        <div class="navbar-brand">
          <h1>📘 行为观察助手 V4.11.0</h1>
        </div>
        <div class="navbar-nav">
          <button @click="activeTab = 'chat'" :class="{ active: activeTab === 'chat' }" class="nav-btn">
            🎯 行为分析
          </button>
        </div>
      </nav>

      <!-- 内容区域 -->
      <main class="main-content">
        <!-- 行为分析 -->
        <div v-if="activeTab === 'chat'" class="chat-container">
          <div class="chat-messages" ref="messagesContainer">
            <!-- 欢迎消息 -->
            <div v-if="messages.length === 0" class="welcome-message">
              <div class="message ai">
                <div class="message-content">
                  <p>你好！我是你的行为观察伙伴 👋</p>
                  <p>我在这里倾听你的分享，帮助你理解孩子的行为。</p>
                  <p class="hint">💡 请告诉我，最近有什么关于孩子的行为让你比较在意？</p>
                </div>
              </div>
            </div>

            <!-- 对话消息 -->
            <div 
              v-for="(msg, index) in messages" 
              :key="index"
              class="message"
              :class="[msg.role, { 'is-error': msg.isError }]"
            >
              <div class="message-avatar">
                {{ msg.role === 'user' ? '👤' : (msg.isError ? '⚠️' : '💬') }}
              </div>
              <div class="message-content">
                <p v-html="formatMessage(msg.text)"></p>
              </div>
            </div>

            <!-- V4.5 洞察报告（会话完成时） -->
            <div v-if="insightReport" class="insight-report v35-report">
              <div class="report-header-section">
                <h2>📘 行为观察助手 V4.11.0</h2>
                <div class="report-meta">
                  <span><strong>场景：</strong>{{ reportData.scene || '行为观察' }}</span>
                  <span><strong>分析日期：</strong>{{ today }}</span>
                </div>
              </div>

              <!-- 第一部分：📝 场景描述 -->
              <div class="scene-section">
                <h3>📝 场景描述</h3>
                <div class="scene-content">
                  <div class="scene-item">
                    <span class="scene-label">情境：</span>
                    <span class="scene-text">{{ reportData.context || '未明确' }}</span>
                  </div>
                  <div class="scene-item">
                    <span class="scene-label">孩子的表现：</span>
                    <span class="scene-text">{{ reportData.child_behavior || '未明确' }}</span>
                  </div>
                  <div class="scene-item">
                    <span class="scene-label">周围的反应：</span>
                    <span class="scene-text">{{ reportData.others_response || '未明确' }}</span>
                  </div>
                  <div class="scene-item">
                    <span class="scene-label">孩子年龄：</span>
                    <span class="scene-text">{{ insightReport.child_age || '未明确' }}</span>
                  </div>
                </div>
              </div>

              <!-- 第二部分：🔍 行为分析 -->
              <div class="analysis-section">
                <h3>🔍 行为分析</h3>
                <div class="analysis-content">
                  <!-- 行为功能 -->
                  <div class="analysis-item">
                    <span class="analysis-label">行为功能：</span>
                    <div class="analysis-text" v-html="formatMarkdown(insightReport.functional_judgment || insightReport.expert_view)"></div>
                  </div>
                  
                  <!-- 核心能力缺口 -->
                  <div class="analysis-item" v-if="insightReport.core_capability_goal">
                    <span class="analysis-label">核心能力缺口：</span>
                    <div class="analysis-text" v-html="formatMarkdown(insightReport.core_capability_goal)"></div>
                  </div>
                  
                  <!-- 观察到的问题 -->
                  <div class="analysis-item" v-if="insightReport.core_insight">
                    <span class="analysis-label">观察到的问题：</span>
                    <div class="analysis-text" v-html="formatMarkdown(insightReport.core_insight)"></div>
                  </div>
                </div>
              </div>

              <!-- 第三部分：💡 心伴解读 -->
              <div class="heart-section">
                <h3>💡 心伴解读</h3>
                <div class="heart-content">
                  <!-- 我们觉得 -->
                  <div class="heart-item">
                    <span class="heart-label">我们觉得：</span>
                    <div class="heart-text" v-html="formatMarkdown(insightReport.parent_insight || insightReport.reflection)"></div>
                  </div>
                  
                  <!-- 优先解决的卡点 -->
                  <div class="heart-item" v-if="interventionPlan && interventionPlan.goal">
                    <span class="heart-label">优先解决的卡点：</span>
                    <div class="heart-text">{{ interventionPlan.goal }}</div>
                  </div>
                  
                  <!-- 建议 -->
                  <div class="heart-item" v-if="interventionPlan && (interventionPlan.strategy_details_gamified || interventionPlan.strategy_details)">
                    <span class="heart-label">建议：</span>
                    <div class="heart-text" v-html="formatMarkdown(interventionPlan.strategy_details_gamified || interventionPlan.strategy_details)"></div>
                  </div>
                  
                  <!-- 赋能思考 -->
                  <div class="heart-item" v-if="insightReport.empowerment_question">
                    <span class="heart-label">赋能思考：</span>
                    <div class="heart-text">{{ insightReport.empowerment_question }}</div>
                  </div>
                </div>
              </div>

              <!-- V4.10.4 新增：用户反馈区域 -->
              <div class="feedback-section">
                <h4>💬 帮助我们改进</h4>
                <p class="feedback-intro">这份分析对你有帮助吗？你的反馈会让我们变得更好。</p>
                
                <div class="rating-stars">
                  <span 
                    v-for="star in 5" 
                    :key="star"
                    class="star"
                    :class="{ active: star <= feedbackForm.rating }"
                    @click="setRating(star)"
                  >
                    {{ star <= feedbackForm.rating ? '⭐' : '☆' }}
                  </span>
                  <span class="rating-text">{{ getRatingText() }}</span>
                </div>
                
                <div class="accuracy-select">
                  <label>分析准确性：</label>
                  <select v-model="feedbackForm.accuracy">
                    <option value="">请选择</option>
                    <option value="accurate">✅ 准确</option>
                    <option value="partial">⚠️ 部分准确</option>
                    <option value="inaccurate">❌ 不准确</option>
                  </select>
                </div>
                
                <div class="feedback-textarea">
                  <label>具体反馈（选填）：</label>
                  <textarea 
                    v-model="feedbackForm.feedbackText"
                    placeholder="哪些地方分析得好？哪些地方需要改进？"
                    rows="3"
                  ></textarea>
                </div>
                
                <button 
                  @click="submitFeedback" 
                  :disabled="!feedbackForm.rating || submittingFeedback"
                  class="btn-feedback"
                >
                  {{ submittingFeedback ? '提交中...' : '提交反馈' }}
                </button>
                
                <div v-if="feedbackMessage" class="feedback-message" :class="feedbackMessageType">
                  {{ feedbackMessage }}
                </div>
              </div>
              
              <div class="report-actions">
                <button @click="startNewSession" class="btn-primary">
                  🔄 开始新的记录
                </button>
                <button @click="copyReport" class="btn-secondary">
                  📋 复制指南
                </button>
              </div>
            </div>

            <!-- 加载指示器 -->
            <div v-if="loading" class="message ai">
              <div class="message-content">
                <div class="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                <p class="loading-text">
                  🤖 AI 正在深度分析中，请耐心等待 <strong>60-90 秒</strong>...
                </p>
                <p class="loading-hint">
                  💡 提示：AI 正在进行多步分析（行为识别 → 能力评估 → 干预建议），首次分析可能需要更长时间。<br/>
                  ⏱️ 如果超过 2 分钟无响应，请刷新页面重试。
                </p>
                <!-- V4.11.1 新增：取消按钮 -->
                <button @click="cancelRequest" class="btn-cancel">
                  ⏹️ 取消分析
                </button>
              </div>
            </div>
          </div>

          <!-- 输入区域 -->
          <div class="input-area">
            <textarea
              v-model="userInput"
              placeholder="分享你的观察...（按 Enter 发送，Shift+Enter 换行）"
              :disabled="loading && !sessionCompleted"
              @keydown.enter.exact.prevent="sendMessage"
              rows="3"
            ></textarea>
            <button 
              @click="sendMessage" 
              :disabled="!userInput.trim() || loading"
              class="send-btn"
            >
              <span v-if="!loading">发送</span>
              <span v-else>...</span>
            </button>
          </div>
        </div>
      </main>

      <footer class="footer">
        <p>行为观察助手 V4.11.0 | 测试版</p>
      </footer>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'App',
  data() {
    return {
      activeTab: 'chat',
      
      // 会话相关
      sessionId: null,
      userInput: '',
      messages: [],
      loading: false,
      sessionCompleted: false,
      showReport: false,  // 控制报告显示
      insightReport: null,
      interventionPlan: null,  // V3.5 新增
      reportData: {},  // V3.5 新增
      today: new Date().toLocaleDateString('zh-CN'),
      abortController: null,  // V4.11.1 新增：请求取消控制器
      showObservationTool: false,  // 控制观察小工具展开/收起
      // V4.10.4 新增：反馈表单
      feedbackForm: {
        rating: 0,
        accuracy: '',
        feedbackText: '',
        improvementSuggestion: ''
      },
      submittingFeedback: false,
      feedbackMessage: '',
      feedbackMessageType: 'success'
    }
  },
  methods: {
    async sendMessage() {
      // V4.11.3 调试：添加日志
      console.log('[App] sendMessage 开始', { text: this.userInput?.substring(0, 50), loading: this.loading })
      
      const text = this.userInput.trim()
      if (!text || this.loading) return

      // 添加用户消息
      this.messages.push({
        role: 'user',
        text: text,
        timestamp: new Date().toISOString(),
      })

      this.userInput = ''
      this.loading = true
      this.scrollToBottom()
      
      console.log('[App] 发送请求前', { sessionId: this.sessionId, messagesCount: this.messages.length })

      try {
        // V4.11.1 优化：增加超时时间到 300 秒，并添加请求取消支持
        const controller = new AbortController()
        this.abortController = controller
        
        const response = await axios.post('/api/v4/analyze', {
          session_id: this.sessionId,
          user_input: text,
        }, {
          timeout: 300000, // 300 秒超时（V4.11.1 优化）
          signal: controller.signal,
        })

        const data = response.data
        
        console.log('[App] 收到响应', data)

        // 处理不同格式的响应
        if (data.report && data.intervention_plan) {
          // 直接返回报告的格式（会话已完成）
          console.log('[App] 收到完成报告')
          this.sessionCompleted = true
          this.insightReport = data.report || {}
          this.interventionPlan = data.intervention_plan
          this.reportData = {
            context: data.context || data.report.context || '',
            child_behavior: data.child_behavior || data.report.child_behavior || '',
            others_response: data.others_response || data.report.others_response || '',
            scene: data.context || data.report.context || '',
          }
          // 显示报告
          this.showReport = true
          // 添加成功消息
          this.messages.push({
            role: 'ai',
            text: '分析完成，已生成报告',
            timestamp: new Date().toISOString(),
          })
        } else if (data.status) {
          // 有状态的响应格式
          if (!this.sessionId) {
            this.sessionId = data.session_id
          }

          // 添加 AI 响应
          this.messages.push({
            role: 'ai',
            text: data.message || '分析中...',
            timestamp: new Date().toISOString(),
          })
          
          console.log('[App] 消息已添加', { messagesCount: this.messages.length })

          // 检查是否完成
          if (data.status === 'completed' && data.data) {
            console.log('[App] 状态：completed')
            this.sessionCompleted = true
            this.insightReport = data.data.report || {}
            // V3.5 新增：干预计划
            this.interventionPlan = data.data.intervention_plan
            this.reportData = {
              context: data.data.context || data.data.report.context || '',
              child_behavior: data.data.child_behavior || data.data.report.child_behavior || '',
              others_response: data.data.others_response || data.data.report.others_response || '',
              scene: data.data.context || data.data.report.context || '',
            }
            // V3.6 新增：确保 clinical_differential 字段可用
            if (data.data.report && data.data.report.clinical_differential) {
              this.insightReport.clinical_differential = data.data.report.clinical_differential
            }
            // 显示报告
            this.showReport = true
          } else if (data.status === 'in_progress') {
            console.log('[App] 状态：in_progress - 调用 scrollToBottom')
            // 多轮对话中，继续收集信息
            this.loading = false
            this.scrollToBottom()  // V4.11.2 修复：确保滚动到最新消息
            console.log('[App] in_progress 处理完成，messages:', this.messages.length)
            return
          }
        } else {
          // 未知格式的响应
          console.error('[App] 未知响应格式', data)
          this.messages.push({
            role: 'ai',
            text: '分析过程中出现问题，请重试',
            timestamp: new Date().toISOString(),
            isError: true,
          })
        }

        this.scrollToBottom()
        console.log('[App] 完成，调用 scrollToBottom')

      } catch (error) {
        console.error('发送失败:', error)
        
        let errorMessage = '抱歉，处理您的请求时出现了问题。'
        
        // V4.11.1 优化：更详细的错误分类
        if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
          errorMessage = '⏱️ 分析超时（超过 5 分钟）\n\n可能原因：\n1. 网络波动或服务器繁忙\n2. AI 分析复杂度较高\n\n建议：\n• 刷新页面后重试\n• 避开使用高峰（晚上 8-10 点）\n• 如问题持续，请联系管理员'
        } else if (error.code === 'ERR_CANCELED') {
          errorMessage = '⚠️ 请求已取消'
        } else if (error.response) {
          // 服务器返回了错误响应
          const status = error.response.status
          if (status === 500) {
            errorMessage = '❌ 服务器内部错误\n\n请稍后重试，或联系管理员。'
          } else if (status === 503) {
            errorMessage = '🔧 服务暂时不可用\n\n请稍后再试。'
          } else {
            errorMessage = `❌ 请求失败（状态码：${status}）\n\n请重试。`
          }
        } else if (error.request) {
          // 请求已发送但没有收到响应
          errorMessage = '📡 网络错误\n\n无法连接到服务器，请检查网络连接后重试。'
        } else {
          errorMessage += '请重试。'
        }
        
        this.messages.push({
          role: 'ai',
          text: errorMessage,
          timestamp: new Date().toISOString(),
          isError: true,  // 标记为错误消息
        })
      } finally {
        this.loading = false
        this.abortController = null
      }
    },

    // V4.11.1 新增：取消当前请求
    cancelRequest() {
      if (this.abortController) {
        this.abortController.abort()
        this.abortController = null
        this.loading = false
        this.messages.push({
          role: 'ai',
          text: '⚠️ 已取消当前分析请求。',
          timestamp: new Date().toISOString(),
        })
      }
    },

    startNewSession() {
      // V4.11.1 优化：清理未完成的请求
      if (this.abortController) {
        this.abortController.abort()
        this.abortController = null
      }
      this.sessionId = null
      this.messages = []
      this.sessionCompleted = false
      this.userInput = ''
      this.insightReport = null
    },

    copyReport() {
      if (!this.insightReport) return

      const plan = this.interventionPlan || {}
      
      const report = `
📘 行为观察助手
========================

📋 摘要
${this.insightReport.summary || this.insightReport.observation}

一、我们共同的发现：理解行为
- 情境：${this.reportData.context || ''}
- 孩子的表现：${this.reportData.child_behavior || ''}
- 周围的反应：${this.reportData.others_response || ''}

二、专业视角：可能性分析与决策
${this.insightReport.expert_view}

三、我们的第一步计划：${plan.phase_name || '支持计划'}
🎯 目标：${plan.goal || ''}
🎮 具体怎么玩：${plan.strategy_details_gamified || plan.strategy_details || ''}
✅ 成功标准：${plan.success_criteria || ''}
📝 观察小工具：${plan.parent_observation_task || ''}

四、展望与共勉
后续方向：${plan.next_phase_preview || this.insightReport.reflection}
赋能思考：${this.insightReport.empowerment_question || ''}
      `.trim()

      navigator.clipboard.writeText(report).then(() => {
        alert('指南已复制到剪贴板！')
      }).catch(err => {
        console.error('复制失败:', err)
        alert('复制失败，请手动选择复制')
      })
    },

    // ========== V4.10.4 新增：反馈相关方法 ==========
    
    setRating(star) {
      this.feedbackForm.rating = star
    },
    
    getRatingText() {
      const texts = ['', '非常差', '差', '一般', '好', '非常好']
      return texts[this.feedbackForm.rating] || ''
    },
    
    async submitFeedback() {
      if (!this.feedbackForm.rating || !this.sessionId) {
        this.feedbackMessage = '请先评分'
        this.feedbackMessageType = 'error'
        return
      }
      
      this.submittingFeedback = true
      
      try {
        const response = await axios.post('/api/v4/feedback', {
          session_id: this.sessionId,
          rating: this.feedbackForm.rating,
          accuracy: this.feedbackForm.accuracy || 'partial',
          feedback_text: this.feedbackForm.feedbackText,
          improvement_suggestion: this.feedbackForm.improvementSuggestion
        }, {
          timeout: 10000, // 10 秒超时
        })
        
        if (response.data.status === 'success') {
          this.feedbackMessage = '✅ 感谢你的反馈！'
          this.feedbackMessageType = 'success'
          // 清空表单
          this.feedbackForm = {
            rating: 0,
            accuracy: '',
            feedbackText: '',
            improvementSuggestion: ''
          }
        }
      } catch (error) {
        console.error('提交反馈失败:', error)
        this.feedbackMessage = '❌ 提交失败，请稍后重试'
        this.feedbackMessageType = 'error'
      } finally {
        this.submittingFeedback = false
        
        // 3 秒后清除消息
        setTimeout(() => {
          this.feedbackMessage = ''
        }, 3000)
      }
    },

    formatMessage(text) {
      if (!text) return ''
      // V3.6 修复：使用全局过滤器处理特殊字符
      return this.$escape(text).replace(/\n/g, '<br>')
    },

    // V4.10.3 新增：Markdown 格式化（支持加粗、列表）
    formatMarkdown(text) {
      if (!text) return ''
      
      // 1. 先处理换行：保留所有换行
      let html = text.replace(/\n/g, '<LINEBREAK>')
      
      // 2. 移除所有 ** 符号
      html = html.replace(/\*\*/g, '')
      
      // 3. 有序列表和无序列表处理
      const lines = html.split('<LINEBREAK>')
      const processedLines = []
      let inOrderedList = false
      let inUnorderedList = false
      
      // V4.10.3 修复：主标题关键词（不渲染为列表，保持为普通段落）
      const mainTitles = ['多角度理解', '核心分析', '能力评估']
      
      for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim()
        
        // 匹配有序列表：1. 2. 3. 或数字 + 点
        const orderedMatch = line.match(/^(\d+)\.\s*(.+)/)
        
        // 匹配无序列表：• 或 - 或 *
        const unorderedMatch = line.match(/^[•\-\*]\s*(.+)/)
        
        // V4.10.3 修复：检查是否是主标题（包含关键词）
        const isMainTitle = mainTitles.some(title => line.includes(title))
        
        if (orderedMatch && !isMainTitle) {
          // 关闭无序列表（如果正在其中）
          if (inUnorderedList) {
            processedLines.push('</ul>')
            inUnorderedList = false
          }
          // 开启或继续有序列表
          if (!inOrderedList) {
            processedLines.push('<ol>')
            inOrderedList = true
          }
          // 转义列表内容
          let listContent = this.$escape(orderedMatch[2])
          processedLines.push(`<li>${listContent}</li>`)
        } else if (unorderedMatch && !isMainTitle) {
          // 关闭有序列表（如果正在其中）
          if (inOrderedList) {
            processedLines.push('</ol>')
            inOrderedList = false
          }
          // 开启或继续无序列表
          if (!inUnorderedList) {
            processedLines.push('<ul>')
            inUnorderedList = true
          }
          // 转义列表内容
          let listContent = this.$escape(unorderedMatch[1])
          processedLines.push(`<li>${listContent}</li>`)
        } else {
          // 普通段落（包括主标题）：关闭所有列表
          if (inOrderedList) {
            processedLines.push('</ol>')
            inOrderedList = false
          }
          if (inUnorderedList) {
            processedLines.push('</ul>')
            inUnorderedList = false
          }
          // 普通段落：有内容则显示，空行则跳过
          if (line && line !== '<br>') {
            // 转义普通文本
            let paragraph = this.$escape(line)
            // 处理核心能力目标等标签，使用更语义化的标签
            paragraph = paragraph.replace(/&lt;strong&gt;核心能力目标：&lt;\/strong&gt;/g, '<h4>核心能力目标：</h4>')
            paragraph = paragraph.replace(/&lt;strong&gt;赋能思考：&lt;\/strong&gt;/g, '<h4>赋能思考：</h4>')
            processedLines.push(paragraph + '<br>')
          }
        }
      }
      
      // 关闭未结束的列表
      if (inOrderedList) {
        processedLines.push('</ol>')
      }
      if (inUnorderedList) {
        processedLines.push('</ul>')
      }
      
      // 直接返回处理后的 HTML
      return processedLines.join('')
    },
    
    // V4.11.4 新增：临床鉴别思考格式化（移除鉴别与排除，分段显示）
    formatClinicalDifferential(text) {
      if (!text) return ''
      
      // 1. 移除"鉴别与排除"部分
      let cleanedText = text.replace(/1\.\s*\*\*鉴别与排除\*\*[\s\S]*?(?=2\.|$)/, '')
      
      // 2. 移除所有 ** 标记
      cleanedText = cleanedText.replace(/\*\*/g, '')
      
      // 3. 重新编号：将 2. 改为 1.，3. 改为 2.
      cleanedText = cleanedText.replace(/^2\.\s*/gm, '1. ')
      cleanedText = cleanedText.replace(/^3\.\s*/gm, '2. ')
      
      // 4. 处理换行
      let html = cleanedText.replace(/\n/g, '<LINEBREAK>')
      
      // 5. 分段处理（1.、2. 等）
      const lines = html.split('<LINEBREAK>')
      const processedLines = []
      
      for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim()
        
        // 匹配分段：1. 2. 等
        const sectionMatch = line.match(/^(\d+)\.\s*(.+)/)
        
        if (sectionMatch) {
          // 分段标题
          processedLines.push(`<h4>${sectionMatch[1]}. ${sectionMatch[2]}</h4>`)
        } else if (line && line !== '<br>') {
          // 普通段落
          processedLines.push(line + '<br>')
        }
      }
      
      return processedLines.join('')
    },

    scrollToBottom() {
      this.$nextTick(() => {
        const container = this.$refs.messagesContainer
        if (container) {
          container.scrollTop = container.scrollHeight
        }
      })
    },
    
    getConfidenceClass() {
      if (!this.insightReport) return 'medium';
      return this.insightReport.confidence_level || 'medium';
    },
    
    // 切换观察小工具展开/收起
    toggleObservationTool() {
      this.showObservationTool = !this.showObservationTool
    },
  },
}
</script>

<style>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
}

.app-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: clamp(8px, 2vw, 20px);
  height: 100vh;
  display: flex;
  flex-direction: column;
}

/* 登录容器 */
.login-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 主应用 */
.main-app {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.2);
  overflow: hidden;
}

/* 导航栏 */
.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.navbar-brand h1 {
  font-size: clamp(1rem, 2.5vw, 1.5rem);
  margin: 0;
}

.navbar-nav {
  display: flex;
  gap: 10px;
}

.nav-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.nav-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: translateY(-2px);
}

.nav-btn.active {
  background: white;
  color: #667eea;
  font-weight: 500;
}

.nav-btn.logout {
  background: rgba(255, 77, 77, 0.2);
}

.nav-btn.logout:hover {
  background: rgba(255, 77, 77, 0.3);
}

/* 内容区域 */
.main-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

/* 儿童管理和历史记录容器 */
.children-container,
.history-container {
  height: 100%;
}

/* 响应式设计 */
@media (max-width: 767px) {
  /* 手机：单列布局 */
  .app-container {
    max-width: 100%;
    padding: 8px;
  }
  
  .navbar {
    flex-direction: column;
    gap: 10px;
    padding: 10px;
  }
  
  .navbar-nav {
    flex-wrap: wrap;
    justify-content: center;
  }
  
  .nav-btn {
    font-size: 12px;
    padding: 6px 12px;
  }
  
  .main-content {
    padding: 10px;
  }
  
  .chat-messages {
    padding: 10px;
  }
  
  .message-content {
    max-width: 90%;
    padding: 10px 12px;
    font-size: 0.85rem;
  }
  
  .input-area {
    padding: 10px;
  }
  
  textarea {
    padding: 10px 12px;
    font-size: 0.85rem;
  }
  
  .send-btn {
    padding: 10px 15px;
    font-size: 0.85rem;
  }
  
  .insight-report {
    margin: 10px 0;
    padding: 15px;
  }
  
  .capability-cards {
    flex-direction: column;
  }
  
  .capability-card {
    min-width: 100%;
  }
  
  /* 移动端报告样式优化 */
  .v35-report {
    margin: 10px 0;
    padding: 15px;
  }
  
  .v35-report .report-header-section h2 {
    font-size: 1.2em;
  }
  
  .v35-report .report-meta {
    flex-direction: column;
    gap: 8px;
  }
  
  .v35-report .summary {
    padding: 15px;
  }
  
  .v35-report .detail-list {
    padding: 12px;
  }
  
  .v35-report .hypothesis-box,
  .v35-report .clinical-differential,
  .v35-report .intervention-plan {
    padding: 15px;
  }
  
  .v35-report .plan-item {
    padding: 12px;
  }
  
  /* 确保列表在移动端正确显示 */
  .v35-report ol,
  .v35-report ul {
    padding-left: 1.5em;
  }
  
  /* 长文本自动换行 */
  .v35-report {
    word-wrap: break-word;
    overflow-wrap: break-word;
  }
  
  /* 按钮适配 */
  .report-actions {
    flex-direction: column;
    gap: 8px;
  }
  
  .btn-primary,
  .btn-secondary {
    width: 100%;
    padding: 10px 20px;
  }
}

@media (min-width: 768px) and (max-width: 1023px) {
  /* 平板：适当留白 */
  .app-container {
    max-width: 90%;
    padding: 15px;
  }
  
  .main-content {
    padding: 15px;
  }
  
  .chat-messages {
    padding: 15px;
  }
  
  .insight-report {
    margin: 15px 0;
    padding: 20px;
  }
  
  /* 平板布局优化 */
  .v35-report .report-meta {
    flex-wrap: wrap;
  }
  
  /* 强制单列布局 */
  .v35-report .intervention-plan {
    display: block !important;
  }
  
  .v35-report .plan-details {
    display: block !important;
    flex-direction: column !important;
  }
  
  .v35-report .plan-item {
    width: 100% !important;
    margin-bottom: 20px;
    display: block !important;
  }
  
  .v35-report .plan-item.observation-tool {
    width: 100% !important;
  }
}

@media (min-width: 1024px) {
  /* 桌面：居中布局，最大宽度限制 */
  .app-container {
    max-width: 1000px;
    padding: 20px;
  }
  
  .main-content {
    padding: 20px;
  }
  
  .chat-messages {
    padding: 20px;
  }
  
  .insight-report {
    margin: 20px 0;
    padding: 25px;
  }
  
  /* 强制单列布局 */
  .v35-report .intervention-plan {
    display: block !important;
  }
  
  .v35-report .plan-details {
    display: block !important;
    flex-direction: column !important;
  }
  
  .v35-report .plan-item {
    width: 100% !important;
    margin-bottom: 25px;
    display: block !important;
  }
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: clamp(10px, 2vw, 20px);
}

.welcome-message {
  text-align: center;
  padding: clamp(15px, 3vw, 40px) clamp(15px, 3vw, 20px);
}

.message {
  display: flex;
  margin-bottom: clamp(12px, 2.5vw, 20px);
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  font-size: clamp(1.1rem, 2.5vw, 1.5rem);
  margin: 0 clamp(6px, 1.5vw, 10px);
}

.message-content {
  max-width: 85%;
  padding: clamp(8px, 2vw, 15px) clamp(12px, 2.5vw, 20px);
  border-radius: 10px;
  background: #f0f0f0;
  line-height: 1.5;
  font-size: clamp(0.85rem, 2.2vw, 1rem);
}

.message.user .message-content {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.message.ai .message-content {
  background: #f8f9fa;
  border: 1px solid #e0e0e0;
}

/* V4.11.1 新增：错误消息样式 */
.message.ai.is-error .message-content {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-left: 4px solid #ef4444;
}

.hint {
  font-size: 0.9em;
  color: #666;
  margin-top: 10px;
  padding: 10px;
  background: #fff3cd;
  border-radius: 6px;
}

/* 洞察报告 */
.insight-report {
  margin: clamp(10px, 2vw, 20px);
  background: white;
  border-radius: 10px;
  padding: clamp(12px, 3vw, 25px);
  border: 1.5px solid #667eea;
  box-shadow: 0 3px 15px rgba(102, 126, 234, 0.15);
}

.report-header {
  display: flex;
  align-items: center;
  gap: clamp(6px, 1.5vw, 10px);
  margin-bottom: clamp(10px, 2vw, 20px);
  padding-bottom: clamp(8px, 2vw, 15px);
  border-bottom: 1.5px solid #667eea;
}

.report-header .header-icon {
  font-size: clamp(1.2em, 3vw, 1.8em);
}

.report-header h3 {
  color: #667eea;
  font-size: clamp(1em, 2.5vw, 1.4em);
  margin: 0;
}

.report-content {
  display: flex;
  flex-direction: column;
  gap: clamp(10px, 2vw, 20px);
}

.report-section {
  background: #f8f9fa;
  border-radius: 6px;
  padding: clamp(8px, 2vw, 15px) clamp(10px, 2.5vw, 20px);
}

.report-section h4 {
  color: #333;
  font-size: clamp(0.85em, 2vw, 1em);
  margin-bottom: clamp(6px, 1.5vw, 10px);
}

/* V3.1 新增：专家拆解样式 */
.report-section.expert-breakdown {
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  border: 2px solid #2196f3;
  border-radius: 8px;
  padding: 18px 22px;
}

.expert-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.expert-header .expert-icon {
  font-size: 1.3em;
}

.expert-header h4 {
  color: #1565c0;
  font-size: 1.1em;
  margin: 0;
  font-weight: 600;
}

.report-section.expert-breakdown p {
  color: #0d47a1;
  line-height: 1.7;
  font-size: 0.95em;
}

/* V3.3 核心洞察样式 */
.report-section.core-insight {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 10px;
  padding: 20px 25px;
}

.insight-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.insight-header .insight-icon {
  font-size: 1.5em;
}

.insight-header h4 {
  color: rgba(255,255,255,0.95);
  font-size: 1.1em;
  margin: 0;
  font-weight: 600;
}

.report-section.core-insight .insight-text {
  font-size: 1.08em;
  line-height: 1.8;
  font-weight: 400;
}

/* V3.3 专业视角样式 */
.report-section.expert-view {
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  border: 2px solid #2196f3;
  border-radius: 10px;
  padding: 20px 25px;
}

.report-section.suggestion {
  background: #e8f5e9;
  border-left: 4px solid #4caf50;
}

.report-section.suggestion h4 {
  color: #2e7d32;
}

.report-section.reflection {
  background: #fff3e0;
  border-left: 4px solid #ff9800;
}

.report-section.reflection h4 {
  color: #e65100;
}

.report-actions {
  display: flex;
  gap: 10px;
  margin-top: 25px;
  padding-top: 20px;
  border-top: 1px solid #e0e0e0;
}

.btn-primary, .btn-secondary {
  padding: 12px 25px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1em;
  transition: all 0.2s;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  flex: 1;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
}

.btn-secondary {
  background: #f0f0f0;
  color: #333;
}

.btn-secondary:hover {
  background: #e0e0e0;
}

/* 输入区域 */
.input-area {
  display: flex;
  gap: clamp(6px, 1.5vw, 10px);
  padding: clamp(10px, 2vw, 20px);
  border-top: 1px solid #e0e0e0;
  background: #f8f9fa;
}

textarea {
  flex: 1;
  padding: clamp(8px, 2vw, 12px) clamp(10px, 2vw, 15px);
  border: 1.5px solid #e0e0e0;
  border-radius: 8px;
  font-size: clamp(0.85rem, 2vw, 1em);
  resize: none;
  font-family: inherit;
  transition: border-color 0.3s;
}

textarea:focus {
  outline: none;
  border-color: #667eea;
}

textarea:disabled {
  background: #f0f0f0;
  cursor: not-allowed;
}

.send-btn {
  padding: clamp(8px, 2vw, 12px) clamp(15px, 3vw, 25px);
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: clamp(0.85rem, 2vw, 1em);
  cursor: pointer;
  transition: all 0.2s;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 打字指示器 */
.typing-indicator {
  display: flex;
  gap: 5px;
  padding: 10px 0;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #999;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

/* 加载提示文本 */
.loading-text {
  margin: 10px 0 5px 0;
  color: #667eea;
  font-size: 0.95em;
  line-height: 1.5;
}

.loading-text strong {
  color: #f59e0b;
  font-weight: 600;
}

.loading-hint {
  margin: 5px 0 0 0;
  color: #999;
  font-size: 0.85em;
  line-height: 1.4;
  font-style: italic;
}

/* V4.11.1 新增：取消按钮样式 */
.btn-cancel {
  margin-top: 12px;
  padding: 8px 16px;
  background: #f0f0f0;
  border: 1px solid #ddd;
  border-radius: 6px;
  color: #666;
  font-size: 0.9em;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel:hover {
  background: #e0e0e0;
  border-color: #ccc;
}

.footer {
  text-align: center;
  color: rgba(255,255,255,0.8);
  margin-top: 20px;
  padding: 10px;
  font-size: 0.85em;
}

/* V3.5 新版报告样式 */
.v35-report {
  background: #fff;
  border: 2px solid #667eea;
  border-radius: 12px;
  padding: 25px;
  margin: 20px;
}

.v35-report .report-header-section {
  border-bottom: 3px solid #667eea;
  padding-bottom: 15px;
  margin-bottom: 25px;
}

.v35-report .report-header-section h2 {
  color: #667eea;
  font-size: 1.5em;
  margin-bottom: 10px;
}

.v35-report .report-meta {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  font-size: 0.9em;
  color: #666;
}

.v35-report .report-meta span {
  background: #f0f0f0;
  padding: 5px 12px;
  border-radius: 15px;
}

.v35-report .summary {
  background: linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%);
  color: white;
  padding: 25px;
  border-radius: 12px;
  margin-bottom: 30px;
  box-shadow: 0 6px 20px rgba(90, 103, 216, 0.4);
  border: none;
}

.v35-report .summary h3 {
  margin-bottom: 15px;
  font-size: 1.4em;
  font-weight: 600;
  text-align: center;
  text-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.v35-report .summary-text {
  font-size: 1.15em;
  line-height: 1.8;
  font-weight: 500;
  text-align: center;
  padding: 0 20px;
}

.v35-report .detail-list {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
}

.v35-report .detail-item {
  margin-bottom: 12px;
  line-height: 1.6;
}

.v35-report .detail-item:last-child {
  margin-bottom: 0;
}

.v35-report .detail-item.highlight {
  background: #fff3cd;
  padding: 12px;
  border-radius: 6px;
  border-left: 4px solid #ffc107;
}

.v35-report .hypothesis-box {
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  border: 2px solid #2196f3;
  padding: 18px;
  border-radius: 10px;
}

.v35-report .hypothesis-box p {
  margin-bottom: 12px;
  line-height: 1.7;
}

.v35-report .hypothesis-box p:last-child {
  margin-bottom: 0;
}

/* V6.0 行为功能判断新样式 */
.v35-report .functional-judgment-content {
  display: block;
}

.v35-report .main-judgment {
  background: white;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 15px;
  border-left: 4px solid #2196f3;
}

.v35-report .judgment-label {
  font-weight: 600;
  color: #1976d2;
  margin-right: 8px;
}

.v35-report .judgment-text {
  font-weight: 500;
  color: #0d47a1;
  font-size: 1.1em;
}

.v35-report .capability-goals {
  background: rgba(255, 255, 255, 0.6);
  padding: 15px;
  border-radius: 8px;
  border-left: 4px solid #4caf50;
}

.v35-report .capability-goals h4 {
  margin-bottom: 10px;
  color: #2e7d32;
  font-size: 1em;
  font-weight: 600;
}

.v35-report .capability-goals .goal-list {
  color: #1b5e20;
  line-height: 1.7;
  font-weight: 500;
}

/* V3.5 干预计划样式 */
.v35-report .intervention-plan {
  background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
  border: 2px solid #4caf50;
  padding: 20px;
  border-radius: 10px;
  margin-top: 25px;
}

.v35-report .intervention-plan h3 {
  color: #2e7d32;
  margin-bottom: 15px;
}

.v35-report .plan-details {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.v35-report .plan-item {
  background: white;
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.v35-report .plan-item h4 {
  color: #4caf50;
  margin-bottom: 8px;
  font-size: 1em;
}

.v35-report .plan-item p {
  line-height: 1.7;
  color: #333;
}

.v35-report .plan-item .gamified-strategy {
  background: #fff9e6;
  padding: 12px;
  border-radius: 6px;
  border-left: 3px solid #ffc107;
}

.v35-report .plan-item .success-criteria {
  font-weight: 600;
  color: #2e7d32;
}

.v35-report .future-section {
  background: #fff3e0;
  padding: 15px;
  border-radius: 8px;
  border-left: 4px solid #ff9800;
}

.v35-report .future-section p {
  margin-bottom: 12px;
  line-height: 1.7;
}

.v35-report .future-section p:last-child {
  margin-bottom: 0;
}

/* V3.5 新增：小目标样式 */
.v35-report .plan-item.mini-goal {
  background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
  border: 2px solid #ff9800;
}

.v35-report .plan-item.mini-goal h4 {
  color: #e65100;
}

.v35-report .mini-goal-text {
  font-size: 1.05em;
  font-weight: 600;
  color: #bf360c;
}

/* V3.5 新增：观察记录小工具样式 */
.v35-report .plan-item.observation-tool {
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  border: 2px solid #2196f3;
}

.v35-report .plan-item.observation-tool h4 {
  color: #0d47a1;
}

.v35-report .plan-item.observation-tool p {
  background: white;
  padding: 10px;
  border-radius: 6px;
}

/* V3.6 新增：临床鉴别思考样式 */
.v35-report .clinical-differential {
  background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
  border: 2px solid #9c27b0;
  padding: 20px;
  border-radius: 10px;
  margin-bottom: 25px;
}

.v35-report .clinical-differential h3 {
  color: #7b1fa2;
  margin-bottom: 12px;
  font-size: 1.2em;
}

.v35-report .clinical-differential p {
  color: #4a148c;
  line-height: 1.8;
  font-size: 0.98em;
}

/* V4.1 四步结构样式 */
.v35-report .intervention-plan-final {
  background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
  border: 2px solid #4caf50;
  padding: 20px;
  border-radius: 10px;
  margin-top: 25px;
}

.v35-report .intervention-plan-v37 h3 {
  color: #2e7d32;
  margin-bottom: 20px;
  font-size: 1.3em;
}

.v35-report .four-step-container {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.v35-report .step-item {
  background: white;
  padding: 18px;
  border-radius: 8px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.v35-report .step-item h4 {
  margin-bottom: 10px;
  font-size: 1.05em;
}

.v35-report .step-core {
  border-left: 4px solid #2196f3;
}

.v35-report .step-core h4 {
  color: #1976d2;
}

.v35-report .step-plan {
  border-left: 4px solid #ff9800;
}

.v35-report .step-plan h4 {
  color: #f57c00;
}

.v35-report .step-success {
  border-left: 4px solid #4caf50;
}

.v35-report .step-success h4 {
  color: #388e3c;
}

.v35-report .step-success .success-picture {
  font-weight: 600;
  color: #2e7d32;
  background: #f1f8e9;
  padding: 12px;
  border-radius: 6px;
}

.v35-report .step-first {
  border-left: 4px solid #9c27b0;
}

.v35-report .step-first h4 {
  color: #7b1fa2;
}

/* V4.1 成功时刻记录卡 */
.v35-report .observation-tool-final {
  background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
  border: 2px solid #ff9800;
  padding: 18px;
  border-radius: 8px;
  margin-top: 20px;
}

.v35-report .observation-tool-v37 h4 {
  color: #e65100;
  margin-bottom: 10px;
  font-size: 1.05em;
}

.v35-report .observation-tool-v37 p {
  color: #bf360c;
  line-height: 1.7;
  background: white;
  padding: 12px;
  border-radius: 6px;
}

/* V4.6.0 新增样式 */
.clinical-text {
  line-height: 1.8;
  color: #475569;
  margin-bottom: 16px;
  white-space: normal; /* 允许换行 */
}

/* V4.10.3 新增：临床文本加粗 */
.clinical-text strong {
  font-weight: 600;
  color: #1e293b;
}

/* V4.10.3 新增：临床文本列表样式 */
.clinical-text ol {
  margin: 12px 0;
  padding-left: 24px;
}

.clinical-text ul {
  margin: 12px 0;
  padding-left: 24px;
  list-style-type: disc; /* 实心圆点 */
}

.clinical-text li {
  margin: 8px 0;
  line-height: 1.7;
}

/* 子列表层级区分 */
.clinical-text li > ol {
  margin-top: 4px;
  padding-left: 20px;
  list-style-type: lower-alpha; /* a, b, c... */
}

.clinical-text li > ul {
  margin-top: 4px;
  padding-left: 20px;
  list-style-type: circle; /* 空心圆 */
}

/* 报告内容列表样式 */
.v35-report ol,
.v35-report ul {
  margin: 1.2em 0;
  padding-left: 2em;
}

.v35-report li {
  padding-bottom: 8px;
  border-bottom: 2px solid rgba(102, 126, 234, 0.3);
}

.v35-report h4 {
  margin-bottom: 12px;
  font-size: 1.1em;
  font-weight: 500;
  color: #444;
}

/* 段落间距 */
.v35-report .plan-item p,
.v35-report .plan-item div {
  margin-bottom: 1.2em;
  line-height: 1.7;
}

/* 视觉层次增强 */
.v35-report .summary {
  background: linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%);
  color: white;
  border: none;
  box-shadow: 0 4px 12px rgba(90, 103, 216, 0.3);
}

.v35-report .hypothesis-box {
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  border: 2px solid #1976d2;
  box-shadow: 0 4px 12px rgba(25, 118, 210, 0.2);
}

.v35-report .hypothesis-box p {
  color: #0d47a1;
  font-weight: 500;
}

/* 置信度显示样式 */
.confidence-indicator {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 13px;
  margin-bottom: 12px;
  font-weight: 500;
}

.confidence-indicator.high {
  background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
  color: #155724;
  border: 1px solid #c3e6cb;
}

.confidence-indicator.medium {
  background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
  color: #856404;
  border: 1px solid #ffeaa7;
}

.confidence-indicator.low {
  background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.confidence-reason {
  display: block;
  margin-top: 5px;
  font-size: 0.85em;
  font-style: italic;
}

.confidence-indicator strong {
  font-weight: 600;
}

.v35-report .clinical-differential {
  background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
  border: 2px solid #7b1fa2;
  box-shadow: 0 4px 12px rgba(123, 31, 162, 0.2);
}

.v35-report .clinical-differential p {
  color: #4a148c;
  font-weight: 500;
}

.v35-report .intervention-plan {
  background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
  border: 2px solid #388e3c;
  box-shadow: 0 4px 12px rgba(56, 142, 60, 0.2);
}

.v35-report .intervention-plan p {
  color: #1b5e20;
  font-weight: 500;
}

.v35-report .future-section {
  background: #fff3e0;
  border-left: 4px solid #f57c00;
  box-shadow: 0 4px 12px rgba(245, 124, 0, 0.2);
}

.v35-report .future-section p {
  color: #e65100;
  font-weight: 500;
}

/* 详细信息列表样式 */
.v35-report .detail-list {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.v35-report .detail-item {
  margin-bottom: 12px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(0,0,0,0.05);
}

.v35-report .detail-item:last-child {
  margin-bottom: 0;
  border-bottom: none;
}

/* 计划项目样式 */
.v35-report .plan-item {
  background: white;
  padding: 20px;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  margin-bottom: 20px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.v35-report .plan-item:hover {
  box-shadow: 0 6px 20px rgba(0,0,0,0.15);
  transform: translateY(-3px);
}

.v35-report .plan-item h4 {
  margin-bottom: 15px;
  font-size: 1.1em;
  font-weight: 600;
  color: #333;
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 目标项样式 */
.v35-report .plan-item.goal-item {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
}

.v35-report .plan-item.goal-item h4 {
  color: white;
}

.v35-report .plan-item.goal-item .goal-content p {
  font-size: 1.05em;
  line-height: 1.7;
  font-weight: 500;
}

/* 策略项样式 */
.v35-report .plan-item.strategy-item {
  border-left: 4px solid #ffc107;
}

.v35-report .plan-item .gamified-strategy {
  background: #fff9e6;
  padding: 18px;
  border-radius: 8px;
  border-left: 4px solid #ffc107;
  margin-top: 12px;
}

.v35-report .plan-item .strategy-placeholder {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  border: 2px dashed #dee2e6;
  text-align: center;
}

.v35-report .plan-item .placeholder-hint {
  font-size: 0.9em;
  color: #6c757d;
  margin-top: 8px;
}

/* 成功标准样式 */
.v35-report .plan-item.success-item {
  border-left: 4px solid #4caf50;
}

.v35-report .plan-item .success-criteria {
  font-weight: 600;
  color: #2e7d32;
  background: #f1f8e9;
  padding: 15px;
  border-radius: 8px;
  margin-top: 12px;
}

.v35-report .plan-item .placeholder-text {
  color: #6c757d;
  font-style: italic;
}

/* 观察小工具样式 */
.v35-report .plan-item.observation-tool {
  border-left: 4px solid #2196f3;
  cursor: pointer;
  transition: all 0.3s ease;
}

.v35-report .plan-item.observation-tool:hover {
  background: #f8f9fa;
}

.v35-report .plan-item.observation-tool .tool-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.v35-report .plan-item.observation-tool .tool-toggle {
  font-size: 0.8em;
  color: #6c757d;
  transition: transform 0.3s ease;
}

.v35-report .plan-item.observation-tool .tool-content {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #e9ecef;
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.v35-report .plan-item.observation-tool p {
  background: white;
  padding: 15px;
  border-radius: 8px;
  border: 1px solid #e3f2fd;
  line-height: 1.7;
}

/* 临床鉴别思考样式增强 */
.v35-report .clinical-differential {
  background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
  border: 2px solid #9c27b0;
  padding: 25px;
  border-radius: 12px;
  margin-bottom: 30px;
  box-shadow: 0 6px 20px rgba(156, 39, 176, 0.2);
}

.v35-report .clinical-differential h3 {
  color: #7b1fa2;
  margin-bottom: 15px;
  font-size: 1.3em;
  font-weight: 600;
}

.v35-report .clinical-differential p {
  color: #4a148c;
  line-height: 1.8;
  font-size: 1em;
  font-weight: 500;
}

/* 反思与展望样式增强 */
.v35-report .future-section {
  background: #fff3e0;
  border-left: 4px solid #ff9800;
  padding: 20px;
  border-radius: 10px;
  margin-top: 30px;
  box-shadow: 0 4px 15px rgba(255, 152, 0, 0.2);
}

.v35-report .future-section h3 {
  color: #e65100;
  margin-bottom: 15px;
  font-size: 1.2em;
  font-weight: 600;
}

.v35-report .future-section p {
  color: #e65100;
  line-height: 1.7;
  font-weight: 500;
  margin-bottom: 15px;
}

.v35-report .future-section p:last-child {
  margin-bottom: 0;
}

/* 详细信息列表样式增强 */
.v35-report .detail-list {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  padding: 20px;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  margin-bottom: 30px;
}

.v35-report .detail-item {
  margin-bottom: 15px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(0,0,0,0.05);
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.v35-report .detail-item:last-child {
  margin-bottom: 0;
  border-bottom: none;
}

.v35-report .detail-item strong {
  font-weight: 600;
  color: #333;
  min-width: 80px;
}

/* 响应式布局优化 - 全部单列 */
@media (min-width: 768px) {
  /* 平板：强制单列布局 */
  .v35-report .intervention-plan {
    display: block !important;
  }
  
  .v35-report .plan-details {
    display: block !important;
    flex-direction: column !important;
  }
  
  .v35-report .plan-item {
    width: 100% !important;
    margin-bottom: 20px;
    display: block !important;
  }
  
  .v35-report .plan-item.observation-tool {
    width: 100% !important;
  }
}

@media (min-width: 1024px) {
  /* 桌面：强制单列布局 */
  .v35-report .intervention-plan {
    display: block !important;
  }
  
  .v35-report .plan-details {
    display: block !important;
    flex-direction: column !important;
  }
  
  .v35-report .plan-item {
    width: 100% !important;
    margin-bottom: 25px;
    display: block !important;
  }
}

.intervention-direction {
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  padding: 16px;
  margin-top: 24px;
}

.intervention-intro {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 12px;
}

.intervention-suggestion {
  background: white;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 12px;
}

.intervention-suggestion p {
  margin: 8px 0;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap; /* 保留换行 */
}

/* 修复加粗显示 */
.intervention-suggestion strong {
  font-weight: 600;
  color: #1e293b;
}

/* 列表样式优化 */
.intervention-suggestion ol,
.intervention-suggestion ul {
  margin: 12px 0;
  padding-left: 24px;
}

.intervention-suggestion li {
  margin: 6px 0;
  line-height: 1.6;
  font-size: 13px;
}

/* 子列表样式（层级区分） */
.intervention-suggestion li > ol,
.intervention-suggestion li > ul {
  margin-top: 4px;
  padding-left: 20px;
  list-style-type: lower-alpha; /* a, b, c... */
}

.intervention-note {
  font-size: 11px;
  color: #94a3b8;
  font-style: italic;
  margin-top: 12px;
}

/* V4.10.1 新增：场景化衔接说明样式 */
.scene-bridge-box {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  border-left: 4px solid #f59e0b;
  border-radius: 6px;
  padding: 14px 16px;
  margin: 16px 0;
}

.scene-bridge-box p {
  font-size: 13px;
  line-height: 1.6;
  color: #92400e;
  margin: 0;
}

.scene-bridge-box strong {
  color: #b45309;
}

/* V4.10.2 新增：免责声明样式 */
.disclaimer-box {
  background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
  border-left: 4px solid #ef4444;
  border-radius: 6px;
  padding: 14px 16px;
  margin: 16px 0;
}

.disclaimer-box p {
  font-size: 12px;
  line-height: 1.6;
  color: #991b1b;
  margin: 0;
}

.disclaimer-box strong {
  color: #b91c1c;
}

.game-box {
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border-left: 4px solid #0284c7;
  border-radius: 6px;
  padding: 16px;
  margin: 16px 0;
}

.game-box h4 {
  color: #0369a1;
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 12px 0;
}

.game-box p {
  font-size: 13px;
  line-height: 1.7;
  color: #0c4a6e;
  margin: 8px 0;
}

.why-effective {
  background: white;
  padding: 12px;
  border-radius: 4px;
  margin-top: 12px;
  font-size: 12px;
  line-height: 1.6;
}

.why-effective strong {
  color: #0891b2;
}

.game-box .why-effective-box {
  background: #f0f9ff;
  border-left: 3px solid #0284c7;
  padding: 12px;
  margin-top: 12px;
  border-radius: 4px;
}

.game-box .why-effective-box p {
  font-size: 12px;
  line-height: 1.7;
  color: #0c4a6e;
  margin: 0;
}

/* ========== V5.0 三幕式报告样式 ========== */

.v50-report {
  background: #fff;
  border: 2px solid #667eea;
  border-radius: 12px;
  padding: 25px;
  margin: 20px;
}

.v50-report .report-header-section {
  border-bottom: 3px solid #667eea;
  padding-bottom: 15px;
  margin-bottom: 25px;
}

.v50-report .report-header-section h2 {
  color: #667eea;
  font-size: 1.5em;
  margin-bottom: 10px;
}

.v50-report .report-meta {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  font-size: 0.9em;
  color: #666;
}

.v50-report .report-meta span {
  background: #f0f0f0;
  padding: 5px 12px;
  border-radius: 15px;
}

/* 三幕式结构 */
.act-section {
  background: #f8f9fa;
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 25px;
}

.act-section.act1 {
  background: linear-gradient(135deg, #f0f4ff 0%, #e6eeff 100%);
  border: 2px solid #667eea;
}

.act-section.act2 {
  background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
  border: 2px solid #9c27b0;
}

.act-section.act3 {
  background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
  border: 2px solid #4caf50;
}

.act-title {
  font-size: 1.3em;
  font-weight: 600;
  margin-bottom: 5px;
  color: #333;
}

.act1 .act-title { color: #667eea; }
.act2 .act-title { color: #7b1fa2; }
.act3 .act-title { color: #2e7d32; }
.act4 .act-title { color: #ff9800; }

.act-subtitle {
  font-size: 0.9em;
  color: #666;
  margin-bottom: 20px;
  font-style: italic;
}

/* 第一幕：一言以蔽之 */
.one-liner-box {
  background: white;
  border-left: 4px solid #667eea;
  border-radius: 8px;
  padding: 18px;
  margin-bottom: 20px;
}

.one-liner-box h4 {
  color: #667eea;
  font-size: 1em;
  margin-bottom: 12px;
}

.one-liner-text {
  font-size: 1.05em;
  line-height: 1.8;
  color: #333;
  font-style: italic;
}

/* 第一幕：初步判断 */
.judgment-box {
  background: white;
  border-radius: 8px;
  padding: 18px;
  margin-bottom: 20px;
}

.judgment-box h4 {
  color: #667eea;
  font-size: 1em;
  margin-bottom: 12px;
}

.judgment-box p {
  margin: 8px 0;
  line-height: 1.7;
  color: #555;
}

.judgment-box strong {
  color: #333;
}

/* 第一幕：能力缺口卡片 */
.capability-cards {
  display: flex;
  gap: 15px;
  flex-wrap: wrap;
}

.capability-card {
  flex: 1;
  min-width: 200px;
  background: white;
  border-radius: 8px;
  padding: 18px;
  display: flex;
  gap: 15px;
  align-items: flex-start;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.card-icon {
  font-size: 2em;
  line-height: 1;
}

.card-content h4 {
  color: #667eea;
  font-size: 1em;
  margin-bottom: 8px;
}

.card-content p {
  font-size: 0.9em;
  line-height: 1.6;
  color: #666;
  margin: 0;
}

/* 第二幕：分析步骤 */
.analysis-steps {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.analysis-step {
  background: white;
  border-radius: 8px;
  padding: 18px;
}

.analysis-step h4 {
  color: #7b1fa2;
  font-size: 1em;
  margin-bottom: 12px;
}

.analysis-step p {
  line-height: 1.8;
  color: #555;
  margin: 0;
}

/* 第三幕：核心思路 */
.core-idea-box {
  background: white;
  border-left: 4px solid #4caf50;
  border-radius: 8px;
  padding: 18px;
  margin-bottom: 20px;
}

.core-idea-box h4 {
  color: #2e7d32;
  font-size: 1em;
  margin-bottom: 12px;
}

.core-idea-box p {
  line-height: 1.7;
  color: #555;
  margin: 0;
}

/* 第三幕：本周核心任务 */
.weekly-task-box {
  background: white;
  border-radius: 8px;
  padding: 18px;
  margin-bottom: 20px;
}

.weekly-task-box h4 {
  color: #2e7d32;
  font-size: 1em;
  margin-bottom: 15px;
}

.task-steps {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.task-step {
  background: #f8f9fa;
  border-radius: 6px;
  padding: 15px;
}

.task-step.beginner {
  border-left: 4px solid #2196f3;
}

.task-step.advanced {
  border-left: 4px solid #ff9800;
}

.task-step strong {
  color: #333;
  display: block;
  margin-bottom: 8px;
}

.task-step p {
  line-height: 1.7;
  color: #555;
  margin: 0;
}

/* 第三幕：成功的关键 */
.success-key-box {
  background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
  border-left: 4px solid #ff9800;
  border-radius: 8px;
  padding: 18px;
  margin-bottom: 20px;
}

.success-key-box h4 {
  color: #e65100;
  font-size: 1em;
  margin-bottom: 12px;
}

.success-key-box p {
  line-height: 1.7;
  color: #555;
  margin: 0;
}

/* 第三幕：重要提示 */
.important-note-box {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 15px;
  font-size: 0.85em;
  color: #666;
  font-style: italic;
  line-height: 1.7;
}

/* V5.0 新增：第四幕 发展性视角 */
.act-section.act4 {
  background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
  border: 2px solid #ff9800;
}

.act4 .capability-gap-list {
  background: white;
  border-radius: 8px;
  padding: 20px;
  line-height: 1.8;
}

.act4 .capability-gap-list h3 {
  color: #ff9800;
  font-size: 1.1em;
  margin-top: 20px;
  margin-bottom: 10px;
}

.act4 .capability-gap-list p {
  color: #333;
  margin: 5px 0;
}

.act4 .capability-gap-list strong {
  color: #e65100;
}

/* V5.1 新增：排除性分析 */
.exclusion-box {
  background: white;
  border-left: 4px solid #9c27b0;
  border-radius: 8px;
  padding: 18px;
  margin-bottom: 15px;
}

.exclusion-box h4 {
  color: #7b1fa2;
  font-size: 1em;
  margin-bottom: 15px;
}

.exclusion-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.exclusion-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  background: #f8f9fa;
  padding: 12px;
  border-radius: 6px;
}

.exclusion-item.conclusion {
  background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
  border: 1px solid #4caf50;
}

.exclusion-icon {
  font-size: 1.3em;
  line-height: 1;
}

.exclusion-item strong {
  display: block;
  color: #333;
  margin-bottom: 4px;
  font-size: 0.95em;
}

.exclusion-item p {
  margin: 0;
  font-size: 0.9em;
  line-height: 1.6;
  color: #555;
}

/* V5.1 新增：认知机制 */
.cognitive-mechanisms-box {
  background: white;
  border-left: 4px solid #2196f3;
  border-radius: 8px;
  padding: 18px;
  margin-bottom: 15px;
}

.cognitive-mechanisms-box h4 {
  color: #1976d2;
  font-size: 1em;
  margin-bottom: 15px;
}

.mechanism-item {
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e0e0e0;
}

.mechanism-item:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.mechanism-item strong {
  display: block;
  color: #1976d2;
  margin-bottom: 6px;
  font-size: 0.95em;
}

.mechanism-item p {
  margin: 0;
  font-size: 0.9em;
  line-height: 1.7;
  color: #555;
}

/* V5.1 新增：四类支持策略 */
.four-strategies-box {
  background: white;
  border-radius: 8px;
  padding: 18px;
  margin-bottom: 20px;
}

.four-strategies-box h4 {
  color: #2e7d32;
  font-size: 1em;
  margin-bottom: 15px;
}

.strategy-card {
  background: #f8f9fa;
  border-left: 3px solid #4caf50;
  padding: 15px;
  margin-bottom: 15px;
  border-radius: 6px;
}

.strategy-card:last-child {
  margin-bottom: 0;
}

.strategy-card h5 {
  color: #2e7d32;
  font-size: 0.95em;
  margin-bottom: 10px;
  font-weight: 600;
}

.strategy-card p {
  margin: 6px 0;
  font-size: 0.9em;
  line-height: 1.7;
  color: #555;
}

.strategy-card strong {
  color: #1b5e20;
}

.strategy-card ul {
  margin: 0;
  padding-left: 20px;
}

.strategy-card li {
  margin: 6px 0;
  font-size: 0.9em;
  line-height: 1.7;
  color: #555;
}

/* V5.1 新增：发展预期与监测 */
.development-expectation-box {
  background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
  border-left: 4px solid #ff9800;
  border-radius: 8px;
  padding: 18px;
  margin-bottom: 20px;
}

.development-expectation-box h4 {
  color: #e65100;
  font-size: 1em;
  margin-bottom: 15px;
}

.expectation-item {
  margin-bottom: 15px;
  padding-bottom: 15px;
  border-bottom: 1px solid rgba(0,0,0,0.1);
}

.expectation-item:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.expectation-item.concerning {
  background: rgba(244, 67, 54, 0.1);
  padding: 12px;
  border-radius: 6px;
  border-left: 3px solid #f44336;
}

.expectation-item strong {
  display: block;
  color: #e65100;
  margin-bottom: 6px;
  font-size: 0.95em;
}

.expectation-item p {
  margin: 0;
  font-size: 0.9em;
  line-height: 1.7;
  color: #555;
}

.expectation-item ul {
  margin: 0;
  padding-left: 20px;
}

.expectation-item li {
  margin: 4px 0;
  font-size: 0.9em;
  line-height: 1.6;
  color: #555;
}

/* V5.1 新增：家长心态调整 */
.parent-mindset-box {
  background: linear-gradient(135deg, #fce4ec 0%, #f8bbd9 100%);
  border-left: 4px solid #e91e63;
  border-radius: 8px;
  padding: 18px;
  margin-bottom: 20px;
}

.parent-mindset-box h4 {
  color: #880e4f;
  font-size: 1em;
  margin-bottom: 12px;
}

.parent-mindset-box p {
  line-height: 1.8;
  color: #555;
  margin: 0;
  font-size: 0.95em;
}

/* V5.2 新增：鉴别性思考 */
.differential-thinking-box {
  background: white;
  border-left: 4px solid #673ab7;
  border-radius: 8px;
  padding: 18px;
  margin-bottom: 15px;
}

.differential-thinking-box h4 {
  color: #512da8;
  font-size: 1em;
  margin-bottom: 10px;
}

.section-intro {
  font-size: 0.9em;
  color: #666;
  margin-bottom: 15px;
  font-style: italic;
}

.hypotheses-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 15px;
}

.hypothesis-item {
  background: #f3e5f5;
  padding: 12px;
  border-radius: 6px;
  border-left: 3px solid #9c27b0;
}

.hypothesis-label {
  display: inline-block;
  background: #9c27b0;
  color: white;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 0.85em;
  font-weight: 600;
  margin-bottom: 8px;
}

.hypothesis-item p {
  margin: 0;
  font-size: 0.9em;
  line-height: 1.7;
  color: #555;
}

.evidence-exclusion {
  background: #e8eaf6;
  padding: 15px;
  border-radius: 6px;
  margin-bottom: 15px;
}

.evidence-exclusion h5 {
  color: #3f51b5;
  font-size: 0.95em;
  margin-bottom: 10px;
}

.evidence-exclusion ul {
  margin: 0;
  padding-left: 20px;
}

.evidence-exclusion li {
  margin: 6px 0;
  font-size: 0.9em;
  line-height: 1.7;
  color: #555;
}

.conclusion-box {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
  padding: 15px;
  border-radius: 6px;
  border: 1px solid #4caf50;
}

.conclusion-icon {
  font-size: 1.5em;
  line-height: 1;
}

.conclusion-box strong {
  display: block;
  color: #2e7d32;
  margin-bottom: 6px;
  font-size: 0.95em;
}

.conclusion-box p {
  margin: 0;
  font-size: 0.9em;
  line-height: 1.7;
  color: #555;
}

/* V5.2 新增：专家视角整合 */
.expert-integration-box {
  background: linear-gradient(135deg, #fff8e1 0%, #ffecb3 100%);
  border-left: 4px solid #ffc107;
  border-radius: 8px;
  padding: 20px;
  margin-top: 15px;
}

.expert-integration-box h4 {
  color: #ff8f00;
  font-size: 1em;
  margin-bottom: 10px;
}

.expert-integration-text {
  line-height: 1.9;
  color: #555;
  font-size: 0.95em;
  margin: 0;
  font-style: italic;
}

/* V5.2 新增：为什么有效 */
.why-effective-box {
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  border-left: 4px solid #2196f3;
  border-radius: 8px;
  padding: 15px;
  margin-top: 15px;
}

.why-effective-box h5 {
  color: #1976d2;
  font-size: 0.95em;
  margin-bottom: 10px;
}

.why-effective-box p {
  line-height: 1.7;
  color: #555;
  margin: 0;
  font-size: 0.9em;
}

/* ========== V4.10.4 反馈区域样式 ========== */

.feedback-section {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  border: 2px solid #f59e0b;
  border-radius: 12px;
  padding: 24px;
  margin: 24px 0;
}

.feedback-section h4 {
  color: #92400e;
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 8px 0;
}

.feedback-intro {
  color: #78350f;
  font-size: 13px;
  margin: 0 0 16px 0;
}

.rating-stars {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.star {
  font-size: 28px;
  cursor: pointer;
  transition: transform 0.2s;
  user-select: none;
}

.star:hover {
  transform: scale(1.2);
}

.star.active {
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
}

.rating-text {
  color: #92400e;
  font-size: 14px;
  font-weight: 500;
  margin-left: 8px;
}

.accuracy-select {
  margin-bottom: 16px;
}

.accuracy-select label {
  display: block;
  color: #78350f;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 8px;
}

.accuracy-select select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d97706;
  border-radius: 6px;
  font-size: 14px;
  background: white;
  color: #78350f;
}

.feedback-textarea label {
  display: block;
  color: #78350f;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 8px;
}

.feedback-textarea textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #d97706;
  border-radius: 6px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  background: white;
  color: #78350f;
  box-sizing: border-box;
}

.feedback-textarea textarea::placeholder {
  color: #b45309;
  opacity: 0.7;
}

.btn-feedback {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  margin-top: 12px;
  width: 100%;
}

.btn-feedback:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.4);
}

.btn-feedback:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.feedback-message {
  margin-top: 12px;
  padding: 12px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  text-align: center;
}

.feedback-message.success {
  background: #dcfce7;
  color: #166534;
  border: 1px solid #86efac;
}

.feedback-message.error {
  background: #fee2e2;
  color: #991b1b;
  border: 1px solid #fca5a5;
}

/* ========== V4.12.0 三部分报告结构样式 ========== */

/* 📝 场景描述部分 */
.v35-report .scene-section {
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border-left: 4px solid #0284c7;
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 25px;
}

.v35-report .scene-section h3 {
  color: #0369a1;
  font-size: 1.3em;
  font-weight: 600;
  margin: 0 0 15px 0;
}

.v35-report .scene-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.v35-report .scene-item {
  display: flex;
  gap: 10px;
  line-height: 1.7;
}

.v35-report .scene-label {
  font-weight: 600;
  color: #0369a1;
  min-width: 100px;
  flex-shrink: 0;
}

.v35-report .scene-text {
  color: #334155;
  flex: 1;
}

/* 🔍 行为分析部分 */
.v35-report .analysis-section {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  border-left: 4px solid #f59e0b;
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 25px;
}

.v35-report .analysis-section h3 {
  color: #b45309;
  font-size: 1.3em;
  font-weight: 600;
  margin: 0 0 15px 0;
}

.v35-report .analysis-content {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.v35-report .analysis-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.v35-report .analysis-label {
  font-weight: 600;
  color: #b45309;
  font-size: 1.05em;
}

.v35-report .analysis-text {
  color: #334155;
  line-height: 1.8;
  background: rgba(255, 255, 255, 0.6);
  padding: 12px;
  border-radius: 6px;
}

/* 💡 心伴解读部分 */
.v35-report .heart-section {
  background: linear-gradient(135deg, #fce7f3 0%, #fbcfe8 100%);
  border-left: 4px solid #ec4899;
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 25px;
}

.v35-report .heart-section h3 {
  color: #be185d;
  font-size: 1.3em;
  font-weight: 600;
  margin: 0 0 15px 0;
}

.v35-report .heart-content {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.v35-report .heart-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.v35-report .heart-label {
  font-weight: 600;
  color: #be185d;
  font-size: 1.05em;
}

.v35-report .heart-text {
  color: #334155;
  line-height: 1.8;
  background: rgba(255, 255, 255, 0.6);
  padding: 12px;
  border-radius: 6px;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .v35-report .scene-item,
  .v35-report .analysis-item,
  .v35-report .heart-item {
    flex-direction: column;
  }
  
  .v35-report .scene-label,
  .v35-report .analysis-label,
  .v35-report .heart-label {
    min-width: auto;
    margin-bottom: 4px;
  }
  
  .v35-report .scene-text,
  .v35-report .analysis-text,
  .v35-report .heart-text {
    padding: 8px;
  }
}
</style>
