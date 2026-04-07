<template>
  <div class="history-viewer">
    <h2>历史记录</h2>
    
    <!-- 搜索和筛选 -->
    <div class="search-filter">
      <div class="search-box">
        <input type="text" v-model="searchKeyword" placeholder="搜索记录...">
        <button @click="searchSessions" class="btn-secondary">搜索</button>
      </div>
      <div class="filter-box">
        <select v-model="filterChildId">
          <option value="">所有儿童</option>
          <option v-for="child in children" :key="child.id" :value="child.id">{{ child.name }}</option>
        </select>
        <select v-model="filterStatus">
          <option value="">所有状态</option>
          <option value="active">进行中</option>
          <option value="completed">已完成</option>
        </select>
        <button @click="filterSessions" class="btn-secondary">筛选</button>
      </div>
    </div>
    
    <!-- 历史记录列表 -->
    <div class="history-list">
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="sessions.length === 0" class="empty">暂无历史记录</div>
      <div v-else class="session-cards">
        <div v-for="session in sessions" :key="session.session_id" class="session-card">
          <div class="session-header">
            <h4>会话 ID: {{ session.session_id }}</h4>
            <span class="session-status" :class="session.status">{{ session.status === 'completed' ? '已完成' : '进行中' }}</span>
          </div>
          <div class="session-info">
            <p><strong>开始时间：</strong>{{ formatDate(session.started_at) }}</p>
            <p v-if="session.ended_at"><strong>结束时间：</strong>{{ formatDate(session.ended_at) }}</p>
            <p><strong>对话轮次：</strong>{{ session.total_turns }}</p>
            <p v-if="session.child_id"><strong>儿童：</strong>{{ getChildName(session.child_id) }}</p>
          </div>
          <div class="session-actions">
            <button @click="viewSession(session)" class="btn-secondary">查看详情</button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 分页 -->
    <div class="pagination" v-if="sessions.length > 0">
      <button @click="loadMore" :disabled="loading" class="btn-secondary">
        {{ loading ? '加载中...' : '加载更多' }}
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'HistoryViewer',
  props: {
    user_id: {
      type: Number,
      required: true
    },
    children: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      sessions: [],
      loading: false,
      searchKeyword: '',
      filterChildId: '',
      filterStatus: '',
      limit: 10,
      offset: 0
    }
  },
  mounted() {
    this.loadSessions()
  },
  methods: {
    async loadSessions() {
      this.loading = true
      try {
        const response = await this.$axios.get(`/api/v4/sessions/${this.user_id}`, {
          params: {
            limit: this.limit
          }
        })
        if (response.data.status === 'success') {
          this.sessions = response.data.sessions
        }
      } catch (error) {
        console.error('加载会话列表失败:', error)
      } finally {
        this.loading = false
      }
    },
    async searchSessions() {
      if (!this.searchKeyword) {
        await this.loadSessions()
        return
      }

      this.loading = true
      try {
        const response = await this.$axios.get(`/api/v4/data/search/${this.user_id}`, {
          params: {
            keyword: this.searchKeyword,
            limit: this.limit
          }
        })
        if (response.data.status === 'success') {
          this.sessions = response.data.sessions
        }
      } catch (error) {
        console.error('搜索会话失败:', error)
      } finally {
        this.loading = false
      }
    },
    async filterSessions() {
      this.loading = true
      try {
        const response = await this.$axios.get(`/api/v4/data/filter/${this.user_id}`, {
          params: {
            child_id: this.filterChildId || null,
            status: this.filterStatus || null,
            limit: this.limit
          }
        })
        if (response.data.status === 'success') {
          this.sessions = response.data.sessions
        }
      } catch (error) {
        console.error('筛选会话失败:', error)
      } finally {
        this.loading = false
      }
    },
    async loadMore() {
      this.offset += this.limit
      this.loading = true
      try {
        const response = await this.$axios.get(`/api/v4/sessions/${this.user_id}`, {
          params: {
            limit: this.limit,
            offset: this.offset
          }
        })
        if (response.data.status === 'success' && response.data.sessions.length > 0) {
          this.sessions = [...this.sessions, ...response.data.sessions]
        }
      } catch (error) {
        console.error('加载更多会话失败:', error)
      } finally {
        this.loading = false
      }
    },
    viewSession(session) {
      this.$emit('session-selected', session)
    },
    getChildName(childId) {
      const child = this.children.find(c => c.id === childId)
      return child ? child.name : '未知'
    },
    formatDate(dateString) {
      if (!dateString) return ''
      const date = new Date(dateString)
      return date.toLocaleString('zh-CN')
    }
  }
}
</script>

<style scoped>
.history-viewer {
  padding: 20px;
}

h2 {
  text-align: center;
  color: #667eea;
  margin-bottom: 20px;
}

.search-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 20px;
  background: white;
  padding: 15px;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.search-box,
.filter-box {
  display: flex;
  align-items: center;
  gap: 10px;
}

input, select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 14px;
}

.btn-secondary {
  padding: 8px 16px;
  background: #f0f0f0;
  color: #333;
  border: none;
  border-radius: 5px;
  font-size: 14px;
  cursor: pointer;
}

.btn-secondary:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.history-list {
  margin-bottom: 20px;
}

.loading,
.empty {
  text-align: center;
  padding: 40px;
  color: #666;
  background: white;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.session-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 15px;
}

.session-card {
  background: white;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.session-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f0f0f0;
}

.session-header h4 {
  color: #667eea;
  margin: 0;
}

.session-status {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.session-status.completed {
  background: #e8f5e9;
  color: #2e7d32;
}

.session-status.active {
  background: #e3f2fd;
  color: #1976d2;
}

.session-info p {
  margin: 5px 0;
  font-size: 14px;
  color: #555;
}

.session-actions {
  margin-top: 15px;
  text-align: right;
}

.pagination {
  text-align: center;
  margin-top: 20px;
}
</style>