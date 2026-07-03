<script setup>
import { ref, computed } from 'vue'
import { useLocale } from '@/composables/useLocale'

const { t } = useLocale()

/**
 * Модалка выбора города.
 * Список городов + поиск + "Другой город" (свободный ввод).
 */
const props = defineProps({
  // Показывать модалку
  visible: { type: Boolean, default: false },
  // Заголовок
  title: { type: String, default: '' },
})

const emit = defineEmits(['select', 'close'])

// Поиск
const searchQuery = ref('')

// Свободный ввод (другой город)
const customCity = ref('')
const showCustomInput = ref(false)

// Список городов
const cities = [
  { id: 'dubai', name_ru: 'Дубай', name_en: 'Dubai', flag: '🇦🇪' },
  { id: 'almaty', name_ru: 'Алматы', name_en: 'Almaty', flag: '🇰🇿' },
  { id: 'moscow', name_ru: 'Москва', name_en: 'Moscow', flag: '🇷🇺' },
  { id: 'newyork', name_ru: 'Нью-Йорк', name_en: 'New York', flag: '🇺🇸' },
  { id: 'istanbul', name_ru: 'Стамбул', name_en: 'Istanbul', flag: '🇹🇷' },
  { id: 'astana', name_ru: 'Астана', name_en: 'Astana', flag: '🇰🇿' },
]

// Фильтрация по поиску
const filteredCities = computed(() => {
  const q = searchQuery.value.toLowerCase()
  if (!q) return cities
  return cities.filter(c =>
    c.name_ru.toLowerCase().includes(q) || c.name_en.toLowerCase().includes(q)
  )
})

// Выбрать город
const selectCity = (city) => {
  emit('select', city.name_en)
  emit('close')
}

// Подтвердить свой город
const submitCustomCity = () => {
  if (customCity.value.trim()) {
    emit('select', customCity.value.trim())
    emit('close')
    customCity.value = ''
    showCustomInput.value = false
  }
}
</script>

<template>
  <!-- Оверлей модалки -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
        <!-- Контент модалки -->
        <div class="modal-content">
          <!-- Заголовок -->
          <div class="modal-header">
            <h3>{{ title || t('route_from') }}</h3>
            <button class="close-btn" @click="$emit('close')">✕</button>
          </div>

          <!-- Поиск -->
          <input
            v-model="searchQuery"
            class="input search-input"
            :placeholder="t('search')"
            type="text"
          />

          <!-- Список городов -->
          <div class="cities-list">
            <button
              v-for="city in filteredCities"
              :key="city.id"
              class="city-item"
              @click="selectCity(city)"
            >
              <span class="city-flag">{{ city.flag }}</span>
              <span class="city-name">{{ city.name_ru }}</span>
            </button>

            <!-- Другой город -->
            <button
              v-if="!showCustomInput"
              class="city-item city-other"
              @click="showCustomInput = true"
            >
              <span class="city-flag">🌍</span>
              <span class="city-name">{{ t('city_other') }}</span>
            </button>

            <!-- Поле ввода своего города -->
            <div v-else class="custom-city-input">
              <input
                v-model="customCity"
                class="input"
                :placeholder="t('city_other')"
                @keyup.enter="submitCustomCity"
                autofocus
              />
              <button class="btn btn-primary" @click="submitCustomCity">
                {{ t('confirm') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: flex-end;
  z-index: 200;
}

.modal-content {
  width: 100%;
  max-height: 80vh;
  background: #1C1C1E;
  border-radius: 16px 16px 0 0;
  padding: 20px 16px;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.modal-header h3 {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
}

.close-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #2C2C2E;
  border: none;
  color: #8E8E93;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.search-input {
  margin-bottom: 12px;
}

.cities-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.city-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 12px;
  background: none;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  width: 100%;
  text-align: left;
  transition: background 0.15s;
}

.city-item:active {
  background: #2C2C2E;
}

.city-flag {
  font-size: 28px;
}

.city-name {
  font-size: 16px;
  color: #fff;
}

.city-other .city-name {
  color: #6C5CE7;
}

.custom-city-input {
  display: flex;
  gap: 8px;
  padding: 8px 0;
}

.custom-city-input .input {
  flex: 1;
}

.custom-city-input .btn {
  flex-shrink: 0;
}
</style>
