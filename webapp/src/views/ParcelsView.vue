<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { useParcelsStore } from '@/stores/parcels'
import PageHeader from '@/components/layout/PageHeader.vue'

const router = useRouter()
const { t } = useLocale()
const { haptic } = useTelegram()
const parcelsStore = useParcelsStore()

// Активный таб: active / completed
const activeTab = ref('active')

// Переключение табов
const switchTab = (tab) => {
  haptic.selection()
  activeTab.value = tab
}

// Фильтрованный список посылок по статусу
const filteredParcels = computed(() => {
  if (activeTab.value === 'active') {
    // Активные: все кроме delivered и cancelled
    return parcelsStore.myParcels.filter(
      (p) => !['delivered', 'cancelled'].includes(p.status)
    )
  }
  // Завершённые: delivered или cancelled
  return parcelsStore.myParcels.filter(
    (p) => ['delivered', 'cancelled'].includes(p.status)
  )
})

// Маппинг статусов на цвета бейджей
const statusColors = {
  pending: '#FFD60A',
  accepted: '#30D158',
  handed: '#6C5CE7',
  in_transit: '#0A84FF',
  delivered: '#30D158',
  cancelled: '#FF453A',
}

// Получить цвет бейджа по статусу
const getStatusColor = (status) => statusColors[status] || '#8E8E93'

// Переход к трекингу посылки
const goToTracking = (parcel) => {
  haptic.impact('light')
  router.push({ name: 'tracking', params: { id: parcel.id } })
}

// Переход к созданию посылки
const goCreateParcel = () => {
  haptic.impact('medium')
  router.push({ name: 'home' })
}

// Загрузка данных при монтировании
onMounted(() => {
  parcelsStore.fetchMyParcels()
})
</script>

<template>
  <div class="parcels-page">
    <!-- Заголовок страницы -->
    <PageHeader :title="t('my_parcels')" />

    <!-- Табы: активные / завершённые -->
    <div class="tabs">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'active' }"
        @click="switchTab('active')"
      >
        {{ t('tab_active') }}
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'completed' }"
        @click="switchTab('completed')"
      >
        {{ t('tab_completed') }}
      </button>
    </div>

    <!-- Ошибка загрузки -->
    <div v-if="parcelsStore.error" class="error-state">
      <span class="error-icon">&#x26A0;&#xFE0F;</span>
      <p class="error-text">{{ parcelsStore.error }}</p>
      <button class="btn btn-primary" @click="parcelsStore.fetchMyParcels()">
        {{ t('retry') }}
      </button>
    </div>

    <!-- Загрузка -->
    <div v-else-if="parcelsStore.loading" class="parcels-list">
      <div v-for="i in 3" :key="i" class="card skeleton-card">
        <div class="skeleton" style="width: 70%; height: 16px; margin-bottom: 8px"></div>
        <div class="skeleton" style="width: 50%; height: 14px; margin-bottom: 8px"></div>
        <div class="skeleton" style="width: 30%; height: 12px"></div>
      </div>
    </div>

    <!-- Список посылок -->
    <div v-else-if="filteredParcels.length > 0" class="parcels-list">
      <div
        v-for="parcel in filteredParcels"
        :key="parcel.id"
        class="card parcel-card"
        @click="goToTracking(parcel)"
      >
        <!-- Верхняя строка: маршрут и бейдж статуса -->
        <div class="parcel-top">
          <span class="parcel-route">
            {{ parcel.from_city }} → {{ parcel.to_city }}
          </span>
          <span
            class="status-badge"
            :style="{ background: getStatusColor(parcel.status) + '20', color: getStatusColor(parcel.status) }"
          >
            {{ t('status_' + parcel.status) }}
          </span>
        </div>

        <!-- Средняя строка: описание -->
        <p class="parcel-desc">{{ parcel.description }}</p>

        <!-- Нижняя строка: вес и цена -->
        <div class="parcel-bottom">
          <span class="parcel-weight">{{ parcel.weight }} {{ t('kg') }}</span>
          <span class="parcel-price">${{ parcel.price }}</span>
        </div>
      </div>
    </div>

    <!-- Пустое состояние -->
    <div v-else class="empty-state">
      <span class="empty-icon">📦</span>
      <p class="empty-text">{{ t('no_parcels') }}</p>
      <button class="btn btn-primary" @click="goCreateParcel">
        {{ t('create_parcel') }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.parcels-page {
  padding-bottom: 80px;
}

/* Табы переключения */
.tabs {
  display: flex;
  gap: 4px;
  padding: 0 16px 16px;
  background: #1C1C1E;
  border-radius: 10px;
  margin: 0 16px 16px;
}

.tab-btn {
  flex: 1;
  padding: 10px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  background: transparent;
  color: #8E8E93;
}

.tab-btn.active {
  background: #6C5CE7;
  color: #fff;
}

.tab-btn:active {
  transform: scale(0.97);
}

/* Список посылок */
.parcels-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 16px;
}

/* Карточка посылки */
.parcel-card {
  padding: 14px;
  cursor: pointer;
  transition: transform 0.1s;
}

.parcel-card:active {
  transform: scale(0.98);
}

/* Маршрут и статус */
.parcel-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.parcel-route {
  font-size: 15px;
  font-weight: 600;
  color: #fff;
}

/* Бейдж статуса */
.status-badge {
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
}

/* Описание посылки */
.parcel-desc {
  font-size: 13px;
  color: #8E8E93;
  margin-bottom: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Вес и цена */
.parcel-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.parcel-weight {
  font-size: 13px;
  color: #8E8E93;
}

.parcel-price {
  font-size: 15px;
  font-weight: 700;
  color: #6C5CE7;
}

/* Скелетон загрузки */
.skeleton-card {
  padding: 16px;
}

/* Состояние ошибки */
.error-state {
  text-align: center;
  padding: 60px 20px;
}

.error-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 12px;
}

.error-text {
  font-size: 15px;
  color: #FF453A;
  margin-bottom: 20px;
}

/* Пустое состояние */
.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 12px;
}

.empty-text {
  font-size: 15px;
  color: #8E8E93;
  margin-bottom: 20px;
}
</style>
