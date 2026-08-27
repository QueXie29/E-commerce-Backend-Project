import type { Cart, CartItem } from './contracts'
import { apiClient } from './client'

export function getCart(): Promise<Cart> {
  return apiClient.request('cart/')
}

export function addCartItem(productId: number, quantity: number): Promise<CartItem> {
  return apiClient.request('cart/items/', {
    method: 'POST',
    body: { product_id: productId, quantity },
  })
}

export function updateCartItem(id: number, input: { quantity?: number; selected?: boolean }): Promise<CartItem> {
  return apiClient.request(`cart/items/${id}/`, { method: 'PATCH', body: input })
}

export function removeCartItem(id: number): Promise<null> {
  return apiClient.request(`cart/items/${id}/`, { method: 'DELETE' })
}

export function clearCart(): Promise<null> {
  return apiClient.request('cart/clear/', { method: 'DELETE' })
}
