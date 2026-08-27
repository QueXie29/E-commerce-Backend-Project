<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { ElMessage } from 'element-plus'
import { computed, reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import ProductCard from '@/components/storefront/ProductCard.vue'
import { firstQueryValue, positivePage } from '@/components/storefront/format'
import type { ProductFilters } from '@/shared/api/contracts'
import { errorMessage } from '@/shared/api/errors'
import { listCategories, listProducts } from '@/shared/api/products'

defineOptions({ name: 'ProductListView' })

const route = useRoute()
const router = useRouter()
const pageSize = 12

const orderingValues = [
  'created_at',
  '-created_at',
  'price',
  '-price',
  'sales_count',
  '-sales_count',
] as const
type Ordering = (typeof orderingValues)[number]

function routeOrdering(): Ordering {
  const value = firstQueryValue(route.query.ordering)
  return orderingValues.includes(value as Ordering) ? (value as Ordering) : '-created_at'
}

const form = reactive({
  keyword: firstQueryValue(route.query.keyword),
  category: firstQueryValue(route.query.category),
  minPrice: firstQueryValue(route.query.min_price),
  maxPrice: firstQueryValue(route.query.max_price),
  ordering: routeOrdering(),
})

watch(
  () => route.query,
  () => {
    form.keyword = firstQueryValue(route.query.keyword)
    form.category = firstQueryValue(route.query.category)
    form.minPrice = firstQueryValue(route.query.min_price)
    form.maxPrice = firstQueryValue(route.query.max_price)
    form.ordering = routeOrdering()
  },
)

const page = computed(() => positivePage(route.query.page))
const filters = computed<ProductFilters>(() => {
  const category = Number(firstQueryValue(route.query.category))
  return {
    page: page.value,
    page_size: pageSize,
    keyword: firstQueryValue(route.query.keyword).trim() || undefined,
    category: Number.isInteger(category) && category > 0 ? category : undefined,
    min_price: firstQueryValue(route.query.min_price) || undefined,
    max_price: firstQueryValue(route.query.max_price) || undefined,
    ordering: routeOrdering(),
  }
})

const categoriesQuery = useQuery({
  queryKey: ['categories'],
  queryFn: listCategories,
  staleTime: 5 * 60 * 1000,
})

const productsQuery = useQuery({
  queryKey: computed(() => ['products', 'list', filters.value]),
  queryFn: () => listProducts(filters.value),
  placeholderData: (previous) => previous,
})

function isValidPrice(value: string): boolean {
  if (!value) return true
  const number = Number(value)
  return Number.isFinite(number) && number >= 0
}

async function search(): Promise<void> {
  if (!isValidPrice(form.minPrice) || !isValidPrice(form.maxPrice)) {
    ElMessage.warning('请输入大于或等于 0 的有效价格')
    return
  }
  if (form.minPrice && form.maxPrice && Number(form.minPrice) > Number(form.maxPrice)) {
    ElMessage.warning('最低价格不能高于最高价格')
    return
  }

  await router.push({
    name: 'product-list',
    query: {
      ...(form.keyword.trim() ? { keyword: form.keyword.trim() } : {}),
      ...(form.category ? { category: form.category } : {}),
      ...(form.minPrice ? { min_price: form.minPrice } : {}),
      ...(form.maxPrice ? { max_price: form.maxPrice } : {}),
      ...(form.ordering !== '-created_at' ? { ordering: form.ordering } : {}),
    },
  })
}

async function resetFilters(): Promise<void> {
  await router.push({ name: 'product-list' })
}

async function changePage(nextPage: number): Promise<void> {
  await router.push({
    name: 'product-list',
    query: {
      ...route.query,
      ...(nextPage > 1 ? { page: String(nextPage) } : { page: undefined }),
    },
  })
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
</script>

<template>
  <div class="catalog-page">
    <section class="hero">
      <div>
        <p class="eyebrow">MINI MALL · 精选好物</p>
        <h1>日常所需，认真挑选</h1>
        <p>从实用到惊喜，让每一次挑选都轻松一点。</p>
      </div>
      <div class="hero__stamp" aria-hidden="true">
        <strong>新鲜</strong>
        <span>每日上新</span>
      </div>
    </section>

    <section class="filter-card" aria-label="商品筛选">
      <el-input
        v-model="form.keyword"
        class="filter-card__keyword"
        clearable
        aria-label="搜索商品名称或描述"
        placeholder="搜索商品名称或描述"
        @keyup.enter="search"
      />
      <el-select v-model="form.category" clearable placeholder="全部分类" aria-label="商品分类" :loading="categoriesQuery.isLoading.value">
        <el-option
          v-for="category in categoriesQuery.data.value?.results ?? []"
          :key="category.id"
          :label="category.name"
          :value="String(category.id)"
        />
      </el-select>
      <div class="price-range">
        <el-input v-model="form.minPrice" inputmode="decimal" placeholder="最低价" aria-label="最低价格" @keyup.enter="search" />
        <span>—</span>
        <el-input v-model="form.maxPrice" inputmode="decimal" placeholder="最高价" aria-label="最高价格" @keyup.enter="search" />
      </div>
      <el-select v-model="form.ordering" aria-label="商品排序">
        <el-option label="最新上架" value="-created_at" />
        <el-option label="最早上架" value="created_at" />
        <el-option label="价格从低到高" value="price" />
        <el-option label="价格从高到低" value="-price" />
        <el-option label="销量从高到低" value="-sales_count" />
        <el-option label="销量从低到高" value="sales_count" />
      </el-select>
      <el-button type="primary" @click="search">查找商品</el-button>
      <el-button plain @click="resetFilters">重置</el-button>
      <div v-if="categoriesQuery.isError.value" class="filter-card__error" role="status">
        <span>分类加载失败：{{ errorMessage(categoriesQuery.error.value) }}</span>
        <el-button link type="primary" @click="categoriesQuery.refetch()">重试</el-button>
      </div>
    </section>

    <div class="catalog-heading">
      <div>
        <p>SHOP</p>
        <h2>{{ form.keyword ? `“${form.keyword}”的搜索结果` : '全部商品' }}</h2>
      </div>
      <span v-if="productsQuery.data.value">共 {{ productsQuery.data.value.count }} 件</span>
    </div>

    <section v-if="productsQuery.isPending.value" class="product-grid" aria-label="正在加载商品">
      <el-skeleton v-for="index in 8" :key="index" animated class="skeleton-card">
        <template #template>
          <el-skeleton-item variant="image" class="skeleton-image" />
          <div class="skeleton-body">
            <el-skeleton-item variant="text" style="width: 36%" />
            <el-skeleton-item variant="h3" style="width: 78%" />
            <el-skeleton-item variant="text" style="width: 52%" />
          </div>
        </template>
      </el-skeleton>
    </section>

    <el-result
      v-else-if="productsQuery.isError.value"
      icon="error"
      title="商品暂时加载失败"
      :sub-title="errorMessage(productsQuery.error.value)"
    >
      <template #extra><el-button type="primary" @click="productsQuery.refetch()">重新加载</el-button></template>
    </el-result>

    <el-empty
      v-else-if="!productsQuery.data.value?.results.length"
      description="没有找到符合条件的商品"
    >
      <el-button type="primary" plain @click="resetFilters">查看全部商品</el-button>
    </el-empty>

    <section
      v-else
      v-loading="productsQuery.isFetching.value"
      class="product-grid"
      aria-live="polite"
    >
      <ProductCard v-for="product in productsQuery.data.value.results" :key="product.id" :product="product" />
    </section>

    <el-pagination
      v-if="(productsQuery.data.value?.count ?? 0) > pageSize"
      class="pagination"
      background
      layout="prev, pager, next"
      :current-page="page"
      :page-size="pageSize"
      :total="productsQuery.data.value?.count ?? 0"
      @current-change="changePage"
    />
  </div>
</template>

<style scoped>
.catalog-page {
  width: min(1180px, calc(100% - 36px));
  margin: 0 auto;
  padding: 32px 0 72px;
}

.hero {
  position: relative;
  min-height: 220px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  overflow: hidden;
  padding: 42px 54px;
  border-radius: 26px;
  color: #f9fcf9;
  background:
    radial-gradient(circle at 88% 24%, rgb(255 255 255 / 12%) 0 80px, transparent 81px),
    linear-gradient(120deg, #183e2a, #2f6544);
}

.hero::after {
  content: '';
  position: absolute;
  right: 18%;
  bottom: -85px;
  width: 210px;
  height: 210px;
  border: 1px solid rgb(255 255 255 / 18%);
  border-radius: 50%;
}

.eyebrow,
.catalog-heading p {
  margin: 0 0 10px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.16em;
  opacity: 0.72;
}

.hero h1 {
  margin: 0;
  font-size: clamp(32px, 5vw, 52px);
  line-height: 1.1;
  letter-spacing: -0.04em;
}

.hero > div > p:last-child {
  margin: 17px 0 0;
  color: rgb(255 255 255 / 72%);
}

.hero__stamp {
  position: relative;
  z-index: 1;
  width: 104px;
  height: 104px;
  display: grid;
  place-content: center;
  flex: 0 0 auto;
  border: 1px solid rgb(255 255 255 / 34%);
  border-radius: 50%;
  text-align: center;
  transform: rotate(8deg);
}

.hero__stamp strong,
.hero__stamp span {
  display: block;
}

.hero__stamp strong {
  font-size: 21px;
}

.hero__stamp span {
  margin-top: 3px;
  font-size: 11px;
  opacity: 0.65;
}

.filter-card {
  position: relative;
  z-index: 2;
  display: grid;
  grid-template-columns: minmax(190px, 1.6fr) minmax(130px, 0.8fr) minmax(210px, 1.2fr) minmax(155px, 0.9fr) auto auto;
  gap: 10px;
  align-items: center;
  margin: -22px 28px 48px;
  padding: 17px;
  border: 1px solid #e6ebe7;
  border-radius: 17px;
  background: rgb(255 255 255 / 96%);
  box-shadow: 0 14px 34px rgb(20 48 30 / 12%);
}

.price-range {
  display: flex;
  align-items: center;
  gap: 7px;
  color: #9ba49d;
}

.filter-card__error {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding-top: 5px;
  color: #b45d2d;
  font-size: 12px;
}

.catalog-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  margin-bottom: 20px;
}

.catalog-heading p {
  color: #327149;
}

.catalog-heading h2 {
  margin: 0;
  color: #1d2d21;
  font-size: 27px;
}

.catalog-heading > span {
  color: #7b877d;
  font-size: 13px;
}

.product-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 20px;
}

.skeleton-card {
  overflow: hidden;
  border: 1px solid #e9ecea;
  border-radius: 18px;
}

.skeleton-image {
  width: 100%;
  height: auto;
  aspect-ratio: 4 / 3;
}

.skeleton-body {
  display: grid;
  gap: 15px;
  padding: 18px;
}

.pagination {
  justify-content: center;
  margin-top: 40px;
}

:deep(.el-result),
:deep(.el-empty) {
  min-height: 360px;
}

@media (max-width: 1050px) {
  .filter-card {
    grid-template-columns: repeat(3, 1fr);
  }

  .product-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .catalog-page {
    width: min(100% - 24px, 1180px);
    padding-top: 18px;
  }

  .hero {
    min-height: 190px;
    padding: 32px 26px 50px;
  }

  .hero__stamp {
    display: none;
  }

  .filter-card {
    grid-template-columns: 1fr 1fr;
    margin: -28px 12px 38px;
  }

  .filter-card__keyword,
  .price-range {
    grid-column: 1 / -1;
  }

  .product-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }
}

@media (max-width: 480px) {
  .filter-card {
    grid-template-columns: 1fr;
  }

  .filter-card__keyword,
  .price-range {
    grid-column: auto;
  }

  .catalog-heading h2 {
    font-size: 23px;
  }
}
</style>
