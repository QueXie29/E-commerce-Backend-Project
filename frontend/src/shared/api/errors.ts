export class ApiError extends Error {
  readonly status: number
  readonly code: number
  readonly data: unknown

  constructor(message: string, options: { status: number; code?: number; data?: unknown }) {
    super(message)
    this.name = 'ApiError'
    this.status = options.status
    this.code = options.code ?? 50000
    this.data = options.data ?? null
  }

  get fieldErrors(): Record<string, string[]> {
    if (!this.data || typeof this.data !== 'object' || Array.isArray(this.data)) return {}

    return Object.fromEntries(
      Object.entries(this.data as Record<string, unknown>).map(([field, value]) => [
        field,
        Array.isArray(value) ? value.map(String) : [String(value)],
      ]),
    )
  }
}

export function errorMessage(error: unknown, fallback = '操作失败，请稍后重试'): string {
  if (error instanceof ApiError || error instanceof Error) return error.message
  return fallback
}
