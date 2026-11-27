import { Activity, Cpu, Database, HardDrive, Send, Server, Unplug, type LucideIcon } from 'lucide-react'
import { Link } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useEffect, useMemo, useState } from 'react'
import { StatusBadge, type StatusKind } from '@/components/common/status-badge'
import { HintIcon } from '@/components/common/term'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Separator } from '@/components/ui/separator'
import { useHealth, type Health, type HealthStatus } from '@/hooks/use-health'
import { t } from '@/lib/i18n'
import { cn } from '@/lib/utils'

const toneCls: Record<HealthStatus, string> = {
  ok: 'text-success',
  warn: 'text-warning',
  error: 'text-danger',
}

function Indicator({
  icon: Icon,
  status,
  label,
  value,
}: {
  icon: LucideIcon
  status: HealthStatus
  label: string
  value?: string
}) {
  return (
    <span className="flex items-center gap-1.5 text-xs" title={label}>
      <Icon className={cn('size-3.5', toneCls[status])} aria-hidden />
      <span className="hidden text-muted-foreground xl:inline">{label}</span>
      {value && <span className="num font-medium">{value}</span>}
      <span className="sr-only">{t.status[status]}</span>
    </span>
  )
}

/** Server vaqti (Asia/Tashkent), server javobidagi vaqtga nisbatan siljish bilan har soniyada yangilanadi. */
function ServerClock({ serverTime, timezone }: { serverTime?: string; timezone: string }) {
  const [now, setNow] = useState(() => Date.now())
  // serverTime kelgan paytdagi farq (brauzer soati noto'g'ri bo'lsa ham server vaqti ko'rsatiladi)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const offset = useMemo(() => (serverTime ? new Date(serverTime).getTime() - Date.now() : 0), [serverTime])
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])
  const fmt = new Intl.DateTimeFormat('uz-UZ', {
    timeZone: timezone,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
  return (
    <span className="num text-xs font-medium tabular-nums" title={t.health.serverTime}>
      {fmt.format(new Date(now + offset))}
    </span>
  )
}

function toKind(s: HealthStatus): StatusKind {
  return s
}

function Details({ h }: { h: Health }) {
  const gpu = h.gpu.data.gpus?.[0]
  const rows: { label: string; status: HealthStatus; detail?: string | null; extra?: string }[] = [
    { label: t.health.db, status: h.db.status, detail: h.db.detail },
    { label: t.health.redis, status: h.redis.status, detail: h.redis.detail },
    {
      label: t.health.gpu,
      status: h.gpu.status,
      detail: h.gpu.detail,
      extra: gpu ? `${gpu.name} · ${gpu.util_pct}% · ${gpu.temp_c}°C · ${gpu.mem_used_mb}/${gpu.mem_total_mb} MB` : undefined,
    },
    {
      label: t.health.disk,
      status: h.disk.status,
      detail: h.disk.detail,
      extra:
        h.disk.data.free_gb !== undefined
          ? `${h.disk.data.free_gb} GB ${t.health.free} (${h.disk.data.free_pct}%)`
          : undefined,
    },
  ]
  return (
    <div className="space-y-3 text-sm">
      <div className="space-y-2">
        {rows.map((r) => (
          <div key={r.label} className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="font-medium">{r.label}</div>
              {(r.detail || r.extra) && <div className="text-xs text-muted-foreground">{r.detail ?? r.extra}</div>}
            </div>
            <StatusBadge status={toKind(r.status)} size="sm" />
          </div>
        ))}
      </div>
      <Separator />
      <div>
        <div className="mb-1.5 flex items-center gap-1 font-medium">
          {t.health.processes} <HintIcon id="heartbeat" />
        </div>
        <div className="grid grid-cols-1 gap-1">
          {h.processes.map((p) => (
            <div key={p.name} className="flex items-center justify-between gap-2 text-xs">
              <span className="truncate">{t.processes[p.name] ?? p.name}</span>
              <StatusBadge
                status={toKind(p.status)}
                variant="inline"
                size="sm"
                label={p.status === 'ok' ? t.status.ok : t.health.notResponding}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function TrainTelegram() {
  const { data: tr } = useQuery({ queryKey: ['training-current'], queryFn: () => api.get<{ job_id?: number; stage?: string; epoch?: number; epochs?: number }>('/training/current'), refetchInterval: 4000 })
  const { data: tg } = useQuery({ queryKey: ['tg-status-mini'], queryFn: () => api.get<{ state: string; label: string }>('/telegram/status'), refetchInterval: 15000 })
  return (
    <>
      {tr?.job_id && (
        <Link to={`/training/${tr.job_id}`} className="flex items-center gap-1 rounded-md bg-info-muted px-2 py-1 text-xs text-info" title="Train ketmoqda — mahsulot sanash to'xtatilgan">
          <Activity className="size-3.5 animate-pulse" /> Train ketmoqda{tr.epochs ? ` ${tr.epoch}/${tr.epochs}` : ''}
        </Link>
      )}
      {tg && tg.state !== 'no_token' && (
        <Link to="/telegram" title={`Telegram: ${tg.label}`} className="flex items-center">
          <Send className={cn('size-3.5', tg.state === 'connected' ? 'text-success' : 'text-danger')} />
          <span className="sr-only">Telegram: {tg.label}</span>
        </Link>
      )}
    </>
  )
}

/** Yuqori paneldagi umumiy holat ko'rsatkichlari (`/api/health` asosida). */
export function HealthIndicators() {
  const { data, isError } = useHealth()

  if (isError || !data) {
    return (
      <div className="flex items-center gap-3">
        {isError ? (
          <span className="flex items-center gap-1.5 text-xs text-danger" role="status">
            <Unplug className="size-3.5" /> {t.health.unreachable}
          </span>
        ) : (
          <span className="text-xs text-muted-foreground">{t.common.loading}</span>
        )}
      </div>
    )
  }

  const gpu = data.gpu.data.gpus?.[0]
  const procBad = data.processes.filter((p) => p.status !== 'ok').length
  const procStatus: HealthStatus = procBad === 0 ? 'ok' : 'error'
  const problems =
    [data.db, data.redis, data.gpu, data.disk].filter((c) => c.status !== 'ok').length + procBad

  return (
    <div className="flex items-center gap-3">
      <TrainTelegram />
      <Popover>
        <PopoverTrigger asChild>
          <button
            type="button"
            className="flex h-8 items-center gap-3 rounded-md px-2 hover:bg-accent"
            aria-label={t.health.title}
          >
            <Indicator icon={Database} status={data.db.status === 'ok' && data.redis.status === 'ok' ? 'ok' : 'error'} label={t.health.db} />
            <Indicator icon={Cpu} status={data.gpu.status} label={t.health.gpu} value={gpu ? `${gpu.util_pct}%` : undefined} />
            <Indicator
              icon={HardDrive}
              status={data.disk.status}
              label={t.health.disk}
              value={data.disk.data.free_pct !== undefined ? `${Math.round(100 - data.disk.data.free_pct)}%` : undefined}
            />
            <Indicator icon={Server} status={procStatus} label={t.health.processes} />
            <span className={cn('hidden text-xs font-medium lg:inline', problems ? 'text-danger' : 'text-success')}>
              {problems ? t.health.problems(problems) : t.health.allOk}
            </span>
          </button>
        </PopoverTrigger>
        <PopoverContent align="end" className="w-80">
          <div className="mb-2 font-semibold">{t.health.title}</div>
          <Details h={data} />
        </PopoverContent>
      </Popover>
      <Separator orientation="vertical" className="h-4" />
      <ServerClock serverTime={data.server_time} timezone={data.timezone} />
    </div>
  )
}
