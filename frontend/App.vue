<template>
  <div class="app-container">
    <header class="header">
      <h1>📘 行为观察与干预支持指南 V4.5</h1>
      <p class="subtitle">临床推理引擎 | 动态假设追踪 | 叙事性报告</p>
    </header>

    <main class="main-content">
      <div class="chat-container">
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
            :class="msg.role"
          >
            <div class="message-avatar">
              {{ msg.role === 'user' ? '👤' : '💬' }}
            </div>
            <div class="message-content">
              <p v-html="formatMessage(msg.text)"></p>
            </div>
          </div>

          <!-- V3.5 洞察报告（会话完成时） -->
          <div v-if="insightReport" class="insight-report v35-report">
            <div class="report-header-section">
              <h2>📘 行为观察与干预支持指南</h2>
              <div class="report-meta">
                <span><strong>场景：</strong>{{ reportData.scene || '行为观察' }}</span>
                <span><strong>分析日期：</strong>{{ today }}</span>
              </div>
            </div>

            <!-- 摘要 -->
            <div class="report-section summary">
              <h3>📋 摘要</h3>
              <p class="summary-text">{{ insightReport.summary || insightReport.observation }}</p>
            </div>

            <!-- 一、我们共同的发现 -->
            <div class="report-section">
              <h3>一、我们共同的发现：理解行为</h3>
              <div class="detail-list">
                <div class="detail-item">
                  <strong>情境：</strong>{{ reportData.context || insightReport.context }}
                </div>
                <div class="detail-item">
                  <strong>孩子的表现：</strong>{{ reportData.child_behavior || insightReport.child_behavior }}
                </div>
                <div class="detail-item">
                  <strong>周围的反应：</strong>{{ reportData.others_response || insightReport.others_response }}
                </div>
                <div class="detail-item highlight">
                  <strong>您的关键洞察：</strong>{{ insightReport.parent_insight || '您敏锐地观察到了孩子的行为模式，这是帮助他的第一步。' }}
                </div>
              </div>
            </div>

            <!-- 二、多角度理解与能力分析（V4.10.0 精简版） -->
            <div v-if="insightReport.clinical_differential" class="report-section clinical-differential">
              <h3>二、多角度理解与能力分析</h3>
              <div class="clinical-text" v-html="formatMarkdown(insightReport.clinical_differential)"></div>
              <!-- V4.10.0 修复：删除冗余的 hypothesis-box，clinical_differential 已包含完整三模块 -->
            </div>

            <!-- 三、行动起点：从一个关键信号开始（V4.10.2 通用框架版） -->
            <div v-if="interventionPlan && interventionPlan.four_step_plan" class="report-section intervention-direction">
              <h3>三、可尝试的行动方向（仅供参考）</h3>
              <p class="intervention-intro">基于上述能力缺口，以下是干预的核心思路和参考方向。</p>
              
              <!-- V4.10.2 新增：免责声明 -->
              <div class="disclaimer-box">
                <p>⚠️ <strong>重要提示：</strong>以下建议仅供参考，不能替代专业评估和个性化干预方案。具体训练活动建议咨询专业治疗师，根据孩子的具体情况设计。</p>
              </div>
              
              <!-- V4.10.1 新增：场景化衔接说明 -->
              <div v-if="interventionPlan.scene_bridge" class="scene-bridge-box">
                <p><strong>🎯 干预重点：</strong>{{ interventionPlan.scene_bridge }}</p>
              </div>
              
              <!-- V4.10.0 新增：核心思路 -->
              <div v-if="interventionPlan.four_step_plan.core_idea" class="core-idea-box">
                <p><strong>💡 核心思路：</strong>{{ interventionPlan.four_step_plan.core_idea }}</p>
              </div>
              
              <div class="intervention-suggestion">
                <div class="game-box">
                  <h4>📚 参考练习类型</h4>
                  <p>{{ interventionPlan.four_step_plan.our_plan }}</p>
                </div>
                
                <p><strong>建议起点：</strong>{{ interventionPlan.four_step_plan.first_step }}</p>
              </div>
              
              <p class="intervention-note">注：以上分析是基于您提供的有限情境的深度解读。每个孩子都是独特的，一份完整的干预方案需要更全面的评估并由专业人员制定。</p>
            </div>

            <!-- 四、展望与共勉 -->
            <div class="report-section reflection">
              <h3>四、展望与共勉</h3>
              <div class="future-section">
                <p><strong>后续可能的方向：</strong>{{ interventionPlan?.next_phase_preview || insightReport.reflection }}</p>
                <p><strong>给您的赋能思考题：</strong>{{ insightReport.empowerment_question || '在接下来一周，请留意孩子在哪件他热爱的事情上，展现出惊人的"无需提醒"的专注力？' }}</p>
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
                🤖 AI 正在分析您的问题，这通常需要 <strong>5-10 秒</strong>，请耐心等待...
              </p>
              <p class="loading-hint">
                💡 提示：AI 正在进行深度临床推理，包括行为功能分析、能力缺口评估和干预建议生成。
              </p>
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
      <p>Behavior Recorder V4.5 | 临床推理引擎 | 动态假设追踪</p>
    </footer>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'App',
  data() {
    return {
      sessionId: null,
      userInput: '',
      messages: [],
      loading: false,
      sessionCompleted: false,
      insightReport: null,
      interventionPlan: null,  // V3.5 新增
      reportData: {},  // V3.5 新增
      today: new Date().toLocaleDateString('zh-CN'),
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

      try {
        const response = await axios.post('/api/v4/chat', {
          session_id: this.sessionId,
          user_input: text,
        }, {
          timeout: 60000, // 60 秒超时（V4.10.5 优化）
        })

        const data = response.data

        if (!this.sessionId) {
          this.sessionId = data.session_id
        }

        // 添加 AI 响应
        this.messages.push({
          role: 'ai',
          text: data.message,
          timestamp: new Date().toISOString(),
        })

        // 检查是否完成
        if (data.status === 'completed' && data.data) {
          this.sessionCompleted = true
          this.insightReport = data.data.report
          // V3.5 新增：干预计划
          this.interventionPlan = data.data.intervention_plan
          this.reportData = {
            context: data.data.context,
            child_behavior: data.data.child_behavior,
            others_response: data.data.others_response,
            scene: data.data.context,
          }
          // V3.6 新增：确保 clinical_differential 字段可用
          if (data.data.report.clinical_differential) {
            this.insightReport.clinical_differential = data.data.report.clinical_differential
          }
        }

        this.scrollToBottom()

      } catch (error) {
        console.error('发送失败:', error)
        
        let errorMessage = '抱歉，处理您的请求时出现了问题。'
        
        if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
          errorMessage = '⏱️ 响应时间较长，AI 仍在努力分析中。建议您：\n\n1. 稍等片刻后刷新页面重试\n2. 避开使用高峰（如晚上 8-10 点）\n3. 如果问题持续，请联系管理员\n\n感谢您的耐心！'
        } else {
          errorMessage += '请重试。'
        }
        
        this.messages.push({
          role: 'ai',
          text: errorMessage,
          timestamp: new Date().toISOString(),
        })
      } finally {
        this.loading = false
      }
    },

    startNewSession() {
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
📘 行为观察与干预支持指南
========================

📋 摘要
${this.insightReport.summary || this.insightReport.observation}

一、我们共同的发现：理解行为
- 情境：${this.reportData.context || ''}
- 孩子的表现：${this.reportData.child_behavior || ''}
- 周围的反应：${this.reportData.others_response || ''}

二、专业视角：可能性分析与决策
${this.insightReport.expert_view}

三、我们的第一步计划：${plan.phase_name || '干预计划'}
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
      
      let html = this.$escape(text)
      
      // 1. 加粗：**text** → <strong>text</strong>（全局替换，支持多次出现）
      html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      
      // 2. 处理换行：先保留所有换行
      html = html.replace(/\n/g, '<LINEBREAK>')
      
      // 3. 有序列表和无序列表处理
      const lines = html.split('<LINEBREAK>')
      const processedLines = []
      let inOrderedList = false
      let inUnorderedList = false
      
      // V4.10.3 修复：主标题关键词（不渲染为列表，保持为普通段落）
      const mainTitles = ['鉴别与排除', '核心假设', '能力缺口分析']
      
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim()
        
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
          processedLines.push(`<li>${orderedMatch[2]}</li>`)
        } else if (unorderedMatch) {
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
          processedLines.push(`<li>${unorderedMatch[1]}</li>`)
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
            processedLines.push(line + '<br>')
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
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  text-align: center;
  color: white;
  margin-bottom: 20px;
}

.header h1 {
  font-size: 2rem;
  margin-bottom: 5px;
}

.subtitle {
  font-size: 1rem;
  opacity: 0.9;
}

.main-content {
  flex: 1;
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.2);
  overflow: hidden;
  display: flex;
  flex-direction: column;
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
  padding: 20px;
}

.welcome-message {
  text-align: center;
  padding: 40px 20px;
}

.message {
  display: flex;
  margin-bottom: 20px;
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
  font-size: 1.5rem;
  margin: 0 10px;
}

.message-content {
  max-width: 80%;
  padding: 15px 20px;
  border-radius: 12px;
  background: #f0f0f0;
  line-height: 1.6;
}

.message.user .message-content {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.message.ai .message-content {
  background: #f8f9fa;
  border: 1px solid #e0e0e0;
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
  margin: 20px;
  background: white;
  border-radius: 12px;
  padding: 25px;
  border: 2px solid #667eea;
  box-shadow: 0 5px 20px rgba(102, 126, 234, 0.2);
}

.report-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 2px solid #667eea;
}

.report-header .header-icon {
  font-size: 1.8em;
}

.report-header h3 {
  color: #667eea;
  font-size: 1.4em;
  margin: 0;
}

.report-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.report-section {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 15px 20px;
}

.report-section h4 {
  color: #333;
  font-size: 1em;
  margin-bottom: 10px;
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
  gap: 10px;
  padding: 20px;
  border-top: 1px solid #e0e0e0;
  background: #f8f9fa;
}

textarea {
  flex: 1;
  padding: 12px 15px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 1em;
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
  padding: 12px 25px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1em;
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  border-radius: 10px;
  margin-bottom: 25px;
}

.v35-report .summary h3 {
  margin-bottom: 10px;
}

.v35-report .summary-text {
  font-size: 1.05em;
  line-height: 1.7;
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
</style>
