import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { OrderDetail } from './contracts'
import { apiClient } from './client'
import { abandonCheckoutIntent, createOrder } from './orders'

const order = {
  id: 1,
  order_no: 'EC001',
  user_id: 1,
  total_amount: '99.00',
  status: 'pending',
  remark: '放门口',
  items: [],
  created_at: '2026-08-13T00:00:00Z',
  expires_at: '2026-08-13T01:00:00Z',
  paid_at: null,
  cancelled_at: null,
  updated_at: '2026-08-13T00:00:00Z',
} satisfies OrderDetail

describe('orderSubmission module', () => {
  beforeEach(() => {
    abandonCheckoutIntent()
    vi.restoreAllMocks()
  })

  it('reuses the same idempotency key when the same checkout intent is retried', async () => {
    const request = vi
      .spyOn(apiClient, 'request')
      .mockRejectedValueOnce(new TypeError('network unavailable'))
      .mockResolvedValueOnce(order)

    await expect(createOrder('放门口', '1:10:2')).rejects.toThrow('network unavailable')
    await expect(createOrder('放门口', '1:10:2')).resolves.toEqual(order)

    const firstHeaders = request.mock.calls[0]?.[1]?.headers as Record<string, string>
    const secondHeaders = request.mock.calls[1]?.[1]?.headers as Record<string, string>
    expect(firstHeaders['Idempotency-Key']).toBeTruthy()
    expect(secondHeaders['Idempotency-Key']).toBe(firstHeaders['Idempotency-Key'])
  })

  it('creates a new key after the user changes the order remark', async () => {
    const request = vi.spyOn(apiClient, 'request').mockRejectedValue(new TypeError('offline'))

    await createOrder('备注 A', '1:10:2').catch(() => undefined)
    await createOrder('备注 B', '1:10:2').catch(() => undefined)

    const firstHeaders = request.mock.calls[0]?.[1]?.headers as Record<string, string>
    const secondHeaders = request.mock.calls[1]?.[1]?.headers as Record<string, string>
    expect(secondHeaders['Idempotency-Key']).not.toBe(firstHeaders['Idempotency-Key'])
  })

  it('creates a new key when the selected cart changes', async () => {
    const request = vi.spyOn(apiClient, 'request').mockRejectedValue(new TypeError('offline'))

    await createOrder('相同备注', '1:10:2').catch(() => undefined)
    await createOrder('相同备注', '1:10:2|2:11:1').catch(() => undefined)

    const firstHeaders = request.mock.calls[0]?.[1]?.headers as Record<string, string>
    const secondHeaders = request.mock.calls[1]?.[1]?.headers as Record<string, string>
    expect(secondHeaders['Idempotency-Key']).not.toBe(firstHeaders['Idempotency-Key'])
  })
})
