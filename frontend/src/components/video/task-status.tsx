import { Activity, Boxes, CircleHelp, Gauge, Loader, Repeat } from 'lucide-react'
import { fmtDuration, fmtNum, fmtPct, fmtSec } from '@/lib/format'
import type { CameraLive } from '@/lib/types'
import { cn } from '@/lib/utils'

/**
 * Video ustidagi vazifa holati yozuvlari (AI Vision'ga bog'liq emas, doim ko'rinadi).
 * size: 'lg' (1×1, 2×2) — batafsil; 'sm' (3×3, 4×4) — faqat asosiy raqamlar.
 */
export function TaskStatusOverlay({ live, size }: { live: CameraLive['live'] | undefined; size: 'lg' | 'sm' }) {
  if (!live) return null
  const c = live.counting
  const e = live.equipment
  if (!c && !e && !live.enabled?.length) return null
  const sm = size === 'sm'
  const box = 'rounded-md bg-overlay-label-bg/90 text-white backdrop-blur-sm'
  return (
    <div className={cn('pointer-events-none absolute right-2 bottom-2 left-2 flex flex-col items-start gap-1', sm && 'right-1 bottom-1 left-1')}>
      {live.enabled?.includes('counting') && !c && (
        <div className={cn(box, 'px-2 py-1 text-xs')}>Sanash: sozlanmagan</div>
      )}
      {c && (
        <div className={cn(box, sm ? 'px-1.5 py-0.5' : 'px-2 py-1.5')}>
          <div className={cn('flex items-center gap-1.5 font-semibold', sm ? 'text-xs' : 'text-sm')}>
            <Boxes className={sm ? 'size-3' : 'size-3.5'} aria-hidden />
            <span className="num text-success">{fmtNum(c.total)}</span>
            {!sm && <span className="font-normal text-white/70">sanaldi</span>}
            {c.uncertain > 0 && (
              <span className="ml-1 flex items-center gap-0.5 text-warning">
                <CircleHelp className="size-3" aria-hidden />
                <span className="num">{c.uncertain}</span>
                {!sm && <span className="font-normal">noaniq</span>}
              </span>
            )}
            {c.paused && (
              <span className="ml-1 flex items-center gap-1 font-normal text-info">
                <Loader className="size-3 animate-spin" aria-hidden />
                {sm ? 'Train' : 'Train ketmoqda'}
              </span>
            )}
          </div>
          {!sm && c.per_product.length > 0 && (
            <div className="mt-0.5 space-y-0.5 text-xs text-white/85">
              {c.per_product.slice(0, 5).map((p) => (
                <div key={p.product_id ?? p.name} className="flex justify-between gap-3">
                  <span className="truncate">{p.name}</span>
                  <span className="num font-medium">{p.count}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      {live.enabled?.includes('equipment') && !e && (
        <div className={cn(box, 'px-2 py-1 text-xs')}>Uskuna: sozlanmagan</div>
      )}
      {e && (
        <div className={cn(box, sm ? 'px-1.5 py-0.5' : 'px-2 py-1.5')}>
          <div className={cn('flex items-center gap-1.5 font-semibold', sm ? 'text-xs' : 'text-sm')}>
            <Activity
              className={cn(sm ? 'size-3' : 'size-3.5', e.state === 'running' ? 'text-success' : e.state === 'stopped' ? 'text-danger' : 'text-neutral')}
              aria-hidden
            />
            <span className={e.state === 'running' ? 'text-success' : e.state === 'stopped' ? 'text-danger' : 'text-neutral'}>
              {e.state === 'running' ? 'Ishlayapti' : e.state === 'stopped' ? "To'xtagan" : "Noma'lum"}
            </span>
            <span className="num font-normal text-white/85">{fmtDuration(e.run_seconds)}</span>
            <span className="flex items-center gap-0.5 font-normal text-white/85">
              <Repeat className="size-3" aria-hidden />
              <span className="num">{fmtNum(e.cycles)}</span>
            </span>
          </div>
          {!sm && (
            <div className="mt-0.5 flex gap-3 text-xs text-white/80">
              <span>
                Oxirgi sikl: <span className="num font-medium">{fmtSec(e.last_cycle_sec)}</span>
              </span>
              <span className="flex items-center gap-1">
                <Gauge className="size-3" aria-hidden /> <span className="num font-medium">{fmtPct(e.utilization_pct)}</span>
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
