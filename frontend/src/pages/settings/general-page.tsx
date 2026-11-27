import { DatabaseBackup, FolderOpen, HardDrive, RotateCcw, Save, ScrollText, TriangleAlert } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { NumberField } from '@/components/common/fields'
import { Progress } from '@/components/common/progress'
import { StatusBadge } from '@/components/common/status-badge'
import { PageBody, PageHeader, useRouteTitle } from '@/components/layout/page'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useHealth } from '@/hooks/use-health'
import { param, useUrlState } from '@/hooks/use-url-state'
import { api } from '@/lib/api'
import { fmtDateTime } from '@/lib/format'
import { notify } from '@/lib/notify'
import { cn } from '@/lib/utils'
import { AutostartPanel } from './autostart-panel'

type Info = {
  disk: { total: number; used: number; free: number; free_pct: number }
  folders: Record<string, number>
  cpu_pct: number
  cpu_count: number
  ram: { total: number; used: number; pct: number }
  inference: Record<string, string>
  backup: { status: string; message: string; ts: number; last_success_ts: number | null; files: { name: string; size: number }[]; last_verify?: { ts: number; status: string; message: string } } | null
}
const GB = (b: number) => `${(b / 2 ** 30).toFixed(1)} GB`
const FOLDER: Record<string, string> = { images: 'Vazifa rasmlari (standart papka)', snapshots: 'Sanoq snapshotlari', datasets: 'Datasetlar', models: 'Modellar', engines: "Engine'lar", logs: 'Loglar', backups: 'Zaxira nusxalar', equipment: 'Uskuna kadrlari' }

type Storage = {
  images_root: string
  resolved: string
  default: string
  exists: boolean
  writable: boolean
  disk: { total: number; free: number } | null
  layout: string
  tasks: { camera_id: number; camera_name: string; task_type: 'counting' | 'equipment'; enabled: boolean; path: string; exists: boolean; size: number; files: number }[]
}
const TASK_LABEL: Record<string, string> = { counting: 'Mahsulot sanash', equipment: 'Uskuna ish vaqti' }
const size = (b: number) => (b > 2 ** 30 ? GB(b) : `${(b / 2 ** 20).toFixed(b > 0 && b < 2 ** 20 ? 2 : 0)} MB`)

function ImagesFolder() {
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ['sys-storage'], queryFn: () => api.get<Storage>('/system/storage'), refetchInterval: 30000 })
  const [value, setValue] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  if (!data) return <Skeleton className="h-48 w-full lg:col-span-2" />
  const v = value ?? data.images_root
  const dirty = v.trim() !== data.images_root
  const save = async (next: string) => {
    setSaving(true)
    try {
      const res = await api.put<Storage>('/system/storage', { images_root: next.trim() })
      qc.setQueryData(['sys-storage'], res)
      setValue(null)
      notify.success('Rasmlar papkasi saqlandi', `Yangi rasmlar: ${res.resolved}`)
    } catch (e) {
      notify.error("Papkani saqlab bo'lmadi", e)
    } finally {
      setSaving(false)
    }
  }
  return (
    <Card className="lg:col-span-2">
      <CardHeader><CardTitle className="flex items-center gap-2 text-base"><FolderOpen className="size-4" /> Rasmlar papkasi</CardTitle></CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="space-y-1">
          <Label htmlFor="images-root">Umumiy papka</Label>
          <div className="flex flex-wrap gap-2">
            <Input id="images-root" className="h-8 min-w-64 flex-1 font-mono text-xs" value={v} placeholder={data.default} onChange={(e) => setValue(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && dirty) void save(v) }} />
            <Button size="sm" disabled={!dirty || saving} onClick={() => void save(v)}><Save /> Saqlash</Button>
            {data.images_root && <Button size="sm" variant="outline" disabled={saving} onClick={() => void save('')}><RotateCcw /> Standart</Button>}
          </div>
          <p className="text-xs text-muted-foreground">
            Mutlaq yo'l (masalan, <code>/mnt/disk2/fcv-images</code>) yoki <code>data/</code> ga nisbatan yo'l. Bo'sh — standart papka. Har bir vazifa alohida papkada: <code>{data.layout}</code>. Papka o'zgarsa eski rasmlar joyida qoladi, yangilari yangi papkaga yoziladi.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <span>Hozir saqlanmoqda: <code className="font-mono text-xs">{data.resolved}</code></span>
          <StatusBadge size="sm" status={data.writable ? 'ok' : data.exists ? 'error' : 'warn'} label={data.writable ? 'Yozish mumkin' : data.exists ? "Yozish huquqi yo'q" : 'Hali yaratilmagan'} />
          {data.disk && <span className="num text-muted-foreground">{GB(data.disk.free)} bo'sh / {GB(data.disk.total)}</span>}
        </div>
        {data.tasks.length === 0 ? (
          <p className="text-muted-foreground">Kamera qo'shilmagan — vazifa papkalari kamera qo'shilgach paydo bo'ladi.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow><TableHead>Kamera</TableHead><TableHead>Vazifa</TableHead><TableHead>Papka</TableHead><TableHead className="text-right">Rasmlar</TableHead><TableHead className="text-right">Hajm</TableHead></TableRow>
            </TableHeader>
            <TableBody>
              {data.tasks.map((t) => (
                <TableRow key={`${t.camera_id}-${t.task_type}`} className={cn(!t.enabled && !t.exists && 'text-muted-foreground')}>
                  <TableCell className="py-1.5">{t.camera_name}</TableCell>
                  <TableCell className="py-1.5">{TASK_LABEL[t.task_type] ?? t.task_type}{t.enabled && <StatusBadge className="ml-2" size="sm" status="ok" label="yoqilgan" />}</TableCell>
                  <TableCell className="py-1.5 font-mono text-xs break-all">{t.path}</TableCell>
                  <TableCell className="num py-1.5 text-right">{t.exists ? t.files : '—'}</TableCell>
                  <TableCell className="num py-1.5 text-right">{t.exists ? size(t.size) : '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}

function Settings() {
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ['sys-settings'], queryFn: () => api.get<Record<string, Record<string, number> | number>>('/system/settings') })
  const [v, setV] = useState<Record<string, Record<string, number> | number> | null>(null)
  useEffect(() => setV(data ?? null), [data])
  if (!v) return <Skeleton className="h-40 w-full" />
  const r = v['dataset.readiness'] as Record<string, number>
  const tr = v['training.defaults'] as Record<string, number>
  const save = async (key: string) => {
    try {
      await api.put(`/system/settings/${key}`, { value: v[key] })
      notify.success('Saqlandi')
      void qc.invalidateQueries({ queryKey: ['sys-settings'] })
    } catch (e) {
      notify.error("Saqlab bo'lmadi", e)
    }
  }
  const set = (key: string, sub: string | null, val: number | null) =>
    setV({ ...v, [key]: sub ? { ...(v[key] as Record<string, number>), [sub]: val ?? 0 } : (val ?? 0) })
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader><CardTitle className="text-base">Tayyorlik indikatori</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <NumberField id="rmin" label="Minimal (ramka)" value={r.minimal} onChange={(x) => set('dataset.readiness', 'minimal', x)} min={1} />
            <NumberField id="rready" label="Tayyor (ramka)" value={r.ready} onChange={(x) => set('dataset.readiness', 'ready', x)} min={1} />
          </div>
          <Button size="sm" onClick={() => void save('dataset.readiness')}><Save /> Saqlash</Button>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle className="text-base">Train standart parametrlari</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <NumberField id="ep" label="Epochlar" value={tr.epochs} onChange={(x) => set('training.defaults', 'epochs', x)} min={1} />
            <NumberField id="bs" label="Batch" value={tr.batch} onChange={(x) => set('training.defaults', 'batch', x)} min={1} />
            <NumberField id="neg" label="Negativ nisbati" value={tr.negative_ratio} onChange={(x) => set('training.defaults', 'negative_ratio', x)} step={0.1} min={0} />
          </div>
          <Button size="sm" onClick={() => void save('training.defaults')}><Save /> Saqlash</Button>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle className="text-base">GPU va Telegram</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <NumberField id="ml" label="Inference byudjeti" unit="inference/s" value={v['inference.max_load'] as number} onChange={(x) => set('inference.max_load', null, x)} min={10} hint="Oshsa UI ogohlantiradi; kechikish katta bo'lsa fps avtomatik pasayadi" />
          <Button size="sm" onClick={() => void save('inference.max_load')}><Save /> Saqlash</Button>
          <NumberField id="ttl" label="Telegram xabari yashash muddati" unit="soat" value={v['telegram.outbox_ttl_hours'] as number} onChange={(x) => set('telegram.outbox_ttl_hours', null, x)} min={1} />
          <Button size="sm" onClick={() => void save('telegram.outbox_ttl_hours')}><Save /> Saqlash</Button>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle className="text-base">Disk ogohlantirishi</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <NumberField id="dw" label="Bo'sh joy chegarasi" unit="%" value={v['system.disk_warn_free_pct'] as number} onChange={(x) => set('system.disk_warn_free_pct', null, x)} min={1} max={50} />
          <Button size="sm" onClick={() => void save('system.disk_warn_free_pct')}><Save /> Saqlash</Button>
        </CardContent>
      </Card>
    </div>
  )
}

export function GeneralPage() {
  const title = useRouteTitle()
  const [tab, setTab] = useUrlState('tab', param.oneOf(['status', 'autostart', 'logs', 'events', 'params'] as const), 'status')
  const { data: info } = useQuery({ queryKey: ['sys-info'], queryFn: () => api.get<Info>('/system/info'), refetchInterval: 10000 })
  const { data: health } = useHealth()
  const { data: logs } = useQuery({ queryKey: ['sys-logs'], queryFn: () => api.get<{ ts: string; level: string; process: string; logger: string; message: string }[]>('/system/logs', { query: { level: 'WARNING', limit: 200 } }), enabled: tab === 'logs', refetchInterval: 15000 })
  const { data: events } = useQuery({ queryKey: ['sys-events'], queryFn: () => api.get<{ id: number; ts: string; level: string; source: string; kind: string; message: string }[]>('/system/events', { query: { limit: 200 } }), enabled: tab === 'events', refetchInterval: 15000 })
  const gpu = health?.gpu.data.gpus?.[0]
  const usedPct = info ? 100 - info.disk.free_pct : 0

  return (
    <PageBody>
      <PageHeader title={title} description="Server holati, disk, avtomatik ishga tushish, zaxira nusxalar, xatolar va umumiy parametrlar." />
      <Tabs value={tab} onValueChange={(x) => setTab(x as typeof tab)} className="mb-4">
        <TabsList>
          <TabsTrigger value="status">Holat</TabsTrigger>
          <TabsTrigger value="autostart">Avtomatik ishga tushish</TabsTrigger>
          <TabsTrigger value="logs">Xatolar</TabsTrigger>
          <TabsTrigger value="events">Hodisalar jurnali</TabsTrigger>
          <TabsTrigger value="params">Parametrlar</TabsTrigger>
        </TabsList>
      </Tabs>
      {tab === 'status' && (!info ? <Skeleton className="h-64 w-full" /> : (
        <div className="grid gap-4 lg:grid-cols-2">
          <ImagesFolder />
          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2 text-base"><HardDrive className="size-4" /> Disk</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between text-sm"><span>{GB(info.disk.used)} / {GB(info.disk.total)}</span><span className="num">{GB(info.disk.free)} bo'sh ({info.disk.free_pct}%)</span></div>
              <Progress value={usedPct} tone={info.disk.free_pct < 10 ? 'danger' : info.disk.free_pct < 20 ? 'warning' : 'success'} />
              {info.disk.free_pct < 10 && <p className="flex items-center gap-1 text-sm text-danger"><TriangleAlert className="size-4" /> Diskda joy kam — eski snapshotlarni ko'chiring yoki disk qo'shing.</p>}
              <Table>
                <TableBody>
                  {Object.entries(info.folders).map(([k, b]) => (
                    <TableRow key={k}><TableCell className="py-1.5">{FOLDER[k] ?? k}</TableCell><TableCell className="num py-1.5 text-right">{b > 2 ** 30 ? GB(b) : `${(b / 2 ** 20).toFixed(0)} MB`}</TableCell></TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle className="text-base">Resurslar</CardTitle></CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div><div className="flex justify-between"><span>CPU ({info.cpu_count} thread)</span><span className="num">{info.cpu_pct.toFixed(0)}%</span></div><Progress value={info.cpu_pct} /></div>
              <div><div className="flex justify-between"><span>RAM</span><span className="num">{GB(info.ram.used)} / {GB(info.ram.total)}</span></div><Progress value={info.ram.pct} /></div>
              {gpu && (
                <>
                  <div><div className="flex justify-between"><span>GPU ({gpu.name})</span><span className="num">{gpu.util_pct}% · {gpu.temp_c}°C</span></div><Progress value={gpu.util_pct} tone={gpu.temp_c > 80 ? 'warning' : 'primary'} /></div>
                  <div><div className="flex justify-between"><span>VRAM</span><span className="num">{(gpu.mem_used_mb / 1024).toFixed(1)} / {(gpu.mem_total_mb / 1024).toFixed(0)} GB</span></div><Progress value={(gpu.mem_used_mb / gpu.mem_total_mb) * 100} /></div>
                </>
              )}
              <div className="text-muted-foreground">Inference: {info.inference.rps ?? 0}/s · {info.inference.latency_ms ?? 0} ms · {info.inference.engines ?? 0} engine</div>
            </CardContent>
          </Card>
          <Card className="lg:col-span-2">
            <CardHeader><CardTitle className="flex items-center gap-2 text-base"><DatabaseBackup className="size-4" /> Zaxira nusxa</CardTitle></CardHeader>
            <CardContent className="space-y-1 text-sm">
              {info.backup ? (
                <>
                  <div className="flex items-center gap-2"><StatusBadge status={info.backup.status === 'ok' ? 'ok' : 'error'} label={info.backup.status === 'ok' ? 'Muvaffaqiyatli' : 'Xato'} size="sm" /> {info.backup.message}</div>
                  <div>Oxirgi muvaffaqiyatli zaxira: <b>{info.backup.last_success_ts ? fmtDateTime(info.backup.last_success_ts) : '—'}</b> {info.backup.files.map((f) => `· ${f.name} (${(f.size / 2 ** 20).toFixed(1)} MB)`).join(' ')}</div>
                  {info.backup.last_verify && <div className="text-muted-foreground">Tiklash sinovi: {fmtDateTime(info.backup.last_verify.ts)} — {info.backup.last_verify.message}</div>}
                </>
              ) : (
                <p className="text-warning">Zaxira hali olinmagan. Har kuni 03:30 da avtomatik (systemd timer) yoki `scripts/backup.sh`.</p>
              )}
            </CardContent>
          </Card>
        </div>
      ))}
      {tab === 'logs' && (
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2 text-base"><ScrollText className="size-4" /> Oxirgi xato va ogohlantirishlar</CardTitle></CardHeader>
          <CardContent className="space-y-1">
            {!logs?.length && <p className="text-sm text-muted-foreground">Xato yo'q.</p>}
            {logs?.map((l, i) => (
              <details key={i} className="rounded-md border px-2 py-1 text-xs">
                <summary className="cursor-pointer">
                  <span className="num text-muted-foreground">{l.ts}</span> <span className={cn('font-semibold', l.level === 'ERROR' || l.level === 'CRITICAL' ? 'text-danger' : 'text-warning')}>{l.level}</span> <span className="text-muted-foreground">[{l.process}]</span> {l.message.split('\n')[0].slice(0, 200)}
                </summary>
                <pre className="mt-1 overflow-x-auto font-mono whitespace-pre-wrap text-muted-foreground">{l.logger}: {l.message}</pre>
              </details>
            ))}
          </CardContent>
        </Card>
      )}
      {tab === 'events' && (
        <Card>
          <CardContent className="pt-4">
            <Table>
              <TableBody>
                {events?.map((e) => (
                  <TableRow key={e.id}>
                    <TableCell className="num w-44 text-xs">{fmtDateTime(e.ts)}</TableCell>
                    <TableCell className="w-32"><StatusBadge size="sm" status={e.level === 'error' ? 'error' : e.level === 'warning' ? 'warn' : 'ok'} label={e.source || e.kind} /></TableCell>
                    <TableCell className="text-sm">{e.message}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
      {tab === 'autostart' && <AutostartPanel />}
      {tab === 'params' && <Settings />}
    </PageBody>
  )
}
