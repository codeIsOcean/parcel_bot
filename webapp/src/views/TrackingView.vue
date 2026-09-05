<script setup>
import { ref, computed, onMounted } from 'vue'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { parcelsApi } from '@/api/parcels'
import { reportsApi } from '@/api/reports'
import { mediaApi } from '@/api/media'
import { chatsApi } from '@/api/chats'
import { useRouter } from 'vue-router'
import PageHeader from '@/components/layout/PageHeader.vue'

const { t } = useLocale()
const { haptic } = useTelegram()
const router = useRouter()

// ID посылки из параметров маршрута
const props = defineProps({
  id: { type: [String, Number], required: true },
})

const loading = ref(true)
const error = ref('')

// Данные посылки
const parcel = ref({
  id: props.id,
  from_city: '',
  to_city: '',
  description: '',
  weight: 0,
  price: 0,
  status: '',
})

// Перевозчик
const traveler = ref(null)
// Этапы доставки с бэкенда
const timeline = ref([])
// Код выдачи виден только отправителю
const handoverCode = ref(null)
// Смотрит перевозчик или отправитель
const isTraveler = ref(false)
// Какие действия доступны прямо сейчас
const actions = ref({})
// Идёт запрос действия
const busy = ref(false)

// Ввод кода при закрытии доставки
const showCodeInput = ref(false)
const codeInput = ref('')

// Снимки по этапам
const photos = ref({ parcel: [], handover: [], delivery: [] })
const uploading = ref(false)

// Форма жалобы
const showReport = ref(false)
const reportReason = ref('scam')
const reportComment = ref('')

// Подписи и иконки этапов
const STEP_META = {
  created: { icon: '📝', key: 'tracking_created' },
  accepted: { icon: '✅', key: 'tracking_accepted' },
  handed: { icon: '🤝', key: 'tracking_handed' },
  in_transit: { icon: '✈️', key: 'tracking_in_transit' },
  arrived: { icon: '🛬', key: 'tracking_arrived' },
  delivered: { icon: '📦', key: 'tracking_delivered' },
}

// Причины жалобы
const REPORT_REASONS = ['scam', 'no_show', 'prohibited', 'rude', 'other']

// Этапы для отрисовки
const steps = computed(() =>
  timeline.value.map((step) => ({
    key: step.key,
    icon: STEP_META[step.key]?.icon || '•',
    label: t(STEP_META[step.key]?.key || step.key),
    completed: step.done,
    at: step.at,
  }))
)

// Последний завершённый этап — он подсвечивается как текущий
const currentStepIndex = computed(() => {
  let last = -1
  steps.value.forEach((step, i) => {
    if (step.completed) last = i
  })
  return last
})

// Второй участник сделки — на него можно пожаловаться
const counterpartId = computed(() =>
  isTraveler.value ? parcel.value.sender_id : parcel.value.traveler_id
)

// Загрузка отслеживания
const load = async () => {
  loading.value = true
  error.value = ''
  try {
    const data = await parcelsApi.getTracking(props.id)
    parcel.value = data.parcel
    timeline.value = data.timeline || []
    handoverCode.value = data.handover_code
    isTraveler.value = data.is_traveler
    actions.value = data.actions || {}
    photos.value = data.photos || { parcel: [], handover: [], delivery: [] }

    if (data.parcel.traveler_id) {
      traveler.value = {
        name: data.parcel.traveler_name || '',
        rating: data.parcel.traveler_rating || 0,
      }
    }
  } catch {
    error.value = t('error_loading')
  } finally {
    loading.value = false
  }
}

// Общая обёртка над действиями перевозчика
const runAction = async (fn) => {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    await fn()
    haptic.notification('success')
    await load()
  } catch (err) {
    // 400 с неверным кодом показываем отдельным текстом
    const detail = err?.response?.data?.detail || ''
    error.value = detail.includes('code') ? t('code_invalid') : t('error_generic')
    haptic.notification('error')
  } finally {
    busy.value = false
  }
}

const markHanded = () => runAction(() => parcelsApi.markHanded(props.id))
const markInTransit = () => runAction(() => parcelsApi.markInTransit(props.id))
const markArrived = () => runAction(() => parcelsApi.markArrived(props.id))

// Закрытие доставки кодом
const confirmDelivery = async () => {
  if (!codeInput.value.trim()) return
  await runAction(() => parcelsApi.markDelivered(props.id, codeInput.value.trim()))
  showCodeInput.value = false
  codeInput.value = ''
}

// Прикрепить снимок к этапу доставки
const uploadPhoto = async (event, step) => {
  const file = event.target.files?.[0]
  // Сбрасываем input, иначе повторный выбор того же файла не сработает
  event.target.value = ''
  if (!file) return

  uploading.value = true
  error.value = ''
  try {
    const data = await mediaApi.attachToParcel(props.id, file, step)
    photos.value[step] = data.photos || []
    haptic.notification('success')
  } catch {
    error.value = t('photo_error')
    haptic.notification('error')
  } finally {
    uploading.value = false
  }
}

// Открыть переписку со второй стороной сделки
const openChat = async () => {
  try {
    const data = await chatsApi.start(Number(props.id))
    router.push(`/chats/${data.chat_id}`)
  } catch {
    error.value = t('error_generic')
  }
}

// Отправка жалобы
const sendReport = async () => {
  if (!counterpartId.value) return
  busy.value = true
  try {
    await reportsApi.create({
      target_id: counterpartId.value,
      reason: reportReason.value,
      comment: reportComment.value || null,
      parcel_id: Number(props.id),
    })
    showReport.value = false
    reportComment.value = ''
    haptic.notification('success')
  } catch {
    error.value = t('error_generic')
  } finally {
    busy.value = false
  }
}

onMounted(load)
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

      <!-- Переписка со второй стороной сделки -->
      <button v-if="counterpartId" class="chat-btn" @click="openChat">
        💬 {{ t('open_chat') }}
      </button>

      <!-- Код выдачи: виден только отправителю -->
      <div v-if="handoverCode" class="card code-card">
        <div class="code-title">🔑 {{ t('handover_code_title') }}</div>
        <div class="code-value">{{ handoverCode }}</div>
        <div class="code-hint">{{ t('handover_code_hint') }}</div>
      </div>

      <!-- Действия перевозчика по этапам доставки -->
      <div v-if="isTraveler" class="actions-block">
        <button v-if="actions.can_hand" class="action-btn" :disabled="busy" @click="markHanded">
          🤝 {{ t('action_handed') }}
        </button>
        <button v-if="actions.can_transit" class="action-btn" :disabled="busy" @click="markInTransit">
          🛫 {{ t('action_transit') }}
        </button>
        <button v-if="actions.can_arrive" class="action-btn" :disabled="busy" @click="markArrived">
          🛬 {{ t('action_arrived') }}
        </button>
        <button
          v-if="actions.can_deliver && !showCodeInput"
          class="action-btn"
          :disabled="busy"
          @click="showCodeInput = true"
        >
          📦 {{ t('action_deliver') }}
        </button>

        <!-- Ввод кода получателя -->
        <div v-if="showCodeInput" class="code-input-row">
          <input
            v-model="codeInput"
            class="code-input"
            inputmode="numeric"
            :placeholder="t('enter_code')"
          />
          <button class="action-btn" :disabled="busy" @click="confirmDelivery">
            {{ t('send') }}
          </button>
        </div>
      </div>

      <!-- Ошибка действия -->
      <div v-if="error" class="error-bar">{{ error }}</div>

      <!-- Снимки по этапам -->
      <div v-if="photos.handover.length || photos.delivery.length || isTraveler" class="photos-block">
        <div v-if="photos.handover.length || (isTraveler && actions.can_hand)" class="photo-group">
          <div class="photo-title">{{ t('photos_handover') }}</div>
          <div class="photo-row">
            <img v-for="url in photos.handover" :key="url" :src="url" class="photo" alt="" />
            <label v-if="isTraveler" class="photo-add">
              <input type="file" accept="image/*" hidden @change="uploadPhoto($event, 'handover')" />
              <span>{{ uploading ? t('photo_uploading') : t('add_photo') }}</span>
            </label>
          </div>
        </div>

        <div v-if="photos.delivery.length || (isTraveler && actions.can_deliver)" class="photo-group">
          <div class="photo-title">{{ t('photos_delivery') }}</div>
          <div class="photo-row">
            <img v-for="url in photos.delivery" :key="url" :src="url" class="photo" alt="" />
            <label v-if="isTraveler" class="photo-add">
              <input type="file" accept="image/*" hidden @change="uploadPhoto($event, 'delivery')" />
              <span>{{ uploading ? t('photo_uploading') : t('add_photo') }}</span>
            </label>
          </div>
        </div>
      </div>

      <!-- Вертикальный таймлайн трекинга -->
      <div class="timeline">
        <div
          v-for="(step, index) in steps"
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

      <!-- Жалоба на второго участника сделки -->
      <div v-if="counterpartId" class="report-block">
        <button v-if="!showReport" class="report-btn" @click="showReport = true">
          🚩 {{ t('report_user') }}
        </button>

        <div v-else class="card report-form">
          <div class="report-title">{{ t('report_title') }}</div>
          <label v-for="reason in REPORT_REASONS" :key="reason" class="report-reason">
            <input type="radio" :value="reason" v-model="reportReason" />
            <span>{{ t('report_reason_' + reason) }}</span>
          </label>
          <textarea
            v-model="reportComment"
            class="report-comment"
            rows="3"
            :placeholder="t('report_title')"
          ></textarea>
          <div class="report-actions">
            <button class="report-cancel" @click="showReport = false">{{ t('cancel') }}</button>
            <button class="action-btn" :disabled="busy" @click="sendReport">{{ t('send') }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Кнопка перехода в переписку */
.chat-btn {
  width: 100%;
  padding: 12px;
  margin-bottom: 12px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
  color: var(--text-1);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
}

/* Снимки по этапам */
.photos-block {
  margin-bottom: 16px;
}

.photo-group {
  margin-bottom: 12px;
}

.photo-title {
  font-size: 13px;
  color: var(--text-2);
  margin-bottom: 6px;
}

.photo-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.photo {
  width: 72px;
  height: 72px;
  object-fit: cover;
  border-radius: 10px;
  border: 1px solid var(--border);
}

.photo-add {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  padding: 4px;
  border: 1px dashed var(--border-strong);
  border-radius: 10px;
  color: var(--text-2);
  font-size: 11px;
  text-align: center;
  cursor: pointer;
}

/* Код выдачи */
.code-card {
  margin-bottom: 12px;
  text-align: center;
}

.code-title {
  font-size: 13px;
  color: var(--text-2);
  margin-bottom: 6px;
}

.code-value {
  font-size: 32px;
  font-weight: 800;
  letter-spacing: 6px;
  color: var(--primary);
  margin-bottom: 6px;
}

.code-hint {
  font-size: 12px;
  color: var(--text-2);
  line-height: 1.4;
}

/* Действия перевозчика */
.actions-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.action-btn {
  padding: 12px;
  border: none;
  border-radius: 10px;
  background: var(--primary);
  color: var(--on-accent);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.code-input-row {
  display: flex;
  gap: 8px;
}

.code-input {
  flex: 1;
  padding: 12px;
  border: 1px solid var(--border-strong);
  border-radius: 10px;
  background: var(--surface);
  color: var(--text-1);
  font-size: 16px;
  letter-spacing: 3px;
  text-align: center;
}

.error-bar {
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(255, 59, 48, 0.1);
  color: var(--danger);
  font-size: 13px;
  text-align: center;
}

/* Жалоба */
.report-block {
  margin-top: 20px;
}

.report-btn {
  width: 100%;
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: transparent;
  color: var(--text-2);
  font-size: 14px;
  cursor: pointer;
}

.report-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-1);
  margin-bottom: 10px;
}

.report-reason {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  font-size: 14px;
  color: var(--text-1);
  cursor: pointer;
}

.report-comment {
  width: 100%;
  margin-top: 8px;
  padding: 10px;
  border: 1px solid var(--border-strong);
  border-radius: 10px;
  background: var(--surface);
  color: var(--text-1);
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
}

.report-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.report-cancel {
  flex: 1;
  padding: 12px;
  border: none;
  border-radius: 10px;
  background: var(--surface-2);
  color: var(--text-1);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
}

.report-actions .action-btn {
  flex: 1;
}

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
  border-bottom: 1px solid var(--border);
}

.info-label {
  font-size: 13px;
  color: var(--text-2);
}

.info-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-1);
}

.info-value.price {
  color: var(--primary);
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
  background: var(--primary);
  color: var(--on-accent);
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
  color: var(--text-1);
}

.traveler-meta {
  font-size: 13px;
  color: var(--warning);
  margin-top: 2px;
}

.traveler-flight {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 10px;
  border-top: 1px solid var(--border);
}

.flight-label {
  font-size: 13px;
  color: var(--text-2);
}

.flight-value {
  font-size: 13px;
  color: var(--text-1);
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
  background: var(--surface-2);
  overflow: hidden;
}

.timeline-line-fill {
  width: 100%;
  height: 100%;
  background: var(--surface-2);
  transition: background 0.3s;
}

.timeline-line-fill.filled {
  background: var(--primary);
}

/* Точка таймлайна */
.timeline-dot {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: var(--surface-2);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 2px solid var(--border-strong);
  transition: all 0.3s;
  z-index: 1;
}

.timeline-step.completed .timeline-dot {
  background: rgba(108, 92, 231, 0.15);
  border-color: var(--primary);
}

.timeline-step.current .timeline-dot {
  background: var(--primary);
  border-color: var(--primary);
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
  color: var(--text-2);
}

.timeline-step.completed .timeline-label,
.timeline-step.current .timeline-label {
  color: var(--text-1);
}

.timeline-date {
  font-size: 12px;
  color: var(--text-3);
  margin-top: 2px;
}

.timeline-step.completed .timeline-date {
  color: var(--text-2);
}</style>
