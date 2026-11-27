import { Cpu, Loader2, Plus, Ruler, X } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Progress } from '@/components/common/progress'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { api } from '@/lib/api'
import { notify } from '@/lib/notify'

type CamProduct = { product_id: number; name: string; code: string; model_version_id: number | null; active_version: number | null; engine_ready: boolean; size_min: number | null; size_max: number | null }
type Out = { items: CamProduct[]; available: CamProduct[]; load: { per_camera: Record<string, number>; total: number; budget: number; rps: number; latency_ms: number; fps_scale: number; vram_mb: number } }

/** Faol mahsulotlar (faqat faol modeli borlar) + GPU yuklama ko'rsatkichi. */
export function CountingProducts({ cameraId }: { cameraId: number }) {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['cam-products', cameraId], queryFn: () => api.get<Out>(`/cameras/${cameraId}/counting/products`), refetchInterval: 5000 })
  const [busy, setBusy] = useState(false)

  const save = async (items: CamProduct[]) => {
    setBusy(true)
    try {
      const out = await api.put<Out>(`/cameras/${cameraId}/counting/products`, { items })
      qc.setQueryData(['cam-products', cameraId], out)
      notify.success('Mahsulotlar saqlandi')
    } catch (e) {
      notify.error("Saqlab bo'lmadi", e)
    } finally {
      setBusy(false)
    }
  }
  const learn = async () => {
    try {
      const r = await api.post<{ learned: Record<string, unknown> }>(`/cameras/${cameraId}/counting/learn-sizes`)
      const n = Object.keys(r.learned).length
      notify.success(n ? `${n} ta mahsulot uchun o'lcham oralig'i o'rganildi` : "Yetarli tasdiqlangan sanoq yo'q (har mahsulotga ≥20)")
      void qc.invalidateQueries({ queryKey: ['cam-products', cameraId] })
    } catch (e) {
      notify.error("O'rganib bo'lmadi", e)
    }
  }

  if (isLoading || !data) return <Loader2 className="size-4 animate-spin text-muted-foreground" />
  const myLoad = data.load.per_camera[String(cameraId)] ?? 0
  const pct = data.load.budget ? (data.load.total / data.load.budget) * 100 : 0

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        {data.items.length === 0 && <p className="text-sm text-muted-foreground">Mahsulot tanlanmagan — sanash ishlamaydi.</p>}
        {data.items.map((p) => (
          <div key={p.product_id} className="flex items-center gap-2 rounded-md border px-2 py-1.5 text-sm">
            <span className="flex-1 truncate">{p.name}</span>
            <span className="text-xs text-muted-foreground">v{p.active_version ?? '—'}</span>
            {p.size_min != null && <Ruler className="size-3.5 text-success" aria-label="O'lcham oralig'i o'rganilgan" />}
            <Button size="icon-xs" variant="ghost" disabled={busy} onClick={() => void save(data.items.filter((x) => x.product_id !== p.product_id))} aria-label="Olib tashlash">
              <X />
            </Button>
          </div>
        ))}
      </div>
      {data.available.length > 0 ? (
        <Select
          value=""
          disabled={busy}
          onValueChange={(v) => {
            const p = data.available.find((x) => String(x.product_id) === v)
            if (p) void save([...data.items, p])
          }}
        >
          <SelectTrigger className="h-8 w-full">
            <Plus className="size-4" />
            <SelectValue placeholder="Mahsulot qo'shish (darhol saqlanadi)" />
          </SelectTrigger>
          <SelectContent>
            {data.available.map((p) => (
              <SelectItem key={p.product_id} value={String(p.product_id)}>
                {p.name} (v{p.active_version})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      ) : (
        data.items.length === 0 && (
          <p className="text-xs text-muted-foreground">
            Faol modeli bor mahsulot yo'q. <Link to="/models" className="text-primary underline">Modellar</Link> sahifasida versiyani faollashtiring.
          </p>
        )
      )}
      <Button size="xs" variant="ghost" onClick={learn}>
        <Ruler /> O'lcham oralig'ini o'rganish
      </Button>
      <div className="space-y-1.5 rounded-lg bg-muted/60 p-2.5 text-xs">
        <div className="flex items-center gap-1 font-medium">
          <Cpu className="size-3.5" /> GPU yuklama
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Shu kamera</span>
          <span className="num">{myLoad} inference/s</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Umumiy / byudjet</span>
          <span className="num">
            {data.load.total} / {data.load.budget}
          </span>
        </div>
        <Progress value={pct} tone={pct > 90 ? 'danger' : pct > 70 ? 'warning' : 'success'} />
        <div className="flex justify-between text-muted-foreground">
          <span>Haqiqiy: {data.load.rps}/s · {data.load.latency_ms} ms</span>
          <span>VRAM {Math.round(data.load.vram_mb)} MB</span>
        </div>
        {data.load.fps_scale < 1 && <div className="text-warning">Yuklama yuqori — inference fps avtomatik {Math.round(data.load.fps_scale * 100)}% gacha pasaytirildi</div>}
      </div>
    </div>
  )
}
