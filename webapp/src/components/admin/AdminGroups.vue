<script setup>
import { ref, onMounted } from 'vue'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { adminApi } from '@/api/admin'

const { t } = useLocale()
const { haptic } = useTelegram()

// Ссылка / @username / ID новой группы
const link = ref('')
const adding = ref(false)
const addError = ref('')

// Реестр групп
const items = ref([])
const loading = ref(false)
const error = ref('')

// Группа, ожидающая подтверждения удаления
const confirmId = ref(null)

// Коды ошибок подключения, у которых есть свой текст
const knownErrors = ['bad_link', 'invite_link', 'not_found', 'not_group', 'no_token']

// Загрузка реестра
const load = async () => {
  loading.value = true
  error.value = ''
  try {
    items.value = (await adminApi.groups()).items
  } catch {
    error.value = t('admin_error')
  } finally {
    loading.value = false
  }
}

// Подключить группу по ссылке
const add = async () => {
  const value = link.value.trim()
  if (!value || adding.value) return
  haptic.impact('medium')
  adding.value = true
  addError.value = ''
  try {
    const group = await adminApi.addGroup(value)
    // Повторное подключение обновляет карточку — не дублируем
    items.value = [group, ...items.value.filter((g) => g.id !== group.id)]
    link.value = ''
    haptic.notification('success')
  } catch (e) {
    haptic.notification('error')
    const code = e?.response?.data?.detail
    addError.value = knownErrors.includes(code) ? t('admin_group_err_' + code) : t('admin_error')
  } finally {
    adding.value = false
  }
}

// Сохранить поле группы и заменить карточку ответом сервера
const patch = async (group, data) => {
  error.value = ''
  try {
    const updated = await adminApi.updateGroup(group.id, data)
    items.value = items.value.map((g) => (g.id === group.id ? updated : g))
    haptic.selection()
  } catch {
    haptic.notification('error')
    error.value = t('admin_error')
  }
}

// Переключатели: включена, посылки, рейсы
const toggleField = (group, field) => patch(group, { [field]: !group[field] })

// Фильтр городов сохраняется при потере фокуса
const saveCities = (group, event) => {
  const value = event.target.value.trim()
  if ((group.cities || '') === value) return
  patch(group, { cities: value })
}

// Удаление в два нажатия
const remove = async (group) => {
  if (confirmId.value !== group.id) {
    haptic.impact('light')
    confirmId.value = group.id
    return
  }
  try {
    await adminApi.deleteGroup(group.id)
    items.value = items.value.filter((g) => g.id !== group.id)
    haptic.notification('success')
  } catch {
    haptic.notification('error')
    error.value = t('admin_error')
  } finally {
    confirmId.value = null
  }
}

onMounted(load)
</script>

<template>
  <div class="groups">
    <!-- Подсказка: сначала добавить бота в группу -->
    <p class="hint">{{ t('admin_groups_hint') }}</p>

    <!-- Форма подключения -->
    <div class="add-form">
      <input v-model="link" class="input" :placeholder="t('admin_groups_link_placeholder')" @keyup.enter="add" />
      <button class="btn btn-primary" :disabled="adding || !link.trim()" @click="add">
        {{ adding ? '…' : t('admin_groups_add') }}
      </button>
    </div>
    <p v-if="addError" class="error-text">{{ addError }}</p>

    <p v-if="error" class="error-text">{{ error }}</p>
    <p v-if="loading" class="muted">{{ t('admin_loading') }}</p>
    <p v-else-if="!items.length" class="muted">{{ t('admin_groups_empty') }}</p>

    <!-- Карточка группы -->
    <div v-for="g in items" :key="g.id" class="card group-card" :class="{ inactive: !g.is_active || !g.is_member }">
      <div class="group-top">
        <div class="group-main">
          <span class="group-title">{{ g.title || g.chat_id }}</span>
          <span class="group-sub">{{ g.username ? '@' + g.username : g.chat_id }} · {{ t('admin_groups_posts') }}: {{ g.posts_count }}</span>
        </div>
        <!-- Бота выгнали — постить некуда -->
        <span v-if="!g.is_member" class="badge badge-red">{{ t('admin_groups_bot_removed') }}</span>
      </div>

      <!-- Переключатели -->
      <div class="toggles">
        <div class="toggle-row" @click="toggleField(g, 'is_active')">
          <span>{{ t('admin_groups_enabled') }}</span>
          <div class="toggle" :class="{ active: g.is_active }"><div class="toggle-thumb"></div></div>
        </div>
        <div class="toggle-row" @click="toggleField(g, 'post_parcels')">
          <span>📦 {{ t('admin_groups_post_parcels') }}</span>
          <div class="toggle" :class="{ active: g.post_parcels }"><div class="toggle-thumb"></div></div>
        </div>
        <div class="toggle-row" @click="toggleField(g, 'post_flights')">
          <span>✈️ {{ t('admin_groups_post_flights') }}</span>
          <div class="toggle" :class="{ active: g.post_flights }"><div class="toggle-thumb"></div></div>
        </div>
      </div>

      <!-- Фильтр городов -->
      <label class="cities-label">{{ t('admin_groups_cities') }}</label>
      <input
        :value="g.cities || ''"
        class="input input-sm"
        :placeholder="t('admin_groups_cities_placeholder')"
        @blur="saveCities(g, $event)"
      />

      <!-- Удаление -->
      <button class="btn btn-sm btn-outline danger-outline" @click="remove(g)">
        {{ confirmId === g.id ? t('admin_confirm_delete') : t('admin_action_delete') }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.groups {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hint {
  font-size: 13px;
  color: var(--text-2);
}

.add-form {
  display: flex;
  gap: 8px;
}

.add-form .input {
  flex: 1;
}

.add-form .btn:disabled {
  opacity: 0.5;
}

.group-card {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.group-card.inactive {
  opacity: 0.7;
}

.group-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}

.group-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.group-title {
  font-size: 15px;
  font-weight: 600;
}

.group-sub {
  font-size: 12px;
  color: var(--text-2);
  word-break: break-all;
}

.toggles {
  display: flex;
  flex-direction: column;
}

.toggle-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  font-size: 14px;
  border-top: 1px solid var(--border);
  cursor: pointer;
}

/* Тогл в стиле настроек */
.toggle {
  width: 44px;
  height: 26px;
  border-radius: 13px;
  background: var(--surface-3);
  position: relative;
  transition: background 0.2s;
}

.toggle.active {
  background: var(--primary);
}

.toggle-thumb {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #fff;
  position: absolute;
  top: 2px;
  left: 2px;
  transition: transform 0.2s;
}

.toggle.active .toggle-thumb {
  transform: translateX(18px);
}

.cities-label {
  font-size: 12px;
  color: var(--text-2);
}

.input-sm {
  padding: 8px 12px;
  font-size: 14px;
}

.btn-sm {
  padding: 8px 12px;
  font-size: 13px;
  align-self: flex-start;
}

.danger-outline {
  color: var(--danger);
  border-color: var(--danger);
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
