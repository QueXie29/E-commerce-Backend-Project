import type { AccessTokenResponse, LoginInput, RegisterInput, User } from './contracts'
import { apiClient } from './client'
import { setAccessToken } from './session'

export async function login(input: LoginInput): Promise<User> {
  const result = await apiClient.request<AccessTokenResponse>('auth/browser/login/', {
    method: 'POST',
    auth: false,
    csrf: true,
    body: input,
  })
  setAccessToken(result.access)
  return getCurrentUser()
}

export async function register(input: RegisterInput): Promise<User> {
  return apiClient.request<User>('auth/register/', { method: 'POST', auth: false, body: input })
}

export async function getCurrentUser(): Promise<User> {
  return apiClient.request<User>('auth/me/')
}

export async function restoreSession(): Promise<User | null> {
  try {
    await apiClient.refreshAccessToken()
    return await getCurrentUser()
  } catch {
    setAccessToken(null)
    return null
  }
}

export async function logout(): Promise<void> {
  try {
    await apiClient.request<null>('auth/browser/logout/', {
      method: 'POST',
      auth: false,
      csrf: true,
      body: {},
    })
  } finally {
    setAccessToken(null)
  }
}
