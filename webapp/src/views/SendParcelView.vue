<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { useParcelsStore } from '@/stores/parcels'
import { mediaApi } from '@/api/media'
import PageHeader from '@/components/layout/PageHeader.vue'
import CityPicker from '@/components/shared/CityPicker.vue'

const route = useRoute()
const router = useRouter()
const { t } = useLocale()
const { haptic, showMainButton, hideMainButton } = useTelegram()
const parcelsStore = useParcelsStore()

// Маршрут. Приходит из адреса, если его выбрали на главной,
// но остаётся редактируемым: посылку можно опубликовать без поиска перевозчика.
const fromCity = ref(route.query.from || '')
const toCity = ref(route.query.to || '')

// Модалка выбора города
const showCityPicker = ref(false)
const cityPickerTarget = ref('from')

// Открыть выбор города
const openCityPicker = (target) => {
  haptic.selection()
  cityPickerTarget.value = target
  showCityPicker.value = true
}

// Город выбран
const onCitySelect = (city) => {
  if (cityPickerTarget.value === 'from') {
    fromCity.value = city
  } else {
    toCity.value = city
  }
  showCityPicker.value = false
}

// Поменять города местами
const swapCities = () => {
  haptic.impact('light')
  const buffer = fromCity.value
  fromCity.value = toCity.value
  toCity.value = buffer
}

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
  return (
    fromCity.value &&
    toCity.value &&
    description.value.trim().length >= 3 &&
    weight.value > 0 &&
    price.value > 0
  )
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

// Выбор фото. Сам файл уходит на сервер после создания посылки,
// потому что снимок привязывается к её идентификатору.
const fileInput = ref(null)
const photoFile = ref(null)
const onPhotoSelect = (event) => {
  const file = event.target.files[0]
  if (file) {
    photoFile.value = file
    const reader = new FileReader()
    reader.onload = (e) => {
      photoPreview.value = e.target.result
    }
    reader.readAsDataURL(file)
  }
}

// Текст ошибки отправки
const error = ref('')

// Отправка заявки
const submitting = ref(false)
const submitParcel = async () => {
  if (!isValid.value || submitting.value) return

  haptic.impact('medium')
  submitting.value = true

  try {
    const parcel = await parcelsStore.createParcel({
      from_city: fromCity.value,
      to_city: toCity.value,
      description: description.value,
      weight: weight.value,
      size: size.value,
      price: price.value,
      traveler_id: route.query.traveler_id,
    })

    // Снимок отправляем отдельно: он привязан к созданной посылке
    if (photoFile.value && parcel?.id) {
      try {
        await mediaApi.attachToParcel(parcel.id, photoFile.value, 'parcel')
      } catch {
        // Посылка уже создана — из-за фото заявку не теряем
      }
    }

    // Успех — тактильная обратная связь и переход
    haptic.notification('success')
    router.push({ name: 'parcels' })
  } catch (e) {
    // Запрещённое вложение — объясняем причину отдельно
    if (e?.response?.status === 422) {
      error.value = t('prohibited_content')
    }
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
      :subtitle="fromCity && toCity ? `${fromCity} → ${toCity}` : ''"
      show-back
    />

    <div class="form-content">
      <!-- Маршрут -->
      <div class="form-group">
        <label class="form-label">{{ t('route_label') }}</label>
        <div class="route-inputs">
          <button class="route-input" @click="openCityPicker('from')">
            <span class="dot dot-green"></span>
            <span :class="{ placeholder: !fromCity }">{{ fromCity || t('route_from') }}</span>
          </button>

          <button class="swap-btn" @click="swapCities">⇄</button>

          <button class="route-input" @click="openCityPicker('to')">
            <span class="dot dot-red"></span>
            <span :class="{ placeholder: !toCity }">{{ toCity || t('route_to') }}</span>
          </button>
        </div>
      </div>

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
      <div v-if="error" class="error-bar">{{ error }}</div>

      <button
        class="btn btn-primary btn-block submit-btn"
        :disabled="!isValid || submitting"
        @click="submitParcel"
      >
        {{ submitting ? t('loading') : t('send_request') }}
      </button>
    </div>
    <!-- Выбор города -->
    <CityPicker
      :visible="showCityPicker"
      :title="cityPickerTarget === 'from' ? t('choose_from_city') : t('choose_to_city')"
      @select="onCitySelect"
      @close="showCityPicker = false"
    />
  </div>
</template>

<style scoped>
/* Селектор маршрута на экране публикации */
.route-inputs {
  display: flex;
  align-items: center;
  gap: 8px;
}

.route-input {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--border-strong);
  border-radius: 12px;
  background: var(--surface-2);
  color: var(--text-1);
  font-size: 14px;
  cursor: pointer;
  overflow: hidden;
  white-space: nowrap;
}

.route-input .placeholder {
  color: var(--text-3);
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-green {
  background: var(--success);
}

.dot-red {
  background: var(--danger);
}

.swap-btn {
  width: 36px;
  height: 36px;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: var(--surface);
  color: var(--text-2);
  font-size: 16px;
  cursor: pointer;
  flex-shrink: 0;
}

/* Ошибка отправки заявки */
.error-bar {
  margin-bottom: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(255, 59, 48, 0.1);
  color: var(--danger);
  font-size: 13px;
  text-align: center;
}

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
  color: var(--text-2);
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
  background: var(--surface-2);
  border: 1px solid var(--border-strong);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.size-btn.active {
  border-color: var(--primary);
  background: rgba(108, 92, 231, 0.1);
}

.size-icon {
  font-size: 24px;
}

.size-label {
  font-size: 12px;
  color: var(--text-2);
}

.size-btn.active .size-label {
  color: var(--primary);
}

/* Фото */
.photo-upload {
  width: 100%;
  height: 120px;
  border: 2px dashed var(--border-strong);
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
  color: var(--text-2);
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
  background: var(--surface-2);
  border: 1px solid var(--border-strong);
  color: var(--text-1);
  font-size: 22px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.price-btn:active {
  background: var(--surface-3);
}

.price-display {
  text-align: center;
}

.price-value {
  font-size: 36px;
  font-weight: 800;
  color: var(--text-1);
}

.price-hint {
  text-align: center;
  font-size: 12px;
  color: var(--text-2);
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
}</style>
