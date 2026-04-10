<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">📋 问答历史</h2>
        <p class="page-desc">查看所有 AI 问答记录</p>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar card">
      <select v-model="filterKbId" class="input filter-select" @change="fetchHistory(1)">
        <option value="">全部知识库</option>
        <option v-for="kb in kbList" :key="kb.id" :value="kb.id">{{ kb.name }}</option>
      </select>
      <span class="total-info">共 {{ total }} 条记录</span>
    </div>

    <!-- 列表 -->
    <div v-if="loading" class="empty-state">
      <span class="spinner" style="width:32px;height:32px;border-width:3px"></span>
    </div>

    <div v-else-if="historyList.length === 0" class="empty-state">
      <span class="icon">📭</span>
      <p>暂无问答历史</p>
    </div>

    <div v-else class="history-list">
      <div v-for="item in historyList" :key="item.id" class="history-card card">
        <div class="history-header">
          <div class="history-meta">
            <span class="tag tag-blue">{{ item.kb_name }}</span>
            <span class="history-time">{{ formatDate(item.created_at) }}</span>
            <span v-if="item.tokens_used" class="tag tag-green">{{ item.tokens_used }} tokens</span>
          </div>
          <button
            class="btn btn-ghost btn-sm delete-btn"
            :disabled="deletingId === item.id"
            @click="handleDelete(item)"
          >
            <span v-if="deletingId === item.id" class="spinner" style="width:12px;height:12px;border-width:2px"></span>
            <span v-else>🗑️</span>
          </button>
        </div>

        <div class="qa-block">
          <div class="qa-question">
            <span class="qa-label q-label">Q</span>
            <div class="qa-text">{{ item.question }}</div>
          </div>
          <div class="qa-answer">
            <span class="qa-label a-label">A</span>
            <div class="qa-text answer-text" :class="{ expanded: expandedIds.has(item.id) }">
              {{ item.answer }}
            </div>
          </div>
          <button
            v-if="item.answer.length > 200"
            class="expand-btn"
            @click="toggleExpand(item.id)"
          >
            {{ expandedIds.has(item.id) ? '▲ 收起' : '▼ 展开全文' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="pages > 1" class="pagination">
      <button
        class="btn btn-ghost btn-sm"
        :disabled="currentPage === 1"
        @click="fetchHistory(currentPage - 1)"
      >
        ← 上一页
      </button>
      <span class="page-info">{{ currentPage }} / {{ pages }}</span>
      <button
        class="btn btn-ghost btn-sm"
        :disabled="currentPage === pages"
        @click="fetchHistory(currentPage + 1)"
      >
        下一页 →
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { listKb } from '@/api/kb'
import { getHistory, deleteHistory } from '@/api/chat'
import { useToastStore } from '@/stores/toast'

const toast = useToastStore()

const kbList = ref([])
const historyList = ref([])
const loading = ref(false)
const filterKbId = ref('')
const total = ref(0)
const currentPage = ref(1)
const pages = ref(1)
const deletingId = ref(null)
const expandedIds = reactive(new Set())

async function fetchKbList() {
  try {
    const res = await listKb()
    kbList.value = res.data
  } catch {}
}

async function fetchHistory(page = 1) {
  loading.value = true
  currentPage.value = page
  try {
    const params = { page, per_page: 15 }
    if (filterKbId.value) params.kb_id = filterKbId.value
    const res = await getHistory(params)
    historyList.value = res.data.items
    total.value = res.data.total
    pages.value = res.data.pages
  } catch (e) {
    toast.error('获取历史失败：' + e.message)
  } finally {
    loading.value = false
  }
}

async function handleDelete(item) {
  if (!confirm('确定删除这条问答记录？')) return
  deletingId.value = item.id
  try {
    await deleteHistory(item.id)
    toast.success('已删除')
    historyList.value = historyList.value.filter((h) => h.id !== item.id)
    total.value--
  } catch (e) {
    toast.error('删除失败：' + e.message)
  } finally {
    deletingId.value = null
  }
}

function toggleExpand(id) {
  if (expandedIds.has(id)) expandedIds.delete(id)
  else expandedIds.add(id)
}

function formatDate(iso) {
  return new Date(iso).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

onMounted(async () => {
  await fetchKbList()
  await fetchHistory()
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
  margin-bottom: 14px;
}
.history-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.history-time { font-size: 12px; color: var(--text-muted); }
.delete-btn { color: var(--danger); border-color: transparent; }
.delete-btn:hover { background: var(--danger-light); }

.qa-block { display: flex; flex-direction: column; gap: 10px; }

.qa-question, .qa-answer {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}
.qa-label {
  width: 22px; height: 22px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700;
  flex-shrink: 0;
  margin-top: 1px;
}
.q-label { background: var(--primary-light); color: var(--primary); }
.a-label { background: var(--success-light); color: #16a34a; }

.qa-text {
  flex: 1;
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-primary);
  word-break: break-word;
}
.answer-text {
  max-height: 80px;
  overflow: hidden;
  position: relative;
}
.answer-text::after {
  content: '';
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 30px;
  background: linear-gradient(transparent, white);
}
.answer-text.expanded {
  max-height: none;
}
.answer-text.expanded::after { display: none; }

.expand-btn {
  background: none;
  border: none;
  color: var(--primary);
  font-size: 12px;
  cursor: pointer;
  padding: 2px 0;
  margin-left: 32px;
}
.expand-btn:hover { text-decoration: underline; }

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
