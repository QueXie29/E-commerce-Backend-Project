<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { ElMessage } from 'element-plus'
import { Menu, ShoppingBag, UserRound, X } from '@lucide/vue'

import { useAuthStore } from '@/stores/auth'
import { getCart } from '@/shared/api/cart'
import { errorMessage } from '@/shared/api/errors'

const auth = useAuthStore()
const { user, isAuthenticated, isAdmin } = storeToRefs(auth)
const router = useRouter()
const queryClient = useQueryClient()
const mobileOpen = ref(false)
const cartEnabled = computed(() => isAuthenticated.value)
const cartQuery = useQuery({
  queryKey: ['cart'],
  queryFn: getCart,
  enabled: cartEnabled,
})
const cartCount = computed(() =>
  cartQuery.data.value?.items.reduce((sum, item) => sum + item.quantity, 0) ?? 0,
)

async function handleLogout() {
  closeMobile()
  try {
    await auth.logout()
    queryClient.clear()
    ElMessage.success('已安全退出')
    await router.push({ name: 'product-list' })
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}

function closeMobile() {
  mobileOpen.value = false
}
</script>

<template>
  <div class="site-frame">
    <a class="skip-link" href="#main-content">跳到主要内容</a>
    <header class="site-header">
      <div class="header-inner">
        <RouterLink class="brand" :to="{ name: 'product-list' }" @click="closeMobile">
          <span class="brand-mark">M</span>
          <span>
            <strong>MINI MALL</strong>
            <small>GOOD THINGS, SIMPLY</small>
          </span>
        </RouterLink>

        <button
          class="mobile-toggle"
          type="button"
          :aria-label="mobileOpen ? '关闭菜单' : '打开菜单'"
          :aria-expanded="mobileOpen"
          aria-controls="main-navigation"
          @click="mobileOpen = !mobileOpen"
        >
          <X v-if="mobileOpen" :size="22" />
          <Menu v-else :size="22" />
        </button>

        <nav id="main-navigation" class="main-nav" :class="{ 'is-open': mobileOpen }" aria-label="主导航">
          <RouterLink :to="{ name: 'product-list' }" @click="closeMobile">逛商品</RouterLink>
          <RouterLink v-if="isAuthenticated" :to="{ name: 'orders' }" @click="closeMobile">我的订单</RouterLink>
          <RouterLink v-if="isAdmin" :to="{ name: 'manage-dashboard' }" @click="closeMobile">管理中心</RouterLink>
          <button v-if="isAuthenticated" class="mobile-logout" type="button" @click="handleLogout">
            退出登录
          </button>
        </nav>

        <div class="header-actions">
          <template v-if="isAuthenticated">
            <RouterLink class="icon-link" :to="{ name: 'account' }" :title="user?.username">
              <UserRound :size="20" />
              <span class="desktop-label">{{ user?.username }}</span>
            </RouterLink>
            <RouterLink class="icon-link cart-link" :to="{ name: 'cart' }" title="购物车">
              <ShoppingBag :size="20" />
              <span class="desktop-label">购物车</span>
              <span v-if="cartCount" class="cart-badge">{{ cartCount > 99 ? '99+' : cartCount }}</span>
            </RouterLink>
            <button class="text-button" type="button" @click="handleLogout">退出</button>
          </template>
          <template v-else>
            <RouterLink class="text-link" :to="{ name: 'login' }">登录</RouterLink>
            <RouterLink class="solid-link" :to="{ name: 'register' }">注册</RouterLink>
          </template>
        </div>
      </div>
    </header>

    <main id="main-content" class="site-main">
      <RouterView />
    </main>

    <footer class="site-footer">
      <div class="footer-inner">
        <div>
          <strong>MINI MALL</strong>
          <p>一个把可靠交易流程和简洁购物体验放在一起的练习项目。</p>
        </div>
        <div class="footer-meta">
          <span>Django REST Framework</span>
          <span>Vue · TypeScript</span>
        </div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.site-frame { min-height: 100vh; display: flex; flex-direction: column; }
.site-header { position: sticky; top: 0; z-index: 50; border-bottom: 1px solid var(--line); background: color-mix(in srgb, var(--paper) 94%, transparent); backdrop-filter: blur(16px); }
.header-inner { width: min(1180px, calc(100% - 32px)); min-height: 76px; margin: 0 auto; display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 32px; }
.brand { display: inline-flex; align-items: center; gap: 11px; color: var(--ink); text-decoration: none; line-height: 1; }
.brand-mark { width: 38px; height: 38px; display: grid; place-items: center; color: var(--paper); background: var(--ink); border-radius: 50% 50% 46% 54%; font-family: var(--font-display); font-size: 20px; }
.brand strong { display: block; font: 700 15px/1 var(--font-display); letter-spacing: .14em; }
.brand small { display: block; margin-top: 7px; color: var(--muted); font-size: 8px; letter-spacing: .12em; }
.main-nav { display: flex; justify-content: center; gap: 30px; }
.main-nav a { position: relative; color: var(--muted-strong); text-decoration: none; font-size: 14px; }
.main-nav a::after { content: ''; position: absolute; left: 0; right: 100%; bottom: -8px; height: 2px; background: var(--accent); transition: right .2s ease; }
.main-nav a:hover::after, .main-nav a.router-link-active::after { right: 0; }
.header-actions { display: flex; align-items: center; gap: 14px; }
.icon-link { position: relative; display: inline-flex; align-items: center; gap: 6px; color: var(--ink); text-decoration: none; font-size: 13px; }
.cart-badge { position: absolute; top: -11px; left: 12px; min-width: 18px; height: 18px; padding: 0 5px; display: grid; place-items: center; border-radius: 999px; background: var(--accent); color: white; font-size: 10px; }
.text-button { border: 0; padding: 0; background: transparent; color: var(--muted); cursor: pointer; }
.text-link, .solid-link { font-size: 14px; text-decoration: none; }
.text-link { color: var(--ink); }
.solid-link { padding: 9px 16px; border-radius: 999px; background: var(--ink); color: white; }
.mobile-toggle { display: none; border: 0; background: transparent; color: var(--ink); }
.mobile-logout { display: none; border: 0; padding: 0; background: transparent; color: var(--accent-dark); font: inherit; cursor: pointer; }
.site-main { flex: 1; }
.site-footer { margin-top: 72px; border-top: 1px solid var(--line); background: var(--ink); color: #f9f5ed; }
.footer-inner { width: min(1180px, calc(100% - 32px)); margin: 0 auto; padding: 42px 0; display: flex; justify-content: space-between; gap: 30px; }
.footer-inner strong { font-family: var(--font-display); letter-spacing: .13em; }
.footer-inner p { max-width: 500px; margin: 12px 0 0; color: #aaa69e; font-size: 13px; }
.footer-meta { display: flex; gap: 10px; align-items: start; flex-wrap: wrap; }
.footer-meta span { padding: 7px 10px; border: 1px solid #46433f; border-radius: 999px; color: #c9c3ba; font-size: 11px; }

@media (max-width: 820px) {
  .header-inner { grid-template-columns: auto auto 1fr; gap: 14px; min-height: 66px; }
  .mobile-toggle { display: grid; place-items: center; }
  .main-nav { display: none; position: absolute; top: 66px; left: 0; right: 0; padding: 20px 24px 26px; flex-direction: column; align-items: flex-start; gap: 22px; border-bottom: 1px solid var(--line); background: var(--paper); box-shadow: var(--shadow-soft); }
  .main-nav.is-open { display: flex; }
  .mobile-logout { display: block; }
  .header-actions { justify-self: end; gap: 10px; }
  .desktop-label, .text-button { display: none; }
  .brand small { display: none; }
  .site-footer { margin-top: 48px; }
  .footer-inner { flex-direction: column; }
}

@media (max-width: 480px) {
  .header-inner { width: min(100% - 22px, 1180px); }
  .brand strong { font-size: 13px; }
  .brand-mark { width: 34px; height: 34px; }
  .solid-link { padding: 8px 12px; }
}
</style>
