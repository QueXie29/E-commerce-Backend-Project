import type { OrderDetail, OrderFilters, OrderSummary, Paginated } from './contracts'
import { apiClient } from './client'

const CHECKOUT_KEY = 'mini-mall:checkout-intent'

interface CheckoutIntent {
  key: string
  remark: string
  cartSignature: string
}

function readIntent(): CheckoutIntent | null {
  try {
    const value = sessionStorage.getItem(CHECKOUT_KEY)
    return value ? (JSON.parse(value) as CheckoutIntent) : null
  } catch {
    return null
  }
}

function intentFor(remark: string, cartSignature: string): CheckoutIntent {
  const existing = readIntent()
  if (existing?.remark === remark && existing.cartSignature === cartSignature) return existing
  const intent = { key: crypto.randomUUID(), remark, cartSignature }
  sessionStorage.setItem(CHECKOUT_KEY, JSON.stringify(intent))
  return intent
}

export function abandonCheckoutIntent(): void {
  sessionStorage.removeItem(CHECKOUT_KEY)
}

export async function createOrder(remark: string, cartSignature: string): Promise<OrderDetail> {
  const intent = intentFor(remark, cartSignature)
  const order = await apiClient.request<OrderDetail>('orders/', {
    method: 'POST',
    headers: { 'Idempotency-Key': intent.key },
    body: { remark, cart_signature: cartSignature },
  })
  abandonCheckoutIntent()
  return order
}

export function listOrders(filters: OrderFilters): Promise<Paginated<OrderSummary>> {
  return apiClient.request('orders/', { query: { ...filters } })
}

export function getOrder(id: number): Promise<OrderDetail> {
  return apiClient.request(`orders/${id}/`)
}

export function payOrder(id: number): Promise<OrderDetail> {
  return apiClient.request(`orders/${id}/pay/`, { method: 'POST', body: {} })
}

export function cancelOrder(id: number): Promise<OrderDetail> {
  return apiClient.request(`orders/${id}/cancel/`, { method: 'POST', body: {} })
}
