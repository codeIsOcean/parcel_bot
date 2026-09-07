<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { usersApi } from '@/api/users'
import { parcelsApi } from '@/api/parcels'
import PageHeader from '@/components/layout/PageHeader.vue'
import RatingStars from '@/components/shared/RatingStars.vue'

const router = useRouter()
const { t } = useLocale()
const { haptic } = useTelegram()

// ID доставки из пропсов
const props = defineProps({
  id: { type: [String, Number], required: true },
})

// Рейтинг (1-5 звёзд)
const rating = ref(0)

// Текст комментария
const comment = ref('')

// Теги-похвалы: быстрый отзыв одним касанием
const TAGS = ['on_time', 'careful', 'polite', 'good_price', 'recommended']
const selectedTags = ref([])
const toggleTag = (tag) => {
  haptic.selection()
  const idx = selectedTags.value.indexOf(tag)
  if (idx >= 0) selectedTags.value.splice(idx, 1)
  else selectedTags.value.push(tag)
}

// Статус отправки
const submitting = ref(false)

// Статус успешной отправки
const submitted = ref(false)

// Загрузка информации о доставке
const loading = ref(true)

// Информация о доставке (загружается из API)
const delivery = ref({
  from_city: '',
  to_city: '',
  traveler_name: '',
  traveler_id: null,
})

// Валидация — обязательно выбрать рейтинг и иметь traveler_id
const isValid = computed(() => rating.value > 0 && delivery.value.traveler_id)

// Обновление рейтинга через RatingStars
const updateRating = (value) => {
  haptic.selection()
  rating.value = value
}

// Загрузка данных о доставке при монтировании
onMounted(async () => {
  try {
    const data = await parcelsApi.getById(props.id)
    delivery.value = {
      from_city: data.from_city || '',
      to_city: data.to_city || '',
      traveler_name: data.traveler_name || '',
      traveler_id: data.traveler_id || null,
    }
  } catch (e) {
    // Ошибка загрузки данных доставки
  } finally {
    loading.value = false
  }
})

// Отправка отзыва
const submitReview = async () => {
  if (!isValid.value || submitting.value) return

  haptic.impact('medium')
  submitting.value = true

  try {
    // Отправка отзыва через API
    await usersApi.createReview(delivery.value.traveler_id, {
      rating: rating.value,
      comment: comment.value,
      tags: selectedTags.value,
      parcel_id: props.id,
    })

    // Успешная отправка
    haptic.notification('success')
    submitted.value = true
  } catch (e) {
    haptic.notification('error')
  } finally {
    submitting.value = false
  }
}

// Возврат на главную после отправки
const goHome = () => {
  router.push({ name: 'home' })
}
</script>

<template>
  <div class="rate-page">
    <!-- Заголовок -->
    <PageHeader
      :title="t('rate_delivery')"
      show-back
    />

    <div class="rate-content">
      <!-- Состояние: отзыв успешно отправлен -->
      <div v-if="submitted" class="success-state">
        <span class="success-icon">🎉</span>
        <h2 class="success-title">{{ t('rate_success') }}</h2>
        <p class="success-text">{{ t('rate_success_text') }}</p>
        <button class="btn btn-primary btn-block" @click="goHome">
          {{ t('go_home') }}
        </button>
      </div>

      <!-- Форма оценки -->
      <template v-else>
        <!-- Информация о доставке -->
        <div class="card delivery-info">
          <div class="delivery-route">
            {{ delivery.from_city }} → {{ delivery.to_city }}
          </div>
          <div class="delivery-traveler">
            {{ t('traveler') }}: {{ delivery.traveler_name }}
          </div>
        </div>

        <!-- Блок выбора рейтинга -->
        <div class="rating-section">
          <h3 class="rating-title">{{ t('rate_question') }}</h3>

          <!-- Интерактивные звёзды (можно выбирать) -->
          <RatingStars
            :value="rating"
            interactive
            size="lg"
            @update:value="updateRating"
          />

          <!-- Подсказка по рейтингу -->
          <p v-if="rating > 0" class="rating-hint">
            {{ t('rate_label_' + rating) }}
          </p>
        </div>

        <!-- Теги-похвалы -->
        <div class="form-group">
          <label class="form-label">{{ t('rate_tags_title') }}</label>
          <div class="tags-row">
            <button
              v-for="tag in TAGS"
              :key="tag"
              type="button"
              class="tag-chip"
              :class="{ active: selectedTags.includes(tag) }"
              @click="toggleTag(tag)"
            >
              {{ t('tag_' + tag) }}
            </button>
          </div>
        </div>

        <!-- Поле комментария -->
        <div class="form-group">
          <label class="form-label">{{ t('rate_comment') }}</label>
          <textarea
            v-model="comment"
            class="input textarea"
            :placeholder="t('rate_comment_placeholder')"
            rows="4"
          ></textarea>
        </div>

        <!-- Кнопка отправки -->
        <button
          class="btn btn-primary btn-block submit-btn"
          :disabled="!isValid || submitting"
          @click="submitReview"
        >
          {{ submitting ? t('loading') : t('submit_review') }}
        </button>
      </template>
    </div>
  </div>
</template>

<style scoped>
/* Теги-похвалы */
.tags-row { display: flex; flex-wrap: wrap; gap: 8px; }
.tag-chip {
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid var(--border-strong);
  background: var(--surface-2);
  color: var(--text-1);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.tag-chip.active { background: var(--primary-soft); border-color: var(--primary); color: var(--primary); }

.rate-page {
  padding-bottom: 32px;
}

.rate-content {
  padding: 0 16px;
}

/* Информация о доставке */
.delivery-info {
  margin-bottom: 24px;
  text-align: center;
}

.delivery-route {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-1);
  margin-bottom: 4px;
}

.delivery-traveler {
  font-size: 13px;
  color: var(--text-2);
}

/* Секция рейтинга */
.rating-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 0 24px;
}

.rating-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-1);
  margin-bottom: 16px;
}

/* Подсказка текущего рейтинга */
.rating-hint {
  margin-top: 10px;
  font-size: 14px;
  color: var(--primary);
  font-weight: 500;
}

/* Форма */
.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-2);
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.textarea {
  resize: none;
  min-height: 100px;
}

/* Кнопка отправки */
.submit-btn {
  padding: 16px;
  font-size: 16px;
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Состояние успешной отправки */
.success-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 60px 20px;
}

.success-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.success-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-1);
  margin-bottom: 8px;
}

.success-text {
  font-size: 14px;
  color: var(--text-2);
  margin-bottom: 32px;
  line-height: 1.4;
}</style>
