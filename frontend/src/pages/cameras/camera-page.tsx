import { ArrowLeft, Boxes, Cog, Pencil, PanelRightClose, PanelRightOpen, TriangleAlert, Wrench } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Link, useParams } from 'react-router'
import { useConfirm } from '@/components/common/confirm-dialog'
import { EmptyState, ErrorState } from '@/components/common/states'
import { StatusBadge } from '@/components/common/status-badge'
import { HintIcon, Term } from '@/components/common/term'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { useCameraFeed } from '@/components/video/use-feed'
import { VideoCanvas } from '@/components/video/video-canvas'
import { useCamera } from '@/hooks/use-cameras'
import { useSetAnalysisStream, useTasks, useToggleTask, type TaskType } from '@/hooks/use-tasks'
import { storage } from '@/lib/storage'
import { fmtDuration, fmtNum, fmtPct, fmtSec, resolution } from '@/lib/format'
import { notify } from '@/lib/notify'
import type { Camera, CameraLive } from '@/lib/types'
import { cn } from '@/lib/utils'
import { CameraExtras } from './camera-extras'

function Section({ title, children, action }: { title: ReactNode; children: ReactNode; action?: ReactNode }) {
  return (
    <section className="space-y-2">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  )
}

function StreamsInfo({ cam, live }: { cam: Camera; live?: CameraLive }) {
  return (
    <div className="space-y-1.5 text-sm">
      {cam.streams.map((s) => {
        const ls = live?.streams[s.kind]
        const st = ls?.status ?? s.status
        return (
          <div key={s.kind} className="flex items-center justify-between gap-2">
            <span className="w-16 text-muted-foreground">{s.kind === 'main' ? 'Asosiy' : 'Sub'}</span>
            <span className="num flex-1 text-xs">
              {s.codec?.toUpperCase() ?? '—'} · {resolution(ls?.width ?? s.width, ls?.height ?? s.height)} · {s.fps ? `${s.fps} fps` : '—'}
            </span>
            <StatusBadge status={st === 'online' ? 'online' : st === 'connecting' ? 'connecting' : st === 'error' ? 'error' : 'offline'} size="sm" variant="inline" label={st === 'offline' && s.kind === 'main' ? 'Yopiq' : undefined} />
          </div>
        )
      })}
      {cam.onvif?.model && (
        <div className="text-xs text-muted-foreground">
          ONVIF: {cam.onvif.manufacturer} {cam.onvif.model} · {cam.onvif.serial ?? ''}
        </div>
      )}
    </div>
  )
}

const TASKS: { type: TaskType; label: string; icon: typeof Boxes; path: string }[] = [
  { type: 'counting', label: 'Mahsulot sanash', icon: Boxes, path: 'counting' },
  { type: 'equipment', label: 'Uskuna ish vaqti', icon: Wrench, path: 'equipment' },
]

function TasksPanel({ cameraId }: { cameraId: number }) {
  const { data, isLoading } = useTasks(cameraId)
  const toggle = useToggleTask(cameraId)
  const setStream = useSetAnalysisStream(cameraId)
  const confirm = useConfirm()
  if (isLoading || !data) return <Skeleton className="h-32 w-full" />

  const changeStream = async (s: 'main' | 'sub') => {
    if (s === data.analysis_stream) return
    const anyEnabled = data.tasks.counting.enabled
    const ok = await confirm({
      title: `Tahlil oqimini "${s === 'main' ? 'Asosiy' : 'Sub'}" ga almashtirish`,
      description: (
        <>
          Shu kameraning barcha vazifalari shakllari (ROI, chiziq, zonalar) qayta chiziladi — asosiy va sub oqimning ko'rish maydoni bir xil bo'lmasligi mumkin.
          {anyEnabled && (
            <span className="mt-2 block text-warning">
              Sanash yoqilgan: modellar boshqa oqim rasmlarida train qilingan bo'lsa, aniqlik tushishi mumkin.
            </span>
          )}
        </>
      ),
      confirmText: 'Almashtirish',
    })
    if (!ok) return
    setStream.mutate(s, {
      onSuccess: () => notify.info('Tahlil oqimi almashtirildi', 'Vazifalar shakllarini qayta chizing'),
      onError: (e) => notify.error('Almashtirib bo\'lmadi', e),
    })
  }

  const size = (k: 'main' | 'sub') => {
    const s = data.stream_sizes[k]
    return s ? `${s[0]}×${s[1]}` : ''
  }

  return (
    <div className="space-y-3">
      <div className="space-y-1.5">
        <Term id="analysisStream" className="text-sm font-medium" />
        <ToggleGroup type="single" variant="outline" size="sm" value={data.analysis_stream} onValueChange={(v) => v && void changeStream(v as 'main' | 'sub')} className="w-full">
          <ToggleGroupItem value="main" className="flex-1 text-xs">
            Asosiy <span className="num ml-1 text-muted-foreground">{size('main')}</span>
          </ToggleGroupItem>
          <ToggleGroupItem value="sub" className="flex-1 text-xs" disabled={!data.has_sub}>
            Sub <span className="num ml-1 text-muted-foreground">{size('sub')}</span>
          </ToggleGroupItem>
        </ToggleGroup>
      </div>
      <div className="space-y-2">
        {TASKS.map((t) => {
          const st = data.tasks[t.type]
          return (
            <div key={t.type} className="rounded-lg border p-2.5">
              <div className="flex items-center gap-2">
                <Checkbox
                  id={`task-${t.type}`}
                  checked={st.enabled}
                  onCheckedChange={(v) => toggle.mutate({ task: t.type, enabled: v === true }, { onError: (e) => notify.error('Saqlab bo\'lmadi', e) })}
                />
                <Label htmlFor={`task-${t.type}`} className="flex flex-1 cursor-pointer items-center gap-1.5">
                  <t.icon className="size-4 text-muted-foreground" /> {t.label}
                </Label>
                {st.enabled ? (
                  <Button size="xs" variant={st.configured ? 'outline' : 'default'} asChild>
                    <Link to={`/cameras/${cameraId}/${t.path}`}>
                      <Cog /> Sozlash
                    </Link>
                  </Button>
                ) : (
                  <Button size="xs" variant="outline" disabled>
                    <Cog /> Sozlash
                  </Button>
                )}
              </div>
              {st.enabled && st.issues.length > 0 && (
                <div className="mt-1.5 space-y-0.5 pl-6">
                  {st.issues.map((i) => (
                    <div key={i} className="flex items-center gap-1 text-xs text-warning">
                      <TriangleAlert className="size-3 shrink-0" /> {i}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function Stat({ label, value, tone }: { label: ReactNode; value: ReactNode; tone?: string }) {
  return (
    <div className="rounded-md bg-muted/60 px-2.5 py-1.5">
      <div className="text-2xs text-muted-foreground">{label}</div>
      <div className={cn('num text-lg font-semibold', tone)}>{value}</div>
    </div>
  )
}

function LiveStats({ live }: { live?: CameraLive }) {
  const c = live?.live?.counting
  const e = live?.live?.equipment
  if (!c && !e) return <p className="text-sm text-muted-foreground">Yoqilgan va sozlangan vazifa yo'q.</p>
  return (
    <div className="space-y-3">
      {c && (
        <div className="space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <Stat label="Sanaldi (joriy smena)" value={fmtNum(c.total)} tone="text-success" />
            <Stat label={<span className="inline-flex items-center gap-1">Noaniq <HintIcon id="uncertainCount" /></span>} value={fmtNum(c.uncertain)} tone={c.uncertain ? 'text-warning' : undefined} />
          </div>
          {c.paused && <StatusBadge status="training" label={c.paused_reason ?? 'Train ketmoqda — sanash to\'xtatilgan'} />}
          {c.per_product.length > 0 && (
            <div className="space-y-1 text-sm">
              {c.per_product.map((p) => (
                <div key={p.product_id ?? p.name} className="flex justify-between gap-2">
                  <span className="truncate">{p.name}</span>
                  <span className="num font-medium">{p.count}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      {e && (
        <div className="grid grid-cols-2 gap-2">
          <Stat
            label="Holat"
            value={e.state === 'running' ? 'Ishlayapti' : e.state === 'stopped' ? "To'xtagan" : "Noma'lum"}
            tone={e.state === 'running' ? 'text-success' : e.state === 'stopped' ? 'text-danger' : 'text-neutral'}
          />
          <Stat label="Ish vaqti %" value={fmtPct(e.utilization_pct)} />
          <Stat label="Ishladi" value={fmtDuration(e.run_seconds)} />
          <Stat label="To'xtadi" value={fmtDuration(e.stop_seconds)} />
          <Stat label="Sikllar" value={fmtNum(e.cycles)} />
          <Stat label="Oxirgi / o'rtacha sikl" value={<span className="text-base">{fmtSec(e.last_cycle_sec)} / {fmtSec(e.avg_cycle_sec)}</span>} />
          <Stat label={<span className="inline-flex items-center gap-1">Etalon sikl <HintIcon id="referenceCycle" /></span>} value={fmtSec(e.reference_cycle_sec)} />
          <Stat label="Mikro-to'xtashlar" value={fmtNum(e.micro_stops)} tone={e.micro_stops ? 'text-warning' : undefined} />
        </div>
      )}
    </div>
  )
}

export function CameraPage() {
  const id = Number(useParams().id)
  const { data: cam, isLoading, error, refetch } = useCamera(id)
  const { hub, states } = useCameraFeed(id, 'main')
  const [ai, setAi] = useState(() => storage.get<boolean>('fcv.camera.ai') ?? true)
  const [panel, setPanel] = useState(() => storage.get<boolean>('fcv.camera.panel') ?? true)
  const [stale, setStale] = useState(false)
  useDocumentTitle(cam?.name ?? `Kamera ${id}`)
  const live = states[id]

  if (error) return <ErrorState error={error} onRetry={() => refetch()} className="h-full" />
  if (!isLoading && !cam) return <EmptyState title="Kamera topilmadi" />

  return (
    <div className="flex h-full min-h-0 flex-1">
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-2 border-b px-3 py-2">
          <Button variant="ghost" size="icon-sm" asChild aria-label="Orqaga">
            <Link to="/">
              <ArrowLeft />
            </Link>
          </Button>
          <h1 className="truncate text-lg font-semibold">{cam?.name ?? <Skeleton className="h-5 w-40" />}</h1>
          {cam && (
            <StatusBadge
              status={live?.streams.main.status === 'online' || live?.streams.sub.status === 'online' ? 'online' : stale ? 'offline' : 'connecting'}
              size="sm"
            />
          )}
          <div className="ml-auto flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Switch
                id="cam-ai"
                checked={ai}
                onCheckedChange={(v) => {
                  setAi(v)
                  storage.set('fcv.camera.ai', v)
                }}
              />
              <Label htmlFor="cam-ai" className="text-sm">
                AI qatlami
              </Label>
            </div>
            <Button variant="ghost" size="icon-sm" asChild aria-label="Tahrirlash">
              <Link to={`/settings/cameras/${id}/edit`}>
                <Pencil />
              </Link>
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => {
                setPanel(!panel)
                storage.set('fcv.camera.panel', !panel)
              }}
              aria-label="Yon panel"
            >
              {panel ? <PanelRightClose /> : <PanelRightOpen />}
            </Button>
          </div>
        </div>
        <div className="min-h-0 flex-1 p-2">
          <VideoCanvas hub={hub} cameraId={id} showAi={ai} onStale={setStale} className="rounded-lg">
            {stale && (
              <div className="absolute inset-0 flex items-center justify-center text-sm text-white/70">
                {live?.streams.main.error ?? 'Video kutilmoqda…'}
              </div>
            )}
          </VideoCanvas>
        </div>
      </div>
      {panel && (
        <aside className="w-[340px] shrink-0 space-y-5 overflow-y-auto border-l p-4">
          {cam && (
            <Section title="Oqimlar">
              <StreamsInfo cam={cam} live={live} />
            </Section>
          )}
          <Separator />
          <Section title="Vazifalar">
            <TasksPanel cameraId={id} />
          </Section>
          <Separator />
          <Section title="Joriy smena">
            <LiveStats live={live} />
          </Section>
          <CameraExtras cameraId={id} />
        </aside>
      )}
    </div>
  )
}
