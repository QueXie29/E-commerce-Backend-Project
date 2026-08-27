type SessionListener = (accessToken: string | null) => void

let accessToken: string | null = null
const listeners = new Set<SessionListener>()

export function getAccessToken(): string | null {
  return accessToken
}

export function setAccessToken(token: string | null): void {
  accessToken = token
  listeners.forEach((listener) => listener(token))
}

export function subscribeToSession(listener: SessionListener): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}
