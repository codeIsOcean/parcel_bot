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

  // Параметр запуска из ссылки t.me/bot?startapp=... (кнопки в группах)
  const startParam = computed(() => tg?.initDataUnsafe?.start_param || '')

  /**
   * Запросить номер телефона нативным окном Telegram.
   * Контакт уходит боту сообщением, бот сохраняет номер в профиль.
   * Возвращает true, если пользователь поделился.
   */
  const requestContact = () => new Promise((resolve) => {
    if (!tg?.requestContact) {
      resolve(false)
      return
    }
    try {
      tg.requestContact((sent) => resolve(!!sent))
    } catch {
      resolve(false)
    }
  })

  /**
   * Открыть ссылку на бота (запасной путь регистрации).
   */
  const openTelegramLink = (url) => {
    if (tg?.openTelegramLink) tg.openTelegramLink(url)
    else window.open(url, '_blank')
  }

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
      // Красим шапку и фон Telegram под фирменную палитру приложения.
      // Методы появились в Bot API 6.1+, на старых клиентах их просто нет.
      tg.setHeaderColor?.('#FFFFFF')
      tg.setBackgroundColor?.('#F7F8FA')
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
   * Открыть счёт на оплату звёздами.
   * Возвращает статус: paid | cancelled | failed | pending.
   */
  const openInvoice = (url) =>
    new Promise((resolve) => {
      // Вне Telegram оплатить нельзя — честно сообщаем об этом вызывающему
      if (!tg?.openInvoice) {
        resolve('unavailable')
        return
      }
      tg.openInvoice(url, (status) => resolve(status))
    })

  /**
   * Открыть внешнюю ссылку (кошелёк TON и подобное).
   */
  const openLink = (url) => {
    if (tg?.openLink) {
      tg.openLink(url)
    } else {
      window.open(url, '_blank')
    }
  }

  /**
   * Закрыть Mini App.
   */
  const close = () => tg?.close()

  return {
    tg,
    user,
    initData,
    startParam,
    requestContact,
    openTelegramLink,
    colorScheme,
    themeParams,
    ready,
    showBackButton,
    hideBackButton,
    showMainButton,
    hideMainButton,
    haptic,
    openInvoice,
    openLink,
    close,
  }
}
