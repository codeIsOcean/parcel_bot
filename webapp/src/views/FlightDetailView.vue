<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { useAuthStore } from '@/stores/auth'
import { flightsApi } from '@/api/flights'
import PageHeader from '@/components/layout/PageHeader.vue'
import RatingStars from '@/components/shared/RatingStars.vue'

const props = defineProps({
  id: { type: [String, Number], required: true },
})

const router = useRouter()
const { t } = useLocale()
const { haptic } = useTelegram()
const authStore = useAuthStore()

// Рейс
const flight = ref(null)
const loading = ref(true)
const error = ref('')

// Подтверждение отмены в два касания
const confirmCancel = ref(false)

// Свой ли рейс
const isOwner = computed(() => flight.value && flight.value.traveler_id === authStore.user?.id)

// Рейс принимает заявки
const isActive = computed(() => flight.value?.status === 'active')

const formatDate = (value) => (value ? new Date(value).toLocaleDateString('ru-RU') : '')

const load = async () => {
  try {
    flight.value = await flightsApi.getById(props.id)
  } catch {
    error.value = t('error_loading')
  } finally {
    loading.value = false
  }
}

// Отправить посылку этим рейсом: форма посылки с заявкой на рейс
const sendWithFlight = () => {
  haptic.impact('medium')
  router.push({
    name: 'send-parcel',
    query: {
      from: flight.value.from_city,
      to: flight.value.to_city,
      traveler_id: flight.value.traveler_id,
      flight_id: flight.value.id,
    },
  })
}

// Отменить свой рейс (двойное касание)
const cancel = async () => {
  if (!confirmCancel.value) {
    confirmCancel.value = true
    haptic.impact('light')
    return
  }
  try {
    flight.value = await flightsApi.cancel(props.id)
    haptic.notification('success')
  } catch {
    error.value = t('error_generic')
    haptic.notification('error')
  } finally {
    confirmCancel.value = false
  }
}

const openProfile = () => router.push({ name: 'user-profile', params: { id: flight.value.traveler_id } })
const openRequests = () => router.push({ name: 'requests' })

onMounted(load)
</script>

<template>
  <div class="flight-page">
    <PageHeader :title="t('flight_title')" show-back />

    <div v-if="loading" class="state-text">{{ t('loading') }}</div>
    <div v-else-if="!flight" class="state-text">{{ error || t('not_found') }}</div>

    <div v-else class="flight-content">
      <!-- Карточка рейса -->
      <div class="card">
        <div class="route-row">
          <span class="route">✈️ {{ flight.from_city }} → {{ flight.to_city }}</span>
          <span class="status-badge" :class="'st-' + flight.status">{{ t('status_flight_' + flight.status) }}</span>
        </div>
        <div class="meta-row">
          <span>📅 {{ formatDate(flight.flight_date) }}</span>
          <span>⚖️ {{ flight.available_kg }} / {{ flight.total_kg }} {{ t('kg') }}</span>
          <span>💰 ${{ flight.price_per_kg }}{{ t('per_kg') }}</span>
        </div>
        <p v-if="flight.notes" class="notes">{{ flight.notes }}</p>
      </div>

      <!-- Перевозчик -->
      <div class="card person-card" @click="openProfile">
        <div class="person-avatar">{{ (flight.traveler_name || '?')[0] }}</div>
        <div class="person-info">
          <span class="person-label">{{ t('traveler') }}</span>
          <span class="person-name">{{ flight.traveler_name }} <span v-if="flight.traveler_verified">✓</span></span>
          <RatingStars :value="flight.traveler_rating || 0" size="sm" />
          <span class="person-label">{{ t('trips_count', { count: flight.traveler_trips || 0 }) }}</span>
        </div>
      </div>

      <p v-if="error" class="error-text">{{ error }}</p>

      <!-- Отправитель: отправить этим рейсом -->
      <button v-if="!isOwner && isActive" class="btn btn-primary btn-block" @click="sendWithFlight">
        {{ t('send_with_flight') }}
      </button>
      <p v-else-if="!isOwner" class="state-text">{{ t('flight_closed') }}</p>

      <!-- Владелец: заявки и отмена -->
      <template v-if="isOwner">
        <button class="btn btn-primary btn-block" @click="openRequests">
          {{ t('incoming_requests') }} ({{ flight.requests_count }})
        </button>
        <button v-if="isActive" class="btn btn-block" :class="confirmCancel ? 'btn-danger' : 'btn-outline'" @click="cancel">
          {{ confirmCancel ? t('confirm_cancel') : t('cancel_flight') }}
        </button>
      </template>
    </div>
  </div>
</template>

<style scoped>
.flight-page { padding-bottom: 32px; }
.flight-content { padding: 0 16px; display: flex; flex-direction: column; gap: 12px; }
.state-text { padding: 24px 16px; text-align: center; color: var(--text-2); font-size: 14px; }
.error-text { color: var(--danger); font-size: 13px; }
.route-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 8px; }
.route { font-size: 17px; font-weight: 700; color: var(--text-1); }
.meta-row { display: flex; flex-wrap: wrap; gap: 12px; font-size: 13px; color: var(--text-2); }
.notes { margin-top: 10px; font-size: 14px; color: var(--text-1); white-space: pre-wrap; }
.status-badge { padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; background: var(--surface-2); color: var(--text-2); }
.st-active { background: #16C78420; color: #16C784; }
.st-cancelled { background: #FF3B3020; color: #FF3B30; }
.person-card { display: flex; align-items: center; gap: 12px; cursor: pointer; }
.person-avatar { width: 44px; height: 44px; border-radius: 50%; background: var(--primary); color: var(--on-accent); display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 18px; flex-shrink: 0; }
.person-info { display: flex; flex-direction: column; gap: 2px; }
.person-label { font-size: 12px; color: var(--text-3); }
.person-name { font-size: 15px; font-weight: 600; color: var(--text-1); }
</style>
