import { useEffect, useLayoutEffect, useRef } from 'react'

export type Hotkey = {
  /** Masalan: 'mod+k', '?', 'escape', 'shift+d'. `mod` = Ctrl (Mac'da Cmd). */
  combo: string
  handler: (e: KeyboardEvent) => void
  /** Matn kiritish maydonida ham ishlasinmi (default: faqat mod+ kombinatsiyalar). */
  allowInInput?: boolean
}

function isEditable(el: EventTarget | null) {
  if (!(el instanceof HTMLElement)) return false
  return el.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName)
}

function matches(e: KeyboardEvent, combo: string) {
  const parts = combo.toLowerCase().split('+')
  const key = parts.pop()!
  const mod = parts.includes('mod')
  const shift = parts.includes('shift')
  const alt = parts.includes('alt')
  const isMac = navigator.platform.toLowerCase().includes('mac')
  const modPressed = isMac ? e.metaKey : e.ctrlKey
  if (mod !== modPressed) return false
  if (alt !== e.altKey) return false
  // '?' kabi belgilarda shift tabiiy — tekshirmaymiz
  if (key.length > 1 || /[a-z0-9]/.test(key)) {
    if (shift !== e.shiftKey) return false
  }
  return e.key.toLowerCase() === key
}

/** Global klaviatura qisqa tugmalari. */
export function useHotkeys(hotkeys: Hotkey[]) {
  const ref = useRef(hotkeys)
  useLayoutEffect(() => {
    ref.current = hotkeys
  })

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      for (const h of ref.current) {
        if (!matches(e, h.combo)) continue
        const hasMod = h.combo.includes('mod+')
        if (isEditable(e.target) && !h.allowInInput && !hasMod) continue
        e.preventDefault()
        h.handler(e)
        return
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])
}
