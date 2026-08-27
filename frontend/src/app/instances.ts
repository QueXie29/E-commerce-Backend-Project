import { createPinia } from 'pinia'
import { QueryClient } from '@tanstack/vue-query'

import { ApiError } from '@/shared/api/errors'

export const pinia = createPinia()

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status < 500) return false
        return failureCount < 2
      },
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
})
