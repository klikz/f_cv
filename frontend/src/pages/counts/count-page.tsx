import { ArrowLeft, ArrowRight, Ban, Check, DatabaseZap, RotateCcw } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router'
import { useQueryClient } from '@tanstack/react-query'
import { ErrorState } from '@/components/common/states'
import { StatusBadge } from '@/components/common/status-badge'
import { PageBody } from '@/components/layout/page'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Kbd } from '@/components/ui/kbd'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { useProducts } from '@/hooks/use-catalog'
import { COUNT_STATUS_LABEL, useCountEvent, type CountEvent } from '@/hooks/use-counts'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { api } from '@/lib/api'
import { fmtDate, fmtDateTime } from '@/lib/format'
import { notify } from '@/lib/notify'
import { STATUS_KIND } from './counts-page'

export function CountPage() {
  const id = Number(useParams().eventId)
  const location = useLocation()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const sp = new URLSearchParams(location.search)
  const review = sp.get('review') === '1'
  const { data: e, error, refetch } = useCountEvent(id)
  const { data: products } = useProducts()
  const [ver, setVer] = useState(0)
  useDocumentTitle(`Sanoq #${id}`)

  const nextUncertain = async (): Promise<number | null> => {
    const r = await api.get<{ items: CountEvent[] }>('/counts', { query: { status: 'uncertain', limit: 2 } })
    return r.items.find((x) => x.id !== id)?.id ?? null
  }

  const act = async (body: { action: 'set_product' | 'cancel' | 'restore'; product_id?: number }) => {
    try {
      await api.post(`/counts/${id}/correct`, body)
      void qc.invalidateQueries({ queryKey: ['counts'] })
      await refetch()
      setVer((v) => v + 1)
      if (review) {
        const n = await nextUncertain()
        if (n) navigate(`/counts/${n}${location.search}`, { replace: true })
        else {
          notify.success("Barcha noaniq sanoqlar ko'rib chiqildi")
          navigate('/counts')
        }
      } else notify.success('Saqlandi')
    } catch (err) {
      notify.error("Saqlab bo'lmadi", err)
    }
  }
  const toDataset = async () => {
    try {
      const r = await api.post<{ image_id: number; created: boolean }>(`/counts/${id}/to-dataset`)
      notify.success(r.created ? "Datasetga qo'shildi" : 'Bu snapshot datasetda allaqachon bor')
    } catch (err) {
      notify.error("Qo'shib bo'lmadi", err)
    }
  }

  useEffect(() => {
    const h = (ev: KeyboardEvent) => {
      if (!e || (ev.target as HTMLElement).tagName === 'INPUT') return
      if (/^[1-9]$/.test(ev.key)) {
        const c = e.candidates[Number(ev.key) - 1]
        if (c) void act({ action: 'set_product', product_id: c.product_id })
      } else if (ev.key === 'Enter' && e.product_id) void act({ action: 'set_product', product_id: e.product_id })
      else if (ev.key === 'x' || ev.key === 'Delete') void act({ action: 'cancel' })
      else return
      ev.preventDefault()
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  })

  if (error) return <ErrorState error={error} onRetry={() => refetch()} />
  if (!e)
    return (
      <PageBody>
        <Skeleton className="aspect-video w-full" />
      </PageBody>
    )

  return (
    <PageBody>
      <div className="mb-3 flex items-center gap-2">
        <Button variant="ghost" size="sm" asChild>
          <Link to={`/counts${location.search.replace(/[?&]review=1/, '')}`}>
            <ArrowLeft /> Sanoqlar jurnali
          </Link>
        </Button>
        <h1 className="text-xl font-semibold">Sanoq #{e.id}</h1>
        <StatusBadge status={STATUS_KIND[e.status]} label={COUNT_STATUS_LABEL[e.status]} />
        {review && <span className="ml-auto text-sm text-muted-foreground">Tezkor ko'rib chiqish: <Kbd>1–9</Kbd> nomzod, <Kbd>Enter</Kbd> tasdiqlash, <Kbd>X</Kbd> bekor</span>}
      </div>
      <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
        <div className="overflow-hidden rounded-xl border bg-video-bg">
          {e.has_snapshot ? <img src={`/api/counts/${e.id}/snapshot?v=${ver}`} alt="Snapshot" className="w-full" /> : <div className="flex aspect-video items-center justify-center text-sm text-white/60">Snapshot yo'q</div>}
        </div>
        <div className="space-y-4">
          <Card>
            <CardContent className="space-y-2 pt-4 text-sm">
              <Row label="Mahsulot" value={<span className="font-semibold">{e.product_name ?? 'Noaniq'}</span>} />
              {e.original_product_id !== e.product_id && <Row label="Asl qiymat" value={e.original_product_name ?? 'Noaniq'} />}
              <Row label="Kamera" value={e.camera_name} />
              <Row label="Vaqt" value={fmtDateTime(e.ts)} />
              <Row label="Smena sanasi" value={fmtDate(e.shift_date)} />
              <Row label="Yo'nalish" value={e.direction === 'forward' ? 'Asosiy' : 'Teskari'} />
              <Row label="Ishonch" value={e.confidence != null ? `${Math.round(e.confidence * 100)}%` : '—'} />
              {e.corrected_at && <Row label="Tuzatilgan" value={fmtDateTime(e.corrected_at)} />}
            </CardContent>
          </Card>
          <Card>
            <CardContent className="space-y-3 pt-4">
              {e.candidates.length > 0 && (
                <div className="space-y-1">
                  <div className="text-xs font-semibold text-muted-foreground uppercase">Nomzodlar</div>
                  {e.candidates.map((c, i) => (
                    <button key={c.product_id} type="button" onClick={() => void act({ action: 'set_product', product_id: c.product_id })} className="flex w-full items-center gap-2 rounded-md border px-2 py-1.5 text-left text-sm hover:bg-accent">
                      <Kbd>{i + 1}</Kbd>
                      <span className="flex-1">{c.name}</span>
                      <span className="num text-muted-foreground">{Math.round(c.score * 100)}%</span>
                      {c.product_id === e.product_id && <Check className="size-4 text-success" />}
                    </button>
                  ))}
                </div>
              )}
              <div className="space-y-1">
                <div className="text-xs font-semibold text-muted-foreground uppercase">Boshqa mahsulot</div>
                <Select value="" onValueChange={(v) => void act({ action: 'set_product', product_id: Number(v) })}>
                  <SelectTrigger className="h-8 w-full"><SelectValue placeholder="Tanlang…" /></SelectTrigger>
                  <SelectContent>{products?.map((p) => <SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="flex flex-wrap gap-2">
                {e.status === 'cancelled' ? (
                  <Button size="sm" variant="outline" onClick={() => void act({ action: 'restore' })}><RotateCcw /> Tiklash</Button>
                ) : (
                  <Button size="sm" variant="outline" className="text-danger" onClick={() => void act({ action: 'cancel' })}><Ban /> Yolg'on sanoq <Kbd>X</Kbd></Button>
                )}
                <Button size="sm" variant="outline" onClick={toDataset} disabled={!e.product_id || e.status === 'uncertain' || e.status === 'cancelled'}>
                  <DatabaseZap /> Datasetga qo'shish
                </Button>
                {review && (
                  <Button size="sm" variant="ghost" onClick={async () => { const n = await nextUncertain(); if (n) navigate(`/counts/${n}${location.search}`) }}>
                    O'tkazib yuborish <ArrowRight />
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </PageBody>
  )
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-3">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right">{value}</span>
    </div>
  )
}
