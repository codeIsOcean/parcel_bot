<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { useFlightsStore } from '@/stores/flights'
import PageHeader from '@/components/layout/PageHeader.vue'
import TravelerCard from '@/components/shared/TravelerCard.vue'

const route = useRoute()
const router = useRouter()
const { t } = useLocale()
const { haptic } = useTelegram()
const flightsStore = useFlightsStore()

// Маршрут из query параметров
const fromCity = computed(() => route.query.from || '')
const toCity = computed(() => route.query.to || '')

// Активный фильтр
const activeFilter = ref('all')
const filters = computed(() => [
  { id: 'all', label: t('filter_all') },
  { id: 'soon', label: t('filter_soon') },
  { id: 'heavy', label: t('filter_heavy') },
  { id: 'top', label: t('filter_top') },
])

// Загрузка — привязана к store
const loading = computed(() => flightsStore.loading)

// Список попутчиков из store (результаты поиска рейсов)
const travelers = computed(() => flightsStore.searchResults)

// Фильтрация попутчиков
const filteredTravelers = computed(() => {
  let result = [...travelers.value]
  switch (activeFilter.value) {
    case 'soon':
      // Сортировка по дате (ближайшие первые) — сравнение по реальным датам
      return result.sort((a, b) => new Date(a.flight_date) - new Date(b.flight_date))
    case 'heavy':
      // Много кг — сортировка по весу (убывание)
      return result.sort((a, b) => b.available_kg - a.available_kg)
    case 'top':
      // Топ рейтинг — сортировка по рейтингу (убывание)
      return result.sort((a, b) => b.traveler_rating - a.traveler_rating)
    default:
      return result
  }
})

// Выбор фильтра
const setFilter = (filterId) => {
  haptic.selection()
  activeFilter.value = filterId
}

// Выбор попутчика — переход к отправке посылки
const selectTraveler = (traveler) => {
  haptic.impact('light')
  router.push({
    name: 'send-parcel',
    query: {
      from: fromCity.value,
      to: toCity.value,
      traveler_id: traveler.traveler_id,
    },
  })
}

// Загрузка рейсов из API по маршруту
onMounted(async () => {
  await flightsStore.searchFlights({
    from: fromCity.value,
    to: toCity.value,
  })
})
</script>

<template>
  <div class="travelers-page">
    <!-- Заголовок с кнопкой "Назад" -->
    <PageHeader
      :title="t('travelers_title')"
      :subtitle="`${fromCity} → ${toCity}`"
      show-back
    />

    <!-- Фильтры (горизонтальный скролл) -->
    <div class="filters hide-scrollbar">
      <button
        v-for="filter in filters"
        :key="filter.id"
        class="chip"
        :class="{ active: activeFilter === filter.id }"
        @click="setFilter(filter.id)"
      >
        {{ filter.label }}
      </button>
    </div>

    <!-- Список попутчиков -->
    <div class="travelers-list">
      <!-- Загрузка -->
      <template v-if="loading">
        <div v-for="i in 3" :key="i" class="card skeleton-card">
          <div class="skeleton" style="width: 44px; height: 44px; border-radius: 50%"></div>
          <div style="flex: 1">
            <div class="skeleton" style="width: 60%; height: 16px; margin-bottom: 8px"></div>
            <div class="skeleton" style="width: 40%; height: 12px"></div>
          </div>
        </div>
      </template>

      <!-- Пустое состояние -->
      <div v-else-if="filteredTravelers.length === 0" class="empty-state">
        <span class="empty-icon">🔍</span>
        <p>{{ t('no_data') }}</p>
      </div>

      <!-- Карточки попутчиков -->
      <TravelerCard
        v-else
        v-for="traveler in filteredTravelers"
        :key="traveler.id"
        :traveler="traveler"
        @select="selectTraveler"
      />
    </div>
  </div>
</template>

<style scoped>
.travelers-page {
  padding-bottom: 16px;
}

.filters {
  display: flex;
  gap: 8px;
  padding: 0 16px 16px;
  overflow-x: auto;
}

.travelers-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 16px;
}

.skeleton-card {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 16px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #8E8E93;
}

.empty-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 12px;
}
</style>
