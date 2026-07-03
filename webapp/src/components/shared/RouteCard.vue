<script setup>
import { useLocale } from '@/composables/useLocale'

const { t } = useLocale()

/**
 * Карточка популярного маршрута.
 * Показывает: флаги, маршрут, количество попутчиков.
 */
const props = defineProps({
  route: { type: Object, required: true },
})

const emit = defineEmits(['select'])

// Флаги стран (эмодзи)
const cityFlags = {
  'Dubai': '🇦🇪',
  'Almaty': '🇰🇿',
  'Moscow': '🇷🇺',
  'New York': '🇺🇸',
  'Istanbul': '🇹🇷',
  'Astana': '🇰🇿',
}
</script>

<template>
  <!-- Карточка маршрута -->
  <div class="card route-card" @click="emit('select', route)">
    <!-- Флаги стран -->
    <div class="route-flags">
      <span>{{ cityFlags[route.from_city] || '🌍' }}</span>
      <span>{{ cityFlags[route.to_city] || '🌍' }}</span>
    </div>

    <!-- Информация о маршруте -->
    <div class="route-info">
      <div class="route-name">{{ route.from_city }} → {{ route.to_city }}</div>
      <div class="route-count">{{ t('travelers_count', { count: route.travelers_count || 0 }) }}</div>
    </div>

    <!-- Стрелка перехода -->
    <span class="route-arrow">›</span>
  </div>
</template>

<style scoped>
.route-card {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: transform 0.1s;
}

.route-card:active {
  transform: scale(0.98);
}

.route-flags {
  display: flex;
  gap: 2px;
  font-size: 24px;
}

.route-info {
  flex: 1;
}

.route-name {
  font-size: 15px;
  font-weight: 600;
  color: #fff;
}

.route-count {
  font-size: 13px;
  color: #8E8E93;
  margin-top: 2px;
}

.route-arrow {
  font-size: 20px;
  color: #8E8E93;
}
</style>
