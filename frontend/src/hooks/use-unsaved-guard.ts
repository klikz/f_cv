import { useEffect } from 'react'
import { useBlocker } from 'react-router'
import { useConfirm } from '@/components/common/confirm-dialog'
import { t } from '@/lib/i18n'

/** Saqlanmagan o'zgarish bo'lsa — sahifadan chiqishda (ichki havola va brauzer yopilishi) ogohlantirish. */
export function useUnsavedGuard(dirty: boolean) {
  const blocker = useBlocker(({ currentLocation, nextLocation }) => dirty && currentLocation.pathname !== nextLocation.pathname)
  const confirm = useConfirm()

  useEffect(() => {
    if (blocker.state !== 'blocked') return
    void confirm({
      title: "Saqlanmagan o'zgarishlar",
      description: t.common.unsavedChanges,
      confirmText: 'Chiqish',
      cancelText: 'Qolish',
      destructive: true,
    }).then((ok) => (ok ? blocker.proceed() : blocker.reset()))
  }, [blocker, confirm])

  useEffect(() => {
    if (!dirty) return
    const h = (e: BeforeUnloadEvent) => {
      e.preventDefault()
    }
    window.addEventListener('beforeunload', h)
    return () => window.removeEventListener('beforeunload', h)
  }, [dirty])
}
