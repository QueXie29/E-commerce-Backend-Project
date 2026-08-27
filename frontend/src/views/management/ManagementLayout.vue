<script setup lang="ts">
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { useAuthStore } from '@/stores/auth'
import { errorMessage } from '@/shared/api/errors'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const navigation = [
  { to: '/manage', label: '管理概览', exact: true },
  { to: '/manage/categories', label: '分类管理' },
  { to: '/manage/products', label: '商品管理' },
  { to: '/manage/orders', label: '订单管理' },
]

function isActive(to: string, exact = false): boolean {
  return exact ? route.path === to : route.path.startsWith(to)
}

async function logout(): Promise<void> {
  try {
    await auth.logout()
    ElMessage.success('已安全退出')
    await router.replace({ name: 'product-list' })
  } catch (error) {
    ElMessage.error(errorMessage(error))
  }
}
</script>

<template>
  <div class="management-shell">
    <aside class="management-sidebar">
      <div class="management-brand">
        <span class="management-brand__mark">M</span>
        <div>
          <strong>商城管理台</strong>
          <small>Mini Mall</small>
        </div>
      </div>

      <nav class="management-nav" aria-label="管理端导航">
        <RouterLink
          v-for="item in navigation"
          :key="item.to"
          :to="item.to"
          class="management-nav__link"
          :class="{ 'management-nav__link--active': isActive(item.to, item.exact) }"
        >
          {{ item.label }}
        </RouterLink>
      </nav>

      <RouterLink to="/" class="back-to-store">返回商城首页</RouterLink>
    </aside>

    <main class="management-main">
      <header class="management-topbar">
        <div>
          <span class="management-topbar__eyebrow">ADMIN CONSOLE</span>
          <h1>后台管理</h1>
        </div>
        <el-tag type="warning" effect="plain" round>管理员区域</el-tag>
      </header>

      <div class="mobile-management-nav" aria-label="管理端移动导航">
        <RouterLink to="/">返回商城</RouterLink>
        <RouterLink
          v-for="item in navigation"
          :key="item.to"
          :to="item.to"
          :class="{ 'mobile-management-nav__active': isActive(item.to, item.exact) }"
        >
          {{ item.label }}
        </RouterLink>
        <RouterLink :to="{ name: 'account' }">账户</RouterLink>
        <button type="button" @click="logout">退出</button>
      </div>

      <section class="management-content">
        <RouterView />
      </section>
    </main>
  </div>
</template>

<style scoped>
.management-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 250px minmax(0, 1fr);
  background: #f5f7fb;
  color: #1f2937;
}

.management-sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 28px 20px;
  background: #172033;
  color: #fff;
}

.management-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 8px 28px;
}

.management-brand__mark {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 13px;
  background: #eab308;
  color: #172033;
  font-weight: 800;
}

.management-brand strong,
.management-brand small {
  display: block;
}

.management-brand small {
  margin-top: 3px;
  color: #94a3b8;
  font-size: 11px;
  letter-spacing: 0.12em;
}

.management-nav {
  display: grid;
  gap: 8px;
}

.management-nav__link {
  padding: 12px 14px;
  border-radius: 10px;
  color: #cbd5e1;
  text-decoration: none;
  transition: 0.18s ease;
}

.management-nav__link:hover,
.management-nav__link--active {
  background: #28344d;
  color: #fff;
}

.management-nav__link--active {
  box-shadow: inset 3px 0 #eab308;
}

.back-to-store {
  margin-top: auto;
  padding: 12px 14px;
  color: #94a3b8;
  text-decoration: none;
}

.back-to-store:hover {
  color: #fff;
}

.management-main {
  min-width: 0;
}

.management-topbar {
  min-height: 88px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 18px clamp(20px, 4vw, 48px);
  border-bottom: 1px solid #e5e7eb;
  background: rgb(255 255 255 / 92%);
}

.management-topbar h1 {
  margin: 2px 0 0;
  font-size: 22px;
}

.management-topbar__eyebrow {
  color: #9a6d00;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.16em;
}

.management-content {
  padding: 32px clamp(20px, 4vw, 48px) 56px;
}

.mobile-management-nav {
  display: none;
}

@media (max-width: 820px) {
  .management-shell {
    display: block;
  }

  .management-sidebar {
    display: none;
  }

  .management-topbar {
    min-height: 76px;
  }

  .mobile-management-nav {
    display: flex;
    gap: 8px;
    padding: 12px 20px;
    overflow-x: auto;
    border-bottom: 1px solid #e5e7eb;
    background: #fff;
  }

  .mobile-management-nav a,
  .mobile-management-nav button {
    flex: 0 0 auto;
    padding: 8px 12px;
    border: 0;
    border-radius: 999px;
    color: #64748b;
    background: transparent;
    font: inherit;
    text-decoration: none;
    font-size: 13px;
    cursor: pointer;
  }

  .mobile-management-nav__active {
    background: #172033;
    color: #fff !important;
  }
}
</style>
