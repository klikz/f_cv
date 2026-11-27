import { Moon, Sun } from 'lucide-react'
import { SidebarMenu, SidebarMenuButton, SidebarMenuItem } from '@/components/ui/sidebar'
import { t } from '@/lib/i18n'
import { useTheme } from '@/lib/theme'

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()
  const Icon = theme === 'dark' ? Sun : Moon
  const label = theme === 'dark' ? t.theme.light : t.theme.dark
  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <SidebarMenuButton onClick={toggleTheme} tooltip={t.theme.toggle} aria-label={t.theme.toggle}>
          <Icon />
          <span>
            {t.theme.label}: {label}
          </span>
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>
  )
}
