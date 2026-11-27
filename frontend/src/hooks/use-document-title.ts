import { useEffect } from 'react'
import { t } from '@/lib/i18n'

/** Brauzer yorlig'idagi nom: "Kamera 3 — Sanash sozlamalari · F_CV". */
export function useDocumentTitle(...parts: (string | null | undefined | false)[]) {
  const title = parts.filter(Boolean).join(' — ')
  useEffect(() => {
    document.title = title ? `${title} · ${t.app.name}` : t.app.name
  }, [title])
}
