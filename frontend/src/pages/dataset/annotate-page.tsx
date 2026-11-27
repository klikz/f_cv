import type Konva from 'konva'
import { ArrowLeft, ArrowRight, Box, Check, Copy, Loader2, PackageOpen, Search, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Group, Image as KImage, Layer, Rect, Stage, Text, Transformer } from 'react-konva'
import { Link, useLocation, useNavigate, useParams } from 'react-router'
import { useQueryClient } from '@tanstack/react-query'
import { useConfirm } from '@/components/common/confirm-dialog'
import { ErrorState } from '@/components/common/states'
import { HintIcon } from '@/components/common/term'
import { ShortcutsDialog } from '@/components/layout/shortcuts-dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Kbd } from '@/components/ui/kbd'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { useImage, useProducts, type Annotation, type ImageFilters } from '@/hooks/use-catalog'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { api } from '@/lib/api'
import { fmtDateTime } from '@/lib/format'
import { notify } from '@/lib/notify'
import { storage } from '@/lib/storage'
import { cn } from '@/lib/utils'

const PALETTE = ['#60a5fa', '#34d399', '#fbbf24', '#f472b6', '#a78bfa', '#f87171', '#2dd4bf', '#fb923c', '#a3e635', '#e879f9']
const RECENT_KEY = 'fcv.annotate.recent'
const MIN_BOX = 0.008

type Box = Annotation & { key: string }
let keySeq = 0
const k = () => `b${++keySeq}`

function colorFor(pid: number) {
  return PALETTE[pid % PALETTE.length]
}

function useImageEl(src: string | null) {
  const [img, setImg] = useState<HTMLImageElement | null>(null)
  useEffect(() => {
    if (!src) return
    const el = new window.Image()
    el.onload = () => setImg(el)
    el.src = src
    return () => {
      el.onload = null
    }
  }, [src])
  return img
}

const SHORTCUTS = [
  {
    title: 'Belgilash',
    items: [
      { keys: ['Sichqoncha'], label: "Bo'sh joyda sudrash — yangi ramka" },
      { keys: ['1–9'], label: 'Mahsulot (oxirgi ishlatilganlar ro\'yxatidan)' },
      { keys: ['→', 'D'], label: 'Saqlash va keyingi rasm' },
      { keys: ['←', 'A'], label: 'Saqlash va oldingi rasm' },
      { keys: ['Enter'], label: 'Avto takliflarni tasdiqlash va keyingi' },
      { keys: ['Delete'], label: "Tanlangan ramkani o'chirish" },
      { keys: ['B'], label: 'Qutili / qutisiz' },
      { keys: ['T'], label: 'Tegib turgan' },
      { keys: ['E'], label: "Bo'sh rasm (negativ)" },
      { keys: ['C'], label: 'Oldingi rasm ramkalarini nusxalash' },
      { keys: ['Ctrl', 'Z'], label: 'Bekor qilish' },
      { keys: ['/'], label: 'Mahsulot qidirish' },
      { keys: ['0'], label: 'Zoomni tiklash' },
    ],
  },
]

export function AnnotatePage() {
  const imageId = Number(useParams().imageId)
  const location = useLocation()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const confirm = useConfirm()
  const sp = new URLSearchParams(location.search)
  const filters: ImageFilters = {
    camera_id: sp.get('camera_id') ? Number(sp.get('camera_id')) : undefined,
    product_id: sp.get('product_id') ? Number(sp.get('product_id')) : undefined,
    status: sp.get('status') ?? undefined,
    source: sp.get('source') ?? undefined,
    day: sp.get('day') ?? undefined,
  }
  const { data: img, error, refetch, isFetching } = useImage(imageId, filters)
  const { data: products } = useProducts()
  useDocumentTitle(`Belgilash #${imageId}`)

  const [boxes, setBoxes] = useState<Box[]>([])
  const [isEmpty, setIsEmpty] = useState(false)
  const [selected, setSelected] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [recent, setRecent] = useState<number[]>(() => storage.get<number[]>(RECENT_KEY) ?? [])
  const [current, setCurrent] = useState<number | null>(() => (storage.get<number[]>(RECENT_KEY) ?? [])[0] ?? null)
  const [search, setSearch] = useState('')
  const [help, setHelp] = useState(false)
  const history = useRef<Box[][]>([])
  const prevBoxes = useRef<Box[] | null>(null)
  const searchRef = useRef<HTMLInputElement>(null)

  // rasm almashganda holatni yuklash
  const loadedFor = useRef<number | null>(null)
  useEffect(() => {
    if (!img || img.id !== imageId || loadedFor.current === imageId) return
    loadedFor.current = imageId
    setBoxes(img.annotations.map((a) => ({ ...a, key: k() })))
    setIsEmpty(img.is_empty)
    // rasm qaysi mahsulot uchun olingan bo'lsa (yoki filtr) — shu mahsulot tanlanadi
    const pid = img.product_id ?? filters.product_id
    if (pid) setCurrent(pid)
    setSelected(null)
    setDirty(false)
    history.current = []
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [img, imageId])

  const productById = useMemo(() => new Map((products ?? []).map((p) => [p.id, p])), [products])
  const recentList = recent.filter((id) => productById.has(id)).slice(0, 9)

  const pushHistory = () => {
    history.current.push(boxes.map((b) => ({ ...b })))
    if (history.current.length > 50) history.current.shift()
  }
  const update = (next: Box[]) => {
    pushHistory()
    setBoxes(next)
    setDirty(true)
    if (next.length) setIsEmpty(false)
  }
  const pickProduct = (pid: number) => {
    setCurrent(pid)
    const r = [pid, ...recent.filter((x) => x !== pid)].slice(0, 12)
    setRecent(r)
    storage.set(RECENT_KEY, r)
  }

  const save = useCallback(async (): Promise<boolean> => {
    if (!img || !dirty) return true
    setSaving(true)
    try {
      await api.put(`/dataset/images/${img.id}/annotations`, {
        annotations: boxes.map(({ key: _k, ...a }) => a),
        is_empty: isEmpty,
      })
      setDirty(false)
      void qc.invalidateQueries({ queryKey: ['images'] })
      void qc.invalidateQueries({ queryKey: ['readiness'] })
      return true
    } catch (e) {
      notify.error("Saqlab bo'lmadi", e)
      return false
    } finally {
      setSaving(false)
    }
  }, [img, dirty, boxes, isEmpty, qc])

  const go = async (id: number | null | undefined) => {
    if (!id) {
      notify.info("Ro'yxat oxiri")
      return
    }
    if (!(await save())) return
    prevBoxes.current = boxes
    navigate(`/dataset/annotate/${id}${location.search}`)
  }

  const confirmAllAndNext = async () => {
    const next = boxes.map((b) => ({ ...b, status: 'confirmed' as const }))
    setBoxes(next)
    if (!img) return
    try {
      await api.put(`/dataset/images/${img.id}/annotations`, { annotations: next.map(({ key: _k, ...a }) => a), is_empty: isEmpty && !next.length })
      setDirty(false)
      void qc.invalidateQueries({ queryKey: ['images'] })
      prevBoxes.current = next
      if (img.next_id) navigate(`/dataset/annotate/${img.next_id}${location.search}`)
    } catch (e) {
      notify.error("Saqlab bo'lmadi", e)
    }
  }

  const sel = boxes.find((b) => b.key === selected) ?? null

  // klaviatura
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement
      if (t && ['INPUT', 'TEXTAREA'].includes(t.tagName)) {
        if (e.key === 'Escape') (t as HTMLInputElement).blur()
        return
      }
      const key = e.key.toLowerCase()
      if ((e.ctrlKey || e.metaKey) && key === 'z') {
        const prev = history.current.pop()
        if (prev) {
          setBoxes(prev)
          setDirty(true)
        }
        e.preventDefault()
        return
      }
      if (e.ctrlKey || e.metaKey || e.altKey) return
      if (key === 'arrowright' || key === 'd') void go(img?.next_id)
      else if (key === 'arrowleft' || key === 'a') void go(img?.prev_id)
      else if (key === 'enter') void confirmAllAndNext()
      else if ((key === 'delete' || key === 'backspace') && sel) update(boxes.filter((b) => b.key !== sel.key))
      else if (key === 'b' && sel) update(boxes.map((b) => (b.key === sel.key ? { ...b, packaging: b.packaging === 'boxed' ? 'unboxed' : 'boxed', status: 'confirmed' } : b)))
      else if (key === 't' && sel) update(boxes.map((b) => (b.key === sel.key ? { ...b, touching: !b.touching } : b)))
      else if (key === 'e') {
        if (boxes.length) update([])
        setIsEmpty((v) => !v || boxes.length > 0)
        setDirty(true)
      } else if (key === 'c' && prevBoxes.current?.length) update([...boxes, ...prevBoxes.current.map((b) => ({ ...b, key: k(), id: null, status: 'confirmed' as const }))])
      else if (key === '/') {
        searchRef.current?.focus()
        e.preventDefault()
      } else if (key === '?') setHelp(true)
      else if (/^[1-9]$/.test(key)) {
        const pid = recentList[Number(key) - 1]
        if (!pid) return
        pickProduct(pid)
        if (sel) update(boxes.map((b) => (b.key === sel.key ? { ...b, product_id: pid, status: 'confirmed' } : b)))
      } else if (key === 'escape') setSelected(null)
      else return
      e.preventDefault()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  // oldingi/keyingi rasmni oldindan yuklash
  useEffect(() => {
    for (const id of [img?.next_id, img?.prev_id]) if (id) new window.Image().src = `/api/dataset/images/${id}/file`
  }, [img?.next_id, img?.prev_id])

  if (error) return <ErrorState error={error} onRetry={() => refetch()} className="h-full" />

  const filtered = (products ?? []).filter((p) => !search || p.name.toLowerCase().includes(search.toLowerCase()) || p.code.toLowerCase().includes(search.toLowerCase()))
  const backHref = `/dataset${location.search}`

  return (
    <div className="flex h-full min-h-0 flex-1">
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-2 border-b px-3 py-1.5">
          <Button variant="ghost" size="sm" asChild>
            <Link to={backHref}>
              <ArrowLeft /> Dataset
            </Link>
          </Button>
          <Separator orientation="vertical" className="h-4" />
          <Button variant="outline" size="sm" onClick={() => void go(img?.prev_id)} disabled={!img?.prev_id}>
            <ArrowLeft /> Oldingi
          </Button>
          <span className="num min-w-20 text-center text-sm">{img?.position ? `${img.position} / ${img.total}` : `#${imageId}`}</span>
          <Button variant="outline" size="sm" onClick={() => void go(img?.next_id)} disabled={!img?.next_id}>
            Keyingi <ArrowRight />
          </Button>
          <span className="ml-2 text-xs text-muted-foreground">
            {img && (
              <>
                {img.camera_name ?? '—'} · {img.stream === 'main' ? 'asosiy' : 'sub'} oqim · {fmtDateTime(img.captured_at)}
              </>
            )}
          </span>
          <span className="ml-auto flex items-center gap-2 text-xs">
            {saving || isFetching ? <Loader2 className="size-3.5 animate-spin" /> : dirty ? <span className="text-warning">saqlanmagan</span> : <span className="text-success">saqlangan</span>}
            <Button variant="ghost" size="xs" onClick={() => setHelp(true)}>
              <Kbd>?</Kbd> tugmalar
            </Button>
          </span>
        </div>
        <div className="relative min-h-0 flex-1 bg-video-bg">
          {img && (
            <AnnotCanvas
              src={`/api/dataset/images/${img.id}/file`}
              boxes={boxes}
              selected={selected}
              onSelect={setSelected}
              onChange={update}
              currentProduct={current}
              productName={(id) => productById.get(id)?.name ?? `#${id}`}
              onNeedProduct={() => {
                notify.warning('Avval mahsulotni tanlang', "O'ng paneldan yoki 1–9 tugmalari bilan")
                searchRef.current?.focus()
              }}
            />
          )}
          {isEmpty && (
            <div className="pointer-events-none absolute top-3 left-1/2 -translate-x-1/2 rounded-md bg-overlay-label-bg px-3 py-1.5 text-sm text-white">
              <PackageOpen className="mr-1 inline size-4" /> Bo'sh rasm — negativ namuna
            </div>
          )}
        </div>
      </div>

      <aside className="flex w-[320px] shrink-0 flex-col border-l">
        <div className="space-y-3 border-b p-3">
          <div className="relative">
            <Search className="absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input ref={searchRef} value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Mahsulot qidirish ( / )" className="h-8 pl-8" onKeyDown={(e) => {
              if (e.key === 'Enter' && filtered[0]) {
                pickProduct(filtered[0].id)
                if (sel) update(boxes.map((b) => (b.key === sel.key ? { ...b, product_id: filtered[0].id, status: 'confirmed' } : b)))
                setSearch('')
                ;(e.target as HTMLInputElement).blur()
              }
            }} />
          </div>
          <div className="max-h-60 space-y-0.5 overflow-y-auto">
            {(search ? filtered : [...recentList.map((id) => productById.get(id)!), ...(products ?? []).filter((p) => !recentList.includes(p.id))]).slice(0, 30).map((p) => {
              const n = recentList.indexOf(p.id)
              return (
                <button
                  key={p.id}
                  type="button"
                  className={cn('flex w-full items-center gap-2 rounded-md px-2 py-1 text-left text-sm hover:bg-accent', current === p.id && 'bg-primary/15 ring-1 ring-primary')}
                  onClick={() => {
                    pickProduct(p.id)
                    if (sel) update(boxes.map((b) => (b.key === sel.key ? { ...b, product_id: p.id, status: 'confirmed' } : b)))
                  }}
                >
                  <span className="size-2.5 shrink-0 rounded-sm" style={{ background: colorFor(p.id) }} />
                  <span className="flex-1 truncate">{p.name}</span>
                  {!search && n >= 0 && <Kbd>{n + 1}</Kbd>}
                </button>
              )
            })}
            {products && products.length === 0 && (
              <p className="p-2 text-sm text-muted-foreground">
                Katalog bo'sh. <Link to="/products/new" className="text-primary underline">Mahsulot qo'shing</Link>
              </p>
            )}
          </div>
        </div>
        <div className="flex-1 space-y-3 overflow-y-auto p-3">
          {sel ? (
            <div className="space-y-2 rounded-lg border p-2.5">
              <div className="text-xs font-semibold text-muted-foreground uppercase">Tanlangan ramka</div>
              <div className="font-medium">{productById.get(sel.product_id)?.name ?? `#${sel.product_id}`}</div>
              <div className="flex items-center gap-2">
                <Button size="xs" variant={sel.packaging === 'boxed' ? 'default' : 'outline'} onClick={() => update(boxes.map((b) => (b.key === sel.key ? { ...b, packaging: 'boxed', status: 'confirmed' } : b)))}>
                  <Box /> Qutili
                </Button>
                <Button size="xs" variant={sel.packaging === 'unboxed' ? 'default' : 'outline'} onClick={() => update(boxes.map((b) => (b.key === sel.key ? { ...b, packaging: 'unboxed', status: 'confirmed' } : b)))}>
                  Qutisiz
                </Button>
                <HintIcon id="packaging" />
              </div>
              <div className="flex items-center gap-2">
                <Checkbox id="touch" checked={sel.touching} onCheckedChange={(v) => update(boxes.map((b) => (b.key === sel.key ? { ...b, touching: v === true } : b)))} />
                <Label htmlFor="touch" className="text-sm">Boshqa mahsulotga tegib turibdi <Kbd>T</Kbd></Label>
              </div>
              {sel.status === 'auto' && <Badge variant="secondary">Avto taklif · {Math.round((sel.confidence ?? 0) * 100)}%</Badge>}
              <Button size="xs" variant="ghost" className="text-danger" onClick={() => update(boxes.filter((b) => b.key !== sel.key))}>
                <Trash2 /> O'chirish <Kbd>Del</Kbd>
              </Button>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Mahsulotni tanlang va rasmda ramka chizing (sudrang). Har tegib turgan mahsulot — alohida ramka.
            </p>
          )}
          <div>
            <div className="mb-1 text-xs font-semibold text-muted-foreground uppercase">Ramkalar ({boxes.length})</div>
            <div className="space-y-0.5">
              {boxes.map((b, i) => (
                <button key={b.key} type="button" onClick={() => setSelected(b.key)} className={cn('flex w-full items-center gap-2 rounded px-2 py-1 text-left text-sm hover:bg-accent', selected === b.key && 'bg-accent')}>
                  <span className="size-2.5 rounded-sm" style={{ background: colorFor(b.product_id) }} />
                  <span className="flex-1 truncate">
                    {i + 1}. {productById.get(b.product_id)?.name ?? `#${b.product_id}`}
                  </span>
                  {b.packaging === 'boxed' && <Box className="size-3.5 text-muted-foreground" />}
                  {b.status === 'auto' && <span className="text-2xs text-warning">avto</span>}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="space-y-2 border-t p-3">
          <div className="grid grid-cols-2 gap-2">
            <Button variant={isEmpty ? 'default' : 'outline'} size="sm" onClick={() => {
              if (boxes.length) update([])
              setIsEmpty(!isEmpty || boxes.length > 0)
              setDirty(true)
            }}>
              <PackageOpen /> Bo'sh rasm <Kbd>E</Kbd>
            </Button>
            <Button variant="outline" size="sm" disabled={!prevBoxes.current?.length} onClick={() => prevBoxes.current && update([...boxes, ...prevBoxes.current.map((b) => ({ ...b, key: k(), id: null, status: 'confirmed' as const }))])}>
              <Copy /> Nusxalash <Kbd>C</Kbd>
            </Button>
          </div>
          <div className="flex gap-2">
            <Button size="sm" className="flex-1" onClick={() => void confirmAllAndNext()}>
              <Check /> Tasdiqlash va keyingi <Kbd>Enter</Kbd>
            </Button>
            <Button size="icon-sm" variant="ghost" className="text-danger" aria-label="Rasmni o'chirish" onClick={async () => {
              if (!img || !(await confirm({ title: "Rasm o'chirilsinmi?", description: "Rasm va undagi ramkalar o'chiriladi.", destructive: true, confirmText: "O'chirish" }))) return
              await api.delete(`/dataset/images/${img.id}`)
              void qc.invalidateQueries({ queryKey: ['images'] })
              setDirty(false)
              if (img.next_id) navigate(`/dataset/annotate/${img.next_id}${location.search}`, { replace: true })
              else navigate(backHref)
            }}>
              <Trash2 />
            </Button>
          </div>
        </div>
      </aside>
      <ShortcutsDialog open={help} onOpenChange={setHelp} groups={SHORTCUTS} />
    </div>
  )
}

function AnnotCanvas({
  src,
  boxes,
  selected,
  onSelect,
  onChange,
  currentProduct,
  productName,
  onNeedProduct,
}: {
  src: string
  boxes: Box[]
  selected: string | null
  onSelect: (k: string | null) => void
  onChange: (b: Box[]) => void
  currentProduct: number | null
  productName: (id: number) => string
  onNeedProduct: () => void
}) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const stageRef = useRef<Konva.Stage>(null)
  const trRef = useRef<Konva.Transformer>(null)
  const img = useImageEl(src)
  const [size, setSize] = useState({ w: 0, h: 0 })
  const [view, setView] = useState({ scale: 1, x: 0, y: 0 })
  const [draft, setDraft] = useState<{ x1: number; y1: number; x2: number; y2: number } | null>(null)
  const [space, setSpace] = useState(false)

  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const ro = new ResizeObserver(() => setSize({ w: el.clientWidth, h: el.clientHeight }))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  useEffect(() => setView({ scale: 1, x: 0, y: 0 }), [src])
  useEffect(() => {
    const d = (e: KeyboardEvent) => {
      if (e.code === 'Space' && !(e.target instanceof HTMLInputElement)) {
        setSpace(true)
        e.preventDefault()
      }
      if (e.key === '0' && !(e.target instanceof HTMLInputElement)) setView({ scale: 1, x: 0, y: 0 })
    }
    const u = (e: KeyboardEvent) => e.code === 'Space' && setSpace(false)
    window.addEventListener('keydown', d)
    window.addEventListener('keyup', u)
    return () => {
      window.removeEventListener('keydown', d)
      window.removeEventListener('keyup', u)
    }
  }, [])

  const rect = useMemo(() => {
    if (!img || !size.w) return { x: 0, y: 0, w: 1, h: 1 }
    const s = Math.min(size.w / img.width, size.h / img.height)
    return { x: (size.w - img.width * s) / 2, y: (size.h - img.height * s) / 2, w: img.width * s, h: img.height * s }
  }, [img, size])

  useEffect(() => {
    const tr = trRef.current
    const st = stageRef.current
    if (!tr || !st) return
    const node = selected ? st.findOne(`#${selected}`) : null
    tr.nodes(node ? [node] : [])
    tr.getLayer()?.batchDraw()
  }, [selected, boxes])

  const pointer = () => {
    const st = stageRef.current
    const p = st?.getPointerPosition()
    if (!st || !p) return null
    const x = (p.x - st.x()) / st.scaleX()
    const y = (p.y - st.y()) / st.scaleY()
    return { nx: Math.min(1, Math.max(0, (x - rect.x) / rect.w)), ny: Math.min(1, Math.max(0, (y - rect.y) / rect.h)) }
  }

  const onDown = (e: Konva.KonvaEventObject<MouseEvent>) => {
    if (space || e.evt.button !== 0) return
    const isBg = e.target === e.target.getStage() || e.target.name() === 'bg'
    if (!isBg) return
    onSelect(null)
    const p = pointer()
    if (p) setDraft({ x1: p.nx, y1: p.ny, x2: p.nx, y2: p.ny })
  }
  const onMove = () => {
    if (!draft) return
    const p = pointer()
    if (p) setDraft({ ...draft, x2: p.nx, y2: p.ny })
  }
  const onUp = () => {
    if (!draft) return
    const x1 = Math.min(draft.x1, draft.x2)
    const x2 = Math.max(draft.x1, draft.x2)
    const y1 = Math.min(draft.y1, draft.y2)
    const y2 = Math.max(draft.y1, draft.y2)
    setDraft(null)
    if (x2 - x1 < MIN_BOX || y2 - y1 < MIN_BOX) return
    if (!currentProduct) {
      onNeedProduct()
      return
    }
    const nb: Box = { key: k(), product_id: currentProduct, bbox: [x1, y1, x2, y2], packaging: 'unboxed', status: 'confirmed', touching: false }
    onChange([...boxes, nb])
    onSelect(nb.key)
  }

  const onWheel = (e: Konva.KonvaEventObject<WheelEvent>) => {
    e.evt.preventDefault()
    const st = stageRef.current
    const p = st?.getPointerPosition()
    if (!st || !p) return
    const old = view.scale
    const scale = Math.min(8, Math.max(1, old * (e.evt.deltaY < 0 ? 1.15 : 1 / 1.15)))
    const mx = (p.x - view.x) / old
    const my = (p.y - view.y) / old
    setView(scale === 1 ? { scale: 1, x: 0, y: 0 } : { scale, x: p.x - mx * scale, y: p.y - my * scale })
  }

  const sw = 2 / view.scale
  return (
    <div ref={wrapRef} className="absolute inset-0" style={{ cursor: space ? 'grab' : 'crosshair' }}>
      {size.w > 0 && (
        <Stage
          ref={stageRef}
          width={size.w}
          height={size.h}
          scaleX={view.scale}
          scaleY={view.scale}
          x={view.x}
          y={view.y}
          draggable={space}
          onDragEnd={(e) => e.target === stageRef.current && setView((v) => ({ ...v, x: e.target.x(), y: e.target.y() }))}
          onMouseDown={onDown}
          onMouseMove={onMove}
          onMouseUp={onUp}
          onWheel={onWheel}
        >
          <Layer>
            {img && <KImage name="bg" image={img} x={rect.x} y={rect.y} width={rect.w} height={rect.h} />}
            {boxes.map((b, i) => {
              const [x1, y1, x2, y2] = b.bbox
              const c = colorFor(b.product_id)
              const auto = b.status === 'auto'
              return (
                <Group key={b.key}>
                  <Rect
                    id={b.key}
                    x={rect.x + x1 * rect.w}
                    y={rect.y + y1 * rect.h}
                    width={(x2 - x1) * rect.w}
                    height={(y2 - y1) * rect.h}
                    stroke={c}
                    strokeWidth={selected === b.key ? sw * 1.5 : sw}
                    dash={auto ? [6 / view.scale, 4 / view.scale] : undefined}
                    fill={selected === b.key ? `${c}22` : undefined}
                    draggable={!space}
                    onMouseDown={(e) => {
                      e.cancelBubble = true
                      onSelect(b.key)
                    }}
                    onDragEnd={(e) => {
                      const n = e.target
                      const nx1 = (n.x() - rect.x) / rect.w
                      const ny1 = (n.y() - rect.y) / rect.h
                      const w = x2 - x1
                      const h = y2 - y1
                      const cx = Math.min(1 - w, Math.max(0, nx1))
                      const cy = Math.min(1 - h, Math.max(0, ny1))
                      onChange(boxes.map((bb) => (bb.key === b.key ? { ...bb, bbox: [cx, cy, cx + w, cy + h], status: 'confirmed' } : bb)))
                    }}
                    onTransformEnd={(e) => {
                      const n = e.target
                      const w = (n.width() * n.scaleX()) / rect.w
                      const h = (n.height() * n.scaleY()) / rect.h
                      n.scaleX(1)
                      n.scaleY(1)
                      const nx1 = Math.max(0, (n.x() - rect.x) / rect.w)
                      const ny1 = Math.max(0, (n.y() - rect.y) / rect.h)
                      onChange(boxes.map((bb) => (bb.key === b.key ? { ...bb, bbox: [nx1, ny1, Math.min(1, nx1 + w), Math.min(1, ny1 + h)], status: 'confirmed' } : bb)))
                    }}
                  />
                  <Text
                    x={rect.x + x1 * rect.w + 3 / view.scale}
                    y={rect.y + y1 * rect.h - 16 / view.scale}
                    text={`${i + 1}. ${productName(b.product_id)}${b.packaging === 'boxed' ? ' [quti]' : ''}${auto ? ` ${Math.round((b.confidence ?? 0) * 100)}%` : ''}`}
                    fontSize={13 / view.scale}
                    fontStyle="bold"
                    fill={c}
                    listening={false}
                  />
                </Group>
              )
            })}
            {draft && (
              <Rect
                x={rect.x + Math.min(draft.x1, draft.x2) * rect.w}
                y={rect.y + Math.min(draft.y1, draft.y2) * rect.h}
                width={Math.abs(draft.x2 - draft.x1) * rect.w}
                height={Math.abs(draft.y2 - draft.y1) * rect.h}
                stroke={currentProduct ? colorFor(currentProduct) : '#fff'}
                strokeWidth={sw}
                dash={[4 / view.scale, 3 / view.scale]}
                listening={false}
              />
            )}
            <Transformer ref={trRef} rotateEnabled={false} keepRatio={false} ignoreStroke anchorSize={8} borderStroke="#fff" anchorStroke="#000" />
          </Layer>
        </Stage>
      )}
    </div>
  )
}
