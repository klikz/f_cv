import { CheckCheck, ChevronLeft, ChevronRight, Images, Loader2, Settings2, Sparkles, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router'
import { useQueryClient } from '@tanstack/react-query'
import { ReadinessBadge } from '@/components/common/readiness-badge'
import { EmptyState, ErrorState, CardGridSkeleton } from '@/components/common/states'
import { HintIcon } from '@/components/common/term'
import { PageBody, PageHeader, useRouteTitle } from '@/components/layout/page'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useCameras } from '@/hooks/use-cameras'
import { useImages, useProducts, useReadiness, type DatasetImage } from '@/hooks/use-catalog'
import { param, useUrlState } from '@/hooks/use-url-state'
import { api } from '@/lib/api'
import { fmtDateTime } from '@/lib/format'
import { notify } from '@/lib/notify'
import { cn } from '@/lib/utils'
import { SnapshotPanel } from './snapshot-panel'

const PAGE = 60
const STATUS_TABS = [
  { v: '', label: 'Hammasi', key: 'all' },
  { v: 'unlabeled', label: 'Belgilanmagan', key: 'unlabeled' },
  { v: 'auto', label: 'Avto', key: 'auto' },
  { v: 'confirmed', label: 'Tasdiqlangan', key: 'confirmed' },
  { v: 'empty', label: "Bo'sh (negativ)", key: 'empty' },
] as const

function Thumb({ img, href }: { img: DatasetImage; href: string }) {
  return (
    <Link to={href} className="group relative flex aspect-video items-center justify-center overflow-hidden rounded-lg border bg-video-bg focus-visible:ring-2 focus-visible:ring-ring">
      {/* rasm o'z nisbatida (ROI kesimi tik bo'lishi mumkin) — ramkalar rasmga mos turadi */}
      <div className="relative" style={img.width / img.height >= 16 / 9 ? { width: '100%', aspectRatio: `${img.width} / ${img.height}` } : { height: '100%', aspectRatio: `${img.width} / ${img.height}` }}>
        <img src={`/api/dataset/images/${img.id}/file`} alt="" loading="lazy" className="h-full w-full transition-transform group-hover:scale-[1.02]" />
        {img.annotations.map((a, i) => (
          <span
            key={i}
            className={cn('absolute border', a.status === 'auto' ? 'border-dashed border-warning' : 'border-success')}
            style={{ left: `${a.bbox[0] * 100}%`, top: `${a.bbox[1] * 100}%`, width: `${(a.bbox[2] - a.bbox[0]) * 100}%`, height: `${(a.bbox[3] - a.bbox[1]) * 100}%` }}
          />
        ))}
      </div>
      {img.crop && <span className="absolute top-1 left-1 rounded bg-black/60 px-1 text-2xs text-white">ROI</span>}
      <div className="absolute right-0 bottom-0 left-0 flex items-center justify-between bg-gradient-to-t from-black/70 to-transparent px-1.5 py-1 text-2xs text-white">
        <span>{fmtDateTime(img.captured_at)}</span>
        <span className="flex items-center gap-1">
          {img.is_empty ? 'bo\'sh' : img.annotations.length ? `${img.annotations.length} ta` : ''}
          <span className={cn('size-2 rounded-full', img.status === 'confirmed' ? 'bg-success' : img.status === 'auto' ? 'bg-warning' : 'bg-neutral')} />
        </span>
      </div>
    </Link>
  )
}

function AutoCollectDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const { data: cams } = useCameras()
  const qc = useQueryClient()
  const [cfg, setCfg] = useState<Record<string, { enabled: boolean; interval_sec: number; daily_limit: number }> | null>(null)
  const load = async () => setCfg(await api.get('/dataset/autocollect'))
  if (open && cfg === null) void load()
  const saveOne = async (cid: number) => {
    const v = cfg?.[cid] ?? { enabled: false, interval_sec: 10, daily_limit: 500 }
    try {
      await api.put(`/dataset/autocollect/${cid}`, v)
      notify.success('Saqlandi')
      void qc.invalidateQueries({ queryKey: ['images'] })
    } catch (e) {
      notify.error("Saqlab bo'lmadi", e)
    }
  }
  return (
    <Dialog open={open} onOpenChange={(o) => { onOpenChange(o); if (!o) setCfg(null) }}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Avto-yig'ish</DialogTitle>
          <DialogDescription>ROI hududida harakat bo'lganda har N soniyada snapshot olinadi (deyarli bir xil kadrlar o'tkazib yuboriladi).</DialogDescription>
        </DialogHeader>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Kamera</TableHead>
              <TableHead>Yoqilgan</TableHead>
              <TableHead>Har (s)</TableHead>
              <TableHead>Kunlik limit</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {cams?.map((c) => {
              const v = cfg?.[c.id] ?? { enabled: false, interval_sec: 10, daily_limit: 500 }
              const set = (patch: Partial<typeof v>) => setCfg({ ...(cfg ?? {}), [c.id]: { ...v, ...patch } })
              return (
                <TableRow key={c.id}>
                  <TableCell>{c.name}</TableCell>
                  <TableCell>
                    <Switch checked={v.enabled} onCheckedChange={(e) => set({ enabled: e })} />
                  </TableCell>
                  <TableCell>
                    <Input type="number" className="num h-7 w-20" value={v.interval_sec} onChange={(e) => set({ interval_sec: Number(e.target.value) })} />
                  </TableCell>
                  <TableCell>
                    <Input type="number" className="num h-7 w-24" value={v.daily_limit} onChange={(e) => set({ daily_limit: Number(e.target.value) })} />
                  </TableCell>
                  <TableCell>
                    <Button size="xs" variant="outline" onClick={() => void saveOne(c.id)}>
                      Saqlash
                    </Button>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </DialogContent>
    </Dialog>
  )
}

function AutolabelDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const { data: products } = useProducts()
  const [pid, setPid] = useState<string>('')
  const [conf, setConf] = useState(0.4)
  const [busy, setBusy] = useState(false)
  const run = async () => {
    setBusy(true)
    try {
      const j = await api.post<{ id: number }>('/dataset/autolabel', { product_id: Number(pid), conf })
      notify.success('Avto-belgilash navbatga qo\'yildi', `Job #${j.id} — natija "Avto" yorlig'ida`)
      onOpenChange(false)
    } catch (e) {
      notify.error("Boshlab bo'lmadi", e)
    } finally {
      setBusy(false)
    }
  }
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Avto-belgilash</DialogTitle>
          <DialogDescription>Mahsulot modeli belgilanmagan rasmlarga ramka taklif qiladi; siz tasdiqlaysiz yoki tuzatasiz. Model yo'q bo'lsa, avval ~30 rasmni qo'lda belgilab "tez qoralama" train qiling.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label>Mahsulot</Label>
            <Select value={pid} onValueChange={setPid}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Tanlang" />
              </SelectTrigger>
              <SelectContent>
                {products?.map((p) => (
                  <SelectItem key={p.id} value={String(p.id)}>
                    {p.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="conf">Minimal ishonch</Label>
            <Input id="conf" type="number" step={0.05} min={0.05} max={0.95} value={conf} onChange={(e) => setConf(Number(e.target.value))} className="num" />
          </div>
        </div>
        <DialogFooter>
          <Button onClick={run} disabled={!pid || busy}>
            {busy ? <Loader2 className="animate-spin" /> : <Sparkles />} Boshlash
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function DatasetPage() {
  const title = useRouteTitle()
  const location = useLocation()
  const qc = useQueryClient()
  const [camera, setCamera] = useUrlState('camera_id', param.int, 0)
  const [product, setProduct] = useUrlState('product_id', param.int, 0)
  const [status, setStatus] = useUrlState('status', param.string, '')
  const [day, setDay] = useUrlState('day', param.string, '')
  const [page, setPage] = useUrlState('page', param.int, 1)
  const [showReady, setShowReady] = useUrlState('ready', param.bool, true, { rememberKey: 'fcv.dataset.ready' })
  const filters = useMemo(() => ({ camera_id: camera || undefined, product_id: product || undefined, status: status || undefined, day: day || undefined }), [camera, product, status, day])
  const { data, isLoading, error, refetch, isFetching } = useImages(filters, (page - 1) * PAGE, PAGE)
  const { data: cams } = useCameras()
  const { data: products } = useProducts()
  const { data: ready } = useReadiness()
  const [acOpen, setAcOpen] = useState(false)
  const [alOpen, setAlOpen] = useState(false)
  const pages = Math.max(1, Math.ceil((data?.total ?? 0) / PAGE))
  const qs = location.search

  const confirmAuto = async () => {
    const r = await api.post<{ confirmed: number }>('/dataset/images/confirm-auto', undefined, { query: { product_id: product || undefined, min_conf: 0.7 } })
    notify.success(`${r.confirmed} ta rasm tasdiqlandi`, 'Ishonchi ≥70% bo\'lgan avto takliflar')
    void qc.invalidateQueries({ queryKey: ['images'] })
    void qc.invalidateQueries({ queryKey: ['readiness'] })
  }
  const firstUnlabeled = data?.items[0]

  return (
    <PageBody>
      <PageHeader
        title={title}
        description="Kamera tahlil oqimidan olingan rasmlar. Belgilash — har mahsulot ramka bilan; bo'sh rasmlar negativ namuna bo'ladi."
        actions={
          <>
            <Button variant="outline" onClick={() => setAcOpen(true)}>
              <Settings2 /> Avto-yig'ish
            </Button>
            <Button variant="outline" onClick={() => setAlOpen(true)}>
              <Sparkles /> Avto-belgilash
            </Button>
          </>
        }
      />

      <div className="mb-4 rounded-xl border bg-card">
        <div className="flex w-full items-center justify-between px-4 py-2.5 text-sm font-semibold">
          <span className="flex items-center gap-1">
            Tayyorlik indikatori <HintIcon id="readiness" />
          </span>
          <button type="button" className="text-xs font-normal text-muted-foreground hover:text-foreground" onClick={() => setShowReady(!showReady)} aria-expanded={showReady}>
            {showReady ? 'yashirish' : "ko'rsatish"}
          </button>
        </div>
        {showReady && ready && (
          <div className="max-h-72 overflow-auto border-t">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Mahsulot</TableHead>
                  <TableHead className="text-right">Tasdiqlangan</TableHead>
                  <TableHead className="text-right">Avto</TableHead>
                  <TableHead className="text-right">Qutili / qutisiz</TableHead>
                  <TableHead className="text-right">Tegib turgan</TableHead>
                  <TableHead className="text-right">Negativ</TableHead>
                  <TableHead>Kameralar</TableHead>
                  <TableHead>Holat</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {ready.map((r) => (
                  <TableRow key={r.product_id} className="cursor-pointer" onClick={() => setProduct(r.product_id)}>
                    <TableCell className="font-medium">{r.name}</TableCell>
                    <TableCell className="num text-right">{r.confirmed}</TableCell>
                    <TableCell className="num text-right">{r.auto}</TableCell>
                    <TableCell className="num text-right">
                      {r.boxed} / {r.unboxed}
                    </TableCell>
                    <TableCell className="num text-right">{r.touching}</TableCell>
                    <TableCell className="num text-right">{r.negatives}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{Object.entries(r.per_camera).map(([k, v]) => `${k}: ${v}`).join(', ') || '—'}</TableCell>
                    <TableCell>
                      <ReadinessBadge level={r.level} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Tabs value={status} onValueChange={(v) => { setStatus(v); setPage(1) }}>
          <TabsList>
            {STATUS_TABS.map((t) => (
              <TabsTrigger key={t.key} value={t.v} className="text-xs">
                {t.label}
                {data?.counts[t.key] != null && <span className="num ml-1 text-muted-foreground">{data.counts[t.key]}</span>}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
        <Select value={String(camera || 'all')} onValueChange={(v) => { setCamera(v === 'all' ? 0 : Number(v)); setPage(1) }}>
          <SelectTrigger className="h-8 w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Barcha kameralar</SelectItem>
            {cams?.map((c) => (
              <SelectItem key={c.id} value={String(c.id)}>
                {c.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={String(product || 'all')} onValueChange={(v) => { setProduct(v === 'all' ? 0 : Number(v)); setPage(1) }}>
          <SelectTrigger className="h-8 w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Barcha mahsulotlar</SelectItem>
            {products?.map((p) => (
              <SelectItem key={p.id} value={String(p.id)}>
                {p.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input type="date" value={day} onChange={(e) => { setDay(e.target.value); setPage(1) }} className="h-8 w-40" aria-label="Sana" />
        {(camera || product || day) && (
          <Button variant="ghost" size="sm" onClick={() => { setCamera(0); setProduct(0); setDay(''); setPage(1) }}>
            <X /> Filtrni tozalash
          </Button>
        )}
        <div className="ml-auto flex items-center gap-2">
          {status === 'auto' && (
            <Button size="sm" variant="outline" onClick={() => void confirmAuto()}>
              <CheckCheck /> Ishonchlilarini tasdiqlash
            </Button>
          )}
          {firstUnlabeled && (
            <Button size="sm" asChild>
              <Link to={`/dataset/annotate/${firstUnlabeled.id}${qs}`}>Belgilashni boshlash</Link>
            </Button>
          )}
        </div>
      </div>

      {camera ? (
        <SnapshotPanel key={camera} cameraId={camera} productId={product} productName={products?.find((p) => p.id === product)?.name} />
      ) : (
        <div className="mb-4 rounded-xl border border-dashed px-4 py-3 text-sm text-muted-foreground">Jonli ko'rinish va snapshot uchun kamerani tanlang.</div>
      )}

      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <CardGridSkeleton count={12} className="lg:grid-cols-6" />
      ) : !data?.items.length ? (
        <div className="rounded-xl border">
          <EmptyState
            icon={Images}
            title="Rasm yo'q"
            description={status || camera || product || day ? 'Filtr bo\'yicha rasm topilmadi.' : 'Kameradan snapshot oling yoki avto-yig\'ishni yoqing.'}
          />
        </div>
      ) : (
        <>
          <div className={cn('grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5 xl:grid-cols-6', isFetching && 'opacity-70')}>
            {data.items.map((img) => (
              <Thumb key={img.id} img={img} href={`/dataset/annotate/${img.id}${qs}`} />
            ))}
          </div>
          {pages > 1 && (
            <div className="mt-4 flex items-center justify-center gap-2">
              <Button variant="outline" size="icon-sm" disabled={page <= 1} onClick={() => setPage(page - 1)} aria-label="Oldingi">
                <ChevronLeft />
              </Button>
              <span className="num text-sm">
                {page} / {pages} <span className="text-muted-foreground">({data.total} ta)</span>
              </span>
              <Button variant="outline" size="icon-sm" disabled={page >= pages} onClick={() => setPage(page + 1)} aria-label="Keyingi">
                <ChevronRight />
              </Button>
            </div>
          )}
        </>
      )}
      <AutoCollectDialog open={acOpen} onOpenChange={setAcOpen} />
      <AutolabelDialog open={alOpen} onOpenChange={setAlOpen} />
      <Badge className="hidden" />
    </PageBody>
  )
}
