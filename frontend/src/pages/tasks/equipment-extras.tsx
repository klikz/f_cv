import { Camera, Loader2, Sparkles, Wand2 } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { baseOption, Chart, useChartTheme } from '@/components/common/chart'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import type { EquipmentConfig } from '@/hooks/use-tasks'
import { api } from '@/lib/api'
import { notify } from '@/lib/notify'

type SignalPoint = [number, number, number, string] // t, harakat %, tayanchdan farq %, holat

/** Jonli signal grafigi: harakat %, chegara chizig'i (sudrab o'zgartiriladi), holat fonida, sikllar belgilari. */
export function EquipmentSignal({ cameraId, config, onThreshold }: { cameraId: number; config: Partial<EquipmentConfig>; onThreshold: (v: number) => void }) {
  const t = useChartTheme()
  const [win, setWin] = useState(120)
  const { data } = useQuery({
    queryKey: ['eq-signal', cameraId, win],
    queryFn: () => api.get<{ points: SignalPoint[] }>(`/cameras/${cameraId}/equipment/signal`, { query: { seconds: win, max_points: 1200 } }),
    refetchInterval: 1000,
  })
  const { data: cycles } = useQuery({
    queryKey: ['eq-cycles', cameraId, win],
    queryFn: () => api.get<{ start: number; end: number; duration: number; micro: boolean }[]>(`/cameras/${cameraId}/equipment/cycles`, { query: { seconds: win } }),
    refetchInterval: 2000,
  })
  const pts = data?.points ?? []
  const thr = config.motion_threshold ?? 2

  const option = useMemo(() => {
    const motion = pts.map((p) => [p[0] * 1000, p[1]])
    const home = pts.map((p) => [p[0] * 1000, p[2]])
    // holat fonida (yashil — ishlayapti, qizil — to'xtagan)
    const areas: { xAxis: number; itemStyle: { color: string } }[][] = []
    let cur: string | null = null
    let start = 0
    for (const p of pts) {
      if (p[3] !== cur) {
        if (cur && cur !== 'u') areas.push([{ xAxis: start, itemStyle: { color: cur === 'r' ? t.success : t.danger } }, { xAxis: p[0] * 1000, itemStyle: { color: '' } }])
        cur = p[3]
        start = p[0] * 1000
      }
    }
    if (cur && cur !== 'u' && pts.length) areas.push([{ xAxis: start, itemStyle: { color: cur === 'r' ? t.success : t.danger } }, { xAxis: pts[pts.length - 1][0] * 1000, itemStyle: { color: '' } }])
    const b = baseOption(t)
    return {
      ...b,
      grid: { left: 36, right: 12, top: 22, bottom: 22 },
      tooltip: { ...b.tooltip, valueFormatter: (v: number) => `${v?.toFixed?.(1)}%` },
      xAxis: { ...b.xAxis, type: 'time', axisLabel: { ...b.xAxis.axisLabel, formatter: '{HH}:{mm}:{ss}' } },
      yAxis: { ...b.yAxis, type: 'value', min: 0, max: (v: { max: number }) => Math.max(thr * 2, Math.ceil(v.max * 1.1)) },
      series: [
        {
          name: 'Harakat %',
          type: 'line',
          showSymbol: false,
          data: motion,
          lineStyle: { width: 1.5 },
          markLine: {
            symbol: 'none',
            silent: true,
            data: [{ yAxis: thr, lineStyle: { color: t.warning, type: 'dashed', width: 2 }, label: { formatter: `chegara ${thr}%`, color: t.warning } }],
          },
          markArea: { silent: true, itemStyle: { opacity: 0.08 }, data: areas },
        },
        ...(config.cycle_mode === 'home'
          ? [{ name: 'Tayanchdan farq %', type: 'line', showSymbol: false, data: home, lineStyle: { width: 1, type: 'dotted' } }]
          : []),
        {
          name: 'Sikl',
          type: 'scatter',
          symbolSize: 7,
          data: (cycles ?? []).map((c) => ({ value: [c.end * 1000, 0], itemStyle: { color: c.micro ? t.danger : t.series[2] } })),
          tooltip: { formatter: (p: { dataIndex: number }) => `Sikl: ${cycles?.[p.dataIndex]?.duration.toFixed(2)} s` },
        },
      ],
    }
  }, [pts, cycles, thr, t, config.cycle_mode])

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between px-1 text-xs text-muted-foreground">
        <span>Jonli signal — grafikni bosib chegarani o'rnating</span>
        <div className="flex gap-1">
          {[60, 120, 300, 900].map((s) => (
            <button key={s} type="button" className={`rounded px-1.5 ${win === s ? 'bg-accent text-foreground' : ''}`} onClick={() => setWin(s)}>
              {s < 120 ? `${s} s` : `${s / 60} daq`}
            </button>
          ))}
        </div>
      </div>
      {pts.length ? (
        <Chart
          option={option}
          height="100%"
          className="min-h-0 flex-1"
        />
      ) : (
        <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">Signal yo'q — ROI chizib saqlang va vazifani yoqing</div>
      )}
      <ThresholdPicker max={Math.max(10, ...pts.map((p) => p[1]))} value={thr} onChange={onThreshold} />
    </div>
  )
}

function ThresholdPicker({ value, max, onChange }: { value: number; max: number; onChange: (v: number) => void }) {
  return (
    <input
      type="range"
      min={0.1}
      max={Math.ceil(max)}
      step={0.1}
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      className="mt-1 w-full accent-warning"
      aria-label="Harakat chegarasi"
    />
  )
}

/** Tayanch kadr: joriy kadrdan olish yoki avtomatik taklif (eng so'nggi tinch holat). */
export function HomeReference({ cameraId, value }: { cameraId: number; value: string | null }) {
  const qc = useQueryClient()
  const [busy, setBusy] = useState<string | null>(null)
  const [ver, setVer] = useState(0)
  const take = async (fromCandidate: boolean) => {
    setBusy(fromCandidate ? 'c' : 'n')
    try {
      await api.post(`/cameras/${cameraId}/equipment/home`, undefined, { query: { from_candidate: fromCandidate }, timeoutMs: 30000 })
      notify.success('Tayanch kadr saqlandi')
      setVer((v) => v + 1)
      void qc.invalidateQueries({ queryKey: ['equipment-config', cameraId] })
      void qc.invalidateQueries({ queryKey: ['tasks', cameraId] })
    } catch (e) {
      notify.error("Tayanch kadrni olib bo'lmadi", e)
    } finally {
      setBusy(null)
    }
  }
  return (
    <div className="space-y-2 rounded-lg border p-2.5">
      <div className="text-sm font-medium">Tayanch ("uy") kadr</div>
      {value ? (
        <img src={`/api/cameras/${cameraId}/equipment/home.jpg?v=${ver}-${value}`} alt="Tayanch kadr" className="aspect-video w-full rounded border object-contain bg-video-bg" />
      ) : (
        <p className="text-xs text-warning">Olinmagan — uskuna boshlang'ich holatida turganda oling.</p>
      )}
      <div className="flex gap-2">
        <Button size="xs" variant="outline" onClick={() => void take(false)} disabled={!!busy}>
          {busy === 'n' ? <Loader2 className="animate-spin" /> : <Camera />} Hozirgi kadr
        </Button>
        <Button size="xs" variant="outline" onClick={() => void take(true)} disabled={!!busy} title="Eng so'nggi tinch holat kadri">
          {busy === 'c' ? <Loader2 className="animate-spin" /> : <Sparkles />} Avto taklif
        </Button>
      </div>
    </div>
  )
}

type Suggestion = {
  period_sec: number
  returns_per_cycle: number
  motion_threshold: number
  peak_min_height: number
  peak_min_distance_sec: number
  home_exit_threshold: number | null
  home_return_threshold: number | null
  reference_cycle_sec: number
}

/** Avto-aniqlash: davr va parametrlar taklifi; qabul qilinsa formaga yoziladi. */
export function AutoDetect({ cameraId, onApply }: { cameraId: number; onApply: (s: Suggestion) => void }) {
  const [busy, setBusy] = useState(false)
  const [s, setS] = useState<Suggestion | null>(null)
  const run = async () => {
    setBusy(true)
    try {
      setS(await api.post<Suggestion>(`/cameras/${cameraId}/equipment/autodetect`))
    } catch (e) {
      notify.error("Aniqlab bo'lmadi", e)
    } finally {
      setBusy(false)
    }
  }
  return (
    <>
      <Button size="xs" variant="outline" onClick={run} disabled={busy}>
        {busy ? <Loader2 className="animate-spin" /> : <Wand2 />} Avto-aniqlash
      </Button>
      <Dialog open={!!s} onOpenChange={(o) => !o && setS(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Taklif qilingan parametrlar</DialogTitle>
            <DialogDescription>Oxirgi daqiqalardagi signal avtokorrelyatsiyasi bo'yicha.</DialogDescription>
          </DialogHeader>
          {s && (
            <div className="grid grid-cols-2 gap-2 text-sm">
              <span className="text-muted-foreground">Sikl davri</span>
              <span className="num">{s.period_sec} s</span>
              <span className="text-muted-foreground">Siklda qaytish/cho'qqi (K)</span>
              <span className="num">{s.returns_per_cycle}</span>
              <span className="text-muted-foreground">Harakat chegarasi</span>
              <span className="num">{s.motion_threshold}%</span>
              <span className="text-muted-foreground">Cho'qqi balandligi</span>
              <span className="num">{s.peak_min_height}%</span>
              {s.home_exit_threshold != null && (
                <>
                  <span className="text-muted-foreground">Tayanch: chiqdi / qaytdi</span>
                  <span className="num">
                    {s.home_exit_threshold}% / {s.home_return_threshold}%
                  </span>
                </>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="ghost" onClick={() => setS(null)}>
              Bekor qilish
            </Button>
            <Button
              onClick={() => {
                if (s) onApply(s)
                setS(null)
              }}
            >
              Qabul qilish
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
