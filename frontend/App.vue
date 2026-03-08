<template>
  <div class="app-container">
    <header class="header">
      <h1>📘 行为观察与干预支持指南 V3.9 Final</h1>
      <p class="subtitle">从分析到决策支持</p>
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

            <!-- 二、多角度理解（V3.9 Final） -->
            <div v-if="insightReport.clinical_differential" class="report-section clinical-differential">
              <h3>二、多角度理解</h3>
              <p>{{ insightReport.clinical_differential }}</p>
            </div>

            <!-- 三、行为模式解读 -->
            <div class="report-section expert-view">
              <h3>三、行为模式解读</h3>
              <div class="hypothesis-box">
                <p><strong>主要假设：</strong>{{ insightReport.primary_hypothesis || insightReport.expert_view }}</p>
                <p><strong>支持证据：</strong>{{ insightReport.supporting_evidence || '基于您的详细描述和行为模式分析。' }}</p>
                <p><strong>核心能力建设目标：</strong>{{ insightReport.core_capability_goal || '提升在无实时外部提示下，维持任务序列的工作记忆能力。' }}</p>
              </div>
            </div>

            <!-- 四、我们可以这样开始（V3.9 Final） -->
            <div v-if="interventionPlan && interventionPlan.four_step_plan" class="report-section intervention-plan-final">
              <h3>四、我们可以这样开始</h3>
              
              <div class="four-step-container">
                <!-- 1. 核心思路 -->
                <div class="step-item step-core">
                  <h4>💡 核心思路</h4>
                  <p>{{ interventionPlan.four_step_plan.core_idea }}</p>
                </div>
                
                <!-- 2. 我们的计划 -->
                <div class="step-item step-plan">
                  <h4>🎮 我们的计划：{{ interventionPlan.phase_name || '动作密语' }}</h4>
                  <p>{{ interventionPlan.four_step_plan.our_plan }}</p>
                </div>
                
                <!-- 3. 成功的画面 -->
                <div class="step-item step-success">
                  <h4> 成功的画面</h4>
                  <p class="success-picture">{{ interventionPlan.four_step_plan.success_picture }}</p>
                </div>
                
                <!-- 4. 第一步行动与观察 -->
                <div class="step-item step-first">
                  <h4>🚀 第一步行动与观察</h4>
                  <p>{{ interventionPlan.four_step_plan.first_step }}</p>
                </div>
              </div>
              
              <!-- V3.9 Final 成功时刻记录卡 -->
              <div v-if="interventionPlan.observation_tool" class="observation-tool-final">
                <h4>📋 您的"成功时刻"记录卡</h4>
                <p>{{ interventionPlan.observation_tool }}</p>
              </div>
            </div>

            <!-- 五、展望与共勉 -->
            <div class="report-section reflection">
              <h3>五、展望与共勉</h3>
              <div class="future-section">
                <p><strong>后续可能的方向：</strong>{{ interventionPlan?.next_phase_preview || insightReport.reflection }}</p>
                <p><strong>给您的赋能思考题：</strong>{{ insightReport.empowerment_question || '在接下来一周，请留意孩子在哪件他热爱的事情上，展现出惊人的"无需提醒"的专注力？' }}</p>
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
      <p>Behavior Recorder V3.9 Final | 行为记录员封版</p>
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
        const response = await axios.post('/api/v3/chat', {
          session_id: this.sessionId,
          user_input: text,
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
        this.messages.push({
          role: 'ai',
          text: '抱歉，处理您的请求时出现了问题。请重试。',
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

    formatMessage(text) {
      if (!text) return ''
      // V3.6 修复：使用全局过滤器处理特殊字符
      return this.$escape(text).replace(/\n/g, '<br>')
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

/* V3.9.1 Final 四步结构样式 */
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

/* V3.9.1 Final 成功时刻记录卡 */
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
</style>
