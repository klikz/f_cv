import { Boxes, Plus, Search } from 'lucide-react'
import { Link, useNavigate } from 'react-router'
import { ReadinessBadge } from '@/components/common/readiness-badge'
import { EmptyState, ErrorState, TableSkeleton } from '@/components/common/states'
import { PageBody, PageHeader, useRouteTitle } from '@/components/layout/page'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useCategories, useProducts, useReadiness } from '@/hooks/use-catalog'
import { param, useUrlState } from '@/hooks/use-url-state'

export function ProductsPage() {
  const title = useRouteTitle()
  const navigate = useNavigate()
  const [q, setQ] = useUrlState('q', param.string, '')
  const [cat, setCat] = useUrlState('category', param.string, '')
  const { data, isLoading, error, refetch } = useProducts(q || undefined, cat || undefined)
  const { data: cats } = useCategories()
  const { data: ready } = useReadiness()
  const readyBy = new Map((ready ?? []).map((r) => [r.product_id, r]))

  return (
    <PageBody>
      <PageHeader
        title={title}
        description="Har mahsulot alohida model bilan aniqlanadi. Kod va nom kiriting, so'ng datasetda rasmlarini belgilang."
        actions={
          <Button asChild>
            <Link to="/products/new">
              <Plus /> Mahsulot qo'shish
            </Link>
          </Button>
        }
      />
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="relative w-72">
          <Search className="absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Nom yoki kod bo'yicha qidirish" className="h-8 pl-8" />
        </div>
        <Select value={cat || 'all'} onValueChange={(v) => setCat(v === 'all' ? '' : v)}>
          <SelectTrigger className="h-8 w-52">
            <SelectValue placeholder="Kategoriya" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Barcha kategoriyalar</SelectItem>
            {cats?.map((c) => (
              <SelectItem key={c} value={c}>
                {c}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {data && <span className="text-sm text-muted-foreground">{data.length} ta</span>}
      </div>
      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <TableSkeleton />
      ) : !data?.length ? (
        <div className="rounded-xl border">
          <EmptyState
            icon={Boxes}
            title={q || cat ? 'Hech narsa topilmadi' : "Mahsulot yo'q"}
            description={q || cat ? "Qidiruv so'zini o'zgartiring." : "Katalog bo'sh — birinchi mahsulotni qo'shing."}
            action={
              !q && !cat && (
                <Button asChild>
                  <Link to="/products/new">
                    <Plus /> Mahsulot qo'shish
                  </Link>
                </Button>
              )
            }
          />
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-28">Kod</TableHead>
                <TableHead>Nomi</TableHead>
                <TableHead>Kategoriya</TableHead>
                <TableHead className="text-right">Belgilangan</TableHead>
                <TableHead>Tayyorlik</TableHead>
                <TableHead>Faol model</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((p) => {
                const r = readyBy.get(p.id)
                return (
                  <TableRow key={p.id} className="cursor-pointer" onClick={() => navigate(`/products/${p.id}`)}>
                    <TableCell className="font-mono text-xs">{p.code}</TableCell>
                    <TableCell>
                      <Link to={`/products/${p.id}`} className="font-medium hover:underline" onClick={(e) => e.stopPropagation()}>
                        {p.name}
                      </Link>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">{p.category ?? '—'}</TableCell>
                    <TableCell className="num text-right">{r?.confirmed ?? 0}</TableCell>
                    <TableCell>{r && <ReadinessBadge level={r.level} />}</TableCell>
                    <TableCell>{p.active_version ? <Badge variant="secondary">v{p.active_version}</Badge> : <span className="text-xs text-muted-foreground">yo'q</span>}</TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </PageBody>
  )
}
