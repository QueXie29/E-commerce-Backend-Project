<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { ElMessage } from 'element-plus'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import ProductImage from '@/components/storefront/ProductImage.vue'
import { getCart } from '@/shared/api/cart'
import { errorMessage } from '@/shared/api/errors'
import { abandonCheckoutIntent, createOrder } from '@/shared/api/orders'
import { useAuthStore } from '@/stores/auth'

defineOptions({ name: 'CheckoutView' })

const router = useRouter()
const auth = useAuthStore()
const queryClient = useQueryClient()
const remark = ref('')
const submissionLocked = ref(false)

const cartQuery = useQuery({
  queryKey: ['cart'],
  queryFn: getCart,
  enabled: computed(() => auth.isAuthenticated),
})

const selectedItems = computed(() => cartQuery.data.value?.items.filter((item) => item.selected) ?? [])
const unavailableItems = computed(() =>
  selectedItems.value.filter(
    (item) => item.product.status !== 'active' || item.product.stock <= 0 || item.quantity > item.product.stock,
  ),
)
const cartSignature = computed(() =>
  selectedItems.value
    .map((item) => `${item.id}:${item.product.id}:${item.quantity}`)
    .sort()
    .join('|'),
)

const orderMutation = useMutation({
  mutationFn: ({ orderRemark, signature }: { orderRemark: string; signature: string }) =>
    createOrder(orderRemark, signature),
  onSuccess: async (order) => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['cart'], exact: true }),
      queryClient.invalidateQueries({ queryKey: ['orders', 'list'] }),
      queryClient.invalidateQueries({ queryKey: ['products'] }),
      queryClient.invalidateQueries({ queryKey: ['management'] }),
    ])
    ElMessage.success('订单提交成功')
    await router.replace({ name: 'order-detail', params: { id: order.id } })
  },
  onError: (error) => ElMessage.error(errorMessage(error, '订单提交失败，请稍后重试')),
})

async function returnToCart(): Promise<void> {
  abandonCheckoutIntent()
  await router.push({ name: 'cart' })
}

async function submitOrder(): Promise<void> {
  if (submissionLocked.value || orderMutation.isPending.value) return
  if (!selectedItems.value.length) {
    ElMessage.warning('购物车中没有选中的商品')
    return
  }
  if (unavailableItems.value.length) {
    ElMessage.warning('部分商品库存发生变化，请返回购物车调整')
    return
  }

  submissionLocked.value = true
  try {
    await orderMutation.mutateAsync({ orderRemark: remark.value.trim(), signature: cartSignature.value })
  } catch {
    // onError already presents the request failure to the customer.
  } finally {
    submissionLocked.value = false
  }
}
</script>

<template>
  <div class="checkout-page">
    <div class="steps" aria-label="结算步骤">
      <span class="is-done">1 <small>购物车</small></span>
      <i />
      <span class="is-current">2 <small>确认订单</small></span>
      <i />
      <span>3 <small>完成</small></span>
    </div>

    <div class="page-heading">
      <p>CHECKOUT</p>
      <h1>确认订单</h1>
      <span>请核对商品与数量，订单创建后将为你短暂保留库存。</span>
    </div>

    <el-result v-if="!auth.isAuthenticated" icon="info" title="请先登录" sub-title="登录后才能确认并提交订单">
      <template #extra>
        <el-button type="primary" @click="router.push({ name: 'login', query: { redirect: '/checkout' } })">去登录</el-button>
      </template>
    </el-result>

    <section v-else-if="cartQuery.isPending.value" class="checkout-layout">
      <el-skeleton class="panel" animated :rows="8" />
      <el-skeleton class="panel" animated :rows="5" />
    </section>

    <el-result
      v-else-if="cartQuery.isError.value"
      icon="error"
      title="结算信息加载失败"
      :sub-title="errorMessage(cartQuery.error.value)"
    >
      <template #extra><el-button type="primary" @click="cartQuery.refetch()">重新加载</el-button></template>
    </el-result>

    <el-empty v-else-if="!selectedItems.length" description="没有选中可结算的商品">
      <el-button type="primary" @click="router.replace({ name: 'cart' })">返回购物车</el-button>
    </el-empty>

    <section v-else class="checkout-layout">
      <div class="panel order-items">
        <div class="panel__heading">
          <div>
            <p>ITEMS</p>
            <h2>商品清单</h2>
          </div>
          <button class="return-link" type="button" @click="returnToCart">返回修改</button>
        </div>

        <article v-for="item in selectedItems" :key="item.id" class="checkout-item">
          <ProductImage compact :src="item.product.image_url" :alt="item.product.name" />
          <div>
            <RouterLink :to="{ name: 'product-detail', params: { id: item.product.id } }">
              {{ item.product.name }}
            </RouterLink>
            <p>¥{{ item.product.price }} × {{ item.quantity }}</p>
            <span v-if="item.product.status !== 'active' || item.quantity > item.product.stock" class="warning">
              商品状态或库存已变化
            </span>
          </div>
          <strong><small>¥</small>{{ item.subtotal }}</strong>
        </article>

        <div class="remark-field">
          <div>
            <label for="order-remark">订单备注</label>
            <span>{{ remark.length }}/255</span>
          </div>
          <el-input
            id="order-remark"
            v-model="remark"
            type="textarea"
            :rows="4"
            maxlength="255"
            resize="none"
            placeholder="选填，可填写商品或订单相关说明"
          />
        </div>
      </div>

      <aside class="panel final-summary">
        <p>PAYMENT SUMMARY</p>
        <h2>应付摘要</h2>
        <div class="summary-row">
          <span>商品种类</span>
          <span>{{ selectedItems.length }} 种</span>
        </div>
        <div class="summary-row">
          <span>商品件数</span>
          <span>{{ selectedItems.reduce((total, item) => total + item.quantity, 0) }} 件</span>
        </div>
        <div class="summary-total">
          <span>应付金额</span>
          <strong><small>¥</small>{{ cartQuery.data.value?.total_amount ?? '0.00' }}</strong>
        </div>
        <p class="server-note">最终金额和库存以提交时的服务端校验为准</p>

        <el-alert
          v-if="unavailableItems.length"
          title="部分商品不可结算，请返回购物车调整"
          type="warning"
          show-icon
          :closable="false"
        />
        <el-alert
          v-else-if="orderMutation.isError.value"
          :title="errorMessage(orderMutation.error.value)"
          type="error"
          show-icon
          :closable="false"
        />

        <el-button
          class="submit-button"
          type="primary"
          size="large"
          :loading="submissionLocked || orderMutation.isPending.value"
          :disabled="unavailableItems.length > 0"
          @click="submitOrder"
        >
          提交订单
        </el-button>
        <div class="safety-note">重复点击或网络重试不会重复创建同一订单</div>
      </aside>
    </section>
  </div>
</template>

<style scoped>
.checkout-page {
  width: min(1060px, calc(100% - 36px));
  margin: 0 auto;
  padding: 30px 0 78px;
}

.steps {
  width: min(500px, 90%);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 4px auto 34px;
}

.steps > span {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border: 1px solid #dce3dd;
  border-radius: 50%;
  color: #89948b;
  font-size: 12px;
  background: #fff;
}

.steps > span small {
  position: absolute;
  margin-top: 58px;
  width: 70px;
  color: #7c877e;
  text-align: center;
}

.steps > span.is-done,
.steps > span.is-current {
  border-color: #33734b;
  color: #fff;
  background: #33734b;
}

.steps > span.is-current {
  box-shadow: 0 0 0 5px rgb(51 115 75 / 11%);
}

.steps i {
  width: 130px;
  height: 1px;
  background: #dfe5e0;
}

.page-heading {
  margin: 55px 0 26px;
}

.page-heading p,
.panel__heading p,
.final-summary > p {
  margin: 0 0 7px;
  color: #37744e;
  font-size: 11px;
  font-weight: 750;
  letter-spacing: 0.15em;
}

.page-heading h1 {
  margin: 0 0 8px;
  color: #1c2d21;
  font-size: 34px;
}

.page-heading > span {
  color: #7a857d;
  font-size: 13px;
}

.checkout-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 310px;
  gap: 24px;
  align-items: start;
}

.panel {
  border: 1px solid #e3e9e4;
  border-radius: 19px;
  background: #fff;
  box-shadow: 0 12px 36px rgb(30 51 35 / 6%);
}

.order-items {
  padding: 25px;
}

.panel__heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding-bottom: 20px;
  border-bottom: 1px solid #e9eeea;
}

.panel h2 {
  margin: 0;
  color: #243428;
  font-size: 22px;
}

.return-link {
  border: 0;
  padding: 0;
  background: transparent;
  color: #39764f;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  text-decoration: none;
}

.checkout-item {
  display: grid;
  grid-template-columns: 86px minmax(0, 1fr) auto;
  gap: 17px;
  align-items: center;
  padding: 20px 0;
  border-bottom: 1px solid #edf0ed;
}

.checkout-item > div a {
  color: #27382c;
  font-weight: 650;
  text-decoration: none;
}

.checkout-item > div p {
  margin: 8px 0 0;
  color: #7a857d;
  font-size: 12px;
}

.checkout-item .warning {
  display: block;
  margin-top: 5px;
  color: #bd6429;
  font-size: 12px;
}

.checkout-item > strong,
.summary-total strong {
  color: #d6532f;
  font-size: 18px;
  font-variant-numeric: tabular-nums;
}

.checkout-item small,
.summary-total small {
  margin-right: 2px;
  font-size: 11px;
}

.remark-field {
  padding-top: 24px;
}

.remark-field > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.remark-field label {
  color: #334238;
  font-size: 14px;
  font-weight: 650;
}

.remark-field span {
  color: #99a099;
  font-size: 11px;
}

.final-summary {
  position: sticky;
  top: 88px;
  padding: 26px;
}

.final-summary h2 {
  margin-bottom: 24px;
}

.summary-row,
.summary-total {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.summary-row {
  margin: 13px 0;
  color: #6d786f;
  font-size: 13px;
}

.summary-total {
  margin-top: 22px;
  padding-top: 20px;
  border-top: 1px solid #e5ebe6;
  color: #303f34;
  font-weight: 650;
}

.summary-total strong {
  font-size: 26px;
}

.server-note {
  margin: 8px 0 20px;
  color: #919991;
  font-size: 11px;
  line-height: 1.5;
  text-align: right;
}

.submit-button {
  width: 100%;
  margin-top: 18px;
}

.safety-note {
  margin-top: 11px;
  color: #8d968f;
  font-size: 10px;
  line-height: 1.5;
  text-align: center;
}

:deep(.el-empty),
:deep(.el-result) {
  min-height: 400px;
}

@media (max-width: 820px) {
  .checkout-layout {
    grid-template-columns: 1fr;
  }

  .final-summary {
    position: static;
  }
}

@media (max-width: 520px) {
  .checkout-page {
    width: min(100% - 24px, 1060px);
  }

  .steps i {
    width: 75px;
  }

  .order-items {
    padding: 18px;
  }

  .checkout-item {
    grid-template-columns: 70px minmax(0, 1fr);
  }

  .checkout-item :deep(.product-image--compact) {
    width: 70px;
    min-width: 70px;
  }

  .checkout-item > strong {
    grid-column: 2;
  }
}
</style>
