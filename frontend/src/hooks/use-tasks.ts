import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Point } from '@/lib/types'

export type TaskType = 'counting' | 'equipment'
export type TaskState = { enabled: boolean; configured: boolean; issues: string[] }
export type TasksOut = {
  camera_id: number
  analysis_stream: 'main' | 'sub'
  has_sub: boolean
  stream_sizes: { main: [number, number] | null; sub: [number, number] | null }
  tasks: Record<TaskType, TaskState>
}

export type CountingConfig = {
  stream: 'main' | 'sub'
  roi_polygon: Point[] | null
  line: [Point, Point] | null
  direction: 'a_to_b' | 'b_to_a' | 'both'
  reverse_policy: 'ignore' | 'subtract' | 'separate'
  max_angle: number
  track_point: 'center' | 'bottom_center'
  inference_fps: number
  min_track_frames: number
  min_distance: number
  conf_threshold: number
  uncertain_margin: number
  min_winner_score: number
}

export type EquipmentConfig = {
  stream: 'main' | 'sub'
  roi_polygon: Point[] | null
  control_zone: Point[] | null
  exclude_zones: Point[][]
  motion_threshold: number
  min_on_sec: number
  min_off_sec: number
  cycle_mode: 'home' | 'peaks' | 'off'
  returns_per_cycle: number
  home_exit_threshold: number
  home_return_threshold: number
  peak_min_height: number
  peak_min_distance_sec: number
  reference_cycle_sec: number | null
  auto_reference: boolean
  micro_stop_factor: number
  home_reference: string | null
}

export const taskKeys = {
  tasks: (id: number) => ['tasks', id] as const,
  counting: (id: number) => ['counting-config', id] as const,
  equipment: (id: number) => ['equipment-config', id] as const,
}

export function useTasks(id: number) {
  return useQuery({ queryKey: taskKeys.tasks(id), queryFn: ({ signal }) => api.get<TasksOut>(`/cameras/${id}/tasks`, { signal }) })
}

export function useToggleTask(id: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ task, enabled }: { task: TaskType; enabled: boolean }) => api.put<TasksOut>(`/cameras/${id}/tasks/${task}`, { enabled }),
    onMutate: async ({ task, enabled }) => {
      const prev = qc.getQueryData<TasksOut>(taskKeys.tasks(id))
      if (prev) qc.setQueryData(taskKeys.tasks(id), { ...prev, tasks: { ...prev.tasks, [task]: { ...prev.tasks[task], enabled } } })
      return { prev }
    },
    onError: (_e, _v, ctx) => ctx?.prev && qc.setQueryData(taskKeys.tasks(id), ctx.prev),
    onSuccess: (d) => qc.setQueryData(taskKeys.tasks(id), d),
  })
}

export function useSetAnalysisStream(id: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (stream: 'main' | 'sub') => api.post<TasksOut>(`/cameras/${id}/analysis-stream`, { stream }),
    onSuccess: (d) => {
      qc.setQueryData(taskKeys.tasks(id), d)
      void qc.invalidateQueries({ queryKey: taskKeys.counting(id) })
      void qc.invalidateQueries({ queryKey: taskKeys.equipment(id) })
      void qc.invalidateQueries({ queryKey: ['cameras'] })
    },
  })
}

export function useCountingConfig(id: number) {
  return useQuery({ queryKey: taskKeys.counting(id), queryFn: ({ signal }) => api.get<CountingConfig>(`/cameras/${id}/counting`, { signal }) })
}

export function useEquipmentConfig(id: number) {
  return useQuery({ queryKey: taskKeys.equipment(id), queryFn: ({ signal }) => api.get<EquipmentConfig>(`/cameras/${id}/equipment`, { signal }) })
}

export function useSaveConfig<T>(id: number, kind: TaskType) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: T) => api.put<T>(`/cameras/${id}/${kind}`, data as Record<string, unknown>),
    onSuccess: (d) => {
      qc.setQueryData(kind === 'counting' ? taskKeys.counting(id) : taskKeys.equipment(id), d)
      void qc.invalidateQueries({ queryKey: taskKeys.tasks(id) })
    },
  })
}
