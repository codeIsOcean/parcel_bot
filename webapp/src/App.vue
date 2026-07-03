<script setup>
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useTelegram } from '@/composables/useTelegram'
import { useLocale } from '@/composables/useLocale'
import { useAuthStore } from '@/stores/auth'
import BottomNav from '@/components/layout/BottomNav.vue'

const route = useRoute()
const { ready, initData } = useTelegram()
const { initLang } = useLocale()
const authStore = useAuthStore()

// Страницы без BottomNav (чат, отправка, публикация и т.д.)
const pagesWithoutNav = ['chat', 'send-parcel', 'publish-flight', 'rate', 'tracking']

onMounted(async () => {
  // Инициализация Telegram WebApp
  ready()

  // Инициализация языка
  initLang()

  // Авторизация через Telegram initData
  if (initData.value && !authStore.isAuthenticated) {
    try {
      await authStore.login(initData.value)
    } catch {
      // В dev-режиме без Telegram — работаем без авторизации
      console.warn('Telegram auth unavailable, running in dev mode')
    }
  }

  // При повторном визите — загружаем профиль по существующему токену
  if (authStore.token && !authStore.user) {
    await authStore.fetchMe()
  }
})
</script>

<template>
  <!-- Основной контейнер приложения -->
  <div class="app-container">
    <!-- Страница (анимация перехода) -->
    <router-view v-slot="{ Component }">
      <transition name="slide-up" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>

    <!-- Нижняя навигация (скрываем на определённых страницах) -->
    <BottomNav v-if="!pagesWithoutNav.includes(route.name)" />
  </div>
</template>

<style scoped>
.app-container {
  min-height: 100vh;
  max-width: 100vw;
  overflow-x: hidden;
}
</style>
