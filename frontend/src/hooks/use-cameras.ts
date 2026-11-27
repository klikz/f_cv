import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Camera, ProbeResult } from '@/lib/types'

export const cameraKeys = {
  all: ['cameras'] as const,
  one: (id: number) => ['cameras', id] as const,
}

export function useCameras() {
  return useQuery({
    queryKey: cameraKeys.all,
    queryFn: ({ signal }) => api.get<Camera[]>('/cameras', { signal }),
    refetchInterval: 10_000,
  })
}

export function useCamera(id: number | undefined) {
  return useQuery({
    queryKey: cameraKeys.one(id ?? 0),
    queryFn: ({ signal }) => api.get<Camera>(`/cameras/${id}`, { signal }),
    enabled: !!id,
    refetchInterval: 10_000,
  })
}

export type CameraInput = {
  name: string
  enabled?: boolean
  main_rtsp_url: string
  sub_rtsp_url?: string | null
  fov_match?: boolean
  connection_type?: 'rtsp' | 'onvif'
  onvif_host?: string | null
  onvif_port?: number | null
  onvif_username?: string | null
  onvif_password?: string | null
  onvif_manufacturer?: string | null
  onvif_model?: string | null
  onvif_serial?: string | null
  onvif_main_profile?: string | null
  onvif_sub_profile?: string | null
  clear_sub?: boolean
}

export function useSaveCamera() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id?: number; data: CameraInput }) =>
      id ? api.patch<Camera>(`/cameras/${id}`, data) : api.post<Camera>('/cameras', data),
    onSuccess: (cam) => {
      qc.setQueryData(cameraKeys.one(cam.id), cam)
      void qc.invalidateQueries({ queryKey: cameraKeys.all })
    },
  })
}

export function useDeleteCamera() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.delete(`/cameras/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: cameraKeys.all }),
  })
}

export function useReorderCameras() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (ids: number[]) => api.post('/cameras/reorder', { ids }),
    onMutate: async (ids) => {
      await qc.cancelQueries({ queryKey: cameraKeys.all })
      const prev = qc.getQueryData<Camera[]>(cameraKeys.all)
      if (prev) {
        const byId = new Map(prev.map((c) => [c.id, c]))
        qc.setQueryData(
          cameraKeys.all,
          ids.map((id) => byId.get(id)!).filter(Boolean),
        )
      }
      return { prev }
    },
    onError: (_e, _v, ctx) => ctx?.prev && qc.setQueryData(cameraKeys.all, ctx.prev),
    onSettled: () => qc.invalidateQueries({ queryKey: cameraKeys.all }),
  })
}

export function probeStream(body: { url?: string; camera_id?: number; kind?: 'main' | 'sub' }) {
  return api.post<ProbeResult>('/cameras/probe', body, { timeoutMs: 30_000 })
}

export function previewFrames(body: { main_url?: string | null; sub_url?: string | null; camera_id?: number }) {
  return api.post<{ main: string | null; sub: string | null; main_error: string | null; sub_error: string | null }>(
    '/cameras/preview',
    body,
    { timeoutMs: 40_000 },
  )
}

/** Oqim holati: WS holatidan (jonli) yoki API javobidan. */
export function streamOf(cam: Camera, kind: 'main' | 'sub') {
  return cam.streams.find((s) => s.kind === kind)
}
