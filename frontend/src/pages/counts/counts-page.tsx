import { ChevronLeft, ChevronRight, CircleHelp, ListChecks, Plus, Trash2, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { StatusBadge, type StatusKind } from '@/components/common/status-badge'
import { EmptyState, ErrorState, CardGridSkeleton } from '@/components/common/states'
import { HintIcon } from '@/components/common/term'
import { PageBody, PageHeader, useRouteTitle } from '@/components/layout/page'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useCameras } from '@/hooks/use-cameras'
import { useProducts } from '@/hooks/use-catalog'
import { COUNT_STATUS_LABEL, useCountEvents, type CountEvent } from '@/hooks/use-counts'
import { param, useUrlState } from '@/hooks/use-url-state'
import { api } from '@/lib/api'
import { fmtDateTime, fmtTime } from '@/lib/format'
import { notify } from '@/lib/notify'
import { cn } from '@/lib/utils'

const PAGE = 48
export const STATUS_KIND: Record<CountEvent['status'], StatusKind> = { confirmed: 'ok', uncertain: 'uncertain', corrected: 'running', cancelled: 'disabled' }

function EventCard({ e, href }: { e: CountEvent; href: string }) {
  return (
    <Link to={href} className={cn('group block overflow-hidden rounded-lg border bg-card focus-visible:ring-2 focus-visible:ring-ring', e.status === 'cancelled' && 'opacity-60')}>
      <div className="relative aspect-video bg-video-bg">
        {e.has_snapshot && <img src={`/api/counts/${e.id}/snapshot?raw=1`} alt="" loading="lazy" className="h-full w-full object-cover" />}
        {e.bbox && (
          <span
            className={cn('absolute border-2', e.status === 'uncertain' ? 'border-warning' : 'border-success')}
            style={{ left: `${e.bbox[0] * 100}%`, top: `${e.bbox[1] * 100}%`, width: `${(e.bbox[2] - e.bbox[0]) * 100}%`, height: `${(e.bbox[3] - e.bbox[1]) * 100}%` }}
          />
        )}
        <span className="absolute top-1 right-1">
          <StatusBadge status={STATUS_KIND[e.status]} label={COUNT_STATUS_LABEL[e.status]} size="sm" className="bg-black/60" />
        </span>
      </div>
      <div className="flex items-center justify-between gap-2 px-2 py-1.5">
        <div className="min-w-0">
          <div className="truncate text-sm font-medium">{e.product_name ?? 'Noaniq'}</div>
          <div className="truncate text-2xs text-muted-foreground">
            {e.camera_name} {e.direction === 'reverse' && '· teskari'}
          </div>
        </div>
        <span className="num shrink-0 text-xs text-muted-foreground">{fmtTime(e.ts)}</span>
      </div>
    </Link>
  )
}

type Manual = { id: number; camera_id: number; camera_name: string | null; product_id: number | null; product_name: string | null; start_ts: string; end_ts: string; count: number; system_count: number; diff: number; accuracy_pct: number | null; note: string | null }

function AccuracyTab() {
  const qc = useQueryClient()
  const { data: cams } = useCameras()
  const { data: products } = useProducts()
  const { data: rows } = useQuery({ queryKey: ['manual-counts'], queryFn: () => api.get<Manual[]>('/manual-counts') })
  const [f, setF] = useState({ camera_id: '', product_id: 'all', start: '', end: '', count: '' })
  const add = async () => {
    try {
      await api.post('/manual-counts', {
        camera_id: Number(f.camera_id),
        product_id: f.product_id === 'all' ? null : Number(f.product_id),
        start_ts: new Date(f.start).toISOString(),
        end_ts: new Date(f.end).toISOString(),
        count: Number(f.count),
      })
      setF({ ...f, count: '' })
      void qc.invalidateQueries({ queryKey: ['manual-counts'] })
    } catch (e) {
      notify.error("Qo'shib bo'lmadi", e)
    }
  }
  const totals = (rows ?? []).reduce((a, r) => ({ m: a.m + r.count, s: a.s + r.system_count }), { m: 0, s: 0 })
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Qo'lda sanoq bilan solishtirish</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-3 text-sm text-muted-foreground">Vaqt oralig'ida haqiqatda o'tgan mahsulotlar sonini kiriting — tizim o'z hisobini ko'rsatadi. O'tkazib yuborilgan sanoqlar shu orqali aniqlanadi.</p>
          <div className="grid gap-3 sm:grid-cols-6">
            <div className="space-y-1 sm:col-span-1">
              <Label>Kamera</Label>
              <Select value={f.camera_id} onValueChange={(v) => setF({ ...f, camera_id: v })}>
                <SelectTrigger className="h-8 w-full"><SelectValue placeholder="Tanlang" /></SelectTrigger>
                <SelectContent>{cams?.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-1 sm:col-span-1">
              <Label>Mahsulot</Label>
              <Select value={f.product_id} onValueChange={(v) => setF({ ...f, product_id: v })}>
                <SelectTrigger className="h-8 w-full"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Hammasi</SelectItem>
                  {products?.map((p) => <SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1"><Label>Boshlanish</Label><Input type="datetime-local" className="h-8" value={f.start} onChange={(e) => setF({ ...f, start: e.target.value })} /></div>
            <div className="space-y-1"><Label>Tugash</Label><Input type="datetime-local" className="h-8" value={f.end} onChange={(e) => setF({ ...f, end: e.target.value })} /></div>
            <div className="space-y-1"><Label>Qo'lda sanaldi</Label><Input type="number" className="num h-8" value={f.count} onChange={(e) => setF({ ...f, count: e.target.value })} /></div>
            <div className="flex items-end"><Button size="sm" className="w-full" onClick={add} disabled={!f.camera_id || !f.start || !f.end || f.count === ''}><Plus /> Qo'shish</Button></div>
          </div>
        </CardContent>
      </Card>
      {rows && rows.length > 0 && (
        <div className="overflow-hidden rounded-xl border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Kamera</TableHead><TableHead>Mahsulot</TableHead><TableHead>Oraliq</TableHead>
                <TableHead className="text-right">Qo'lda</TableHead><TableHead className="text-right">Tizim</TableHead>
                <TableHead className="text-right">Farq</TableHead><TableHead className="text-right">Aniqlik</TableHead><TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((r) => (
                <TableRow key={r.id}>
                  <TableCell>{r.camera_name}</TableCell>
                  <TableCell>{r.product_name ?? 'Hammasi'}</TableCell>
                  <TableCell className="text-xs">{fmtDateTime(r.start_ts)} — {fmtTime(r.end_ts)}</TableCell>
                  <TableCell className="num text-right">{r.count}</TableCell>
                  <TableCell className="num text-right">{r.system_count}</TableCell>
                  <TableCell className={cn('num text-right', r.diff !== 0 && 'text-warning')}>{r.diff > 0 ? `+${r.diff}` : r.diff}</TableCell>
                  <TableCell className={cn('num text-right font-semibold', (r.accuracy_pct ?? 0) >= 99 ? 'text-success' : 'text-warning')}>{r.accuracy_pct != null ? `${r.accuracy_pct}%` : '—'}</TableCell>
                  <TableCell>
                    <Button size="icon-xs" variant="ghost" onClick={async () => { await api.delete(`/manual-counts/${r.id}`); void qc.invalidateQueries({ queryKey: ['manual-counts'] }) }} aria-label="O'chirish"><Trash2 /></Button>
                  </TableCell>
                </TableRow>
              ))}
              <TableRow>
                <TableCell colSpan={3} className="font-medium">Jami</TableCell>
                <TableCell className="num text-right font-medium">{totals.m}</TableCell>
                <TableCell className="num text-right font-medium">{totals.s}</TableCell>
                <TableCell className="num text-right">{totals.s - totals.m}</TableCell>
                <TableCell className="num text-right font-semibold">{totals.m ? `${(100 - (Math.abs(totals.s - totals.m) / totals.m) * 100).toFixed(2)}%` : '—'}</TableCell>
                <TableCell />
              </TableRow>
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}

export function CountsPage() {
  const title = useRouteTitle()
  const location = useLocation()
  const [tab, setTab] = useUrlState('tab', param.oneOf(['events', 'accuracy'] as const), 'events')
  const [camera, setCamera] = useUrlState('camera_id', param.int, 0)
  const [product, setProduct] = useUrlState('product_id', param.int, 0)
  const [status, setStatus] = useUrlState('status', param.string, '')
  const [from, setFrom] = useUrlState('day_from', param.string, '')
  const [to, setTo] = useUrlState('day_to', param.string, '')
  const [shift, setShift] = useUrlState('shift_id', param.int, 0)
  const [page, setPage] = useUrlState('page', param.int, 1)
  const filters = useMemo(() => ({ camera_id: camera || undefined, product_id: product || undefined, status: status || undefined, day_from: from || undefined, day_to: to || undefined, shift_id: shift || undefined }), [camera, product, status, from, to, shift])
  const { data, isLoading, error, refetch } = useCountEvents(filters, (page - 1) * PAGE, PAGE)
  const { data: cams } = useCameras()
  const { data: products } = useProducts()
  const pages = Math.max(1, Math.ceil((data?.total ?? 0) / PAGE))
  const qs = location.search
  const firstUncertain = status === 'uncertain' ? data?.items[0] : undefined

  return (
    <PageBody>
      <PageHeader
        title={title}
        description="Har sanoq snapshot bilan. Noaniq sanoqlarni to'g'rilang, yolg'on sanoqlarni bekor qiling — asl qiymat saqlanadi."
        actions={
          (data?.summary.uncertain ?? 0) > 0 && (
            <Button asChild>
              <Link to={`/counts?status=uncertain`} onClick={() => setPage(1)}>
                <CircleHelp /> Noaniqlarni ko'rib chiqish ({data?.summary.uncertain})
              </Link>
            </Button>
          )
        }
      />
      <Tabs value={tab} onValueChange={(v) => setTab(v as 'events' | 'accuracy')} className="mb-3">
        <TabsList>
          <TabsTrigger value="events">Sanoqlar</TabsTrigger>
          <TabsTrigger value="accuracy">Aniqlikni tekshirish</TabsTrigger>
        </TabsList>
      </Tabs>
      {tab === 'accuracy' ? (
        <AccuracyTab />
      ) : (
        <>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <Tabs value={status} onValueChange={(v) => { setStatus(v); setPage(1) }}>
              <TabsList>
                <TabsTrigger value="" className="text-xs">Hammasi</TabsTrigger>
                {(['confirmed', 'uncertain', 'corrected', 'cancelled'] as const).map((s) => (
                  <TabsTrigger key={s} value={s} className="text-xs">
                    {COUNT_STATUS_LABEL[s]} {data?.summary[s] != null && <span className="num ml-1 text-muted-foreground">{data.summary[s]}</span>}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
            <Select value={String(camera || 'all')} onValueChange={(v) => { setCamera(v === 'all' ? 0 : Number(v)); setPage(1) }}>
              <SelectTrigger className="h-8 w-40"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Barcha kameralar</SelectItem>
                {cams?.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={String(product || 'all')} onValueChange={(v) => { setProduct(v === 'all' ? 0 : Number(v)); setPage(1) }}>
              <SelectTrigger className="h-8 w-48"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Barcha mahsulotlar</SelectItem>
                {products?.map((p) => <SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>)}
              </SelectContent>
            </Select>
            <Input type="date" value={from} onChange={(e) => { setFrom(e.target.value); setPage(1) }} className="h-8 w-36" aria-label="Sanadan" />
            <span className="text-muted-foreground">—</span>
            <Input type="date" value={to} onChange={(e) => { setTo(e.target.value); setPage(1) }} className="h-8 w-36" aria-label="Sanagacha" />
            <Select value={String(shift || 'all')} onValueChange={(v) => { setShift(v === 'all' ? 0 : Number(v)); setPage(1) }}>
              <SelectTrigger className="h-8 w-36"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Barcha smenalar</SelectItem>
                <ShiftOptions />
              </SelectContent>
            </Select>
            {(camera || product || from || to || shift) ? (
              <Button variant="ghost" size="sm" onClick={() => { setCamera(0); setProduct(0); setFrom(''); setTo(''); setShift(0); setPage(1) }}>
                <X /> Tozalash
              </Button>
            ) : null}
            {firstUncertain && (
              <Button size="sm" className="ml-auto" asChild>
                <Link to={`/counts/${firstUncertain.id}${qs}${qs ? '&' : '?'}review=1`}>Tezkor ko'rib chiqish <HintIcon id="uncertainCount" /></Link>
              </Button>
            )}
          </div>
          {error ? (
            <ErrorState error={error} onRetry={() => refetch()} />
          ) : isLoading ? (
            <CardGridSkeleton count={12} className="lg:grid-cols-6" />
          ) : !data?.items.length ? (
            <div className="rounded-xl border">
              <EmptyState icon={ListChecks} title="Sanoq yo'q" description="Filtr bo'yicha sanoq topilmadi yoki sanash hali ishlamagan." />
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5 xl:grid-cols-6">
                {data.items.map((e) => <EventCard key={e.id} e={e} href={`/counts/${e.id}${qs}`} />)}
              </div>
              {pages > 1 && (
                <div className="mt-4 flex items-center justify-center gap-2">
                  <Button variant="outline" size="icon-sm" disabled={page <= 1} onClick={() => setPage(page - 1)} aria-label="Oldingi"><ChevronLeft /></Button>
                  <span className="num text-sm">{page} / {pages} <span className="text-muted-foreground">({data.total} ta)</span></span>
                  <Button variant="outline" size="icon-sm" disabled={page >= pages} onClick={() => setPage(page + 1)} aria-label="Keyingi"><ChevronRight /></Button>
                </div>
              )}
            </>
          )}
        </>
      )}
    </PageBody>
  )
}

function ShiftOptions() {
  const { data } = useQuery({ queryKey: ['shifts-current'], queryFn: () => api.get<{ current: { id: number; name: string }[] }>('/shifts') })
  return <>{data?.current.map((s) => <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>)}</>
}
