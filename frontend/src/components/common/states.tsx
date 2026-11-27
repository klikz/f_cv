import { CircleAlert, Inbox, RotateCw, type LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { errorMessage } from '@/lib/api'
import { t } from '@/lib/i18n'
import { cn } from '@/lib/utils'

/** Bo'sh holat — doim yo'l ko'rsatadi ("Kamera yo'q → Kamera qo'shish"). */
export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className,
  compact,
}: {
  icon?: LucideIcon
  title: string
  description?: ReactNode
  action?: ReactNode
  className?: string
  compact?: boolean
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center text-center',
        compact ? 'gap-2 p-6' : 'gap-3 p-10',
        className,
      )}
    >
      <div className={cn('flex items-center justify-center rounded-full bg-muted', compact ? 'size-10' : 'size-12')}>
        <Icon className={cn('text-muted-foreground', compact ? 'size-5' : 'size-6')} aria-hidden />
      </div>
      <div className="space-y-1">
        <h3 className="text-lg font-semibold">{title}</h3>
        {description && <p className="max-w-md text-sm text-muted-foreground">{description}</p>}
      </div>
      {action && <div className="mt-1">{action}</div>}
    </div>
  )
}

/** Xato holati — nima bo'lgani va nima qilish kerakligi + "Qayta urinish". */
export function ErrorState({
  error,
  title = t.errors.generic,
  onRetry,
  className,
  compact,
}: {
  error?: unknown
  title?: string
  onRetry?: () => void
  className?: string
  compact?: boolean
}) {
  return (
    <div
      role="alert"
      className={cn(
        'flex flex-col items-center justify-center text-center',
        compact ? 'gap-2 p-6' : 'gap-3 p-10',
        className,
      )}
    >
      <div className={cn('flex items-center justify-center rounded-full bg-danger-muted', compact ? 'size-10' : 'size-12')}>
        <CircleAlert className={cn('text-danger', compact ? 'size-5' : 'size-6')} aria-hidden />
      </div>
      <div className="space-y-1">
        <h3 className="text-lg font-semibold">{title}</h3>
        {error !== undefined && <p className="max-w-md text-sm text-muted-foreground">{errorMessage(error)}</p>}
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RotateCw /> {t.common.retry}
        </Button>
      )}
    </div>
  )
}

/** Yuklanish skeletlari. */
export function TableSkeleton({ rows = 6, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="space-y-2" aria-busy aria-label={t.common.loading}>
      <div className="flex gap-3">
        {Array.from({ length: cols }, (_, i) => (
          <Skeleton key={i} className="h-4 flex-1" />
        ))}
      </div>
      {Array.from({ length: rows }, (_, r) => (
        <div key={r} className="flex gap-3">
          {Array.from({ length: cols }, (_, i) => (
            <Skeleton key={i} className="h-8 flex-1" />
          ))}
        </div>
      ))}
    </div>
  )
}

export function CardGridSkeleton({ count = 6, className }: { count?: number; className?: string }) {
  return (
    <div className={cn('grid grid-cols-2 gap-3 lg:grid-cols-3', className)} aria-busy aria-label={t.common.loading}>
      {Array.from({ length: count }, (_, i) => (
        <Skeleton key={i} className="aspect-video w-full" />
      ))}
    </div>
  )
}
