import type { Category, Paginated, ProductDetail, ProductFilters, ProductSummary } from './contracts'
import { apiClient } from './client'

export function listCategories(): Promise<Paginated<Category>> {
  return apiClient.request('categories/', { auth: false, query: { page_size: 100 } })
}

export function listProducts(filters: ProductFilters): Promise<Paginated<ProductSummary>> {
  return apiClient.request('products/', { auth: false, query: { ...filters } })
}

export function getProduct(id: number): Promise<ProductDetail> {
  return apiClient.request(`products/${id}/`, { auth: false })
}
