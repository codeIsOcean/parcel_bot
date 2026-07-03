<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { useAuthStore } from '@/stores/auth'
import { useFlightsStore } from '@/stores/flights'
import { useParcelsStore } from '@/stores/parcels'
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

// City picker
const showCityPicker = ref(false)
const cityPickerTarget = ref('from') // 'from' или 'to'

// Популярные маршруты (загружаются из API поиска рейсов)
const popularRoutes = computed(() => {
  // Формируем список популярных маршрутов из результатов поиска
  return flightsStore.searchResults.slice(0, 6).map((flight, index) => ({
    id: flight.id || index + 1,
    from_city: flight.from_city,
    to_city: flight.to_city,
    travelers_count: flight.requests_count || 0,
  }))
})

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
    // Для отправителя: загружаем популярные маршруты (публичный)
    // и посылки (только если авторизован)
    const tasks = [flightsStore.searchFlights()]
    if (authStore.isAuthenticated) {
      tasks.push(parcelsStore.fetchMyParcels({ status: 'active' }))
    }
    await Promise.all(tasks)
  } else if (authStore.isAuthenticated) {
    // Для перевозчика: загружаем мои рейсы (требует авторизации)
    await flightsStore.fetchMyFlights()
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
            :key="r.id"
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
        <div v-for="flight in myFlights" :key="flight.id" class="card flight-card">
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
  color: #8E8E93;
}

.app-title {
  font-size: 28px;
  font-weight: 800;
  color: #fff;
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
  background: #FF453A;
  border-radius: 50%;
}

.avatar-header {
  width: 38px;
  height: 38px;
  background: #6C5CE7;
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
  border: 1px solid #2C2C2E;
  background: transparent;
  color: #8E8E93;
}

.role-btn.active {
  background: #6C5CE7;
  border-color: #6C5CE7;
  color: #fff;
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
  color: #8E8E93;
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
  background: #2C2C2E;
  border: 1px solid #3A3A3C;
  border-radius: 10px;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  text-align: left;
}

.route-input .placeholder {
  color: #8E8E93;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-green { background: #30D158; }
.dot-red { background: #FF453A; }

.swap-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #2C2C2E;
  border: 1px solid #3A3A3C;
  color: #8E8E93;
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
  color: #fff;
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
  background: linear-gradient(135deg, #6C5CE7, #A29BFE);
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
  color: #fff;
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
  color: #fff;
}

.sub-status {
  font-size: 13px;
  color: #30D158;
  margin-top: 2px;
}

.route-arrow {
  font-size: 20px;
  color: #8E8E93;
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
  color: #fff;
}

.flight-date {
  font-size: 13px;
  color: #8E8E93;
}

.flight-bottom {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
}

.flight-kg {
  font-size: 13px;
  color: #8E8E93;
}
</style>
