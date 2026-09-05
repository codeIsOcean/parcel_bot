<script setup>
import { ref, computed, onMounted } from 'vue'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { walletApi } from '@/api/wallet'
import PageHeader from '@/components/layout/PageHeader.vue'

const { t } = useLocale()
const { haptic, openInvoice, openLink } = useTelegram()

const loading = ref(true)
const wallet = ref(null)
const notice = ref('')
const busy = ref(false)

// Выбранный пакет пополнения
const selected = ref(null)

// Реквизиты перевода в TON, когда пользователь выбрал этот способ
const tonInvoice = ref(null)

// Баланс в звёздах
const balance = computed(() => wallet.value?.balance_stars ?? 0)

// Состояние дневного доступа
const access = computed(() => wallet.value?.access || {})

// На сколько рабочих дней хватает баланса
const daysLeft = computed(() => {
  const price = access.value.daily_fee_stars || 0
  return price > 0 ? Math.floor(balance.value / price) : 0
})

// Открыть рабочий день прямо из кабинета
const openDay = async () => {
  if (busy.value) return
  busy.value = true
  notice.value = ''
  try {
    await walletApi.openDay()
    notice.value = t('day_opened')
    haptic.notification('success')
    await load()
  } catch (err) {
    notice.value = err?.response?.status === 402 ? t('not_enough_stars') : t('error_generic')
    haptic.notification('error')
  } finally {
    busy.value = false
  }
}

// Загрузка кабинета
const load = async () => {
  loading.value = true
  try {
    wallet.value = await walletApi.get()
    if (!selected.value && wallet.value.packages?.length) {
      selected.value = wallet.value.packages[1] ?? wallet.value.packages[0]
    }
  } catch {
    notice.value = t('error_loading')
  } finally {
    loading.value = false
  }
}

// Выбор пакета
const choose = (amount) => {
  haptic.selection()
  selected.value = amount
  tonInvoice.value = null
}

// Оплата звёздами: счёт открывается штатным окном Telegram
const payWithStars = async () => {
  if (!selected.value || busy.value) return
  busy.value = true
  notice.value = ''
  try {
    const data = await walletApi.topUpStars(selected.value)
    const status = await openInvoice(data.invoice_link)

    if (status === 'paid') {
      haptic.notification('success')
      notice.value = t('wallet_paid_ok')
      // Баланс зачисляет бот по событию Telegram, поэтому перечитываем
      await load()
    } else if (status === 'cancelled') {
      notice.value = t('wallet_paid_cancelled')
    } else if (status === 'unavailable') {
      notice.value = t('wallet_outside_telegram')
    } else {
      notice.value = t('wallet_paid_failed')
    }
  } catch {
    notice.value = t('error_generic')
  } finally {
    busy.value = false
  }
}

// Оплата в TON: показываем реквизиты и код для комментария
const payWithTon = async () => {
  if (!selected.value || busy.value) return
  busy.value = true
  notice.value = ''
  try {
    tonInvoice.value = await walletApi.topUpTon(selected.value)
  } catch {
    notice.value = t('error_generic')
  } finally {
    busy.value = false
  }
}

// Проверка поступления перевода
const checkTon = async () => {
  if (!tonInvoice.value || busy.value) return
  busy.value = true
  try {
    const data = await walletApi.checkTon(tonInvoice.value.payment_id)
    if (data.status === 'completed') {
      haptic.notification('success')
      notice.value = t('wallet_paid_ok')
      tonInvoice.value = null
      await load()
    } else {
      notice.value = t('ton_pending')
    }
  } catch {
    notice.value = t('error_generic')
  } finally {
    busy.value = false
  }
}

// Копирование реквизитов
const copy = async (value) => {
  try {
    await navigator.clipboard.writeText(value)
    haptic.impact('light')
    notice.value = t('copied')
  } catch {
    // Буфер обмена может быть недоступен — молча игнорируем
  }
}

// Подпись операции в истории
const kindLabel = (kind) => t(`wallet_kind_${kind}`)

// Дата операции
const formatDate = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('ru-RU', {
    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
  })
}

onMounted(load)
</script>

<template>
  <div class="wallet-view">
    <PageHeader :title="t('wallet_title')" show-back />

    <div v-if="loading" class="state">{{ t('loading') }}</div>

    <div v-else-if="wallet" class="content">
      <!-- Баланс -->
      <div class="card balance-card">
        <div class="balance-label">{{ t('wallet_balance') }}</div>
        <div class="balance-value">{{ balance }} ⭐</div>
        <div class="balance-hint">
          {{ t('day_tariff') }}: {{ access.daily_fee_stars }} ⭐
        </div>
        <div v-if="daysLeft > 0" class="balance-posts">
          {{ t('days_left_short', { days: daysLeft }) }}
        </div>
      </div>

      <!-- Сегодняшний рабочий день -->
      <div class="card day-card">
        <div v-if="access.launch_trial" class="day-ok">🎁 {{ t('launch_trial_banner') }}</div>
        <template v-else-if="access.can_respond">
          <div class="day-ok">✅ {{ t('day_paid_today') }}</div>
          <div v-if="access.trial_days_left" class="day-hint">
            {{ t('day_trial_left', { days: access.trial_days_left }) }}
          </div>
        </template>
        <template v-else>
          <div class="day-hint">{{ t('day_locked_hint', { price: access.daily_fee_stars }) }}</div>
          <button class="btn-primary" :disabled="busy" @click="openDay">
            {{ access.trial_days_left
              ? t('day_open_free', { days: access.trial_days_left })
              : t('day_open', { price: access.daily_fee_stars }) }}
          </button>
        </template>
      </div>

      <!-- Пакеты пополнения -->
      <div class="section">
        <h2 class="section-title">{{ t('wallet_choose_amount') }}</h2>
        <div class="packages">
          <button
            v-for="amount in wallet.packages"
            :key="amount"
            class="package"
            :class="{ active: selected === amount }"
            @click="choose(amount)"
          >
            {{ amount }} ⭐
          </button>
        </div>

        <button class="btn-primary" :disabled="busy || !selected" @click="payWithStars">
          ⭐ {{ t('wallet_pay_stars') }}
        </button>

        <button
          v-if="wallet.ton_enabled"
          class="btn-secondary"
          :disabled="busy || !selected"
          @click="payWithTon"
        >
          💎 {{ t('wallet_pay_ton') }}
        </button>
      </div>

      <!-- Реквизиты перевода в TON -->
      <div v-if="tonInvoice" class="card ton-card">
        <div class="ton-title">💎 {{ t('ton_title') }}</div>
        <div class="ton-hint">{{ t('ton_hint') }}</div>

        <div class="ton-row" @click="copy(String(tonInvoice.amount_ton))">
          <span class="ton-label">{{ t('ton_amount') }}</span>
          <span class="ton-value">{{ tonInvoice.amount_ton }} TON</span>
        </div>
        <div class="ton-row" @click="copy(tonInvoice.payment_code)">
          <span class="ton-label">{{ t('ton_code') }}</span>
          <span class="ton-value code">{{ tonInvoice.payment_code }}</span>
        </div>
        <div class="ton-row wallet-row" @click="copy(tonInvoice.wallet_address)">
          <span class="ton-label">{{ t('ton_wallet') }}</span>
          <span class="ton-value address">{{ tonInvoice.wallet_address }}</span>
        </div>

        <button class="btn-primary" @click="openLink(tonInvoice.deep_link)">
          {{ t('ton_open_wallet') }}
        </button>
        <button class="btn-secondary" :disabled="busy" @click="checkTon">
          {{ t('ton_check') }}
        </button>
      </div>

      <!-- Сообщение о результате -->
      <div v-if="notice" class="notice">{{ notice }}</div>

      <!-- История операций -->
      <div class="section">
        <h2 class="section-title">{{ t('wallet_history') }}</h2>
        <div v-if="!wallet.transactions.length" class="empty">
          {{ t('wallet_empty_history') }}
        </div>
        <div v-for="txn in wallet.transactions" :key="txn.id" class="txn">
          <div class="txn-main">
            <span class="txn-kind">{{ kindLabel(txn.kind) }}</span>
            <span class="txn-amount" :class="txn.kind">
              {{ txn.kind === 'charge' ? '−' : '+' }}{{ txn.amount_stars }} ⭐
            </span>
          </div>
          <div class="txn-meta">
            <span>{{ txn.note }}</span>
            <span>{{ formatDate(txn.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.wallet-view {
  padding: 0 16px 32px;
}

.state,
.empty {
  padding: 32px 0;
  text-align: center;
  color: var(--text-2);
  font-size: 14px;
}

/* Сегодняшний рабочий день */
.day-card {
  margin-bottom: 20px;
  text-align: center;
}

.day-ok {
  font-size: 15px;
  font-weight: 600;
  color: var(--success);
}

.day-hint {
  font-size: 13px;
  color: var(--text-2);
  line-height: 1.4;
  margin-bottom: 10px;
}

/* Баланс */
.balance-card {
  text-align: center;
  margin-bottom: 20px;
}

.balance-label {
  font-size: 13px;
  color: var(--text-2);
}

.balance-value {
  font-size: 34px;
  font-weight: 800;
  color: var(--text-1);
  margin: 4px 0 8px;
}

.balance-hint {
  font-size: 13px;
  color: var(--text-2);
}

.balance-posts {
  margin-top: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--success);
}

.section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-1);
  margin-bottom: 10px;
}

/* Пакеты */
.packages {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.package {
  padding: 12px 6px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
  color: var(--text-1);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.package.active {
  border-color: var(--primary);
  background: var(--primary-soft);
  color: var(--primary);
}

.btn-primary,
.btn-secondary {
  width: 100%;
  padding: 13px;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  margin-bottom: 8px;
}

.btn-primary {
  background: var(--primary);
  color: var(--on-accent);
}

.btn-secondary {
  background: var(--surface-2);
  color: var(--text-1);
}

.btn-primary:disabled,
.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Реквизиты TON */
.ton-card {
  margin-bottom: 20px;
}

.ton-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-1);
  margin-bottom: 4px;
}

.ton-hint {
  font-size: 12px;
  color: var(--text-2);
  line-height: 1.4;
  margin-bottom: 12px;
}

.ton-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
}

.wallet-row {
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.ton-label {
  font-size: 13px;
  color: var(--text-2);
}

.ton-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-1);
}

.ton-value.code {
  letter-spacing: 1px;
  color: var(--primary);
}

.ton-value.address {
  font-size: 12px;
  word-break: break-all;
  font-weight: 500;
}

.notice {
  margin-bottom: 16px;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--primary-soft);
  color: var(--text-1);
  font-size: 13px;
  text-align: center;
}

/* История */
.txn {
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}

.txn-main {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.txn-kind {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-1);
}

.txn-amount {
  font-size: 15px;
  font-weight: 700;
  color: var(--success);
}

.txn-amount.charge {
  color: var(--danger);
}

.txn-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-top: 2px;
  font-size: 12px;
  color: var(--text-2);
}
</style>
