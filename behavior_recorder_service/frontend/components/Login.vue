<template>
  <div class="login-container">
    <div class="login-form">
      <h2>登录</h2>
      <div class="form-group">
        <label for="email">邮箱</label>
        <input type="email" id="email" v-model="loginForm.email" placeholder="请输入邮箱">
      </div>
      <div class="form-group">
        <label for="password">密码</label>
        <input type="password" id="password" v-model="loginForm.password" placeholder="请输入密码">
      </div>
      <button @click="login" :disabled="loading" class="btn-primary">
        {{ loading ? '登录中...' : '登录' }}
      </button>
      <div class="form-footer">
        <p>还没有账号？<a href="#" @click.prevent="showRegister = true">立即注册</a></p>
      </div>
      <div v-if="errorMessage" class="error-message">
        {{ errorMessage }}
      </div>
    </div>

    <!-- 注册表单 -->
    <div class="register-form" v-if="showRegister">
      <h2>注册</h2>
      <div class="form-group">
        <label for="username">用户名</label>
        <input type="text" id="username" v-model="registerForm.username" placeholder="请输入用户名">
      </div>
      <div class="form-group">
        <label for="register-email">邮箱</label>
        <input type="email" id="register-email" v-model="registerForm.email" placeholder="请输入邮箱">
      </div>
      <div class="form-group">
        <label for="register-password">密码</label>
        <input type="password" id="register-password" v-model="registerForm.password" placeholder="请输入密码">
      </div>
      <div class="form-group">
        <label for="full-name">全名</label>
        <input type="text" id="full-name" v-model="registerForm.full_name" placeholder="请输入全名">
      </div>
      <button @click="register" :disabled="registerLoading" class="btn-primary">
        {{ registerLoading ? '注册中...' : '注册' }}
      </button>
      <div class="form-footer">
        <p>已有账号？<a href="#" @click.prevent="showRegister = false">立即登录</a></p>
      </div>
      <div v-if="registerErrorMessage" class="error-message">
        {{ registerErrorMessage }}
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Login',
  data() {
    return {
      showRegister: false,
      loading: false,
      registerLoading: false,
      errorMessage: '',
      registerErrorMessage: '',
      loginForm: {
        email: '',
        password: ''
      },
      registerForm: {
        username: '',
        email: '',
        password: '',
        full_name: ''
      }
    }
  },
  methods: {
    async login() {
      if (!this.loginForm.email || !this.loginForm.password) {
        this.errorMessage = '邮箱和密码是必填项'
        return
      }

      this.loading = true
      this.errorMessage = ''

      try {
        const response = await this.$axios.post('/api/v4/auth/login', {
          email: this.loginForm.email,
          password: this.loginForm.password
        })

        if (response.data.status === 'success') {
          localStorage.setItem('token', response.data.access_token)
          localStorage.setItem('user', JSON.stringify(response.data.user))
          this.$emit('login-success', response.data.user)
        } else {
          this.errorMessage = response.data.message || '登录失败'
        }
      } catch (error) {
        this.errorMessage = error.response?.data?.detail || '登录失败，请重试'
      } finally {
        this.loading = false
      }
    },
    async register() {
      if (!this.registerForm.username || !this.registerForm.email || !this.registerForm.password) {
        this.registerErrorMessage = '用户名、邮箱和密码是必填项'
        return
      }

      this.registerLoading = true
      this.registerErrorMessage = ''

      try {
        const response = await this.$axios.post('/api/v4/auth/register', {
          username: this.registerForm.username,
          email: this.registerForm.email,
          password: this.registerForm.password,
          full_name: this.registerForm.full_name
        })

        if (response.data.status === 'success') {
          this.showRegister = false
          this.loginForm.email = this.registerForm.email
          this.loginForm.password = this.registerForm.password
          this.registerForm = {
            username: '',
            email: '',
            password: '',
            full_name: ''
          }
        } else {
          this.registerErrorMessage = response.data.message || '注册失败'
        }
      } catch (error) {
        this.registerErrorMessage = error.response?.data?.detail || '注册失败，请重试'
      } finally {
        this.registerLoading = false
      }
    }
  }
}
</script>

<style scoped>
.login-container {
  max-width: 400px;
  margin: 0 auto;
  padding: 20px;
}

.login-form,
.register-form {
  background: white;
  border-radius: 10px;
  padding: 30px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

h2 {
  text-align: center;
  color: #667eea;
  margin-bottom: 20px;
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

input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 16px;
}

input:focus {
  outline: none;
  border-color: #667eea;
}

.btn-primary {
  width: 100%;
  padding: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 5px;
  font-size: 16px;
  cursor: pointer;
  margin-top: 10px;
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.form-footer {
  text-align: center;
  margin-top: 15px;
  font-size: 14px;
}

.form-footer a {
  color: #667eea;
  text-decoration: none;
}

.form-footer a:hover {
  text-decoration: underline;
}

.error-message {
  color: #e74c3c;
  font-size: 14px;
  margin-top: 10px;
  text-align: center;
}
</style>