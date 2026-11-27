import type { ReactNode } from 'react'
import { useMatches, useParams } from 'react-router'
import { isRouteHandle } from '@/app/crumbs'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { cn } from '@/lib/utils'

/** Joriy marshrut handle'i (non bo'laklari, bosqich). */
export function useRouteHandle() {
  const matches = useMatches()
  for (let i = matches.length - 1; i >= 0; i--) {
    const h = matches[i].handle
    if (isRouteHandle(h)) return h
  }
  return null
}

/** Marshrut nomlaridan brauzer yorlig'i nomi: oxirgi ikki bo'lak, teskari tartibda emas. */
export function useRouteTitle(override?: string) {
  const handle = useRouteHandle()
  const params = useParams()
  const crumbs = handle?.crumbs(params) ?? []
  const last = crumbs.slice(-2).map((c) => c.label)
  const title = override ?? (crumbs.length > 2 ? last.join(' — ') : crumbs.at(-1)?.label)
  useDocumentTitle(title)
  return crumbs.at(-1)?.label ?? ''
}

/** Sahifa sarlavhasi: nom, qisqa izoh, bitta asosiy amal + ikkinchi darajali amallar. */
export function PageHeader({
  title,
  description,
  actions,
  className,
}: {
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
  className?: string
}) {
  return (
    <div className={cn('mb-4 flex flex-wrap items-start justify-between gap-3', className)}>
      <div className="min-w-0 space-y-0.5">
        <h1 className="truncate text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  )
}

export function PageBody({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn('mx-auto w-full max-w-[1600px] p-4 lg:p-6', className)}>{children}</div>
}
