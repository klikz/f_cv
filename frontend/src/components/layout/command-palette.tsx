import { Keyboard, Moon, PanelLeft, Sun } from 'lucide-react'
import { useNavigate } from 'react-router'
import { visibleNavGroups } from '@/app/nav'
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from '@/components/ui/command'
import { useSidebar } from '@/components/ui/sidebar'
import { t } from '@/lib/i18n'
import { useTheme } from '@/lib/theme'

/**
 * Buyruqlar oynasi (Ctrl+K): sahifa, kamera, mahsulotni nomidan topib ochish.
 * Hozircha sahifalar va umumiy amallar; kameralar va mahsulotlar 1/3-bosqichda qo'shiladi.
 */
export function CommandPalette({
  open,
  onOpenChange,
  onShowShortcuts,
}: {
  open: boolean
  onOpenChange: (o: boolean) => void
  onShowShortcuts: () => void
}) {
  const navigate = useNavigate()
  const { theme, toggleTheme } = useTheme()
  const { toggleSidebar } = useSidebar()

  const run = (fn: () => void) => {
    onOpenChange(false)
    fn()
  }

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange} title={t.command.open} description={t.command.placeholder}>
      <CommandInput placeholder={t.command.placeholder} />
      <CommandList>
        <CommandEmpty>{t.command.empty}</CommandEmpty>
        {visibleNavGroups.map((g) => (
          <CommandGroup key={g.label} heading={g.label}>
            {g.items.map((item) => (
              <CommandItem
                key={item.to}
                value={`${item.label} ${item.keywords?.join(' ') ?? ''}`}
                onSelect={() => run(() => navigate(item.to))}
              >
                <item.icon />
                {item.label}
              </CommandItem>
            ))}
          </CommandGroup>
        ))}
        <CommandSeparator />
        <CommandGroup heading={t.command.actions}>
          <CommandItem value={`${t.theme.toggle} mavzu theme`} onSelect={() => run(toggleTheme)}>
            {theme === 'dark' ? <Sun /> : <Moon />}
            {t.theme.toggle}
            <CommandShortcut>Shift+T</CommandShortcut>
          </CommandItem>
          <CommandItem value={`${t.shortcuts.toggleSidebar} menyu`} onSelect={() => run(toggleSidebar)}>
            <PanelLeft />
            {t.shortcuts.toggleSidebar}
            <CommandShortcut>Ctrl+B</CommandShortcut>
          </CommandItem>
          <CommandItem value={`${t.shortcuts.title} klaviatura`} onSelect={() => run(onShowShortcuts)}>
            <Keyboard />
            {t.shortcuts.title}
            <CommandShortcut>?</CommandShortcut>
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  )
}
