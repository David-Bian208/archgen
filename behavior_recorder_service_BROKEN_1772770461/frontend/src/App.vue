<template>
  <div class="app-container">
    <header class="header">
      <h1>🧩 行为记录员</h1>
      <p class="subtitle">自闭症干预辅助系统 - 行为分析工具</p>
    </header>

    <main class="main-content">
      <!-- 输入区域 -->
      <section class="input-section">
        <h2>📝 行为描述</h2>
        <textarea
          v-model="description"
          placeholder="请描述孩子的行为情况，例如：&#10;不给他手机，他就打自己头，我赶紧把手机给他了。"
          rows="6"
          :disabled="loading"
        ></textarea>
        <button 
          @click="analyze" 
          :disabled="!description.trim() || loading"
          class="analyze-btn"
        >
          {{ loading ? '分析中...' : '开始分析' }}
        </button>
      </section>

      <!-- 结果区域 -->
      <section v-if="result" class="result-section">
        <h2>📊 分析结果</h2>
        
        <div class="result-grid">
          <div class="result-card antecedent">
            <h3>前因 (A)</h3>
            <p>{{ result.antecedent || '未提取到' }}</p>
          </div>
          
          <div class="result-card behavior">
            <h3>行为 (B)</h3>
            <p>{{ result.behavior || '未提取到' }}</p>
          </div>
          
          <div class="result-card consequence">
            <h3>后果 (C)</h3>
            <p>{{ result.consequence || '未提取到' }}</p>
          </div>
          
          <div class="result-card function" :class="result.hypothesized_function">
            <h3>假设功能</h3>
            <p class="function-value">{{ formatFunction(result.hypothesized_function) }}</p>
            <p class="function-desc">{{ getFunctionDescription(result.hypothesized_function) }}</p>
          </div>
        </div>

        <!-- 功能说明 -->
        <div class="function-guide">
          <h3>💡 功能说明</h3>
          <ul>
            <li><strong>逃避 (escape)</strong>：行为是为了逃避或终止某个任务或情境</li>
            <li><strong>实物 (tangible)</strong>：行为是为了获得物品、食物或活动</li>
            <li><strong>关注 (attention)</strong>：行为是为了获得他人的注意（正面或负面）</li>
            <li><strong>自我刺激 (automatic)</strong>：行为是为了自我刺激或感官调节</li>
          </ul>
        </div>
      </section>

      <!-- 错误提示 -->
      <section v-if="error" class="error-section">
        <h2>⚠️ 分析失败</h2>
        <p>{{ error }}</p>
        <button @click="clearError" class="retry-btn">重试</button>
      </section>
    </main>

    <footer class="footer">
      <p>Behavior Recorder Service v1.0.0 | 自闭症干预辅助系统</p>
    </footer>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'App',
  data() {
    return {
      description: '',
      result: null,
      loading: false,
      error: null,
    }
  },
  methods: {
    async analyze() {
      if (!this.description.trim()) return

      this.loading = true
      this.error = null
      this.result = null

      try {
        const response = await axios.post('/api/analyze', {
          description: this.description.trim()
        })

        if (response.data.success) {
          this.result = response.data.data
        } else {
          this.error = response.data.message || '分析失败'
        }
      } catch (err) {
        console.error('分析请求失败:', err)
        this.error = err.response?.data?.detail || '网络错误，请稍后重试'
      } finally {
        this.loading = false
      }
    },

    clearError() {
      this.error = null
    },

    formatFunction(func) {
      const map = {
        escape: '逃避 (Escape)',
        tangible: '实物 (Tangible)',
        attention: '关注 (Attention)',
        automatic: '自我刺激 (Automatic)'
      }
      return map[func] || func
    },

    getFunctionDescription(func) {
      const descriptions = {
        escape: '孩子通过行为来逃避或终止不喜欢的任务或情境',
        tangible: '孩子通过行为来获得想要的物品、食物或活动',
        attention: '孩子通过行为来获得他人的注意（包括批评）',
        automatic: '行为本身带来感官刺激或自我调节的效果'
      }
      return descriptions[func] || ''
    }
  }
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
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
}

.header {
  text-align: center;
  color: white;
  margin-bottom: 30px;
}

.header h1 {
  font-size: 2.5rem;
  margin-bottom: 10px;
}

.subtitle {
  font-size: 1.1rem;
  opacity: 0.9;
}

.main-content {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.2);
}

.input-section h2,
.result-section h2,
.error-section h2 {
  color: #333;
  margin-bottom: 15px;
  font-size: 1.5rem;
}

textarea {
  width: 100%;
  padding: 15px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 1rem;
  resize: vertical;
  transition: border-color 0.3s;
}

textarea:focus {
  outline: none;
  border-color: #667eea;
}

.analyze-btn {
  margin-top: 15px;
  padding: 12px 30px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1.1rem;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.analyze-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
}

.analyze-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
  margin-bottom: 25px;
}

.result-card {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 20px;
  border-left: 4px solid #667eea;
}

.result-card h3 {
  font-size: 0.9rem;
  color: #666;
  margin-bottom: 10px;
  text-transform: uppercase;
}

.result-card p {
  font-size: 1.1rem;
  color: #333;
}

.result-card.antecedent { border-left-color: #4CAF50; }
.result-card.behavior { border-left-color: #2196F3; }
.result-card.consequence { border-left-color: #FF9800; }

.result-card.function {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-left: none;
}

.result-card.function h3 {
  color: rgba(255,255,255,0.8);
}

.result-card.function p {
  color: white;
}

.function-value {
  font-size: 1.3rem !important;
  font-weight: bold;
  margin-bottom: 5px !important;
}

.function-desc {
  font-size: 0.85rem !important;
  opacity: 0.9;
}

.function-guide {
  background: #f0f4ff;
  border-radius: 8px;
  padding: 20px;
}

.function-guide h3 {
  color: #667eea;
  margin-bottom: 15px;
}

.function-guide ul {
  list-style: none;
}

.function-guide li {
  padding: 8px 0;
  color: #555;
  border-bottom: 1px solid #e0e0e0;
}

.function-guide li:last-child {
  border-bottom: none;
}

.error-section {
  background: #ffebee;
  border-radius: 8px;
  padding: 20px;
  margin-top: 20px;
}

.error-section h2 {
  color: #c62828;
}

.error-section p {
  color: #b71c1c;
  margin-bottom: 15px;
}

.retry-btn {
  padding: 10px 20px;
  background: #c62828;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.retry-btn:hover {
  background: #b71c1c;
}

.footer {
  text-align: center;
  color: rgba(255,255,255,0.8);
  margin-top: 30px;
  padding: 20px;
}
</style>
