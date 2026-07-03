<script setup>
import RatingStars from './RatingStars.vue'
import { useLocale } from '@/composables/useLocale'

const { t } = useLocale()

/**
 * Карточка попутчика в списке.
 * Показывает: аватар, имя, рейтинг, вес, цену, дату, рейс.
 */
const props = defineProps({
  traveler: { type: Object, required: true },
})

const emit = defineEmits(['select'])

// Генерируем цвет аватара по ID перевозчика
const avatarColors = ['#6C5CE7', '#30D158', '#FF453A', '#FFD60A', '#FF9500', '#5AC8FA', '#AF52DE']
const avatarColor = avatarColors[(props.traveler.traveler_id || 0) % avatarColors.length]

// Инициалы для аватара (безопасно обрабатываем пустое имя)
const name = props.traveler.traveler_name || '?'
const initials = name
  .split(' ')
  .filter(w => w.length > 0)
  .map(w => w[0])
  .join('')
  .substring(0, 2)
  .toUpperCase() || '?'
</script>

<template>
  <!-- Карточка попутчика -->
  <div class="card traveler-card" @click="emit('select', traveler)">
    <div class="traveler-top">
      <!-- Аватар с инициалами -->
      <div class="avatar" :style="{ background: avatarColor }">
        {{ initials }}
      </div>

      <!-- Информация о попутчике -->
      <div class="traveler-info">
        <!-- Имя + верификация -->
        <div class="traveler-name">
          <span>{{ traveler.traveler_name }}</span>
          <span v-if="traveler.traveler_verified" class="verified-badge">✓</span>
        </div>
        <!-- Рейтинг + количество поездок -->
        <div class="traveler-meta">
          <RatingStars :value="traveler.traveler_rating" size="sm" />
          <span class="trips">· {{ t('trips_count', { count: traveler.traveler_trips || 0 }) }}</span>
        </div>
      </div>

      <!-- Вес и дата справа -->
      <div class="traveler-right">
        <span class="weight">{{ traveler.available_kg }} {{ t('kg') }}</span>
        <span class="date">{{ traveler.flight_date }}</span>
      </div>
    </div>

    <!-- Теги: рейс + цена -->
    <div class="traveler-tags">
      <span v-if="traveler.flight_number" class="tag tag-flight">
        {{ traveler.flight_number }}
      </span>
      <span class="tag tag-price">
        ~${{ traveler.price_per_kg }}{{ t('per_kg') }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.traveler-card {
  cursor: pointer;
  transition: transform 0.1s;
}

.traveler-card:active {
  transform: scale(0.98);
}

.traveler-top {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.traveler-info {
  flex: 1;
  min-width: 0;
}

.traveler-name {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 15px;
  font-weight: 600;
  color: #fff;
}

.verified-badge {
  color: #30D158;
  font-size: 13px;
}

.traveler-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 2px;
}

.trips {
  font-size: 13px;
  color: #8E8E93;
}

.traveler-right {
  text-align: right;
  flex-shrink: 0;
}

.weight {
  font-size: 15px;
  font-weight: 700;
  color: #30D158;
  display: block;
}

.date {
  font-size: 12px;
  color: #8E8E93;
  margin-top: 2px;
}

.traveler-tags {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.tag {
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

.tag-flight {
  background: rgba(142, 142, 147, 0.15);
  color: #8E8E93;
}

.tag-price {
  background: rgba(48, 209, 88, 0.12);
  color: #30D158;
}
</style>
