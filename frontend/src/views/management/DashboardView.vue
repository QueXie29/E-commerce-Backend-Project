<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import {
  listManagedCategories,
  listManagedOrders,
  listManagedProducts,
} from '@/shared/api/management'

const categoriesQuery = useQuery({
  queryKey: ['management', 'dashboard', 'categories'],
  queryFn: () => listManagedCategories(1),
})

const productsQuery = useQuery({
  queryKey: ['management', 'dashboard', 'products'],
  queryFn: () => listManagedProducts({ page: 1, page_size: 1 }),
})

const ordersQuery = useQuery({
  queryKey: ['management', 'dashboard', 'orders'],
  queryFn: () => listManagedOrders({ page: 1, page_size: 1 }),
})

const cards = computed(() => [
  {
    label: '分类总数',
    value: categoriesQuery.data.value?.count,
    pending: categoriesQuery.isPending.value,
    error: categoriesQuery.isError.value,
    to: '/manage/categories',
  },
  {
    label: '商品总数',
    value: productsQuery.data.value?.count,
    pending: productsQuery.isPending.value,
    error: productsQuery.isError.value,
    to: '/manage/products',
  },
  {
    label: '订单总数',
    value: ordersQuery.data.value?.count,
    pending: ordersQuery.isPending.value,
    error: ordersQuery.isError.value,
    to: '/manage/orders',
  },
])
</script>

<template>
  <div class="dashboard">
    <section class="dashboard-hero">
      <div>
        <p class="section-kicker">OVERVIEW</p>
        <h2>管理概览</h2>
        <p>在这里维护商城分类与商品状态，并查看所有用户的订单记录。</p>
      </div>
      <RouterLink to="/manage/products" class="primary-link">管理商品</RouterLink>
    </section>

    <section class="metric-grid" aria-label="实时数据概览">
      <RouterLink v-for="card in cards" :key="card.label" :to="card.to" class="metric-card">
        <span>{{ card.label }}</span>
        <strong v-if="card.pending">—</strong>
        <strong v-else-if="card.error" class="metric-card__error">加载失败</strong>
        <strong v-else>{{ card.value ?? 0 }}</strong>
        <small>查看详情 →</small>
      </RouterLink>
    </section>

    <section class="quick-section">
      <div class="section-heading">
        <div>
          <p class="section-kicker">QUICK ACTIONS</p>
          <h2>快捷入口</h2>
        </div>
      </div>

      <div class="quick-grid">
        <RouterLink to="/manage/categories" class="quick-card">
          <strong>维护分类</strong>
          <span>新增、编辑、停用或重新启用商品分类。</span>
        </RouterLink>
        <RouterLink to="/manage/products" class="quick-card">
          <strong>维护商品</strong>
          <span>更新商品资料、库存、价格以及上下架状态。</span>
        </RouterLink>
        <RouterLink to="/manage/orders" class="quick-card">
          <strong>查看订单</strong>
          <span>按状态筛选订单，并进入详情查看订单明细。</span>
        </RouterLink>
      </div>
    </section>
  </div>
</template>

<style scoped>
.dashboard {
  display: grid;
  gap: 28px;
}

.dashboard-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: clamp(24px, 4vw, 42px);
  overflow: hidden;
  border-radius: 20px;
  background: linear-gradient(135deg, #172033 0%, #263653 70%, #33466b 100%);
  color: #fff;
  box-shadow: 0 18px 44px rgb(15 23 42 / 12%);
}

.dashboard-hero h2,
.section-heading h2 {
  margin: 5px 0 10px;
  font-size: clamp(25px, 3vw, 34px);
}

.dashboard-hero p:not(.section-kicker) {
  max-width: 620px;
  margin: 0;
  color: #cbd5e1;
  line-height: 1.7;
}

.section-kicker {
  margin: 0;
  color: #d29c12;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.16em;
}

.primary-link {
  flex: 0 0 auto;
  padding: 11px 18px;
  border-radius: 10px;
  background: #eab308;
  color: #172033;
  font-weight: 700;
  text-decoration: none;
}

.metric-grid,
.quick-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.metric-card,
.quick-card {
  padding: 24px;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  background: #fff;
  color: inherit;
  text-decoration: none;
  box-shadow: 0 8px 24px rgb(15 23 42 / 4%);
  transition: 0.18s ease;
}

.metric-card:hover,
.quick-card:hover {
  transform: translateY(-2px);
  border-color: #d4a514;
  box-shadow: 0 14px 32px rgb(15 23 42 / 8%);
}

.metric-card span,
.metric-card small,
.quick-card span {
  display: block;
  color: #64748b;
}

.metric-card strong {
  display: block;
  margin: 12px 0 16px;
  font-size: 34px;
}

.metric-card .metric-card__error {
  color: #dc2626;
  font-size: 16px;
}

.metric-card small {
  font-size: 12px;
}

.quick-section {
  display: grid;
  gap: 16px;
}

.section-heading h2 {
  margin-bottom: 0;
  color: #172033;
  font-size: 24px;
}

.quick-card strong {
  display: block;
  margin-bottom: 9px;
  color: #172033;
  font-size: 17px;
}

.quick-card span {
  line-height: 1.65;
}

@media (max-width: 850px) {
  .metric-grid,
  .quick-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .dashboard-hero {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
