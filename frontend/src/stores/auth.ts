import { computed, onScopeDispose, ref } from 'vue'
import { defineStore } from 'pinia'

import type { LoginInput, RegisterInput, User } from '@/shared/api/contracts'
import {
  getCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
  register as registerRequest,
  restoreSession,
} from '@/shared/api/auth'
import { subscribeToSession } from '@/shared/api/session'
import { queryClient } from '@/app/instances'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const initialized = ref(false)
  const busy = ref(false)
  const isAuthenticated = computed(() => user.value !== null)
  const isAdmin = computed(() => user.value?.role === 'admin')
  let initialization: Promise<void> | null = null

  const unsubscribe = subscribeToSession((token) => {
    if (!token) {
      user.value = null
      queryClient.clear()
    }
  })
  onScopeDispose(unsubscribe)

  function initialize(): Promise<void> {
    initialization ??= restoreSession()
      .then((restoredUser) => {
        user.value = restoredUser
      })
      .finally(() => {
        initialized.value = true
      })
    return initialization
  }

  async function login(input: LoginInput): Promise<User> {
    busy.value = true
    try {
      queryClient.clear()
      user.value = await loginRequest(input)
      initialized.value = true
      return user.value
    } finally {
      busy.value = false
    }
  }

  async function register(input: RegisterInput): Promise<User> {
    busy.value = true
    try {
      queryClient.clear()
      await registerRequest(input)
      user.value = await loginRequest({ username: input.username, password: input.password })
      initialized.value = true
      return user.value
    } finally {
      busy.value = false
    }
  }

  async function logout(): Promise<void> {
    busy.value = true
    try {
      await logoutRequest()
      user.value = null
    } finally {
      busy.value = false
    }
  }

  async function refreshUser(): Promise<User> {
    user.value = await getCurrentUser()
    return user.value
  }

  return {
    user,
    initialized,
    busy,
    isAuthenticated,
    isAdmin,
    initialize,
    login,
    register,
    logout,
    refreshUser,
  }
})
