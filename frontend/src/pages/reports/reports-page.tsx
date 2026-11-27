import { Download, TriangleAlert } from 'lucide-react'
import { useMemo } from 'react'
import { Link } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { baseOption, Chart, useChartTheme } from '@/components/common/chart'
import { ErrorState } from '@/components/common/states'
import { HintIcon } from '@/components/common/term'
import { PageBody, PageHeader, useRouteTitle } from '@/components/layout/page'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useCameras } from '@/hooks/use-cameras'
import { useProducts } from '@/hooks/use-catalog'
import { param, useUrlState } from '@/hooks/use-url-state'
import { api } from '@/lib/api'
import { fmtDuration, fmtNum, fmtPct, fmtTime, todayISO } from '@/lib/format'

type CountsR = {
  total: number
  uncertain: number
  corrected: number
  cancelled: number
  by_day: { date: string; count: number }[]
  by_shift: { date: string; shift_id: number | null; shift: string; count: number }[]
  by_hour: { hour: string; count: number }[]
  by_product: { product_id: number | null; name: string; count: number; uncertain: number }[]
  by_camera: { camera_id: number; camera: string; count: number }[]
}
type EqCam = { camera_id: number; camera: string; running: number; stopped: number; unknown: number; utilization_pct: number | null; cycles: number; avg_cycle_sec: number | null; median_cycle_sec: number | null; micro_stops: number; durations: number[]; timeline: { state: string; start: string; end: string }[] }
type Gap = { camera: string; reason: string; reason_label: string; start: string; end: string; seconds: number; open: boolean }

function Kpi({ label, value, tone, hint }: { label: React.ReactNode; value: React.ReactNode; tone?: string; hint?: React.ReactNode }) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className={`num text-2xl font-semibold ${tone ?? ''}`}>{value}</div>
      {hint && <div className="text-2xs text-muted-foreground">{hint}</div>}
    </div>
  )
}

function Timeline({ items, from, to }: { items: EqCam['timeline']; from: number; to: number }) {
  const span = Math.max(1, to - from)
  return (
    <div className="relative h-5 overflow-hidden rounded bg-muted">
      {items.map((it, i) => {
        const a = (new Date(it.start).getTime() - from) / span
        const b = (new Date(it.end).getTime() - from) / span
        return (
          <span
            key={i}
            title={`${it.state === 'running' ? 'Ishladi' : it.state === 'stopped' ? "To'xtadi" : "Noma'lum"}: ${fmtTime(it.start)} — ${fmtTime(it.end)}`}
            className={`absolute top-0 h-full ${it.state === 'running' ? 'bg-success' : it.state === 'stopped' ? 'bg-danger' : 'bg-neutral'}`}
            style={{ left: `${a * 100}%`, width: `${Math.max(0.1, (b - a) * 100)}%` }}
          />
        )
      })}
    </div>
  )
}

export function ReportsPage() {
  const title = useRouteTitle()
  const t = useChartTheme()
  const today = todayISO()
  const [from, setFrom] = useUrlState('from', param.string, today)
  const [to, setTo] = useUrlState('to', param.string, today)
  const [shift, setShift] = useUrlState('shift_id', param.int, 0)
  const [camera, setCamera] = useUrlState('camera_id', param.int, 0)
  const [product, setProduct] = useUrlState('product_id', param.int, 0)
  const q = { from, to, shift_id: shift || undefined, camera_id: camera || undefined, product_id: product || undefined }
  const { data: cams } = useCameras()
  const { data: products } = useProducts()
  const { data: shiftsData } = useQuery({ queryKey: ['shifts'], queryFn: () => api.get<{ current: { id: number; name: string }[] }>('/shifts') })
  const counts = useQuery({ queryKey: ['rep-counts', q], queryFn: () => api.get<CountsR>('/reports/counts', { query: q }), refetchInterval: 30000 })
  const eq = useQuery({ queryKey: ['rep-eq', q], queryFn: () => api.get<{ cameras: EqCam[] }>('/reports/equipment', { query: q }), refetchInterval: 30000 })
  const gaps = useQuery({ queryKey: ['rep-gaps', q], queryFn: () => api.get<Gap[]>('/reports/gaps', { query: q }), refetchInterval: 30000 })
  const fromMs = new Date(`${from}T00:00:00+05:00`).getTime()
  const toMs = Math.min(Date.now(), new Date(`${to}T00:00:00+05:00`).getTime() + 86400000)

  const hourOpt = useMemo(() => {
    const d = counts.data?.by_hour ?? []
    const b = baseOption(t)
    const gapAreas = (gaps.data ?? []).map((g) => [{ xAxis: new Date(g.start).getTime(), itemStyle: { color: t.warning, opacity: 0.12 } }, { xAxis: new Date(g.end).getTime() }])
    return {
      ...b,
      xAxis: { ...b.xAxis, type: 'time', min: fromMs, max: toMs },
      yAxis: { ...b.yAxis, type: 'value', minInterval: 1 },
      series: [{ name: 'Sanoq', type: 'bar', barMaxWidth: 24, data: d.map((x) => [new Date(x.hour.replace(' ', 'T') + ':00+05:00').getTime() + 1800000, x.count]), markArea: { silent: true, data: gapAreas } }],
    }
  }, [counts.data, gaps.data, t, fromMs, toMs])

  const histOpt = (durs: number[]) => {
    if (!durs.length) return null
    const lo = Math.floor(Math.min(...durs))
    const hi = Math.ceil(Math.max(...durs))
    const n = Math.min(30, Math.max(5, hi - lo))
    const w = (hi - lo) / n || 1
    const bins = Array.from({ length: n }, (_, i) => ({ x: +(lo + i * w).toFixed(1), c: 0 }))
    durs.forEach((d) => (bins[Math.min(n - 1, Math.floor((d - lo) / w))].c += 1))
    const b = baseOption(t)
    return { ...b, grid: { ...b.grid, top: 10 }, legend: { show: false }, xAxis: { ...b.xAxis, type: 'category', data: bins.map((x) => `${x.x}s`) }, yAxis: { ...b.yAxis, type: 'value', minInterval: 1 }, series: [{ type: 'bar', data: bins.map((x) => x.c), itemStyle: { color: t.series[1] } }] }
  }

  const cq = new URLSearchParams({ day_from: from, day_to: to, ...(camera ? { camera_id: String(camera) } : {}), ...(shift ? { shift_id: String(shift) } : {}) }).toString()

  return (
    <PageBody>
      <PageHeader
        title={title}
        description="Smena sanasi bo'yicha. Bekor qilingan sanoqlar hisobga olinmaydi, tuzatilganlar — tuzatilgan mahsulot bilan."
        actions={
          <Button variant="outline" asChild>
            <a href={`/api/reports/export.xlsx?${new URLSearchParams(Object.entries(q).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])).toString()}`}>
              <Download /> Excel
            </a>
          </Button>
        }
      />
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Input type="date" value={from} onChange={(e) => setFrom(e.target.value)} className="h-8 w-36" aria-label="Sanadan" />
        <span className="text-muted-foreground">—</span>
        <Input type="date" value={to} onChange={(e) => setTo(e.target.value)} className="h-8 w-36" aria-label="Sanagacha" />
        <Select value={String(shift || 'all')} onValueChange={(v) => setShift(v === 'all' ? 0 : Number(v))}>
          <SelectTrigger className="h-8 w-40"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Barcha smenalar</SelectItem>
            {shiftsData?.current.map((s) => <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={String(camera || 'all')} onValueChange={(v) => setCamera(v === 'all' ? 0 : Number(v))}>
          <SelectTrigger className="h-8 w-40"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Barcha kameralar</SelectItem>
            {cams?.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={String(product || 'all')} onValueChange={(v) => setProduct(v === 'all' ? 0 : Number(v))}>
          <SelectTrigger className="h-8 w-48"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Barcha mahsulotlar</SelectItem>
            {products?.map((p) => <SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {(gaps.data?.length ?? 0) > 0 && (
        <div className="mb-4 flex items-center gap-2 rounded-lg bg-warning-muted px-3 py-2 text-sm text-warning">
          <TriangleAlert className="size-4" /> Ma'lumot to'liq emas: davrda {gaps.data!.length} ta sanalmagan oraliq bor (jami {fmtDuration(gaps.data!.reduce((a, g) => a + g.seconds, 0))}). <HintIcon id="coverageGap" />
        </div>
      )}

      <h2 className="mb-2 font-semibold">Mahsulot sanash</h2>
      {counts.error ? (
        <ErrorState error={counts.error} compact />
      ) : !counts.data ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <div className="mb-6 space-y-4">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Kpi label="Jami sanaldi" value={fmtNum(counts.data.total)} tone="text-success" />
            <Kpi label="Noaniq" value={fmtNum(counts.data.uncertain)} tone={counts.data.uncertain ? 'text-warning' : ''} hint={counts.data.uncertain ? <Link to={`/counts?status=uncertain&${cq}`} className="underline">ko'rib chiqish</Link> : undefined} />
            <Kpi label="Tuzatilgan" value={fmtNum(counts.data.corrected)} />
            <Kpi label="Bekor qilingan" value={fmtNum(counts.data.cancelled)} />
          </div>
          <div className="grid gap-4 lg:grid-cols-[1fr_380px]">
            <Card>
              <CardHeader><CardTitle className="text-base">Soatlar bo'yicha</CardTitle></CardHeader>
              <CardContent>{counts.data.by_hour.length ? <Chart option={hourOpt} height={240} /> : <p className="text-sm text-muted-foreground">Sanoq yo'q.</p>}</CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-base">Mahsulotlar</CardTitle></CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader><TableRow><TableHead>Mahsulot</TableHead><TableHead className="text-right">Soni</TableHead><TableHead className="text-right">Noaniq</TableHead></TableRow></TableHeader>
                  <TableBody>
                    {counts.data.by_product.map((p) => (
                      <TableRow key={p.product_id ?? 'x'}>
                        <TableCell><Link to={`/counts?${cq}${p.product_id ? `&product_id=${p.product_id}` : ''}`} className="hover:underline">{p.name}</Link></TableCell>
                        <TableCell className="num text-right font-medium">{p.count}</TableCell>
                        <TableCell className="num text-right">{p.uncertain || ''}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
          {counts.data.by_shift.length > 0 && (
            <Card>
              <CardHeader><CardTitle className="text-base">Smenalar bo'yicha</CardTitle></CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                {counts.data.by_shift.map((s) => (
                  <div key={`${s.date}-${s.shift_id}`} className="rounded-md bg-muted px-3 py-1.5 text-sm">
                    <span className="text-muted-foreground">{s.date} · {s.shift}:</span> <b className="num">{s.count}</b>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      <h2 className="mb-2 font-semibold">Uskuna ish vaqti</h2>
      {!eq.data ? (
        <Skeleton className="h-40 w-full" />
      ) : eq.data.cameras.length === 0 ? (
        <p className="mb-6 text-sm text-muted-foreground">Bu davrda uskuna ma'lumoti yo'q.</p>
      ) : (
        <div className="mb-6 space-y-3">
          {eq.data.cameras.map((c) => {
            const h = histOpt(c.durations)
            return (
              <Card key={c.camera_id}>
                <CardContent className="space-y-3 pt-4">
                  <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
                    <span className="font-semibold">{c.camera}</span>
                    <span className="text-sm">Ish vaqti: <b className="num">{fmtPct(c.utilization_pct, 1)}</b></span>
                    <span className="text-sm text-success">Ishladi: <b className="num">{fmtDuration(c.running)}</b></span>
                    <span className="text-sm text-danger">To'xtadi: <b className="num">{fmtDuration(c.stopped)}</b></span>
                    {c.unknown > 0 && <span className="text-sm text-neutral">Noma'lum: <b className="num">{fmtDuration(c.unknown)}</b></span>}
                    <span className="text-sm">Sikllar: <b className="num">{fmtNum(c.cycles)}</b></span>
                    <span className="text-sm">O'rtacha sikl: <b className="num">{c.avg_cycle_sec ?? '—'} s</b></span>
                    <span className="text-sm">Mikro-to'xtash: <b className="num">{c.micro_stops}</b></span>
                  </div>
                  <Timeline items={c.timeline} from={fromMs} to={toMs} />
                  {h && (
                    <div>
                      <div className="mb-1 text-xs text-muted-foreground">Sikl vaqti taqsimoti</div>
                      <Chart option={h} height={140} />
                    </div>
                  )}
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      <h2 className="mb-2 flex items-center gap-1 font-semibold">Sanalmagan oraliqlar <HintIcon id="coverageGap" /></h2>
      {gaps.data && gaps.data.length > 0 ? (
        <div className="overflow-hidden rounded-xl border bg-card">
          <Table>
            <TableHeader><TableRow><TableHead>Kamera</TableHead><TableHead>Sabab</TableHead><TableHead>Boshlanish</TableHead><TableHead>Tugash</TableHead><TableHead className="text-right">Davomiylik</TableHead></TableRow></TableHeader>
            <TableBody>
              {gaps.data.map((g, i) => (
                <TableRow key={i}>
                  <TableCell>{g.camera}</TableCell>
                  <TableCell>{g.reason_label}</TableCell>
                  <TableCell className="num text-sm">{fmtTime(g.start)}</TableCell>
                  <TableCell className="num text-sm">{g.open ? 'davom etmoqda' : fmtTime(g.end)}</TableCell>
                  <TableCell className="num text-right">{fmtDuration(g.seconds)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">Bu davrda sanalmagan oraliq yo'q.</p>
      )}
    </PageBody>
  )
}
