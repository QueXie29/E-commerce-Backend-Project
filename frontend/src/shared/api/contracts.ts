export interface ApiEnvelope<T> {
  code: number
  message: string
  data: T
}

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface PageParams {
  page?: number
  page_size?: number
}

export type UserRole = 'user' | 'admin'

export interface User {
  id: number
  username: string
  email: string
  phone: string
  role: UserRole
  date_joined: string
}

export interface Category {
  id: number
  name: string
  slug: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export type ProductStatus = 'active' | 'inactive'

export interface ProductCategory {
  id: number
  name: string
  slug: string
}

export interface ProductSummary {
  id: number
  category: ProductCategory
  name: string
  slug: string
  price: string
  stock: number
  sales_count: number
  status: ProductStatus
  image_url: string
  created_at: string
}

export interface ProductDetail extends ProductSummary {
  description: string
  updated_at: string
}

export interface ProductWrite {
  category: number
  name: string
  slug: string
  description: string
  price: string
  stock: number
  status: ProductStatus
  image_url: string
}

export interface CartProduct {
  id: number
  name: string
  price: string
  stock: number
  status: ProductStatus
  image_url: string
}

export interface CartItem {
  id: number
  product: CartProduct
  quantity: number
  selected: boolean
  subtotal: string
  created_at: string
  updated_at: string
}

export interface Cart {
  items: CartItem[]
  total_amount: string
}

export type OrderStatus = 'pending' | 'paid' | 'cancelled'

export interface OrderSummary {
  id: number
  order_no: string
  total_amount: string
  status: OrderStatus
  remark: string
  created_at: string
  expires_at: string
  paid_at: string | null
  cancelled_at: string | null
}

export interface OrderItem {
  id: number
  product_id: number
  product_name: string
  product_price: string
  quantity: number
  subtotal: string
  created_at: string
}

export interface OrderDetail extends OrderSummary {
  user_id: number
  items: OrderItem[]
  updated_at: string
}

export interface LoginInput {
  username: string
  password: string
}

export interface RegisterInput extends LoginInput {
  password_confirm: string
  email?: string
  phone?: string
}

export interface AccessTokenResponse {
  access: string
}

export interface ProductFilters extends PageParams {
  category?: number
  keyword?: string
  min_price?: string
  max_price?: string
  ordering?: 'created_at' | '-created_at' | 'price' | '-price' | 'sales_count' | '-sales_count'
}

export interface OrderFilters extends PageParams {
  status?: OrderStatus
}
