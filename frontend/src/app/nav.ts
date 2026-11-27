import {
  Activity,
  BarChart3,
  Boxes,
  BrainCircuit,
  Camera,
  Clock,
  Images,
  LayoutGrid,
  ListChecks,
  Send,
  SlidersHorizontal,
  type LucideIcon,
} from 'lucide-react'
import { t } from '@/lib/i18n'

export type NavItem = {
  to: string
  label: string
  icon: LucideIcon
  /** Buyruqlar oynasida qidirish uchun qo'shimcha so'zlar. */
  keywords?: string[]
  /** Faqat ishlab chiqishda ko'rinadi. */
  devOnly?: boolean
}

export type NavGroup = { label: string; items: NavItem[] }

export const navGroups: NavGroup[] = [
  {
    label: t.nav.groups.monitoring,
    items: [
      { to: '/', label: t.nav.grid, icon: LayoutGrid, keywords: ['grid', 'bosh sahifa', 'video'] },
      { to: '/counts', label: t.nav.counts, icon: ListChecks, keywords: ['sanoq', 'snapshot', 'noaniq'] },
      { to: '/reports', label: t.nav.reports, icon: BarChart3, keywords: ['hisobot', 'smena'] },
    ],
  },
  {
    label: t.nav.groups.data,
    items: [
      { to: '/products', label: t.nav.products, icon: Boxes, keywords: ['katalog', 'mahsulot'] },
      { to: '/dataset', label: t.nav.dataset, icon: Images, keywords: ['rasm', 'belgilash', 'annotatsiya'] },
    ],
  },
  {
    label: t.nav.groups.ai,
    items: [
      { to: '/training', label: t.nav.training, icon: Activity, keywords: ['train', "o'qitish", 'navbat'] },
      { to: '/models', label: t.nav.models, icon: BrainCircuit, keywords: ['model', 'versiya', 'engine'] },
    ],
  },
  {
    label: t.nav.groups.settings,
    items: [
      { to: '/settings/cameras', label: t.nav.cameras, icon: Camera, keywords: ['kamera', 'rtsp', 'onvif'] },
      { to: '/settings/shifts', label: t.nav.shifts, icon: Clock, keywords: ['smena'] },
      { to: '/telegram', label: t.nav.telegram, icon: Send, keywords: ['bot', 'xabar', 'chat'] },
      { to: '/settings/general', label: t.nav.general, icon: SlidersHorizontal, keywords: ['disk', 'parametr'] },
    ],
  },
]

export const showDev = import.meta.env.DEV || import.meta.env.VITE_SHOW_DEV === '1'

export const visibleNavGroups = navGroups
  .map((g) => ({ ...g, items: g.items.filter((i) => !i.devOnly || showDev) }))
  .filter((g) => g.items.length > 0)
