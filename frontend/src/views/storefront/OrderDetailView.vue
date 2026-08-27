<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import OrderStatusBadge from '@/components/storefront/OrderStatusBadge.vue'
import { formatDateTime } from '@/components/storefront/format'
import type { OrderDetail } from '@/shared/api/contracts'
import { errorMessage } from '@/shared/api/errors'
import { cancelOrder, getOrder, payOrder } from '@/shared/api/orders'
import { useAuthStore } from '@/stores/auth'

defineOptions({ name: 'OrderDetailView' })

type OrderAction = 'pay' | 'cancel'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const queryClient = useQueryClient()
const now = ref(Date.now())
const expiryRefetched = ref(false)
let clock: ReturnType<typeof setInterval> | undefined
const isManagementView = computed(() => route.name === 'manage-order-detail')
const listRouteName = computed(() => isManagementView.value ? 'manage-orders' : 'orders')
const listLabel = computed(() => isManagementView.value ? '订单管理' : '我的订单')

const orderId = computed(() => {
  const parsed = Number(route.params.id)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
})

const orderQuery = useQuery({
  queryKey: computed(() => ['orders', 'detail', orderId.value]),
  queryFn: () => {
    if (orderId.value === null) throw new Error('订单编号无效')
    return getOrder(orderId.value)
  },
  enabled: computed(() => auth.isAuthenticated && orderId.value !== null),
})

const remainingMilliseconds = computed(() => {
  const order = orderQuery.data.value
  if (!order || order.status !== 'pending') return 0
  const expiresAt = new Date(order.expires_at).getTime()
  if (Number.isNaN(expiresAt)) return 0
  return Math.max(0, expiresAt - now.value)
})

const countdown = computed(() => {
  const totalSeconds = Math.ceil(remainingMilliseconds.value / 1000)
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  return [hours, minutes, seconds].map((part) => String(part).padStart(2, '0')).join(':')
})

const pendingExpired = computed(
  () => orderQuery.data.value?.status === 'pending' && remainingMilliseconds.value <= 0,
)

function tick(): void {
  now.value = Date.now()
  if (pendingExpired.value && !expiryRefetched.value) {
    expiryRefetched.value = true
    void orderQuery.refetch()
  }
}

watch(
  () => [orderQuery.data.value?.status, orderQuery.data.value?.expires_at] as const,
  () => {
    expiryRefetched.value = false
    now.value = Date.now()
    tick()
  },
)

onMounted(() => {
  tick()
  clock = setInterval(tick, 1000)
})

onBeforeUnmount(() => {
  if (clock !== undefined) clearInterval(clock)
})

const actionMutation = useMutation({
  mutationFn: ({ action, id }: { action: OrderAction; id: number }) =>
    action === 'pay' ? payOrder(id) : cancelOrder(id),
  onSuccess: async (updatedOrder) => {
    queryClient.setQueryData<OrderDetail>(['orders', 'detail', updatedOrder.id], updatedOrder)
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['orders', 'list'] }),
      queryClient.invalidateQueries({ queryKey: ['products'] }),
      queryClient.invalidateQueries({ queryKey: ['management'] }),
    ])
    ElMessage.success(updatedOrder.status === 'paid' ? '支付成功' : '订单已取消')
  },
  onError: async (error) => {
    ElMessage.error(errorMessage(error, '订单操作失败'))
    await orderQuery.refetch()
  },
})

async function performAction(action: OrderAction): Promise<void> {
  const order = orderQuery.data.value
  if (!order || actionMutation.isPending.value) return
  try {
    await ElMessageBox.confirm(
      action === 'pay' ? `确认模拟支付 ¥${order.total_amount} 吗？` : '取消后库存会释放，确定取消该订单吗？',
      action === 'pay' ? '确认支付' : '取消订单',
      {
        type: action === 'pay' ? 'info' : 'warning',
        confirmButtonText: action === 'pay' ? '确认支付' : '确认取消',
        cancelButtonText: '再想想',
      },
    )
    actionMutation.mutate({ action, id: order.id })
  } catch {
    // The customer dismissed the confirmation.
  }
}
</script>

<template>
  <div class="order-page">
    <el-breadcrumb separator="/" class="breadcrumb">
      <el-breadcrumb-item :to="{ name: listRouteName }">{{ listLabel }}</el-breadcrumb-item>
      <el-breadcrumb-item>订单详情</el-breadcrumb-item>
    </el-breadcrumb>

    <el-result v-if="!auth.isAuthenticated" icon="info" title="请先登录" sub-title="登录后才能查看订单详情">
      <template #extra>
        <el-button type="primary" @click="router.push({ name: 'login', query: { redirect: route.fullPath } })">去登录</el-button>
      </template>
    </el-result>

    <section v-else-if="orderQuery.isPending.value" class="loading-panel">
      <el-skeleton animated :rows="9" />
    </section>

    <el-result
      v-else-if="orderId === null || orderQuery.isError.value"
      icon="error"
      title="无法查看该订单"
      :sub-title="orderId === null ? '订单编号无效' : errorMessage(orderQuery.error.value)"
    >
      <template #extra>
        <el-button type="primary" @click="router.push({ name: listRouteName })">返回订单列表</el-button>
        <el-button v-if="orderId !== null" @click="orderQuery.refetch()">重新加载</el-button>
      </template>
    </el-result>

    <template v-else-if="orderQuery.data.value">
      <section class="status-banner" :class="`status-banner--${orderQuery.data.value.status}`">
        <div class="status-banner__icon" aria-hidden="true">
          {{ orderQuery.data.value.status === 'pending' ? '时' : orderQuery.data.value.status === 'paid' ? '✓' : '×' }}
        </div>
        <div class="status-banner__copy">
          <OrderStatusBadge :status="orderQuery.data.value.status" />
          <h1>
            {{
              orderQuery.data.value.status === 'pending'
                ? '订单等待支付'
                : orderQuery.data.value.status === 'paid'
                  ? '订单支付完成'
                  : '订单已经取消'
            }}
          </h1>
          <p v-if="orderQuery.data.value.status === 'pending' && !pendingExpired">
            请在 <strong class="countdown">{{ countdown }}</strong> 内完成支付
          </p>
          <p v-else-if="pendingExpired">页面计时已到，订单能否操作仍以服务器状态为准。</p>
          <p v-else-if="orderQuery.data.value.status === 'paid'">支付时间：{{ formatDateTime(orderQuery.data.value.paid_at) }}</p>
          <p v-else>取消时间：{{ formatDateTime(orderQuery.data.value.cancelled_at) }}</p>
        </div>
        <div v-if="orderQuery.data.value.status === 'pending' && !isManagementView" class="status-banner__actions">
          <el-button
            type="primary"
            size="large"
            :loading="actionMutation.isPending.value && actionMutation.variables.value?.action === 'pay'"
            :disabled="actionMutation.isPending.value"
            @click="performAction('pay')"
          >
            模拟支付
          </el-button>
          <el-button
            plain
            size="large"
            :loading="actionMutation.isPending.value && actionMutation.variables.value?.action === 'cancel'"
            :disabled="actionMutation.isPending.value"
            @click="performAction('cancel')"
          >
            取消订单
          </el-button>
        </div>
        <el-button v-else-if="orderQuery.data.value.status === 'pending'" :loading="orderQuery.isFetching.value" @click="orderQuery.refetch()">
          刷新状态
        </el-button>
      </section>

      <el-alert
        v-if="actionMutation.isError.value"
        class="action-error"
        type="error"
        show-icon
        :closable="false"
        :title="errorMessage(actionMutation.error.value)"
      />

      <section class="order-grid">
        <div class="panel item-panel">
          <div class="panel__heading">
            <div>
              <p>ORDER ITEMS</p>
              <h2>商品明细</h2>
            </div>
            <span>共 {{ orderQuery.data.value.items.reduce((total, item) => total + item.quantity, 0) }} 件</span>
          </div>

          <article v-for="item in orderQuery.data.value.items" :key="item.id" class="order-item">
            <div class="order-item__mark">{{ item.quantity }}×</div>
            <div>
              <RouterLink :to="{ name: 'product-detail', params: { id: item.product_id } }">
                {{ item.product_name }}
              </RouterLink>
              <p>单价 ¥{{ item.product_price }}</p>
            </div>
            <strong><small>¥</small>{{ item.subtotal }}</strong>
          </article>

          <div class="grand-total">
            <span>订单总额</span>
            <strong><small>¥</small>{{ orderQuery.data.value.total_amount }}</strong>
          </div>
        </div>

        <aside class="panel info-panel">
          <div class="panel__heading">
            <div>
              <p>ORDER INFO</p>
              <h2>订单信息</h2>
            </div>
          </div>
          <dl>
            <div>
              <dt>订单编号</dt>
              <dd class="order-no">{{ orderQuery.data.value.order_no }}</dd>
            </div>
            <div>
              <dt>创建时间</dt>
              <dd>{{ formatDateTime(orderQuery.data.value.created_at) }}</dd>
            </div>
            <div>
              <dt>支付截止</dt>
              <dd>{{ formatDateTime(orderQuery.data.value.expires_at) }}</dd>
            </div>
            <div>
              <dt>订单状态</dt>
              <dd><OrderStatusBadge :status="orderQuery.data.value.status" /></dd>
            </div>
            <div>
              <dt>订单备注</dt>
              <dd>{{ orderQuery.data.value.remark || '无' }}</dd>
            </div>
          </dl>
        </aside>
      </section>
    </template>
  </div>
</template>

<style scoped>
.order-page {
  width: min(1060px, calc(100% - 36px));
  margin: 0 auto;
  padding: 30px 0 78px;
}

.breadcrumb {
  margin: 4px 0 22px;
}

.loading-panel,
.panel {
  border: 1px solid #e3e9e4;
  border-radius: 19px;
  background: #fff;
  box-shadow: 0 12px 36px rgb(30 51 35 / 6%);
}

.loading-panel {
  padding: 30px;
}

.status-banner {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 27px 30px;
  overflow: hidden;
  border: 1px solid #e1e8e3;
  border-radius: 20px;
  background: linear-gradient(115deg, #f6faf7, #eef5f0);
}

.status-banner--paid {
  background: linear-gradient(115deg, #f1faf4, #e8f5ec);
}

.status-banner--cancelled {
  background: linear-gradient(115deg, #f8f8f8, #f1f2f1);
}

.status-banner__icon {
  width: 64px;
  height: 64px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 50%;
  color: #fff;
  background: #ca832b;
  font-size: 22px;
  font-weight: 750;
  box-shadow: 0 8px 22px rgb(202 131 43 / 22%);
}

.status-banner--paid .status-banner__icon {
  background: #3b8656;
  box-shadow: 0 8px 22px rgb(59 134 86 / 22%);
}

.status-banner--cancelled .status-banner__icon {
  background: #808981;
  box-shadow: none;
}

.status-banner__copy {
  min-width: 0;
  flex: 1;
}

.status-banner h1 {
  margin: 8px 0 5px;
  color: #203126;
  font-size: 25px;
}

.status-banner p {
  margin: 0;
  color: #6d796f;
  font-size: 13px;
}

.countdown {
  margin: 0 4px;
  color: #c87626;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 17px;
  font-variant-numeric: tabular-nums;
}

.status-banner__actions {
  display: flex;
  align-items: center;
}

.action-error {
  margin-top: 16px;
}

.order-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px;
  gap: 22px;
  align-items: start;
  margin-top: 22px;
}

.panel {
  padding: 25px;
}

.panel__heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding-bottom: 19px;
  border-bottom: 1px solid #e9eeea;
}

.panel__heading p {
  margin: 0 0 7px;
  color: #37744e;
  font-size: 11px;
  font-weight: 750;
  letter-spacing: 0.15em;
}

.panel__heading h2 {
  margin: 0;
  color: #243428;
  font-size: 22px;
}

.panel__heading > span {
  color: #7e8880;
  font-size: 12px;
}

.order-item {
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr) auto;
  gap: 14px;
  align-items: center;
  padding: 20px 0;
  border-bottom: 1px solid #edf0ed;
}

.order-item__mark {
  width: 43px;
  height: 43px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  color: #3c714e;
  background: #edf5ef;
  font-size: 13px;
  font-weight: 750;
}

.order-item a {
  color: #293a2e;
  font-weight: 650;
  text-decoration: none;
}

.order-item p {
  margin: 7px 0 0;
  color: #7c867e;
  font-size: 12px;
}

.order-item > strong,
.grand-total strong {
  color: #d6532f;
  font-size: 18px;
  font-variant-numeric: tabular-nums;
}

.order-item small,
.grand-total small {
  margin-right: 2px;
  font-size: 11px;
}

.grand-total {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 22px;
  color: #344339;
  font-weight: 650;
}

.grand-total strong {
  font-size: 26px;
}

.info-panel dl {
  margin: 0;
}

.info-panel dl > div {
  display: grid;
  gap: 7px;
  padding: 15px 0;
  border-bottom: 1px solid #edf0ed;
}

.info-panel dl > div:last-child {
  border-bottom: 0;
}

.info-panel dt {
  color: #8b948c;
  font-size: 11px;
}

.info-panel dd {
  margin: 0;
  overflow-wrap: anywhere;
  color: #465249;
  font-size: 13px;
  line-height: 1.55;
}

.info-panel .order-no {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

:deep(.el-result) {
  min-height: 420px;
}

@media (max-width: 820px) {
  .order-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 650px) {
  .order-page {
    width: min(100% - 24px, 1060px);
    padding-top: 20px;
  }

  .status-banner {
    align-items: flex-start;
    flex-wrap: wrap;
    padding: 23px 21px;
  }

  .status-banner__icon {
    width: 50px;
    height: 50px;
  }

  .status-banner__actions {
    width: 100%;
  }

  .status-banner__actions .el-button {
    flex: 1;
  }
}
</style>
