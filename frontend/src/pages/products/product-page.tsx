import { Activity, BrainCircuit, ImagePlus, Images, Loader2, Save, Trash2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useQueryClient } from '@tanstack/react-query'
import { useConfirm } from '@/components/common/confirm-dialog'
import { ReadinessBadge } from '@/components/common/readiness-badge'
import { EmptyState, ErrorState } from '@/components/common/states'
import { HintIcon } from '@/components/common/term'
import { PageBody, PageHeader, useRouteTitle } from '@/components/layout/page'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { useProduct, useReadiness, useSaveProduct, useVersions } from '@/hooks/use-catalog'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { useUnsavedGuard } from '@/hooks/use-unsaved-guard'
import { api, apiFetch } from '@/lib/api'
import { fmtDateTime } from '@/lib/format'
import { notify } from '@/lib/notify'

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-md bg-muted/60 px-3 py-2">
      <div className="text-2xs text-muted-foreground">{label}</div>
      <div className="num text-lg font-semibold">{value}</div>
    </div>
  )
}

export function ProductPage() {
  const params = useParams()
  const id = params.id ? Number(params.id) : undefined
  const isNew = !id
  const routeTitle = useRouteTitle()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const confirm = useConfirm()
  const { data: p, isLoading, error, refetch } = useProduct(id)
  const { data: ready } = useReadiness()
  const { data: versions } = useVersions(id ?? 0)
  const save = useSaveProduct()
  const [form, setForm] = useState({ code: '', name: '', category: '' })
  const [initial, setInitial] = useState(form)
  const fileRef = useRef<HTMLInputElement>(null)
  const [imgVer, setImgVer] = useState(0)
  useDocumentTitle(p?.name ?? routeTitle)

  useEffect(() => {
    if (p) {
      const f = { code: p.code, name: p.name, category: p.category ?? '' }
      setForm(f)
      setInitial(f)
    }
  }, [p])
  const dirty = JSON.stringify(form) !== JSON.stringify(initial)
  useUnsavedGuard(dirty && !save.isPending)

  const r = ready?.find((x) => x.product_id === id)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const out = await save.mutateAsync({ id, data: { code: form.code, name: form.name, category: form.category || null } })
      setInitial(form)
      notify.success(isNew ? `"${out.name}" qo'shildi` : 'Saqlandi')
      if (isNew) navigate(`/products/${out.id}`)
    } catch (err) {
      notify.error("Saqlab bo'lmadi", err)
    }
  }

  const upload = async (f: File) => {
    const fd = new FormData()
    fd.append('file', f)
    try {
      await apiFetch(`/products/${id}/image`, { method: 'PUT', body: fd, timeoutMs: 60000 })
    } catch (e) {
      notify.error("Rasmni yuklab bo'lmadi", e)
      return
    }
    setImgVer((v) => v + 1)
    void qc.invalidateQueries({ queryKey: ['product', id] })
  }

  const remove = async () => {
    if (!p) return
    const ok = await confirm({
      title: `"${p.name}" o'chirilsinmi?`,
      description: "Mahsulot, uning belgilangan ramkalari va model versiyalari o'chiriladi. Bu amalni qaytarib bo'lmaydi.",
      destructive: true,
      confirmText: "O'chirish",
    })
    if (!ok) return
    await api.delete(`/products/${p.id}`)
    setInitial(form)
    void qc.invalidateQueries({ queryKey: ['products'] })
    notify.success("Mahsulot o'chirildi")
    navigate('/products')
  }

  if (!isNew && error) return <ErrorState error={error} onRetry={() => refetch()} />
  if (!isNew && isLoading)
    return (
      <PageBody className="max-w-5xl">
        <Skeleton className="h-64 w-full" />
      </PageBody>
    )
  if (!isNew && !p) return <EmptyState title="Mahsulot topilmadi" />

  return (
    <PageBody className="max-w-5xl">
      <PageHeader
        title={isNew ? routeTitle : p!.name}
        description={isNew ? undefined : <span className="font-mono">{p!.code}</span>}
        actions={
          !isNew && (
            <>
              <Button variant="outline" asChild>
                <Link to={`/dataset?product_id=${id}`}>
                  <Images /> Rasmlari
                </Link>
              </Button>
              <Button variant="outline" asChild>
                <Link to={`/training?new=1&product=${id}`}>
                  <Activity /> Train qilish
                </Link>
              </Button>
              <Button variant="ghost" className="text-danger" onClick={remove}>
                <Trash2 />
              </Button>
            </>
          )
        }
      />
      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Ma'lumotlar</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={submit} className="grid gap-3 sm:grid-cols-[160px_1fr]">
                <div className="space-y-1.5">
                  <Label htmlFor="code">Kod</Label>
                  <Input id="code" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} className="font-mono" required autoFocus={isNew} />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="pname">Nomi</Label>
                  <Input id="pname" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
                </div>
                <div className="space-y-1.5 sm:col-span-2">
                  <Label htmlFor="cat">Kategoriya <span className="font-normal text-muted-foreground">(faqat guruhlash uchun)</span></Label>
                  <Input id="cat" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} placeholder="Masalan: Televizorlar" />
                </div>
                <div className="flex justify-end gap-2 sm:col-span-2">
                  {isNew && (
                    <Button type="button" variant="ghost" asChild>
                      <Link to="/products">Bekor qilish</Link>
                    </Button>
                  )}
                  <Button type="submit" disabled={save.isPending || (!isNew && !dirty)}>
                    {save.isPending ? <Loader2 className="animate-spin" /> : <Save />} Saqlash
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
          {!isNew && (
            <Card>
              <CardHeader className="flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-1 text-lg">
                  Dataset holati <HintIcon id="readiness" />
                </CardTitle>
                {r && <ReadinessBadge level={r.level} />}
              </CardHeader>
              <CardContent className="space-y-3">
                {r ? (
                  <>
                    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                      <Stat label="Tasdiqlangan ramka" value={r.confirmed} />
                      <Stat label="Avto (tasdiqlanmagan)" value={r.auto} />
                      <Stat label="Qutili / qutisiz" value={`${r.boxed} / ${r.unboxed}`} />
                      <Stat label="Tegib turgan" value={r.touching} />
                      <Stat label="Rasmlar" value={r.images} />
                      <Stat label="Negativ rasmlar" value={r.negatives} />
                    </div>
                    <div className="text-sm">
                      <span className="text-muted-foreground">Kameralar bo'yicha: </span>
                      {Object.entries(r.per_camera).map(([k, v]) => `${k} — ${v}`).join(', ') || '—'}
                      <span className="ml-3 text-muted-foreground">Oqimlar: </span>
                      {Object.entries(r.per_stream).map(([k, v]) => `${k === 'main' ? 'asosiy' : 'sub'} — ${v}`).join(', ') || '—'}
                    </div>
                  </>
                ) : (
                  <Skeleton className="h-20 w-full" />
                )}
              </CardContent>
            </Card>
          )}
          {!isNew && (
            <Card>
              <CardHeader className="flex-row items-center justify-between">
                <CardTitle className="text-lg">Model versiyalari</CardTitle>
                <Button variant="outline" size="sm" asChild>
                  <Link to={`/models/${id}`}>
                    <BrainCircuit /> Batafsil
                  </Link>
                </Button>
              </CardHeader>
              <CardContent>
                {!versions?.length ? (
                  <p className="text-sm text-muted-foreground">Hali train qilinmagan.</p>
                ) : (
                  <div className="space-y-1 text-sm">
                    {versions.slice(0, 5).map((v) => (
                      <div key={v.id} className="flex items-center justify-between gap-2">
                        <span>
                          v{v.version} {v.is_draft && <span className="text-xs text-muted-foreground">(qoralama)</span>}
                          {v.is_active && <span className="ml-2 text-xs text-success">faol</span>}
                        </span>
                        <span className="num text-muted-foreground">mAP50 {v.metrics.map50 != null ? Number(v.metrics.map50).toFixed(3) : '—'}</span>
                        <span className="text-xs text-muted-foreground">{fmtDateTime(v.created_at)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
        {!isNew && (
          <Card className="h-fit">
            <CardHeader>
              <CardTitle className="text-lg">Rasm</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {p?.has_image ? (
                <img src={`/api/products/${id}/image?v=${imgVer}`} alt={p.name} className="aspect-square w-full rounded-md border object-contain" />
              ) : (
                <div className="flex aspect-square items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground">Rasm yo'q</div>
              )}
              <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={(e) => e.target.files?.[0] && void upload(e.target.files[0])} />
              <Button variant="outline" className="w-full" onClick={() => fileRef.current?.click()}>
                <ImagePlus /> Rasm yuklash
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </PageBody>
  )
}
