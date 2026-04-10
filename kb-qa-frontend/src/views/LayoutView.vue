<template>
  <div class="layout">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-logo">
        <span class="logo-icon">📚</span>
        <span class="logo-text">知识库问答</span>
      </div>

      <nav class="sidebar-nav">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          active-class="nav-item--active"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="user-info">
          <div class="user-avatar">{{ userInitial }}</div>
          <div class="user-meta">
            <div class="user-name">{{ auth.user?.username }}</div>
            <div class="user-role">普通用户</div>
          </div>
        </div>
        <button class="btn btn-ghost btn-sm logout-btn" @click="handleLogout">
          退出
        </button>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const navItems = [
  { to: '/kb',      icon: '🗂️',  label: '知识库管理' },
  { to: '/chat',    icon: '💬',  label: 'AI 问答' },
  { to: '/history', icon: '📋',  label: '问答历史' },
]

const userInitial = computed(() =>
  auth.user?.username?.charAt(0).toUpperCase() || 'U'
)

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* ── 侧边栏 ── */
.sidebar {
  width: var(--sidebar-width);
  background: #1e293b;
  color: #e2e8f0;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 22px 20px;
  border-bottom: 1px solid #334155;
}
.logo-icon { font-size: 22px; }
.logo-text { font-size: 16px; font-weight: 700; color: #f1f5f9; }

.sidebar-nav {
  flex: 1;
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  color: #94a3b8;
  font-size: 14px;
  transition: all .18s;
}
.nav-item:hover { background: #334155; color: #e2e8f0; }
.nav-item--active { background: var(--primary); color: #fff !important; }
.nav-icon { font-size: 16px; width: 20px; text-align: center; }

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid #334155;
  display: flex;
  align-items: center;
  gap: 10px;
}
.user-info { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; }
.user-avatar {
  width: 34px; height: 34px;
  background: var(--primary);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 14px; color: #fff;
  flex-shrink: 0;
}
.user-meta { min-width: 0; }
.user-name { font-size: 13px; font-weight: 600; color: #f1f5f9; truncate: ellipsis; overflow: hidden; white-space: nowrap; }
.user-role { font-size: 11px; color: #64748b; }
.logout-btn { color: #94a3b8; border-color: #334155; font-size: 12px; padding: 4px 10px; }
.logout-btn:hover { color: #f1f5f9; background: #334155; }

/* ── 主内容 ── */
.main-content {
  flex: 1;
  overflow-y: auto;
  background: var(--bg);
}
</style>
