import { CalendarClock, Plus, Save, Trash2, TriangleAlert } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useConfirm } from '@/components/common/confirm-dialog'
import { HintIcon } from '@/components/common/term'
import { PageBody, PageHeader, useRouteTitle } from '@/components/layout/page'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api } from '@/lib/api'
import { fmtDate, fmtDateTime } from '@/lib/format'
import { notify } from '@/lib/notify'

type S = { id?: number; name: string; start_time: string; end_time: string }
type Data = { current: S[]; effective_from: string | null; now: { shift_name: string; shift_date: string } | null; scheduled: { effective_from: string; shifts: S[] }[]; history: { effective_from: string; shifts: S[] }[] }

export function ShiftsPage() {
  const title = useRouteTitle()
  const qc = useQueryClient()
  const confirm = useConfirm()
  const { data } = useQuery({ queryKey: ['shifts'], queryFn: () => api.get<Data>('/shifts') })
  const [rows, setRows] = useState<S[]>([])
  const [when, setWhen] = useState('')
  const [warn, setWarn] = useState<string[]>([])
  useEffect(() => {
    if (data) setRows(data.current.map((s) => ({ name: s.name, start_time: s.start_time, end_time: s.end_time })))
  }, [data])
  useEffect(() => {
    if (!rows.length) return
    const t = setTimeout(() => {
      api.post<{ warnings: string[] }>('/shifts/validate', { shifts: rows }).then((r) => setWarn(r.warnings)).catch((e) => setWarn([String(e.message)]))
    }, 300)
    return () => clearTimeout(t)
  }, [rows])

  const save = async () => {
    const ok = await confirm({
      title: 'Yangi smena jadvali',
      description: `O'zgarish ${when ? fmtDateTime(when) : 'hozirdan'} kuchga kiradi va faqat shundan keyingi hodisalarga ta'sir qiladi. Oldingi ma'lumotlar o'zgarmaydi.`,
      confirmText: 'Saqlash',
    })
    if (!ok) return
    try {
      const r = await api.post<{ warnings: string[] }>('/shifts', { shifts: rows, effective_from: when ? new Date(when).toISOString() : null })
      notify.success('Smena jadvali saqlandi', r.warnings.join('; ') || undefined)
      void qc.invalidateQueries({ queryKey: ['shifts'] })
    } catch (e) {
      notify.error("Saqlab bo'lmadi", e)
    }
  }

  return (
    <PageBody className="max-w-4xl">
      <PageHeader
        title={title}
        description={
          <span className="inline-flex items-center gap-1">
            Yarim tundan o'tuvchi smena boshlangan sanaga tegishli. <HintIcon id="shiftDate" />
          </span>
        }
      />
      <div className="space-y-4">
        {data?.now && (
          <div className="rounded-lg bg-info-muted px-3 py-2 text-sm">
            Hozir: <b>{data.now.shift_name}</b> · smena sanasi {fmtDate(data.now.shift_date)}
          </div>
        )}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Jadval</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {rows.map((r, i) => (
              <div key={i} className="grid grid-cols-[1fr_120px_120px_auto] items-end gap-2">
                <div className="space-y-1">
                  {i === 0 && <Label>Nomi</Label>}
                  <Input value={r.name} onChange={(e) => setRows(rows.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))} className="h-8" />
                </div>
                <div className="space-y-1">
                  {i === 0 && <Label>Boshlanish</Label>}
                  <Input type="time" value={r.start_time} onChange={(e) => setRows(rows.map((x, j) => (j === i ? { ...x, start_time: e.target.value } : x)))} className="num h-8" />
                </div>
                <div className="space-y-1">
                  {i === 0 && <Label>Tugash</Label>}
                  <Input type="time" value={r.end_time} onChange={(e) => setRows(rows.map((x, j) => (j === i ? { ...x, end_time: e.target.value } : x)))} className="num h-8" />
                </div>
                <Button size="icon-sm" variant="ghost" onClick={() => setRows(rows.filter((_, j) => j !== i))} disabled={rows.length <= 1} aria-label="O'chirish">
                  <Trash2 />
                </Button>
              </div>
            ))}
            <Button size="sm" variant="outline" onClick={() => setRows([...rows, { name: `Smena ${rows.length + 1}`, start_time: '08:00', end_time: '16:00' }])} disabled={rows.length >= 6}>
              <Plus /> Smena qo'shish
            </Button>
            {warn.map((w) => (
              <p key={w} className="flex items-center gap-1 text-sm text-warning">
                <TriangleAlert className="size-4" /> {w}
              </p>
            ))}
            <div className="flex flex-wrap items-end gap-3 border-t pt-3">
              <div className="space-y-1">
                <Label className="flex items-center gap-1">
                  <CalendarClock className="size-4" /> Qachondan kuchga kiradi
                </Label>
                <Input type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} className="h-8 w-56" />
                <p className="text-xs text-muted-foreground">Bo'sh — hozirdan</p>
              </div>
              <Button onClick={save} className="ml-auto">
                <Save /> Saqlash
              </Button>
            </div>
          </CardContent>
        </Card>
        {data && data.scheduled.length > 0 && (
          <Card>
            <CardHeader><CardTitle className="text-base">Rejalashtirilgan</CardTitle></CardHeader>
            <CardContent className="space-y-1 text-sm">
              {data.scheduled.map((s) => (
                <div key={s.effective_from}>{fmtDateTime(s.effective_from)}: {s.shifts.map((x) => `${x.name} ${x.start_time}–${x.end_time}`).join(', ')}</div>
              ))}
            </CardContent>
          </Card>
        )}
        <Card>
          <CardHeader><CardTitle className="text-base">O'zgarishlar tarixi</CardTitle></CardHeader>
          <CardContent className="space-y-1 text-sm">
            {data?.history.map((h) => (
              <div key={h.effective_from} className="flex gap-3">
                <span className="w-40 shrink-0 text-muted-foreground">{fmtDateTime(h.effective_from)}</span>
                <span>{h.shifts.map((x) => `${x.name} ${x.start_time}–${x.end_time}`).join(', ')}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </PageBody>
  )
}
