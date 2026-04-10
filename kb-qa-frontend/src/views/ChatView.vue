<template>
  <div class="chat-page">
    <!-- 顶部工具栏 -->
    <div class="chat-toolbar card">
      <div class="toolbar-left">
        <label class="toolbar-label">选择知识库：</label>
        <select v-model="selectedKbId" class="input kb-select" :disabled="kbLoading">
          <option value="" disabled>-- 请选择知识库 --</option>
          <option v-for="kb in kbList" :key="kb.id" :value="kb.id">
            {{ kb.name }}（{{ kb.char_count.toLocaleString() }} 字符）
          </option>
        </select>
      </div>
      <div v-if="selectedKb" class="toolbar-right">
        <span class="tag tag-green">✅ 已选：{{ selectedKb.name }}</span>
      </div>
    </div>

    <!-- 消息区域 -->
    <div class="chat-body" ref="chatBodyRef">
      <div v-if="!selectedKbId" class="empty-state">
        <span class="icon">💬</span>
        <p>请先在上方选择一个知识库，然后开始提问</p>
      </div>

      <div v-else-if="messages.length === 0" class="empty-state">
        <span class="icon">🤖</span>
        <p>已选择知识库「{{ selectedKb?.name }}」，请在下方输入问题</p>
      </div>

      <template v-else>
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="message-row"
          :class="msg.role === 'user' ? 'message-row--user' : 'message-row--ai'"
        >
          <div class="message-avatar">
            {{ msg.role === 'user' ? '👤' : '🤖' }}
          </div>
          <div class="message-bubble" :class="msg.role === 'user' ? 'bubble-user' : 'bubble-ai'">
            <div class="message-content" v-html="renderContent(msg.content)"></div>
            <div class="message-meta">
              {{ formatTime(msg.time) }}
              <span v-if="msg.tokens" class="token-info">· {{ msg.tokens }} tokens</span>
            </div>
          </div>
        </div>

        <!-- AI 思考中 -->
        <div v-if="thinking" class="message-row message-row--ai">
          <div class="message-avatar">🤖</div>
          <div class="message-bubble bubble-ai thinking">
            <span class="dot"></span><span class="dot"></span><span class="dot"></span>
          </div>
        </div>
      </template>
    </div>

    <!-- 输入区域 -->
    <div class="chat-input-area card">
      <textarea
        v-model="inputText"
        class="input chat-textarea"
        placeholder="输入问题，按 Enter 发送，Shift+Enter 换行..."
        :disabled="!selectedKbId || thinking"
        rows="3"
        @keydown.enter.exact.prevent="handleSend"
      ></textarea>
      <div class="input-actions">
        <span class="char-count" :class="{ 'char-count--warn': inputText.length > 800 }">
          {{ inputText.length }} / 1000
        </span>
        <button
          class="btn btn-ghost btn-sm"
          :disabled="messages.length === 0"
          @click="clearMessages"
        >
          清空对话
        </button>
        <button
          class="btn btn-primary"
          :disabled="!canSend"
          @click="handleSend"
        >
          <span v-if="thinking" class="spinner" style="width:14px;height:14px;border-width:2px"></span>
          {{ thinking ? '回答中...' : '发 送' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { listKb } from '@/api/kb'
import { sendChat } from '@/api/chat'
import { useToastStore } from '@/stores/toast'

const route = useRoute()
const toast = useToastStore()

const kbList = ref([])
const kbLoading = ref(false)
const selectedKbId = ref('')
const messages = ref([])
const inputText = ref('')
const thinking = ref(false)
const chatBodyRef = ref(null)

const selectedKb = computed(() =>
  kbList.value.find((k) => k.id === selectedKbId.value) || null
)

const canSend = computed(() =>
  selectedKbId.value &&
  inputText.value.trim().length > 0 &&
  inputText.value.length <= 1000 &&
  !thinking.value
)

async function fetchKbList() {
  kbLoading.value = true
  try {
    const res = await listKb()
    kbList.value = res.data
    // 如果路由带了 kb_id 参数，自动选中
    const qKbId = Number(route.query.kb_id)
    if (qKbId && kbList.value.find((k) => k.id === qKbId)) {
      selectedKbId.value = qKbId
    }
  } catch (e) {
    toast.error('获取知识库列表失败')
  } finally {
    kbLoading.value = false
  }
}

async function handleSend() {
  if (!canSend.value) return
  const question = inputText.value.trim()
  inputText.value = ''

  // 添加用户消息
  messages.value.push({
    id: Date.now(),
    role: 'user',
    content: question,
    time: new Date(),
  })
  scrollToBottom()

  thinking.value = true
  try {
    const res = await sendChat(selectedKbId.value, question)
    messages.value.push({
      id: Date.now() + 1,
      role: 'ai',
      content: res.data.answer,
      tokens: res.data.tokens_used,
      time: new Date(),
    })
  } catch (e) {
    messages.value.push({
      id: Date.now() + 1,
      role: 'ai',
      content: `❌ 请求失败：${e.message}`,
      time: new Date(),
    })
  } finally {
    thinking.value = false
    await nextTick()
    scrollToBottom()
  }
}

function clearMessages() {
  if (messages.value.length === 0) return
  if (confirm('确定清空当前对话记录？')) {
    messages.value = []
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (chatBodyRef.value) {
      chatBodyRef.value.scrollTop = chatBodyRef.value.scrollHeight
    }
  })
}

// 简单的换行转 <br>，保留代码块样式
function renderContent(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
}

function formatTime(date) {
  return new Date(date).toLocaleTimeString('zh-CN', {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

// 切换知识库时清空对话
watch(selectedKbId, () => { messages.value = [] })

onMounted(fetchKbList)
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 20px 24px;
  gap: 16px;
  overflow: hidden;
}

/* ── 工具栏 ── */
.chat-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  gap: 16px;
  flex-shrink: 0;
}
.toolbar-left { display: flex; align-items: center; gap: 10px; }
.toolbar-label { font-size: 13px; font-weight: 500; color: var(--text-secondary); white-space: nowrap; }
.kb-select { width: 280px; }

/* ── 消息区 ── */
.chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px 4px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message-row {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}
.message-row--user { flex-direction: row-reverse; }

.message-avatar {
  font-size: 22px;
  flex-shrink: 0;
  width: 36px;
  text-align: center;
  margin-top: 2px;
}

.message-bubble {
  max-width: 72%;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.7;
  font-size: 14px;
}
.bubble-user {
  background: var(--primary);
  color: #fff;
  border-top-right-radius: 4px;
}
.bubble-ai {
  background: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--text-primary);
  border-top-left-radius: 4px;
  box-shadow: var(--shadow-sm);
}

.message-content { word-break: break-word; }
.message-meta {
  font-size: 11px;
  margin-top: 6px;
  opacity: .6;
}
.token-info { margin-left: 4px; }

/* 思考动画 */
.thinking {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 14px 18px;
}
.dot {
  width: 7px; height: 7px;
  background: var(--text-muted);
  border-radius: 50%;
  animation: bounce .9s infinite;
}
.dot:nth-child(2) { animation-delay: .15s; }
.dot:nth-child(3) { animation-delay: .3s; }
@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-6px); }
}

/* ── 输入区 ── */
.chat-input-area {
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex-shrink: 0;
}
.chat-textarea {
  resize: none;
  font-size: 14px;
  line-height: 1.6;
  min-height: 72px;
}
.input-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}
.char-count { font-size: 12px; color: var(--text-muted); margin-right: auto; }
.char-count--warn { color: var(--danger); }
</style>
