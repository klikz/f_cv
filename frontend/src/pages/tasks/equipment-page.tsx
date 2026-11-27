import { Eraser, Loader2, PencilLine, Plus, Save, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router'
import { Advanced, NumberField, SelectField } from '@/components/common/fields'
import { ErrorState } from '@/components/common/states'
import { HintIcon, Term } from '@/components/common/term'
import { ShapeEditor, useShapeHistory, type ShapeDef, type ShapeMap } from '@/components/draw/shape-editor'
import { overlayPalette } from '@/components/video/overlay'
import { useCameraFeed } from '@/components/video/use-feed'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { useCamera } from '@/hooks/use-cameras'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { useHotkeys } from '@/hooks/use-hotkeys'
import { useEquipmentConfig, useSaveConfig, useTasks, type EquipmentConfig } from '@/hooks/use-tasks'
import { useUnsavedGuard } from '@/hooks/use-unsaved-guard'
import { notify } from '@/lib/notify'
import type { Point } from '@/lib/types'
import { EditorToolbar } from './editor-toolbar'
import { AutoDetect, EquipmentSignal, HomeReference } from './equipment-extras'

type Params = Omit<EquipmentConfig, 'stream' | 'roi_polygon' | 'control_zone' | 'exclude_zones' | 'home_reference'>
const MAX_EXCLUDE = 6

function toShapes(c: EquipmentConfig): ShapeMap {
  const m: ShapeMap = { roi: c.roi_polygon, control: c.control_zone }
  c.exclude_zones.forEach((z, i) => (m[`exclude${i}`] = z))
  return m
}

export function EquipmentPage() {
  const id = Number(useParams().id)
  const { data: cam } = useCamera(id)
  useDocumentTitle(cam ? `${cam.name} — Uskuna sozlamalari` : 'Uskuna sozlamalari')
  const { data: cfg, isLoading, error, refetch } = useEquipmentConfig(id)
  const { data: tasks } = useTasks(id)
  const save = useSaveConfig<EquipmentConfig>(id, 'equipment')
  const { hub } = useCameraFeed(id, 'analysis')
  const [tool, setTool] = useState<string | null>(null)
  const [params, setParams] = useState<Params | null>(null)
  const [initialParams, setInitialParams] = useState<Params | null>(null)
  const hist = useShapeHistory({ roi: null, control: null })
  const [initialShapes, setInitialShapes] = useState<ShapeMap>({})

  useEffect(() => {
    if (!cfg) return
    const { stream: _s, roi_polygon: _r, control_zone: _c, exclude_zones: _e, home_reference: _h, ...rest } = cfg
    void [_s, _r, _c, _e, _h]
    const sh = toShapes(cfg)
    hist.reset(sh)
    setInitialShapes(sh)
    setParams(rest)
    setInitialParams(rest)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cfg])

  const pal = overlayPalette()
  const excludeKeys = Object.keys(hist.shapes).filter((k) => k.startsWith('exclude') && hist.shapes[k])
  const defs: Record<string, ShapeDef> = useMemo(() => {
    const d: Record<string, ShapeDef> = {
      roi: { kind: 'polygon', color: pal.success, label: 'ROI', fillAlpha: 0.08 },
      control: { kind: 'polygon', color: pal.roi, label: 'Nazorat', dash: [4, 4], fillAlpha: 0.05 },
    }
    for (let i = 0; i < MAX_EXCLUDE; i++) d[`exclude${i}`] = { kind: 'polygon', color: pal.neutral, label: `Istisno ${i + 1}`, dash: [2, 3], fillAlpha: 0.25 }
    return d
  }, [pal.success, pal.roi, pal.neutral])

  const dirty = JSON.stringify(hist.shapes) !== JSON.stringify(initialShapes) || JSON.stringify(params) !== JSON.stringify(initialParams)
  useUnsavedGuard(dirty)

  useHotkeys([
    { combo: 'mod+z', handler: hist.undo },
    { combo: 'mod+y', handler: hist.redo },
    { combo: 'mod+s', handler: () => void doSave(), allowInInput: true },
  ])

  async function doSave() {
    if (!params) return
    const sh = hist.shapes
    const excl = Object.keys(sh)
      .filter((k) => k.startsWith('exclude'))
      .sort()
      .map((k) => sh[k])
      .filter((z): z is Point[] => !!z && z.length >= 3)
    try {
      await save.mutateAsync({ ...params, stream: tasks?.analysis_stream ?? 'main', roi_polygon: sh.roi, control_zone: sh.control?.length ? sh.control : null, exclude_zones: excl, home_reference: cfg?.home_reference ?? null })
      setInitialShapes(sh)
      setInitialParams(params)
      notify.success('Uskuna sozlamalari saqlandi')
    } catch (e) {
      notify.error('Saqlab bo\'lmadi', e)
    }
  }

  const set = <K extends keyof Params>(k: K, v: Params[K]) => setParams((p) => (p ? { ...p, [k]: v } : p))
  const nextExclude = () => {
    for (let i = 0; i < MAX_EXCLUDE; i++) if (!hist.shapes[`exclude${i}`]?.length) return `exclude${i}`
    return null
  }

  if (error) return <ErrorState error={error} onRetry={() => refetch()} />
  const roiOk = (hist.shapes.roi?.length ?? 0) >= 3

  return (
    <div className="flex h-full min-h-0 flex-1">
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="relative min-h-0 flex-1 bg-video-bg">
          {isLoading ? (
            <Skeleton className="h-full w-full" />
          ) : (
            <ShapeEditor hub={hub} cameraId={id} defs={defs} shapes={hist.shapes} onChange={hist.change} tool={tool} onToolDone={() => setTool(null)} className="absolute inset-0" />
          )}
        </div>
        <div className="h-48 shrink-0 border-t p-2">
          {params && <EquipmentSignal cameraId={id} config={params} onThreshold={(v) => set('motion_threshold', Math.round(v * 10) / 10)} />}
        </div>
        <EditorToolbar canUndo={hist.canUndo} canRedo={hist.canRedo} onUndo={hist.undo} onRedo={hist.redo} hint={tool ? 'Poligon nuqtalarini bosing; yopish — birinchi nuqta yoki Enter' : undefined} />
      </div>
      <aside className="flex w-[360px] shrink-0 flex-col border-l">
        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          <section className="space-y-2">
            <h2 className="font-semibold">1. Hududlar</h2>
            <div className="flex items-center justify-between gap-2">
              <Term id="roi" className="text-sm" />
              <div className="flex gap-1">
                <Button size="xs" variant={roiOk ? 'outline' : 'default'} onClick={() => setTool('roi')}>
                  <PencilLine /> {roiOk ? 'Qayta' : 'Chizish'}
                </Button>
              </div>
            </div>
            <div className="flex items-center justify-between gap-2">
              <Term id="controlZone" className="text-sm">
                Nazorat zonasi <span className="text-xs text-muted-foreground">(ixtiyoriy)</span>
              </Term>
              <div className="flex gap-1">
                <Button size="xs" variant="outline" onClick={() => setTool('control')}>
                  <PencilLine /> {hist.shapes.control?.length ? 'Qayta' : 'Chizish'}
                </Button>
                {!!hist.shapes.control?.length && (
                  <Button size="icon-xs" variant="ghost" onClick={() => hist.change({ ...hist.shapes, control: null }, true)} aria-label="Nazorat zonasini o'chirish">
                    <Eraser />
                  </Button>
                )}
              </div>
            </div>
            <div className="space-y-1">
              <div className="flex items-center justify-between gap-2">
                <Term id="excludeZone" className="text-sm">
                  Istisno zonalari <span className="text-xs text-muted-foreground">(ixtiyoriy)</span>
                </Term>
                <Button
                  size="xs"
                  variant="outline"
                  disabled={!nextExclude()}
                  onClick={() => {
                    const k = nextExclude()
                    if (k) setTool(k)
                  }}
                >
                  <Plus /> Qo'shish
                </Button>
              </div>
              {excludeKeys.map((k, i) => (
                <div key={k} className="flex items-center justify-between rounded-md bg-muted px-2 py-1 text-xs">
                  Istisno {i + 1}
                  <Button size="icon-xs" variant="ghost" onClick={() => hist.change({ ...hist.shapes, [k]: null }, true)} aria-label="O'chirish">
                    <X />
                  </Button>
                </div>
              ))}
            </div>
          </section>
          <Separator />
          {params && (
            <>
              <section className="space-y-3">
                <h2 className="font-semibold">2. Ish holati</h2>
                <NumberField id="thr" label="Harakat chegarasi" unit="% ROI" value={params.motion_threshold} onChange={(v) => set('motion_threshold', v ?? 2)} min={0.1} max={100} step={0.1} hint="Grafikdagi chiziqni sudrab ham o'zgartirish mumkin" />
                <div className="grid grid-cols-2 gap-3">
                  <NumberField id="minon" label="Min. ish vaqti" unit="s" value={params.min_on_sec} onChange={(v) => set('min_on_sec', v ?? 3)} min={0} step={0.5} />
                  <NumberField id="minoff" label="Min. to'xtash" unit="s" value={params.min_off_sec} onChange={(v) => set('min_off_sec', v ?? 10)} min={0} step={1} />
                </div>
              </section>
              <Separator />
              <section className="space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="flex items-center gap-1 font-semibold">
                    3. Sikl <HintIcon id="cycle" />
                  </h2>
                  <AutoDetect
                    cameraId={id}
                    onApply={(sg) =>
                      setParams((p) =>
                        p
                          ? {
                              ...p,
                              returns_per_cycle: sg.returns_per_cycle,
                              motion_threshold: sg.motion_threshold,
                              peak_min_height: sg.peak_min_height,
                              peak_min_distance_sec: sg.peak_min_distance_sec,
                              home_exit_threshold: sg.home_exit_threshold ?? p.home_exit_threshold,
                              home_return_threshold: sg.home_return_threshold ?? p.home_return_threshold,
                              reference_cycle_sec: p.auto_reference ? p.reference_cycle_sec : sg.reference_cycle_sec,
                            }
                          : p,
                      )
                    }
                  />
                </div>
                <SelectField
                  id="mode"
                  label="Sikl rejimi"
                  value={params.cycle_mode}
                  onChange={(v) => set('cycle_mode', v)}
                  options={[
                    { value: 'home', label: 'Tayanch holat bo\'yicha (asosiy)' },
                    { value: 'peaks', label: "Harakat cho'qqilari bo'yicha" },
                    { value: 'off', label: 'Sikl sanalmaydi' },
                  ]}
                />
                {params.cycle_mode !== 'off' && (
                  <NumberField
                    id="k"
                    label={params.cycle_mode === 'home' ? 'Siklga qaytishlar soni (K)' : "Siklga cho'qqilar soni (K)"}
                    value={params.returns_per_cycle}
                    onChange={(v) => set('returns_per_cycle', Math.max(1, Math.round(v ?? 1)))}
                    min={1}
                    max={20}
                    hint="Press — 1 (bitta tushib-ko'tarilish); ikki marta aylanish — 2"
                  />
                )}
                {params.cycle_mode === 'home' && <HomeReference cameraId={id} value={cfg?.home_reference ?? null} />}
                <div className="flex items-center justify-between gap-2">
                  <Label htmlFor="autoref" className="flex items-center gap-1 text-sm">
                    <Term id="referenceCycle" />: avtomatik
                  </Label>
                  <Switch id="autoref" checked={params.auto_reference} onCheckedChange={(v) => set('auto_reference', v)} />
                </div>
                {!params.auto_reference && (
                  <NumberField id="ref" label="Etalon sikl vaqti" unit="s" value={params.reference_cycle_sec} onChange={(v) => set('reference_cycle_sec', v)} min={0.1} step={0.1} nullable />
                )}
              </section>
              <Advanced>
                <NumberField id="exit" label="'Chiqdi' chegarasi (tayanchdan farq)" unit="%" value={params.home_exit_threshold} onChange={(v) => set('home_exit_threshold', v ?? 12)} step={0.5} />
                <NumberField id="ret" label="'Qaytdi' chegarasi" unit="%" value={params.home_return_threshold} onChange={(v) => set('home_return_threshold', v ?? 6)} step={0.5} />
                <NumberField id="ph" label="Cho'qqi minimal balandligi" unit="%" value={params.peak_min_height} onChange={(v) => set('peak_min_height', v ?? 5)} step={0.5} />
                <NumberField id="pd" label="Cho'qqilar orasidagi min. vaqt" unit="s" value={params.peak_min_distance_sec} onChange={(v) => set('peak_min_distance_sec', v ?? 0.5)} step={0.1} />
                <NumberField id="ms" label="Mikro-to'xtash koeffitsienti" unit="× etalon" value={params.micro_stop_factor} onChange={(v) => set('micro_stop_factor', v ?? 1.5)} min={1.05} step={0.05} />
              </Advanced>
            </>
          )}
        </div>
        <div className="flex items-center justify-end gap-2 border-t p-3">
          <Button variant="ghost" size="sm" asChild>
            <Link to={`/cameras/${id}`}>Bekor qilish</Link>
          </Button>
          <Button size="sm" onClick={() => void doSave()} disabled={save.isPending || !dirty || !roiOk}>
            {save.isPending ? <Loader2 className="animate-spin" /> : <Save />} Saqlash
          </Button>
        </div>
      </aside>
    </div>
  )
}
