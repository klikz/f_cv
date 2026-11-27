import { createBrowserRouter, type RouteObject } from 'react-router'
import type { Crumb, RouteHandle } from '@/app/crumbs'
import { showDev } from '@/app/nav'
import { AppLayout } from '@/components/layout/app-layout'
import { t } from '@/lib/i18n'
import { NotFoundPage, RouteErrorPage } from '@/pages/not-found'
import { PlaceholderPage } from '@/pages/placeholder'

/*
 * URL tuzilmasi — PLAN.md 4.2. URL nomlari inglizcha va barqaror (o'zgartirilmaydi).
 */

const grid: Crumb = { label: t.pages.grid, to: '/' }
const camera = (id?: string): Crumb => ({ label: `${t.pages.camera} ${id ?? ''}`.trim(), to: `/cameras/${id}` })
const cameras: Crumb = { label: t.pages.cameras, to: '/settings/cameras' }
const products: Crumb = { label: t.pages.products, to: '/products' }
const dataset: Crumb = { label: t.pages.dataset, to: '/dataset' }
const training: Crumb = { label: t.pages.training, to: '/training' }
const models: Crumb = { label: t.pages.models, to: '/models' }
const counts: Crumb = { label: t.pages.counts, to: '/counts' }

const h = (crumbs: RouteHandle['crumbs'], stage?: number, extra?: Partial<RouteHandle>): RouteHandle => ({
  crumbs,
  stage,
  ...extra,
})

type PageRoute = { path: string; handle: RouteHandle; element?: React.ReactNode; lazy?: RouteObject['lazy'] }

/** Tayyor sahifalar `lazy` bilan ulanadi; qolganlari — bo'sh sahifa (bosqich raqami bilan). */
export const pageRoutes: PageRoute[] = [
  { path: '/', handle: h(() => [{ label: t.pages.grid }], 1, { bleed: true }), lazy: async () => ({ Component: (await import('@/pages/grid/grid-page')).GridPage }) },
  { path: '/cameras/:id', handle: h((p) => [grid, { ...camera(p.id), to: undefined }], 1, { bleed: true }), lazy: async () => ({ Component: (await import('@/pages/cameras/camera-page')).CameraPage }) },
  {
    path: '/cameras/:id/counting',
    handle: h((p) => [grid, camera(p.id), { label: t.pages.counting }], 2, { bleed: true }),
    lazy: async () => ({ Component: (await import('@/pages/tasks/counting-page')).CountingPage }),
  },
  {
    path: '/cameras/:id/equipment',
    handle: h((p) => [grid, camera(p.id), { label: t.pages.equipment }], 2, { bleed: true }),
    lazy: async () => ({ Component: (await import('@/pages/tasks/equipment-page')).EquipmentPage }),
  },
  { path: '/settings/cameras', handle: h(() => [{ label: t.pages.cameras }], 1), lazy: async () => ({ Component: (await import('@/pages/cameras/cameras-list-page')).CamerasListPage }) },
  { path: '/settings/cameras/new', handle: h(() => [cameras, { label: t.pages.cameraNew }], 1), lazy: async () => ({ Component: (await import('@/pages/cameras/camera-form-page')).CameraFormPage }) },
  {
    path: '/settings/cameras/:id/edit',
    handle: h((p) => [cameras, { label: `${t.pages.camera} ${p.id}` }, { label: t.pages.cameraEdit }], 1),
    lazy: async () => ({ Component: (await import('@/pages/cameras/camera-form-page')).CameraFormPage }),
  },
  { path: '/products', handle: h(() => [{ label: t.pages.products }], 3), lazy: async () => ({ Component: (await import('@/pages/products/products-page')).ProductsPage }) },
  { path: '/products/new', handle: h(() => [products, { label: t.pages.productNew }], 3), lazy: async () => ({ Component: (await import('@/pages/products/product-page')).ProductPage }) },
  { path: '/products/:id', handle: h((p) => [products, { label: `${t.pages.product} ${p.id}` }], 3), lazy: async () => ({ Component: (await import('@/pages/products/product-page')).ProductPage }) },
  { path: '/dataset', handle: h(() => [{ label: t.pages.dataset }], 3), lazy: async () => ({ Component: (await import('@/pages/dataset/dataset-page')).DatasetPage }) },
  {
    path: '/dataset/annotate/:imageId',
    handle: h((p) => [dataset, { label: `${t.pages.annotate} #${p.imageId}` }], 3, { bleed: true }),
    lazy: async () => ({ Component: (await import('@/pages/dataset/annotate-page')).AnnotatePage }),
  },
  { path: '/training', handle: h(() => [{ label: t.pages.training }], 3), lazy: async () => ({ Component: (await import('@/pages/training/training-page')).TrainingPage }) },
  { path: '/training/:jobId', handle: h((p) => [training, { label: `${t.pages.trainingJob} #${p.jobId}` }], 3), lazy: async () => ({ Component: (await import('@/pages/training/job-page')).JobPage }) },
  { path: '/models', handle: h(() => [{ label: t.pages.models }], 3), lazy: async () => ({ Component: (await import('@/pages/models/models-page')).ModelsPage }) },
  { path: '/models/:productId', handle: h((p) => [models, { label: `${t.pages.modelVersions} #${p.productId}` }], 3), lazy: async () => ({ Component: (await import('@/pages/models/versions-page')).VersionsPage }) },
  { path: '/counts', handle: h(() => [{ label: t.pages.counts }], 4), lazy: async () => ({ Component: (await import('@/pages/counts/counts-page')).CountsPage }) },
  { path: '/counts/:eventId', handle: h((p) => [counts, { label: `${t.pages.countEvent} #${p.eventId}` }], 4), lazy: async () => ({ Component: (await import('@/pages/counts/count-page')).CountPage }) },
  { path: '/reports', handle: h(() => [{ label: t.pages.reports }], 7), lazy: async () => ({ Component: (await import('@/pages/reports/reports-page')).ReportsPage }) },
  { path: '/telegram', handle: h(() => [{ label: t.pages.telegram }], 6), lazy: async () => ({ Component: (await import('@/pages/telegram/telegram-page')).TelegramPage }) },
  { path: '/settings/shifts', handle: h(() => [{ label: t.pages.shifts }], 7), lazy: async () => ({ Component: (await import('@/pages/settings/shifts-page')).ShiftsPage }) },
  { path: '/settings/general', handle: h(() => [{ label: t.pages.general }], 8), lazy: async () => ({ Component: (await import('@/pages/settings/general-page')).GeneralPage }) },
]

const devRoutes: PageRoute[] = showDev
  ? [
      {
        path: '/dev/ui',
        handle: h(() => [{ label: t.pages.devUi }], 0),
        lazy: async () => ({ Component: (await import('@/pages/dev-ui/dev-ui-page')).DevUiPage }),
      },
    ]
  : []

export function createAppRouter() {
  const children: RouteObject[] = [...pageRoutes, ...devRoutes].map((r) => {
    return {
      path: r.path,
      handle: r.handle,
      ...(r.lazy ? { lazy: r.lazy } : { element: r.element ?? <PlaceholderPage /> }),
    } as RouteObject
  })
  children.push({ path: '*', element: <NotFoundPage />, handle: h(() => [{ label: t.pages.notFound }]) })

  return createBrowserRouter([{ element: <AppLayout />, errorElement: <RouteErrorPage />, children }])
}
