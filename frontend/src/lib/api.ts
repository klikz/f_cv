import { QueryClient } from '@tanstack/react-query'
import { t } from '@/lib/i18n'

/** API xatosi: foydalanuvchiga ko'rsatiladigan xabar bilan. */
export class ApiError extends Error {
  readonly status: number
  readonly detail: unknown

  constructor(status: number, message: string, detail?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }

  get isNetwork() {
    return this.status === 0
  }
}

type Json = Record<string, unknown> | unknown[] | string | number | boolean | null

export type RequestOptions = Omit<RequestInit, 'body'> & {
  body?: Json | FormData
  query?: Record<string, string | number | boolean | null | undefined>
  timeoutMs?: number
}

function buildUrl(path: string, query?: RequestOptions['query']) {
  const url = new URL(path.startsWith('/api') ? path : `/api${path}`, window.location.origin)
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v))
    }
  }
  return url.toString()
}

function extractMessage(status: number, body: unknown): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const d = (body as { detail: unknown }).detail
    if (typeof d === 'string') return d
    if (Array.isArray(d) && d.length && typeof d[0] === 'object' && d[0] && 'msg' in d[0]) {
      return String((d[0] as { msg: unknown }).msg)
    }
  }
  return t.errors.http(status)
}

export async function apiFetch<T = unknown>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { body, query, timeoutMs = 15000, headers, signal, ...rest } = opts
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(new DOMException('timeout', 'TimeoutError')), timeoutMs)
  signal?.addEventListener('abort', () => ctrl.abort(signal.reason))

  const isForm = body instanceof FormData
  let res: Response
  try {
    res = await fetch(buildUrl(path, query), {
      ...rest,
      signal: ctrl.signal,
      headers: {
        Accept: 'application/json',
        ...(body !== undefined && !isForm ? { 'Content-Type': 'application/json' } : {}),
        ...headers,
      },
      body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
    })
  } catch (e) {
    if (signal?.aborted) throw e
    throw new ApiError(0, t.errors.network, e)
  } finally {
    clearTimeout(timer)
  }

  const text = await res.text()
  const data = text ? safeJson(text) : null
  if (!res.ok) throw new ApiError(res.status, extractMessage(res.status, data), data)
  return data as T
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

export const api = {
  get: <T>(path: string, opts?: RequestOptions) => apiFetch<T>(path, { ...opts, method: 'GET' }),
  post: <T>(path: string, body?: Json | FormData, opts?: RequestOptions) =>
    apiFetch<T>(path, { ...opts, method: 'POST', body }),
  put: <T>(path: string, body?: Json, opts?: RequestOptions) => apiFetch<T>(path, { ...opts, method: 'PUT', body }),
  patch: <T>(path: string, body?: Json, opts?: RequestOptions) =>
    apiFetch<T>(path, { ...opts, method: 'PATCH', body }),
  delete: <T>(path: string, opts?: RequestOptions) => apiFetch<T>(path, { ...opts, method: 'DELETE' }),
}

export function errorMessage(e: unknown): string {
  if (e instanceof ApiError) return e.message
  if (e instanceof Error) return e.message
  return t.errors.generic
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5_000,
      refetchOnWindowFocus: false,
      retry: (count, err) => !(err instanceof ApiError && err.status >= 400 && err.status < 500) && count < 2,
    },
  },
})
