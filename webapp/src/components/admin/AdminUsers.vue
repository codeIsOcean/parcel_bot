<script setup>
import { ref, onMounted } from 'vue'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { adminApi } from '@/api/admin'

const { t } = useLocale()
const { haptic } = useTelegram()

// Строка поиска и фильтр
const query = ref('')
const filter = ref('all')
const filters = ['all', 'blocked', 'admins', 'travelers', 'reported']

// Список и пагинация
const items = ref([])
const total = ref(0)
const page = ref(1)
const limit = 20
const loading = ref(false)
const error = ref('')

// Раскрытый пользователь и его детали
const openedId = ref(null)
const detail = ref(null)
const detailLoading = ref(false)

// Форма изменения баланса
const balanceDelta = ref(null)
const balanceNote = ref('')

// Ошибка действия внутри карточки
const actionError = ref('')

// Дата в коротком виде
const fmtDate = (value) => (value ? new Date(value).toLocaleDateString('ru-RU') : '')

// Параметры запроса
const params = () => ({
  q: query.value || undefined,
  only: filter.value === 'all' ? undefined : filter.value,
  page: page.value,
  limit,
})

// Загрузка первой страницы
const load = async () => {
  loading.value = true
  error.value = ''
  page.value = 1
  try {
    const data = await adminApi.users(params())
    items.value = data.items
    total.value = data.total
  } catch {
    error.value = t('admin_error')
  } finally {
    loading.value = false
  }
}

// Догрузка следующей страницы
const loadMore = async () => {
  page.value += 1
  try {
    const data = await adminApi.users(params())
    items.value = [...items.value, ...data.items]
    total.value = data.total
  } catch {
    page.value -= 1
  }
}

// Смена фильтра
const setFilter = (id) => {
  haptic.selection()
  filter.value = id
  load()
}

// Раскрыть карточку и загрузить детали
const toggle = async (user) => {
  haptic.impact('light')
  actionError.value = ''
  if (openedId.value === user.id) {
    openedId.value = null
    detail.value = null
    return
  }
  openedId.value = user.id
  detail.value = null
  detailLoading.value = true
  try {
    detail.value = await adminApi.user(user.id)
  } catch {
    actionError.value = t('admin_error')
  } finally {
    detailLoading.value = false
  }
}

// Обновить пользователя в списке после действия
const replaceUser = (updated) => {
  items.value = items.value.map((u) => (u.id === updated.id ? updated : u))
  if (detail.value) detail.value.user = updated
}

// Общий вызов действия с обработкой ошибок
const run = async (fn) => {
  actionError.value = ''
  try {
    const updated = await fn()
    if (updated?.id) replaceUser(updated)
    haptic.notification('success')
    return updated
  } catch (e) {
    haptic.notification('error')
    const code = e?.response?.data?.detail
    actionError.value = typeof code === 'string' ? t('admin_err_' + code) : t('admin_error')
    return null
  }
}

// Блокировка / разблокировка
const toggleBlock = (user) => run(() => adminApi.block(user.id, !user.is_blocked))

// Галочка проверенного
const toggleVerify = (user) => run(() => adminApi.verify(user.id, !user.is_verified))

// Назначение / снятие админа
const toggleAdmin = (user) => run(() => adminApi.setAdmin(user.id, !user.is_admin))

// Изменение баланса: sign = 1 начислить, -1 списать
const applyBalance = async (user, sign) => {
  const amount = Math.abs(Number(balanceDelta.value) || 0)
  if (!amount) return
  const result = await run(() => adminApi.balance(user.id, { delta: sign * amount, note: balanceNote.value || undefined }))
  if (result) {
    replaceUser({ ...user, balance_stars: result.balance_stars })
    balanceDelta.value = null
    balanceNote.value = ''
  }
}

onMounted(load)
</script>

<template>
  <div class="users">
    <!-- Поиск -->
    <input
      v-model="query"
      class="input"
      :placeholder="t('admin_users_search')"
      @keyup.enter="load"
      @blur="load"
    />

    <!-- Фильтры -->
    <div class="chips">
      <button
        v-for="f in filters"
        :key="f"
        class="chip"
        :class="{ active: filter === f }"
        @click="setFilter(f)"
      >
        {{ t('admin_users_filter_' + f) }}
      </button>
    </div>

    <!-- Ошибка / загрузка / пусто -->
    <p v-if="error" class="error-text">{{ error }}</p>
    <p v-else-if="loading" class="muted">{{ t('admin_loading') }}</p>
    <p v-else-if="!items.length" class="muted">{{ t('admin_empty') }}</p>

    <!-- Список пользователей -->
    <div v-for="user in items" :key="user.id" class="card user-card">
      <!-- Шапка карточки -->
      <div class="user-top" @click="toggle(user)">
        <div class="user-main">
          <span class="user-name">{{ user.first_name }} {{ user.last_name || '' }}</span>
          <span class="user-sub">
            {{ user.username ? '@' + user.username : '#' + user.id }}
            <template v-if="user.phone"> · {{ user.phone }}</template>
          </span>
        </div>
        <div class="badges">
          <span v-if="user.is_blocked" class="badge badge-red">{{ t('admin_badge_blocked') }}</span>
          <span v-if="user.is_admin" class="badge badge-purple">{{ t('admin_badge_admin') }}</span>
          <span v-if="user.is_verified" class="badge badge-green">✓</span>
        </div>
      </div>

      <!-- Краткие метрики -->
      <div class="user-meta">
        <span>{{ t('admin_role_' + user.role) }}</span>
        <span>⭐ {{ (user.rating || 0).toFixed(1) }} ({{ user.reviews_count }})</span>
        <span>{{ user.balance_stars }} ⭐</span>
        <span>{{ fmtDate(user.created_at) }}</span>
      </div>

      <!-- Раскрытые детали -->
      <div v-if="openedId === user.id" class="user-detail">
        <p v-if="detailLoading" class="muted">{{ t('admin_loading') }}</p>

        <template v-if="detail">
          <!-- Посылки пользователя -->
          <div v-if="detail.parcels.length" class="detail-block">
            <div class="detail-title">{{ t('admin_tab_parcels') }}</div>
            <div v-for="p in detail.parcels" :key="p.id" class="detail-row">
              #{{ p.id }} {{ p.from_city }} → {{ p.to_city }} · {{ t('admin_status_' + p.status) }}
            </div>
          </div>
          <!-- Рейсы пользователя -->
          <div v-if="detail.flights.length" class="detail-block">
            <div class="detail-title">{{ t('admin_tab_flights') }}</div>
            <div v-for="f in detail.flights" :key="f.id" class="detail-row">
              #{{ f.id }} {{ f.from_city }} → {{ f.to_city }} · {{ fmtDate(f.flight_date) }} · {{ t('admin_status_' + f.status) }}
            </div>
          </div>
          <!-- Жалобы на пользователя -->
          <div v-if="detail.reports.length" class="detail-block">
            <div class="detail-title">{{ t('admin_tab_reports') }}</div>
            <div v-for="r in detail.reports" :key="r.id" class="detail-row">
              {{ t('admin_reason_' + r.reason) }} · {{ r.author_name }} · {{ fmtDate(r.created_at) }}
            </div>
          </div>
        </template>

        <!-- Действия -->
        <div class="actions">
          <button class="btn btn-sm" :class="user.is_blocked ? 'btn-success' : 'btn-danger'" @click="toggleBlock(user)">
            {{ user.is_blocked ? t('admin_action_unblock') : t('admin_action_block') }}
          </button>
          <button class="btn btn-sm btn-secondary" @click="toggleVerify(user)">
            {{ user.is_verified ? t('admin_action_unverify') : t('admin_action_verify') }}
          </button>
          <!-- Владельца из .env снять нельзя -->
          <button
            v-if="!user.is_env_admin"
            class="btn btn-sm btn-secondary"
            @click="toggleAdmin(user)"
          >
            {{ user.is_admin ? t('admin_action_revoke_admin') : t('admin_action_make_admin') }}
          </button>
        </div>

        <!-- Баланс -->
        <div class="balance-form">
          <input v-model="balanceDelta" type="number" min="1" class="input input-sm" :placeholder="t('admin_balance_amount')" />
          <input v-model="balanceNote" class="input input-sm" :placeholder="t('admin_balance_note')" />
          <div class="balance-btns">
            <button class="btn btn-sm btn-success" @click="applyBalance(user, 1)">+ {{ t('admin_balance_add') }}</button>
            <button class="btn btn-sm btn-danger" @click="applyBalance(user, -1)">− {{ t('admin_balance_charge') }}</button>
          </div>
        </div>

        <p v-if="actionError" class="error-text">{{ actionError }}</p>
      </div>
    </div>

    <!-- Догрузить -->
    <button v-if="items.length < total" class="btn btn-secondary btn-block" @click="loadMore">
      {{ t('admin_load_more') }} ({{ items.length }}/{{ total }})
    </button>
  </div>
</template>

<style scoped>
.users {
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

.user-card {
  padding: 12px;
}

.user-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  cursor: pointer;
}

.user-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.user-name {
  font-size: 15px;
  font-weight: 600;
}

.user-sub {
  font-size: 12px;
  color: var(--text-2);
  word-break: break-all;
}

.badges {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.user-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 10px;
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-2);
}

.user-detail {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detail-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-2);
  text-transform: uppercase;
  margin-bottom: 4px;
}

.detail-row {
  font-size: 13px;
  padding: 3px 0;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.btn-sm {
  padding: 8px 12px;
  font-size: 13px;
}

.balance-form {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.input-sm {
  padding: 8px 12px;
  font-size: 14px;
}

.balance-btns {
  display: flex;
  gap: 6px;
}

.balance-btns .btn {
  flex: 1;
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
