<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, reactive, ref } from 'vue'

import type { Category } from '@/shared/api/contracts'
import { ApiError, errorMessage } from '@/shared/api/errors'
import {
  createCategory,
  deactivateCategory,
  listManagedCategories,
  updateCategory,
} from '@/shared/api/management'

interface CategoryForm {
  name: string
  slug: string
  is_active: boolean
}

const queryClient = useQueryClient()
const page = ref(1)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const formError = ref('')
const form = reactive<CategoryForm>({
  name: '',
  slug: '',
  is_active: true,
})

const categoriesQuery = useQuery({
  queryKey: computed(() => ['management', 'categories', page.value]),
  queryFn: () => listManagedCategories(page.value),
})

const saveMutation = useMutation({
  mutationFn: ({ id, input }: { id: number | null; input: CategoryForm }) =>
    id === null ? createCategory(input) : updateCategory(id, input),
  onSuccess: async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['management'] }),
      queryClient.invalidateQueries({ queryKey: ['categories'] }),
      queryClient.invalidateQueries({ queryKey: ['products'] }),
      queryClient.invalidateQueries({ queryKey: ['product-form-categories'] }),
    ])
  },
})

const statusMutation = useMutation({
  mutationFn: ({ category, activate }: { category: Category; activate: boolean }) =>
    activate ? updateCategory(category.id, { is_active: true }) : deactivateCategory(category.id),
  onSuccess: async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['management'] }),
      queryClient.invalidateQueries({ queryKey: ['categories'] }),
      queryClient.invalidateQueries({ queryKey: ['products'] }),
      queryClient.invalidateQueries({ queryKey: ['product-form-categories'] }),
    ])
  },
})

const dialogTitle = computed(() => (editingId.value === null ? '新增分类' : '编辑分类'))

function resetForm(): void {
  editingId.value = null
  form.name = ''
  form.slug = ''
  form.is_active = true
  formError.value = ''
  saveMutation.reset()
}

function openCreate(): void {
  resetForm()
  dialogVisible.value = true
}

function openEdit(category: Category): void {
  resetForm()
  editingId.value = category.id
  form.name = category.name
  form.slug = category.slug
  form.is_active = category.is_active
  dialogVisible.value = true
}

function validateForm(): string | null {
  if (!form.name.trim()) return '请输入分类名称'
  if (!form.slug.trim()) return '请输入分类标识'
  if (!/^[-a-zA-Z0-9_]+$/.test(form.slug.trim())) {
    return '分类标识只能包含字母、数字、短横线和下划线'
  }
  return null
}

function apiFieldError(field: keyof CategoryForm): string {
  const error = saveMutation.error.value
  if (!(error instanceof ApiError)) return ''
  return error.fieldErrors[field]?.join('；') ?? ''
}

async function submitForm(): Promise<void> {
  formError.value = ''
  const validationError = validateForm()
  if (validationError) {
    formError.value = validationError
    return
  }

  try {
    await saveMutation.mutateAsync({
      id: editingId.value,
      input: {
        name: form.name.trim(),
        slug: form.slug.trim(),
        is_active: form.is_active,
      },
    })
    dialogVisible.value = false
    ElMessage.success(editingId.value === null ? '分类已新增' : '分类已更新')
  } catch (error) {
    formError.value = errorMessage(error, '保存分类失败，请稍后重试')
  }
}

async function changeStatus(category: Category): Promise<void> {
  const activate = !category.is_active
  if (!activate) {
    try {
      await ElMessageBox.confirm(
        `停用“${category.name}”后，该分类将不会出现在商城前台。确认继续吗？`,
        '确认停用分类',
        {
          type: 'warning',
          confirmButtonText: '确认停用',
          cancelButtonText: '取消',
        },
      )
    } catch {
      return
    }
  }

  try {
    await statusMutation.mutateAsync({ category, activate })
    ElMessage.success(activate ? '分类已启用' : '分类已停用')
  } catch (error) {
    ElMessage.error(errorMessage(error, activate ? '启用分类失败' : '停用分类失败'))
  }
}

function formatDate(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}
</script>

<template>
  <div class="management-page">
    <header class="page-header">
      <div>
        <p class="page-kicker">CATALOG</p>
        <h2>分类管理</h2>
        <p>维护商品分类。停用分类不会永久删除已有数据。</p>
      </div>
      <el-button type="primary" @click="openCreate">新增分类</el-button>
    </header>

    <el-card shadow="never" class="data-card">
      <el-skeleton v-if="categoriesQuery.isPending.value" :rows="6" animated />

      <el-result
        v-else-if="categoriesQuery.isError.value"
        icon="error"
        title="分类加载失败"
        :sub-title="errorMessage(categoriesQuery.error.value, '请稍后重试')"
      >
        <template #extra>
          <el-button type="primary" @click="categoriesQuery.refetch()">重新加载</el-button>
        </template>
      </el-result>

      <template v-else>
        <el-table
          :data="categoriesQuery.data.value?.results ?? []"
          empty-text="暂无分类，点击右上角新增"
          row-key="id"
        >
          <el-table-column prop="name" label="分类名称" min-width="160" />
          <el-table-column prop="slug" label="分类标识" min-width="160" />
          <el-table-column label="状态" width="110">
            <template #default="scope">
              <el-tag :type="scope.row.is_active ? 'success' : 'info'" effect="light">
                {{ scope.row.is_active ? '已启用' : '已停用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="更新时间" min-width="180">
            <template #default="scope">{{ formatDate(scope.row.updated_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="190" fixed="right">
            <template #default="scope">
              <el-button link type="primary" @click="openEdit(scope.row)">编辑</el-button>
              <el-button
                link
                :type="scope.row.is_active ? 'danger' : 'success'"
                :loading="statusMutation.isPending.value"
                @click="changeStatus(scope.row)"
              >
                {{ scope.row.is_active ? '停用' : '启用' }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="(categoriesQuery.data.value?.count ?? 0) > 20" class="pagination-wrap">
          <el-pagination
            v-model:current-page="page"
            background
            layout="prev, pager, next, total"
            :page-size="20"
            :total="categoriesQuery.data.value?.count ?? 0"
          />
        </div>
      </template>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="min(520px, 92vw)"
      :close-on-click-modal="!saveMutation.isPending.value"
      :close-on-press-escape="!saveMutation.isPending.value"
      :show-close="!saveMutation.isPending.value"
      @closed="resetForm"
    >
      <el-alert v-if="formError" :title="formError" type="error" :closable="false" show-icon />
      <el-form label-position="top" class="category-form" @submit.prevent="submitForm">
        <el-form-item label="分类名称" required :error="apiFieldError('name')">
          <el-input v-model="form.name" maxlength="100" show-word-limit placeholder="例如：数码家电" />
        </el-form-item>
        <el-form-item label="分类标识" required :error="apiFieldError('slug')">
          <el-input v-model="form.slug" maxlength="120" placeholder="例如：digital-products" />
          <div class="field-tip">用于生成稳定标识，建议使用小写字母和短横线。</div>
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" />
        </el-form-item>
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
  gap: 22px;
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

.data-card {
  border-radius: 16px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  padding-top: 22px;
}

.category-form {
  margin-top: 18px;
}

.field-tip {
  padding-top: 5px;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.5;
}

@media (max-width: 560px) {
  .page-header {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
