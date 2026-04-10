<template>
  <div class="login-page">
    <div class="login-card card">
      <div class="login-header">
        <div class="login-logo">📚</div>
        <h1>知识库问答系统</h1>
        <p>请使用预置账号登录</p>
      </div>

      <form class="login-form" @submit.prevent="handleLogin">
        <div class="form-group">
          <label>用户名</label>
          <input
            v-model="form.username"
            class="input"
            type="text"
            placeholder="请输入用户名"
            autocomplete="username"
            :disabled="loading"
          />
        </div>

        <div class="form-group">
          <label>密码</label>
          <input
            v-model="form.password"
            class="input"
            type="password"
            placeholder="请输入密码"
            autocomplete="current-password"
            :disabled="loading"
          />
        </div>

        <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>

        <button class="btn btn-primary login-btn" type="submit" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? '登录中...' : '登 录' }}
        </button>
      </form>

      <div class="login-hint">
        <p>预置账号：</p>
        <div class="hint-accounts">
          <span class="tag tag-blue" @click="fillAccount('admin', 'admin123')">admin / admin123</span>
          <span class="tag tag-blue" @click="fillAccount('demo', 'demo123')">demo / demo123</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'

const router = useRouter()
const auth = useAuthStore()
const toast = useToastStore()

const form = reactive({ username: '', password: '' })
const loading = ref(false)
const errorMsg = ref('')

function fillAccount(username, password) {
  form.username = username
  form.password = password
}

async function handleLogin() {
  errorMsg.value = ''
  if (!form.username.trim() || !form.password.trim()) {
    errorMsg.value = '用户名和密码不能为空'
    return
  }
  loading.value = true
  try {
    await auth.login(form.username.trim(), form.password.trim())
    toast.success('登录成功，欢迎回来！')
    router.push('/')
  } catch (e) {
    errorMsg.value = e.message || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 400px;
  padding: 40px 36px;
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}
.login-logo { font-size: 48px; margin-bottom: 12px; }
.login-header h1 { font-size: 22px; font-weight: 700; color: var(--text-primary); }
.login-header p { color: var(--text-muted); margin-top: 6px; font-size: 13px; }

.login-form { display: flex; flex-direction: column; gap: 18px; }

.form-group { display: flex; flex-direction: column; gap: 6px; }
.form-group label { font-size: 13px; font-weight: 500; color: var(--text-secondary); }

.error-msg {
  padding: 10px 14px;
  background: var(--danger-light);
  color: var(--danger);
  border-radius: var(--radius-sm);
  font-size: 13px;
  border: 1px solid #fecaca;
}

.login-btn {
  width: 100%;
  justify-content: center;
  padding: 11px;
  font-size: 15px;
  margin-top: 4px;
}

.login-hint {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--border);
  text-align: center;
}
.login-hint p { font-size: 12px; color: var(--text-muted); margin-bottom: 10px; }
.hint-accounts { display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; }
.hint-accounts .tag { cursor: pointer; transition: opacity .18s; }
.hint-accounts .tag:hover { opacity: .75; }
</style>
