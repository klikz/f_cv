import { Fragment } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Kbd, KbdGroup } from '@/components/ui/kbd'
import { t } from '@/lib/i18n'

export type ShortcutGroup = { title: string; items: { keys: string[]; label: string }[] }

/** Global qisqa tugmalar. Sahifalar (belgilash, jurnal) keyin o'z guruhlarini qo'shadi. */
export const globalShortcuts: ShortcutGroup = {
  title: 'Umumiy',
  items: [
    { keys: ['Ctrl', 'K'], label: t.shortcuts.commandPalette },
    { keys: ['?'], label: t.shortcuts.help },
    { keys: ['Ctrl', 'B'], label: t.shortcuts.toggleSidebar },
    { keys: ['Shift', 'T'], label: t.shortcuts.toggleTheme },
    { keys: ['Esc'], label: t.shortcuts.escape },
  ],
}

export function ShortcutsDialog({
  open,
  onOpenChange,
  groups = [globalShortcuts],
}: {
  open: boolean
  onOpenChange: (o: boolean) => void
  groups?: ShortcutGroup[]
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t.shortcuts.title}</DialogTitle>
          <DialogDescription className="sr-only">{t.shortcuts.help}</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          {groups.map((g) => (
            <div key={g.title}>
              <div className="mb-2 text-xs font-medium tracking-wide text-muted-foreground uppercase">{g.title}</div>
              <div className="space-y-1.5">
                {g.items.map((it) => (
                  <div key={it.label} className="flex items-center justify-between gap-4 text-sm">
                    <span>{it.label}</span>
                    <KbdGroup>
                      {it.keys.map((k, i) => (
                        <Fragment key={k}>
                          {i > 0 && <span className="text-xs text-muted-foreground">+</span>}
                          <Kbd>{k}</Kbd>
                        </Fragment>
                      ))}
                    </KbdGroup>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}
