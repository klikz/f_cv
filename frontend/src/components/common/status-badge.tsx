import { CircleCheck, CircleDashed, CircleHelp, CircleSlash, CircleX, Loader, TriangleAlert, type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'

/**
 * Holat ifodasi: doim rang + ikon + matn (faqat rangga tayanilmaydi, PLAN.md 4.1.1).
 * Ranglar: yashil — ishlayapti/online, sariq — ogohlantirish/noaniq, qizil — to'xtagan/offline,
 * kulrang — o'chirilgan, ko'k — faol/jarayonda.
 */
export type StatusKind =
  | 'ok'
  | 'online'
  | 'running'
  | 'warn'
  | 'uncertain'
  | 'error'
  | 'offline'
  | 'stopped'
  | 'disabled'
  | 'unknown'
  | 'connecting'
  | 'training'

type Tone = 'success' | 'warning' | 'danger' | 'neutral' | 'info'

const MAP: Record<StatusKind, { tone: Tone; icon: LucideIcon; label: string; spin?: boolean }> = {
  ok: { tone: 'success', icon: CircleCheck, label: t.status.ok },
  online: { tone: 'success', icon: CircleCheck, label: t.status.online },
  running: { tone: 'success', icon: CircleCheck, label: t.status.running },
  warn: { tone: 'warning', icon: TriangleAlert, label: t.status.warn },
  uncertain: { tone: 'warning', icon: CircleHelp, label: t.status.uncertain },
  error: { tone: 'danger', icon: CircleX, label: t.status.error },
  offline: { tone: 'danger', icon: CircleX, label: t.status.offline },
  stopped: { tone: 'danger', icon: CircleSlash, label: t.status.stopped },
  disabled: { tone: 'neutral', icon: CircleDashed, label: t.status.disabled },
  unknown: { tone: 'neutral', icon: CircleHelp, label: t.status.unknown },
  connecting: { tone: 'info', icon: Loader, label: t.status.connecting, spin: true },
  training: { tone: 'info', icon: Loader, label: t.status.training, spin: true },
}

export const toneText: Record<Tone, string> = {
  success: 'text-success',
  warning: 'text-warning',
  danger: 'text-danger',
  neutral: 'text-neutral',
  info: 'text-info',
}

const toneBadge: Record<Tone, string> = {
  success: 'bg-success-muted text-success',
  warning: 'bg-warning-muted text-warning',
  danger: 'bg-danger-muted text-danger',
  neutral: 'bg-neutral-muted text-neutral',
  info: 'bg-info-muted text-info',
}

const toneDot: Record<Tone, string> = {
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-danger',
  neutral: 'bg-neutral',
  info: 'bg-info',
}

export function statusTone(kind: StatusKind): Tone {
  return MAP[kind].tone
}

type Props = {
  status: StatusKind
  label?: string
  /** 'badge' — fonli belgi; 'inline' — faqat ikon+matn; 'dot' — nuqta+matn */
  variant?: 'badge' | 'inline' | 'dot'
  size?: 'sm' | 'md'
  className?: string
}

export function StatusBadge({ status, label, variant = 'badge', size = 'md', className }: Props) {
  const m = MAP[status]
  const Icon = m.icon
  const text = label ?? m.label
  const iconCls = cn(size === 'sm' ? 'size-3' : 'size-3.5', 'shrink-0', m.spin && 'animate-spin')

  if (variant === 'dot') {
    return (
      <span className={cn('inline-flex items-center gap-1.5', size === 'sm' ? 'text-xs' : 'text-sm', className)}>
        <span className={cn('size-2 shrink-0 rounded-full', toneDot[m.tone])} aria-hidden />
        <span>{text}</span>
      </span>
    )
  }
  if (variant === 'inline') {
    return (
      <span
        className={cn('inline-flex items-center gap-1', toneText[m.tone], size === 'sm' ? 'text-xs' : 'text-sm', className)}
      >
        <Icon className={iconCls} aria-hidden />
        <span>{text}</span>
      </span>
    )
  }
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full font-medium whitespace-nowrap',
        size === 'sm' ? 'h-5 px-1.5 text-2xs' : 'h-6 px-2 text-xs',
        toneBadge[m.tone],
        className,
      )}
    >
      <Icon className={iconCls} aria-hidden />
      {text}
    </span>
  )
}
