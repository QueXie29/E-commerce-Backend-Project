<script setup lang="ts">
import type { ProductSummary } from '@/shared/api/contracts'

import ProductImage from './ProductImage.vue'

defineProps<{
  product: ProductSummary
}>()
</script>

<template>
  <RouterLink
    class="product-card"
    :to="{ name: 'product-detail', params: { id: product.id } }"
    :aria-label="`查看${product.name}`"
  >
    <ProductImage :src="product.image_url" :alt="product.name" />
    <div class="product-card__body">
      <div class="product-card__meta">
        <span>{{ product.category.name }}</span>
        <span>已售 {{ product.sales_count }}</span>
      </div>
      <h2>{{ product.name }}</h2>
      <div class="product-card__bottom">
        <strong><small>¥</small>{{ product.price }}</strong>
        <span :class="{ 'is-low': product.stock > 0 && product.stock <= 5 }">
          {{ product.stock > 0 ? `库存 ${product.stock}` : '暂时缺货' }}
        </span>
      </div>
    </div>
  </RouterLink>
</template>

<style scoped>
.product-card {
  display: block;
  overflow: hidden;
  color: inherit;
  text-decoration: none;
  border: 1px solid #e5ebe6;
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 8px 28px rgb(27 48 32 / 6%);
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    border-color 0.2s ease;
}

.product-card:hover {
  transform: translateY(-4px);
  border-color: #c9d7cc;
  box-shadow: 0 18px 38px rgb(27 48 32 / 11%);
}

.product-card__body {
  padding: 17px 18px 19px;
}

.product-card__meta,
.product-card__bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.product-card__meta {
  color: #7d887f;
  font-size: 12px;
}

h2 {
  min-height: 48px;
  margin: 10px 0 18px;
  color: #1e2d22;
  font-size: 17px;
  line-height: 1.45;
}

strong {
  color: #d6532f;
  font-size: 22px;
  font-variant-numeric: tabular-nums;
}

strong small {
  margin-right: 2px;
  font-size: 13px;
}

.product-card__bottom > span {
  color: #78827a;
  font-size: 12px;
}

.product-card__bottom > span.is-low {
  color: #c97324;
}
</style>
