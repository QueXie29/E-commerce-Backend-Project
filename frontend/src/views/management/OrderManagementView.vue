<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import type { OrderFilters, OrderStatus } from '@/shared/api/contracts'
import { errorMessage } from '@/shared/api/errors'
import { listManagedOrders } from '@/shared/api/management'

const PAGE_SIZE = 15
const page = ref(1)
const status = ref<OrderStatus | undefined>()

const filters = computed<OrderFilters>(() => ({
  page: page.value,
  page_size: PAGE_SIZE,
  status: status.value,
}))

const ordersQuery = useQuery({
  queryKey: computed(() => ['management', 'orders', filters.value]),
  queryFn: () => listManagedOrders(filters.value),
})

watch(status, () => {
  page.value = 1
})

function statusLabel(value: OrderStatus): string {
  return {
    pending: '待支付',
    paid: '已支付',
    cancelled: '已取消',
  }[value]
}

function statusTagType(value: OrderStatus): 'warning' | 'success' | 'info' {
  return {
    pending: 'warning',
    paid: 'success',
    cancelled: 'info',
  }[value] as 'warning' | 'success' | 'info'
}

function formatMoney(value: string): string {
  const amount = Number(value)
  return Number.isFinite(amount)
    ? amount.toLocaleString('zh-CN', { style: 'currency', currency: 'CNY' })
    : value
}

function formatDate(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}
</script>

<template>
  <div class="management-page">
    <header class="page-header">
      <div>
        <p class="page-kicker">ORDERS</p>
        <h2>订单管理</h2>
        <p>查看所有用户的订单，并按当前订单状态筛选。</p>
      </div>
    </header>

    <el-card shadow="never" class="filter-card">
      <el-form inline class="filter-form">
        <el-form-item label="订单状态">
          <el-select v-model="status" clearable placeholder="全部状态">
            <el-option label="待支付" value="pending" />
            <el-option label="已支付" value="paid" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <span class="result-count">
            共 {{ ordersQuery.data.value?.count ?? 0 }} 条订单
          </span>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="data-card">
      <el-skeleton v-if="ordersQuery.isPending.value" :rows="7" animated />
      <el-result
        v-else-if="ordersQuery.isError.value"
        icon="error"
        title="订单加载失败"
        :sub-title="errorMessage(ordersQuery.error.value, '请稍后重试')"
      >
        <template #extra>
          <el-button type="primary" @click="ordersQuery.refetch()">重新加载</el-button>
        </template>
      </el-result>

      <template v-else>
        <el-table
          :data="ordersQuery.data.value?.results ?? []"
          empty-text="当前筛选条件下暂无订单"
          row-key="id"
        >
          <el-table-column prop="order_no" label="订单编号" min-width="210" />
          <el-table-column label="金额" width="130">
            <template #default="scope">{{ formatMoney(scope.row.total_amount) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="scope">
              <el-tag :type="statusTagType(scope.row.status)">
                {{ statusLabel(scope.row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="备注" min-width="180" show-overflow-tooltip>
            <template #default="scope">{{ scope.row.remark || '—' }}</template>
          </el-table-column>
          <el-table-column label="下单时间" min-width="180">
            <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="支付时间" min-width="180">
            <template #default="scope">{{ formatDate(scope.row.paid_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="110" fixed="right">
            <template #default="scope">
              <RouterLink
                :to="{ name: 'manage-order-detail', params: { id: scope.row.id } }"
                class="detail-link"
              >
                查看详情
              </RouterLink>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="(ordersQuery.data.value?.count ?? 0) > PAGE_SIZE" class="pagination-wrap">
          <el-pagination
            v-model:current-page="page"
            background
            layout="prev, pager, next, total"
            :page-size="PAGE_SIZE"
            :total="ordersQuery.data.value?.count ?? 0"
          />
        </div>
      </template>
    </el-card>
  </div>
</template>

<style scoped>
.management-page {
  display: grid;
  gap: 20px;
}

.page-header h2 {
  margin: 4px 0 8px;
  color: #172033;
  font-size: 28px;
}

.page-header p:not(.page-kicker) {
  margin: 0;
  color: #64748b;
}

.page-kicker {
  margin: 0;
  color: #9a6d00;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.16em;
}

.filter-card,
.data-card {
  border-radius: 16px;
}

.filter-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.filter-form :deep(.el-select) {
  width: 190px;
}

.result-count {
  color: #64748b;
  font-size: 13px;
}

.detail-link {
  color: var(--el-color-primary);
  text-decoration: none;
}

.detail-link:hover {
  text-decoration: underline;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  padding-top: 22px;
}

@media (max-width: 560px) {
  .filter-form :deep(.el-form-item),
  .filter-form :deep(.el-select) {
    width: 100%;
  }

  .filter-form :deep(.el-form-item:first-child) {
    margin-bottom: 12px;
  }
}
</style>
