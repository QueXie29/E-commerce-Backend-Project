import { createApp, watch } from 'vue'
import { VueQueryPlugin } from '@tanstack/vue-query'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

import 'element-plus/dist/index.css'
import '@/styles/base.css'

import App from './App.vue'
import router from './app/router'
import { pinia, queryClient } from './app/instances'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore(pinia)

watch(
  () => [auth.initialized, auth.isAuthenticated, auth.isAdmin] as const,
  ([initialized, isAuthenticated, isAdmin]) => {
    if (!initialized) return
    const current = router.currentRoute.value
    if (current.meta.requiresAuth && !isAuthenticated) {
      void router.replace({ name: 'login', query: { redirect: current.fullPath } })
    } else if (current.meta.requiresAdmin && !isAdmin) {
      void router.replace({ name: 'product-list' })
    }
  },
  { immediate: true },
)

createApp(App)
  .use(pinia)
  .use(router)
  .use(VueQueryPlugin, { queryClient })
  .use(ElementPlus, { locale: zhCn })
  .mount('#app')
