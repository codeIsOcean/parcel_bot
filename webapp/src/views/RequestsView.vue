<script setup>
import { ref, computed, onMounted } from 'vue'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { useRouter } from 'vue-router'
import { matchesApi } from '@/api/matches'
import { walletApi } from '@/api/wallet'
import PageHeader from '@/components/layout/PageHeader.vue'

const { t } = useLocale()
const { haptic } = useTelegram()
const router = useRouter()

// Группы заявок по рейсам
const groups = ref([])
// Дневной доступ: один на перевозчика, а не на каждый рейс
const access = ref({})
const loading = ref(true)
// Текст ошибки последнего действия
const error = ref('')
// Пока идёт запрос принятия/отклонения — блокируем кнопки этой заявки
const busyId = ref(null)

// Всего заявок по всем рейсам
const total = computed(() =>
  groups.value.reduce((sum, g) => sum + g.requests.length, 0)
)

// Загрузка входящих заявок
const load = async () => {
  loading.value = true
  error.value = ''
  try {
    const data = await matchesApi.getIncoming()
    groups.value = data.items || []
    access.value = data.access || {}
  } catch {
    // Пустой список лучше, чем сломанный экран
    groups.value = []
    error.value = t('error_generic')
  } finally {
    loading.value = false
  }
}

// Убрать заявку из списка после ответа
const removeRequest = (group, matchId) => {
  group.requests = group.requests.filter((r) => r.id !== matchId)
}

// Принять заявку
const accept = async (group, request) => {
  // Без открытого дня кнопка неактивна — показываем причину вместо запроса
  if (!access.value.can_respond) {
    haptic.notification('warning')
    return
  }
  haptic.impact('light')
  busyId.value = request.id
  error.value = ''
  try {
    await matchesApi.accept(request.id)
    removeRequest(group, request.id)
    haptic.notification('success')
  } catch (err) {
    // 402 — день не оплачен, обновляем состояние доступа
    if (err?.response?.status === 402) {
      access.value.can_respond = false
    } else {
      error.value = t('accept_error')
    }
    haptic.notification('error')
  } finally {
    busyId.value = null
  }
}

// Отклонить заявку — доступно и без оплаты
const decline = async (group, request) => {
  haptic.impact('light')
  busyId.value = request.id
  try {
    await matchesApi.decline(request.id)
    removeRequest(group, request.id)
  } catch {
    error.value = t('error_generic')
  } finally {
    busyId.value = null
  }
}

// Открыть рабочий день: списывает тариф или тратит пробный день
const openDay = async () => {
  if (busyId.value) return
  busyId.value = 'day'
  error.value = ''
  try {
    const data = await walletApi.openDay()
    access.value = data.access || {}
    error.value = t('day_opened')
    haptic.notification('success')
  } catch (err) {
    // Не хватает звёзд — уводим в кабинет пополнения
    if (err?.response?.status === 402) {
      error.value = t('not_enough_stars')
      router.push('/wallet')
    } else {
      error.value = t('error_generic')
    }
    haptic.notification('error')
  } finally {
    busyId.value = null
  }
}

// Рейтинг отправителя строкой
const ratingLabel = (sender) =>
  sender.reviews_count
    ? `⭐ ${sender.rating.toFixed(1)} (${sender.reviews_count})`
    : t('no_reviews')

// Дата рейса в коротком формате
const formatDate = (iso) => {
  const d = new Date(iso)
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

onMounted(load)
</script>

<template>
  <div class="requests-view">
    <PageHeader :title="t('requests_title')" show-back />

    <!-- Загрузка -->
    <div v-if="loading" class="state">{{ t('loading') }}</div>

    <!-- Нет ни одной заявки -->
    <div v-if="!loading && total === 0" class="state empty">
      <div class="empty-icon">📭</div>
      <div class="empty-title">{{ t('requests_empty') }}</div>
      <div class="empty-hint">{{ t('requests_empty_hint') }}</div>
    </div>

    <!-- Состояние рабочего дня: один блок на весь экран -->
    <div v-if="!loading && access.launch_trial" class="banner banner-trial">
      🎁 {{ t('launch_trial_banner') }}
    </div>

    <template v-if="!loading && !access.launch_trial">
      <div v-if="access.can_respond" class="banner banner-trial">
        ✅ {{ t('day_paid_today') }}
        <span v-if="access.trial_days_left">
          · {{ t('day_trial_left', { days: access.trial_days_left }) }}
        </span>
      </div>

      <div v-else class="banner banner-locked">
        <div class="banner-title">🔒 {{ t('day_locked_title') }}</div>
        <div class="banner-hint">
          {{ t('day_locked_hint', { price: access.daily_fee_stars }) }}
        </div>
        <button class="unlock-btn" :disabled="busyId === 'day'" @click="openDay">
          {{ access.trial_days_left
            ? t('day_open_free', { days: access.trial_days_left })
            : t('day_open', { price: access.daily_fee_stars }) }}
        </button>
      </div>
    </template>

    <!-- Заявки по рейсам -->
    <div v-if="!loading && total > 0" class="groups">
      <section v-for="group in groups" :key="group.flight.id" class="group">
        <!-- Рейс, к которому относятся заявки -->
        <header class="flight-head">
          <span class="flight-route">
            {{ group.flight.from_city }} → {{ group.flight.to_city }}
          </span>
          <span class="flight-date">{{ formatDate(group.flight.flight_date) }}</span>
        </header>

        <!-- Список заявок на этот рейс -->
        <article v-for="request in group.requests" :key="request.id" class="request card">
          <div class="request-top">
            <div class="sender">
              <div class="sender-name">{{ request.sender.name }}</div>
              <div class="sender-rating">{{ ratingLabel(request.sender) }}</div>
            </div>
            <div class="request-price">${{ request.parcel.price }}</div>
          </div>

          <div class="parcel-desc">{{ request.parcel.description }}</div>
          <div class="parcel-meta">⚖️ {{ request.parcel.weight }} кг</div>

          <div class="actions">
            <button
              class="btn-accept"
              :class="{ locked: !access.can_respond }"
              :disabled="busyId === request.id"
              @click="accept(group, request)"
            >
              <span v-if="!access.can_respond">🔒</span>
              {{ t('accept') }}
            </button>
            <button
              class="btn-decline"
              :disabled="busyId === request.id"
              @click="decline(group, request)"
            >
              {{ t('decline') }}
            </button>
          </div>
        </article>

        <!-- У рейса нет заявок -->
        <div v-if="group.requests.length === 0" class="group-empty">
          {{ t('requests_empty') }}
        </div>
      </section>
    </div>

    <!-- Ошибка последнего действия -->
    <div v-if="error" class="error-bar">{{ error }}</div>
  </div>
</template>

<style scoped>
.requests-view {
  padding: 0 16px 24px;
}

.state {
  padding: 48px 16px;
  text-align: center;
  color: var(--text-2);
  font-size: 14px;
}

.empty-icon {
  font-size: 40px;
  margin-bottom: 12px;
}

.empty-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-1);
  margin-bottom: 6px;
}

.empty-hint {
  font-size: 13px;
  color: var(--text-2);
  max-width: 280px;
  margin: 0 auto;
  line-height: 1.4;
}

.group {
  margin-bottom: 24px;
}

/* Шапка рейса */
.flight-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 10px;
}

.flight-route {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-1);
}

.flight-date {
  font-size: 13px;
  color: var(--text-2);
}

/* Баннеры состояния доступа */
.banner {
  border-radius: 12px;
  padding: 12px 14px;
  margin-bottom: 12px;
  font-size: 13px;
}

.banner-trial {
  background: rgba(22, 199, 132, 0.12);
  color: var(--success);
  font-weight: 600;
}

.banner-locked {
  background: var(--primary-soft);
  border: 1px solid var(--border);
}

.banner-title {
  font-weight: 700;
  color: var(--text-1);
  margin-bottom: 4px;
}

.banner-hint {
  color: var(--text-2);
  line-height: 1.4;
  margin-bottom: 10px;
}

.unlock-btn {
  width: 100%;
  padding: 10px;
  border: none;
  border-radius: 10px;
  background: var(--primary);
  color: var(--on-accent);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.unlock-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

/* Карточка заявки */
.request {
  margin-bottom: 10px;
}

.request-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 8px;
}

.sender-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-1);
}

.sender-rating {
  font-size: 12px;
  color: var(--text-2);
  margin-top: 2px;
}

.request-price {
  font-size: 17px;
  font-weight: 800;
  color: var(--success);
}

.parcel-desc {
  font-size: 14px;
  color: var(--text-1);
  margin-bottom: 4px;
}

.parcel-meta {
  font-size: 13px;
  color: var(--text-2);
  margin-bottom: 12px;
}

.actions {
  display: flex;
  gap: 8px;
}

.btn-accept,
.btn-decline {
  flex: 1;
  padding: 10px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: opacity 0.2s;
}

.btn-accept {
  background: var(--primary);
  color: var(--on-accent);
}

/* Без оплаты кнопка видна, но не работает */
.btn-accept.locked {
  background: var(--surface-2);
  color: var(--text-3);
  cursor: not-allowed;
}

.btn-decline {
  background: var(--surface-2);
  color: var(--text-1);
}

.btn-accept:disabled,
.btn-decline:disabled {
  opacity: 0.6;
}

.group-empty {
  font-size: 13px;
  color: var(--text-3);
  padding: 4px 2px 8px;
}

.error-bar {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(255, 59, 48, 0.1);
  color: var(--danger);
  font-size: 13px;
  text-align: center;
}
</style>
