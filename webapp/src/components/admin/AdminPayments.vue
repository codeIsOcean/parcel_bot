<script setup>
import { ref, onMounted } from 'vue'
import { useLocale } from '@/composables/useLocale'
import { adminApi } from '@/api/admin'

const { t } = useLocale()

// Список и пагинация
const items = ref([])
const total = ref(0)
const page = ref(1)
const limit = 30
const loading = ref(false)
const error = ref('')

// Дата и время
const fmtDate = (value) => (value ? new Date(value).toLocaleString('ru-RU') : '—')

// Цвет бейджа статуса платежа
const statusClass = (s) => ({
  completed: 'badge-green',
  pending: 'badge-yellow',
  failed: 'badge-red',
  refunded: 'badge-purple',
}[s] || '')

// Сумма в удобном виде: звёзды, TON или доллары
const amountText = (p) => {
  if (p.amount_stars) return `${p.amount_stars} ⭐`
  if (p.amount_ton) return `${p.amount_ton} TON`
  return `$${p.amount}`
}

// Первая страница
const load = async () => {
  loading.value = true
  error.value = ''
  page.value = 1
  try {
    const data = await adminApi.payments({ page: page.value, limit })
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
    const data = await adminApi.payments({ page: page.value, limit })
    items.value = [...items.value, ...data.items]
    total.value = data.total
  } catch {
    page.value -= 1
  }
}

onMounted(load)
</script>

<template>
  <div class="payments">
    <p v-if="error" class="error-text">{{ error }}</p>
    <p v-if="loading" class="muted">{{ t('admin_loading') }}</p>
    <p v-else-if="!items.length" class="muted">{{ t('admin_empty') }}</p>

    <!-- Карточка платежа -->
    <div v-for="p in items" :key="p.id" class="card pay-card">
      <div class="pay-top">
        <span class="pay-amount">{{ amountText(p) }}</span>
        <span class="badge" :class="statusClass(p.status)">{{ t('admin_pay_status_' + p.status) }}</span>
      </div>
      <div class="pay-meta">
        <span>👤 {{ p.user_name || p.user_id }}</span>
        <span>{{ t('admin_pay_method_' + p.method) }} · {{ t('admin_pay_kind_' + p.kind) }}</span>
      </div>
      <div class="pay-meta">
        <span>#{{ p.id }} · {{ fmtDate(p.created_at) }}</span>
        <span v-if="p.completed_at">✓ {{ fmtDate(p.completed_at) }}</span>
      </div>
    </div>

    <button v-if="items.length < total" class="btn btn-secondary btn-block" @click="loadMore">
      {{ t('admin_load_more') }} ({{ items.length }}/{{ total }})
    </button>
  </div>
</template>

<style scoped>
.payments {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.pay-card {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pay-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pay-amount {
  font-size: 16px;
  font-weight: 700;
  color: var(--primary);
}

.pay-meta {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  color: var(--text-2);
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
