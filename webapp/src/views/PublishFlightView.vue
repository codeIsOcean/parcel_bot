<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { useFlightsStore } from '@/stores/flights'
import PageHeader from '@/components/layout/PageHeader.vue'
import CityPicker from '@/components/shared/CityPicker.vue'

const router = useRouter()
const { t } = useLocale()
const { haptic } = useTelegram()
const flightsStore = useFlightsStore()

// Поля формы рейса
const fromCity = ref('')
const toCity = ref('')
const date = ref('')
const availableKg = ref(null)
const pricePerKg = ref(null)
const notes = ref('')

// Состояние city picker
const showCityPicker = ref(false)
const cityPickerTarget = ref('from')

// Статус отправки
const submitting = ref(false)

// Валидация формы
const isValid = computed(() => {
  return (
    fromCity.value &&
    toCity.value &&
    date.value &&
    availableKg.value > 0 &&
    pricePerKg.value > 0
  )
})

// Открыть выбор города
const openCityPicker = (target) => {
  cityPickerTarget.value = target
  showCityPicker.value = true
}

// Обработка выбора города
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

// Отправка формы — публикация рейса
const submitFlight = async () => {
  if (!isValid.value || submitting.value) return

  haptic.impact('medium')
  submitting.value = true

  try {
    await flightsStore.publishFlight({
      from_city: fromCity.value,
      to_city: toCity.value,
      flight_date: date.value,
      available_kg: availableKg.value,
      price_per_kg: pricePerKg.value,
      notes: notes.value,
    })

    // Успешная публикация — переход на главную
    haptic.notification('success')
    router.push({ name: 'home' })
  } catch (e) {
    haptic.notification('error')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="publish-flight-page">
    <!-- Заголовок с кнопкой назад -->
    <PageHeader
      :title="t('publish_flight')"
      show-back
    />

    <div class="form-content">
      <!-- Маршрут: откуда и куда -->
      <div class="form-group">
        <label class="form-label">{{ t('route_label') }}</label>
        <div class="route-inputs">
          <!-- Город отправления -->
          <button class="route-input" @click="openCityPicker('from')">
            <span class="dot dot-green"></span>
            <span :class="{ placeholder: !fromCity }">
              {{ fromCity || t('route_from') }}
            </span>
          </button>

          <!-- Кнопка обмена городов -->
          <button class="swap-btn" @click="swapCities">⇄</button>

          <!-- Город назначения -->
          <button class="route-input" @click="openCityPicker('to')">
            <span class="dot dot-red"></span>
            <span :class="{ placeholder: !toCity }">
              {{ toCity || t('route_to') }}
            </span>
          </button>
        </div>
      </div>

      <!-- Дата вылета -->
      <div class="form-group">
        <label class="form-label">{{ t('flight_date') }}</label>
        <input
          v-model="date"
          type="date"
          class="input"
          :min="new Date().toISOString().split('T')[0]"
        />
      </div>

      <!-- Доступный вес (кг) -->
      <div class="form-group">
        <label class="form-label">{{ t('available_kg') }}</label>
        <input
          v-model.number="availableKg"
          type="number"
          class="input"
          :placeholder="t('available_kg_placeholder')"
          min="0.5"
          max="50"
          step="0.5"
        />
      </div>

      <!-- Цена за кг -->
      <div class="form-group">
        <label class="form-label">{{ t('price_per_kg') }}</label>
        <div class="price-input-wrap">
          <span class="price-currency">$</span>
          <input
            v-model.number="pricePerKg"
            type="number"
            class="input input-with-prefix"
            :placeholder="t('price_per_kg_placeholder')"
            min="1"
            step="1"
          />
        </div>
      </div>

      <!-- Примечания -->
      <div class="form-group">
        <label class="form-label">{{ t('notes') }}</label>
        <textarea
          v-model="notes"
          class="input textarea"
          :placeholder="t('notes_placeholder')"
          rows="3"
        ></textarea>
      </div>

      <!-- Кнопка публикации -->
      <button
        class="btn btn-primary btn-block submit-btn"
        :disabled="!isValid || submitting"
        @click="submitFlight"
      >
        {{ submitting ? t('loading') : t('publish_flight') }}
      </button>
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
.publish-flight-page {
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

/* Маршрут: два поля и кнопка обмена */
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

/* Точки маршрута */
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-green { background: #30D158; }
.dot-red { background: #FF453A; }

/* Кнопка обмена городов */
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

/* Поле ввода с префиксом валюты */
.price-input-wrap {
  position: relative;
}

.price-currency {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: #8E8E93;
  font-size: 16px;
  font-weight: 600;
}

.input-with-prefix {
  padding-left: 32px;
}

/* Текстовое поле примечаний */
.textarea {
  resize: none;
  min-height: 80px;
}

/* Кнопка отправки */
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
