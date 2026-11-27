import { Plus, Save, Trash2 } from 'lucide-react'
import { useEffect, useRef, type ReactNode } from 'react'
import { useConfirm } from '@/components/common/confirm-dialog'
import { Advanced, NumberField, SelectField } from '@/components/common/fields'
import { Progress } from '@/components/common/progress'
import { ReadinessBadge } from '@/components/common/readiness-badge'
import { CardGridSkeleton, EmptyState, ErrorState, TableSkeleton } from '@/components/common/states'
import { StatusBadge, type StatusKind } from '@/components/common/status-badge'
import { Term } from '@/components/common/term'
import { PageBody, PageHeader, useRouteTitle } from '@/components/layout/page'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Kbd } from '@/components/ui/kbd'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { containRect, drawOverlay } from '@/components/video/overlay'
import { TaskStatusOverlay } from '@/components/video/task-status'
import { ApiError } from '@/lib/api'
import { notify } from '@/lib/notify'
import { useTheme } from '@/lib/theme'

const COLORS = ['background', 'foreground', 'card', 'muted', 'muted-foreground', 'primary', 'secondary', 'accent', 'border', 'success', 'warning', 'danger', 'neutral', 'info', 'overlay-roi', 'overlay-line', 'overlay-box', 'video-bg']
const STATUSES: StatusKind[] = ['ok', 'online', 'running', 'warn', 'uncertain', 'error', 'offline', 'stopped', 'disabled', 'unknown', 'connecting', 'training']

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="border-b pb-1 text-lg font-semibold">{title}</h2>
      {children}
    </section>
  )
}

/** AI qatlami namunasi: sintetik kadr + ROI, chiziq, ramkalar, harakat sohalari. */
function OverlaySample({ w, label }: { w: number; label: string }) {
  const ref = useRef<HTMLCanvasElement>(null)
  const { theme } = useTheme()
  useEffect(() => {
    const cv = ref.current
    if (!cv) return
    const h = Math.round((w * 9) / 16)
    cv.width = w
    cv.height = h
    const ctx = cv.getContext('2d')!
    ctx.fillStyle = '#3a3d42'
    ctx.fillRect(0, 0, w, h)
    ctx.fillStyle = '#2f3034'
    ctx.fillRect(0, h * 0.44, w, h * 0.36)
    ctx.fillStyle = '#eee'
    ctx.fillRect(w * 0.18, h * 0.5, w * 0.13, h * 0.24)
    ctx.fillStyle = '#1b1b1d'
    ctx.fillRect(w * 0.6, h * 0.52, w * 0.2, h * 0.2)
    const r = containRect(w, h, w, h)
    drawOverlay(ctx, r, {
      counting: {
        roi: [[0.04, 0.4], [0.96, 0.4], [0.96, 0.84], [0.04, 0.84]],
        line: [[0.5, 0.88], [0.5, 0.36]],
        direction: 'a_to_b',
        detections: [
          { bbox: [0.18, 0.5, 0.31, 0.74], label: 'Muzlatgich', score: 0.93, track_id: 12, counted: false },
          { bbox: [0.6, 0.52, 0.8, 0.72], label: 'Televizor 55', score: 0.88, track_id: 11, counted: true },
        ],
      },
    })
  }, [w, theme])
  return (
    <figure className="space-y-1">
      <div className="relative w-fit overflow-hidden rounded-lg border">
        <canvas ref={ref} className="block" />
        <TaskStatusOverlay
          size={w > 420 ? 'lg' : 'sm'}
          live={{ ts: 0, tasks: ['counting'], enabled: ['counting'], counting: { total: 128, uncertain: 2, per_product: [{ product_id: 1, name: 'Televizor 55', count: 70 }, { product_id: 2, name: 'Muzlatgich', count: 58 }] } }}
        />
      </div>
      <figcaption className="text-xs text-muted-foreground">{label}</figcaption>
    </figure>
  )
}

export function DevUiPage() {
  const title = useRouteTitle()
  const confirm = useConfirm()
  const { theme, toggleTheme } = useTheme()
  return (
    <PageBody className="space-y-8">
      <PageHeader title={title} description="Barcha komponentlar va tokenlar bir joyda — yangi sahifalar shulardan yig'iladi." actions={<Button variant="outline" onClick={toggleTheme}>Mavzu: {theme === 'dark' ? "qorong'i" : "yorug'"}</Button>} />

      <Section title="Ranglar (tokenlar)">
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-6 lg:grid-cols-9">
          {COLORS.map((c) => (
            <div key={c} className="space-y-1">
              <div className="h-12 rounded-md border" style={{ background: `var(--${c})` }} />
              <div className="truncate font-mono text-2xs text-muted-foreground">{c}</div>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Tipografiya">
        <div className="space-y-1">
          <div className="text-3xl font-semibold">Sarlavha 3xl</div>
          <div className="text-2xl font-semibold">Sahifa sarlavhasi 2xl</div>
          <div className="text-lg font-semibold">Bo'lim lg</div>
          <div className="text-base">Asosiy matn base — Konveyerda mahsulotlar chapdan o'ngga o'tadi.</div>
          <div className="text-sm text-muted-foreground">Ikkinchi darajali matn sm</div>
          <div className="num text-2xl font-semibold">1 234 567 · 09:41:05 — tabular-nums</div>
        </div>
      </Section>

      <Section title="Tugmalar">
        <div className="flex flex-wrap items-center gap-2">
          <Button><Save /> Asosiy amal</Button>
          <Button variant="secondary">Ikkinchi darajali</Button>
          <Button variant="outline"><Plus /> Outline</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="destructive"><Trash2 /> Xavfli</Button>
          <Button variant="link">Havola</Button>
          <Button size="sm">Kichik</Button>
          <Button size="xs">XS</Button>
          <Button disabled>Nofaol</Button>
        </div>
      </Section>

      <Section title="Holat belgilari (rang + ikon + matn)">
        <div className="flex flex-wrap gap-2">{STATUSES.map((s) => <StatusBadge key={s} status={s} />)}</div>
        <div className="flex flex-wrap gap-4">{STATUSES.slice(0, 6).map((s) => <StatusBadge key={s} status={s} variant="inline" />)}</div>
        <div className="flex flex-wrap gap-2"><ReadinessBadge level="insufficient" /><ReadinessBadge level="minimal" /><ReadinessBadge level="ready" /><Badge>Badge</Badge><Badge variant="secondary">secondary</Badge></div>
        <div className="max-w-sm space-y-2"><Progress value={30} /><Progress value={75} tone="warning" /><Progress value={95} tone="danger" /></div>
      </Section>

      <Section title="Forma elementlari">
        <div className="grid max-w-3xl gap-4 sm:grid-cols-2">
          <div className="space-y-1.5"><Label htmlFor="d1">Kamera nomi</Label><Input id="d1" placeholder="Liniya-1" /></div>
          <NumberField id="d2" label="Inference tezligi" unit="kadr/s" value={5} onChange={() => {}} />
          <SelectField id="d3" label={<Term id="direction" />} value="a_to_b" onChange={() => {}} options={[{ value: 'a_to_b', label: 'A→B' }, { value: 'both', label: 'Ikkalasi' }]} />
          <div className="flex items-center gap-4 pt-6"><div className="flex items-center gap-2"><Checkbox id="d4" defaultChecked /><Label htmlFor="d4">Checkbox</Label></div><div className="flex items-center gap-2"><Switch id="d5" defaultChecked /><Label htmlFor="d5">Switch</Label></div></div>
          <div className="sm:col-span-2"><Advanced><p className="text-sm text-muted-foreground">Kamdan-kam ishlatiladigan parametrlar shu yerga yig'iladi.</p></Advanced></div>
        </div>
        <p className="text-sm">Qisqa tugmalar: <Kbd>Ctrl</Kbd> + <Kbd>K</Kbd>, <Kbd>?</Kbd></p>
      </Section>

      <Section title="Jadval va kartochka">
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="overflow-hidden rounded-xl border bg-card">
            <Table>
              <TableHeader><TableRow><TableHead>Mahsulot</TableHead><TableHead className="text-right">Soni</TableHead><TableHead>Holat</TableHead></TableRow></TableHeader>
              <TableBody>
                <TableRow><TableCell>Televizor 55</TableCell><TableCell className="num text-right">70</TableCell><TableCell><StatusBadge status="ok" size="sm" /></TableCell></TableRow>
                <TableRow><TableCell>Muzlatgich</TableCell><TableCell className="num text-right">58</TableCell><TableCell><StatusBadge status="uncertain" size="sm" /></TableCell></TableRow>
              </TableBody>
            </Table>
          </div>
          <Card><CardHeader><CardTitle className="text-base">Kartochka</CardTitle></CardHeader><CardContent className="text-sm text-muted-foreground">Ma'lumot zich, lekin tartibli; ortiqcha bezaksiz.</CardContent></Card>
        </div>
      </Section>

      <Section title="Toast va oynalar">
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => notify.success('Saqlandi')}>Muvaffaqiyat</Button>
          <Button variant="outline" onClick={() => notify.warning('Diqqat', 'Diskda joy kam')}>Ogohlantirish</Button>
          <Button variant="outline" onClick={() => notify.error("Kameraga ulanib bo'lmadi", new ApiError(401, 'Login yoki parol xato'))}>Xato</Button>
          <Button variant="outline" onClick={() => notify.undoable("Sanoq bekor qilindi", () => { notify.info('Qaytarildi') })}>Qaytarish (undo)</Button>
          <Button variant="outline" onClick={() => void confirm({ title: "Kamera o'chirilsinmi?", description: "Bu amalni qaytarib bo'lmaydi.", destructive: true, confirmText: "O'chirish" })}>Tasdiqlash oynasi</Button>
        </div>
      </Section>

      <Section title="Bo'sh, yuklanish va xato holatlari">
        <div className="grid gap-4 lg:grid-cols-3">
          <Card><EmptyState compact title="Kamera yo'q" description="Kamera qo'shing" action={<Button size="sm"><Plus /> Kamera qo'shish</Button>} /></Card>
          <Card className="p-4"><TableSkeleton rows={3} cols={3} /></Card>
          <Card><ErrorState compact error={new ApiError(0, "Server bilan aloqa yo'q")} onRetry={() => {}} /></Card>
        </div>
        <CardGridSkeleton count={3} />
      </Section>

      <Section title="Video katagi va AI qatlami">
        <div className="flex flex-wrap items-start gap-4">
          <OverlaySample w={640} label="Katta katak (1×1, 2×2): to'liq yorliqlar, mahsulotlar kesimi" />
          <OverlaySample w={300} label="Kichik katak (4×4): yupqa chiziqlar, qisqa yorliqlar" />
        </div>
      </Section>
    </PageBody>
  )
}
