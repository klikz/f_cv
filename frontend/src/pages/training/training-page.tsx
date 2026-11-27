import { Activity, Plus, X } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { useQueryClient } from '@tanstack/react-query'
import { EmptyState, ErrorState, TableSkeleton } from '@/components/common/states'
import { PageBody, PageHeader, useRouteTitle } from '@/components/layout/page'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/common/progress'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { KIND_LABEL, STAGE_LABEL, useJobs } from '@/hooks/use-catalog'
import { param, useUrlState } from '@/hooks/use-url-state'
import { api } from '@/lib/api'
import { fmtDateTime, fmtDuration } from '@/lib/format'
import { notify } from '@/lib/notify'
import { JobStatus } from './job-status'
import { NewJobDialog } from './new-job-dialog'

export function TrainingPage() {
  const title = useRouteTitle()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { data, isLoading, error, refetch } = useJobs()
  const [open, setOpen] = useUrlState('new', param.bool, false, { push: true })
  const [pre] = useUrlState('product', param.int, 0)
  const [, force] = useState(0)

  const cancel = async (id: number) => {
    try {
      await api.post(`/training/jobs/${id}/cancel`)
      void qc.invalidateQueries({ queryKey: ['jobs'] })
      force((n) => n + 1)
    } catch (e) {
      notify.error("Bekor qilib bo'lmadi", e)
    }
  }
  const active = data?.filter((j) => ['queued', 'running', 'cancelling'].includes(j.status)) ?? []
  const history = data?.filter((j) => !['queued', 'running', 'cancelling'].includes(j.status)) ?? []

  const dur = (a: string | null, b: string | null) => (a ? fmtDuration(((b ? new Date(b) : new Date()).getTime() - new Date(a).getTime()) / 1000) : '—')

  return (
    <PageBody>
      <PageHeader
        title={title}
        description="Bir vaqtda bitta train ishlaydi. Train paytida mahsulot sanash to'xtatiladi (video va uskuna vazifasi davom etadi)."
        actions={
          <Button onClick={() => setOpen(true)}>
            <Plus /> Yangi train
          </Button>
        }
      />
      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <TableSkeleton />
      ) : !data?.length ? (
        <div className="rounded-xl border">
          <EmptyState icon={Activity} title="Train hali bo'lmagan" description="Mahsulot rasmlarini belgilang, so'ng train qiling." action={<Button onClick={() => setOpen(true)}><Plus /> Yangi train</Button>} />
        </div>
      ) : (
        <div className="space-y-6">
          {active.length > 0 && (
            <section>
              <h2 className="mb-2 text-sm font-semibold">Navbat</h2>
              <div className="overflow-hidden rounded-xl border bg-card">
                <Table>
                  <TableBody>
                    {active.map((j) => (
                      <TableRow key={j.id} className="cursor-pointer" onClick={() => navigate(`/training/${j.id}`)}>
                        <TableCell className="w-16 text-muted-foreground">#{j.id}</TableCell>
                        <TableCell>
                          <Link to={`/training/${j.id}`} className="font-medium hover:underline" onClick={(e) => e.stopPropagation()}>
                            {j.product_name}
                          </Link>
                          <div className="text-xs text-muted-foreground">{KIND_LABEL[j.kind]}</div>
                        </TableCell>
                        <TableCell className="w-48">
                          <JobStatus status={j.status} size="sm" />
                          <div className="mt-1 text-xs text-muted-foreground">{STAGE_LABEL[j.stage]}</div>
                        </TableCell>
                        <TableCell className="w-64">
                          {j.status === 'running' && j.epochs > 0 && (
                            <div className="space-y-1">
                              <Progress value={(j.epoch / j.epochs) * 100} />
                              <div className="num text-xs text-muted-foreground">
                                {j.epoch} / {j.epochs} · qoldi {fmtDuration(j.eta_sec)}
                              </div>
                            </div>
                          )}
                          {j.status === 'queued' && j.scheduled_at && <span className="text-xs">{fmtDateTime(j.scheduled_at)} da</span>}
                        </TableCell>
                        <TableCell className="w-12">
                          <Button size="icon-sm" variant="ghost" onClick={(e) => { e.stopPropagation(); void cancel(j.id) }} aria-label="Bekor qilish">
                            <X />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </section>
          )}
          <section>
            <h2 className="mb-2 text-sm font-semibold">Tarix</h2>
            <div className="overflow-hidden rounded-xl border bg-card">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-16">#</TableHead>
                    <TableHead>Mahsulot</TableHead>
                    <TableHead>Turi</TableHead>
                    <TableHead>Holat</TableHead>
                    <TableHead>Boshlangan</TableHead>
                    <TableHead>Davomiylik</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {history.map((j) => (
                    <TableRow key={j.id} className="cursor-pointer" onClick={() => navigate(`/training/${j.id}`)}>
                      <TableCell className="text-muted-foreground">#{j.id}</TableCell>
                      <TableCell>
                        <Link to={`/training/${j.id}`} className="font-medium hover:underline" onClick={(e) => e.stopPropagation()}>
                          {j.product_name}
                        </Link>
                      </TableCell>
                      <TableCell className="text-sm">{KIND_LABEL[j.kind]}</TableCell>
                      <TableCell>
                        <JobStatus status={j.status} size="sm" />
                      </TableCell>
                      <TableCell className="text-sm">{fmtDateTime(j.started_at)}</TableCell>
                      <TableCell className="num text-sm">{dur(j.started_at, j.finished_at)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </section>
        </div>
      )}
      <NewJobDialog open={open} onOpenChange={setOpen} preselect={pre || undefined} />
    </PageBody>
  )
}
