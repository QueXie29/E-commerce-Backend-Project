import type {
  Category,
  OrderFilters,
  OrderSummary,
  Paginated,
  ProductDetail,
  ProductFilters,
  ProductSummary,
  ProductWrite,
} from './contracts'
import { apiClient } from './client'

export function listManagedCategories(page = 1): Promise<Paginated<Category>> {
  return apiClient.request('admin/categories/', { query: { page, page_size: 20 } })
}

export function createCategory(input: Pick<Category, 'name' | 'slug' | 'is_active'>): Promise<Category> {
  return apiClient.request('admin/categories/', { method: 'POST', body: input })
}

export function updateCategory(id: number, input: Partial<Pick<Category, 'name' | 'slug' | 'is_active'>>): Promise<Category> {
  return apiClient.request(`admin/categories/${id}/`, { method: 'PATCH', body: input })
}

export function deactivateCategory(id: number): Promise<null> {
  return apiClient.request(`admin/categories/${id}/`, { method: 'DELETE' })
}

export function listManagedProducts(filters: ProductFilters): Promise<Paginated<ProductSummary>> {
  return apiClient.request('admin/products/', { query: { ...filters, page_size: filters.page_size ?? 20 } })
}

export function getManagedProduct(id: number): Promise<ProductDetail> {
  return apiClient.request(`admin/products/${id}/`)
}

export function createProduct(input: ProductWrite): Promise<ProductDetail> {
  return apiClient.request('admin/products/', { method: 'POST', body: input })
}

export function updateProduct(id: number, input: Partial<ProductWrite>): Promise<ProductDetail> {
  return apiClient.request(`admin/products/${id}/`, { method: 'PATCH', body: input })
}

export function deactivateProduct(id: number): Promise<null> {
  return apiClient.request(`admin/products/${id}/`, { method: 'DELETE' })
}

export function listManagedOrders(filters: OrderFilters): Promise<Paginated<OrderSummary>> {
  return apiClient.request('orders/', { query: { ...filters, page_size: filters.page_size ?? 20 } })
}
