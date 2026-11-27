import { Search } from 'lucide-react'
import { createContext, Fragment, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { Link, Outlet, useParams } from 'react-router'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb'
import { Button } from '@/components/ui/button'
import { Kbd } from '@/components/ui/kbd'
import { Separator } from '@/components/ui/separator'
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'
import { useHotkeys } from '@/hooks/use-hotkeys'
import { t } from '@/lib/i18n'
import { storage } from '@/lib/storage'
import { useTheme } from '@/lib/theme'
import { AppSidebar } from './app-sidebar'
import { CommandPalette } from './command-palette'
import { HealthIndicators } from './health-indicators'
import { useRouteHandle } from './page'
import { ShortcutsDialog } from './shortcuts-dialog'

const SIDEBAR_KEY = 'fcv.sidebar.open'

type LayoutCtx = {
  fullscreen: boolean
  setFullscreen: (v: boolean) => void
  openCommand: () => void
  openShortcuts: () => void
}

const LayoutContext = createContext<LayoutCtx | null>(null)

// eslint-disable-next-line react-refresh/only-export-components
export function useLayout() {
  const ctx = useContext(LayoutContext)
  if (!ctx) throw new Error('useLayout AppLayout ichida ishlatilishi kerak')
  return ctx
}

function Breadcrumbs() {
  const handle = useRouteHandle()
  const params = useParams()
  const crumbs = handle?.crumbs(params) ?? []
  return (
    <Breadcrumb className="min-w-0">
      <BreadcrumbList className="flex-nowrap">
        {crumbs.map((c, i) => {
          const last = i === crumbs.length - 1
          return (
            <Fragment key={`${c.label}-${i}`}>
              {i > 0 && <BreadcrumbSeparator />}
              <BreadcrumbItem className="min-w-0">
                {last || !c.to ? (
                  <BreadcrumbPage className="truncate">{c.label}</BreadcrumbPage>
                ) : (
                  <BreadcrumbLink asChild className="truncate">
                    <Link to={c.to}>{c.label}</Link>
                  </BreadcrumbLink>
                )}
              </BreadcrumbItem>
            </Fragment>
          )
        })}
      </BreadcrumbList>
    </Breadcrumb>
  )
}

function TopBar({ onSearch }: { onSearch: () => void }) {
  return (
    <header className="sticky top-0 z-20 flex h-12 shrink-0 items-center gap-2 border-b bg-background/85 px-3 backdrop-blur">
      <SidebarTrigger aria-label={t.common.toggleSidebar} />
      <Separator orientation="vertical" className="h-4" />
      <Breadcrumbs />
      <div className="ml-auto flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="hidden w-56 justify-start gap-2 text-muted-foreground md:flex"
          onClick={onSearch}
        >
          <Search />
          <span className="flex-1 text-left">{t.common.search}…</span>
          <Kbd>Ctrl K</Kbd>
        </Button>
        <Button variant="ghost" size="icon-sm" className="md:hidden" onClick={onSearch} aria-label={t.command.open}>
          <Search />
        </Button>
        <HealthIndicators />
      </div>
    </header>
  )
}

export function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(() => storage.get<boolean>(SIDEBAR_KEY) ?? true)
  const [cmdOpen, setCmdOpen] = useState(false)
  const [helpOpen, setHelpOpen] = useState(false)
  const [fullscreen, setFullscreenState] = useState(false)
  const { toggleTheme } = useTheme()
  const handle = useRouteHandle()

  const onSidebarChange = (o: boolean) => {
    setSidebarOpen(o)
    storage.set(SIDEBAR_KEY, o)
  }

  const setFullscreen = useCallback((v: boolean) => {
    setFullscreenState(v)
    try {
      if (v && !document.fullscreenElement) void document.documentElement.requestFullscreen?.()
      if (!v && document.fullscreenElement) void document.exitFullscreen?.()
    } catch {
      /* brauzer ruxsat bermasa — faqat panellar yashiriladi */
    }
  }, [])

  useEffect(() => {
    const onFs = () => {
      if (!document.fullscreenElement) setFullscreenState(false)
    }
    document.addEventListener('fullscreenchange', onFs)
    return () => document.removeEventListener('fullscreenchange', onFs)
  }, [])

  useHotkeys([
    { combo: 'mod+k', handler: () => setCmdOpen((o) => !o), allowInInput: true },
    { combo: '?', handler: () => setHelpOpen(true) },
    { combo: 'shift+t', handler: toggleTheme },
    { combo: 'escape', handler: () => fullscreen && setFullscreen(false) },
  ])

  const ctx = useMemo<LayoutCtx>(
    () => ({
      fullscreen,
      setFullscreen,
      openCommand: () => setCmdOpen(true),
      openShortcuts: () => setHelpOpen(true),
    }),
    [fullscreen, setFullscreen],
  )

  return (
    <LayoutContext value={ctx}>
      <SidebarProvider open={sidebarOpen && !fullscreen} onOpenChange={onSidebarChange}>
        {!fullscreen && <AppSidebar />}
        <SidebarInset className="min-w-0">
          {!fullscreen && <TopBar onSearch={() => setCmdOpen(true)} />}
          <div className={handle?.bleed ? 'flex min-h-0 flex-1 flex-col' : 'flex-1'}>
            <Outlet />
          </div>
        </SidebarInset>
        <CommandPalette open={cmdOpen} onOpenChange={setCmdOpen} onShowShortcuts={() => setHelpOpen(true)} />
        <ShortcutsDialog open={helpOpen} onOpenChange={setHelpOpen} />
      </SidebarProvider>
    </LayoutContext>
  )
}
