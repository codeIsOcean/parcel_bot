<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { useChatsStore } from '@/stores/chats'
import { useAuthStore } from '@/stores/auth'
import { chatsApi } from '@/api/chats'
import PageHeader from '@/components/layout/PageHeader.vue'

const router = useRouter()
const { t } = useLocale()
const { haptic } = useTelegram()
const chatsStore = useChatsStore()
const authStore = useAuthStore()

// ID чата из пропсов (через route params)
const props = defineProps({
  id: { type: [String, Number], required: true },
})

// Загрузка данных
const loading = ref(true)

// Текст нового сообщения
const messageText = ref('')

// Ссылка на контейнер сообщений (для прокрутки)
const messagesContainer = ref(null)

// Информация о посылке, привязанной к чату (из данных чата)
const parcelInfo = ref(null)

// Имя собеседника (из данных чата)
const chatPartner = ref({
  name: '',
  online: false,
})

// Интервал опроса новых сообщений
let pollInterval = null

// Показать панель предложения цены
const showPriceOffer = ref(false)
const offerPrice = ref(20)

// ID текущего пользователя для определения стороны сообщения
const currentUserId = computed(() => authStore.user?.id || 1)

// Прокрутка к последнему сообщению
const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// Отправка текстового сообщения
const sendMessage = async () => {
  const text = messageText.value.trim()
  if (!text) return

  haptic.impact('light')
  messageText.value = ''

  try {
    await chatsStore.sendMessage(props.id, text)
    scrollToBottom()
  } catch (e) {
    haptic.notification('error')
  }
}

// Отправка предложения цены через API
const sendPriceOffer = async () => {
  if (offerPrice.value <= 0) return

  haptic.impact('medium')
  showPriceOffer.value = false

  try {
    await chatsApi.offerPrice(props.id, offerPrice.value)
    // Перезагружаем сообщения, чтобы отобразить системное сообщение о предложении
    await chatsStore.fetchMessages(props.id)
    scrollToBottom()
  } catch (e) {
    haptic.notification('error')
  }
}

// Регулировка предложенной цены
const adjustOfferPrice = (delta) => {
  haptic.selection()
  const newPrice = offerPrice.value + delta
  if (newPrice >= 5) {
    offerPrice.value = newPrice
  }
}

// Форматирование времени сообщения
const formatMessageTime = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

// Загрузка сообщений и метаданных чата при монтировании
onMounted(async () => {
  try {
    // Загружаем список чатов для получения метаданных
    await chatsStore.fetchChats()

    // Находим текущий чат для получения информации о собеседнике и посылке
    const currentChat = chatsStore.chatList.find(
      (c) => String(c.chat_id) === String(props.id)
    )
    if (currentChat) {
      // Устанавливаем данные собеседника
      chatPartner.value = {
        name: currentChat.partner_name || '',
        online: false,
      }
      // Загружаем данные посылки по parcel_id
      if (currentChat.parcel_id) {
        try {
          const { parcelsApi } = await import('@/api/parcels')
          const parcelRes = await parcelsApi.getById(currentChat.parcel_id)
          parcelInfo.value = parcelRes
        } catch {
          // Не критично — баннер просто не покажется
        }
      }
    }

    // Загружаем сообщения чата
    await chatsStore.fetchMessages(props.id)
  } finally {
    loading.value = false
    scrollToBottom()
  }

  // Запускаем опрос новых сообщений каждые 5 секунд
  pollInterval = setInterval(async () => {
    try {
      await chatsStore.fetchMessages(props.id)
    } catch {
      // Молча игнорируем ошибки опроса
    }
  }, 5000)
})

// Очистка интервала опроса при размонтировании
onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
})
</script>

<template>
  <div class="chat-page">
    <!-- Заголовок с именем собеседника -->
    <PageHeader
      :title="chatPartner.name"
      :subtitle="chatPartner.online ? t('online') : t('offline')"
      show-back
    />

    <!-- Баннер информации о посылке -->
    <div class="parcel-banner" v-if="parcelInfo">
      <div class="banner-route">
        {{ parcelInfo.from_city }} → {{ parcelInfo.to_city }}
      </div>
      <div class="banner-details">
        <span>{{ parcelInfo.description }}</span>
        <span class="banner-price">${{ parcelInfo.price }}</span>
      </div>
    </div>

    <!-- Список сообщений (скроллируемая область) -->
    <div ref="messagesContainer" class="messages-container">
      <!-- Загрузка -->
      <div v-if="loading" class="messages-loading">
        <div v-for="i in 5" :key="i" class="skeleton-msg" :class="{ 'skeleton-mine': i % 2 === 0 }">
          <div class="skeleton" :style="{ width: 40 + Math.random() * 40 + '%', height: '32px', borderRadius: '14px' }"></div>
        </div>
      </div>

      <!-- Сообщения -->
      <template v-else>
        <!-- Пустой чат -->
        <div v-if="chatsStore.messages.length === 0" class="empty-chat">
          <p>{{ t('chat_empty') }}</p>
        </div>

        <!-- Список сообщений -->
        <div
          v-for="msg in chatsStore.messages"
          :key="msg.id"
          class="message"
          :class="{ mine: msg.sender_id === currentUserId, theirs: msg.sender_id !== currentUserId }"
        >
          <div class="message-bubble">
            <p class="message-text">{{ msg.text }}</p>
            <span class="message-time">{{ formatMessageTime(msg.created_at) }}</span>
          </div>
        </div>
      </template>
    </div>

    <!-- Панель предложения цены (выдвижная) -->
    <Transition name="slide-up">
      <div v-if="showPriceOffer" class="price-offer-panel">
        <div class="offer-header">
          <span class="offer-title">{{ t('price_offer') }}</span>
          <button class="offer-close" @click="showPriceOffer = false">✕</button>
        </div>
        <!-- Регулятор цены -->
        <div class="offer-controls">
          <button class="price-btn" @click="adjustOfferPrice(-5)">−</button>
          <div class="offer-price">${{ offerPrice }}</div>
          <button class="price-btn" @click="adjustOfferPrice(5)">+</button>
        </div>
        <button class="btn btn-primary btn-block" @click="sendPriceOffer">
          {{ t('send_offer') }}
        </button>
      </div>
    </Transition>

    <!-- Нижняя панель ввода сообщения -->
    <div class="input-bar">
      <!-- Кнопка предложения цены -->
      <button class="action-btn" @click="showPriceOffer = !showPriceOffer">
        💰
      </button>

      <!-- Поле ввода сообщения -->
      <input
        v-model="messageText"
        class="message-input"
        :placeholder="t('type_message')"
        @keyup.enter="sendMessage"
      />

      <!-- Кнопка отправки -->
      <button
        class="send-btn"
        :class="{ active: messageText.trim() }"
        :disabled="!messageText.trim()"
        @click="sendMessage"
      >
        ↑
      </button>
    </div>
  </div>
</template>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #000;
}

/* Баннер информации о посылке */
.parcel-banner {
  padding: 10px 16px;
  background: #1C1C1E;
  border-bottom: 1px solid #2C2C2E;
}

.banner-route {
  font-size: 13px;
  font-weight: 600;
  color: #6C5CE7;
  margin-bottom: 2px;
}

.banner-details {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #8E8E93;
}

.banner-price {
  font-weight: 700;
  color: #fff;
}

/* Контейнер сообщений (скроллируемый) */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

/* Скелетон загрузки сообщений */
.messages-loading {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skeleton-msg {
  display: flex;
}

.skeleton-msg.skeleton-mine {
  justify-content: flex-end;
}

/* Пустой чат */
.empty-chat {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8E8E93;
  font-size: 14px;
}

/* Сообщение */
.message {
  display: flex;
  max-width: 80%;
}

.message.mine {
  align-self: flex-end;
}

.message.theirs {
  align-self: flex-start;
}

/* Пузырёк сообщения */
.message-bubble {
  padding: 8px 12px;
  border-radius: 16px;
  max-width: 100%;
}

.message.mine .message-bubble {
  background: #6C5CE7;
  border-bottom-right-radius: 4px;
}

.message.theirs .message-bubble {
  background: #2C2C2E;
  border-bottom-left-radius: 4px;
}

.message-text {
  font-size: 14px;
  color: #fff;
  word-wrap: break-word;
  line-height: 1.4;
}

.message-time {
  display: block;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.5);
  text-align: right;
  margin-top: 2px;
}

/* Панель предложения цены */
.price-offer-panel {
  padding: 16px;
  background: #1C1C1E;
  border-top: 1px solid #2C2C2E;
  border-radius: 16px 16px 0 0;
}

.offer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.offer-title {
  font-size: 16px;
  font-weight: 700;
  color: #fff;
}

.offer-close {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #2C2C2E;
  border: none;
  color: #8E8E93;
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.offer-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  margin-bottom: 16px;
}

.price-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: #2C2C2E;
  border: 1px solid #3A3A3C;
  color: #fff;
  font-size: 20px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.price-btn:active {
  background: #3A3A3C;
}

.offer-price {
  font-size: 32px;
  font-weight: 800;
  color: #fff;
  min-width: 80px;
  text-align: center;
}

/* Анимация появления панели цены */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.25s ease, opacity 0.25s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}

/* Нижняя панель ввода */
.input-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #1C1C1E;
  border-top: 1px solid #2C2C2E;
  /* Отступ для безопасной зоны (iPhone) */
  padding-bottom: max(8px, env(safe-area-inset-bottom));
}

/* Кнопка действий (предложение цены) */
.action-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #2C2C2E;
  border: none;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* Поле ввода сообщения */
.message-input {
  flex: 1;
  padding: 9px 14px;
  background: #2C2C2E;
  border: 1px solid #3A3A3C;
  border-radius: 20px;
  color: #fff;
  font-size: 14px;
  outline: none;
}

.message-input::placeholder {
  color: #8E8E93;
}

.message-input:focus {
  border-color: #6C5CE7;
}

/* Кнопка отправки */
.send-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #3A3A3C;
  border: none;
  color: #8E8E93;
  font-size: 18px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.2s;
}

.send-btn.active {
  background: #6C5CE7;
  color: #fff;
}

.send-btn:disabled {
  cursor: not-allowed;
}
</style>
