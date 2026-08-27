import { createRouter, createWebHistory } from 'vue-router'

import { pinia } from './instances'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) return { el: to.hash, behavior: 'smooth' }
    if (to.path !== from.path) return { top: 0 }
    return undefined
  },
  routes: [
    {
      path: '/',
      component: () => import('@/app/layouts/StorefrontLayout.vue'),
      children: [
        {
          path: '',
          name: 'product-list',
          component: () => import('@/views/storefront/ProductListView.vue'),
          meta: { title: '精选商品' },
        },
        {
          path: 'products/:id(\\d+)',
          name: 'product-detail',
          component: () => import('@/views/storefront/ProductDetailView.vue'),
          meta: { title: '商品详情' },
        },
        {
          path: 'login',
          name: 'login',
          component: () => import('@/views/auth/LoginView.vue'),
          meta: { guestOnly: true, title: '登录' },
        },
        {
          path: 'register',
          name: 'register',
          component: () => import('@/views/auth/RegisterView.vue'),
          meta: { guestOnly: true, title: '注册' },
        },
        {
          path: 'account',
          name: 'account',
          component: () => import('@/views/account/AccountView.vue'),
          meta: { requiresAuth: true, title: '账户信息' },
        },
        {
          path: 'cart',
          name: 'cart',
          component: () => import('@/views/storefront/CartView.vue'),
          meta: { requiresAuth: true, title: '购物车' },
        },
        {
          path: 'checkout',
          name: 'checkout',
          component: () => import('@/views/storefront/CheckoutView.vue'),
          meta: { requiresAuth: true, title: '确认订单' },
        },
        {
          path: 'orders',
          name: 'orders',
          component: () => import('@/views/storefront/OrderListView.vue'),
          meta: { requiresAuth: true, title: '我的订单' },
        },
        {
          path: 'orders/:id(\\d+)',
          name: 'order-detail',
          component: () => import('@/views/storefront/OrderDetailView.vue'),
          meta: { requiresAuth: true, title: '订单详情' },
        },
      ],
    },
    {
      path: '/manage',
      component: () => import('@/views/management/ManagementLayout.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
      children: [
        {
          path: '',
          name: 'manage-dashboard',
          component: () => import('@/views/management/DashboardView.vue'),
          meta: { title: '管理概览' },
        },
        {
          path: 'categories',
          name: 'manage-categories',
          component: () => import('@/views/management/CategoryManagementView.vue'),
          meta: { title: '分类管理' },
        },
        {
          path: 'products',
          name: 'manage-products',
          component: () => import('@/views/management/ProductManagementView.vue'),
          meta: { title: '商品管理' },
        },
        {
          path: 'orders',
          name: 'manage-orders',
          component: () => import('@/views/management/OrderManagementView.vue'),
          meta: { title: '订单管理' },
        },
        {
          path: 'orders/:id(\\d+)',
          name: 'manage-order-detail',
          component: () => import('@/views/storefront/OrderDetailView.vue'),
          meta: { title: '管理订单详情' },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
      meta: { title: '页面不存在' },
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore(pinia)
  if (!auth.initialized) await auth.initialize()

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin && !auth.isAdmin) return { name: 'product-list' }
  if (to.meta.guestOnly && auth.isAuthenticated) return { name: 'product-list' }
  return true
})

router.afterEach((to) => {
  document.title = `${to.meta.title ?? '商城'} · Mini Mall`
  window.requestAnimationFrame(() => {
    const heading = document.querySelector<HTMLElement>('h1')
    if (!heading) return
    heading.setAttribute('tabindex', '-1')
    heading.focus({ preventScroll: true })
  })
})

export default router
