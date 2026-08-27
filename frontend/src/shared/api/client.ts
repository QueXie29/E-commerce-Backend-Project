import type { AccessTokenResponse, ApiEnvelope } from './contracts'
import { ApiError } from './errors'
import { getAccessToken, setAccessToken } from './session'

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
  auth?: boolean
  csrf?: boolean
  retryAuth?: boolean
  query?: Record<string, string | number | boolean | null | undefined>
}

type FetchAdapter = typeof fetch

function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null
  const prefix = `${encodeURIComponent(name)}=`
  const entry = document.cookie.split('; ').find((cookie) => cookie.startsWith(prefix))
  return entry ? decodeURIComponent(entry.slice(prefix.length)) : null
}

function buildUrl(path: string, query?: RequestOptions['query']): string {
  const url = new URL(path.startsWith('/api/') ? path : `/api/${path.replace(/^\//, '')}`, window.location.origin)
  Object.entries(query ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, String(value))
  })
  return `${url.pathname}${url.search}`
}

export function createApiClient(fetchAdapter: FetchAdapter = fetch) {
  let refreshPromise: Promise<string> | null = null
  let csrfPromise: Promise<void> | null = null

  async function parseResponse<T>(response: Response): Promise<T> {
    const contentType = response.headers.get('content-type') ?? ''
    if (!contentType.includes('application/json')) {
      throw new ApiError(response.ok ? '服务器返回了无法识别的数据' : `请求失败（${response.status}）`, {
        status: response.status,
      })
    }

    const envelope = (await response.json()) as Partial<ApiEnvelope<T>>
    if (!response.ok || envelope.code !== 0) {
      throw new ApiError(envelope.message || `请求失败（${response.status}）`, {
        status: response.status,
        code: envelope.code,
        data: envelope.data,
      })
    }
    return envelope.data as T
  }

  async function ensureCsrf(): Promise<void> {
    if (getCookie('csrftoken')) return
    csrfPromise ??= fetchAdapter('/api/auth/browser/csrf/', {
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
    })
      .then((response) => parseResponse<unknown>(response))
      .then(() => undefined)
      .finally(() => {
        csrfPromise = null
      })
    return csrfPromise
  }

  async function refreshAccessToken(): Promise<string> {
    refreshPromise ??= (async () => {
      await ensureCsrf()
      const csrfToken = getCookie('csrftoken')
      const response = await fetchAdapter('/api/auth/browser/refresh/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {}),
        },
        body: '{}',
      })
      const result = await parseResponse<AccessTokenResponse>(response)
      setAccessToken(result.access)
      return result.access
    })()
      .catch((error) => {
        setAccessToken(null)
        throw error
      })
      .finally(() => {
        refreshPromise = null
      })
    return refreshPromise
  }

  async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const { auth = true, csrf = false, retryAuth = true, query, body, headers: inputHeaders, ...init } = options
    if (csrf) await ensureCsrf()

    const headers = new Headers(inputHeaders)
    headers.set('Accept', 'application/json')
    const token = getAccessToken()
    if (auth && token) headers.set('Authorization', `Bearer ${token}`)
    if (csrf) {
      const csrfToken = getCookie('csrftoken')
      if (csrfToken) headers.set('X-CSRFToken', csrfToken)
    }

    let requestBody: BodyInit | undefined
    if (body !== undefined) {
      if (body instanceof FormData || typeof body === 'string') {
        requestBody = body
      } else {
        headers.set('Content-Type', 'application/json')
        requestBody = JSON.stringify(body)
      }
    }

    const response = await fetchAdapter(buildUrl(path, query), {
      ...init,
      headers,
      body: requestBody,
      credentials: 'same-origin',
    })

    if (response.status === 401 && auth && retryAuth) {
      await refreshAccessToken()
      return request<T>(path, { ...options, retryAuth: false })
    }
    return parseResponse<T>(response)
  }

  return { request, ensureCsrf, refreshAccessToken }
}

export const apiClient = createApiClient()
