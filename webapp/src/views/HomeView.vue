<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { useAuthStore } from '@/stores/auth'
import { useFlightsStore } from '@/stores/flights'
import { useParcelsStore } from '@/stores/parcels'
import { matchesApi } from '@/api/matches'
import { walletApi } from '@/api/wallet'
import { flightsApi } from '@/api/flights'
import RouteCard from '@/components/shared/RouteCard.vue'
import CityPicker from '@/components/shared/CityPicker.vue'

const router = useRouter()
const { t } = useLocale()
const { user: tgUser, haptic } = useTelegram()
const authStore = useAuthStore()
const flightsStore = useFlightsStore()
const parcelsStore = useParcelsStore()

// Текущая роль (отправитель / перевозчик)
const role = computed(() => authStore.role)

// Города маршрута
const fromCity = ref('')
const toCity = ref('')

// Сколько входящих заявок ждёт ответа (для перевозчика)
const incomingCount = ref(null)

// Баланс в звёздах для карточки кабинета
const balanceStars = ref(null)

// City picker
const showCityPicker = ref(false)
const cityPickerTarget = ref('from') // 'from' или 'to'

// Популярные маршруты — считаются на бэкенде по числу активных рейсов
const popularRoutes = ref([])

// Мои рейсы (для перевозчика) — из store
const myFlights = computed(() => flightsStore.myFlights)

// Переключение роли
const switchRole = (newRole) => {
  haptic.impact('light')
  authStore.switchRole(newRole)
}

// Открыть выбор города
const openCityPicker = (target) => {
  cityPickerTarget.value = target
  showCityPicker.value = true
}

// Выбор города
const onCitySelected = (city) => {
  if (cityPickerTarget.value === 'from') {
    fromCity.value = city
  } else {
    toCity.value = city
  }
}

// Поменять города местами
const swapCities = () => {
  haptic.selection()
  const temp = fromCity.value
  fromCity.value = toCity.value
  toCity.value = temp
}

// Поиск попутчиков
const findTravelers = () => {
  if (fromCity.value && toCity.value) {
    haptic.impact('medium')
    router.push({
      name: 'travelers',
      query: { from: fromCity.value, to: toCity.value },
    })
  }
}

// Опубликовать посылку, не выбирая перевозчика. Для отправителя бесплатно:
// заявка ложится в общий поиск, перевозчики откликаются сами.
const publishParcel = () => {
  // Маршрут не обязателен: города можно выбрать прямо на экране публикации
  haptic.impact('light')
  router.push({
    name: 'send-parcel',
    query: { from: fromCity.value || undefined, to: toCity.value || undefined },
  })
}

// Выбор маршрута из популярных
const selectRoute = (route) => {
  haptic.impact('light')
  router.push({
    name: 'travelers',
    query: { from: route.from_city, to: route.to_city },
  })
}

// Перейти к публикации рейса
const goPublishFlight = () => {
  haptic.impact('medium')
  router.push({ name: 'publish-flight' })
}

// Имя пользователя
const userName = computed(() => {
  return authStore.user?.first_name || tgUser.value?.first_name || 'User'
})

onMounted(async () => {
  // Загрузить данные при монтировании в зависимости от роли
  if (role.value === 'sender') {
    // Для отправителя: популярные маршруты (публичные)
    // и посылки (только если авторизован)
    const tasks = [
      flightsStore.searchFlights(),
      flightsApi.getPopularRoutes(6)
        .then((data) => { popularRoutes.value = data.items || [] })
        // Пустой блок лучше, чем сломанная главная
        .catch(() => { popularRoutes.value = [] }),
    ]
    if (authStore.isAuthenticated) {
      tasks.push(parcelsStore.fetchMyParcels({ status: 'active' }))
    }
    await Promise.all(tasks)
  } else if (authStore.isAuthenticated) {
    // Для перевозчика: рейсы и счётчик входящих заявок
    await flightsStore.fetchMyFlights()
    try {
      const data = await matchesApi.getIncoming()
      incomingCount.value = data.total || 0
    } catch {
      // Счётчик не критичен — молча оставляем прочерк
      incomingCount.value = null
    }
    try {
      const wallet = await walletApi.get()
      balanceStars.value = wallet.balance_stars
    } catch {
      balanceStars.value = null
    }
  }
})
</script>

<template>
  <div class="home-page">
    <!-- Шапка: приветствие + уведомления + аватар -->
    <div class="home-header">
      <div class="header-left">
        <span class="welcome-text">{{ t('welcome') }} 👋</span>
        <h1 class="app-title">{{ t('app_name') }}</h1>
      </div>
      <div class="header-right">
        <!-- Уведомления -->
        <button class="icon-btn" @click="router.push('/settings')">
          🔔
          <span class="notification-dot"></span>
        </button>
        <!-- Аватар -->
        <div class="avatar avatar-header" @click="router.push('/profile')">
          {{ userName[0]?.toUpperCase() || 'U' }}
        </div>
      </div>
    </div>

    <!-- Переключатель ролей: Отправить / Перевезти -->
    <div class="role-switcher">
      <button
        class="role-btn"
        :class="{ active: role === 'sender' }"
        @click="switchRole('sender')"
      >
        📦 {{ t('role_sender') }}
      </button>
      <button
        class="role-btn"
        :class="{ active: role === 'traveler' }"
        @click="switchRole('traveler')"
      >
        ✈️ {{ t('role_traveler') }}
      </button>
    </div>

    <!-- ===== КОНТЕНТ ОТПРАВИТЕЛЯ ===== -->
    <div v-if="role === 'sender'" class="role-content">
      <!-- Главное действие отправителя: опубликовать посылку.
           Стоит первым и выделено цветом — от числа отправителей зависит,
           придут ли перевозчики. Поиск попутчиков идёт следующим шагом. -->
      <div class="publish-parcel-card" @click="publishParcel">
        <span class="publish-parcel-icon">📦</span>
        <div class="publish-parcel-text">
          <div class="publish-parcel-title">{{ t('publish_parcel') }}</div>
          <div class="publish-parcel-sub">{{ t('publish_parcel_sub') }}</div>
          <div class="publish-parcel-desc">{{ t('publish_parcel_desc') }}</div>
        </div>
        <span class="publish-parcel-arrow">›</span>
      </div>

      <!-- Селектор маршрута -->
      <div class="card route-selector">
        <span class="route-label">{{ t('route_label') }}</span>
        <div class="route-inputs">
          <!-- Откуда -->
          <button class="route-input" @click="openCityPicker('from')">
            <span class="dot dot-green"></span>
            <span :class="{ placeholder: !fromCity }">
              {{ fromCity || t('route_from') }}
            </span>
          </button>

          <!-- Кнопка обмена -->
          <button class="swap-btn" @click="swapCities">⇄</button>

          <!-- Куда -->
          <button class="route-input" @click="openCityPicker('to')">
            <span class="dot dot-red"></span>
            <span :class="{ placeholder: !toCity }">
              {{ toCity || t('route_to') }}
            </span>
          </button>
        </div>

        <!-- Кнопка поиска -->
        <button
          class="btn btn-primary btn-block"
          :disabled="!fromCity || !toCity"
          @click="findTravelers"
        >
          {{ t('find_travelers') }}
        </button>
      </div>


      <!-- Популярные маршруты -->
      <div class="section">
        <h2 class="section-title">{{ t('popular_routes') }}</h2>
        <div class="routes-list">
          <RouteCard
            v-for="r in popularRoutes"
            :key="`${r.from_city}-${r.to_city}`"
            :route="r"
            @select="selectRoute"
          />
        </div>
      </div>
    </div>

    <!-- ===== КОНТЕНТ ПЕРЕВОЗЧИКА ===== -->
    <div v-else class="role-content">
      <!-- Кнопка "Опубликовать рейс" -->
      <div class="publish-card" @click="goPublishFlight">
        <span class="publish-icon">✈️</span>
        <div class="publish-text">
          <div class="publish-title">{{ t('publish_flight') }}</div>
          <div class="publish-desc">{{ t('publish_flight_desc') }}</div>
        </div>
      </div>

      <!-- Входящие заявки -->
      <div class="card subscription-card" @click="router.push('/requests')">
        <span class="sub-icon">📩</span>
        <div class="sub-info">
          <div class="sub-title">{{ t('incoming_requests') }}</div>
          <div class="sub-status">
            {{ incomingCount ? t('requests_count', { count: incomingCount }) : t('requests_empty') }}
          </div>
        </div>
        <span class="route-arrow">›</span>
      </div>

      <!-- Кабинет: баланс в звёздах -->
      <div class="card subscription-card" @click="router.push('/wallet')">
        <span class="sub-icon">⭐</span>
        <div class="sub-info">
          <div class="sub-title">{{ t('wallet_title') }}</div>
          <div class="sub-status">
            {{ balanceStars !== null ? `${balanceStars} ⭐` : t('loading') }}
          </div>
        </div>
        <span class="route-arrow">›</span>
      </div>

      <!-- Подписка -->
      <div class="card subscription-card" @click="router.push('/subscription')">
        <span class="sub-icon">⭐</span>
        <div class="sub-info">
          <div class="sub-title">{{ t('subscription') }}</div>
          <div class="sub-status">{{ t('trial_period', { days: 25 }) }}</div>
        </div>
        <span class="route-arrow">›</span>
      </div>

      <!-- Мои рейсы -->
      <div class="section">
        <h2 class="section-title">{{ t('my_flights') }}</h2>
        <!-- Карточка рейса ведёт на его страницу: заявки и отмена -->
        <div v-for="flight in myFlights" :key="flight.id" class="card flight-card" @click="router.push({ name: 'flight', params: { id: flight.id } })">
          <div class="flight-top">
            <span class="flight-route">{{ flight.from_city }} → {{ flight.to_city }}</span>
            <span class="flight-date">{{ flight.flight_date }}</span>
          </div>
          <div class="flight-bottom">
            <span class="flight-kg">{{ t('kg_free', { count: flight.available_kg }) }}</span>
            <span v-if="flight.requests_count" class="badge badge-purple">
              {{ t('requests_count', { count: flight.requests_count }) }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Модалка выбора города -->
    <CityPicker
      :visible="showCityPicker"
      :title="cityPickerTarget === 'from' ? t('route_from') : t('route_to')"
      @select="onCitySelected"
      @close="showCityPicker = false"
    />
  </div>
</template>

<style scoped>
/* Главное действие отправителя. Акцентная заливка, чтобы притягивать взгляд:
   спрос первичен, без посылок перевозчикам нечего возить. */
.publish-parcel-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px;
  margin-bottom: 16px;
  border-radius: 16px;
  background: linear-gradient(135deg, var(--primary), var(--primary-light));
  box-shadow: 0 6px 18px rgba(108, 92, 231, 0.28);
  cursor: pointer;
  transition: transform 0.1s;
}

.publish-parcel-card:active {
  transform: scale(0.98);
}

.publish-parcel-icon {
  font-size: 30px;
  flex-shrink: 0;
}

.publish-parcel-text {
  flex: 1;
  min-width: 0;
}

.publish-parcel-title {
  font-size: 17px;
  font-weight: 800;
  color: var(--on-accent);
  line-height: 1.2;
}

.publish-parcel-sub {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  margin-top: 1px;
}

.publish-parcel-desc {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.75);
  margin-top: 4px;
  line-height: 1.35;
}

.publish-parcel-arrow {
  font-size: 22px;
  color: rgba(255, 255, 255, 0.8);
  flex-shrink: 0;
}

.home-page {
  padding: 16px;
}

/* Шапка */
.home-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.welcome-text {
  font-size: 14px;
  color: var(--text-2);
}

.app-title {
  font-size: 28px;
  font-weight: 800;
  color: var(--text-1);
  margin-top: 2px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.icon-btn {
  position: relative;
  background: none;
  border: none;
  font-size: 22px;
  cursor: pointer;
  padding: 4px;
}

.notification-dot {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 8px;
  height: 8px;
  background: var(--danger);
  border-radius: 50%;
}

.avatar-header {
  width: 38px;
  height: 38px;
  background: var(--primary);
  font-size: 15px;
  cursor: pointer;
}

/* Переключатель ролей */
.role-switcher {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.role-btn {
  flex: 1;
  padding: 10px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text-2);
}

.role-btn.active {
  background: var(--primary);
  border-color: var(--primary);
  color: var(--on-accent);
}

.role-btn:active {
  transform: scale(0.97);
}

/* Селектор маршрута */
.route-selector {
  margin-bottom: 20px;
}

.route-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-2);
  letter-spacing: 0.5px;
  display: block;
  margin-bottom: 10px;
}

.route-inputs {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.route-input {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: var(--surface-2);
  border: 1px solid var(--border-strong);
  border-radius: 10px;
  color: var(--text-1);
  font-size: 14px;
  cursor: pointer;
  text-align: left;
}

.route-input .placeholder {
  color: var(--text-2);
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-green { background: var(--success); }
.dot-red { background: var(--danger); }

.swap-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--surface-2);
  border: 1px solid var(--border-strong);
  color: var(--text-2);
  font-size: 16px;
  cursor: pointer;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Секции */
.section {
  margin-bottom: 20px;
}

.section-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-1);
  margin-bottom: 12px;
}

.routes-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Перевозчик: публикация рейса */
.publish-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px;
  background: linear-gradient(135deg, var(--primary), var(--primary-light));
  border-radius: 16px;
  cursor: pointer;
  margin-bottom: 12px;
  transition: transform 0.1s;
}

.publish-card:active {
  transform: scale(0.98);
}

.publish-icon {
  font-size: 32px;
}

.publish-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--on-accent);
}

.publish-desc {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  margin-top: 2px;
}

/* Подписка */
.subscription-card {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  margin-bottom: 16px;
}

.sub-icon {
  font-size: 28px;
}

.sub-info {
  flex: 1;
}

.sub-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-1);
}

.sub-status {
  font-size: 13px;
  color: var(--success);
  margin-top: 2px;
}

.route-arrow {
  font-size: 20px;
  color: var(--text-2);
}

/* Рейс */
.flight-card {
  margin-bottom: 8px;
}

.flight-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.flight-route {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-1);
}

.flight-date {
  font-size: 13px;
  color: var(--text-2);
}

.flight-bottom {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
}

.flight-kg {
  font-size: 13px;
  color: var(--text-2);
}</style>
