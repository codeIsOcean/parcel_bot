<script setup>
import { ref, onMounted } from 'vue'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { adminApi } from '@/api/admin'

const { t } = useLocale()
const { haptic } = useTelegram()

// Фильтр по статусу и поиск
const status = ref('all')
const statuses = ['all', 'active', 'full', 'in_transit', 'completed', 'cancelled']
const query = ref('')

// Список и пагинация
const items = ref([])
const total = ref(0)
const page = ref(1)
const limit = 20
const loading = ref(false)
const error = ref('')

// Рейс, ожидающий подтверждения отмены
const confirmId = ref(null)

// Дата в коротком виде
const fmtDate = (value) => (value ? new Date(value).toLocaleDateString('ru-RU') : '')

// Цвет бейджа статуса
const statusClass = (s) => ({
  active: 'badge-green',
  full: 'badge-yellow',
  in_transit: 'badge-purple',
  completed: 'badge-green',
  cancelled: 'badge-red',
}[s] || '')

// Параметры запроса
const params = () => ({
  status: status.value === 'all' ? undefined : status.value,
  q: query.value || undefined,
  page: page.value,
  limit,
})

// Первая страница
const load = async () => {
  loading.value = true
  error.value = ''
  page.value = 1
  confirmId.value = null
  try {
    const data = await adminApi.flights(params())
    items.value = data.items
    total.value = data.total
  } catch {
    error.value = t('admin_error')
  } finally {
    loading.value = false
  }
}

// Следующая страница
const loadMore = async () => {
  page.value += 1
  try {
    const data = await adminApi.flights(params())
    items.value = [...items.value, ...data.items]
    total.value = data.total
  } catch {
    page.value -= 1
  }
}

// Смена фильтра
const setStatus = (s) => {
  haptic.selection()
  status.value = s
  load()
}

// Отмена в два нажатия
const cancel = async (flight) => {
  if (confirmId.value !== flight.id) {
    haptic.impact('light')
    confirmId.value = flight.id
    return
  }
  try {
    const result = await adminApi.cancelFlight(flight.id)
    items.value = items.value.map((f) => (f.id === flight.id ? { ...f, status: result.status } : f))
    haptic.notification('success')
  } catch (e) {
    haptic.notification('error')
    const code = e?.response?.data?.detail
    error.value = typeof code === 'string' ? t('admin_err_' + code) : t('admin_error')
  } finally {
    confirmId.value = null
  }
}

// Закрытый рейс отменять нечего
const canCancel = (f) => !['completed', 'cancelled'].includes(f.status)

onMounted(load)
</script>

<template>
  <div class="list">
    <!-- Поиск -->
    <input v-model="query" class="input" :placeholder="t('admin_search_flights')" @keyup.enter="load" @blur="load" />

    <!-- Фильтр статуса -->
    <div class="chips">
      <button v-for="s in statuses" :key="s" class="chip" :class="{ active: status === s }" @click="setStatus(s)">
        {{ s === 'all' ? t('admin_filter_all') : t('admin_status_' + s) }}
      </button>
    </div>

    <p v-if="error" class="error-text">{{ error }}</p>
    <p v-if="loading" class="muted">{{ t('admin_loading') }}</p>
    <p v-else-if="!items.length" class="muted">{{ t('admin_empty') }}</p>

    <!-- Карточка рейса -->
    <div v-for="f in items" :key="f.id" class="card item-card">
      <div class="item-top">
        <span class="item-route">#{{ f.id }} · {{ f.from_city }} → {{ f.to_city }}</span>
        <span class="badge" :class="statusClass(f.status)">{{ t('admin_status_' + f.status) }}</span>
      </div>
      <div class="item-meta">
        <span>📅 {{ fmtDate(f.flight_date) }}</span>
        <span>{{ f.available_kg }} {{ t('kg') }} · ${{ f.price_per_kg }}{{ t('per_kg') }}</span>
      </div>
      <div class="item-meta">
        <span>✈️ {{ f.traveler_name || f.traveler_id }}</span>
        <span>{{ t('admin_requests') }}: {{ f.requests_count }}</span>
      </div>
      <!-- Принудительная отмена -->
      <button v-if="canCancel(f)" class="btn btn-sm btn-danger" @click="cancel(f)">
        {{ confirmId === f.id ? t('admin_confirm_cancel') : t('admin_action_cancel') }}
      </button>
    </div>

    <button v-if="items.length < total" class="btn btn-secondary btn-block" @click="loadMore">
      {{ t('admin_load_more') }} ({{ items.length }}/{{ total }})
    </button>
  </div>
</template>

<style scoped>
.list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chips {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  scrollbar-width: none;
}

.chips::-webkit-scrollbar {
  display: none;
}

.item-card {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.item-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.item-route {
  font-size: 15px;
  font-weight: 600;
}

.item-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-2);
}

.btn-sm {
  padding: 8px 12px;
  font-size: 13px;
  align-self: flex-start;
}

.error-text {
  color: var(--danger);
  font-size: 13px;
}

.muted {
  color: var(--text-2);
  font-size: 13px;
}
</style>
