import { ref, computed, onMounted, onUnmounted } from 'vue'

/**
 * Composable для работы с Telegram WebApp SDK.
 * Обёртка над window.Telegram.WebApp.
 */
export function useTelegram() {
  // Объект Telegram WebApp
  const tg = window.Telegram?.WebApp

  // Данные пользователя из Telegram
  const user = computed(() => tg?.initDataUnsafe?.user || null)

  // initData для авторизации на backend
  const initData = computed(() => tg?.initData || '')

  // Цветовая схема (light/dark)
  const colorScheme = computed(() => tg?.colorScheme || 'dark')

  // Параметры темы
  const themeParams = computed(() => tg?.themeParams || {})

  /**
   * Инициализация WebApp — вызвать при монтировании приложения.
   */
  const ready = () => {
    if (tg) {
      // Уведомляем Telegram что приложение готово
      tg.ready()
      // Разворачиваем на весь экран
      tg.expand()
    }
  }

  /**
   * Показать кнопку "Назад" в заголовке Telegram.
   */
  const showBackButton = (callback) => {
    if (tg?.BackButton) {
      tg.BackButton.show()
      tg.BackButton.onClick(callback)
    }
  }

  /**
   * Скрыть кнопку "Назад".
   */
  const hideBackButton = () => {
    if (tg?.BackButton) {
      tg.BackButton.hide()
      tg.BackButton.offClick()
    }
  }

  /**
   * Показать главную кнопку внизу экрана (MainButton).
   */
  const showMainButton = (text, callback) => {
    if (tg?.MainButton) {
      tg.MainButton.setText(text)
      tg.MainButton.show()
      tg.MainButton.onClick(callback)
    }
  }

  /**
   * Скрыть главную кнопку.
   */
  const hideMainButton = () => {
    if (tg?.MainButton) {
      tg.MainButton.hide()
      tg.MainButton.offClick()
    }
  }

  /**
   * Тактильная обратная связь (вибрация).
   */
  const haptic = {
    // Лёгкий тап (нажатие кнопки)
    impact: (style = 'light') => tg?.HapticFeedback?.impactOccurred(style),
    // Уведомление (успех/ошибка/предупреждение)
    notification: (type = 'success') => tg?.HapticFeedback?.notificationOccurred(type),
    // Выбор элемента
    selection: () => tg?.HapticFeedback?.selectionChanged(),
  }

  /**
   * Закрыть Mini App.
   */
  const close = () => tg?.close()

  return {
    tg,
    user,
    initData,
    colorScheme,
    themeParams,
    ready,
    showBackButton,
    hideBackButton,
    showMainButton,
    hideMainButton,
    haptic,
    close,
  }
}
