import { StatusBadge, type StatusKind } from '@/components/common/status-badge'
import { STATUS_LABEL, type Job } from '@/hooks/use-catalog'

const MAP: Record<Job['status'], StatusKind> = { queued: 'unknown', running: 'training', done: 'ok', failed: 'error', cancelled: 'disabled', cancelling: 'warn' }

export function JobStatus({ status, size = 'md' }: { status: Job['status']; size?: 'sm' | 'md' }) {
  return <StatusBadge status={MAP[status]} label={STATUS_LABEL[status]} size={size} />
}
