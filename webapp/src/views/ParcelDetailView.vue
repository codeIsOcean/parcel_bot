<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { useAuthStore } from '@/stores/auth'
import { parcelsApi } from '@/api/parcels'
import { flightsApi } from '@/api/flights'
import { matchesApi } from '@/api/matches'
import { chatsApi } from '@/api/chats'
import PageHeader from '@/components/layout/PageHeader.vue'
import RatingStars from '@/components/shared/RatingStars.vue'

const props = defineProps({
  id: { type: [String, Number], required: true },
})

const router = useRouter()
const { t } = useLocale()
const { haptic } = useTelegram()
const authStore = useAuthStore()

// Посылка
const parcel = ref(null)
const loading = ref(true)
const error = ref('')

// Отклики (отправителю — все, перевозчику — свои)
const offers = ref([])

// Мои активные рейсы — чтобы откликнуться одним из них
const myFlights = ref([])
const selectedFlightId = ref(null)
const submitting = ref(false)

// Своя ли посылка
const isOwner = computed(() => parcel.value && parcel.value.sender_id === authStore.user?.id)

// Мой отклик уже есть
const myOffer = computed(() => offers.value.find((o) => o.traveler?.id === authStore.user?.id))

// Посылка ещё ищет перевозчика
const isOpen = computed(() => parcel.value?.status === 'pending')

// Активные отклики отправителю
const pendingOffers = computed(() => offers.value.filter((o) => o.status === 'pending'))

// Цвета статусов
const statusColors = {
  pending: '#F5B301', accepted: '#6C5CE7', handed: '#5AC8FA',
  in_transit: '#007AFF', delivered: '#16C784', cancelled: '#FF3B30',
}

const formatDate = (value) => (value ? new Date(value).toLocaleDateString('ru-RU') : '')

// Загрузка карточки, откликов и своих рейсов
const load = async () => {
  try {
    parcel.value = await parcelsApi.getById(props.id)
    const res = await parcelsApi.getOffers(props.id)
    offers.value = res.items || []
    // Перевозчику нужны его активные рейсы по этому маршруту
    if (!isOwner.value && isOpen.value) {
      const mine = await flightsApi.getMyFlights({ limit: 50 })
      myFlights.value = (mine.items || []).filter((f) => f.status === 'active')
      // Рейс по тому же маршруту выбираем сразу
      const same = myFlights.value.find(
        (f) => f.from_city === parcel.value.from_city && f.to_city === parcel.value.to_city,
      )
      selectedFlightId.value = same?.id || myFlights.value[0]?.id || null
    }
  } catch (e) {
    error.value = t('error_loading')
  } finally {
    loading.value = false
  }
}

// Откликнуться выбранным рейсом
const respond = async () => {
  if (!selectedFlightId.value || submitting.value) return
  haptic.impact('medium')
  submitting.value = true
  try {
    await parcelsApi.offer(props.id, selectedFlightId.value)
    haptic.notification('success')
    await load()
  } catch (e) {
    // 402 — нужен оплаченный день: ведём в кабинет
    if (e?.response?.status === 402) {
      router.push({ name: 'wallet' })
      return
    }
    error.value = e?.response?.data?.detail || t('error_generic')
    haptic.notification('error')
  } finally {
    submitting.value = false
  }
}

// Отправитель принимает или отклоняет отклик
const answer = async (offer, accept) => {
  haptic.impact('medium')
  try {
    if (accept) await matchesApi.accept(offer.id)
    else await matchesApi.decline(offer.id)
    haptic.notification('success')
    await load()
  } catch (e) {
    error.value = e?.response?.data?.detail || t('error_generic')
    haptic.notification('error')
  }
}

// Открыть чат по посылке
const openChat = async () => {
  haptic.impact('light')
  try {
    const chat = await chatsApi.start(props.id)
    router.push({ name: 'chat', params: { id: chat.chat_id } })
  } catch {
    router.push({ name: 'chats' })
  }
}

// Опубликовать рейс под эту посылку
const publishFlight = () => {
  haptic.impact('light')
  router.push({ name: 'publish-flight', query: { from: parcel.value.from_city, to: parcel.value.to_city } })
}

// Отслеживание
const openTracking = () => router.push({ name: 'tracking', params: { id: props.id } })

// Профиль собеседника
const openProfile = (userId) => router.push({ name: 'user-profile', params: { id: userId } })

onMounted(load)
</script>

<template>
  <div class="parcel-page">
    <!-- Заголовок -->
    <PageHeader :title="t('parcel_title')" show-back />

    <!-- Загрузка -->
    <div v-if="loading" class="state-text">{{ t('loading') }}</div>
    <div v-else-if="!parcel" class="state-text">{{ error || t('not_found') }}</div>

    <div v-else class="parcel-content">
      <!-- Карточка посылки -->
      <div class="card">
        <div class="route-row">
          <span class="route">{{ parcel.from_city }} → {{ parcel.to_city }}</span>
          <span class="status-badge" :style="{ background: (statusColors[parcel.status] || '#8E8E93') + '20', color: statusColors[parcel.status] || '#8E8E93' }">
            {{ t('status_' + parcel.status) }}
          </span>
        </div>
        <p class="description">{{ parcel.description }}</p>
        <div class="meta-row">
          <span>⚖️ {{ parcel.weight }} {{ t('kg') }}</span>
          <span>💰 ${{ parcel.accepted_price || parcel.price }}</span>
          <span>📅 {{ formatDate(parcel.created_at) }}</span>
        </div>
      </div>

      <!-- Отправитель (перевозчику) -->
      <div v-if="!isOwner" class="card person-card" @click="openProfile(parcel.sender_id)">
        <div class="person-avatar">{{ (parcel.sender_name || '?')[0] }}</div>
        <div class="person-info">
          <span class="person-label">{{ t('sender') }}</span>
          <span class="person-name">{{ parcel.sender_name }} <span v-if="parcel.sender_verified">✓</span></span>
          <RatingStars :value="parcel.sender_rating || 0" size="sm" />
        </div>
      </div>

      <!-- Перевозчик (отправителю, когда посылку взяли) -->
      <div v-if="isOwner && parcel.traveler_id" class="card person-card" @click="openProfile(parcel.traveler_id)">
        <div class="person-avatar">{{ (parcel.traveler_name || '?')[0] }}</div>
        <div class="person-info">
          <span class="person-label">{{ t('traveler') }}</span>
          <span class="person-name">{{ parcel.traveler_name }}</span>
          <RatingStars :value="parcel.traveler_rating || 0" size="sm" />
        </div>
      </div>

      <p v-if="error" class="error-text">{{ error }}</p>

      <!-- === Перевозчик: откликнуться === -->
      <template v-if="!isOwner && isOpen">
        <div v-if="myOffer" class="card info-card">
          <span>{{ t('offer_sent') }} · {{ t('status_' + myOffer.status) }}</span>
        </div>
        <template v-else>
          <div v-if="myFlights.length" class="card">
            <label class="form-label">{{ t('offer_choose_flight') }}</label>
            <!-- Выбор рейса, которым откликаемся -->
            <select v-model="selectedFlightId" class="input">
              <option v-for="f in myFlights" :key="f.id" :value="f.id">
                {{ f.from_city }} → {{ f.to_city }} · {{ formatDate(f.flight_date) }} · {{ f.available_kg }} {{ t('kg') }}
              </option>
            </select>
            <button class="btn btn-primary btn-block action-btn" :disabled="submitting || !selectedFlightId" @click="respond">
              {{ submitting ? t('loading') : t('offer_respond') }}
            </button>
          </div>
          <div v-else class="card info-card">
            <p>{{ t('offer_no_flights') }}</p>
            <button class="btn btn-primary btn-block action-btn" @click="publishFlight">{{ t('publish_flight') }}</button>
          </div>
        </template>
      </template>

      <!-- Перевозчик, посылка у него — чат и отслеживание -->
      <div v-if="!isOwner && parcel.traveler_id === authStore.user?.id" class="actions">
        <button class="btn btn-primary btn-block" @click="openChat">{{ t('chat_title') }}</button>
        <button class="btn btn-outline btn-block" @click="openTracking">{{ t('track') }}</button>
      </div>

      <!-- === Отправитель: отклики === -->
      <template v-if="isOwner">
        <div class="actions">
          <button v-if="parcel.traveler_id" class="btn btn-primary btn-block" @click="openChat">{{ t('chat_title') }}</button>
          <button class="btn btn-outline btn-block" @click="openTracking">{{ t('track') }}</button>
        </div>

        <h3 class="section-title">{{ t('offers_title') }} ({{ offers.length }})</h3>
        <p v-if="!offers.length" class="state-text">{{ t('offers_empty') }}</p>

        <!-- Карточка отклика -->
        <div v-for="offer in offers" :key="offer.id" class="card offer-card">
          <div class="person-card" @click="openProfile(offer.traveler.id)">
            <div class="person-avatar">{{ (offer.traveler.name || '?')[0] }}</div>
            <div class="person-info">
              <span class="person-name">{{ offer.traveler.name }} <span v-if="offer.traveler.is_verified">✓</span></span>
              <RatingStars :value="offer.traveler.rating || 0" size="sm" />
              <span class="person-label">{{ t('deliveries_count', { count: offer.traveler.deliveries_count }) }}</span>
            </div>
            <span class="status-badge" :style="{ background: (statusColors[offer.status] || '#8E8E93') + '20', color: statusColors[offer.status] || '#8E8E93' }">
              {{ t('status_' + offer.status) }}
            </span>
          </div>
          <div class="meta-row">
            <span>✈️ {{ offer.flight.from_city }} → {{ offer.flight.to_city }}</span>
            <span>📅 {{ formatDate(offer.flight.flight_date) }}</span>
            <span>💰 ${{ offer.flight.price_per_kg }}{{ t('per_kg') }}</span>
          </div>
          <!-- Принять / отклонить — только пока посылка свободна -->
          <div v-if="offer.status === 'pending' && isOpen" class="offer-actions">
            <button class="btn btn-success" @click="answer(offer, true)">{{ t('accept') }}</button>
            <button class="btn btn-secondary" @click="answer(offer, false)">{{ t('decline') }}</button>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.parcel-page { padding-bottom: 32px; }
.parcel-content { padding: 0 16px; display: flex; flex-direction: column; gap: 12px; }
.state-text { padding: 24px 16px; text-align: center; color: var(--text-2); font-size: 14px; }
.error-text { color: var(--danger); font-size: 13px; }
.route-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 8px; }
.route { font-size: 17px; font-weight: 700; color: var(--text-1); }
.description { font-size: 14px; color: var(--text-1); line-height: 1.5; margin-bottom: 10px; white-space: pre-wrap; }
.meta-row { display: flex; flex-wrap: wrap; gap: 12px; font-size: 13px; color: var(--text-2); }
.status-badge { padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; white-space: nowrap; }
.person-card { display: flex; align-items: center; gap: 12px; cursor: pointer; }
.person-avatar { width: 44px; height: 44px; border-radius: 50%; background: var(--primary); color: var(--on-accent); display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 18px; flex-shrink: 0; }
.person-info { display: flex; flex-direction: column; gap: 2px; flex: 1; min-width: 0; }
.person-label { font-size: 12px; color: var(--text-3); }
.person-name { font-size: 15px; font-weight: 600; color: var(--text-1); }
.info-card { color: var(--text-2); font-size: 14px; }
.form-label { display: block; font-size: 13px; color: var(--text-2); margin-bottom: 8px; }
.action-btn { margin-top: 12px; }
.actions { display: flex; flex-direction: column; gap: 8px; }
.section-title { font-size: 16px; font-weight: 700; color: var(--text-1); margin-top: 8px; }
.offer-card { display: flex; flex-direction: column; gap: 10px; }
.offer-actions { display: flex; gap: 8px; }
.offer-actions .btn { flex: 1; }
</style>
