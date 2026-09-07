<script setup>
import { ref } from 'vue'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { adminApi } from '@/api/admin'

const { t } = useLocale()
const { haptic } = useTelegram()

// Аудитория рассылки
const audience = ref('all')
const audiences = ['all', 'senders', 'travelers', 'with_phone']

// Текст сообщения
const text = ref('')
const maxLength = 4000

// Состояние: подтверждение, отправка, результат
const confirming = ref(false)
const sending = ref(false)
const sentCount = ref(null)
const error = ref('')

// Выбор аудитории сбрасывает подтверждение
const setAudience = (a) => {
  haptic.selection()
  audience.value = a
  confirming.value = false
}

// Отправка в два нажатия: первое — подтвердить, второе — разослать
const send = async () => {
  if (!text.value.trim() || sending.value) return
  if (!confirming.value) {
    haptic.impact('light')
    confirming.value = true
    return
  }
  haptic.impact('medium')
  sending.value = true
  error.value = ''
  sentCount.value = null
  try {
    const result = await adminApi.broadcast({ audience: audience.value, text: text.value.trim() })
    sentCount.value = result.sent
    text.value = ''
    haptic.notification('success')
  } catch {
    haptic.notification('error')
    error.value = t('admin_error')
  } finally {
    sending.value = false
    confirming.value = false
  }
}
</script>

<template>
  <div class="broadcast">
    <!-- Аудитория -->
    <div class="chips">
      <button
        v-for="a in audiences"
        :key="a"
        class="chip"
        :class="{ active: audience === a }"
        @click="setAudience(a)"
      >
        {{ t('admin_audience_' + a) }}
      </button>
    </div>

    <!-- Текст -->
    <textarea
      v-model="text"
      class="input textarea"
      :maxlength="maxLength"
      rows="6"
      :placeholder="t('admin_broadcast_placeholder')"
      @input="confirming = false"
    ></textarea>
    <div class="counter">{{ text.length }}/{{ maxLength }}</div>

    <!-- Отправить -->
    <button
      class="btn btn-block"
      :class="confirming ? 'btn-danger' : 'btn-primary'"
      :disabled="sending || !text.trim()"
      @click="send"
    >
      {{ sending ? '…' : confirming ? t('admin_broadcast_confirm') : t('admin_broadcast_send') }}
    </button>

    <!-- Результат -->
    <p v-if="sentCount !== null" class="success-text">{{ t('admin_broadcast_sent', { count: sentCount }) }}</p>
    <p v-if="error" class="error-text">{{ error }}</p>
  </div>
</template>

<style scoped>
.broadcast {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chips {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  scrollbar-width: none;
}

.chips::-webkit-scrollbar {
  display: none;
}

.textarea {
  resize: vertical;
  min-height: 120px;
}

.counter {
  font-size: 12px;
  color: var(--text-3);
  text-align: right;
}

.btn:disabled {
  opacity: 0.5;
}

.success-text {
  color: var(--success);
  font-size: 13px;
}

.error-text {
  color: var(--danger);
  font-size: 13px;
}
</style>
