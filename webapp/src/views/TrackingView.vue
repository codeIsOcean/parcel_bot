<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { parcelsApi } from '@/api/parcels'
import PageHeader from '@/components/layout/PageHeader.vue'

const route = useRoute()
const { t } = useLocale()
const { haptic } = useTelegram()

// ID посылки из параметров маршрута
const props = defineProps({
  id: { type: [String, Number], required: true },
})

// Загрузка данных
const loading = ref(true)

// Ошибка загрузки
const error = ref(null)

// Данные посылки (загружаются из API)
const parcel = ref({
  id: props.id,
  from_city: '',
  to_city: '',
  description: '',
  weight: 0,
  price: 0,
  status: '',
  created_at: null,
})

// Данные перевозчика (загружаются из ответа API посылки)
const traveler = ref(null)

// Порядок статусов для определения завершённости шагов
const statusOrder = ['pending', 'accepted', 'handed', 'in_transit', 'delivered']

// Индекс текущего статуса
const currentStatusIndex = computed(() =>
  statusOrder.indexOf(parcel.value.status)
)

// Шаги трекинга — определяем завершённость по текущему статусу
const trackingSteps = computed(() => [
  {
    key: 'pending',
    label: t('tracking_created'),
    icon: '📝',
    completed: currentStatusIndex.value >= 0,
  },
  {
    key: 'accepted',
    label: t('tracking_accepted'),
    icon: '✅',
    completed: currentStatusIndex.value >= 1,
  },
  {
    key: 'handed',
    label: t('tracking_handed'),
    icon: '🤝',
    completed: currentStatusIndex.value >= 2,
  },
  {
    key: 'in_transit',
    label: t('tracking_in_transit'),
    icon: '✈️',
    completed: currentStatusIndex.value >= 3,
  },
  {
    key: 'delivered',
    label: t('tracking_delivered'),
    icon: '📦',
    completed: currentStatusIndex.value >= 4,
  },
])

// Текущий активный шаг (последний завершённый)
const currentStepIndex = computed(() => {
  let last = -1
  trackingSteps.value.forEach((step, i) => {
    if (step.completed) last = i
  })
  return last
})

// Загрузка данных посылки из API
onMounted(async () => {
  try {
    const data = await parcelsApi.getById(props.id)
    // Обновляем данные посылки
    parcel.value = data
    // Устанавливаем данные перевозчика из плоских полей ответа
    if (data.traveler_id) {
      traveler.value = {
        name: data.traveler_name || '',
        rating: data.traveler_rating || 0,
      }
    }
  } catch (e) {
    error.value = e.message || t('error_loading')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="tracking-page">
    <!-- Заголовок -->
    <PageHeader
      :title="t('tracking_title')"
      :subtitle="`${parcel.from_city} → ${parcel.to_city}`"
      show-back
    />

    <!-- Загрузка -->
    <div v-if="loading" class="loading-state">
      <div class="skeleton" style="width: 80%; height: 20px; margin: 20px auto 16px"></div>
      <div class="skeleton" style="width: 60%; height: 16px; margin: 0 auto 32px"></div>
      <div v-for="i in 5" :key="i" class="skeleton-step">
        <div class="skeleton" style="width: 32px; height: 32px; border-radius: 50%"></div>
        <div class="skeleton" style="flex: 1; height: 14px"></div>
      </div>
    </div>

    <div v-else class="tracking-content">
      <!-- Информация о посылке -->
      <div class="card parcel-info">
        <div class="info-row">
          <span class="info-label">{{ t('parcel_description') }}</span>
          <span class="info-value">{{ parcel.description }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">{{ t('parcel_weight') }}</span>
          <span class="info-value">{{ parcel.weight }} {{ t('kg') }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">{{ t('your_price') }}</span>
          <span class="info-value price">${{ parcel.price }}</span>
        </div>
      </div>

      <!-- Информация о перевозчике -->
      <div class="card traveler-info" v-if="traveler">
        <div class="traveler-header">
          <!-- Аватар перевозчика -->
          <div class="avatar">{{ (traveler.name || '?')[0] }}</div>
          <div class="traveler-details">
            <span class="traveler-name">{{ traveler.name }}</span>
            <span class="traveler-meta">
              ★ {{ traveler.rating || 0 }}
            </span>
          </div>
        </div>
      </div>

      <!-- Вертикальный таймлайн трекинга -->
      <div class="timeline">
        <div
          v-for="(step, index) in trackingSteps"
          :key="step.key"
          class="timeline-step"
          :class="{
            completed: step.completed,
            current: index === currentStepIndex,
            pending: !step.completed,
          }"
        >
          <!-- Линия соединения (не для первого) -->
          <div class="timeline-line" v-if="index > 0">
            <div
              class="timeline-line-fill"
              :class="{ filled: step.completed }"
            ></div>
          </div>

          <!-- Точка таймлайна -->
          <div class="timeline-dot">
            <span class="timeline-icon">{{ step.icon }}</span>
          </div>

          <!-- Контент шага -->
          <div class="timeline-body">
            <span class="timeline-label">{{ step.label }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tracking-page {
  padding-bottom: 32px;
}

.tracking-content {
  padding: 0 16px;
}

/* Загрузка — скелетон шагов */
.loading-state {
  padding: 0 16px;
}

.skeleton-step {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
}

/* Карточка информации о посылке */
.parcel-info {
  margin-bottom: 12px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
}

.info-row:not(:last-child) {
  border-bottom: 1px solid #2C2C2E;
}

.info-label {
  font-size: 13px;
  color: #8E8E93;
}

.info-value {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}

.info-value.price {
  color: #6C5CE7;
}

/* Карточка перевозчика */
.traveler-info {
  margin-bottom: 20px;
}

.traveler-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #6C5CE7;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 700;
  flex-shrink: 0;
}

.traveler-details {
  display: flex;
  flex-direction: column;
}

.traveler-name {
  font-size: 15px;
  font-weight: 600;
  color: #fff;
}

.traveler-meta {
  font-size: 13px;
  color: #FFD60A;
  margin-top: 2px;
}

.traveler-flight {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 10px;
  border-top: 1px solid #2C2C2E;
}

.flight-label {
  font-size: 13px;
  color: #8E8E93;
}

.flight-value {
  font-size: 13px;
  color: #fff;
  font-weight: 500;
}

/* Вертикальный таймлайн */
.timeline {
  padding: 0 4px;
}

.timeline-step {
  display: flex;
  align-items: flex-start;
  position: relative;
  padding-bottom: 4px;
}

/* Линия соединения между шагами */
.timeline-line {
  position: absolute;
  left: 18px;
  top: -20px;
  width: 2px;
  height: 20px;
  background: #2C2C2E;
  overflow: hidden;
}

.timeline-line-fill {
  width: 100%;
  height: 100%;
  background: #2C2C2E;
  transition: background 0.3s;
}

.timeline-line-fill.filled {
  background: #6C5CE7;
}

/* Точка таймлайна */
.timeline-dot {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: #2C2C2E;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 2px solid #3A3A3C;
  transition: all 0.3s;
  z-index: 1;
}

.timeline-step.completed .timeline-dot {
  background: rgba(108, 92, 231, 0.15);
  border-color: #6C5CE7;
}

.timeline-step.current .timeline-dot {
  background: #6C5CE7;
  border-color: #6C5CE7;
  box-shadow: 0 0 12px rgba(108, 92, 231, 0.4);
}

.timeline-icon {
  font-size: 16px;
}

/* Текст шага */
.timeline-body {
  flex: 1;
  padding: 8px 0 16px 12px;
  display: flex;
  flex-direction: column;
}

.timeline-label {
  font-size: 14px;
  font-weight: 600;
  color: #8E8E93;
}

.timeline-step.completed .timeline-label,
.timeline-step.current .timeline-label {
  color: #fff;
}

.timeline-date {
  font-size: 12px;
  color: #636366;
  margin-top: 2px;
}

.timeline-step.completed .timeline-date {
  color: #8E8E93;
}
</style>
