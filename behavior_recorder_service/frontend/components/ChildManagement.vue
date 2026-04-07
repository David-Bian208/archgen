<template>
  <div class="child-management">
    <h2>儿童管理</h2>
    
    <!-- 儿童列表 -->
    <div class="child-list" v-if="children.length > 0">
      <h3>已添加的儿童</h3>
      <div class="child-cards">
        <div v-for="child in children" :key="child.id" class="child-card">
          <div class="child-info">
            <h4>{{ child.name }}</h4>
            <p><strong>性别：</strong>{{ child.gender || '未设置' }}</p>
            <p><strong>年龄：</strong>{{ child.age || '未设置' }} 岁</p>
            <p><strong>出生日期：</strong>{{ child.birth_date || '未设置' }}</p>
            <p v-if="child.notes"><strong>备注：</strong>{{ child.notes }}</p>
          </div>
          <div class="child-actions">
            <button @click="selectChild(child)" class="btn-secondary">选择</button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 添加儿童表单 -->
    <div class="add-child-form">
      <h3>添加儿童</h3>
      <div class="form-group">
        <label for="child-name">姓名</label>
        <input type="text" id="child-name" v-model="newChild.name" placeholder="请输入儿童姓名">
      </div>
      <div class="form-group">
        <label for="child-gender">性别</label>
        <select id="child-gender" v-model="newChild.gender">
          <option value="">请选择</option>
          <option value="男">男</option>
          <option value="女">女</option>
        </select>
      </div>
      <div class="form-group">
        <label for="child-age">年龄</label>
        <input type="number" id="child-age" v-model.number="newChild.age" placeholder="请输入年龄">
      </div>
      <div class="form-group">
        <label for="child-birth-date">出生日期</label>
        <input type="date" id="child-birth-date" v-model="newChild.birth_date">
      </div>
      <div class="form-group">
        <label for="child-notes">备注</label>
        <textarea id="child-notes" v-model="newChild.notes" placeholder="请输入备注信息"></textarea>
      </div>
      <button @click="addChild" :disabled="loading" class="btn-primary">
        {{ loading ? '添加中...' : '添加儿童' }}
      </button>
      <div v-if="errorMessage" class="error-message">
        {{ errorMessage }}
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ChildManagement',
  props: {
    user_id: {
      type: Number,
      required: true
    }
  },
  data() {
    return {
      children: [],
      newChild: {
        name: '',
        gender: '',
        age: 0,
        birth_date: '',
        notes: ''
      },
      loading: false,
      errorMessage: ''
    }
  },
  mounted() {
    this.loadChildren()
  },
  methods: {
    async loadChildren() {
      try {
        const response = await this.$axios.get(`/api/v4/children/${this.user_id}`)
        if (response.data.status === 'success') {
          this.children = response.data.children
        }
      } catch (error) {
        console.error('加载儿童列表失败:', error)
      }
    },
    async addChild() {
      if (!this.newChild.name) {
        this.errorMessage = '儿童姓名是必填项'
        return
      }

      this.loading = true
      this.errorMessage = ''

      try {
        const response = await this.$axios.post('/api/v4/children', {
          user_id: this.user_id,
          name: this.newChild.name,
          gender: this.newChild.gender,
          birth_date: this.newChild.birth_date,
          age: this.newChild.age,
          notes: this.newChild.notes
        })

        if (response.data.status === 'success') {
          // 重新加载儿童列表
          await this.loadChildren()
          // 重置表单
          this.newChild = {
            name: '',
            gender: '',
            age: 0,
            birth_date: '',
            notes: ''
          }
        } else {
          this.errorMessage = response.data.message || '添加失败'
        }
      } catch (error) {
        this.errorMessage = error.response?.data?.detail || '添加失败，请重试'
      } finally {
        this.loading = false
      }
    },
    selectChild(child) {
      this.$emit('child-selected', child)
    }
  }
}
</script>

<style scoped>
.child-management {
  padding: 20px;
}

h2 {
  text-align: center;
  color: #667eea;
  margin-bottom: 20px;
}

h3 {
  color: #333;
  margin: 20px 0 10px;
}

.child-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 15px;
  margin-bottom: 30px;
}

.child-card {
  background: white;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.child-info {
  flex: 1;
}

.child-info h4 {
  color: #667eea;
  margin-bottom: 10px;
}

.child-info p {
  margin: 5px 0;
  font-size: 14px;
  color: #555;
}

.child-actions {
  margin-left: 15px;
}

.add-child-form {
  background: white;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.form-group {
  margin-bottom: 15px;
}

label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
  color: #333;
}

input, select, textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 16px;
}

textarea {
  resize: vertical;
  min-height: 80px;
}

input:focus, select:focus, textarea:focus {
  outline: none;
  border-color: #667eea;
}

.btn-primary {
  padding: 12px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 5px;
  font-size: 16px;
  cursor: pointer;
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

.btn-primary:hover:not(:disabled),
.btn-secondary:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-primary:disabled,
.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-message {
  color: #e74c3c;
  font-size: 14px;
  margin-top: 10px;
}
</style>