<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { ElMessage } from 'element-plus'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import ProductImage from '@/components/storefront/ProductImage.vue'
import { addCartItem } from '@/shared/api/cart'
import { errorMessage } from '@/shared/api/errors'
import { getProduct } from '@/shared/api/products'
import { useAuthStore } from '@/stores/auth'

defineOptions({ name: 'ProductDetailView' })

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const queryClient = useQueryClient()
const quantity = ref(1)

const productId = computed(() => {
  const parsed = Number(route.params.id)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
})

const productQuery = useQuery({
  queryKey: computed(() => ['products', 'detail', productId.value]),
  queryFn: () => {
    if (productId.value === null) throw new Error('商品编号无效')
    return getProduct(productId.value)
  },
  enabled: computed(() => productId.value !== null),
})

watch(
  () => productQuery.data.value?.stock,
  (stock) => {
    if (stock !== undefined && quantity.value > stock) quantity.value = Math.max(1, stock)
  },
)

const addMutation = useMutation({
  mutationFn: ({ id, count }: { id: number; count: number }) => addCartItem(id, count),
  onSuccess: async () => {
    await queryClient.invalidateQueries({ queryKey: ['cart'], exact: true })
    ElMessage.success('已加入购物车')
  },
  onError: (error) => ElMessage.error(errorMessage(error, '加入购物车失败')),
})

async function addToCart(goToCart = false): Promise<void> {
  if (!auth.isAuthenticated) {
    await router.push({ name: 'login', query: { redirect: route.fullPath } })
    return
  }

  const product = productQuery.data.value
  if (!product || product.stock <= 0 || addMutation.isPending.value) return
  try {
    await addMutation.mutateAsync({ id: product.id, count: quantity.value })
    if (goToCart) await router.push({ name: 'cart' })
  } catch {
    // onError already presents the request failure to the customer.
  }
}
</script>

<template>
  <div class="detail-page">
    <el-breadcrumb separator="/" class="breadcrumb">
      <el-breadcrumb-item :to="{ name: 'product-list' }">全部商品</el-breadcrumb-item>
      <el-breadcrumb-item v-if="productQuery.data.value">{{ productQuery.data.value.category.name }}</el-breadcrumb-item>
      <el-breadcrumb-item>商品详情</el-breadcrumb-item>
    </el-breadcrumb>

    <section v-if="productQuery.isPending.value" class="detail-card detail-card--loading">
      <el-skeleton animated>
        <template #template>
          <div class="loading-grid">
            <el-skeleton-item variant="image" class="loading-image" />
            <div class="loading-copy">
              <el-skeleton-item variant="text" style="width: 25%" />
              <el-skeleton-item variant="h1" style="width: 72%" />
              <el-skeleton-item variant="text" style="width: 95%" />
              <el-skeleton-item variant="text" style="width: 55%" />
              <el-skeleton-item variant="button" style="width: 190px; height: 46px" />
            </div>
          </div>
        </template>
      </el-skeleton>
    </section>

    <el-result
      v-else-if="productId === null || productQuery.isError.value"
      icon="error"
      title="无法查看该商品"
      :sub-title="productId === null ? '商品编号无效' : errorMessage(productQuery.error.value)"
    >
      <template #extra>
        <el-button type="primary" @click="router.push({ name: 'product-list' })">返回商品列表</el-button>
        <el-button v-if="productId !== null" @click="productQuery.refetch()">重新加载</el-button>
      </template>
    </el-result>

    <section v-else-if="productQuery.data.value" class="detail-card">
      <div class="detail-card__visual">
        <ProductImage :src="productQuery.data.value.image_url" :alt="productQuery.data.value.name" />
        <span v-if="productQuery.data.value.stock <= 0" class="sold-out">暂时缺货</span>
      </div>

      <div class="detail-card__content">
        <div class="category-line">
          <span>{{ productQuery.data.value.category.name }}</span>
          <span>已售 {{ productQuery.data.value.sales_count }}</span>
        </div>
        <h1>{{ productQuery.data.value.name }}</h1>
        <div class="price"><small>¥</small>{{ productQuery.data.value.price }}</div>
        <p class="description">
          {{ productQuery.data.value.description || '这件商品暂时没有详细介绍。' }}
        </p>

        <div class="purchase-panel">
          <div class="stock-row">
            <span>购买数量</span>
            <span :class="{ 'stock-low': productQuery.data.value.stock > 0 && productQuery.data.value.stock <= 5 }">
              {{ productQuery.data.value.stock > 0 ? `库存 ${productQuery.data.value.stock} 件` : '无库存' }}
            </span>
          </div>
          <el-input-number
            v-model="quantity"
            :aria-label="`${productQuery.data.value.name}的购买数量`"
            :min="1"
            :max="Math.max(1, productQuery.data.value.stock)"
            :disabled="productQuery.data.value.stock <= 0"
          />
          <div class="purchase-actions">
            <el-button
              type="primary"
              size="large"
              :loading="addMutation.isPending.value"
              :disabled="productQuery.data.value.stock <= 0"
              @click="addToCart(false)"
            >
              加入购物车
            </el-button>
            <el-button
              size="large"
              plain
              :disabled="productQuery.data.value.stock <= 0 || addMutation.isPending.value"
              @click="addToCart(true)"
            >
              立即购买
            </el-button>
          </div>
          <p v-if="!auth.isAuthenticated" class="login-tip">登录后即可加入购物车，我们会带你回到当前页面。</p>
        </div>

        <div class="service-notes" aria-label="服务说明">
          <span>✓ 库存实时校验</span>
          <span>✓ 安全结算</span>
          <span>✓ 订单状态可追踪</span>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.detail-page {
  width: min(1120px, calc(100% - 36px));
  margin: 0 auto;
  padding: 30px 0 76px;
}

.breadcrumb {
  margin: 4px 0 22px;
}

.detail-card {
  display: grid;
  grid-template-columns: minmax(0, 1.04fr) minmax(360px, 0.96fr);
  overflow: hidden;
  border: 1px solid #e5ebe6;
  border-radius: 24px;
  background: #fff;
  box-shadow: 0 20px 55px rgb(27 48 32 / 8%);
}

.detail-card--loading {
  display: block;
  padding: 28px;
}

.loading-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 45px;
}

.loading-image {
  width: 100%;
  height: auto;
  aspect-ratio: 4 / 3;
}

.loading-copy {
  display: grid;
  align-content: center;
  gap: 22px;
}

.detail-card__visual {
  position: relative;
  align-self: stretch;
  background: #f0f4f1;
}

.detail-card__visual :deep(.product-image) {
  height: 100%;
  min-height: 510px;
  aspect-ratio: auto;
}

.sold-out {
  position: absolute;
  top: 22px;
  left: 22px;
  padding: 8px 15px;
  border-radius: 999px;
  color: #fff;
  background: rgb(37 48 40 / 82%);
  font-size: 13px;
}

.detail-card__content {
  padding: 48px 46px 40px;
}

.category-line,
.stock-row,
.service-notes {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.category-line {
  color: #6f7c72;
  font-size: 13px;
}

.category-line span:first-child {
  color: #34724b;
  font-weight: 700;
  letter-spacing: 0.08em;
}

h1 {
  margin: 16px 0 12px;
  color: #1c2d21;
  font-size: clamp(29px, 4vw, 43px);
  line-height: 1.22;
  letter-spacing: -0.035em;
}

.price {
  margin: 12px 0 24px;
  color: #d6532f;
  font-size: 32px;
  font-weight: 750;
  font-variant-numeric: tabular-nums;
}

.price small {
  margin-right: 3px;
  font-size: 16px;
}

.description {
  min-height: 72px;
  margin: 0;
  color: #667168;
  line-height: 1.75;
  white-space: pre-line;
}

.purchase-panel {
  margin-top: 30px;
  padding: 23px;
  border-radius: 17px;
  background: #f6f8f6;
}

.stock-row {
  margin-bottom: 15px;
  color: #506056;
  font-size: 13px;
}

.stock-low {
  color: #bd6924;
}

.purchase-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 18px;
}

.purchase-actions .el-button + .el-button {
  margin-left: 0;
}

.login-tip {
  margin: 13px 0 0;
  color: #7b877e;
  font-size: 12px;
}

.service-notes {
  margin-top: 24px;
  color: #6d786f;
  font-size: 12px;
}

@media (max-width: 820px) {
  .detail-card {
    grid-template-columns: 1fr;
  }

  .detail-card__visual :deep(.product-image) {
    min-height: 0;
    aspect-ratio: 4 / 3;
  }

  .loading-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 520px) {
  .detail-page {
    width: min(100% - 24px, 1120px);
    padding-top: 18px;
  }

  .detail-card__content {
    padding: 29px 22px;
  }

  .purchase-actions {
    grid-template-columns: 1fr;
  }

  .service-notes {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
