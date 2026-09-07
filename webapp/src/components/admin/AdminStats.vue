<script setup>
import { ref, computed, onMounted } from 'vue'
import { useLocale } from '@/composables/useLocale'
import { adminApi } from '@/api/admin'

const { t } = useLocale()

// Сводка с бэкенда
const stats = ref(null)

// Ошибка загрузки
const error = ref('')

// Карточки: заголовок и строки label/value. Считаются из stats.
const cards = computed(() => {
  const s = stats.value
  if (!s) return []
  return [
    {
      title: t('admin_stats_users'),
      rows: [
        [t('admin_stats_total'), s.users.total],
        [t('admin_stats_today'), s.users.today],
        [t('admin_stats_week'), s.users.week],
        [t('admin_stats_with_phone'), s.users.with_phone],
        [t('admin_stats_travelers'), s.users.travelers],
        [t('admin_stats_blocked'), s.users.blocked],
      ],
    },
    {
      title: t('admin_stats_parcels'),
      rows: [
        [t('admin_stats_total'), s.parcels.total],
        [t('admin_stats_open'), s.parcels.open],
        [t('admin_stats_active'), s.parcels.active],
        [t('admin_stats_delivered'), s.parcels.delivered],
        [t('admin_stats_today'), s.parcels.today],
      ],
    },
    {
      title: t('admin_stats_flights'),
      rows: [
        [t('admin_stats_total'), s.flights.total],
        [t('admin_stats_active'), s.flights.active],
        [t('admin_stats_today'), s.flights.today],
        [t('admin_stats_matches'), s.matches.total],
      ],
    },
    {
      title: t('admin_stats_revenue'),
      rows: [
        [t('admin_stats_stars_total'), `${s.revenue.stars_total} ⭐`],
        [t('admin_stats_stars_today'), `${s.revenue.stars_today} ⭐`],
        [t('admin_stats_payments'), s.revenue.payments],
      ],
    },
    {
      title: t('admin_stats_other'),
      rows: [
        [t('admin_stats_reports_open'), s.reports.open],
        [t('admin_stats_groups_active'), s.groups.active],
        [t('admin_stats_posts'), s.groups.posts],
        [t('admin_stats_reviews'), s.reviews.total],
        [t('admin_stats_avg_rating'), s.reviews.avg],
      ],
    },
  ]
})

// Загрузка сводки
const load = async () => {
  error.value = ''
  try {
    stats.value = await adminApi.stats()
  } catch {
    error.value = t('admin_error')
  }
}

onMounted(load)
</script>

<template>
  <div class="stats">
    <!-- Ошибка -->
    <p v-if="error" class="error-text">{{ error }}</p>

    <!-- Загрузка -->
    <p v-else-if="!stats" class="muted">{{ t('admin_loading') }}</p>

    <!-- Карточки сводки -->
    <div v-for="card in cards" :key="card.title" class="card stat-card">
      <div class="card-title">{{ card.title }}</div>
      <!-- Строка метрики -->
      <div v-for="row in card.rows" :key="row[0]" class="row">
        <span class="row-label">{{ row[0] }}</span>
        <span class="row-value">{{ row[1] }}</span>
      </div>
    </div>

    <!-- Обновить -->
    <button v-if="stats" class="btn btn-secondary btn-block" @click="load">
      {{ t('admin_refresh') }}
    </button>
  </div>
</template>

<style scoped>
.stats {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.stat-card {
  padding: 14px;
}

.card-title {
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 8px;
}

.row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-top: 1px solid var(--border);
  font-size: 14px;
}

.row-label {
  color: var(--text-2);
}

.row-value {
  font-weight: 600;
}

.error-text {
  color: var(--danger);
  font-size: 13px;
}

.muted {
  color: var(--text-2);
  font-size: 13px;
}
</style>
