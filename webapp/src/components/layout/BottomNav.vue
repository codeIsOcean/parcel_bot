<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLocale } from '@/composables/useLocale'

const route = useRoute()
const router = useRouter()
const { t } = useLocale()

// Элементы навигации
const navItems = computed(() => [
  { path: '/', icon: '🏠', label: t('nav_home') },
  { path: '/parcels', icon: '📦', label: t('nav_parcels') },
  { path: '/chats', icon: '💬', label: t('nav_chats') },
  { path: '/profile', icon: '👤', label: t('nav_profile') },
])

// Определяем активный таб
const isActive = (path) => {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

// Переход по табу
const navigate = (path) => {
  if (route.path !== path) {
    router.push(path)
  }
}
</script>

<template>
  <!-- Нижняя навигация (Bottom Tab Bar) -->
  <nav class="bottom-nav">
    <button
      v-for="item in navItems"
      :key="item.path"
      class="nav-item"
      :class="{ active: isActive(item.path) }"
      @click="navigate(item.path)"
    >
      <!-- Иконка таба -->
      <span class="nav-icon">{{ item.icon }}</span>
      <!-- Подпись таба -->
      <span class="nav-label">{{ item.label }}</span>
    </button>
  </nav>
</template>

<style scoped>
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-around;
  align-items: center;
  height: 72px;
  padding-bottom: env(safe-area-inset-bottom, 8px);
  background: rgba(28, 28, 30, 0.95);
  backdrop-filter: blur(20px);
  border-top: 1px solid #2C2C2E;
  z-index: 100;
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 8px 16px;
  background: none;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
  -webkit-tap-highlight-color: transparent;
}

.nav-icon {
  font-size: 22px;
  line-height: 1;
}

.nav-label {
  font-size: 10px;
  font-weight: 500;
  color: #8E8E93;
  transition: color 0.2s;
}

.nav-item.active .nav-label {
  color: #6C5CE7;
}
</style>
