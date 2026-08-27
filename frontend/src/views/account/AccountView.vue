<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { CalendarDays, Mail, Phone, ShieldCheck, UserRound } from '@lucide/vue'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const { user } = storeToRefs(auth)

function formatDate(value?: string) {
  return value ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'long' }).format(new Date(value)) : '—'
}
</script>

<template>
  <section class="account-page page-shell">
    <header class="page-header">
      <div><p class="eyebrow">MY ACCOUNT</p><h1>账户信息</h1></div>
      <RouterLink class="primary-link" :to="{ name: 'orders' }">查看我的订单</RouterLink>
    </header>
    <div class="profile-grid">
      <article class="identity-card surface-card">
        <div class="avatar"><UserRound :size="38" /></div>
        <div><span class="role-tag">{{ user?.role === 'admin' ? '管理员' : '普通用户' }}</span><h2>{{ user?.username }}</h2><p>用户编号 #{{ user?.id }}</p></div>
      </article>
      <dl class="detail-card surface-card">
        <div><dt><Mail :size="17" />邮箱</dt><dd>{{ user?.email || '未填写' }}</dd></div>
        <div><dt><Phone :size="17" />手机</dt><dd>{{ user?.phone || '未填写' }}</dd></div>
        <div><dt><CalendarDays :size="17" />加入时间</dt><dd>{{ formatDate(user?.date_joined) }}</dd></div>
        <div><dt><ShieldCheck :size="17" />账户权限</dt><dd>{{ user?.role === 'admin' ? '商品与订单管理' : '购物与订单访问' }}</dd></div>
      </dl>
    </div>
    <p class="scope-note">当前后端暂未提供资料修改、密码修改和找回密码接口，因此此页只展示经过服务器确认的账户信息。</p>
  </section>
</template>

<style scoped>
.account-page { padding-top: 58px; }
.profile-grid { display: grid; grid-template-columns: .82fr 1.18fr; gap: 24px; }
.identity-card { padding: 42px; display: flex; align-items: center; gap: 24px; }
.avatar { width: 82px; height: 82px; flex: 0 0 auto; display: grid; place-items: center; border-radius: 50%; color: white; background: var(--accent); }
.identity-card h2 { margin: 10px 0 4px; font: 500 31px var(--font-display); }
.identity-card p { color: var(--muted); font-size: 13px; }
.role-tag { color: var(--accent-dark); font-size: 11px; letter-spacing: .08em; }
.detail-card { padding: 20px 34px; }
.detail-card > div { display: grid; grid-template-columns: 150px 1fr; gap: 20px; padding: 21px 0; border-bottom: 1px solid var(--line); }
.detail-card > div:last-child { border-bottom: 0; }
dt { display: flex; align-items: center; gap: 9px; color: var(--muted); font-size: 13px; }
dd { margin: 0; color: var(--ink); }
.scope-note { margin: 22px 4px 0; color: var(--muted); font-size: 12px; }
@media (max-width: 780px) { .profile-grid { grid-template-columns: 1fr; } .identity-card { padding: 30px; } .detail-card > div { grid-template-columns: 1fr; gap: 7px; } }
</style>
