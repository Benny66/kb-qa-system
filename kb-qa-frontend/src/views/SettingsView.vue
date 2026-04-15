<template>
  <div class="settings-view">
    <div class="header">
      <div class="header-left">
        <h1>大模型配置</h1>
        <p class="subtitle">管理并切换不同的 AI 提供商和模型。如果这是您第一次启动，请在此处添加您的 API Key。</p>
      </div>
      <button class="btn btn-primary" @click="openAddModal">
        <span class="icon">➕</span> 添加配置
      </button>
    </div>

    <!-- 配置列表 -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>正在加载配置...</p>
    </div>

    <div v-else-if="configs.length > 0" class="config-grid">
      <div 
        v-for="config in configs" 
        :key="config.id" 
        class="config-card" 
        :class="{ 'config-card--default': config.is_default }"
      >
        <div class="config-status-bar" v-if="config.is_default">默认配置</div>
        
        <div class="config-main">
          <div class="config-header">
            <div class="config-title-row">
              <div class="provider-icon" :class="config.provider">
                {{ getProviderIcon(config.provider) }}
              </div>
              <div class="config-info">
                <h3>{{ config.name }}</h3>
                <span class="provider-tag">{{ formatProvider(config.provider) }}</span>
              </div>
            </div>
            <div class="config-actions">
              <button class="btn-icon" @click="editConfig(config)" title="编辑">
                <span class="icon">✏️</span>
              </button>
              <button class="btn-icon btn-icon-danger" @click="confirmDelete(config)" title="删除">
                <span class="icon">🗑️</span>
              </button>
            </div>
          </div>

          <div class="config-details">
            <div class="detail-row">
              <span class="label">聊天模型</span>
              <span class="value font-mono">{{ config.model_name }}</span>
            </div>
            <div class="detail-row">
              <span class="label">向量模型</span>
              <span class="value font-mono">{{ config.embedding_model_name || '未配置 (将使用聊天模型)' }}</span>
            </div>
            <div class="detail-row">
              <span class="label">API Key</span>
              <div class="key-wrapper">
                <span class="value font-mono">{{ config.api_key }}</span>
              </div>
            </div>
            <div class="detail-row" v-if="config.base_url">
              <span class="label">Base URL</span>
              <span class="value truncate" :title="config.base_url">{{ config.base_url }}</span>
            </div>
          </div>
        </div>

        <div class="config-footer">
          <button 
            v-if="!config.is_default" 
            class="btn btn-outline btn-sm" 
            @click="setDefault(config.id)"
          >
            设为默认
          </button>
          <div v-else class="active-badge">
            <span class="dot"></span> 正在使用中
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-state">
      <div class="empty-illustration">🤖</div>
      <h3>尚未配置任何模型</h3>
      <p>系统需要至少一个大模型配置才能进行问答。点击下方按钮开始配置。</p>
      <button class="btn btn-primary btn-lg" @click="openAddModal">
        立即添加第一个配置
      </button>
    </div>

    <!-- 弹窗 -->
    <Transition name="modal">
      <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
        <div class="modal-container">
          <div class="modal-header">
            <h2>{{ editingConfigId ? '编辑模型配置' : '添加新配置' }}</h2>
            <button class="close-btn" @click="closeModal">×</button>
          </div>
          
          <form @submit.prevent="saveConfig" class="modal-form">
            <div class="form-section">
              <div class="form-group">
                <label>配置显示名称</label>
                <input 
                  v-model="form.name" 
                  type="text" 
                  placeholder="给此配置起个名字，如：我的智谱 Flash" 
                  required 
                  ref="nameInput"
                />
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label>AI 提供商</label>
                  <select v-model="form.provider" required>
                    <option value="zhipuai">智谱 AI (ZhipuAI)</option>
                    <option value="doubao">字节豆包 (Doubao)</option>
                    <option value="qianwen">阿里通义 (Qianwen)</option>
                    <option value="minimax">MiniMax</option>
                    <option value="openai-compatible">其他 OpenAI 兼容接口</option>
                  </select>
                </div>
                <div class="form-group">
                  <label>聊天模型名称 (Chat Model)</label>
                  <input v-model="form.model_name" type="text" placeholder="如：glm-4-flash" required />
                </div>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label>向量模型名称 (Embedding Model)</label>
                  <input v-model="form.embedding_model_name" type="text" placeholder="如：embedding-3" />
                </div>
                <div class="form-group">
                  <label>API Key</label>
                  <div class="password-input">
                    <input 
                      v-model="form.api_key" 
                      :type="showApiKey ? 'text' : 'password'" 
                      placeholder="请输入有效的 API Key" 
                      :required="!editingConfigId" 
                    />
                    <button type="button" class="toggle-password" @click="showApiKey = !showApiKey">
                      {{ showApiKey ? '👁️' : '🔒' }}
                    </button>
                  </div>
                </div>
              </div>

              <div class="form-group" v-if="form.provider !== 'zhipuai'">
                <label>接口地址 (Base URL)</label>
                <input v-model="form.base_url" type="text" placeholder="https://api.example.com/v1" />
                <p class="help-text">对于 OpenAI 兼容接口，通常以 /v1 结尾</p>
              </div>

              <div class="form-footer-options">
                <label class="checkbox-container">
                  <input type="checkbox" v-model="form.is_default" />
                  <span class="checkmark"></span>
                  设为系统默认配置
                </label>
              </div>
            </div>

            <div class="modal-actions">
              <button type="button" class="btn btn-ghost" @click="closeModal">取消</button>
              <button type="submit" class="btn btn-primary" :disabled="submitting">
                <span v-if="submitting" class="spinner-sm"></span>
                {{ submitting ? '正在保存...' : '保存配置' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive, nextTick } from 'vue'
import request from '@/api/request'
import { useToastStore } from '@/stores/toast'

const toast = useToastStore()
const configs = ref([])
const loading = ref(true)
const showModal = ref(false)
const editingConfigId = ref(null)
const submitting = ref(false)
const showApiKey = ref(false)
const nameInput = ref(null)

const form = reactive({
  name: '',
  provider: 'zhipuai',
  api_key: '',
  model_name: '',
  embedding_model_name: '',
  base_url: '',
  is_default: false
})

const providerMap = {
  'zhipuai': '智谱 AI',
  'doubao': '字节豆包',
  'qianwen': '阿里通义',
  'minimax': 'MiniMax',
  'openai-compatible': 'OpenAI 兼容'
}

const iconMap = {
  'zhipuai': '🧠',
  'doubao': '📦',
  'qianwen': '☁️',
  'minimax': '🚀',
  'openai-compatible': '🔗'
}

function formatProvider(p) {
  return providerMap[p] || p
}

function getProviderIcon(p) {
  return iconMap[p] || '🤖'
}

async function fetchConfigs() {
  loading.value = true
  try {
    const res = await request.get('/llm-configs')
    configs.value = res.data || []
  } catch (err) {
    toast.error('获取配置失败: ' + err.message)
  } finally {
    loading.value = false
  }
}

function openAddModal() {
  editingConfigId.value = null
  resetForm()
  showModal.value = true
  nextTick(() => nameInput.value?.focus())
}

function editConfig(config) {
  editingConfigId.value = config.id
  form.name = config.name
  form.provider = config.provider
  form.api_key = ''
  form.model_name = config.model_name
  form.embedding_model_name = config.embedding_model_name || ''
  form.base_url = config.base_url || ''
  form.is_default = config.is_default
  showModal.value = true
  nextTick(() => nameInput.value?.focus())
}

function closeModal() {
  showModal.value = false
  editingConfigId.value = null
  showApiKey.value = false
  resetForm()
}

function resetForm() {
  form.name = ''
  form.provider = 'zhipuai'
  form.api_key = ''
  form.model_name = ''
  form.embedding_model_name = ''
  form.base_url = ''
  form.is_default = configs.value.length === 0
}

async function saveConfig() {
  submitting.value = true
  try {
    if (editingConfigId.value) {
      await request.put(`/llm-configs/${editingConfigId.value}`, form)
      toast.success('配置已更新')
    } else {
      await request.post('/llm-configs', form)
      toast.success('配置已添加')
    }
    closeModal()
    fetchConfigs()
  } catch (err) {
    toast.error('保存失败: ' + err.message)
  } finally {
    submitting.value = false
  }
}

async function confirmDelete(config) {
  if (confirm(`确定要删除配置 "${config.name}" 吗？`)) {
    try {
      await request.delete(`/llm-configs/${config.id}`)
      toast.success('配置已删除')
      fetchConfigs()
    } catch (err) {
      toast.error('删除失败: ' + err.message)
    }
  }
}

async function setDefault(id) {
  try {
    await request.post(`/llm-configs/${id}/set-default`)
    toast.success('默认配置已更新')
    fetchConfigs()
  } catch (err) {
    toast.error('设置失败: ' + err.message)
  }
}

onMounted(fetchConfigs)
</script>

<style scoped>
.settings-view {
  padding: 40px;
  max-width: 1200px;
  margin: 0 auto;
  min-height: 100%;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 40px;
}

.header h1 {
  font-size: 28px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 8px;
}

.subtitle {
  color: #64748b;
  font-size: 15px;
}

/* ── Grid & Cards ── */
.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 24px;
}

.config-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.config-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px -8px rgba(0, 0, 0, 0.1);
  border-color: #cbd5e1;
}

.config-card--default {
  border: 2px solid #3b82f6;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.08);
}

.config-status-bar {
  background: #3b82f6;
  color: white;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 4px 0;
  text-align: center;
}

.config-main {
  padding: 24px;
  flex: 1;
}

.config-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.config-title-row {
  display: flex;
  gap: 16px;
  align-items: center;
}

.provider-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.provider-icon.zhipuai { background: #e0f2fe; }
.provider-icon.doubao { background: #fef2f2; }
.provider-icon.qianwen { background: #f0fdf4; }

.config-info h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 4px;
}

.provider-tag {
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
  background: #f8fafc;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid #f1f5f9;
}

.config-actions {
  display: flex;
  gap: 4px;
}

.config-details {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.detail-row .label {
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.detail-row .value {
  font-size: 14px;
  color: #334155;
}

.font-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
}

.config-footer {
  padding: 16px 24px;
  background: #f8fafc;
  border-top: 1px solid #f1f5f9;
}

.active-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #059669;
}

.active-badge .dot {
  width: 8px;
  height: 8px;
  background: #10b981;
  border-radius: 50%;
  box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.15);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

/* ── Modal ── */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-container {
  background: white;
  border-radius: 20px;
  width: 100%;
  max-width: 560px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.modal-header {
  padding: 24px 32px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h2 { font-size: 20px; font-weight: 700; color: #1e293b; }

.close-btn {
  font-size: 24px;
  color: #94a3b8;
  background: none;
  border: none;
  cursor: pointer;
  transition: color 0.2s;
}

.close-btn:hover { color: #1e293b; }

.modal-form { padding: 32px; }

.form-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-bottom: 32px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-size: 14px;
  font-weight: 600;
  color: #475569;
}

.form-group input, 
.form-group select {
  padding: 10px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  font-size: 14px;
  transition: all 0.2s;
}

.form-group input:focus, 
.form-group select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.password-input {
  position: relative;
}

.password-input input {
  width: 100%;
  padding-right: 40px;
}

.toggle-password {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  cursor: pointer;
  opacity: 0.5;
}

.help-text {
  font-size: 12px;
  color: #94a3b8;
}

.checkbox-container {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: #475569;
  cursor: pointer;
  user-select: none;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* ── States ── */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 100px 0;
  color: #64748b;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f1f5f9;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin { to { transform: rotate(360deg); } }

.empty-state {
  text-align: center;
  padding: 80px 40px;
  background: #f8fafc;
  border: 2px dashed #e2e8f0;
  border-radius: 24px;
}

.empty-illustration {
  font-size: 64px;
  margin-bottom: 24px;
}

.empty-state h3 {
  font-size: 20px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 12px;
}

.empty-state p {
  color: #64748b;
  max-width: 400px;
  margin: 0 auto 32px;
}

/* ── Common Components ── */
.btn-outline {
  border: 1px solid #e2e8f0;
  background: white;
  color: #475569;
}

.btn-outline:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.btn-lg {
  padding: 12px 32px;
  font-size: 16px;
  font-weight: 600;
}

.btn-block { width: 100%; }

.btn-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
  border: 1px solid #f1f5f9;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-icon:hover {
  background: #f8fafc;
  border-color: #e2e8f0;
}

.btn-icon-danger:hover {
  background: #fef2f2;
  border-color: #fecaca;
  color: #ef4444;
}

.icon { font-size: 16px; line-height: 1; }

.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
