import type { Params } from 'react-router'

export type Crumb = { label: string; to?: string }

/** Har marshrut `handle` qiymati: non bo'laklari va brauzer yorlig'i nomi uchun. */
export type RouteHandle = {
  crumbs: (params: Params) => Crumb[]
  /** Qaysi bosqichda amalga oshiriladi (bo'sh sahifa uchun). */
  stage?: number
  /** Grid kabi to'liq ekranli sahifa — padding'siz. */
  bleed?: boolean
}

export function isRouteHandle(h: unknown): h is RouteHandle {
  return !!h && typeof h === 'object' && 'crumbs' in h
}
