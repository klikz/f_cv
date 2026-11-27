import { CircleCheck, CircleDashed, TriangleAlert } from 'lucide-react'
import { READINESS_LABEL, type Readiness } from '@/hooks/use-catalog'
import { cn } from '@/lib/utils'

export function ReadinessBadge({ level, className }: { level: Readiness['level']; className?: string }) {
  const Icon = level === 'ready' ? CircleCheck : level === 'minimal' ? TriangleAlert : CircleDashed
  const cls = level === 'ready' ? 'bg-success-muted text-success' : level === 'minimal' ? 'bg-warning-muted text-warning' : 'bg-neutral-muted text-neutral'
  return (
    <span className={cn('inline-flex h-5 items-center gap-1 rounded-full px-1.5 text-2xs font-medium', cls, className)}>
      <Icon className="size-3" /> {READINESS_LABEL[level]}
    </span>
  )
}
