<script setup>
import { useRouter } from 'vue-router'

// Пропсы заголовка страницы
const props = defineProps({
  // Заголовок
  title: { type: String, default: '' },
  // Подзаголовок
  subtitle: { type: String, default: '' },
  // Показывать кнопку "Назад"
  showBack: { type: Boolean, default: false },
  // Правый слот (иконка/кнопка)
  rightIcon: { type: String, default: '' },
})

const emit = defineEmits(['back', 'right-click'])

const router = useRouter()

// Обработка кнопки "Назад" — router.back() по умолчанию, emit для перехвата
const goBack = () => {
  router.back()
  emit('back')
}
</script>

<template>
  <!-- Заголовок страницы с кнопкой назад -->
  <header class="page-header">
    <!-- Кнопка "Назад" -->
    <button v-if="showBack" class="back-btn" @click="goBack">
      <span>‹</span>
    </button>

    <!-- Текст заголовка -->
    <div class="header-text">
      <h1 class="header-title">{{ title }}</h1>
      <p v-if="subtitle" class="header-subtitle">{{ subtitle }}</p>
    </div>

    <!-- Правый слот (иконка) -->
    <button
      v-if="rightIcon"
      class="right-btn"
      @click="$emit('right-click')"
    >
      {{ rightIcon }}
    </button>
    <!-- Пустой spacer если нет правой кнопки но есть левая -->
    <div v-else-if="showBack" class="spacer"></div>
  </header>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  min-height: 56px;
}

.back-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #2C2C2E;
  border: none;
  color: #fff;
  font-size: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
}

.back-btn:active {
  opacity: 0.7;
}

.header-text {
  flex: 1;
  min-width: 0;
}

.header-title {
  font-size: 22px;
  font-weight: 700;
  color: #fff;
  line-height: 1.2;
}

.header-subtitle {
  font-size: 13px;
  color: #8E8E93;
  margin-top: 2px;
}

.right-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #2C2C2E;
  border: none;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
}

.spacer {
  width: 36px;
  flex-shrink: 0;
}
</style>
