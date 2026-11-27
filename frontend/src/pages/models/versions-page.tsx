import { Activity, Power, Trash2, Undo2 } from 'lucide-react'
import { Link, useParams } from 'react-router'
import { useQueryClient } from '@tanstack/react-query'
import { useConfirm } from '@/components/common/confirm-dialog'
import { EmptyState, ErrorState, TableSkeleton } from '@/components/common/states'
import { StatusBadge } from '@/components/common/status-badge'
import { PageBody, PageHeader } from '@/components/layout/page'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useProduct, useVersions, type ModelVersion } from '@/hooks/use-catalog'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { api } from '@/lib/api'
import { fmtDateTime, fmtDuration } from '@/lib/format'
import { notify } from '@/lib/notify'

const n3 = (v: unknown) => (v == null || v === '' ? '—' : Number(v).toFixed(3))

export function VersionsPage() {
  const pid = Number(useParams().productId)
  const { data: product } = useProduct(pid)
  const { data, isLoading, error, refetch } = useVersions(pid)
  const qc = useQueryClient()
  const confirm = useConfirm()
  useDocumentTitle(product ? `${product.name} — Model versiyalari` : 'Model versiyalari')
  const active = data?.find((v) => v.is_active)

  const refresh = () => {
    void qc.invalidateQueries({ queryKey: ['versions', pid] })
    void qc.invalidateQueries({ queryKey: ['models'] })
  }
  const activate = async (v: ModelVersion) => {
    const better = active && v.metrics.map50 != null && active.metrics.map50 != null ? Number(v.metrics.map50) - Number(active.metrics.map50) : null
    const ok = await confirm({
      title: `v${v.version} faollashtirilsinmi?`,
      description: (
        <>
          Shu mahsulotni sanayotgan kameralar yangi engine'ga o'tadi.
          {better != null && (
            <span className={`mt-2 block ${better < 0 ? 'text-warning' : 'text-success'}`}>
              mAP50: {n3(active!.metrics.map50)} → {n3(v.metrics.map50)} ({better >= 0 ? '+' : ''}
              {better.toFixed(3)})
            </span>
          )}
        </>
      ),
      confirmText: 'Faollashtirish',
    })
    if (!ok) return
    try {
      await api.post(`/models/versions/${v.id}/activate`)
      notify.success(`v${v.version} faollashtirildi`)
      refresh()
    } catch (e) {
      notify.error("Faollashtirib bo'lmadi", e)
    }
  }
  const rollback = async () => {
    try {
      const v = await api.post<ModelVersion>(`/models/${pid}/rollback`)
      notify.success(`v${v.version} ga qaytarildi`)
      refresh()
    } catch (e) {
      notify.error("Qaytarib bo'lmadi", e)
    }
  }
  const remove = async (v: ModelVersion) => {
    if (!(await confirm({ title: `v${v.version} o'chirilsinmi?`, destructive: true, confirmText: "O'chirish" }))) return
    try {
      await api.delete(`/models/versions/${v.id}`)
      refresh()
    } catch (e) {
      notify.error("O'chirib bo'lmadi", e)
    }
  }

  return (
    <PageBody>
      <PageHeader
        title={product ? `${product.name} — versiyalar` : 'Versiyalar'}
        actions={
          <>
            {active && (
              <Button variant="outline" onClick={rollback}>
                <Undo2 /> Oldingi versiyaga qaytish
              </Button>
            )}
            <Button asChild>
              <Link to={`/training?new=1&product=${pid}`}>
                <Activity /> Train qilish
              </Link>
            </Button>
          </>
        }
      />
      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <TableSkeleton />
      ) : !data?.length ? (
        <div className="rounded-xl border">
          <EmptyState title="Versiya yo'q" description="Mahsulot hali train qilinmagan." />
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Versiya</TableHead>
                <TableHead className="text-right">mAP50</TableHead>
                <TableHead className="text-right">mAP50-95</TableHead>
                <TableHead className="text-right">P / R</TableHead>
                <TableHead className="text-right">Engine mAP50</TableHead>
                <TableHead>Train / eksport</TableHead>
                <TableHead>Holat</TableHead>
                <TableHead>Sana</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((v) => (
                <TableRow key={v.id}>
                  <TableCell className="font-medium">
                    v{v.version} <span className="text-xs text-muted-foreground">YOLO26{v.model_size}</span>
                    {v.is_draft && <Badge variant="secondary" className="ml-1">qoralama</Badge>}
                    {v.is_active && <Badge className="ml-1">faol</Badge>}
                  </TableCell>
                  <TableCell className="num text-right">{n3(v.metrics.map50)}</TableCell>
                  <TableCell className="num text-right">{n3(v.metrics.map5095)}</TableCell>
                  <TableCell className="num text-right">
                    {n3(v.metrics.precision)} / {n3(v.metrics.recall)}
                  </TableCell>
                  <TableCell className="num text-right" title={String(v.metrics.export_warning ?? '')}>
                    {n3(v.metrics.engine_map50)} {v.metrics.export_warning ? '⚠' : ''}
                  </TableCell>
                  <TableCell className="num text-xs">
                    {fmtDuration(Number(v.metrics.train_seconds) || null)} / {fmtDuration(Number(v.metrics.export_seconds) || null)}
                  </TableCell>
                  <TableCell>
                    <StatusBadge
                      status={v.status === 'ready' ? 'ok' : v.status === 'building' ? 'connecting' : v.status === 'stale' ? 'warn' : 'error'}
                      label={{ ready: 'Tayyor', building: 'Qurilmoqda', failed: 'Xato', stale: 'Qayta qurish kerak' }[v.status]}
                      size="sm"
                    />
                  </TableCell>
                  <TableCell className="text-xs">{fmtDateTime(v.created_at)}</TableCell>
                  <TableCell className="text-right whitespace-nowrap">
                    {!v.is_active && !v.is_draft && v.engine_ready && (
                      <Button size="xs" onClick={() => void activate(v)}>
                        <Power /> Faollashtirish
                      </Button>
                    )}
                    {!v.is_active && (
                      <Button size="icon-xs" variant="ghost" onClick={() => void remove(v)} aria-label="O'chirish">
                        <Trash2 />
                      </Button>
                    )}
                    {v.job_id && (
                      <Button size="xs" variant="ghost" asChild>
                        <Link to={`/training/${v.job_id}`}>train #{v.job_id}</Link>
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </PageBody>
  )
}
