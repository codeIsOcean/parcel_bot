<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { useAuthStore } from '@/stores/auth'
import { usersApi } from '@/api/users'
import PageHeader from '@/components/layout/PageHeader.vue'

const router = useRouter()
const { t, currentLang, setLang } = useLocale()
const { haptic } = useTelegram()
const authStore = useAuthStore()

// Состояние уведомлений
const notificationsEnabled = ref(true)

// Переключение языка
const switchLanguage = (lang) => {
  haptic.selection()
  setLang(lang)
}

// Переключение уведомлений
const toggleNotifications = async () => {
  haptic.selection()
  const newValue = !notificationsEnabled.value
  notificationsEnabled.value = newValue
  try {
    // Сохраняем настройку на сервере
    await usersApi.updateProfile({ notifications_enabled: newValue })
  } catch {
    // Откатываем при ошибке
    notificationsEnabled.value = !newValue
  }
}

// Переход к предложению маршрута
const suggestRoute = () => {
  haptic.impact('light')
  router.push({ name: 'home' })
}

// Выход из аккаунта
const logout = () => {
  haptic.impact('medium')
  authStore.logout()
  router.push({ name: 'home' })
}
</script>

<template>
  <div class="settings-page">
    <!-- Заголовок -->
    <PageHeader
      :title="t('settings_title')"
      show-back
    />

    <div class="settings-content">
      <!-- Карточка: Язык приложения -->
      <div class="card settings-card">
        <div class="card-title">{{ t('settings_language') }}</div>
        <div class="language-switcher">
          <!-- Кнопка русского языка -->
          <button
            class="lang-btn"
            :class="{ active: currentLang === 'ru' }"
            @click="switchLanguage('ru')"
          >
            🇷🇺 Русский
          </button>
          <!-- Кнопка английского языка -->
          <button
            class="lang-btn"
            :class="{ active: currentLang === 'en' }"
            @click="switchLanguage('en')"
          >
            🇬🇧 English
          </button>
        </div>
      </div>

      <!-- Карточка: Уведомления -->
      <div class="card settings-card">
        <div class="setting-row" @click="toggleNotifications">
          <div class="setting-info">
            <span class="setting-icon">🔔</span>
            <span class="setting-label">{{ t('settings_notifications') }}</span>
          </div>
          <!-- Тогл-переключатель -->
          <div class="toggle" :class="{ active: notificationsEnabled }">
            <div class="toggle-thumb"></div>
          </div>
        </div>
      </div>

      <!-- Карточка: Поддержка -->
      <div class="card settings-card">
        <div class="setting-row" @click="router.push('/support')">
          <div class="setting-info">
            <span class="setting-icon">🆘</span>
            <span class="setting-label">{{ t('support_title') }}</span>
          </div>
          <span class="setting-arrow">›</span>
        </div>
      </div>

      <!-- Карточка: Предложить маршрут -->
      <div class="card settings-card">
        <div class="setting-row" @click="suggestRoute">
          <div class="setting-info">
            <span class="setting-icon">✈️</span>
            <span class="setting-label">{{ t('settings_suggest_route') }}</span>
          </div>
          <span class="setting-arrow">›</span>
        </div>
      </div>

      <!-- Карточка: О приложении -->
      <div class="card settings-card">
        <div class="setting-row">
          <div class="setting-info">
            <span class="setting-icon">ℹ️</span>
            <span class="setting-label">{{ t('settings_about') }}</span>
          </div>
          <span class="setting-value">v1.0.0</span>
        </div>
      </div>

      <!-- Кнопка выхода -->
      <button class="btn btn-danger btn-block logout-btn" @click="logout">
        {{ t('logout') }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.settings-page {
  padding-bottom: 32px;
}

.settings-content {
  padding: 0 16px;
}

/* Карточка настроек */
.settings-card {
  margin-bottom: 10px;
}

.card-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-2);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin-bottom: 12px;
}

/* Переключатель языка */
.language-switcher {
  display: flex;
  gap: 8px;
}

.lang-btn {
  flex: 1;
  padding: 10px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid var(--border-strong);
  background: transparent;
  color: var(--text-2);
}

.lang-btn.active {
  background: var(--primary);
  border-color: var(--primary);
  color: var(--on-accent);
}

.lang-btn:active {
  transform: scale(0.97);
}

/* Строка настройки */
.setting-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  cursor: pointer;
}

.setting-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.setting-icon {
  font-size: 20px;
}

.setting-label {
  font-size: 15px;
  color: var(--text-1);
}

.setting-arrow {
  font-size: 20px;
  color: var(--text-2);
}

.setting-value {
  font-size: 13px;
  color: var(--text-2);
}

/* Тогл-переключатель */
.toggle {
  width: 48px;
  height: 28px;
  border-radius: 14px;
  background: var(--surface-3);
  padding: 2px;
  cursor: pointer;
  transition: background 0.25s;
}

.toggle.active {
  background: var(--primary);
}

.toggle-thumb {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--surface);
  box-shadow: 0 1px 3px rgba(20, 22, 26, 0.25);
  transition: transform 0.25s;
}

.toggle.active .toggle-thumb {
  transform: translateX(20px);
}

/* Кнопка выхода */
.btn-danger {
  background: transparent;
  border: 1px solid var(--danger);
  color: var(--danger);
  padding: 14px;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-danger:active {
  background: rgba(255, 69, 58, 0.1);
}

.logout-btn {
  margin-top: 24px;
}</style>
