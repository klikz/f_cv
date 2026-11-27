import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'

export type Product = { id: number; code: string; name: string; category: string | null; has_image: boolean; objects: number; active_version: number | null }
export type Annotation = {
  id?: number | null
  product_id: number
  bbox: [number, number, number, number]
  packaging: 'boxed' | 'unboxed'
  status: 'auto' | 'confirmed'
  confidence?: number | null
  touching: boolean
}
export type DatasetImage = {
  id: number
  camera_id: number | null
  camera_name: string | null
  product_id: number | null
  stream: string
  crop: [number, number, number, number] | null
  width: number
  height: number
  source: 'manual' | 'auto' | 'count'
  status: 'unlabeled' | 'auto' | 'confirmed'
  is_empty: boolean
  captured_at: string
  annotations: Annotation[]
}
export type ImageDetail = DatasetImage & { prev_id: number | null; next_id: number | null; position: number | null; total: number | null }
export type ImagesPage = { items: DatasetImage[]; total: number; counts: Record<string, number> }
export type Readiness = {
  product_id: number
  code: string
  name: string
  objects: number
  confirmed: number
  auto: number
  boxed: number
  unboxed: number
  touching: number
  images: number
  negatives: number
  per_camera: Record<string, number>
  per_stream: Record<string, number>
  level: 'insufficient' | 'minimal' | 'ready'
}
export type Metric = { epoch: number; box_loss: number | null; cls_loss: number | null; dfl_loss: number | null; precision: number | null; recall: number | null; map50: number | null; map5095: number | null }
export type Job = {
  id: number
  product_id: number
  product_name: string | null
  camera_id: number | null
  kind: 'full' | 'draft' | 'autolabel' | 'rebuild'
  params: Record<string, unknown>
  status: 'queued' | 'running' | 'done' | 'failed' | 'cancelled' | 'cancelling'
  stage: 'queued' | 'dataset' | 'train' | 'validate' | 'export' | 'done'
  epoch: number
  epochs: number
  scheduled_at: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
  eta_sec: number | null
  error: string | null
  model_version_id: number | null
  stats: Record<string, unknown>
}
export type JobDetail = Job & { metrics: Metric[] }
export type ModelVersion = {
  id: number
  product_id: number
  camera_id: number | null
  version: number
  model_size: string
  is_draft: boolean
  metrics: Record<string, number | string | null>
  engine_ready: boolean
  trt_version: string | null
  driver_version: string | null
  status: 'building' | 'ready' | 'failed' | 'stale'
  is_active: boolean
  job_id: number | null
  created_at: string
}
export type ProductModels = { product_id: number; code: string; name: string; active: ModelVersion | null; latest: ModelVersion | null; versions_count: number }

export type ImageFilters = { camera_id?: number; product_id?: number; status?: string; source?: string; day?: string }

export function useProducts(q?: string, category?: string) {
  return useQuery({
    queryKey: ['products', q ?? '', category ?? ''],
    queryFn: ({ signal }) => api.get<Product[]>('/products', { signal, query: { q, category } }),
    placeholderData: keepPreviousData,
  })
}
export function useProduct(id: number | undefined) {
  return useQuery({ queryKey: ['product', id], queryFn: ({ signal }) => api.get<Product>(`/products/${id}`, { signal }), enabled: !!id })
}
export function useCategories() {
  return useQuery({ queryKey: ['product-categories'], queryFn: ({ signal }) => api.get<string[]>('/products/categories', { signal }) })
}
export function useSaveProduct() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id?: number; data: { code: string; name: string; category: string | null } }) =>
      id ? api.patch<Product>(`/products/${id}`, data) : api.post<Product>('/products', data),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['products'] })
      void qc.invalidateQueries({ queryKey: ['product'] })
      void qc.invalidateQueries({ queryKey: ['product-categories'] })
    },
  })
}

export function useImages(f: ImageFilters, offset: number, limit = 60) {
  return useQuery({
    queryKey: ['images', f, offset, limit],
    queryFn: ({ signal }) => api.get<ImagesPage>('/dataset/images', { signal, query: { ...f, offset, limit } }),
    placeholderData: keepPreviousData,
  })
}
export function useImage(id: number, f: ImageFilters) {
  return useQuery({
    queryKey: ['image', id, f],
    queryFn: ({ signal }) => api.get<ImageDetail>(`/dataset/images/${id}`, { signal, query: f }),
    placeholderData: keepPreviousData,
  })
}
export function useReadiness() {
  return useQuery({ queryKey: ['readiness'], queryFn: ({ signal }) => api.get<Readiness[]>('/dataset/readiness', { signal }) })
}

export function useJobs() {
  return useQuery({ queryKey: ['jobs'], queryFn: ({ signal }) => api.get<Job[]>('/training/jobs', { signal }), refetchInterval: 3000 })
}
export function useJob(id: number) {
  return useQuery({ queryKey: ['job', id], queryFn: ({ signal }) => api.get<JobDetail>(`/training/jobs/${id}`, { signal }), refetchInterval: 2500 })
}
export function useJobLog(id: number, enabled: boolean) {
  return useQuery({
    queryKey: ['job-log', id],
    queryFn: ({ signal }) => api.get<{ lines: string[] }>(`/training/jobs/${id}/log`, { signal, query: { tail: 400 } }),
    refetchInterval: 3000,
    enabled,
  })
}
export function useModels() {
  return useQuery({ queryKey: ['models'], queryFn: ({ signal }) => api.get<ProductModels[]>('/models', { signal }), refetchInterval: 10000 })
}
export function useVersions(productId: number) {
  return useQuery({ queryKey: ['versions', productId], queryFn: ({ signal }) => api.get<ModelVersion[]>(`/models/${productId}`, { signal }) })
}
export function useTrainingCurrent() {
  return useQuery({
    queryKey: ['training-current'],
    queryFn: ({ signal }) => api.get<{ job_id?: number; stage?: string; epoch?: number; epochs?: number; inference_paused?: string | null; product_id?: number }>('/training/current', { signal }),
    refetchInterval: 4000,
  })
}

export const READINESS_LABEL: Record<Readiness['level'], string> = { insufficient: 'Yetarli emas', minimal: 'Minimal', ready: 'Tayyor' }
export const STAGE_LABEL: Record<Job['stage'], string> = { queued: 'Navbatda', dataset: 'Dataset tayyorlash', train: 'Train', validate: 'Validatsiya', export: 'TensorRT eksport', done: 'Tayyor' }
export const STATUS_LABEL: Record<Job['status'], string> = { queued: 'Navbatda', running: 'Ishlamoqda', done: 'Tayyor', failed: 'Xato', cancelled: 'Bekor qilindi', cancelling: 'Bekor qilinmoqda' }
export const KIND_LABEL: Record<Job['kind'], string> = { full: "To'liq train", draft: 'Tez qoralama', autolabel: 'Avto-belgilash', rebuild: 'Engine qayta qurish' }
