<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, reactive, ref, watch } from 'vue'

import type {
  Category,
  ProductDetail,
  ProductFilters,
  ProductSummary,
  ProductWrite,
} from '@/shared/api/contracts'
import { ApiError, errorMessage } from '@/shared/api/errors'
import {
  createProduct,
  deactivateProduct,
  getManagedProduct,
  listManagedCategories,
  listManagedProducts,
  updateProduct,
} from '@/shared/api/management'

interface SaveProductVariables {
  id: number | null
  input: ProductWrite | Partial<ProductWrite>
}

const PAGE_SIZE = 10
const queryClient = useQueryClient()
const page = ref(1)
const keywordDraft = ref('')
const keyword = ref('')
const categoryFilter = ref<number | undefined>()
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const loadingProductId = ref<number | null>(null)
const originalProduct = ref<ProductWrite | null>(null)
const formError = ref('')
const previewFailed = ref(false)
const form = reactive<ProductWrite>({
  category: 0,
  name: '',
  slug: '',
  description: '',
  price: '',
  stock: 0,
  status: 'active',
  image_url: '',
})

const filters = computed<ProductFilters>(() => ({
  page: page.value,
  page_size: PAGE_SIZE,
  keyword: keyword.value || undefined,
  category: categoryFilter.value,
  ordering: '-created_at',
}))

const productsQuery = useQuery({
  queryKey: computed(() => ['management', 'products', filters.value]),
  queryFn: () => listManagedProducts(filters.value),
})

async function loadAllCategories(): Promise<Category[]> {
  const categories: Category[] = []
  let currentPage = 1

  while (currentPage <= 100) {
    const result = await listManagedCategories(currentPage)
    categories.push(...result.results)
    if (!result.next) break
    currentPage += 1
  }
  return categories
}

const categoriesQuery = useQuery({
  queryKey: ['management', 'product-form-categories'],
  queryFn: loadAllCategories,
})

const saveMutation = useMutation({
  mutationFn: ({ id, input }: SaveProductVariables) =>
    id === null ? createProduct(input as ProductWrite) : updateProduct(id, input),
  onSuccess: async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['management'] }),
      queryClient.invalidateQueries({ queryKey: ['products'] }),
    ])
  },
})

const statusMutation = useMutation({
  mutationFn: ({ product, activate }: { product: ProductSummary; activate: boolean }) =>
    activate ? updateProduct(product.id, { status: 'active' }) : deactivateProduct(product.id),
  onSuccess: async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['management'] }),
      queryClient.invalidateQueries({ queryKey: ['products'] }),
    ])
  },
})

const dialogTitle = computed(() => (editingId.value === null ? '新增商品' : '编辑商品'))
const availableCategories = computed(() => categoriesQuery.data.value ?? [])

watch(categoryFilter, () => {
  page.value = 1
})

watch(
  () => form.image_url,
  () => {
    previewFailed.value = false
  },
)

function emptyProduct(): ProductWrite {
  return {
    category: availableCategories.value.find((category) => category.is_active)?.id ?? 0,
    name: '',
    slug: '',
    description: '',
    price: '',
    stock: 0,
    status: 'active',
    image_url: '',
  }
}

function assignForm(value: ProductWrite): void {
  form.category = value.category
  form.name = value.name
  form.slug = value.slug
  form.description = value.description
  form.price = value.price
  form.stock = value.stock
  form.status = value.status
  form.image_url = value.image_url
}

function resetForm(): void {
  editingId.value = null
  originalProduct.value = null
  formError.value = ''
  previewFailed.value = false
  saveMutation.reset()
  assignForm(emptyProduct())
}

function openCreate(): void {
  resetForm()
  dialogVisible.value = true
}

function detailToWrite(product: ProductDetail): ProductWrite {
  return {
    category: product.category.id,
    name: product.name,
    slug: product.slug,
    description: product.description,
    price: product.price,
    stock: product.stock,
    status: product.status,
    image_url: product.image_url,
  }
}

async function openEdit(product: ProductSummary): Promise<void> {
  loadingProductId.value = product.id
  try {
    const detail = await getManagedProduct(product.id)
    const writeModel = detailToWrite(detail)
    resetForm()
    editingId.value = detail.id
    originalProduct.value = { ...writeModel }
    assignForm(writeModel)
    dialogVisible.value = true
  } catch (error) {
    ElMessage.error(errorMessage(error, '加载商品详情失败'))
  } finally {
    loadingProductId.value = null
  }
}

function validateForm(): string | null {
  if (!form.category) return '请选择商品分类'
  if (!form.name.trim()) return '请输入商品名称'
  if (!form.slug.trim()) return '请输入商品标识'
  if (!/^[-a-zA-Z0-9_]+$/.test(form.slug.trim())) {
    return '商品标识只能包含字母、数字、短横线和下划线'
  }
  if (!form.description.trim()) return '请输入商品描述'
  if (!/^\d{1,8}(\.\d{1,2})?$/.test(form.price.trim()) || Number(form.price) <= 0) {
    return '价格必须大于 0，最多 8 位整数和 2 位小数'
  }
  if (!Number.isInteger(form.stock) || form.stock < 0) return '库存必须是大于或等于 0 的整数'
  if (form.image_url.trim()) {
    try {
      const url = new URL(form.image_url.trim())
      if (url.protocol !== 'http:' && url.protocol !== 'https:') return '图片地址必须使用 http 或 https'
    } catch {
      return '请输入有效的图片地址'
    }
  }
  return null
}

function apiFieldError(field: keyof ProductWrite): string {
  const error = saveMutation.error.value
  if (!(error instanceof ApiError)) return ''
  return error.fieldErrors[field]?.join('；') ?? ''
}

function normalizedInput(): ProductWrite {
  return {
    category: form.category,
    name: form.name.trim(),
    slug: form.slug.trim(),
    description: form.description.trim(),
    price: form.price.trim(),
    stock: form.stock,
    status: form.status,
    image_url: form.image_url.trim(),
  }
}

function changedInput(current: ProductWrite, original: ProductWrite): Partial<ProductWrite> {
  const changed: Partial<ProductWrite> = {}
  if (current.category !== original.category) changed.category = current.category
  if (current.name !== original.name) changed.name = current.name
  if (current.slug !== original.slug) changed.slug = current.slug
  if (current.description !== original.description) changed.description = current.description
  if (current.price !== original.price) changed.price = current.price
  if (current.stock !== original.stock) changed.stock = current.stock
  if (current.status !== original.status) changed.status = current.status
  if (current.image_url !== original.image_url) changed.image_url = current.image_url
  return changed
}

async function submitForm(): Promise<void> {
  formError.value = ''
  const validationError = validateForm()
  if (validationError) {
    formError.value = validationError
    return
  }

  const current = normalizedInput()
  const input =
    editingId.value !== null && originalProduct.value
      ? changedInput(current, originalProduct.value)
      : current

  try {
    await saveMutation.mutateAsync({ id: editingId.value, input })
    dialogVisible.value = false
    ElMessage.success(editingId.value === null ? '商品已新增' : '商品已更新')
  } catch (error) {
    formError.value = errorMessage(error, '保存商品失败，请稍后重试')
  }
}

async function changeStatus(product: ProductSummary): Promise<void> {
  const activate = product.status !== 'active'
  if (!activate) {
    try {
      await ElMessageBox.confirm(
        `下架“${product.name}”后，顾客将无法在商城中购买该商品。确认继续吗？`,
        '确认下架商品',
        {
          type: 'warning',
          confirmButtonText: '确认下架',
          cancelButtonText: '取消',
        },
      )
    } catch {
      return
    }
  }

  try {
    await statusMutation.mutateAsync({ product, activate })
    ElMessage.success(activate ? '商品已上架' : '商品已下架')
  } catch (error) {
    ElMessage.error(errorMessage(error, activate ? '上架商品失败' : '下架商品失败'))
  }
}

function search(): void {
  keyword.value = keywordDraft.value.trim()
  page.value = 1
}

function resetFilters(): void {
  keywordDraft.value = ''
  keyword.value = ''
  categoryFilter.value = undefined
  page.value = 1
}

function formatMoney(value: string): string {
  const amount = Number(value)
  return Number.isFinite(amount)
    ? amount.toLocaleString('zh-CN', { style: 'currency', currency: 'CNY' })
    : value
}
</script>

<template>
  <div class="management-page">
    <header class="page-header">
      <div>
        <p class="page-kicker">INVENTORY</p>
        <h2>商品管理</h2>
        <p>维护商品资料、价格、库存与上下架状态。下架不会永久删除商品。</p>
      </div>
      <el-button type="primary" :disabled="categoriesQuery.isError.value" @click="openCreate">新增商品</el-button>
    </header>

    <el-card shadow="never" class="filter-card">
      <el-alert
        v-if="categoriesQuery.isError.value"
        class="category-error"
        type="error"
        show-icon
        :closable="false"
        :title="`分类加载失败：${errorMessage(categoriesQuery.error.value)}`"
      >
        <template #default>
          <el-button link type="primary" @click="categoriesQuery.refetch()">重新加载分类</el-button>
        </template>
      </el-alert>
      <el-form class="filter-form" inline @submit.prevent="search">
        <el-form-item label="关键词">
          <el-input
            v-model="keywordDraft"
            clearable
            placeholder="搜索名称或描述"
            @keyup.enter="search"
          />
        </el-form-item>
        <el-form-item label="分类">
          <el-select
            v-model="categoryFilter"
            clearable
            filterable
            placeholder="全部分类"
            :loading="categoriesQuery.isPending.value"
          >
            <el-option
              v-for="category in availableCategories"
              :key="category.id"
              :label="category.is_active ? category.name : `${category.name}（已停用）`"
              :value="category.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">搜索</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="data-card">
      <el-skeleton v-if="productsQuery.isPending.value" :rows="7" animated />
      <el-result
        v-else-if="productsQuery.isError.value"
        icon="error"
        title="商品加载失败"
        :sub-title="errorMessage(productsQuery.error.value, '请稍后重试')"
      >
        <template #extra>
          <el-button type="primary" @click="productsQuery.refetch()">重新加载</el-button>
        </template>
      </el-result>

      <template v-else>
        <el-table
          :data="productsQuery.data.value?.results ?? []"
          empty-text="没有符合当前条件的商品"
          row-key="id"
        >
          <el-table-column label="商品" min-width="260">
            <template #default="scope">
              <div class="product-cell">
                <el-image
                  v-if="scope.row.image_url"
                  :src="scope.row.image_url"
                  fit="cover"
                  class="product-cell__image"
                >
                  <template #error><span class="image-fallback">无图</span></template>
                </el-image>
                <span v-else class="product-cell__image image-fallback">无图</span>
                <div>
                  <strong>{{ scope.row.name }}</strong>
                  <small>{{ scope.row.slug }}</small>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="分类" min-width="130">
            <template #default="scope">{{ scope.row.category.name }}</template>
          </el-table-column>
          <el-table-column label="售价" width="130">
            <template #default="scope">{{ formatMoney(scope.row.price) }}</template>
          </el-table-column>
          <el-table-column prop="stock" label="库存" width="90" />
          <el-table-column prop="sales_count" label="销量" width="90" />
          <el-table-column label="状态" width="100">
            <template #default="scope">
              <el-tag :type="scope.row.status === 'active' ? 'success' : 'info'">
                {{ scope.row.status === 'active' ? '已上架' : '已下架' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="190" fixed="right">
            <template #default="scope">
              <el-button
                link
                type="primary"
                :loading="loadingProductId === scope.row.id"
                @click="openEdit(scope.row)"
              >
                编辑
              </el-button>
              <el-button
                link
                :type="scope.row.status === 'active' ? 'danger' : 'success'"
                :loading="statusMutation.isPending.value"
                @click="changeStatus(scope.row)"
              >
                {{ scope.row.status === 'active' ? '下架' : '上架' }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="(productsQuery.data.value?.count ?? 0) > PAGE_SIZE" class="pagination-wrap">
          <el-pagination
            v-model:current-page="page"
            background
            layout="prev, pager, next, total"
            :page-size="PAGE_SIZE"
            :total="productsQuery.data.value?.count ?? 0"
          />
        </div>
      </template>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="min(760px, 94vw)"
      :close-on-click-modal="!saveMutation.isPending.value"
      :close-on-press-escape="!saveMutation.isPending.value"
      :show-close="!saveMutation.isPending.value"
      @closed="resetForm"
    >
      <el-alert v-if="formError" :title="formError" type="error" :closable="false" show-icon />
      <el-form label-position="top" class="product-form" @submit.prevent="submitForm">
        <div class="form-grid">
          <el-form-item label="商品名称" required :error="apiFieldError('name')">
            <el-input v-model="form.name" maxlength="200" show-word-limit />
          </el-form-item>
          <el-form-item label="商品标识" required :error="apiFieldError('slug')">
            <el-input v-model="form.slug" maxlength="220" placeholder="例如：wireless-headphones" />
          </el-form-item>
          <el-form-item label="商品分类" required :error="apiFieldError('category')">
            <el-select
              v-model="form.category"
              filterable
              placeholder="请选择分类"
              :loading="categoriesQuery.isPending.value"
            >
              <el-option
                v-for="category in availableCategories"
                :key="category.id"
                :label="category.is_active ? category.name : `${category.name}（已停用）`"
                :value="category.id"
                :disabled="!category.is_active && category.id !== form.category"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="商品状态" required :error="apiFieldError('status')">
            <el-radio-group v-model="form.status">
              <el-radio value="active">上架</el-radio>
              <el-radio value="inactive">下架</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="价格（元）" required :error="apiFieldError('price')">
            <el-input v-model="form.price" inputmode="decimal" placeholder="0.00" />
          </el-form-item>
          <el-form-item label="库存" required :error="apiFieldError('stock')">
            <el-input-number v-model="form.stock" :min="0" :step="1" step-strictly controls-position="right" />
          </el-form-item>
        </div>

        <el-form-item label="商品描述" required :error="apiFieldError('description')">
          <el-input v-model="form.description" type="textarea" :rows="5" maxlength="5000" show-word-limit />
        </el-form-item>

        <el-form-item label="图片 URL" :error="apiFieldError('image_url')">
          <el-input v-model="form.image_url" placeholder="https://example.com/product.jpg" />
          <div class="field-tip">当前后端接收图片 URL，请填写可公开访问的 http/https 地址。</div>
        </el-form-item>

        <div v-if="form.image_url" class="image-preview">
          <span>图片预览</span>
          <img
            v-if="!previewFailed"
            :src="form.image_url"
            alt="商品图片预览"
            @error="previewFailed = true"
          />
          <div v-else class="image-preview__error">图片无法加载，请检查地址是否有效。</div>
        </div>
      </el-form>
      <template #footer>
        <el-button :disabled="saveMutation.isPending.value" @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saveMutation.isPending.value" @click="submitForm">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.management-page {
  display: grid;
  gap: 20px;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
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

.filter-form :deep(.el-input) {
  width: 240px;
}

.filter-form :deep(.el-select) {
  width: 210px;
}

.product-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.product-cell strong,
.product-cell small {
  display: block;
}

.product-cell small {
  margin-top: 4px;
  color: #94a3b8;
}

.product-cell__image {
  flex: 0 0 auto;
  width: 46px;
  height: 46px;
  border-radius: 8px;
  background: #f1f5f9;
}

.image-fallback {
  display: grid;
  place-items: center;
  color: #94a3b8;
  font-size: 11px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  padding-top: 22px;
}

.product-form {
  margin-top: 18px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 20px;
}

.form-grid :deep(.el-select),
.form-grid :deep(.el-input-number) {
  width: 100%;
}

.field-tip {
  padding-top: 5px;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.5;
}

.image-preview {
  display: grid;
  gap: 8px;
  color: #64748b;
  font-size: 13px;
}

.image-preview img {
  width: 180px;
  height: 130px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  object-fit: cover;
}

.image-preview__error {
  padding: 18px;
  border: 1px dashed #fca5a5;
  border-radius: 10px;
  background: #fef2f2;
  color: #b91c1c;
}

@media (max-width: 680px) {
  .page-header {
    align-items: stretch;
    flex-direction: column;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .filter-form {
    display: grid;
  }

  .filter-form :deep(.el-form-item),
  .filter-form :deep(.el-input),
  .filter-form :deep(.el-select) {
    width: 100%;
  }

  .filter-form :deep(.el-form-item) {
    margin-bottom: 14px;
  }
}
</style>
