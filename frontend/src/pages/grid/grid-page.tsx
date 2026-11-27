import { ChevronLeft, ChevronRight, Expand, Plus, Shrink, Unplug, VideoOff } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { EmptyState, ErrorState } from '@/components/common/states'
import { StatusBadge } from '@/components/common/status-badge'
import { HintIcon } from '@/components/common/term'
import { useLayout } from '@/components/layout/app-layout'
import { useRouteTitle } from '@/components/layout/page'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { TaskStatusOverlay } from '@/components/video/task-status'
import type { FeedHub } from '@/components/video/feed'
import { useGridFeed } from '@/components/video/use-feed'
import { VideoCanvas } from '@/components/video/video-canvas'
import { useCameras } from '@/hooks/use-cameras'
import { useHotkeys } from '@/hooks/use-hotkeys'
import { param, useUrlState } from '@/hooks/use-url-state'
import type { Camera, CameraLive } from '@/lib/types'
import { cn } from '@/lib/utils'

const GRID_SIZES = [1, 2, 3, 4] as const

function streamKind(cam: Camera, st: CameraLive | undefined): 'online' | 'connecting' | 'offline' {
  const s = st?.streams
  const grid = cam.sub_rtsp_url ? s?.sub : s?.main
  if (!s) return 'connecting'
  if (grid?.status === 'online' || s.main?.status === 'online') return 'online'
  if (grid?.status === 'connecting') return 'connecting'
  return 'offline'
}

function Tile({ cam, hub, live, ai, size }: { cam: Camera; hub: FeedHub; live?: CameraLive; ai: boolean; size: number }) {
  const navigate = useNavigate()
  const [stale, setStale] = useState(false)
  const status = cam.enabled ? streamKind(cam, live) : 'offline'
  const sm = size >= 3
  const err = (cam.sub_rtsp_url ? live?.streams.sub : live?.streams.main)?.error
  const showOffline = cam.enabled && (status === 'offline' || (stale && status !== 'connecting'))
  return (
    <div
      className="group relative min-h-0 overflow-hidden rounded-lg border bg-video-bg outline-none focus-visible:ring-2 focus-visible:ring-ring"
      onDoubleClick={() => navigate(`/cameras/${cam.id}`)}
      onKeyDown={(e) => e.key === 'Enter' && navigate(`/cameras/${cam.id}`)}
      tabIndex={0}
      role="button"
      aria-label={`${cam.name} — kamera sahifasini ochish (ikki marta bosing)`}
    >
      <VideoCanvas hub={hub} cameraId={cam.id} showAi={ai} onStale={setStale}>
        <div className={cn('absolute top-0 right-0 left-0 flex items-center justify-between gap-2 bg-gradient-to-b from-black/60 to-transparent', sm ? 'p-1.5' : 'p-2')}>
          <Link
            to={`/cameras/${cam.id}`}
            className={cn('truncate font-semibold text-white hover:underline', sm ? 'text-xs' : 'text-sm')}
            onDoubleClick={(e) => e.stopPropagation()}
          >
            {cam.name}
          </Link>
          <StatusBadge
            status={!cam.enabled ? 'disabled' : status === 'online' ? 'online' : status === 'connecting' ? 'connecting' : 'offline'}
            size="sm"
            label={sm ? '' : undefined}
            className={cn('bg-black/50', sm && 'px-1')}
          />
        </div>
        {showOffline && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-1 bg-black/55 text-center text-white">
            <Unplug className={sm ? 'size-5' : 'size-7'} aria-hidden />
            <div className={cn('font-medium', sm ? 'text-xs' : 'text-sm')}>Aloqa yo'q</div>
            {!sm && err && <div className="max-w-[80%] text-xs text-white/70">{err}</div>}
          </div>
        )}
        {!cam.enabled && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/60 text-sm text-white/80">
            <VideoOff className="mr-2 size-4" /> O'chirilgan
          </div>
        )}
        <TaskStatusOverlay live={live?.live} size={size <= 2 ? 'lg' : 'sm'} />
      </VideoCanvas>
    </div>
  )
}

export function GridPage() {
  useRouteTitle()
  const { data: cams, isLoading, error, refetch } = useCameras()
  const [grid, setGrid] = useUrlState('grid', param.int, 2, { rememberKey: 'fcv.grid.size' })
  const [page, setPage] = useUrlState('page', param.int, 1)
  const [ai, setAi] = useUrlState('ai', param.bool, false, { rememberKey: 'fcv.grid.ai' })
  const { fullscreen, setFullscreen } = useLayout()

  const size = GRID_SIZES.includes(grid as 1) ? grid : 2
  const perPage = size * size
  const list = useMemo(() => cams ?? [], [cams])
  const pages = Math.max(1, Math.ceil(list.length / perPage))
  const cur = Math.min(Math.max(1, page), pages)
  const visible = list.slice((cur - 1) * perPage, cur * perPage)
  const ids = visible.filter((c) => c.enabled).map((c) => c.id)
  const { hub, states } = useGridFeed(ids, ai)

  useEffect(() => {
    if (page !== cur && cams) setPage(cur)
  }, [page, cur, cams, setPage])

  const go = useCallback((d: number) => setPage(Math.min(pages, Math.max(1, cur + d))), [cur, pages, setPage])
  useHotkeys([
    { combo: 'arrowright', handler: () => go(1) },
    { combo: 'arrowleft', handler: () => go(-1) },
    { combo: 'f', handler: () => setFullscreen(!fullscreen) },
    { combo: 'a', handler: () => setAi(!ai) },
    ...GRID_SIZES.map((n) => ({ combo: String(n), handler: () => setGrid(n) })),
  ])

  if (error) return <ErrorState error={error} onRetry={() => refetch()} className="h-full" />

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col">
      <div className={cn('flex flex-wrap items-center gap-3 border-b px-3 py-2', fullscreen && 'absolute top-2 right-2 z-30 rounded-lg border bg-background/80 opacity-0 backdrop-blur transition-opacity hover:opacity-100 focus-within:opacity-100')}>
        <ToggleGroup
          type="single"
          size="sm"
          variant="outline"
          value={String(size)}
          onValueChange={(v) => v && setGrid(Number(v))}
          aria-label="Grid o'lchami"
        >
          {GRID_SIZES.map((n) => (
            <ToggleGroupItem key={n} value={String(n)} className="num px-2.5 text-xs" aria-label={`${n}×${n}`}>
              {n}×{n}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
        <div className="flex items-center gap-2">
          <Checkbox id="ai-vision" checked={ai} onCheckedChange={(v) => setAi(v === true)} />
          <Label htmlFor="ai-vision" className="cursor-pointer text-sm">
            AI Vision
          </Label>
          <HintIcon id="aiVision" />
        </div>
        <div className="ml-auto flex items-center gap-2">
          {pages > 1 && (
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="icon-sm" onClick={() => go(-1)} disabled={cur <= 1} aria-label="Oldingi sahifa">
                <ChevronLeft />
              </Button>
              <span className="num min-w-12 text-center text-sm">
                {cur} / {pages}
              </span>
              <Button variant="ghost" size="icon-sm" onClick={() => go(1)} disabled={cur >= pages} aria-label="Keyingi sahifa">
                <ChevronRight />
              </Button>
            </div>
          )}
          <Button variant="outline" size="sm" onClick={() => setFullscreen(!fullscreen)}>
            {fullscreen ? <Shrink /> : <Expand />}
            {fullscreen ? 'Chiqish' : "To'liq ekran"}
          </Button>
        </div>
      </div>
      <div className="min-h-0 flex-1 p-2">
        {isLoading ? (
          <div className="grid h-full gap-2" style={{ gridTemplateColumns: `repeat(${size}, minmax(0, 1fr))`, gridTemplateRows: `repeat(${size}, minmax(0, 1fr))` }}>
            {Array.from({ length: perPage }, (_, i) => (
              <Skeleton key={i} className="h-full w-full" />
            ))}
          </div>
        ) : list.length === 0 ? (
          <EmptyState
            title="Kamera yo'q"
            description="Kameralar panelida video ko'rish uchun avval kamera qo'shing (RTSP yoki ONVIF orqali)."
            action={
              <Button asChild>
                <Link to="/settings/cameras/new">
                  <Plus /> Kamera qo'shish
                </Link>
              </Button>
            }
            className="h-full"
          />
        ) : (
          <div
            className="grid h-full gap-2"
            style={{ gridTemplateColumns: `repeat(${size}, minmax(0, 1fr))`, gridTemplateRows: `repeat(${size}, minmax(0, 1fr))` }}
          >
            {visible.map((cam) => (
              <Tile key={cam.id} cam={cam} hub={hub} live={states[cam.id]} ai={ai} size={size} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
