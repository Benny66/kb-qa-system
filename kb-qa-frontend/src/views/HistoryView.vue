<template>
  <div class="page"> 
    <div class="page-header">
      <div>
        <h2 class="page-title">📋 会话历史</h2>
        <p class="page-desc">按会话查看历史问答，并可继续聊天</p>
      </div>
    </div>

    <div class="filter-bar card">
      <select v-model="filterKbId" class="input filter-select" @change="fetchSessions(1)">
        <option value="">全部知识库</option>
        <option v-for="kb in kbList" :key="kb.id" :value="kb.id">{{ kb.name }}</option>
      </select>
      <span class="total-info">共 {{ total }} 个会话</span>
    </div>

    <div v-if="loading" class="empty-state">
      <span class="spinner" style="width:32px;height:32px;border-width:3px"></span>
    </div>

    <div v-else-if="sessionList.length === 0" class="empty-state">
      <span class="icon">📭</span>
      <p>暂无会话历史</p>
    </div>

    <div v-else class="history-list">
      <div v-for="item in sessionList" :key="item.id" class="history-card card">
        <div class="history-header">
          <div class="history-meta">
            <span class="tag tag-blue">{{ item.kb_name }}</span>
            <span class="tag tag-green">{{ item.message_count }} 条消息</span>
            <span class="history-time">最近更新：{{ formatDate(item.updated_at) }}</span>
          </div>
          <div class="history-actions">
            <button class="btn btn-primary btn-sm" @click="goContinueChat(item)">
              继续聊天
            </button>
            <button
              class="btn btn-ghost btn-sm delete-btn"
              :disabled="deletingId === item.id"
              @click="handleDelete(item)"
            >
              <span v-if="deletingId === item.id" class="spinner" style="width:12px;height:12px;border-width:2px"></span>
              <span v-else>🗑️</span>
            </button>
          </div>
        </div>

        <div class="session-summary">
          <div class="session-title">{{ item.title }}</div>
          <div v-if="item.last_question" class="session-preview">
            最近提问：{{ item.last_question }}
          </div>
          <div class="session-created">创建时间：{{ formatDate(item.created_at) }}</div>
        </div>
      </div>
    </div>

    <div v-if="pages > 1" class="pagination">
      <button
        class="btn btn-ghost btn-sm"
        :disabled="currentPage === 1"
        @click="fetchSessions(currentPage - 1)"
      >
        ← 上一页
      </button>
      <span class="page-info">{{ currentPage }} / {{ pages }}</span>
      <button
        class="btn btn-ghost btn-sm"
        :disabled="currentPage === pages"
        @click="fetchSessions(currentPage + 1)"
      >
        下一页 →
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listKb } from '@/api/kb'
import { getChatSessions, deleteChatSession } from '@/api/chat'
import { useToastStore } from '@/stores/toast'

const router = useRouter()
const toast = useToastStore()

const kbList = ref([])
const sessionList = ref([])
const loading = ref(false)
const filterKbId = ref('')
const total = ref(0)
const currentPage = ref(1)
const pages = ref(1)
const deletingId = ref(null)

async function fetchKbList() {
  try {
    const res = await listKb()
    kbList.value = res.data
  } catch {}
}

async function fetchSessions(page = 1) {
  loading.value = true
  currentPage.value = page
  try {
    const params = { page, per_page: 15 }
    if (filterKbId.value) params.kb_id = filterKbId.value
    const res = await getChatSessions(params)
    sessionList.value = res.data.items
    total.value = res.data.total
    pages.value = res.data.pages
  } catch (e) {
    toast.error('获取会话历史失败：' + e.message)
  } finally {
    loading.value = false
  }
}

function goContinueChat(item) {
  router.push({
    path: '/chat',
    query: {
      kb_id: item.kb_id,
      session_id: item.id,
    },
  })
}

async function handleDelete(item) {
  if (!confirm(`确定删除会话「${item.title}」？该会话中的全部消息都会删除。`)) return
  deletingId.value = item.id
  try {
    await deleteChatSession(item.id)
    toast.success('已删除')
    sessionList.value = sessionList.value.filter((h) => h.id !== item.id)
    total.value--
  } catch (e) {
    toast.error('删除失败：' + e.message)
  } finally {
    deletingId.value = null
  }
}

function formatDate(iso) {
  return new Date(iso).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

onMounted(async () => {
  await fetchKbList()
  await fetchSessions()
})
</script>

<style scoped>
.page { padding: 28px 32px; }
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}
.page-title { font-size: 20px; font-weight: 700; }
.page-desc { color: var(--text-muted); font-size: 13px; margin-top: 4px; }

.filter-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
  margin-bottom: 20px;
}
.filter-select { width: 220px; }
.total-info { font-size: 13px; color: var(--text-muted); margin-left: auto; }

.history-list { display: flex; flex-direction: column; gap: 14px; }
.history-card { padding: 18px 20px; }
.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.history-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.history-actions { display: flex; align-items: center; gap: 8px; }
.history-time { font-size: 12px; color: var(--text-muted); }
.delete-btn { color: var(--danger); border-color: transparent; }
.delete-btn:hover { background: var(--danger-light); }

.session-summary { display: flex; flex-direction: column; gap: 8px; }
.session-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}
.session-preview {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.7;
}
.session-created {
  font-size: 12px;
  color: var(--text-muted);
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 24px;
  padding-bottom: 20px;
}
.page-info { font-size: 13px; color: var(--text-secondary); }
</style>
