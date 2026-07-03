<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { useAuthStore } from '@/stores/auth'
import { subscriptionsApi } from '@/api/subscriptions'
import PageHeader from '@/components/layout/PageHeader.vue'

const router = useRouter()
const { t } = useLocale()
const { haptic } = useTelegram()
const authStore = useAuthStore()

// Выбранный план
const selectedPlan = ref('monthly')

// Статус оплаты
const paying = ref(false)

// Активная подписка пользователя
const activePlan = ref(null)

// Цены с сервера
const prices = ref(null)

// Загрузка активной подписки и цен при монтировании
onMounted(async () => {
  try {
    const active = await subscriptionsApi.getActive()
    activePlan.value = active?.plan || null
  } catch {
    // Нет активной подписки — оставляем null
  }
  try {
    const pricesData = await subscriptionsApi.getPrices()
    prices.value = pricesData
  } catch {
    // Используем дефолтные цены из планов
  }
})

// Список тарифных планов
const plans = computed(() => [
  {
    id: 'monthly',
    name: t('plan_monthly'),
    price: 40,
    period: t('plan_per_month'),
    icon: '📦',
    features: [
      t('plan_feature_unlimited'),
      t('plan_feature_priority'),
      t('plan_feature_support'),
    ],
  },
  {
    id: 'quarterly',
    name: t('plan_quarterly'),
    price: 100,
    period: t('plan_per_quarter'),
    icon: '🚀',
    // Скидка относительно месячного плана
    discount: 17,
    popular: true,
    features: [
      t('plan_feature_unlimited'),
      t('plan_feature_priority'),
      t('plan_feature_support'),
      t('plan_feature_badge'),
    ],
  },
  {
    id: 'yearly',
    name: t('plan_yearly'),
    price: 300,
    period: t('plan_per_year'),
    icon: '👑',
    // Скидка относительно месячного плана
    discount: 38,
    features: [
      t('plan_feature_unlimited'),
      t('plan_feature_priority'),
      t('plan_feature_support'),
      t('plan_feature_badge'),
      t('plan_feature_analytics'),
    ],
  },
])

// Выбор плана
const selectPlan = (planId) => {
  haptic.selection()
  selectedPlan.value = planId
}

// Текущий выбранный план
const currentPlan = computed(() => plans.value.find((p) => p.id === selectedPlan.value))

// Оплата через Telegram Stars
const payWithStars = async () => {
  if (paying.value) return
  haptic.impact('medium')
  paying.value = true

  try {
    // Оплата через Telegram Stars
    await subscriptionsApi.create({ plan: selectedPlan.value, payment_method: 'stars' })
    haptic.notification('success')
    activePlan.value = selectedPlan.value
  } catch (e) {
    haptic.notification('error')
  } finally {
    paying.value = false
  }
}

// Оплата через TON
const payWithTon = async () => {
  if (paying.value) return
  haptic.impact('medium')
  paying.value = true

  try {
    // Оплата через TON (TonConnect)
    await subscriptionsApi.create({ plan: selectedPlan.value, payment_method: 'ton' })
    haptic.notification('success')
    activePlan.value = selectedPlan.value
  } catch (e) {
    haptic.notification('error')
  } finally {
    paying.value = false
  }
}
</script>

<template>
  <div class="subscription-page">
    <!-- Заголовок -->
    <PageHeader
      :title="t('subscription')"
      show-back
    />

    <div class="subscription-content">
      <!-- Баннер активного плана -->
      <div v-if="activePlan" class="card active-plan-banner">
        <span class="active-icon">✅</span>
        <div class="active-info">
          <span class="active-title">{{ t('plan_active') }}</span>
          <span class="active-name">
            {{ plans.find((p) => p.id === activePlan)?.name }}
          </span>
        </div>
      </div>

      <!-- Список тарифных планов -->
      <div class="plans-list">
        <div
          v-for="plan in plans"
          :key="plan.id"
          class="plan-card"
          :class="{
            selected: selectedPlan === plan.id,
            popular: plan.popular,
          }"
          @click="selectPlan(plan.id)"
        >
          <!-- Бейдж популярного плана -->
          <div v-if="plan.popular" class="popular-badge">
            {{ t('plan_popular') }}
          </div>

          <!-- Заголовок плана -->
          <div class="plan-header">
            <span class="plan-icon">{{ plan.icon }}</span>
            <div class="plan-info">
              <span class="plan-name">{{ plan.name }}</span>
              <span class="plan-period">{{ plan.period }}</span>
            </div>
            <!-- Цена -->
            <div class="plan-price">
              <span class="price-amount">${{ plan.price }}</span>
              <span v-if="plan.discount" class="price-discount">
                -{{ plan.discount }}%
              </span>
            </div>
          </div>

          <!-- Список возможностей (для выбранного плана) -->
          <Transition name="expand">
            <div v-if="selectedPlan === plan.id" class="plan-features">
              <div
                v-for="feature in plan.features"
                :key="feature"
                class="feature-item"
              >
                <span class="feature-check">✓</span>
                <span>{{ feature }}</span>
              </div>
            </div>
          </Transition>
        </div>
      </div>

      <!-- Кнопки оплаты -->
      <div class="payment-buttons">
        <!-- Оплата через Telegram Stars -->
        <button
          class="btn btn-primary btn-block pay-btn"
          :disabled="paying || activePlan === selectedPlan"
          @click="payWithStars"
        >
          <span class="pay-icon">⭐</span>
          {{ paying ? t('loading') : t('pay_with_stars', { price: currentPlan?.price }) }}
        </button>

        <!-- Оплата через TON -->
        <button
          class="btn btn-ton btn-block pay-btn"
          :disabled="paying || activePlan === selectedPlan"
          @click="payWithTon"
        >
          <span class="pay-icon">💎</span>
          {{ paying ? t('loading') : t('pay_with_ton') }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.subscription-page {
  padding-bottom: 32px;
}

.subscription-content {
  padding: 0 16px;
}

/* Баннер активного плана */
.active-plan-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  background: rgba(48, 209, 88, 0.1);
  border: 1px solid rgba(48, 209, 88, 0.3);
}

.active-icon {
  font-size: 24px;
}

.active-info {
  display: flex;
  flex-direction: column;
}

.active-title {
  font-size: 13px;
  color: #30D158;
}

.active-name {
  font-size: 15px;
  font-weight: 600;
  color: #fff;
}

/* Список планов */
.plans-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 24px;
}

/* Карточка плана */
.plan-card {
  position: relative;
  padding: 16px;
  background: #1C1C1E;
  border: 2px solid #2C2C2E;
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.plan-card:active {
  transform: scale(0.98);
}

.plan-card.selected {
  border-color: #6C5CE7;
  background: rgba(108, 92, 231, 0.08);
}

.plan-card.popular {
  border-color: #6C5CE7;
}

/* Бейдж "Популярный" */
.popular-badge {
  position: absolute;
  top: -10px;
  right: 14px;
  padding: 3px 10px;
  background: #6C5CE7;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.3px;
}

/* Заголовок плана */
.plan-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.plan-icon {
  font-size: 28px;
}

.plan-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.plan-name {
  font-size: 15px;
  font-weight: 600;
  color: #fff;
}

.plan-period {
  font-size: 12px;
  color: #8E8E93;
  margin-top: 1px;
}

/* Цена */
.plan-price {
  text-align: right;
}

.price-amount {
  font-size: 22px;
  font-weight: 800;
  color: #fff;
}

.price-discount {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: #30D158;
  margin-top: 1px;
}

/* Список возможностей */
.plan-features {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #2C2C2E;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  font-size: 13px;
  color: #C7C7CC;
}

.feature-check {
  color: #6C5CE7;
  font-weight: 700;
  font-size: 14px;
}

/* Анимация раскрытия списка возможностей */
.expand-enter-active,
.expand-leave-active {
  transition: all 0.25s ease;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
  margin-top: 0;
  padding-top: 0;
}

/* Кнопки оплаты */
.payment-buttons {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.pay-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  font-size: 15px;
  font-weight: 600;
}

.pay-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pay-icon {
  font-size: 18px;
}

/* Кнопка TON */
.btn-ton {
  background: #0098EA;
  color: #fff;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-ton:active:not(:disabled) {
  opacity: 0.85;
}
</style>
