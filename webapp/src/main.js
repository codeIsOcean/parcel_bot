import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/main.css'

// Создаём приложение Vue
const app = createApp(App)

// Подключаем Pinia (state management)
app.use(createPinia())

// Подключаем Vue Router
app.use(router)

// Монтируем приложение
app.mount('#app')
