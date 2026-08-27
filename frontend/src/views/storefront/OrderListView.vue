<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import OrderStatusBadge from '@/components/storefront/OrderStatusBadge.vue'
import { firstQueryValue, formatDateTime, positivePage } from '@/components/storefront/format'
import type { OrderFilters, OrderStatus } from '@/shared/api/contracts'
import { errorMessage } from '@/shared/api/errors'
import { listOrders } from '@/shared/api/orders'
import { useAuthStore } from '@/stores/auth'

defineOptions({ name: 'OrderListView' })

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const pageSize = 10
const validStatuses: OrderStatus[] = ['pending', 'paid', 'cancelled']

const page = computed(() => positivePage(route.query.page))
const status = computed<OrderStatus | ''>({
  get: () => {
    const value = firstQueryValue(route.query.status)
    return validStatuses.includes(value as OrderStatus) ? (value as OrderStatus) : ''
  },
  set: (value) => {
    void router.push({
      name: 'orders',
      query: value ? { status: value } : {},
    })
  },
})

const filters = computed<OrderFilters>(() => ({
  page: page.value,
  page_size: pageSize,
  status: status.value || undefined,
}))

const ordersQuery = useQuery({
  queryKey: computed(() => ['orders', 'list', filters.value]),
  queryFn: () => listOrders(filters.value),
  enabled: computed(() => auth.isAuthenticated),
  placeholderData: (previous) => previous,
})

async function changePage(nextPage: number): Promise<void> {
  await router.push({
    name: 'orders',
    query: {
      ...(status.value ? { status: status.value } : {}),
      ...(nextPage > 1 ? { page: String(nextPage) } : {}),
    },
  })
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
</script>

<template>
  <div class="orders-page">
    <div class="page-heading">
      <div>
        <p>MY ORDERS</p>
        <h1>我的订单</h1>
        <span>查看付款状态与每笔订单的商品明细。</span>
      </div>
      <RouterLink :to="{ name: 'product-list' }">继续购物 →</RouterLink>
    </div>

    <div class="status-filter" aria-label="订单状态筛选">
      <el-radio-group v-model="status" size="large">
        <el-radio-button value="">全部订单</el-radio-button>
        <el-radio-button value="pending">待支付</el-radio-button>
        <el-radio-button value="paid">已支付</el-radio-button>
        <el-radio-button value="cancelled">已取消</el-radio-button>
      </el-radio-group>
    </div>

    <el-result v-if="!auth.isAuthenticated" icon="info" title="登录后查看订单" sub-title="你的历史订单会显示在这里">
      <template #extra>
        <el-button type="primary" @click="router.push({ name: 'login', query: { redirect: '/orders' } })">去登录</el-button>
      </template>
    </el-result>

    <section v-else-if="ordersQuery.isPending.value" class="order-list">
      <el-skeleton v-for="index in 4" :key="index" class="order-card loading-card" animated :rows="3" />
    </section>

    <el-result
      v-else-if="ordersQuery.isError.value"
      icon="error"
      title="订单加载失败"
      :sub-title="errorMessage(ordersQuery.error.value)"
    >
      <template #extra><el-button type="primary" @click="ordersQuery.refetch()">重新加载</el-button></template>
    </el-result>

    <el-empty v-else-if="!ordersQuery.data.value?.results.length" :description="status ? '该状态下暂无订单' : '还没有订单记录'">
      <el-button v-if="status" plain @click="status = ''">查看全部订单</el-button>
      <el-button type="primary" @click="router.push({ name: 'product-list' })">去挑选商品</el-button>
    </el-empty>

    <section v-else class="order-list" aria-live="polite">
      <RouterLink
        v-for="order in ordersQuery.data.value.results"
        :key="order.id"
        class="order-card"
        :to="{ name: 'order-detail', params: { id: order.id } }"
      >
        <div class="order-card__header">
          <div>
            <span>订单号</span>
            <strong>{{ order.order_no }}</strong>
          </div>
          <OrderStatusBadge :status="order.status" />
        </div>
        <div class="order-card__body">
          <div>
            <span>下单时间</span>
            <strong>{{ formatDateTime(order.created_at) }}</strong>
          </div>
          <div>
            <span>{{ order.status === 'pending' ? '支付截止' : order.status === 'paid' ? '支付时间' : '取消时间' }}</span>
            <strong>
              {{ formatDateTime(order.status === 'pending' ? order.expires_at : order.status === 'paid' ? order.paid_at : order.cancelled_at) }}
            </strong>
          </div>
          <div class="order-card__amount">
            <span>订单金额</span>
            <strong><small>¥</small>{{ order.total_amount }}</strong>
          </div>
          <span class="order-card__arrow">查看详情 →</span>
        </div>
        <p v-if="order.remark" class="order-card__remark">备注：{{ order.remark }}</p>
      </RouterLink>
    </section>

    <el-pagination
      v-if="(ordersQuery.data.value?.count ?? 0) > pageSize"
      class="pagination"
      background
      layout="prev, pager, next"
      :current-page="page"
      :page-size="pageSize"
      :total="ordersQuery.data.value?.count ?? 0"
      @current-change="changePage"
    />
  </div>
</template>

<style scoped>
.orders-page {
  width: min(1000px, calc(100% - 36px));
  margin: 0 auto;
  padding: 38px 0 76px;
}

.page-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 28px;
}

.page-heading p {
  margin: 0 0 8px;
  color: #36734d;
  font-size: 11px;
  font-weight: 750;
  letter-spacing: 0.16em;
}

.page-heading h1 {
  margin: 0 0 7px;
  color: #1d2e22;
  font-size: 34px;
}

.page-heading span {
  color: #7b857d;
  font-size: 13px;
}

.page-heading a {
  color: #39764f;
  font-size: 14px;
  text-decoration: none;
}

.status-filter {
  margin-bottom: 22px;
  overflow-x: auto;
  scrollbar-width: none;
}

.status-filter::-webkit-scrollbar {
  display: none;
}

.order-list {
  display: grid;
  gap: 15px;
}

.order-card {
  display: block;
  overflow: hidden;
  color: inherit;
  text-decoration: none;
  border: 1px solid #e3e9e4;
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 8px 28px rgb(30 51 35 / 5%);
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
}

.order-card:not(.loading-card):hover {
  transform: translateY(-2px);
  border-color: #cbd8ce;
  box-shadow: 0 14px 34px rgb(30 51 35 / 9%);
}

.loading-card {
  padding: 24px;
}

.order-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 21px;
  border-bottom: 1px solid #edf0ed;
  background: #fbfcfb;
}

.order-card__header > div {
  display: flex;
  align-items: center;
  gap: 11px;
}

.order-card__header span,
.order-card__body span {
  color: #89928a;
  font-size: 11px;
}

.order-card__header strong {
  color: #36443a;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 13px;
}

.order-card__body {
  display: grid;
  grid-template-columns: 1.1fr 1.1fr 0.75fr auto;
  gap: 24px;
  align-items: center;
  padding: 21px;
}

.order-card__body > div {
  display: grid;
  gap: 7px;
}

.order-card__body > div > strong {
  color: #465249;
  font-size: 13px;
  font-weight: 600;
}

.order-card__amount strong {
  color: #d6532f !important;
  font-size: 20px !important;
  font-variant-numeric: tabular-nums;
}

.order-card__amount small {
  margin-right: 2px;
  font-size: 11px;
}

.order-card__arrow {
  color: #36744d !important;
  white-space: nowrap;
}

.order-card__remark {
  margin: 0;
  padding: 0 21px 17px;
  overflow: hidden;
  color: #7c867f;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pagination {
  justify-content: center;
  margin-top: 35px;
}

:deep(.el-empty),
:deep(.el-result) {
  min-height: 400px;
}

@media (max-width: 730px) {
  .order-card__body {
    grid-template-columns: 1fr 1fr;
  }

  .order-card__arrow {
    justify-self: end;
  }
}

@media (max-width: 520px) {
  .orders-page {
    width: min(100% - 24px, 1000px);
    padding-top: 24px;
  }

  .page-heading a {
    display: none;
  }

  .order-card__body {
    grid-template-columns: 1fr;
    gap: 17px;
  }

  .order-card__arrow {
    justify-self: start;
  }
}
</style>
