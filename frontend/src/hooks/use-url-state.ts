import { useCallback, useEffect, useMemo } from 'react'
import { useSearchParams } from 'react-router'
import { storage } from '@/lib/storage'

type Parser<T> = { parse: (raw: string) => T | undefined; serialize: (v: T) => string }

export const param = {
  string: {
    parse: (r: string) => r,
    serialize: (v: string) => v,
  } satisfies Parser<string>,
  int: {
    parse: (r: string) => {
      const n = Number.parseInt(r, 10)
      return Number.isFinite(n) ? n : undefined
    },
    serialize: (v: number) => String(v),
  } satisfies Parser<number>,
  bool: {
    parse: (r: string) => (r === '1' ? true : r === '0' ? false : undefined),
    serialize: (v: boolean) => (v ? '1' : '0'),
  } satisfies Parser<boolean>,
  oneOf<const T extends string>(values: readonly T[]): Parser<T> {
    return {
      parse: (r) => (values as readonly string[]).includes(r) ? (r as T) : undefined,
      serialize: (v) => v,
    }
  },
}

/**
 * react-router'ning setSearchParams(prev => ...) dagi `prev` — hook render bo'lgandagi qiymat.
 * Bir hodisada ikki marta chaqirilsa (masalan setCamera(4); setPage(1)), ikkinchisi birinchisini
 * o'chirib yuboradi. Shu sababli joriy hodisadagi o'zgarishlar shu yerda yig'iladi.
 */
let pending: URLSearchParams | null = null

type Options = {
  /** URL'da qiymat bo'lmasa, brauzerda eslab qolinganini olish (masalan grid rejimi). */
  rememberKey?: string
  /** true — tarixga yangi yozuv qo'shadi ("orqaga" tugmasi oldingi holatga qaytaradi). */
  push?: boolean
}

/**
 * Holatni URL query parametrida saqlash (PLAN.md 4.2): yorliq, qadam, oyna, filtr.
 * Qiymat default'ga teng bo'lsa URL'dan olib tashlanadi — manzil toza qoladi.
 */
export function useUrlState<T>(key: string, parser: Parser<T>, defaultValue: T, opts: Options = {}) {
  const [params, setParams] = useSearchParams()
  const raw = params.get(key)

  const value = useMemo<T>(() => {
    if (raw !== null) {
      const v = parser.parse(raw)
      if (v !== undefined) return v
    }
    if (opts.rememberKey) {
      const saved = storage.get<string>(opts.rememberKey)
      if (saved !== null) {
        const v = parser.parse(saved)
        if (v !== undefined) return v
      }
    }
    return defaultValue
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [raw, opts.rememberKey])

  useEffect(() => {
    if (opts.rememberKey && raw !== null && parser.parse(raw) !== undefined) storage.set(opts.rememberKey, raw)
  }, [raw, opts.rememberKey, parser])

  const setValue = useCallback(
    (next: T | ((prev: T) => T)) => {
      const p = new URLSearchParams(pending ?? window.location.search)
      const r = p.get(key)
      const parsed = r !== null ? parser.parse(r) : undefined
      const cur = parsed === undefined ? value : parsed
      const v = typeof next === 'function' ? (next as (x: T) => T)(cur) : next
      const s = parser.serialize(v)
      if (s === parser.serialize(defaultValue) && !opts.rememberKey) p.delete(key)
      else p.set(key, s)
      if (opts.rememberKey) storage.set(opts.rememberKey, s)
      if (!pending) queueMicrotask(() => (pending = null))
      pending = p
      setParams(p, { replace: !opts.push })
    },
    [setParams, key, parser, defaultValue, value, opts.rememberKey, opts.push],
  )

  return [value, setValue] as const
}
