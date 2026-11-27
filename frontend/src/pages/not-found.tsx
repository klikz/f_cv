import { House, MapPinOff } from 'lucide-react'
import { isRouteErrorResponse, Link, useRouteError } from 'react-router'
import { EmptyState, ErrorState } from '@/components/common/states'
import { Button } from '@/components/ui/button'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { t } from '@/lib/i18n'

export function NotFoundPage() {
  useDocumentTitle(t.pages.notFound)
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <EmptyState
        icon={MapPinOff}
        title={t.pages.notFound}
        description={t.errors.notFound}
        action={
          <Button asChild>
            <Link to="/">
              <House /> {t.common.goHome}
            </Link>
          </Button>
        }
      />
    </div>
  )
}

/** Marshrut ichidagi kutilmagan xato (komponent yiqilsa). */
export function RouteErrorPage() {
  const err = useRouteError()
  useDocumentTitle(t.errors.generic)
  if (isRouteErrorResponse(err) && err.status === 404) return <NotFoundPage />
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <ErrorState error={err} onRetry={() => window.location.reload()} />
    </div>
  )
}
