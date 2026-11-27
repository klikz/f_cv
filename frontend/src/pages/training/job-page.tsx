import { Check, Cpu, Loader2, RotateCcw, StepForward, X } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useQueryClient } from '@tanstack/react-query'
import { baseOption, Chart, useChartTheme } from '@/components/common/chart'
import { Progress } from '@/components/common/progress'
import { ErrorState } from '@/components/common/states'
import { PageBody, PageHeader } from '@/components/layout/page'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { KIND_LABEL, STAGE_LABEL, useJob, useJobLog, type Job } from '@/hooks/use-catalog'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { useHealth } from '@/hooks/use-health'
import { param, useUrlState } from '@/hooks/use-url-state'
import { api } from '@/lib/api'
import { fmtDateTime, fmtDuration } from '@/lib/format'
import { notify } from '@/lib/notify'
import { cn } from '@/lib/utils'
import { JobStatus } from './job-status'

const STAGES: Job['stage'][] = ['queued', 'dataset', 'train', 'validate', 'export', 'done']

function Stepper({ job }: { job: Job }) {
  const stages = job.kind === 'draft' ? STAGES.filter((s) => s !== 'export') : job.kind === 'autolabel' ? (['queued', 'train', 'done'] as Job['stage'][]) : STAGES
  const cur = stages.indexOf(job.stage)
  const failed = job.status === 'failed' || job.status === 'cancelled'
  return (
    <ol className="flex flex-wrap items-center gap-1 text-sm">
      {stages.map((s, i) => {
        const done = i < cur || job.status === 'done'
        const active = i === cur && job.status === 'running'
        return (
          <li key={s} className="flex items-center gap-1">
            <span
              className={cn(
                'flex items-center gap-1.5 rounded-full px-2.5 py-1',
                done && 'bg-success-muted text-success',
                active && 'bg-info-muted text-info',
                failed && i === cur && 'bg-danger-muted text-danger',
                !done && !active && !(failed && i === cur) && 'bg-muted text-muted-foreground',
              )}
            >
              {done ? <Check className="size-3.5" /> : active ? <Loader2 className="size-3.5 animate-spin" /> : null}
              {job.kind === 'autolabel' && s === 'train' ? 'Belgilash' : STAGE_LABEL[s]}
            </span>
            {i < stages.length - 1 && <span className="text-muted-foreground">›</span>}
          </li>
        )
      })}
    </ol>
  )
}

function Info({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className="text-2xs text-muted-foreground">{label}</div>
      <div className="num font-semibold">{value}</div>
    </div>
  )
}

export function JobPage() {
  const id = Number(useParams().jobId)
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { data: job, error, refetch } = useJob(id)
  const [tab, setTab] = useUrlState('tab', param.oneOf(['charts', 'logs'] as const), 'charts')
  const { data: log } = useJobLog(id, tab === 'logs')
  const { data: health } = useHealth()
  const t = useChartTheme()
  const logRef = useRef<HTMLPreElement>(null)
  useDocumentTitle(job ? `Train #${id} — ${job.product_name}` : `Train #${id}`)

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [log])

  if (error) return <ErrorState error={error} onRetry={() => refetch()} />
  if (!job)
    return (
      <PageBody>
        <Skeleton className="h-96 w-full" />
      </PageBody>
    )

  const elapsed = job.started_at ? ((job.finished_at ? new Date(job.finished_at) : new Date()).getTime() - new Date(job.started_at).getTime()) / 1000 : null
  const gpu = health?.gpu.data.gpus?.[0]
  const ms = job.metrics
  const ep = ms.map((m) => m.epoch)
  const lossOpt = {
    ...baseOption(t),
    xAxis: { ...baseOption(t).xAxis, type: 'category', data: ep, name: 'epoch' },
    yAxis: { ...baseOption(t).yAxis, type: 'value', scale: true },
    series: [
      { name: 'box', type: 'line', showSymbol: false, data: ms.map((m) => m.box_loss) },
      { name: 'cls', type: 'line', showSymbol: false, data: ms.map((m) => m.cls_loss) },
      { name: 'l1/dfl', type: 'line', showSymbol: false, data: ms.map((m) => m.dfl_loss) },
    ],
  }
  const mapOpt = {
    ...baseOption(t),
    xAxis: { ...baseOption(t).xAxis, type: 'category', data: ep, name: 'epoch' },
    yAxis: { ...baseOption(t).yAxis, type: 'value', min: 0, max: 1 },
    series: [
      { name: 'mAP50', type: 'line', showSymbol: false, data: ms.map((m) => m.map50) },
      { name: 'mAP50-95', type: 'line', showSymbol: false, data: ms.map((m) => m.map5095) },
      { name: 'Precision', type: 'line', showSymbol: false, lineStyle: { type: 'dashed' }, data: ms.map((m) => m.precision) },
      { name: 'Recall', type: 'line', showSymbol: false, lineStyle: { type: 'dashed' }, data: ms.map((m) => m.recall) },
    ],
  }
  const last = ms.at(-1)
  const ds = job.stats.dataset as Record<string, unknown> | undefined

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    try {
      await fn()
      notify.success(ok)
      void qc.invalidateQueries({ queryKey: ['job', id] })
    } catch (e) {
      notify.error('Amal bajarilmadi', e)
    }
  }

  return (
    <PageBody>
      <PageHeader
        title={
          <span className="flex items-center gap-3">
            Train #{id}: {job.product_name} <JobStatus status={job.status} />
          </span>
        }
        description={KIND_LABEL[job.kind]}
        actions={
          <>
            {['queued', 'running'].includes(job.status) && (
              <Button variant="outline" className="text-danger" onClick={() => void act(() => api.post(`/training/jobs/${id}/cancel`), "Bekor qilish so'raldi")}>
                <X /> Bekor qilish
              </Button>
            )}
            {['failed', 'cancelled'].includes(job.status) && job.kind !== 'autolabel' && (
              <>
                <Button variant="outline" onClick={async () => {
                  try {
                    const nj = await api.post<Job>(`/training/jobs/${id}/retry`, undefined, { query: { resume: true } })
                    navigate(`/training/${nj.id}`)
                  } catch (e) {
                    notify.error("Davom ettirib bo'lmadi", e)
                  }
                }}>
                  <StepForward /> Davom ettirish
                </Button>
                <Button onClick={async () => {
                  const nj = await api.post<Job>(`/training/jobs/${id}/retry`)
                  navigate(`/training/${nj.id}`)
                }}>
                  <RotateCcw /> Qayta boshlash
                </Button>
              </>
            )}
            {job.model_version_id && (
              <Button variant="outline" asChild>
                <Link to={`/models/${job.product_id}`}>Model versiyalari</Link>
              </Button>
            )}
          </>
        }
      />
      <div className="space-y-4">
        <Card>
          <CardContent className="space-y-4 pt-5">
            <Stepper job={job} />
            {job.error && <div className="rounded-md bg-danger-muted p-3 text-sm text-danger" role="alert">{job.error}</div>}
            {job.epochs > 0 && (
              <div className="space-y-1">
                <Progress value={(job.epoch / job.epochs) * 100} tone={job.status === 'failed' ? 'danger' : job.status === 'done' ? 'success' : 'primary'} />
                <div className="num text-sm text-muted-foreground">
                  {job.kind === 'autolabel' ? 'Rasm' : 'Epoch'} {job.epoch} / {job.epochs}
                </div>
              </div>
            )}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-7">
              <Info label="Boshlangan" value={fmtDateTime(job.started_at)} />
              <Info label="O'tgan vaqt" value={fmtDuration(elapsed)} />
              <Info label="Qolgan vaqt (ETA)" value={job.status === 'running' ? fmtDuration(job.eta_sec) : '—'} />
              <Info label="mAP50" value={last?.map50 != null ? last.map50.toFixed(3) : '—'} />
              <Info label="mAP50-95" value={last?.map5095 != null ? last.map5095.toFixed(3) : '—'} />
              <Info label="Dataset" value={ds ? `${ds.positives} + ${ds.negatives} neg` : '—'} />
              <Info label="GPU" value={gpu ? <span className="flex items-center gap-1"><Cpu className="size-3.5" />{gpu.util_pct}% · {Math.round(gpu.mem_used_mb / 1024 * 10) / 10}/{Math.round(gpu.mem_total_mb / 1024)} GB · {gpu.temp_c}°C</span> : '—'} />
            </div>
            {Array.isArray(ds?.warnings) && (ds!.warnings as string[]).length > 0 && (
              <div className="text-sm text-warning">{(ds!.warnings as string[]).join('; ')}</div>
            )}
          </CardContent>
        </Card>
        <Tabs value={tab} onValueChange={(v) => setTab(v as 'charts' | 'logs')}>
          <TabsList>
            <TabsTrigger value="charts">Grafiklar</TabsTrigger>
            <TabsTrigger value="logs">Loglar</TabsTrigger>
          </TabsList>
        </Tabs>
        {tab === 'charts' ? (
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Loss</CardTitle>
              </CardHeader>
              <CardContent>{ms.length ? <Chart option={lossOpt} height={240} /> : <p className="text-sm text-muted-foreground">Epoch natijalari kutilmoqda…</p>}</CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Aniqlik (val)</CardTitle>
              </CardHeader>
              <CardContent>{ms.length ? <Chart option={mapOpt} height={240} /> : <p className="text-sm text-muted-foreground">Epoch natijalari kutilmoqda…</p>}</CardContent>
            </Card>
          </div>
        ) : (
          <Card>
            <CardContent className="pt-4">
              <pre ref={logRef} className="max-h-[480px] overflow-auto rounded-md bg-video-bg p-3 font-mono text-xs leading-relaxed text-white/85">
                {log?.lines.join('\n') || 'Log yo\'q'}
              </pre>
            </CardContent>
          </Card>
        )}
      </div>
    </PageBody>
  )
}
