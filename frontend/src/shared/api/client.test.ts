import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createApiClient } from './client'
import { ApiError } from './errors'
import { setAccessToken } from './session'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('apiClient interface', () => {
  beforeEach(() => {
    setAccessToken(null)
    document.cookie = 'csrftoken=test-csrf; path=/'
  })

  it('unwraps the common response envelope', async () => {
    const fetchAdapter = vi.fn<typeof fetch>().mockResolvedValue(
      jsonResponse({ code: 0, message: 'success', data: { id: 7 } }),
    )
    const client = createApiClient(fetchAdapter)

    await expect(client.request<{ id: number }>('products/7/', { auth: false })).resolves.toEqual({ id: 7 })
  })

  it('preserves business codes and field errors', async () => {
    const fetchAdapter = vi.fn<typeof fetch>().mockResolvedValue(
      jsonResponse(
        { code: 40000, message: '请求参数错误', data: { username: ['用户名已存在'] } },
        400,
      ),
    )
    const client = createApiClient(fetchAdapter)

    const error = await client.request('auth/register/', { method: 'POST', auth: false }).catch((reason: unknown) => reason)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).code).toBe(40000)
    expect((error as ApiError).fieldErrors.username).toEqual(['用户名已存在'])
  })

  it('coalesces concurrent refreshes and retries each protected request once', async () => {
    setAccessToken('expired-token')
    let refreshCalls = 0
    const attempts = new Map<string, number>()
    const fetchAdapter = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input)
      if (path.endsWith('/api/auth/browser/refresh/')) {
        refreshCalls += 1
        await Promise.resolve()
        return jsonResponse({ code: 0, message: 'success', data: { access: 'fresh-token' } })
      }

      const count = (attempts.get(path) ?? 0) + 1
      attempts.set(path, count)
      if (count === 1) return jsonResponse({ code: 40100, message: '未认证', data: null }, 401)
      expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer fresh-token')
      return jsonResponse({ code: 0, message: 'success', data: path })
    })
    const client = createApiClient(fetchAdapter)

    const result = await Promise.all([client.request<string>('private/a/'), client.request<string>('private/b/')])

    expect(result).toEqual(['/api/private/a/', '/api/private/b/'])
    expect(refreshCalls).toBe(1)
    expect(attempts.get('/api/private/a/')).toBe(2)
    expect(attempts.get('/api/private/b/')).toBe(2)
  })
})
