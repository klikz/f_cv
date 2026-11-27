import { QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router'
import { createAppRouter } from '@/app/router'
import { ConfirmProvider } from '@/components/common/confirm-dialog'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { queryClient } from '@/lib/api'
import { applyTheme, readInitialTheme, ThemeProvider } from '@/lib/theme'
import './index.css'

// Mavzuni birinchi chizishdan oldin qo'llash (miltillamasin)
applyTheme(readInitialTheme())

const router = createAppRouter()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider delayDuration={300}>
          <ConfirmProvider>
            <RouterProvider router={router} />
            <Toaster position="bottom-right" closeButton />
          </ConfirmProvider>
        </TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
)
