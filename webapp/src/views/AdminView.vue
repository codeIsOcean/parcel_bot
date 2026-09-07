<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { adminApi } from '@/api/admin'
import PageHeader from '@/components/layout/PageHeader.vue'
import AdminStats from '@/components/admin/AdminStats.vue'
import AdminUsers from '@/components/admin/AdminUsers.vue'
import AdminParcels from '@/components/admin/AdminParcels.vue'
import AdminFlights from '@/components/admin/AdminFlights.vue'
import AdminGroups from '@/components/admin/AdminGroups.vue'
import AdminReports from '@/components/admin/AdminReports.vue'
import AdminPayments from '@/components/admin/AdminPayments.vue'
import AdminSupport from '@/components/admin/AdminSupport.vue'
import AdminBroadcast from '@/components/admin/AdminBroadcast.vue'

const route = useRoute()
const router = useRouter()
const { t } = useLocale()
const { haptic } = useTelegram()

// Разделы панели и их компоненты
const tabs = [
  { id: 'stats', icon: '📊', component: AdminStats },
  { id: 'users', icon: '👥', component: AdminUsers },
  { id: 'parcels', icon: '📦', component: AdminParcels },
  { id: 'flights', icon: '✈️', component: AdminFlights },
  { id: 'groups', icon: '💬', component: AdminGroups },
  { id: 'reports', icon: '🚩', component: AdminReports },
  { id: 'payments', icon: '⭐', component: AdminPayments },
  { id: 'support', icon: '🆘', component: AdminSupport },
  { id: 'broadcast', icon: '📣', component: AdminBroadcast },
]

// Допустимые идентификаторы разделов
const tabIds = tabs.map((tab) => tab.id)

// Раздел берём из query (?tab=), по умолчанию — статистика
const resolveTab = () => (tabIds.includes(route.query.tab) ? route.query.tab : 'stats')
const activeTab = ref(resolveTab())

// Состояние проверки доступа: loading / ok / denied / error
const phase = ref('loading')

// Компонент активного раздела
const activeComponent = computed(() => tabs.find((tab) => tab.id === activeTab.value)?.component)

// Переключение раздела — пишем в query, чтобы ссылки на раздел работали
const switchTab = (id) => {
  if (id === activeTab.value) return
  haptic.impact('light')
  activeTab.value = id
  router.replace({ query: { ...route.query, tab: id, thread: undefined } })
}

// Диплинк на раздел меняет query без перемонтирования экрана
watch(() => route.query.tab, () => {
  activeTab.value = resolveTab()
})

// Возврат на главную из состояния «нет доступа»
const goHome = () => {
  router.push({ name: 'home' })
}

// Проверяем доступ перед показом панели
onMounted(async () => {
  try {
    await adminApi.me()
    phase.value = 'ok'
  } catch (e) {
    // 401/403 — не админ, остальное — ошибка сети
    phase.value = [401, 403].includes(e?.response?.status) ? 'denied' : 'error'
  }
})
</script>

<template>
  <div class="admin-page">
    <!-- Заголовок панели -->
    <PageHeader :title="t('admin_title')" show-back />

    <!-- Проверка доступа -->
    <div v-if="phase === 'loading'" class="state">
      <p class="state-text">{{ t('admin_loading') }}</p>
    </div>

    <!-- Нет доступа -->
    <div v-else-if="phase === 'denied'" class="state">
      <span class="state-icon">🔒</span>
      <p class="state-text">{{ t('admin_denied') }}</p>
      <button class="btn btn-primary" @click="goHome">{{ t('admin_go_home') }}</button>
    </div>

    <!-- Ошибка сети -->
    <div v-else-if="phase === 'error'" class="state">
      <span class="state-icon">⚠️</span>
      <p class="state-text">{{ t('admin_error') }}</p>
    </div>

    <!-- Панель -->
    <template v-else>
      <!-- Горизонтальная лента разделов -->
      <div class="tabs-row">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="chip tab-chip"
          :class="{ active: activeTab === tab.id }"
          @click="switchTab(tab.id)"
        >
          <span class="tab-icon">{{ tab.icon }}</span>
          {{ t('admin_tab_' + tab.id) }}
        </button>
      </div>

      <!-- Активный раздел -->
      <div class="tab-content">
        <component :is="activeComponent" />
      </div>
    </template>
  </div>
</template>

<style scoped>
.admin-page {
  min-height: 100vh;
  padding-bottom: 24px;
}

/* Лента разделов со скроллом по горизонтали */
.tabs-row {
  display: flex;
  gap: 8px;
  padding: 8px 16px 12px;
  overflow-x: auto;
  scrollbar-width: none;
}

.tabs-row::-webkit-scrollbar {
  display: none;
}

.tab-chip {
  flex-shrink: 0;
  gap: 6px;
}

.tab-icon {
  font-size: 13px;
}

.tab-content {
  padding: 0 16px;
}

/* Состояния загрузки/ошибки */
.state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 48px 24px;
  text-align: center;
}

.state-icon {
  font-size: 40px;
}

.state-text {
  font-size: 14px;
  color: var(--text-2);
}
</style>
