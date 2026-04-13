<template>
  <div class="chat-page"> 
    <div class="chat-toolbar card">
      <div class="toolbar-left">
        <label class="toolbar-label">选择知识库：</label>
        <select v-model="selectedKbId" class="input kb-select" :disabled="kbLoading">
          <option value="" disabled>-- 请选择知识库 --</option>
          <option v-for="kb in kbList" :key="kb.id" :value="kb.id">
            {{ kb.name }}（{{ kb.char_count.toLocaleString() }} 字符）
          </option>
        </select>
        <button
          class="btn btn-primary btn-sm"
          :disabled="!selectedKbId || sessionLoading || thinking"
          @click="handleCreateSession"
        >
          ＋ 新建会话
        </button>
      </div>
      <div v-if="selectedKb" class="toolbar-right">
        <span class="tag tag-green">✅ 已选：{{ selectedKb.name }}</span>
        <span v-if="activeSession" class="tag tag-blue">当前会话：{{ activeSession.title }}</span>
      </div>
    </div>

    <div class="chat-main">
      <aside class="session-panel card">
        <div class="session-panel-header">
          <div class="session-title">会话列表</div>
          <span class="session-count">{{ sessionList.length }} 个</span>
        </div>

        <div v-if="!selectedKbId" class="session-empty">请先选择知识库</div>
        <div v-else-if="sessionLoading" class="session-empty">
          <span class="spinner" style="width:20px;height:20px;border-width:2px"></span>
        </div>
        <div v-else-if="sessionList.length === 0" class="session-empty">
          暂无会话，发送第一条消息后会自动创建
        </div>
        <div v-else class="session-list">
          <div
            v-for="session in sessionList"
            :key="session.id"
            class="session-item"
            :class="{ 'session-item--active': activeSessionId === session.id }"
            @click="loadSessionDetail(session.id)"
          >
            <div class="session-item-main">
              <div class="session-item-title">{{ session.title }}</div>
              <div class="session-item-meta">
                <span>{{ session.message_count }} 条</span>
                <span>{{ formatDateTime(session.updated_at) }}</span>
              </div>
              <div v-if="session.last_question" class="session-item-preview">
                {{ session.last_question }}
              </div>
            </div>
            <button
              class="btn btn-ghost btn-sm session-delete"
              :disabled="deletingSessionId === session.id"
              @click.stop="handleDeleteSession(session)"
            >
              <span v-if="deletingSessionId === session.id" class="spinner" style="width:12px;height:12px;border-width:2px"></span>
              <span v-else>🗑️</span>
            </button>
          </div>
        </div>
      </aside>

      <section class="chat-content">
        <div class="chat-body card" ref="chatBodyRef">
          <div v-if="!selectedKbId" class="empty-state">
            <span class="icon">💬</span>
            <p>请先在上方选择一个知识库，然后开始提问</p>
          </div>

          <div v-else-if="sessionDetailLoading" class="empty-state">
            <span class="spinner" style="width:28px;height:28px;border-width:3px"></span>
          </div>

          <div v-else-if="messages.length === 0" class="empty-state">
            <span class="icon">🤖</span>
            <p>
              {{ activeSession ? `当前会话「${activeSession.title}」暂无消息，请开始提问` : `已选择知识库「${selectedKb?.name}」，请输入第一条问题` }}
            </p>
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

            <div v-if="thinking" class="message-row message-row--ai">
              <div class="message-avatar">🤖</div>
              <div class="message-bubble bubble-ai thinking">
                <span class="dot"></span><span class="dot"></span><span class="dot"></span>
              </div>
            </div>
          </template>
        </div>

        <div class="chat-input-area card">
          <textarea
            v-model="inputText"
            class="input chat-textarea"
            placeholder="输入问题，按 Enter 发送，Shift+Enter 换行..."
            :disabled="!selectedKbId || thinking || sessionDetailLoading"
            rows="3"
            @keydown.enter.exact.prevent="handleSend"
          ></textarea>
          <div class="input-actions">
            <span class="char-count" :class="{ 'char-count--warn': inputText.length > 800 }">
              {{ inputText.length }} / 1000
            </span>
            <button
              class="btn btn-ghost btn-sm"
              :disabled="messages.length === 0 || !activeSessionId"
              @click="handleCreateSession"
            >
              新会话
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
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { listKb } from '@/api/kb'
import {
  sendChat,
  getChatSessions,
  createChatSession,
  getChatSessionDetail,
  deleteChatSession,
} from '@/api/chat'
import { useToastStore } from '@/stores/toast'

const route = useRoute()
const router = useRouter()
const toast = useToastStore()

const kbList = ref([])
const kbLoading = ref(false)
const selectedKbId = ref('')
const sessionList = ref([])
const sessionLoading = ref(false)
const sessionDetailLoading = ref(false)
const activeSessionId = ref(null)
const activeSession = ref(null)
const deletingSessionId = ref(null)
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
  !thinking.value &&
  !sessionDetailLoading.value
)

function buildChatHistory() {
  return messages.value.slice(-10).map((msg) => ({
    role: msg.role === 'ai' ? 'assistant' : 'user',
    content: msg.content,
  }))
}

function normalizeSessionMessages(items = []) {
  const result = []
  for (const item of items) {
    result.push({
      id: `${item.id}-q`,
      role: 'user',
      content: item.question,
      time: item.created_at,
    })
    result.push({
      id: `${item.id}-a`,
      role: 'ai',
      content: item.answer,
      tokens: item.tokens_used,
      time: item.created_at,
    })
  }
  return result
}

async function fetchKbList() {
  kbLoading.value = true
  try {
    const res = await listKb()
    kbList.value = res.data

    const qKbId = Number(route.query.kb_id)
    if (qKbId && kbList.value.find((k) => k.id === qKbId)) {
      selectedKbId.value = qKbId
    } else if (!selectedKbId.value && kbList.value.length > 0) {
      selectedKbId.value = kbList.value[0].id
    }
  } catch (e) {
    toast.error('获取知识库列表失败')
  } finally {
    kbLoading.value = false
  }
}

async function fetchSessions(autoLoad = true) {
  if (!selectedKbId.value) {
    sessionList.value = []
    return
  }

  sessionLoading.value = true
  try {
    const res = await getChatSessions({ kb_id: selectedKbId.value, per_page: 100 })
    sessionList.value = res.data.items

    const routeSessionId = Number(route.query.session_id)
    const existsRouteSession = routeSessionId && sessionList.value.find((s) => s.id === routeSessionId)
    const existsActiveSession = activeSessionId.value && sessionList.value.find((s) => s.id === activeSessionId.value)

    if (autoLoad && existsRouteSession) {
      await loadSessionDetail(routeSessionId)
    } else if (autoLoad && existsActiveSession) {
      await loadSessionDetail(activeSessionId.value)
    } else if (autoLoad && sessionList.value.length > 0) {
      await loadSessionDetail(sessionList.value[0].id)
    } else if (sessionList.value.length === 0) {
      activeSessionId.value = null
      activeSession.value = null
      messages.value = []
    }
  } catch (e) {
    toast.error('获取会话列表失败：' + e.message)
  } finally {
    sessionLoading.value = false
  }
}

async function loadSessionDetail(sessionId) {
  if (!sessionId) return

  sessionDetailLoading.value = true
  try {
    const res = await getChatSessionDetail(sessionId)
    activeSessionId.value = res.data.id
    activeSession.value = {
      id: res.data.id,
      kb_id: res.data.kb_id,
      title: res.data.title,
      updated_at: res.data.updated_at,
      message_count: res.data.message_count,
    }
    selectedKbId.value = res.data.kb_id
    messages.value = normalizeSessionMessages(res.data.messages)
    router.replace({
      path: '/chat',
      query: {
        kb_id: res.data.kb_id,
        session_id: res.data.id,
      },
    })
    scrollToBottom()
  } catch (e) {
    toast.error('加载会话失败：' + e.message)
  } finally {
    sessionDetailLoading.value = false
  }
}

async function handleCreateSession() {
  if (!selectedKbId.value) {
    toast.error('请先选择知识库')
    return
  }

  try {
    const res = await createChatSession(selectedKbId.value)
    toast.success('已创建新会话')
    await fetchSessions(false)
    activeSessionId.value = res.data.id
    activeSession.value = res.data
    messages.value = []
    router.replace({
      path: '/chat',
      query: {
        kb_id: selectedKbId.value,
        session_id: res.data.id,
      },
    })
  } catch (e) {
    toast.error('创建会话失败：' + e.message)
  }
}

async function handleSend() {
  if (!canSend.value) return

  const question = inputText.value.trim()
  const history = buildChatHistory()
  const tempId = Date.now()
  inputText.value = ''

  messages.value.push({
    id: `${tempId}-q`,
    role: 'user',
    content: question,
    time: new Date(),
  })
  scrollToBottom()

  thinking.value = true
  try {
    const res = await sendChat(selectedKbId.value, question, {
      sessionId: activeSessionId.value,
      history,
    })

    activeSessionId.value = res.data.session_id
    activeSession.value = {
      ...(activeSession.value || {}),
      id: res.data.session_id,
      kb_id: selectedKbId.value,
      title: res.data.session_title,
      updated_at: res.data.created_at,
    }

    messages.value.push({
      id: `${tempId}-a`,
      role: 'ai',
      content: res.data.answer,
      tokens: res.data.tokens_used,
      time: res.data.created_at,
    })

    router.replace({
      path: '/chat',
      query: {
        kb_id: selectedKbId.value,
        session_id: res.data.session_id,
      },
    })

    await fetchSessions(false)
  } catch (e) {
    messages.value.push({
      id: `${tempId}-e`,
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

async function handleDeleteSession(session) {
  if (!confirm(`确定删除会话「${session.title}」？该会话中的全部问答都会删除。`)) return

  deletingSessionId.value = session.id
  try {
    await deleteChatSession(session.id)
    toast.success('会话已删除')

    if (activeSessionId.value === session.id) {
      activeSessionId.value = null
      activeSession.value = null
      messages.value = []
    }

    await fetchSessions(false)

    if (sessionList.value.length > 0) {
      await loadSessionDetail(sessionList.value[0].id)
    } else {
      router.replace({ path: '/chat', query: { kb_id: selectedKbId.value } })
    }
  } catch (e) {
    toast.error('删除会话失败：' + e.message)
  } finally {
    deletingSessionId.value = null
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (chatBodyRef.value) {
      chatBodyRef.value.scrollTop = chatBodyRef.value.scrollHeight
    }
  })
}

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

function formatDateTime(iso) {
  return new Date(iso).toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  })
}

watch(selectedKbId, async (newKbId, oldKbId) => {
  if (!newKbId) return
  if (String(newKbId) === String(oldKbId)) return

  activeSessionId.value = null
  activeSession.value = null
  messages.value = []
  router.replace({ path: '/chat', query: { kb_id: newKbId } })
  await fetchSessions(true)
})

onMounted(async () => {
  await fetchKbList()
  await fetchSessions(true)
})
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

.chat-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  gap: 16px;
  flex-shrink: 0;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.toolbar-right {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.toolbar-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  white-space: nowrap;
}
.kb-select { width: 280px; }

.chat-main {
  display: flex;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

.session-panel {
  width: 320px;
  flex-shrink: 0;
  padding: 14px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.session-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.session-title { font-size: 14px; font-weight: 700; }
.session-count { font-size: 12px; color: var(--text-muted); }
.session-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
}
.session-item {
  display: flex;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 10px;
  cursor: pointer;
  transition: all .18s;
}
.session-item:hover {
  border-color: var(--primary);
  background: var(--bg);
}
.session-item--active {
  border-color: var(--primary);
  background: var(--primary-light);
}
.session-item-main { flex: 1; min-width: 0; }
.session-item-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.session-item-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
  flex-wrap: wrap;
}
.session-item-preview {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.session-delete {
  color: var(--danger);
  border-color: transparent;
  align-self: flex-start;
}
.session-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 13px;
  text-align: center;
}

.chat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
  min-height: 0;
}

.chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 14px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
}
.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 8px;
  color: var(--text-muted);
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
.thinking {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 14px 18px;
}
.dot {
  width: 7px;
  height: 7px;
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
.char-count {
  font-size: 12px;
  color: var(--text-muted);
  margin-right: auto;
}
.char-count--warn { color: var(--danger); }
</style>
