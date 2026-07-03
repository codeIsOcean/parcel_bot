<script setup>
/**
 * Компонент рейтинга — звёзды (1-5).
 * Режим отображения (readonly) и режим ввода (interactive).
 */
const props = defineProps({
  // Текущий рейтинг (0-5)
  value: { type: Number, default: 0 },
  // Интерактивный режим (можно выбирать звёзды)
  interactive: { type: Boolean, default: false },
  // Размер звёзд
  size: { type: String, default: 'sm' },
})

const emit = defineEmits(['update:value'])

// Обработка клика по звезде
const setRating = (star) => {
  if (props.interactive) {
    emit('update:value', star)
  }
}
</script>

<template>
  <!-- Звёзды рейтинга -->
  <div class="rating-stars" :class="[size, { interactive }]">
    <span
      v-for="star in 5"
      :key="star"
      class="star"
      :class="{ filled: star <= value }"
      @click="setRating(star)"
    >
      ★
    </span>
    <!-- Числовое значение рядом -->
    <span v-if="!interactive && value > 0" class="rating-number">
      {{ value.toFixed(1) }}
    </span>
  </div>
</template>

<style scoped>
.rating-stars {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.star {
  color: #3A3A3C;
  transition: color 0.15s;
}

.star.filled {
  color: #FFD60A;
}

.interactive .star {
  cursor: pointer;
}

.interactive .star:hover {
  transform: scale(1.2);
}

.rating-number {
  margin-left: 4px;
  font-size: 13px;
  font-weight: 600;
  color: #8E8E93;
}

/* Размеры */
.sm .star { font-size: 14px; }
.md .star { font-size: 22px; }
.lg .star { font-size: 32px; }
</style>
