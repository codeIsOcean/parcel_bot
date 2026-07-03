import { ref, readonly } from 'vue'
import ru from '@/locale/ru.json'
import en from '@/locale/en.json'

// Доступные локали
const locales = { ru, en }

// Текущий язык (определяется из Telegram или localStorage)
const currentLang = ref('ru')

/**
 * Composable для локализации (i18n).
 * Поддержка RU/EN с подстановкой параметров.
 */
export function useLocale() {
  /**
   * Перевод ключа на текущий язык.
   * Поддерживает параметры: t('key', { count: 5 }) → "5 попутчиков"
   */
  const t = (key, params = {}) => {
    // Получаем строку из текущей локали или fallback на русский
    let text = locales[currentLang.value]?.[key] || locales.ru[key] || key

    // Подставляем параметры {param}
    Object.entries(params).forEach(([k, v]) => {
      text = text.replace(`{${k}}`, v)
    })

    return text
  }

  /**
   * Установить язык приложения.
   */
  const setLang = (lang) => {
    if (locales[lang]) {
      currentLang.value = lang
      // Сохраняем выбор в localStorage
      localStorage.setItem('parcel_bot_lang', lang)
    }
  }

  /**
   * Инициализировать язык из Telegram или localStorage.
   */
  const initLang = () => {
    // Приоритет: localStorage → Telegram → русский
    const saved = localStorage.getItem('parcel_bot_lang')
    if (saved && locales[saved]) {
      currentLang.value = saved
      return
    }

    // Определяем из Telegram WebApp
    const tgLang = window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code
    if (tgLang && locales[tgLang]) {
      currentLang.value = tgLang
    }
  }

  return {
    t,
    currentLang: readonly(currentLang),
    setLang,
    initLang,
  }
}
