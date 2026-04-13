<template>
  <div class="page">   
    <div class="page-header">
      <div>
        <h2 class="page-title">🗂️ 知识库管理</h2>
        <p class="page-desc">上传 TXT / PDF / DOCX / Markdown 文件作为知识库，支持中英文内容</p>
      </div>
      <label class="btn btn-primary upload-btn" :class="{ disabled: uploading }">
        <span v-if="uploading" class="spinner"></span>
        <span v-else>＋</span>
        {{ uploading ? `上传中 ${uploadProgress}%` : '上传知识库' }}
        <input
          type="file"
          accept=".txt,.md,.markdown,.pdf,.docx"
          style="display:none"
          :disabled="uploading"
          @change="handleFileChange"
        />
      </label>
    </div>

    <!-- 上传进度条 -->
    <div v-if="uploading" class="progress-bar-wrap">
      <div class="progress-bar" :style="{ width: uploadProgress + '%' }"></div>
    </div>

    <!-- 知识库列表 -->
    <div v-if="loading" class="empty-state">
      <span class="spinner" style="width:32px;height:32px;border-width:3px"></span>
    </div>

    <div v-else-if="kbList.length === 0" class="empty-state">
      <span class="icon">📂</span>
      <p>暂无知识库，点击右上角上传 TXT / PDF / DOCX / Markdown 文件</p>
    </div>

    <div v-else class="kb-grid">
      <div v-for="kb in kbList" :key="kb.id" class="kb-card card">
        <div class="kb-card-header">
          <span class="kb-icon">📄</span>
          <div class="kb-info">
            <div class="kb-name" :title="kb.name">{{ kb.name }}</div>
            <div class="kb-meta">
              <span class="tag tag-blue">{{ formatSize(kb.file_size) }}</span>
              <span class="tag tag-green">{{ kb.char_count.toLocaleString() }} 字符</span>
              <span class="tag" :class="kb.indexed ? 'tag-green' : 'tag-blue'">
                {{ kb.indexed ? '已建索引' : '未建索引' }}
              </span>
              <span class="tag tag-blue">{{ kb.chunk_count || 0 }} chunks</span>
            </div>
          </div>
        </div>
        <div class="kb-date">上传于 {{ formatDate(kb.created_at) }}</div>
        <div class="kb-actions kb-actions--wrap">
          <button class="btn btn-primary btn-sm" @click="goChat(kb)">
            💬 开始问答
          </button>
          <button
            class="btn btn-ghost btn-sm"
            :disabled="reindexingId === kb.id || deletingId === kb.id"
            @click="handleReindex(kb)"
          >
            <span v-if="reindexingId === kb.id" class="spinner" style="width:12px;height:12px;border-width:2px"></span>
            <span v-else>🔄</span>
            重建索引
          </button>
          <button
            class="btn btn-danger btn-sm"
            :disabled="deletingId === kb.id || reindexingId === kb.id"
            @click="handleDelete(kb)"
          >
            <span v-if="deletingId === kb.id" class="spinner" style="width:12px;height:12px;border-width:2px"></span>
            🗑️ 删除
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listKb, uploadKb, deleteKb, reindexKb } from '@/api/kb'
import { useToastStore } from '@/stores/toast'

const router = useRouter()
const toast = useToastStore()

const kbList = ref([])
const loading = ref(false)
const uploading = ref(false)
const uploadProgress = ref(0)
const deletingId = ref(null)
const reindexingId = ref(null)

async function fetchKbList() {
  loading.value = true
  try {
    const res = await listKb()
    kbList.value = res.data
  } catch (e) {
    toast.error('获取知识库列表失败：' + e.message)
  } finally {
    loading.value = false
  }
}

async function handleFileChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  e.target.value = '' // 重置，允许重复上传同名文件

  const allowedExtensions = ['txt', 'md', 'markdown', 'pdf', 'docx']
  const ext = file.name.includes('.') ? file.name.split('.').pop().toLowerCase() : ''
  if (!allowedExtensions.includes(ext)) {
    toast.error('只支持上传 txt / md / markdown / pdf / docx 格式文件')
    return
  }
  if (file.size > 10 * 1024 * 1024) {
    toast.error('文件大小不能超过 10MB')
    return
  }

  uploading.value = true
  uploadProgress.value = 0
  try {
    await uploadKb(file, (p) => { uploadProgress.value = p })
    toast.success('知识库上传成功！')
    await fetchKbList()
  } catch (e) {
    toast.error('上传失败：' + e.message)
  } finally {
    uploading.value = false
    uploadProgress.value = 0
  }
}

async function handleDelete(kb) {
  if (!confirm(`确定删除知识库「${kb.name}」？相关问答历史也会一并删除。`)) return
  deletingId.value = kb.id
  try {
    await deleteKb(kb.id)
    toast.success('知识库已删除')
    kbList.value = kbList.value.filter((k) => k.id !== kb.id)
  } catch (e) {
    toast.error('删除失败：' + e.message)
  } finally {
    deletingId.value = null
  }
}

async function handleReindex(kb) {
  if (!confirm(`确定重建知识库「${kb.name}」的向量索引？`)) return
  reindexingId.value = kb.id
  try {
    const res = await reindexKb(kb.id)
    toast.success(`索引重建成功，共 ${res.data.chunk_count} 个 chunks`)
    const target = kbList.value.find((item) => item.id === kb.id)
    if (target) {
      target.chunk_count = res.data.chunk_count
      target.indexed = true
    }
  } catch (e) {
    toast.error('重建索引失败：' + e.message)
  } finally {
    reindexingId.value = null
  }
}

function goChat(kb) {
  router.push({ path: '/chat', query: { kb_id: kb.id, kb_name: kb.name } })
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

function formatDate(iso) {
  return new Date(iso).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

onMounted(fetchKbList)
</script>

<style scoped>
.page { padding: 28px 32px; }

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
  gap: 16px;
}
.page-title { font-size: 20px; font-weight: 700; }
.page-desc { color: var(--text-muted); font-size: 13px; margin-top: 4px; }

.upload-btn { cursor: pointer; }
.upload-btn.disabled { opacity: .55; pointer-events: none; }

.progress-bar-wrap {
  height: 4px;
  background: var(--border);
  border-radius: 2px;
  margin-bottom: 20px;
  overflow: hidden;
}
.progress-bar {
  height: 100%;
  background: var(--primary);
  border-radius: 2px;
  transition: width .3s;
}

.kb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.kb-card {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: box-shadow .18s;
}
.kb-card:hover { box-shadow: var(--shadow); }

.kb-card-header { display: flex; gap: 12px; align-items: flex-start; }
.kb-icon { font-size: 28px; flex-shrink: 0; }
.kb-info { flex: 1; min-width: 0; }
.kb-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  margin-bottom: 6px;
}
.kb-meta { display: flex; gap: 6px; flex-wrap: wrap; }
.kb-date { font-size: 12px; color: var(--text-muted); }
.kb-actions { display: flex; gap: 8px; }
.kb-actions--wrap { flex-wrap: wrap; }
</style>
