<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/client'

const { t } = useLocale()
const { requestContact, openTelegramLink, haptic } = useTelegram()
const authStore = useAuthStore()

// Ждём, пока бот сохранит номер после requestContact
const waiting = ref(false)

// Пользователь отказался делиться — показываем запасной путь через бота
const declined = ref(false)

// Юзернейм бота для запасной ссылки
const botUsername = ref('')

// Таймер опроса профиля
let pollTimer = null

// Проверить, появился ли номер
const poll = async () => {
  await authStore.fetchMe()
  if (authStore.hasPhone) {
    haptic.notification('success')
    stopPolling()
  }
}

const stopPolling = () => {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = null
  waiting.value = false
}

// Нативный запрос контакта: Telegram отправит его боту, бот сохранит в профиль
const share = async () => {
  haptic.impact('medium')
  const sent = await requestContact()
  if (!sent) {
    declined.value = true
    return
  }
  waiting.value = true
  pollTimer = setInterval(poll, 2000)
  // Дольше минуты не ждём — покажем запасной путь
  setTimeout(() => { if (waiting.value) { stopPolling(); declined.value = true } }, 60000)
}

// Запасной путь: открыть бота, он попросит номер кнопкой
const openBot = () => {
  haptic.impact('light')
  if (botUsername.value) openTelegramLink(`https://t.me/${botUsername.value}?start=app`)
}

onMounted(async () => {
  try {
    const meta = await api.get('/meta')
    botUsername.value = meta.bot_username || ''
  } catch {
    botUsername.value = ''
  }
  // Номер мог быть сохранён ботом, пока приложение было закрыто
  await authStore.fetchMe()
})

onUnmounted(stopPolling)
</script>

<template>
  <!-- Полноэкранная заглушка: без номера телефона сделки закрыты -->
  <div class="phone-gate">
    <div class="phone-card">
      <span class="phone-icon">📱</span>
      <h2 class="phone-title">{{ t('phone_gate_title') }}</h2>
      <p class="phone-text">{{ t('phone_gate_text') }}</p>

      <!-- Ожидание ответа бота -->
      <p v-if="waiting" class="phone-waiting">{{ t('phone_gate_waiting') }}</p>

      <!-- Основная кнопка: нативный запрос контакта -->
      <button class="btn btn-primary btn-block" :disabled="waiting" @click="share">
        {{ t('phone_gate_share') }}
      </button>

      <!-- Запасной путь через бота -->
      <button v-if="declined && botUsername" class="btn btn-outline btn-block fallback-btn" @click="openBot">
        {{ t('phone_gate_open_bot') }}
      </button>
      <p v-if="declined" class="phone-hint">{{ t('phone_gate_hint') }}</p>
    </div>
  </div>
</template>

<style scoped>
.phone-gate {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: var(--bg);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.phone-card {
  width: 100%;
  max-width: 400px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 28px 20px;
  text-align: center;
  box-shadow: var(--shadow-card);
}

.phone-icon {
  font-size: 44px;
  display: block;
  margin-bottom: 12px;
}

.phone-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-1);
  margin-bottom: 8px;
}

.phone-text {
  font-size: 14px;
  color: var(--text-2);
  line-height: 1.5;
  margin-bottom: 20px;
}

.phone-waiting {
  font-size: 13px;
  color: var(--primary);
  margin-bottom: 12px;
}

.fallback-btn {
  margin-top: 10px;
}

.phone-hint {
  margin-top: 12px;
  font-size: 12px;
  color: var(--text-3);
}
</style>
