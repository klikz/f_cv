import { BrainCircuit } from 'lucide-react'
import { Link, useNavigate } from 'react-router'
import { EmptyState, ErrorState, TableSkeleton } from '@/components/common/states'
import { StatusBadge } from '@/components/common/status-badge'
import { HintIcon } from '@/components/common/term'
import { PageBody, PageHeader, useRouteTitle } from '@/components/layout/page'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useModels } from '@/hooks/use-catalog'
import { useHealth } from '@/hooks/use-health'
import { fmtDateTime } from '@/lib/format'
import { ConfusedPairs } from './confused-pairs'

export function ModelsPage() {
  const title = useRouteTitle()
  const navigate = useNavigate()
  const { data, isLoading, error, refetch } = useModels()
  const { data: health } = useHealth()
  const gpu = health?.gpu.data.gpus?.[0]
  const active = data?.filter((m) => m.active).length ?? 0

  return (
    <PageBody>
      <PageHeader
        title={title}
        description={
          <span className="inline-flex items-center gap-1">
            Har mahsulot — alohida model. Yangi versiya avtomatik faollashmaydi: metrikalarni solishtirib "Faollashtirish" bosiladi. <HintIcon id="modelVersion" />
          </span>
        }
      />
      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-lg border bg-card p-3">
          <div className="text-xs text-muted-foreground">Faol modellar</div>
          <div className="num text-2xl font-semibold">{active}</div>
        </div>
        <div className="rounded-lg border bg-card p-3">
          <div className="text-xs text-muted-foreground">GPU xotira (VRAM)</div>
          <div className="num text-2xl font-semibold">{gpu ? `${(gpu.mem_used_mb / 1024).toFixed(1)} / ${(gpu.mem_total_mb / 1024).toFixed(0)} GB` : '—'}</div>
        </div>
      </div>
      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <TableSkeleton />
      ) : !data?.length ? (
        <div className="rounded-xl border">
          <EmptyState icon={BrainCircuit} title="Mahsulot yo'q" description="Avval katalogga mahsulot qo'shing." />
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Mahsulot</TableHead>
                <TableHead>Faol versiya</TableHead>
                <TableHead className="text-right">mAP50</TableHead>
                <TableHead>Oxirgi versiya</TableHead>
                <TableHead>Holat</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((m) => (
                <TableRow key={m.product_id} className="cursor-pointer" onClick={() => navigate(`/models/${m.product_id}`)}>
                  <TableCell>
                    <Link to={`/models/${m.product_id}`} className="font-medium hover:underline" onClick={(e) => e.stopPropagation()}>
                      {m.name}
                    </Link>
                    <div className="font-mono text-xs text-muted-foreground">{m.code}</div>
                  </TableCell>
                  <TableCell>{m.active ? `v${m.active.version}` : <span className="text-muted-foreground">—</span>}</TableCell>
                  <TableCell className="num text-right">{m.active?.metrics.map50 != null ? Number(m.active.metrics.map50).toFixed(3) : '—'}</TableCell>
                  <TableCell className="text-sm">{m.latest ? `v${m.latest.version} · ${fmtDateTime(m.latest.created_at)}` : '—'}</TableCell>
                  <TableCell>
                    {m.active ? (
                      m.active.status === 'stale' ? <StatusBadge status="warn" label="Engine qayta qurilmoqda" size="sm" /> : <StatusBadge status="ok" label="Tayyor" size="sm" />
                    ) : m.latest ? (
                      <StatusBadge status="unknown" label="Faollashtirilmagan" size="sm" />
                    ) : (
                      <StatusBadge status="disabled" label="Train qilinmagan" size="sm" />
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      <ConfusedPairs />
    </PageBody>
  )
}
