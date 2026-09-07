<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { useAuthStore } from '@/stores/auth'
import { usersApi } from '@/api/users'
import PageHeader from '@/components/layout/PageHeader.vue'
import RatingStars from '@/components/shared/RatingStars.vue'

const route = useRoute()
const router = useRouter()
const { t } = useLocale()
const { haptic, user: tgUser } = useTelegram()
const authStore = useAuthStore()

// Загрузка данных
const loading = ref(true)

// Ошибка загрузки
const error = ref(null)

// Данные профиля (загружаются из API)
const profile = ref({
  id: null,
  first_name: '',
  last_name: '',
  username: '',
  rating: 0,
  deliveries_count: 0,
  reviews_count: 0,
  is_verified: false,
  created_at: '',
})

// Статистика пользователя
const stats = computed(() => [
  { label: t('stat_deliveries'), value: profile.value.deliveries_count },
  { label: t('stat_reviews'), value: profile.value.reviews_count },
  { label: t('stat_rating'), value: (profile.value.rating || 0).toFixed(1) },
])

// Отзывы (загружаются из API)
const reviews = ref([])

// Определение: это свой профиль или чужой
const isOwnProfile = computed(() => {
  // Если нет ID в route params — свой профиль
  return !route.params.id || route.params.id == authStore.user?.id
})

// ID пользователя для загрузки
const userId = computed(() => route.params.id || authStore.user?.id)

// Ответ на отзыв: какой отзыв редактируем и текст
const replyingTo = ref(null)
const replyText = ref('')
const replyError = ref('')
const replySending = ref(false)

// Начать ответ
const startReply = (review) => {
  haptic.impact('light')
  replyingTo.value = review.id
  replyText.value = ''
  replyError.value = ''
}

// Отправить ответ на отзыв
const sendReply = async (review) => {
  if (!replyText.value.trim() || replySending.value) return
  replySending.value = true
  try {
    const updated = await usersApi.replyReview(review.id, replyText.value.trim())
    // Обновляем отзыв в списке без перезагрузки
    Object.assign(review, { reply_text: updated.reply_text, reply_created_at: updated.reply_created_at })
    replyingTo.value = null
    haptic.notification('success')
  } catch {
    replyError.value = t('review_reply_error')
    haptic.notification('error')
  } finally {
    replySending.value = false
  }
}

// Дата в коротком виде
const formatDate = (value) => (value ? new Date(value).toLocaleDateString('ru-RU') : '')

// Переход в админ-панель
const openAdmin = () => {
  haptic.impact('light')
  router.push({ name: 'admin' })
}

// Переход к редактированию профиля
const editProfile = () => {
  haptic.impact('light')
  router.push({ name: 'settings' })
}

// Полное имя пользователя
const displayName = computed(() => {
  const first = profile.value.first_name || tgUser.value?.first_name || ''
  const last = profile.value.last_name || ''
  return (first + ' ' + last).trim() || 'User'
})

// Имя пользователя для аватара
const avatarLetter = computed(() => {
  return (profile.value.first_name || tgUser.value?.first_name || 'U')[0].toUpperCase()
})

// Загрузка данных профиля и отзывов из API
onMounted(async () => {
  try {
    // Если свой профиль и данные уже есть в store — используем их
    if (isOwnProfile.value && authStore.user) {
      profile.value = { ...profile.value, ...authStore.user }
    }

    // Загружаем профиль и отзывы параллельно
    const [profileRes, reviewsRes] = await Promise.all([
      usersApi.getProfile(userId.value),
      usersApi.getReviews(userId.value),
    ])

    // Обновляем данные профиля из ответа API (interceptor уже разворачивает response.data)
    profile.value = profileRes
    // Обновляем список отзывов
    reviews.value = reviewsRes.items || reviewsRes
  } catch (e) {
    error.value = e.message || t('error_loading')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="profile-page">
    <!-- Заголовок -->
    <PageHeader
      :title="t('profile_title')"
      show-back
      :right-icon="isOwnProfile ? '⚙️' : ''"
      @right-click="editProfile"
    />

    <!-- Загрузка -->
    <div v-if="loading" class="loading-state">
      <div class="skeleton avatar-skeleton"></div>
      <div class="skeleton" style="width: 50%; height: 20px; margin: 12px auto 6px"></div>
      <div class="skeleton" style="width: 30%; height: 14px; margin: 0 auto"></div>
    </div>

    <div v-else class="profile-content">
      <!-- Шапка профиля: аватар, имя, рейтинг -->
      <div class="profile-header">
        <!-- Аватар -->
        <div class="profile-avatar">
          <span class="avatar-text">{{ avatarLetter }}</span>
          <!-- Бейдж верификации -->
          <span v-if="profile.is_verified" class="verified-badge">✓</span>
        </div>

        <!-- Имя пользователя -->
        <h2 class="profile-name">{{ displayName }}</h2>
        <span class="profile-username">{{ profile.username }}</span>

        <!-- Рейтинг (звёзды) -->
        <RatingStars :value="profile.rating" size="md" />

        <!-- Статус верификации -->
        <div class="verification-status" :class="{ verified: profile.is_verified }">
          <span class="verification-icon">{{ profile.is_verified ? '🛡️' : '⚠️' }}</span>
          <span>{{ profile.is_verified ? t('verified') : t('not_verified') }}</span>
        </div>
      </div>

      <!-- Статистика: доставки, отзывы, рейтинг -->
      <div class="stats-grid">
        <div v-for="stat in stats" :key="stat.label" class="stat-card">
          <span class="stat-value">{{ stat.value }}</span>
          <span class="stat-label">{{ stat.label }}</span>
        </div>
      </div>

      <!-- Кнопка редактирования (для своего профиля) -->
      <button
        v-if="isOwnProfile"
        class="btn btn-outline btn-block edit-btn"
        @click="editProfile"
      >
        {{ t('edit_profile') }}
      </button>

      <!-- Вход в админ-панель — только администратору -->
      <button
        v-if="isOwnProfile && authStore.isAdmin"
        class="btn btn-primary btn-block edit-btn"
        @click="openAdmin"
      >
        🛠 {{ t('admin_panel') }}
      </button>

      <!-- Список отзывов -->
      <div class="section">
        <h3 class="section-title">{{ t('reviews') }} ({{ reviews.length }})</h3>

        <!-- Пустое состояние отзывов -->
        <div v-if="reviews.length === 0" class="empty-reviews">
          <p>{{ t('no_reviews') }}</p>
        </div>

        <!-- Карточки отзывов -->
        <div
          v-for="review in reviews"
          :key="review.id"
          class="card review-card"
        >
          <!-- Заголовок отзыва: автор и рейтинг -->
          <div class="review-header">
            <div class="review-author">
              <div class="review-avatar">{{ (review.author_name || '?')[0] }}</div>
              <span class="review-name">{{ review.author_name || '?' }}</span>
            </div>
            <RatingStars :value="review.rating" size="sm" />
          </div>
          <!-- Теги-похвалы -->
          <div v-if="review.tags?.length" class="review-tags">
            <span v-for="tag in review.tags" :key="tag" class="review-tag">{{ t('tag_' + tag) }}</span>
          </div>
          <!-- Текст отзыва -->
          <p v-if="review.comment" class="review-text">{{ review.comment }}</p>
          <!-- Дата отзыва -->
          <span class="review-date">{{ formatDate(review.created_at) }}</span>

          <!-- Ответ получателя отзыва -->
          <div v-if="review.reply_text" class="review-reply">
            <span class="reply-label">{{ t('review_reply_label') }} · {{ displayName }}</span>
            <p class="reply-text">{{ review.reply_text }}</p>
          </div>

          <!-- Форма ответа: только на своём профиле и пока ответа нет -->
          <template v-else-if="isOwnProfile">
            <button v-if="replyingTo !== review.id" class="reply-btn" @click="startReply(review)">
              💬 {{ t('review_reply') }}
            </button>
            <div v-else class="reply-form">
              <textarea
                v-model="replyText"
                class="input"
                rows="2"
                maxlength="500"
                :placeholder="t('review_reply_placeholder')"
              ></textarea>
              <p v-if="replyError" class="reply-error">{{ replyError }}</p>
              <div class="reply-actions">
                <button class="btn btn-primary" :disabled="replySending || !replyText.trim()" @click="sendReply(review)">
                  {{ t('review_reply_send') }}
                </button>
                <button class="btn btn-secondary" @click="replyingTo = null">{{ t('cancel') }}</button>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Теги и ответы в отзывах */
.review-tags { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; }
.review-tag { padding: 3px 10px; border-radius: 999px; background: var(--primary-soft); color: var(--primary); font-size: 12px; font-weight: 600; }
.review-reply { margin-top: 10px; padding: 10px 12px; background: var(--surface-2); border-radius: 10px; border-left: 3px solid var(--primary); }
.reply-label { font-size: 12px; color: var(--text-3); display: block; margin-bottom: 4px; }
.reply-text { font-size: 14px; color: var(--text-1); line-height: 1.4; }
.reply-btn { margin-top: 8px; background: none; border: none; color: var(--primary); font-size: 13px; font-weight: 600; cursor: pointer; padding: 0; }
.reply-form { margin-top: 10px; display: flex; flex-direction: column; gap: 8px; }
.reply-actions { display: flex; gap: 8px; }
.reply-actions .btn { flex: 1; padding: 10px; font-size: 14px; }
.reply-error { color: var(--danger); font-size: 12px; }

.profile-page {
  padding-bottom: 32px;
}

.profile-content {
  padding: 0 16px;
}

/* Загрузка */
.loading-state {
  padding: 40px 16px;
  text-align: center;
}

.avatar-skeleton {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  margin: 0 auto;
}

/* Шапка профиля */
.profile-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 0;
}

/* Аватар профиля */
.profile-avatar {
  position: relative;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: var(--primary);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}

.avatar-text {
  font-size: 32px;
  font-weight: 800;
  color: var(--on-accent);
}

/* Бейдж верификации на аватаре */
.verified-badge {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 24px;
  height: 24px;
  background: var(--success);
  border-radius: 50%;
  border: 3px solid var(--bg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--on-accent);
  font-weight: 700;
}

/* Имя и юзернейм */
.profile-name {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-1);
  margin-bottom: 2px;
}

.profile-username {
  font-size: 14px;
  color: var(--text-2);
  margin-bottom: 10px;
}

/* Статус верификации */
.verification-status {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  background: rgba(255, 69, 58, 0.1);
  color: var(--danger);
}

.verification-status.verified {
  background: rgba(48, 209, 88, 0.1);
  color: var(--success);
}

.verification-icon {
  font-size: 14px;
}

/* Сетка статистики */
.stats-grid {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.stat-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 14px 8px;
  background: var(--surface);
  border-radius: 12px;
}

.stat-value {
  font-size: 22px;
  font-weight: 800;
  color: var(--text-1);
}

.stat-label {
  font-size: 11px;
  color: var(--text-2);
  margin-top: 4px;
  text-align: center;
}

/* Кнопка редактирования */
.btn-outline {
  background: transparent;
  border: 1px solid var(--border-strong);
  color: var(--text-1);
  padding: 12px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-outline:active {
  background: var(--surface-2);
}

.edit-btn {
  margin-bottom: 24px;
}

/* Секция отзывов */
.section {
  margin-bottom: 20px;
}

.section-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-1);
  margin-bottom: 12px;
}

/* Пустое состояние отзывов */
.empty-reviews {
  text-align: center;
  padding: 30px;
  color: var(--text-2);
  font-size: 14px;
}

/* Карточка отзыва */
.review-card {
  margin-bottom: 8px;
}

.review-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.review-author {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Аватар автора отзыва */
.review-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--surface-3);
  color: var(--text-1);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}

.review-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-1);
}

/* Текст отзыва */
.review-text {
  font-size: 13px;
  color: var(--text-3);
  line-height: 1.4;
  margin-bottom: 6px;
}

/* Дата отзыва */
.review-date {
  font-size: 11px;
  color: var(--text-3);
}</style>
