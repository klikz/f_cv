import { Camera as CameraIcon, GripVertical, MoreHorizontal, Pencil, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { useConfirm } from '@/components/common/confirm-dialog'
import { EmptyState, ErrorState, TableSkeleton } from '@/components/common/states'
import { StatusBadge, type StatusKind } from '@/components/common/status-badge'
import { PageBody, PageHeader, useRouteTitle } from '@/components/layout/page'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { streamOf, useCameras, useDeleteCamera, useReorderCameras } from '@/hooks/use-cameras'
import { errorMessage } from '@/lib/api'
import { resolution } from '@/lib/format'
import { notify } from '@/lib/notify'
import type { Camera, StreamInfo } from '@/lib/types'
import { cn } from '@/lib/utils'

function streamStatus(s: StreamInfo | undefined, enabled: boolean): StatusKind {
  if (!enabled) return 'disabled'
  if (!s) return 'unknown'
  if (s.status === 'online') return 'online'
  if (s.status === 'connecting') return 'connecting'
  if (s.status === 'error') return 'error'
  return 'offline'
}

function StreamCell({ cam, kind }: { cam: Camera; kind: 'main' | 'sub' }) {
  const s = streamOf(cam, kind)
  if (kind === 'sub' && !cam.sub_rtsp_url) return <span className="text-xs text-muted-foreground">yo'q</span>
  const st = streamStatus(s, cam.enabled)
  return (
    <div className="flex flex-col gap-0.5" title={s?.last_error ?? undefined}>
      <StatusBadge status={st} size="sm" variant="inline" label={st === 'offline' && kind === 'main' ? 'Yopiq (kerak bo\'lganda ochiladi)' : undefined} />
      <span className="num text-xs text-muted-foreground">
        {s?.codec?.toUpperCase() ?? '—'} · {resolution(s?.width, s?.height)} · {s?.fps ? `${s.fps} fps` : '—'}
      </span>
    </div>
  )
}

export function CamerasListPage() {
  const title = useRouteTitle()
  const navigate = useNavigate()
  const { data, isLoading, error, refetch } = useCameras()
  const del = useDeleteCamera()
  const reorder = useReorderCameras()
  const confirm = useConfirm()
  const [dragId, setDragId] = useState<number | null>(null)
  const [overId, setOverId] = useState<number | null>(null)

  const remove = async (cam: Camera) => {
    const ok = await confirm({
      title: `"${cam.name}" o'chirilsinmi?`,
      description: "Kamera, uning vazifalari sozlamalari va sanoq tarixi bog'lanishi o'chiriladi. Bu amalni qaytarib bo'lmaydi.",
      confirmText: "O'chirish",
      destructive: true,
    })
    if (!ok) return
    try {
      await del.mutateAsync(cam.id)
      notify.success(`"${cam.name}" o'chirildi`)
    } catch (e) {
      notify.error("O'chirib bo'lmadi", e)
    }
  }

  const drop = (targetId: number) => {
    if (!data || dragId == null || dragId === targetId) return
    const ids = data.map((c) => c.id).filter((id) => id !== dragId)
    ids.splice(ids.indexOf(targetId), 0, dragId)
    reorder.mutate(ids, { onError: (e) => notify.error('Tartibni saqlab bo\'lmadi', e) })
  }

  return (
    <PageBody>
      <PageHeader
        title={title}
        description="Kameralar va ularning oqimlari. Tartibni o'zgartirish uchun qatorni sudrang."
        actions={
          <Button asChild>
            <Link to="/settings/cameras/new">
              <Plus /> Kamera qo'shish
            </Link>
          </Button>
        }
      />
      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <TableSkeleton rows={4} cols={5} />
      ) : !data?.length ? (
        <div className="rounded-xl border">
          <EmptyState
            icon={CameraIcon}
            title="Kamera yo'q"
            description="Kamerani RTSP manzillari bilan yoki ONVIF orqali tarmoqdan topib qo'shing."
            action={
              <Button asChild>
                <Link to="/settings/cameras/new">
                  <Plus /> Kamera qo'shish
                </Link>
              </Button>
            }
          />
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-8" />
                <TableHead>Nomi</TableHead>
                <TableHead>Asosiy oqim</TableHead>
                <TableHead>Sub oqim</TableHead>
                <TableHead>Ulanish</TableHead>
                <TableHead className="w-12" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((cam) => (
                <TableRow
                  key={cam.id}
                  draggable
                  onDragStart={() => setDragId(cam.id)}
                  onDragOver={(e) => {
                    e.preventDefault()
                    setOverId(cam.id)
                  }}
                  onDragLeave={() => setOverId(null)}
                  onDrop={() => {
                    drop(cam.id)
                    setOverId(null)
                    setDragId(null)
                  }}
                  onDragEnd={() => {
                    setDragId(null)
                    setOverId(null)
                  }}
                  className={cn(dragId === cam.id && 'opacity-50', overId === cam.id && dragId !== cam.id && 'border-t-2 border-t-primary')}
                >
                  <TableCell className="cursor-grab text-muted-foreground">
                    <GripVertical className="size-4" aria-label="Sudrash" />
                  </TableCell>
                  <TableCell>
                    <Link to={`/cameras/${cam.id}`} className="font-medium hover:underline">
                      {cam.name}
                    </Link>
                    <div className="max-w-80 truncate font-mono text-xs text-muted-foreground">{cam.main_rtsp_url}</div>
                  </TableCell>
                  <TableCell>
                    <StreamCell cam={cam} kind="main" />
                  </TableCell>
                  <TableCell>
                    <StreamCell cam={cam} kind="sub" />
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="uppercase">
                      {cam.connection_type}
                    </Badge>
                    {cam.onvif?.model && <div className="mt-0.5 text-xs text-muted-foreground">{cam.onvif.manufacturer} {cam.onvif.model}</div>}
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon-sm" aria-label="Amallar">
                          <MoreHorizontal />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onSelect={() => navigate(`/settings/cameras/${cam.id}/edit`)}>
                          <Pencil /> Tahrirlash
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem variant="destructive" onSelect={() => void remove(cam)}>
                          <Trash2 /> O'chirish
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      {del.error && <p className="mt-2 text-sm text-danger">{errorMessage(del.error)}</p>}
    </PageBody>
  )
}
