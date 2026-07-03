/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts}',
  ],
  theme: {
    extend: {
      colors: {
        // Основные цвета из прототипа
        primary: '#6C5CE7',
        'primary-light': '#A29BFE',
        accent: '#30D158',
        danger: '#FF453A',
        warning: '#FFD60A',
        // Фоны
        'bg-primary': 'var(--tg-theme-bg-color, #000000)',
        'bg-secondary': 'var(--tg-theme-secondary-bg-color, #1C1C1E)',
        'bg-tertiary': '#2C2C2E',
        // Текст
        'text-primary': 'var(--tg-theme-text-color, #FFFFFF)',
        'text-secondary': 'var(--tg-theme-hint-color, #8E8E93)',
        'text-link': 'var(--tg-theme-link-color, #6C5CE7)',
      },
      fontFamily: {
        sans: ['Manrope', 'system-ui', '-apple-system', 'sans-serif'],
      },
      borderRadius: {
        'card': '12px',
        'btn': '10px',
        'input': '12px',
      },
    },
  },
  plugins: [],
}
