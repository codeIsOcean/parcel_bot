<script setup>
import { ref, onMounted } from 'vue'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { adminApi } from '@/api/admin'

const { t } = useLocale()
const { haptic } = useTelegram()

// Фильтр по статусу и поиск
const status = ref('all')
const statuses = ['all', 'pending', 'accepted', 'handed', 'in_transit', 'delivered', 'cancelled']
const query = ref('')

// Список и пагинация
const items = ref([])
const total = ref(0)
const page = ref(1)
const limit = 20
const loading = ref(false)
const error = ref('')

// Посылка, ожидающая подтверждения отмены (двойное нажатие)
const confirmId = ref(null)

// Дата в коротком виде
const fmtDate = (value) => (value ? new Date(value).toLocaleDateString('ru-RU') : '')

// Цвет бейджа статуса
const statusClass = (s) => ({
  pending: 'badge-yellow',
  accepted: 'badge-purple',
  handed: 'badge-purple',
  in_transit: 'badge-purple',
  delivered: 'badge-green',
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
    const data = await adminApi.parcels(params())
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
    const data = await adminApi.parcels(params())
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

// Отмена: первое нажатие — вопрос, второе — действие
const cancel = async (parcel) => {
  if (confirmId.value !== parcel.id) {
    haptic.impact('light')
    confirmId.value = parcel.id
    return
  }
  try {
    const result = await adminApi.cancelParcel(parcel.id)
    // Обновляем статус в списке без перезагрузки
    items.value = items.value.map((p) => (p.id === parcel.id ? { ...p, status: result.status } : p))
    haptic.notification('success')
  } catch (e) {
    haptic.notification('error')
    const code = e?.response?.data?.detail
    error.value = typeof code === 'string' ? t('admin_err_' + code) : t('admin_error')
  } finally {
    confirmId.value = null
  }
}

// Можно ли отменить — закрытые нельзя
const canCancel = (p) => !['delivered', 'cancelled'].includes(p.status)

onMounted(load)
</script>

<template>
  <div class="list">
    <!-- Поиск -->
    <input v-model="query" class="input" :placeholder="t('admin_search_parcels')" @keyup.enter="load" @blur="load" />

    <!-- Фильтр статуса -->
    <div class="chips">
      <button v-for="s in statuses" :key="s" class="chip" :class="{ active: status === s }" @click="setStatus(s)">
        {{ s === 'all' ? t('admin_filter_all') : t('admin_status_' + s) }}
      </button>
    </div>

    <p v-if="error" class="error-text">{{ error }}</p>
    <p v-if="loading" class="muted">{{ t('admin_loading') }}</p>
    <p v-else-if="!items.length" class="muted">{{ t('admin_empty') }}</p>

    <!-- Карточка посылки -->
    <div v-for="p in items" :key="p.id" class="card item-card">
      <div class="item-top">
        <span class="item-route">#{{ p.id }} · {{ p.from_city }} → {{ p.to_city }}</span>
        <span class="badge" :class="statusClass(p.status)">{{ t('admin_status_' + p.status) }}</span>
      </div>
      <p class="item-desc">{{ p.description }}</p>
      <div class="item-meta">
        <span>{{ p.weight }} {{ t('kg') }} · ${{ p.price }}</span>
        <span>{{ fmtDate(p.created_at) }}</span>
      </div>
      <!-- Стороны сделки -->
      <div class="item-meta">
        <span>📤 {{ p.sender_name || p.sender_id }}</span>
        <span v-if="p.traveler_id">✈️ {{ p.traveler_name || p.traveler_id }}</span>
      </div>
      <!-- Принудительная отмена -->
      <button v-if="canCancel(p)" class="btn btn-sm btn-danger" @click="cancel(p)">
        {{ confirmId === p.id ? t('admin_confirm_cancel') : t('admin_action_cancel') }}
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

.item-desc {
  font-size: 13px;
  color: var(--text-2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
