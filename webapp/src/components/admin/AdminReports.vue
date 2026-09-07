<script setup>
import { ref, onMounted } from 'vue'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { adminApi } from '@/api/admin'

const { t } = useLocale()
const { haptic } = useTelegram()

// Фильтр: открытые или все
const status = ref('open')

// Список жалоб
const items = ref([])
const loading = ref(false)
const error = ref('')

// Дата в коротком виде
const fmtDate = (value) => (value ? new Date(value).toLocaleDateString('ru-RU') : '')

// Загрузка жалоб
const load = async () => {
  loading.value = true
  error.value = ''
  try {
    items.value = (await adminApi.reports(status.value)).items
  } catch {
    error.value = t('admin_error')
  } finally {
    loading.value = false
  }
}

// Смена фильтра
const setStatus = (s) => {
  haptic.selection()
  status.value = s
  load()
}

// Закрыть жалобу: reviewed (мер нет) или confirmed (меры приняты)
const resolve = async (report, newStatus) => {
  error.value = ''
  try {
    const result = await adminApi.resolveReport(report.id, newStatus)
    // В фильтре «открытые» закрытая жалоба исчезает, в «все» — меняет статус
    items.value = status.value === 'open'
      ? items.value.filter((r) => r.id !== report.id)
      : items.value.map((r) => (r.id === report.id ? { ...r, status: result.status } : r))
    haptic.notification('success')
  } catch {
    haptic.notification('error')
    error.value = t('admin_error')
  }
}

// Быстрая блокировка нарушителя
const blockTarget = async (report) => {
  error.value = ''
  try {
    await adminApi.block(report.target_id, true)
    items.value = items.value.map((r) => (r.target_id === report.target_id ? { ...r, target_blocked: true } : r))
    haptic.notification('success')
  } catch (e) {
    haptic.notification('error')
    const code = e?.response?.data?.detail
    error.value = typeof code === 'string' ? t('admin_err_' + code) : t('admin_error')
  }
}

onMounted(load)
</script>

<template>
  <div class="reports">
    <!-- Фильтр -->
    <div class="chips">
      <button class="chip" :class="{ active: status === 'open' }" @click="setStatus('open')">{{ t('admin_reports_open') }}</button>
      <button class="chip" :class="{ active: status === 'all' }" @click="setStatus('all')">{{ t('admin_filter_all') }}</button>
    </div>

    <p v-if="error" class="error-text">{{ error }}</p>
    <p v-if="loading" class="muted">{{ t('admin_loading') }}</p>
    <p v-else-if="!items.length" class="muted">{{ t('admin_reports_empty') }}</p>

    <!-- Карточка жалобы -->
    <div v-for="r in items" :key="r.id" class="card report-card">
      <div class="report-top">
        <span class="report-reason">{{ t('admin_reason_' + r.reason) }}</span>
        <span class="badge" :class="r.status === 'open' ? 'badge-yellow' : 'badge-green'">
          {{ t('admin_report_status_' + r.status) }}
        </span>
      </div>
      <p v-if="r.comment" class="report-comment">{{ r.comment }}</p>
      <!-- Кто на кого -->
      <div class="report-meta">
        <span>{{ r.author_name || r.author_id }} → <b>{{ r.target_name || r.target_id }}</b></span>
        <span>{{ fmtDate(r.created_at) }}</span>
      </div>
      <div v-if="r.parcel_id" class="report-meta">
        <span>{{ t('admin_tab_parcels') }} #{{ r.parcel_id }}</span>
        <span v-if="r.target_blocked" class="badge badge-red">{{ t('admin_badge_blocked') }}</span>
      </div>
      <!-- Действия -->
      <div v-if="r.status === 'open'" class="actions">
        <button class="btn btn-sm btn-secondary" @click="resolve(r, 'reviewed')">{{ t('admin_report_reviewed') }}</button>
        <button class="btn btn-sm btn-primary" @click="resolve(r, 'confirmed')">{{ t('admin_report_confirmed') }}</button>
        <button v-if="!r.target_blocked" class="btn btn-sm btn-danger" @click="blockTarget(r)">{{ t('admin_action_block') }}</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.reports {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chips {
  display: flex;
  gap: 6px;
}

.report-card {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.report-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.report-reason {
  font-size: 15px;
  font-weight: 600;
}

.report-comment {
  font-size: 13px;
  color: var(--text-1);
}

.report-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-2);
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}

.btn-sm {
  padding: 8px 12px;
  font-size: 13px;
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
