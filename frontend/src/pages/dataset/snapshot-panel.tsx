import { Camera as CameraIcon, Crop, Loader2, Maximize, VideoOff } from 'lucide-react'
import { useCallback, useRef, useState } from 'react'
import { Link } from 'react-router'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Kbd } from '@/components/ui/kbd'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { useCameraFeed } from '@/components/video/use-feed'
import { VideoCanvas } from '@/components/video/video-canvas'
import type { Rect } from '@/components/video/overlay'
import { useHotkeys } from '@/hooks/use-hotkeys'
import { api } from '@/lib/api'
import { notify } from '@/lib/notify'
import { storage } from '@/lib/storage'
import type { Point } from '@/lib/types'

type Mode = 'roi' | 'full'
type RoiInfo = { roi: Point[] | null; crop: [number, number, number, number] | null }
const MODE_KEY = 'fcv.dataset.snapMode'

/** Tanlangan kamera jonli ko'rinishi (tahlil oqimi) + snapshot: ROI kesimi yoki butun kadr. */
export function SnapshotPanel({ cameraId, productId, productName }: { cameraId: number; productId: number; productName?: string }) {
  const qc = useQueryClient()
  const { hub } = useCameraFeed(cameraId, 'analysis')
  const { data: roi } = useQuery({ queryKey: ['dataset-roi', cameraId], queryFn: ({ signal }) => api.get<RoiInfo>(`/dataset/roi/${cameraId}`, { signal }) })
  const hasRoi = !!roi?.roi?.length
  const [modePref, setModePref] = useState<Mode>(() => storage.get<Mode>(MODE_KEY) ?? 'roi')
  const mode: Mode = hasRoi ? modePref : 'full'
  const [rect, setRect] = useState<Rect | null>(null)
  const [stale, setStale] = useState(false)
  const [busy, setBusy] = useState(false)
  const [flash, setFlash] = useState(0)
  const rectRef = useRef<Rect | null>(null)

  const onRect = useCallback((r: Rect) => {
    const p = rectRef.current
    if (p && p.x === r.x && p.y === r.y && p.w === r.w && p.h === r.h) return
    rectRef.current = r
    setRect(r)
  }, [])

  const setMode = (m: Mode) => {
    setModePref(m)
    storage.set(MODE_KEY, m)
  }

  const snapshot = async () => {
    if (busy) return
    setBusy(true)
    try {
      await api.post('/dataset/snapshot', { camera_id: cameraId, product_id: productId || undefined, mode }, { timeoutMs: 30000 })
      setFlash((n) => n + 1)
      notify.success('Snapshot olindi', mode === 'roi' ? 'ROI kesimi saqlandi' : 'Butun kadr saqlandi')
      void qc.invalidateQueries({ queryKey: ['images'] })
    } catch (e) {
      notify.error("Snapshot olib bo'lmadi", e)
    } finally {
      setBusy(false)
    }
  }
  useHotkeys([{ combo: 's', handler: () => void snapshot() }])

  const pts = roi?.roi ?? []
  const px = (p: Point) => `${(rect?.x ?? 0) + p[0] * (rect?.w ?? 0)},${(rect?.y ?? 0) + p[1] * (rect?.h ?? 0)}`

  return (
    <div className="mb-4 grid gap-3 rounded-xl border bg-card p-3 lg:grid-cols-[minmax(0,1fr)_260px]">
      <div className="relative aspect-video overflow-hidden rounded-lg">
        <VideoCanvas hub={hub} cameraId={cameraId} onRect={onRect} onStale={setStale}>
          {rect && hasRoi && (
            <svg className="pointer-events-none absolute inset-0 h-full w-full">
              {mode === 'roi' && pts.length >= 3 && (
                /* faqat ROI ichi saqlanadi — tashqarisi xiralashtiriladi */
                <path fillRule="evenodd" className="fill-black/55" d={`M${rect.x},${rect.y}h${rect.w}v${rect.h}h${-rect.w}z M${pts.map(px).join(' L')}z`} />
              )}
              <polygon points={pts.map(px).join(' ')} fill="var(--overlay-roi)" fillOpacity={0.08} stroke="var(--overlay-roi)" strokeWidth={2} strokeDasharray="6 4" />
            </svg>
          )}
          {flash > 0 && <div key={flash} className="pointer-events-none absolute inset-0 animate-out bg-white/50 fade-out duration-500 fill-mode-forwards" />}
          {stale && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-sm text-white/80">
              <VideoOff className="size-6" />
              Kadr kelmayapti — kamera ulanishini tekshiring
            </div>
          )}
        </VideoCanvas>
      </div>

      <div className="flex flex-col gap-3 text-sm">
        <div>
          <div className="mb-1.5 text-xs font-medium text-muted-foreground">Snapshot hududi</div>
          <ToggleGroup type="single" variant="outline" value={mode} onValueChange={(v) => v && setMode(v as Mode)} className="w-full">
            <ToggleGroupItem value="roi" disabled={!hasRoi} className="flex-1">
              <Crop /> ROI
            </ToggleGroupItem>
            <ToggleGroupItem value="full" className="flex-1">
              <Maximize /> Butun kadr
            </ToggleGroupItem>
          </ToggleGroup>
          {roi && !hasRoi && (
            <p className="mt-1.5 text-xs text-muted-foreground">
              ROI chizilmagan.{' '}
              <Link to={`/cameras/${cameraId}/counting`} className="text-primary underline">
                Sanash sozlamasida chizing
              </Link>
            </p>
          )}
          {hasRoi && mode === 'roi' && <p className="mt-1.5 text-xs text-muted-foreground">Faqat ROI ichi saqlanadi (tashqarisi kulrang) — model ham aynan shuni ko'radi.</p>}
        </div>

        <div>
          <div className="mb-1 text-xs font-medium text-muted-foreground">Mahsulot</div>
          {productId ? (
            <div className="font-medium">{productName ?? `#${productId}`}</div>
          ) : (
            <p className="text-xs text-warning">Mahsulot tanlanmagan — rasm hech qaysi mahsulotga biriktirilmaydi. Yuqoridagi filtrdan mahsulotni tanlang.</p>
          )}
        </div>

        <Button className="mt-auto w-full" onClick={() => void snapshot()} disabled={busy}>
          {busy ? <Loader2 className="animate-spin" /> : <CameraIcon />} Snapshot olish <Kbd className="ml-1">S</Kbd>
        </Button>
      </div>
    </div>
  )
}
