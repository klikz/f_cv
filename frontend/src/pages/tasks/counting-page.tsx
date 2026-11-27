import { ArrowLeftRight, Check, Eraser, Lightbulb, Loader2, PencilLine, RotateCcw, Save } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router'
import { Advanced, NumberField, SelectField } from '@/components/common/fields'
import { ErrorState } from '@/components/common/states'
import { HintIcon, Term } from '@/components/common/term'
import { ShapeEditor, useShapeHistory, type ShapeDef, type ShapeMap } from '@/components/draw/shape-editor'
import { overlayPalette } from '@/components/video/overlay'
import { useCameraFeed } from '@/components/video/use-feed'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useCamera } from '@/hooks/use-cameras'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { useHotkeys } from '@/hooks/use-hotkeys'
import { useCountingConfig, useSaveConfig, useTasks, type CountingConfig } from '@/hooks/use-tasks'
import { useUnsavedGuard } from '@/hooks/use-unsaved-guard'
import { param, useUrlState } from '@/hooks/use-url-state'
import { api } from '@/lib/api'
import { notify } from '@/lib/notify'
import type { Point } from '@/lib/types'
import { cn } from '@/lib/utils'
import { CountingProducts } from './counting-products'
import { EditorToolbar } from './editor-toolbar'

const STEPS = ['roi', 'line', 'products', 'test'] as const
type Step = (typeof STEPS)[number]
const STEP_LABEL: Record<Step, string> = { roi: 'ROI hududi', line: "Kesib o'tish chizig'i", products: 'Mahsulotlar', test: 'Sinab ko\'ring' }

const DEFAULTS: Omit<CountingConfig, 'stream' | 'roi_polygon' | 'line'> = {
  direction: 'a_to_b',
  reverse_policy: 'ignore',
  max_angle: 60,
  track_point: 'center',
  inference_fps: 5,
  min_track_frames: 3,
  min_distance: 0.01,
  conf_threshold: 0.35,
  uncertain_margin: 0.2,
  min_winner_score: 0.5,
}

export function CountingPage() {
  const id = Number(useParams().id)
  const { data: cam } = useCamera(id)
  useDocumentTitle(cam ? `${cam.name} — Sanash sozlamalari` : 'Sanash sozlamalari')
  const { data: cfg, isLoading, error, refetch } = useCountingConfig(id)
  const { data: tasks } = useTasks(id)
  const save = useSaveConfig<CountingConfig>(id, 'counting')
  const { hub } = useCameraFeed(id, 'analysis')
  const [step, setStep] = useUrlState('step', param.oneOf(STEPS), 'roi', { push: true })
  const [tool, setTool] = useState<string | null>(null)
  const [params, setParams] = useState(DEFAULTS)
  const [initialParams, setInitialParams] = useState(DEFAULTS)
  const hist = useShapeHistory({ roi: null, line: null })
  const [initialShapes, setInitialShapes] = useState<ShapeMap>({ roi: null, line: null })

  useEffect(() => {
    if (!cfg) return
    const { stream: _s, roi_polygon, line, ...rest } = cfg
    void _s
    const sh = { roi: roi_polygon, line: line as Point[] | null }
    hist.reset(sh)
    setInitialShapes(sh)
    setParams(rest)
    setInitialParams(rest)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cfg])

  const pal = overlayPalette()
  const defs: Record<string, ShapeDef> = useMemo(
    () => ({
      roi: { kind: 'polygon', color: pal.roi, label: 'ROI', dash: [6, 4], fillAlpha: 0.08 },
      line: { kind: 'line', color: pal.line, label: 'Chiziq' },
    }),
    [pal.roi, pal.line],
  )

  const dirty = JSON.stringify(hist.shapes) !== JSON.stringify(initialShapes) || JSON.stringify(params) !== JSON.stringify(initialParams)
  useUnsavedGuard(dirty)

  useHotkeys([
    { combo: 'mod+z', handler: hist.undo },
    { combo: 'mod+y', handler: hist.redo },
    { combo: 'mod+shift+z', handler: hist.redo },
    { combo: 'mod+s', handler: () => void doSave(), allowInInput: true },
  ])

  // jonli test rejimi: "Sinab ko'ring" qadamida yoqiladi (sanash yoqilmagan bo'lsa ham, bazaga yozmasdan)
  useEffect(() => {
    if (step !== 'test') return
    void api.put(`/cameras/${id}/counting/testmode`, undefined, { query: { enabled: true } }).catch(() => {})
    return () => {
      void api.put(`/cameras/${id}/counting/testmode`, undefined, { query: { enabled: false } }).catch(() => {})
    }
  }, [step, id])

  const roiOk = (hist.shapes.roi?.length ?? 0) >= 3
  const lineOk = (hist.shapes.line?.length ?? 0) === 2
  const stepDone: Record<Step, boolean> = { roi: roiOk, line: lineOk, products: true, test: false }

  async function doSave() {
    try {
      await save.mutateAsync({ ...params, stream: tasks?.analysis_stream ?? 'main', roi_polygon: hist.shapes.roi, line: hist.shapes.line as [Point, Point] | null })
      setInitialShapes(hist.shapes)
      setInitialParams(params)
      notify.success('Sanash sozlamalari saqlandi')
    } catch (e) {
      notify.error('Saqlab bo\'lmadi', e)
    }
  }

  const set = <K extends keyof typeof params>(k: K, v: (typeof params)[K]) => setParams((p) => ({ ...p, [k]: v }))

  if (error) return <ErrorState error={error} onRetry={() => refetch()} />

  return (
    <div className="flex h-full min-h-0 flex-1">
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-1 border-b px-3 py-2">
          {STEPS.map((s, i) => (
            <button
              key={s}
              type="button"
              onClick={() => setStep(s)}
              className={cn(
                'flex items-center gap-1.5 rounded-md px-2.5 py-1 text-sm transition-colors',
                step === s ? 'bg-primary text-primary-foreground' : 'hover:bg-accent',
              )}
            >
              <span className={cn('flex size-5 items-center justify-center rounded-full text-2xs font-semibold', step === s ? 'bg-primary-foreground/20' : stepDone[s] ? 'bg-success-muted text-success' : 'bg-muted')}>
                {stepDone[s] && step !== s ? <Check className="size-3" /> : i + 1}
              </span>
              {STEP_LABEL[s]}
            </button>
          ))}
          <span className="ml-auto text-xs text-muted-foreground">
            Tahlil oqimi: <span className="font-medium text-foreground">{tasks?.analysis_stream === 'sub' ? 'Sub' : 'Asosiy'}</span>
          </span>
        </div>
        <div className="relative min-h-0 flex-1 bg-video-bg">
          {isLoading ? (
            <Skeleton className="h-full w-full" />
          ) : (
            <ShapeEditor
              hub={hub}
              cameraId={id}
              defs={defs}
              shapes={hist.shapes}
              onChange={hist.change}
              tool={tool}
              onToolDone={() => setTool(null)}
              direction={params.direction}
              showLive={step === 'test'}
              className="absolute inset-0"
            />
          )}
        </div>
        <EditorToolbar
          canUndo={hist.canUndo}
          canRedo={hist.canRedo}
          onUndo={hist.undo}
          onRedo={hist.redo}
          hint={tool === 'roi' ? 'Poligon nuqtalarini bosing; yopish — birinchi nuqta yoki Enter' : tool === 'line' ? 'A va B nuqtalarni bosing' : undefined}
        />
      </div>

      <aside className="flex w-[360px] shrink-0 flex-col border-l">
        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          {step === 'roi' && (
            <div className="space-y-3">
              <h2 className="text-lg font-semibold">
                <Term id="roi" />
              </h2>
              <p className="text-sm text-muted-foreground">Konveyerning mahsulot o'tadigan qismini poligon bilan belgilang. Undan tashqaridagi aniqlashlar hisobga olinmaydi.</p>
              <div className="flex gap-2">
                <Button onClick={() => setTool('roi')} variant={roiOk ? 'outline' : 'default'} disabled={tool === 'roi'}>
                  <PencilLine /> {roiOk ? 'Qayta chizish' : 'Chizish'}
                </Button>
                {roiOk && (
                  <Button variant="ghost" onClick={() => hist.change({ ...hist.shapes, roi: null }, true)}>
                    <Eraser /> Tozalash
                  </Button>
                )}
              </div>
              {roiOk && (
                <Button variant="secondary" className="w-full" onClick={() => setStep('line')}>
                  Keyingi: chiziq →
                </Button>
              )}
            </div>
          )}
          {step === 'line' && (
            <div className="space-y-3">
              <h2 className="text-lg font-semibold">
                <Term id="countLine" />
              </h2>
              <div className="flex gap-2 rounded-lg bg-info-muted p-2.5 text-xs text-foreground">
                <Lightbulb className="size-4 shrink-0 text-info" />
                <p>
                  Chiziqni mahsulot kadrda <b>to'liq ko'rinadigan</b> joyga qo'ying: kadrga kirib kelayotgan katta obyektning ramka markazi sun'iy siljiydi. Mahsulotlar eng ajralgan joyni
                  tanlang. Strelka — mahsulot harakat yo'nalishi (kerak bo'lsa A↔B).
                </p>
              </div>
              <div className="flex gap-2">
                <Button onClick={() => setTool('line')} variant={lineOk ? 'outline' : 'default'} disabled={tool === 'line'}>
                  <PencilLine /> {lineOk ? 'Qayta chizish' : 'Chizish'}
                </Button>
                {lineOk && (
                  <Button
                    variant="outline"
                    onClick={() => {
                      const l = hist.shapes.line!
                      hist.change({ ...hist.shapes, line: [l[1], l[0]] }, true)
                    }}
                    title="A va B ni almashtirish"
                  >
                    <ArrowLeftRight /> A↔B
                  </Button>
                )}
              </div>
              <SelectField
                id="direction"
                label={<Term id="direction" />}
                value={params.direction}
                onChange={(v) => set('direction', v)}
                options={[
                  { value: 'a_to_b', label: 'A→B tomonga (strelka bo\'yicha)' },
                  { value: 'b_to_a', label: 'B→A tomonga' },
                  { value: 'both', label: 'Ikkalasi (alohida hisob)' },
                ]}
              />
              <SelectField
                id="reverse"
                label="Teskari kesib o'tish"
                value={params.reverse_policy}
                onChange={(v) => set('reverse_policy', v)}
                options={[
                  { value: 'ignore', label: "E'tiborsiz qoldirish" },
                  { value: 'subtract', label: 'Sanoqdan ayirish' },
                  { value: 'separate', label: 'Alohida hisoblash' },
                ]}
              />
              {lineOk && (
                <Button variant="secondary" className="w-full" onClick={() => setStep('products')}>
                  Keyingi: mahsulotlar →
                </Button>
              )}
            </div>
          )}
          {step === 'products' && (
            <div className="space-y-3">
              <h2 className="text-lg font-semibold">Faol mahsulotlar</h2>
              <p className="text-sm text-muted-foreground">Bu liniyada ketadigan mahsulotlarni tanlang (5–6 ta). Har biri o'z modeli bilan aniqlanadi.</p>
              <CountingProducts cameraId={id} />
            </div>
          )}
          {step === 'test' && (
            <div className="space-y-3">
              <h2 className="text-lg font-semibold">Jonli sinov</h2>
              <p className="text-sm text-muted-foreground">
                Video ustida aniqlangan mahsulotlar ramka bilan ko'rinadi; chiziqdan o'tganlari yashil bo'ladi ("sanalgan bo'lardi"). Saqlangan sozlamalar bilan ishlaydi — o'zgarishlarni avval
                saqlang.
              </p>
              {!tasks?.tasks.counting.enabled && (
                <p className="rounded-md bg-info-muted p-2 text-xs">Sanash vazifasi yoqilmagan — sinov natijalari bazaga yozilmaydi.</p>
              )}
              {dirty && <p className="rounded-md bg-warning-muted p-2 text-xs text-warning">Saqlanmagan o'zgarishlar bor — sinov eski sozlamalar bilan ishlaydi.</p>}
            </div>
          )}
          <Advanced>
            <SelectField
              id="track_point"
              label="Kuzatuv nuqtasi"
              value={params.track_point}
              onChange={(v) => set('track_point', v)}
              options={[
                { value: 'center', label: 'Ramka markazi' },
                { value: 'bottom_center', label: 'Pastki markaz' },
              ]}
            />
            <NumberField id="fps" label="Inference tezligi" unit="kadr/s" value={params.inference_fps} onChange={(v) => set('inference_fps', v ?? 5)} min={1} max={10} step={1} />
            <NumberField id="angle" label="Maksimal burchak" unit="°" value={params.max_angle} onChange={(v) => set('max_angle', v ?? 60)} min={10} max={90} hint="Harakat yo'nalishi chiziq normaliga nisbatan" />
            <NumberField id="mtf" label="Track minimal yoshi" unit="kadr" value={params.min_track_frames} onChange={(v) => set('min_track_frames', v ?? 3)} min={1} max={30} />
            <NumberField id="mdist" label="Ikki tomonda minimal masofa" unit="× diagonal" value={params.min_distance} onChange={(v) => set('min_distance', v ?? 0.01)} min={0} max={0.2} step={0.005} hint="Chiziq yonidagi titrashdan himoya" />
            <NumberField id="conf" label="Aniqlash ishonch chegarasi" value={params.conf_threshold} onChange={(v) => set('conf_threshold', v ?? 0.35)} min={0.05} max={0.95} step={0.05} />
            <NumberField
              id="margin"
              label={<span className="inline-flex items-center gap-1">Noaniqlik farqi <HintIcon id="uncertainCount" /></span>}
              value={params.uncertain_margin}
              onChange={(v) => set('uncertain_margin', v ?? 0.2)}
              min={0}
              max={1}
              step={0.05}
              hint="G'olib va 2-o'rin ballari farqi bundan kichik bo'lsa — noaniq"
            />
            <NumberField id="minscore" label="G'olibning minimal o'rtacha ishonchi" value={params.min_winner_score} onChange={(v) => set('min_winner_score', v ?? 0.5)} min={0} max={1} step={0.05} />
          </Advanced>
        </div>
        <div className="flex items-center gap-2 border-t p-3">
          <Button variant="ghost" size="sm" onClick={() => setParams({ ...DEFAULTS })} title="Parametrlarni standart qiymatlarga qaytarish">
            <RotateCcw /> Standart
          </Button>
          <Button variant="ghost" size="sm" asChild className="ml-auto">
            <Link to={`/cameras/${id}`}>Bekor qilish</Link>
          </Button>
          <Button size="sm" onClick={() => void doSave()} disabled={save.isPending || !dirty}>
            {save.isPending ? <Loader2 className="animate-spin" /> : <Save />} Saqlash
          </Button>
        </div>
      </aside>
    </div>
  )
}
