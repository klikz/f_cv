import { Construction } from 'lucide-react'
import { EmptyState } from '@/components/common/states'
import { PageBody, PageHeader, useRouteHandle, useRouteTitle } from '@/components/layout/page'
import { t } from '@/lib/i18n'

/** Hali amalga oshirilmagan sahifa: o'z URL'i, nomi va non bo'laklari bilan ishlaydi. */
export function PlaceholderPage() {
  const handle = useRouteHandle()
  const title = useRouteTitle()
  return (
    <PageBody>
      <PageHeader title={title} />
      <div className="rounded-xl border border-dashed">
        <EmptyState
          icon={Construction}
          title={t.placeholder.title}
          description={handle?.stage !== undefined ? t.placeholder.description(handle.stage) : undefined}
        />
      </div>
    </PageBody>
  )
}
