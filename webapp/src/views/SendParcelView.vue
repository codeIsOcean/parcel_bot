<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { useParcelsStore } from '@/stores/parcels'
import PageHeader from '@/components/layout/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const { t } = useLocale()
const { haptic, showMainButton, hideMainButton } = useTelegram()
const parcelsStore = useParcelsStore()

// Маршрут из query
const fromCity = computed(() => route.query.from || '')
const toCity = computed(() => route.query.to || '')

// Форма отправки посылки
const description = ref('')
const weight = ref(null)
const size = ref('medium')
const price = ref(20)
const photoPreview = ref(null)

// Варианты веса (быстрый выбор)
const weightOptions = [1, 2, 3, 5, 10]

// Варианты размера
const sizeOptions = computed(() => [
  { id: 'small', label: t('size_small'), icon: '📱' },
  { id: 'medium', label: t('size_medium'), icon: '📦' },
  { id: 'large', label: t('size_large'), icon: '🧳' },
])

// Валидация формы
const isValid = computed(() => {
  return description.value.trim().length >= 3 && weight.value > 0 && price.value > 0
})

// Быстрый выбор веса
const selectWeight = (w) => {
  haptic.selection()
  weight.value = w
}

// InDriver-style: регулировка цены
const adjustPrice = (delta) => {
  haptic.impact('light')
  const newPrice = price.value + delta
  if (newPrice >= 5) {
    price.value = newPrice
  }
}

// Загрузка фото (эмуляция — в реальности через input[type=file])
const fileInput = ref(null)
const onPhotoSelect = (event) => {
  const file = event.target.files[0]
  if (file) {
    const reader = new FileReader()
    reader.onload = (e) => {
      photoPreview.value = e.target.result
    }
    reader.readAsDataURL(file)
  }
}

// Отправка заявки
const submitting = ref(false)
const submitParcel = async () => {
  if (!isValid.value || submitting.value) return

  haptic.impact('medium')
  submitting.value = true

  try {
    await parcelsStore.createParcel({
      from_city: fromCity.value,
      to_city: toCity.value,
      description: description.value,
      weight: weight.value,
      size: size.value,
      price: price.value,
      traveler_id: route.query.traveler_id,
    })

    // Успех — тактильная обратная связь и переход
    haptic.notification('success')
    router.push({ name: 'parcels' })
  } catch (e) {
    haptic.notification('error')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="send-parcel-page">
    <!-- Заголовок -->
    <PageHeader
      :title="t('send_parcel')"
      :subtitle="`${fromCity} → ${toCity}`"
      show-back
    />

    <div class="form-content">
      <!-- Описание посылки -->
      <div class="form-group">
        <label class="form-label">{{ t('parcel_description') }}</label>
        <textarea
          v-model="description"
          class="input textarea"
          :placeholder="t('parcel_description_placeholder')"
          rows="3"
        ></textarea>
      </div>

      <!-- Вес -->
      <div class="form-group">
        <label class="form-label">{{ t('parcel_weight') }}</label>
        <div class="weight-options">
          <button
            v-for="w in weightOptions"
            :key="w"
            class="chip"
            :class="{ active: weight === w }"
            @click="selectWeight(w)"
          >
            {{ w }} {{ t('kg') }}
          </button>
        </div>
        <!-- Ручной ввод -->
        <input
          v-model.number="weight"
          type="number"
          class="input"
          :placeholder="t('parcel_weight')"
          min="0.1"
          max="50"
          step="0.1"
        />
      </div>

      <!-- Размер -->
      <div class="form-group">
        <label class="form-label">{{ t('parcel_size') }}</label>
        <div class="size-options">
          <button
            v-for="s in sizeOptions"
            :key="s.id"
            class="size-btn"
            :class="{ active: size === s.id }"
            @click="size = s.id"
          >
            <span class="size-icon">{{ s.icon }}</span>
            <span class="size-label">{{ s.label }}</span>
          </button>
        </div>
      </div>

      <!-- Фото -->
      <div class="form-group">
        <label class="form-label">{{ t('parcel_photo') }}</label>
        <div class="photo-upload" @click="fileInput?.click()">
          <img v-if="photoPreview" :src="photoPreview" class="photo-preview" alt="" />
          <template v-else>
            <span class="photo-icon">📷</span>
            <span class="photo-text">{{ t('add_photo') }}</span>
          </template>
        </div>
        <input
          ref="fileInput"
          type="file"
          accept="image/*"
          style="display: none"
          @change="onPhotoSelect"
        />
      </div>

      <!-- Цена (InDriver-style) -->
      <div class="form-group">
        <label class="form-label">{{ t('your_price') }}</label>
        <div class="price-control">
          <button class="price-btn" @click="adjustPrice(-5)">−</button>
          <div class="price-display">
            <span class="price-value">${{ price }}</span>
          </div>
          <button class="price-btn" @click="adjustPrice(5)">+</button>
        </div>
        <p class="price-hint">{{ t('avg_price') }}</p>
      </div>

      <!-- Кнопка отправки -->
      <button
        class="btn btn-primary btn-block submit-btn"
        :disabled="!isValid || submitting"
        @click="submitParcel"
      >
        {{ submitting ? t('loading') : t('send_request') }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.send-parcel-page {
  padding-bottom: 32px;
}

.form-content {
  padding: 0 16px;
}

.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #8E8E93;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.textarea {
  resize: none;
  min-height: 80px;
}

.weight-options {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.size-options {
  display: flex;
  gap: 8px;
}

.size-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 14px 8px;
  background: #2C2C2E;
  border: 1px solid #3A3A3C;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.size-btn.active {
  border-color: #6C5CE7;
  background: rgba(108, 92, 231, 0.1);
}

.size-icon {
  font-size: 24px;
}

.size-label {
  font-size: 12px;
  color: #8E8E93;
}

.size-btn.active .size-label {
  color: #6C5CE7;
}

/* Фото */
.photo-upload {
  width: 100%;
  height: 120px;
  border: 2px dashed #3A3A3C;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  overflow: hidden;
}

.photo-icon {
  font-size: 32px;
}

.photo-text {
  font-size: 13px;
  color: #8E8E93;
}

.photo-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* Цена */
.price-control {
  display: flex;
  align-items: center;
  gap: 16px;
  justify-content: center;
}

.price-btn {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #2C2C2E;
  border: 1px solid #3A3A3C;
  color: #fff;
  font-size: 22px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.price-btn:active {
  background: #3A3A3C;
}

.price-display {
  text-align: center;
}

.price-value {
  font-size: 36px;
  font-weight: 800;
  color: #fff;
}

.price-hint {
  text-align: center;
  font-size: 12px;
  color: #8E8E93;
  margin-top: 8px;
}

.submit-btn {
  margin-top: 12px;
  padding: 16px;
  font-size: 16px;
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
