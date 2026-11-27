import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export type CountEvent = {
  id: number
  camera_id: number | null
  camera_name: string | null
  product_id: number | null
  product_name: string | null
  original_product_id: number | null
  original_product_name: string | null
  status: 'confirmed' | 'uncertain' | 'corrected' | 'cancelled'
  candidates: { product_id: number; score: number; name: string | null; winner?: boolean }[]
  direction: 'forward' | 'reverse'
  confidence: number | null
  bbox: [number, number, number, number] | null
  ts: string
  shift_id: number | null
  shift_date: string | null
  has_snapshot: boolean
  corrected_at: string | null
  note: string | null
}
export type EventFilters = { camera_id?: number; product_id?: number; status?: string; day_from?: string; day_to?: string; shift_id?: number }

export function useCountEvents(f: EventFilters, offset: number, limit = 48) {
  return useQuery({
    queryKey: ['counts', f, offset, limit],
    queryFn: ({ signal }) => api.get<{ items: CountEvent[]; total: number; summary: Record<string, number> }>('/counts', { signal, query: { ...f, offset, limit } }),
    placeholderData: keepPreviousData,
    refetchInterval: 10000,
  })
}
export function useCountEvent(id: number) {
  return useQuery({ queryKey: ['count', id], queryFn: ({ signal }) => api.get<CountEvent>(`/counts/${id}`, { signal }) })
}

export const COUNT_STATUS_LABEL: Record<CountEvent['status'], string> = {
  confirmed: 'Tasdiqlangan',
  uncertain: 'Noaniq',
  corrected: 'Tuzatilgan',
  cancelled: 'Bekor qilingan',
}
