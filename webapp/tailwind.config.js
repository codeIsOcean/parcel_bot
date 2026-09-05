/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts}',
  ],
  theme: {
    extend: {
      colors: {
        // Всё тянется из CSS-переменных в assets/main.css — единый источник палитры
        primary: 'var(--primary)',
        'primary-light': 'var(--primary-light)',
        'primary-soft': 'var(--primary-soft)',
        accent: 'var(--success)',
        danger: 'var(--danger)',
        warning: 'var(--warning)',
        // Фоны
        'bg-primary': 'var(--bg)',
        'bg-secondary': 'var(--surface)',
        'bg-tertiary': 'var(--surface-2)',
        border: 'var(--border)',
        // Текст
        'text-primary': 'var(--text-1)',
        'text-secondary': 'var(--text-2)',
        'text-muted': 'var(--text-3)',
        'text-link': 'var(--primary)',
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
