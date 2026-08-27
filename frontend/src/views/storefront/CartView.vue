<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import ProductImage from '@/components/storefront/ProductImage.vue'
import type { CartItem } from '@/shared/api/contracts'
import { clearCart, getCart, removeCartItem, updateCartItem } from '@/shared/api/cart'
import { errorMessage } from '@/shared/api/errors'
import { useAuthStore } from '@/stores/auth'

defineOptions({ name: 'CartView' })

const router = useRouter()
const auth = useAuthStore()
const queryClient = useQueryClient()

const cartQuery = useQuery({
  queryKey: ['cart'],
  queryFn: getCart,
  enabled: computed(() => auth.isAuthenticated),
})

async function refreshCart(): Promise<void> {
  await queryClient.invalidateQueries({ queryKey: ['cart'], exact: true })
}

const patchMutation = useMutation({
  mutationFn: ({ id, input }: { id: number; input: { quantity?: number; selected?: boolean } }) =>
    updateCartItem(id, input),
  onSuccess: refreshCart,
  onError: (error) => ElMessage.error(errorMessage(error, '购物车更新失败')),
})

const batchSelectionMutation = useMutation({
  mutationFn: async ({ items, selected }: { items: CartItem[]; selected: boolean }) => {
    await Promise.all(
      items.filter((item) => item.selected !== selected).map((item) => updateCartItem(item.id, { selected })),
    )
  },
  onError: (error) => ElMessage.error(errorMessage(error, '批量选择失败')),
  onSettled: refreshCart,
})

const deleteMutation = useMutation({
  mutationFn: removeCartItem,
  onSuccess: async () => {
    await refreshCart()
    ElMessage.success('商品已移除')
  },
  onError: (error) => ElMessage.error(errorMessage(error, '移除商品失败')),
})

const clearMutation = useMutation({
  mutationFn: clearCart,
  onSuccess: async () => {
    await refreshCart()
    ElMessage.success('购物车已清空')
  },
  onError: (error) => ElMessage.error(errorMessage(error, '清空购物车失败')),
})

const items = computed(() => cartQuery.data.value?.items ?? [])
const selectedItems = computed(() => items.value.filter((item) => item.selected))
const allSelected = computed(() => items.value.length > 0 && selectedItems.value.length === items.value.length)
const hasUnavailableSelected = computed(() =>
  selectedItems.value.some(
    (item) => item.product.status !== 'active' || item.product.stock < item.quantity || item.product.stock <= 0,
  ),
)

function itemIsUpdating(id: number): boolean {
  return patchMutation.isPending.value && patchMutation.variables.value?.id === id
}

function updateQuantity(item: CartItem, quantity: number | undefined): void {
  if (!quantity || quantity === item.quantity || patchMutation.isPending.value) return
  patchMutation.mutate({ id: item.id, input: { quantity } })
}

function updateSelected(item: CartItem, selected: string | number | boolean): void {
  if (patchMutation.isPending.value) return
  patchMutation.mutate({ id: item.id, input: { selected: Boolean(selected) } })
}

function toggleAll(selected: string | number | boolean): void {
  if (batchSelectionMutation.isPending.value) return
  batchSelectionMutation.mutate({ items: items.value, selected: Boolean(selected) })
}

async function confirmRemove(item: CartItem): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定从购物车移除“${item.product.name}”吗？`, '移除商品', {
      type: 'warning',
      confirmButtonText: '移除',
      cancelButtonText: '保留',
    })
    deleteMutation.mutate(item.id)
  } catch {
    // The customer kept the item.
  }
}

async function confirmClear(): Promise<void> {
  try {
    await ElMessageBox.confirm('确定清空购物车中的全部商品吗？', '清空购物车', {
      type: 'warning',
      confirmButtonText: '清空',
      cancelButtonText: '取消',
    })
    clearMutation.mutate()
  } catch {
    // The customer cancelled the destructive action.
  }
}

async function checkout(): Promise<void> {
  if (!selectedItems.value.length) {
    ElMessage.warning('请先选择要结算的商品')
    return
  }
  if (hasUnavailableSelected.value) {
    ElMessage.warning('选中的商品存在库存不足或已下架，请调整后再结算')
    return
  }
  await router.push({ name: 'checkout' })
}
</script>

<template>
  <div class="cart-page">
    <div class="page-heading">
      <div>
        <p>YOUR BAG</p>
        <h1>我的购物车</h1>
      </div>
      <RouterLink :to="{ name: 'product-list' }">继续逛逛 →</RouterLink>
    </div>

    <el-result v-if="!auth.isAuthenticated" icon="info" title="登录后查看购物车" sub-title="你的购物车会安全保存在账户中">
      <template #extra>
        <el-button type="primary" @click="router.push({ name: 'login', query: { redirect: '/cart' } })">去登录</el-button>
      </template>
    </el-result>

    <section v-else-if="cartQuery.isPending.value" class="cart-layout">
      <div class="cart-list loading-list">
        <el-skeleton v-for="index in 3" :key="index" animated :rows="3" />
      </div>
      <el-skeleton class="summary-card" animated :rows="5" />
    </section>

    <el-result
      v-else-if="cartQuery.isError.value"
      icon="error"
      title="购物车加载失败"
      :sub-title="errorMessage(cartQuery.error.value)"
    >
      <template #extra><el-button type="primary" @click="cartQuery.refetch()">重新加载</el-button></template>
    </el-result>

    <el-empty v-else-if="!items.length" description="购物车还是空的">
      <el-button type="primary" @click="router.push({ name: 'product-list' })">去挑选商品</el-button>
    </el-empty>

    <section v-else class="cart-layout">
      <div class="cart-list">
        <div class="cart-list__toolbar">
          <el-checkbox
            :model-value="allSelected"
            :indeterminate="selectedItems.length > 0 && !allSelected"
            :disabled="batchSelectionMutation.isPending.value"
            @change="toggleAll"
          >
            全选（{{ selectedItems.length }}/{{ items.length }}）
          </el-checkbox>
          <el-button
            text
            type="danger"
            :loading="clearMutation.isPending.value"
            @click="confirmClear"
          >
            清空购物车
          </el-button>
        </div>

        <article v-for="item in items" :key="item.id" class="cart-item" :class="{ 'is-unavailable': item.product.status !== 'active' }">
          <el-checkbox
            :model-value="item.selected"
            :disabled="itemIsUpdating(item.id)"
            :aria-label="`选择${item.product.name}`"
            @change="(selected: string | number | boolean) => updateSelected(item, selected)"
          />
          <RouterLink :to="{ name: 'product-detail', params: { id: item.product.id } }" class="cart-item__image">
            <ProductImage compact :src="item.product.image_url" :alt="item.product.name" />
          </RouterLink>
          <div class="cart-item__info">
            <RouterLink :to="{ name: 'product-detail', params: { id: item.product.id } }">
              {{ item.product.name }}
            </RouterLink>
            <span v-if="item.product.status !== 'active'" class="warning">商品已下架</span>
            <span v-else-if="item.quantity > item.product.stock" class="warning">库存仅剩 {{ item.product.stock }} 件</span>
            <span v-else>单价 ¥{{ item.product.price }}</span>
          </div>
          <div class="cart-item__controls">
            <el-input-number
              :model-value="item.quantity"
              :aria-label="`${item.product.name}的购买数量`"
              :min="1"
              :max="Math.max(1, item.product.stock)"
              :disabled="item.product.status !== 'active' || item.product.stock <= 0 || itemIsUpdating(item.id)"
              size="small"
              @change="(value: number | undefined) => updateQuantity(item, value)"
            />
            <div class="cart-item__price">
              <strong><small>¥</small>{{ item.subtotal }}</strong>
              <el-button
                text
                :loading="deleteMutation.isPending.value && deleteMutation.variables.value === item.id"
                @click="confirmRemove(item)"
              >
                移除
              </el-button>
            </div>
          </div>
        </article>
      </div>

      <aside class="summary-card">
        <p class="summary-card__eyebrow">ORDER SUMMARY</p>
        <h2>结算摘要</h2>
        <div class="summary-row">
          <span>已选商品</span>
          <span>{{ selectedItems.length }} 种</span>
        </div>
        <div class="summary-row">
          <span>商品件数</span>
          <span>{{ selectedItems.reduce((total, item) => total + item.quantity, 0) }} 件</span>
        </div>
        <div class="summary-total">
          <span>合计</span>
          <strong><small>¥</small>{{ cartQuery.data.value?.total_amount ?? '0.00' }}</strong>
        </div>
        <p class="amount-note">金额由服务端根据当前勾选商品计算</p>
        <el-alert
          v-if="hasUnavailableSelected"
          title="部分选中商品库存不足或已下架"
          type="warning"
          :closable="false"
          show-icon
        />
        <el-button
          class="checkout-button"
          type="primary"
          size="large"
          :disabled="!selectedItems.length || hasUnavailableSelected"
          @click="checkout"
        >
          去结算
        </el-button>
      </aside>
    </section>
  </div>
</template>

<style scoped>
.cart-page {
  width: min(1120px, calc(100% - 36px));
  margin: 0 auto;
  padding: 38px 0 76px;
}

.page-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 28px;
}

.page-heading p,
.summary-card__eyebrow {
  margin: 0 0 8px;
  color: #37734d;
  font-size: 11px;
  font-weight: 750;
  letter-spacing: 0.16em;
}

.page-heading h1 {
  margin: 0;
  color: #1c2d21;
  font-size: 34px;
}

.page-heading a {
  color: #39764f;
  font-size: 14px;
  text-decoration: none;
}

.cart-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 24px;
  align-items: start;
}

.cart-list,
.summary-card {
  border: 1px solid #e3e9e4;
  border-radius: 19px;
  background: #fff;
  box-shadow: 0 12px 36px rgb(30 51 35 / 6%);
}

.loading-list {
  display: grid;
  gap: 28px;
  padding: 26px;
}

.cart-list__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px 21px;
  border-bottom: 1px solid #edf0ed;
}

.cart-item {
  display: grid;
  grid-template-columns: auto 86px minmax(160px, 1fr) auto;
  gap: 18px;
  align-items: center;
  padding: 21px;
  border-bottom: 1px solid #edf0ed;
}

.cart-item:last-child {
  border-bottom: 0;
}

.cart-item.is-unavailable {
  background: #fafafa;
}

.cart-item__image {
  display: block;
}

.cart-item__info {
  min-width: 0;
  display: grid;
  gap: 8px;
}

.cart-item__info a {
  overflow: hidden;
  color: #26372b;
  font-size: 15px;
  font-weight: 650;
  text-decoration: none;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cart-item__info span {
  color: #7b867e;
  font-size: 12px;
}

.cart-item__info .warning {
  color: #c3672a;
}

.cart-item__price {
  display: grid;
  justify-items: end;
  gap: 5px;
}

.cart-item__controls {
  display: flex;
  align-items: center;
  gap: 18px;
}

.cart-item__price strong,
.summary-total strong {
  color: #d6532f;
  font-size: 19px;
  font-variant-numeric: tabular-nums;
}

.cart-item__price small,
.summary-total small {
  margin-right: 2px;
  font-size: 12px;
}

.summary-card {
  position: sticky;
  top: 88px;
  padding: 25px;
}

.summary-card h2 {
  margin: 0 0 24px;
  color: #223226;
  font-size: 23px;
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
  border-top: 1px solid #e6ebe7;
  color: #2d3c31;
  font-weight: 650;
}

.summary-total strong {
  font-size: 25px;
}

.amount-note {
  margin: 8px 0 20px;
  color: #909890;
  font-size: 11px;
  text-align: right;
}

.checkout-button {
  width: 100%;
  margin-top: 18px;
}

:deep(.el-empty),
:deep(.el-result) {
  min-height: 430px;
}

@media (max-width: 900px) {
  .cart-layout {
    grid-template-columns: 1fr;
  }

  .summary-card {
    position: static;
  }
}

@media (max-width: 650px) {
  .cart-page {
    width: min(100% - 24px, 1120px);
    padding-top: 24px;
  }

  .cart-item {
    grid-template-columns: auto 72px 1fr;
    gap: 12px;
  }

  .cart-item__image :deep(.product-image--compact) {
    width: 72px;
    min-width: 72px;
  }

  .cart-item__controls {
    grid-column: 2 / 4;
    display: flex;
    justify-content: space-between;
    min-width: 0;
  }

  .cart-item__controls > .el-input-number {
    width: 112px;
  }

  .page-heading a {
    display: none;
  }
}
</style>
