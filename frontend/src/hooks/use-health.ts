import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export type HealthStatus = 'ok' | 'warn' | 'error'

export type Check = { status: HealthStatus; detail: string | null; data: Record<string, unknown> }

export type GpuInfo = {
  index: number
  name: string
  util_pct: number
  mem_used_mb: number
  mem_total_mb: number
  temp_c: number
}

export type Health = {
  status: HealthStatus
  server_time: string
  timezone: string
  db: Check
  redis: Check
  gpu: Check & { data: { driver?: string; gpus?: GpuInfo[] } }
  disk: Check & { data: { total_gb?: number; free_gb?: number; free_pct?: number; used_gb?: number } }
  processes: { name: string; status: HealthStatus; pid: number | null; age_sec: number | null }[]
}

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: ({ signal }) => api.get<Health>('/health', { signal, timeoutMs: 6000 }),
    refetchInterval: 5000,
    refetchIntervalInBackground: true,
    retry: false,
  })
}
