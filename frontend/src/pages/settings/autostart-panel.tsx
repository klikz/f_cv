import { Monitor, Power, TriangleAlert, UserCheck } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { SelectField } from '@/components/common/fields'
import { StatusBadge } from '@/components/common/status-badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { api } from '@/lib/api'
import { notify } from '@/lib/notify'

type Autostart = {
  user: string
  helper: boolean
  services: { installed: boolean; enabled: boolean; state: string; active: boolean }
  kiosk: { enabled: boolean; browser: string | null; fullscreen: boolean; path: string; url: string; browsers: string[] }
  autologin: { supported: boolean; enabled: boolean; user: string | null; other_user: boolean }
}
type Item = 'services' | 'kiosk' | 'autologin'
const BROWSER: Record<string, string> = { 'google-chrome': 'Google Chrome', chromium: 'Chromium', firefox: 'Firefox' }

function Row({ icon, title, desc, checked, disabled, onChange, children }: { icon: ReactNode; title: string; desc: ReactNode; checked: boolean; disabled?: boolean; onChange: (v: boolean) => void; children?: ReactNode }) {
  const id = `as-${title}`
  return (
    <div className="space-y-2 rounded-lg border p-3">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 text-muted-foreground">{icon}</div>
        <div className="flex-1 space-y-0.5">
          <Label htmlFor={id} className="text-sm font-medium">{title}</Label>
          <div className="text-xs text-muted-foreground">{desc}</div>
        </div>
        <Switch id={id} checked={checked} disabled={disabled} onCheckedChange={onChange} />
      </div>
      {children}
    </div>
  )
}

export function AutostartPanel() {
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ['sys-autostart'], queryFn: () => api.get<Autostart>('/system/autostart'), refetchInterval: 15000 })
  const [busy, setBusy] = useState<Item | null>(null)
  const [browser, setBrowser] = useState<string | null>(null)
  if (!data) return <Skeleton className="h-64 w-full" />
  const br = browser ?? data.kiosk.browser ?? data.kiosk.browsers[0] ?? ''

  const put = async (item: Item, body: { enabled: boolean; browser?: string; fullscreen?: boolean }, ok: string) => {
    setBusy(item)
    try {
      qc.setQueryData(['sys-autostart'], await api.put<Autostart>(`/system/autostart/${item}`, body, { timeoutMs: 60000 }))
      notify.success(ok)
    } catch (e) {
      notify.error("O'zgartirib bo'lmadi", e)
    } finally {
      setBusy(null)
    }
  }
  const s = data.services
  const sysLocked = !data.helper

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card className="lg:col-span-2">
        <CardHeader><CardTitle className="flex items-center gap-2 text-base"><Power className="size-4" /> Avtomatik ishga tushish</CardTitle></CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p className="text-muted-foreground">
            Ubuntu 26.04 LTS: servislar <b>systemd</b> orqali, brauzer — GNOME avtomatik ishga tushish ro'yxati orqali ochiladi. Foydalanuvchi: <code>{data.user}</code>.
          </p>
          {sysLocked && (
            <p className="flex items-start gap-2 rounded-md border border-warning/40 bg-warning/10 p-2 text-warning">
              <TriangleAlert className="mt-0.5 size-4 shrink-0" />
              <span>
                Servislar va avtomatik kirishni UI dan boshqarish uchun serverda bir marta o'rnatish kerak: <code>sudo deploy/install.sh</code>
                {!s.installed && ' (systemd unitlari ham hali o\'rnatilmagan)'}. Brauzerni avtomatik ochish o'rnatishsiz ham ishlaydi.
              </span>
            </p>
          )}
          <Row
            icon={<Power className="size-4" />}
            title="F_CV servislari"
            desc={
              <span className="flex flex-wrap items-center gap-2">
                Kompyuter yonganda barcha servislar (API, video, kamera logikasi, inference, train, Telegram, zaxira) ishga tushadi.
                {s.installed ? <StatusBadge size="sm" status={s.active ? 'ok' : 'stopped'} label={s.active ? 'systemd: ishlayapti' : 'systemd: to\'xtagan'} /> : <StatusBadge size="sm" status="unknown" label="systemd unitlari o'rnatilmagan" />}
              </span>
            }
            checked={s.enabled}
            disabled={sysLocked || !s.installed || busy !== null}
            onChange={(v) => void put('services', { enabled: v }, v ? 'Servislar kompyuter yonganda ishga tushadi' : "Servislarning avtomatik ishga tushishi o'chirildi (hozir ishlayotganlari to'xtatilmadi)")}
          />
          <Row
            icon={<Monitor className="size-4" />}
            title="Brauzerda kuzatuv panelini ochish"
            desc={<>Tizimga kirgach <code>{data.kiosk.url}</code> avtomatik ochiladi (API tayyor bo'lishini kutadi). Fayl: <code className="break-all">{data.kiosk.path}</code></>}
            checked={data.kiosk.enabled}
            disabled={busy !== null || (!data.kiosk.enabled && !data.kiosk.browsers.length)}
            onChange={(v) => void put('kiosk', { enabled: v, browser: br, fullscreen: data.kiosk.fullscreen }, v ? 'Brauzer avtomatik ochiladi' : "Brauzerni avtomatik ochish o'chirildi")}
          >
            {!data.kiosk.browsers.length ? (
              <p className="pl-7 text-xs text-danger">Brauzer topilmadi: google-chrome, chromium yoki firefox o'rnating.</p>
            ) : (
              <div className="grid gap-3 pl-7 sm:grid-cols-2">
                <SelectField
                  id="as-browser"
                  label="Brauzer"
                  value={br}
                  onChange={(b) => {
                    setBrowser(b)
                    if (data.kiosk.enabled) void put('kiosk', { enabled: true, browser: b, fullscreen: data.kiosk.fullscreen }, 'Brauzer almashtirildi')
                  }}
                  options={data.kiosk.browsers.map((b) => ({ value: b, label: BROWSER[b] ?? b }))}
                />
                <div className="flex items-center gap-2 self-end pb-1.5">
                  <Switch id="as-full" size="sm" checked={data.kiosk.fullscreen} disabled={!data.kiosk.enabled || busy !== null} onCheckedChange={(f) => void put('kiosk', { enabled: true, browser: br, fullscreen: f }, f ? "To'liq ekran (kiosk) yoqildi" : 'Oddiy oyna rejimi')} />
                  <Label htmlFor="as-full" className="text-sm">To'liq ekran (kiosk)</Label>
                </div>
              </div>
            )}
          </Row>
          <Row
            icon={<UserCheck className="size-4" />}
            title="Avtomatik kirish (login oynasisiz)"
            desc={
              data.autologin.supported ? (
                <>
                  Kompyuter yonganda <code>{data.user}</code> foydalanuvchisi parolsiz kiradi — panel login oynasini kutmasdan ochiladi (GDM).
                  {data.autologin.other_user && <span className="text-warning"> Hozir boshqa foydalanuvchi uchun yoqilgan: {data.autologin.user}.</span>}
                </>
              ) : (
                'GDM topilmadi (/etc/gdm3/custom.conf) — bu sozlama faqat Ubuntu Desktop (GNOME) da ishlaydi.'
              )
            }
            checked={data.autologin.enabled}
            disabled={sysLocked || !data.autologin.supported || busy !== null}
            onChange={(v) => void put('autologin', { enabled: v }, v ? 'Avtomatik kirish yoqildi (keyingi yonishda)' : "Avtomatik kirish o'chirildi")}
          />
        </CardContent>
      </Card>
    </div>
  )
}
