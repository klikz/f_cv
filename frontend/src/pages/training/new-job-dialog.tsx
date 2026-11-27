import { Loader2, Play } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { useQueryClient } from '@tanstack/react-query'
import { Advanced, NumberField, SelectField } from '@/components/common/fields'
import { ReadinessBadge } from '@/components/common/readiness-badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useCameras } from '@/hooks/use-cameras'
import { useReadiness, type Job } from '@/hooks/use-catalog'
import { api } from '@/lib/api'
import { notify } from '@/lib/notify'

export function NewJobDialog({ open, onOpenChange, preselect }: { open: boolean; onOpenChange: (o: boolean) => void; preselect?: number }) {
  const { data: ready } = useReadiness()
  const { data: cams } = useCameras()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [sel, setSel] = useState<number[]>([])
  const [kind, setKind] = useState<'full' | 'draft'>('full')
  const [size, setSize] = useState<'n' | 's'>('n')
  const [epochs, setEpochs] = useState(60)
  const [camera, setCamera] = useState<string>('all')
  const [when, setWhen] = useState<'now' | 'later'>('now')
  const [at, setAt] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (open && preselect) setSel([preselect])
  }, [open, preselect])

  const submit = async () => {
    setBusy(true)
    try {
      const jobs = await api.post<Job[]>('/training/jobs', {
        product_ids: sel,
        kind,
        model_size: size,
        epochs: kind === 'draft' ? Math.min(epochs, 15) : epochs,
        camera_id: camera === 'all' ? null : Number(camera),
        scheduled_at: when === 'later' && at ? new Date(at).toISOString() : null,
      })
      notify.success(`${jobs.length} ta train navbatga qo'yildi`, 'Train paytida mahsulot sanash to\'xtatiladi')
      void qc.invalidateQueries({ queryKey: ['jobs'] })
      onOpenChange(false)
      if (jobs.length === 1) navigate(`/training/${jobs[0].id}`)
    } catch (e) {
      notify.error("Navbatga qo'yib bo'lmadi", e)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Yangi train</DialogTitle>
          <DialogDescription>Har mahsulot alohida train qilinadi — bir nechtasi tanlansa navbatga alohida job bo'lib tushadi.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 sm:grid-cols-[1fr_240px]">
          <div className="max-h-80 space-y-1 overflow-y-auto rounded-lg border p-2">
            {ready?.map((r) => (
              <label key={r.product_id} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1 hover:bg-accent">
                <Checkbox checked={sel.includes(r.product_id)} onCheckedChange={(v) => setSel(v ? [...sel, r.product_id] : sel.filter((x) => x !== r.product_id))} />
                <span className="flex-1 text-sm">{r.name}</span>
                <span className="num text-xs text-muted-foreground">{r.confirmed} ta</span>
                <ReadinessBadge level={r.level} />
              </label>
            ))}
          </div>
          <div className="space-y-3">
            <SelectField id="kind" label="Turi" value={kind} onChange={setKind} options={[{ value: 'full', label: "To'liq (train + engine)" }, { value: 'draft', label: 'Tez qoralama (avto-belgilash uchun)' }]} />
            <SelectField
              id="cam"
              label="Rasmlar"
              value={camera}
              onChange={setCamera}
              options={[{ value: 'all', label: 'Barcha kameralar (umumiy)' }, ...(cams ?? []).map((c) => ({ value: String(c.id), label: `Faqat: ${c.name}` }))]}
            />
            <div className="space-y-1">
              <Label className="text-sm">Qachon</Label>
              <div className="flex gap-3 text-sm">
                <label className="flex items-center gap-1.5">
                  <input type="radio" checked={when === 'now'} onChange={() => setWhen('now')} /> Hozir
                </label>
                <label className="flex items-center gap-1.5">
                  <input type="radio" checked={when === 'later'} onChange={() => setWhen('later')} /> Belgilangan vaqtda
                </label>
              </div>
              {when === 'later' && <Input type="datetime-local" value={at} onChange={(e) => setAt(e.target.value)} className="h-8" />}
            </div>
            <Advanced>
              <SelectField id="size" label="Model o'lchami" value={size} onChange={setSize} options={[{ value: 'n', label: 'YOLO26n (tez)' }, { value: 's', label: 'YOLO26s (aniqroq)' }]} />
              <NumberField id="ep" label="Epochlar" value={epochs} onChange={(v) => setEpochs(v ?? 60)} min={1} max={500} />
            </Advanced>
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Bekor qilish
          </Button>
          <Button onClick={submit} disabled={!sel.length || busy || (when === 'later' && !at)}>
            {busy ? <Loader2 className="animate-spin" /> : <Play />} Navbatga qo'yish ({sel.length})
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
