import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

/**
 * Маршруты приложения.
 * Lazy loading для каждой страницы — быстрая начальная загрузка.
 */
const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
  },
  {
    path: '/travelers',
    name: 'travelers',
    component: () => import('@/views/TravelersView.vue'),
  },
  {
    path: '/send',
    name: 'send-parcel',
    component: () => import('@/views/SendParcelView.vue'),
  },
  {
    path: '/publish-flight',
    name: 'publish-flight',
    component: () => import('@/views/PublishFlightView.vue'),
  },
  {
    path: '/parcels',
    name: 'parcels',
    component: () => import('@/views/ParcelsView.vue'),
  },
  {
    path: '/tracking/:id',
    name: 'tracking',
    component: () => import('@/views/TrackingView.vue'),
    props: true,
  },
  {
    path: '/chats',
    name: 'chats',
    component: () => import('@/views/ChatListView.vue'),
  },
  {
    path: '/chats/:id',
    name: 'chat',
    component: () => import('@/views/ChatView.vue'),
    props: true,
  },
  {
    path: '/profile',
    name: 'profile',
    component: () => import('@/views/ProfileView.vue'),
  },
  {
    path: '/profile/:id',
    name: 'user-profile',
    component: () => import('@/views/ProfileView.vue'),
    props: true,
  },
  {
    path: '/subscription',
    name: 'subscription',
    component: () => import('@/views/SubscriptionView.vue'),
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue'),
  },
  {
    path: '/rate/:id',
    name: 'rate',
    component: () => import('@/views/RateView.vue'),
    props: true,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  // При переходе назад — восстанавливать позицию скролла
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    return { top: 0 }
  },
})

// Навигационный guard — защита приватных маршрутов
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  const publicRoutes = ['/']

  if (!publicRoutes.includes(to.path) && !authStore.token) {
    next('/')
  } else {
    next()
  }
})

export default router
