import { CircleCheck, CircleX, Loader2, Radar, RefreshCw, Save, Search, Trash2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useConfirm } from '@/components/common/confirm-dialog'
import { EmptyState, ErrorState } from '@/components/common/states'
import { HintIcon } from '@/components/common/term'
import { PageBody, PageHeader, useRouteTitle } from '@/components/layout/page'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { previewFrames, probeStream, useCamera, useDeleteCamera, useSaveCamera, type CameraInput } from '@/hooks/use-cameras'
import { useUnsavedGuard } from '@/hooks/use-unsaved-guard'
import { param, useUrlState } from '@/hooks/use-url-state'
import { api, errorMessage } from '@/lib/api'
import { resolution } from '@/lib/format'
import { notify } from '@/lib/notify'
import type { ProbeResult } from '@/lib/types'
import { useQueryClient } from '@tanstack/react-query'

type Discovered = { host: string; port: number; manufacturer: string | null; model: string | null; name: string | null; already_added: boolean }
type Profile = { token: string; name: string; width: number | null; height: number | null; fps: number | null; codec: string | null; rtsp_url: string | null }
type DeviceInfo = {
  manufacturer: string | null
  model: string | null
  serial: string | null
  firmware: string | null
  profiles: Profile[]
  suggested_main: string | null
  suggested_sub: string | null
  time_offset_sec: number | null
}

const EMPTY: CameraInput = { name: '', main_rtsp_url: '', sub_rtsp_url: '', fov_match: false, enabled: true }

function ProbeChip({ r, loading }: { r?: ProbeResult | null; loading?: boolean }) {
  if (loading)
    return (
      <span className="flex items-center gap-1 text-xs text-muted-foreground">
        <Loader2 className="size-3.5 animate-spin" /> Tekshirilmoqda…
      </span>
    )
  if (!r) return null
  if (!r.ok)
    return (
      <span className="flex items-center gap-1 text-xs text-danger" role="alert">
        <CircleX className="size-3.5 shrink-0" /> {r.error}
      </span>
    )
  return (
    <span className="num flex items-center gap-1 text-xs text-success">
      <CircleCheck className="size-3.5" /> {r.codec?.toUpperCase()} · {resolution(r.width, r.height)} · {r.fps ?? '?'} fps
    </span>
  )
}

function UrlField({
  id,
  label,
  value,
  onChange,
  optional,
  cameraId,
  kind,
}: {
  id: string
  label: string
  value: string
  onChange: (v: string) => void
  optional?: boolean
  cameraId?: number
  kind: 'main' | 'sub'
}) {
  const [res, setRes] = useState<ProbeResult | null>(null)
  const [loading, setLoading] = useState(false)
  const test = async () => {
    setLoading(true)
    setRes(null)
    try {
      setRes(await probeStream({ url: value, camera_id: cameraId, kind }))
    } catch (e) {
      setRes({ ok: false, error: errorMessage(e), codec: null, width: null, height: null, fps: null })
    } finally {
      setLoading(false)
    }
  }
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>
        {label} {optional && <span className="font-normal text-muted-foreground">(ixtiyoriy)</span>}
      </Label>
      <div className="flex gap-2">
        <Input
          id={id}
          value={value}
          onChange={(e) => {
            onChange(e.target.value)
            setRes(null)
          }}
          placeholder="rtsp://login:parol@192.168.1.10:554/stream1"
          className="font-mono text-sm"
          autoComplete="off"
          spellCheck={false}
        />
        <Button type="button" variant="outline" onClick={test} disabled={!value || loading}>
          Tekshirish
        </Button>
      </div>
      <ProbeChip r={res} loading={loading} />
    </div>
  )
}

function OnvifPanel({ onApply }: { onApply: (data: Partial<CameraInput>, info: DeviceInfo) => void }) {
  const [devices, setDevices] = useState<Discovered[] | null>(null)
  const [scanning, setScanning] = useState(false)
  const [host, setHost] = useState('')
  const [port, setPort] = useState('80')
  const [user, setUser] = useState('admin')
  const [pass, setPass] = useState('')
  const [info, setInfo] = useState<DeviceInfo | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [connecting, setConnecting] = useState(false)
  const [mainTok, setMainTok] = useState<string | null>(null)
  const [subTok, setSubTok] = useState<string | null>(null)

  const scan = async () => {
    setScanning(true)
    try {
      setDevices(await api.get<Discovered[]>('/onvif/discover', { query: { timeout: 3 }, timeoutMs: 20000 }))
    } catch (e) {
      notify.error('Qidirib bo\'lmadi', e)
    } finally {
      setScanning(false)
    }
  }

  const connect = async () => {
    setConnecting(true)
    setErr(null)
    setInfo(null)
    try {
      const d = await api.post<DeviceInfo>('/onvif/device', { host, port: Number(port) || 80, username: user, password: pass }, { timeoutMs: 30000 })
      setInfo(d)
      setMainTok(d.suggested_main)
      setSubTok(d.suggested_sub)
    } catch (e) {
      setErr(errorMessage(e))
    } finally {
      setConnecting(false)
    }
  }

  const apply = () => {
    if (!info) return
    const m = info.profiles.find((p) => p.token === mainTok)
    const s = info.profiles.find((p) => p.token === subTok)
    if (!m?.rtsp_url) return
    onApply(
      {
        main_rtsp_url: m.rtsp_url,
        sub_rtsp_url: s?.rtsp_url ?? '',
        connection_type: 'onvif',
        onvif_host: host,
        onvif_port: Number(port) || 80,
        onvif_username: user,
        onvif_password: pass,
        onvif_manufacturer: info.manufacturer,
        onvif_model: info.model,
        onvif_serial: info.serial,
        onvif_main_profile: m.token,
        onvif_sub_profile: s?.token ?? null,
      },
      info,
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">1. Kamerani toping</CardTitle>
        <CardDescription>Tarmoqdan qidiring yoki IP manzilni qo'lda kiriting (kamera boshqa tarmoq segmentida bo'lsa).</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2">
          <Button type="button" variant="outline" onClick={scan} disabled={scanning}>
            {scanning ? <Loader2 className="animate-spin" /> : <Radar />} Tarmoqdan qidirish
          </Button>
          {devices && <span className="text-sm text-muted-foreground">{devices.length} ta qurilma topildi</span>}
        </div>
        {devices && devices.length > 0 && (
          <div className="max-h-64 overflow-auto rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>IP</TableHead>
                  <TableHead>Ishlab chiqaruvchi / model</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {devices.map((d) => (
                  <TableRow key={d.host} className={host === d.host ? 'bg-accent' : undefined}>
                    <TableCell className="num font-mono text-sm">{d.host}</TableCell>
                    <TableCell className="text-sm">
                      {d.manufacturer ?? d.name ?? '—'} <span className="text-muted-foreground">{d.model}</span>
                      {d.already_added && <Badge variant="secondary" className="ml-2">qo'shilgan</Badge>}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button type="button" size="xs" variant="ghost" onClick={() => { setHost(d.host); setPort(String(d.port)) }}>
                        Tanlash
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
        <div className="grid gap-3 sm:grid-cols-[1fr_100px]">
          <div className="space-y-1.5">
            <Label htmlFor="onvif-host">IP manzil</Label>
            <Input id="onvif-host" value={host} onChange={(e) => setHost(e.target.value)} placeholder="192.168.1.10" className="font-mono" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="onvif-port">Port</Label>
            <Input id="onvif-port" value={port} onChange={(e) => setPort(e.target.value)} className="num" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="onvif-user">Login</Label>
            <Input id="onvif-user" value={user} onChange={(e) => setUser(e.target.value)} autoComplete="off" />
          </div>
          <div className="space-y-1.5 sm:col-span-1">
            <Label htmlFor="onvif-pass">Parol</Label>
            <Input id="onvif-pass" type="password" value={pass} onChange={(e) => setPass(e.target.value)} autoComplete="new-password" />
          </div>
        </div>
        <Button type="button" onClick={connect} disabled={!host || connecting}>
          {connecting ? <Loader2 className="animate-spin" /> : <Search />} Ulanish va profillarni o'qish
        </Button>
        {err && <p className="text-sm text-danger" role="alert">{err}</p>}
        {info && (
          <div className="space-y-3">
            <div className="text-sm">
              <span className="font-medium">{info.manufacturer} {info.model}</span>
              <span className="text-muted-foreground"> · seriya: {info.serial ?? '—'} · proshivka: {info.firmware ?? '—'}</span>
              {info.time_offset_sec != null && Math.abs(info.time_offset_sec) > 30 && (
                <div className="text-xs text-warning">Kamera soati {Math.round(info.time_offset_sec)} s farq qiladi — hisobga olindi (hisobotlar server vaqtida).</div>
              )}
            </div>
            <div className="overflow-hidden rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Profil</TableHead>
                    <TableHead>O'lcham</TableHead>
                    <TableHead>FPS</TableHead>
                    <TableHead>Kodek</TableHead>
                    <TableHead className="text-center">Asosiy</TableHead>
                    <TableHead className="text-center">Sub</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {info.profiles.map((p) => (
                    <TableRow key={p.token}>
                      <TableCell className="text-sm">{p.name}</TableCell>
                      <TableCell className="num text-sm">{resolution(p.width, p.height)}</TableCell>
                      <TableCell className="num text-sm">{p.fps ?? '—'}</TableCell>
                      <TableCell className="text-sm">{p.codec ?? '—'}</TableCell>
                      <TableCell className="text-center">
                        <input type="radio" name="main" checked={mainTok === p.token} onChange={() => setMainTok(p.token)} disabled={!p.rtsp_url} aria-label={`${p.name} — asosiy`} />
                      </TableCell>
                      <TableCell className="text-center">
                        <input type="radio" name="sub" checked={subTok === p.token} onChange={() => setSubTok(p.token)} disabled={!p.rtsp_url} aria-label={`${p.name} — sub`} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <Button type="button" variant="secondary" onClick={apply} disabled={!mainTok}>
              Manzillarni to'ldirish
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export function CameraFormPage() {
  const params = useParams()
  const id = params.id ? Number(params.id) : undefined
  const isEdit = !!id
  const title = useRouteTitle()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const confirm = useConfirm()
  const { data: cam, isLoading, error, refetch } = useCamera(id)
  const save = useSaveCamera()
  const del = useDeleteCamera()
  const [via, setVia] = useUrlState('via', param.oneOf(['rtsp', 'onvif'] as const), 'rtsp', { push: true })
  const [form, setForm] = useState<CameraInput>(EMPTY)
  const [initial, setInitial] = useState<CameraInput>(EMPTY)
  const [preview, setPreview] = useState<{ main: string | null; sub: string | null; main_error: string | null; sub_error: string | null } | null>(null)
  const [previewing, setPreviewing] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (cam) {
      const v: CameraInput = {
        name: cam.name,
        enabled: cam.enabled,
        main_rtsp_url: cam.main_rtsp_url,
        sub_rtsp_url: cam.sub_rtsp_url ?? '',
        fov_match: cam.fov_match,
      }
      setForm(v)
      setInitial(v)
    }
  }, [cam])

  const dirty = useMemo(() => JSON.stringify(form) !== JSON.stringify(initial), [form, initial])
  useUnsavedGuard(dirty && !save.isPending && !save.isSuccess)
  const set = (patch: Partial<CameraInput>) => setForm((f) => ({ ...f, ...patch }))

  const doPreview = async () => {
    setPreviewing(true)
    try {
      setPreview(await previewFrames({ main_url: form.main_rtsp_url || null, sub_url: form.sub_rtsp_url || null, camera_id: id }))
    } catch (e) {
      notify.error('Kadr olib bo\'lmadi', e)
    } finally {
      setPreviewing(false)
    }
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const errs: Record<string, string> = {}
    if (!form.name.trim()) errs.name = 'Kamera nomini kiriting'
    if (!form.main_rtsp_url.trim()) errs.main = 'Asosiy oqim manzilini kiriting'
    setErrors(errs)
    if (Object.keys(errs).length) return
    const data: CameraInput = { ...form, name: form.name.trim(), sub_rtsp_url: form.sub_rtsp_url?.trim() || null }
    if (isEdit && !data.sub_rtsp_url && cam?.sub_rtsp_url) data.clear_sub = true
    try {
      const saved = await save.mutateAsync({ id, data })
      setInitial(form)
      notify.success(isEdit ? 'Kamera saqlandi' : `"${saved.name}" qo'shildi`)
      navigate(isEdit ? '/settings/cameras' : `/cameras/${saved.id}`)
    } catch (err) {
      notify.error('Saqlab bo\'lmadi', err)
    }
  }

  const onvifRefresh = async () => {
    if (!id) return
    setRefreshing(true)
    try {
      await api.post(`/onvif/cameras/${id}/refresh`, undefined, { timeoutMs: 40000 })
      await qc.invalidateQueries({ queryKey: ['cameras'] })
      await refetch()
      notify.success('ONVIF orqali yangilandi')
    } catch (e) {
      notify.error('ONVIF orqali yangilab bo\'lmadi', e)
    } finally {
      setRefreshing(false)
    }
  }

  const remove = async () => {
    if (!cam) return
    if (!(await confirm({ title: `"${cam.name}" o'chirilsinmi?`, description: "Bu amalni qaytarib bo'lmaydi.", destructive: true, confirmText: "O'chirish" }))) return
    await del.mutateAsync(cam.id)
    setInitial(form)
    notify.success("Kamera o'chirildi")
    navigate('/settings/cameras')
  }

  if (isEdit && error) return <ErrorState error={error} onRetry={() => refetch()} />
  if (isEdit && isLoading)
    return (
      <PageBody className="max-w-4xl space-y-4">
        <Skeleton className="h-8 w-60" />
        <Skeleton className="h-80 w-full" />
      </PageBody>
    )
  if (isEdit && !cam) return <EmptyState title="Kamera topilmadi" />

  return (
    <PageBody className="max-w-4xl">
      <PageHeader
        title={isEdit ? `${cam?.name} — tahrirlash` : title}
        description={isEdit ? undefined : 'RTSP — asosiy usul (manzillarni kiriting). ONVIF — tarmoqdan topib, manzillarni avtomatik olish.'}
        actions={
          isEdit && (
            <>
              {cam?.onvif?.host && (
                <Button variant="outline" onClick={onvifRefresh} disabled={refreshing}>
                  {refreshing ? <Loader2 className="animate-spin" /> : <RefreshCw />} ONVIF orqali yangilash
                </Button>
              )}
              <Button variant="ghost" className="text-danger" onClick={remove}>
                <Trash2 /> O'chirish
              </Button>
            </>
          )
        }
      />
      {!isEdit && (
        <Tabs value={via} onValueChange={(v) => setVia(v as 'rtsp' | 'onvif')} className="mb-4">
          <TabsList>
            <TabsTrigger value="rtsp">RTSP manzillari</TabsTrigger>
            <TabsTrigger value="onvif">ONVIF orqali</TabsTrigger>
          </TabsList>
        </Tabs>
      )}
      <form onSubmit={submit} className="space-y-4">
        {!isEdit && via === 'onvif' && (
          <OnvifPanel
            onApply={(d, info) => {
              set({ ...d, name: form.name || [info.manufacturer, info.model].filter(Boolean).join(' ') })
              notify.success('Manzillar to\'ldirildi — kadrlarni solishtiring va saqlang')
            }}
          />
        )}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">{!isEdit && via === 'onvif' ? '2. Ma\'lumotlar' : 'Kamera'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-[1fr_auto]">
              <div className="space-y-1.5">
                <Label htmlFor="name">Nomi</Label>
                <Input id="name" value={form.name} onChange={(e) => set({ name: e.target.value })} placeholder="Masalan: Liniya-1 kirish" aria-invalid={!!errors.name} autoFocus={!isEdit && via === 'rtsp'} />
                {errors.name && <p className="text-xs text-danger">{errors.name}</p>}
              </div>
              <div className="flex items-end gap-2 pb-2">
                <Switch id="enabled" checked={form.enabled ?? true} onCheckedChange={(v) => set({ enabled: v })} />
                <Label htmlFor="enabled">Faol</Label>
              </div>
            </div>
            <UrlField id="main" label="Asosiy oqim (main)" value={form.main_rtsp_url} onChange={(v) => set({ main_rtsp_url: v })} cameraId={id} kind="main" />
            {errors.main && <p className="-mt-2 text-xs text-danger">{errors.main}</p>}
            <UrlField id="sub" label="Sub oqim" optional value={form.sub_rtsp_url ?? ''} onChange={(v) => set({ sub_rtsp_url: v })} cameraId={id} kind="sub" />
            <p className="text-xs text-muted-foreground">Sub kiritilmasa, hamma ish asosiy oqimdan bajariladi (kameralar panelida ham).</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-1 text-lg">
              Ko'rish maydoni <HintIcon id="fovMatch" />
            </CardTitle>
            <CardDescription>Asosiy va sub oqim kadrlarini yonma-yon ko'ring: ikkalasi bir xil sohani ko'rsatsa, belgini qo'ying.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button type="button" variant="outline" onClick={doPreview} disabled={!form.main_rtsp_url || previewing}>
              {previewing ? <Loader2 className="animate-spin" /> : null} Kadrlarni solishtirish
            </Button>
            {preview && (
              <div className="grid gap-3 sm:grid-cols-2">
                {(['main', 'sub'] as const).map((k) => (
                  <figure key={k} className="space-y-1">
                    <figcaption className="text-xs font-medium text-muted-foreground">{k === 'main' ? 'Asosiy oqim' : 'Sub oqim'}</figcaption>
                    {preview[k] ? (
                      <img src={preview[k]!} alt={k} className="aspect-video w-full rounded-md border bg-video-bg object-contain" />
                    ) : (
                      <div className="flex aspect-video items-center justify-center rounded-md border bg-muted p-4 text-center text-xs text-muted-foreground">
                        {preview[`${k}_error`] ?? 'Manzil kiritilmagan'}
                      </div>
                    )}
                  </figure>
                ))}
              </div>
            )}
            <div className="flex items-center gap-2">
              <Checkbox id="fov" checked={!!form.fov_match} onCheckedChange={(v) => set({ fov_match: v === true })} disabled={!form.sub_rtsp_url} />
              <Label htmlFor="fov">Ko'rish maydoni bir xil</Label>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" asChild>
            <Link to="/settings/cameras">Bekor qilish</Link>
          </Button>
          <Button type="submit" disabled={save.isPending}>
            {save.isPending ? <Loader2 className="animate-spin" /> : <Save />} Saqlash
          </Button>
        </div>
      </form>
    </PageBody>
  )
}
