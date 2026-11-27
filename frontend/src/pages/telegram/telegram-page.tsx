import { KeyRound, Loader2, MessageSquare, Save, Send, Users } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { StatusBadge, type StatusKind } from '@/components/common/status-badge'
import { EmptyState } from '@/components/common/states'
import { PageBody, PageHeader, useRouteTitle } from '@/components/layout/page'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useCameras } from '@/hooks/use-cameras'
import { param, useUrlState } from '@/hooks/use-url-state'
import { api } from '@/lib/api'
import { fmtDateTime } from '@/lib/format'
import { notify } from '@/lib/notify'
import { cn } from '@/lib/utils'

type MsgType = { code: string; title: string; task: 'counting' | 'equipment' | 'system'; params: Record<string, number>; per_camera: boolean }
type Status = { state: string; label: string; error: string | null; username: string | null; has_token: boolean; outbox: Record<string, number>; types: MsgType[] }
type Chat = { id: number; chat_id: number; title: string; type: string; active: boolean; subscriptions: number; created_at: string }
type Sub = { camera_id: number | null; message_type: string; params: Record<string, number> }

const STATE_KIND: Record<string, StatusKind> = { connected: 'online', no_internet: 'offline', bad_token: 'error', no_token: 'disabled', starting: 'connecting' }
const TASK_LABEL = { counting: 'Mahsulot sanash', equipment: 'Uskuna ish vaqti', system: 'Tizim' }

function TokenCard({ status }: { status: Status }) {
  const [token, setToken] = useState('')
  const qc = useQueryClient()
  const save = async () => {
    try {
      await api.put('/telegram/token', { token })
      setToken('')
      notify.success('Token saqlandi', 'Bot bir necha soniyada ulanadi')
      void qc.invalidateQueries({ queryKey: ['tg-status'] })
    } catch (e) {
      notify.error("Saqlab bo'lmadi", e)
    }
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      <KeyRound className="size-4 text-muted-foreground" />
      <Input type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder={status.has_token ? 'Token kiritilgan — almashtirish uchun yangisini yozing' : 'Bot tokeni (BotFather)'} className="h-8 max-w-md" autoComplete="off" />
      <Button size="sm" onClick={save} disabled={!token}>
        <Save /> Saqlash
      </Button>
    </div>
  )
}

function Matrix({ chat, types }: { chat: Chat; types: MsgType[] }) {
  const qc = useQueryClient()
  const { data: cams } = useCameras()
  const { data } = useQuery({ queryKey: ['tg-subs', chat.id], queryFn: () => api.get<{ items: Sub[] }>(`/telegram/chats/${chat.id}/subscriptions`) })
  const [subs, setSubs] = useState<Sub[]>([])
  const [dirty, setDirty] = useState(false)
  useEffect(() => {
    if (data) {
      setSubs(data.items)
      setDirty(false)
    }
  }, [data])
  const has = (cam: number | null, code: string) => subs.some((s) => s.camera_id === cam && s.message_type === code)
  const toggle = (cam: number | null, code: string, on: boolean, params: Record<string, number>) => {
    setSubs(on ? [...subs, { camera_id: cam, message_type: code, params }] : subs.filter((s) => !(s.camera_id === cam && s.message_type === code)))
    setDirty(true)
  }
  const param = (code: string, key: string) => subs.find((s) => s.message_type === code)?.params?.[key]
  const setParam = (code: string, key: string, v: number) => {
    setSubs(subs.map((s) => (s.message_type === code ? { ...s, params: { ...s.params, [key]: v } } : s)))
    setDirty(true)
  }
  const save = async () => {
    try {
      await api.put(`/telegram/chats/${chat.id}/subscriptions`, { items: subs })
      setDirty(false)
      notify.success('Obunalar saqlandi')
      void qc.invalidateQueries({ queryKey: ['tg-chats'] })
    } catch (e) {
      notify.error("Saqlab bo'lmadi", e)
    }
  }
  const camTypes = types.filter((t) => t.per_camera)
  const sysTypes = types.filter((t) => !t.per_camera)

  return (
    <div className="space-y-3">
      <div className="overflow-x-auto rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="min-w-36">Kamera</TableHead>
              {camTypes.map((t) => (
                <TableHead key={t.code} className="text-center text-xs">
                  <div className="text-2xs font-normal text-muted-foreground">{TASK_LABEL[t.task]}</div>
                  {t.title}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {cams?.map((c) => (
              <TableRow key={c.id}>
                <TableCell className="font-medium">{c.name}</TableCell>
                {camTypes.map((t) => (
                  <TableCell key={t.code} className="text-center">
                    <Checkbox checked={has(c.id, t.code)} onCheckedChange={(v) => toggle(c.id, t.code, v === true, t.params)} aria-label={`${c.name}: ${t.title}`} />
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <div className="flex flex-wrap items-center gap-4">
        {sysTypes.map((t) => (
          <label key={t.code} className="flex items-center gap-2 text-sm">
            <Checkbox checked={has(null, t.code)} onCheckedChange={(v) => toggle(null, t.code, v === true, t.params)} /> {t.title}
          </label>
        ))}
        {types
          .filter((t) => Object.keys(t.params).length)
          .map((t) =>
            Object.entries(t.params).map(([k, dv]) => (
              <label key={`${t.code}-${k}`} className="flex items-center gap-2 text-sm">
                "{t.title}" — N =
                <Input type="number" min={1} className="num h-7 w-16" value={param(t.code, k) ?? dv} onChange={(e) => setParam(t.code, k, Number(e.target.value))} />
                daqiqa
              </label>
            )),
          )}
      </div>
      <div className="flex justify-end gap-2">
        <Button size="sm" variant="outline" onClick={async () => { try { await api.post(`/telegram/chats/${chat.id}/test`); notify.success("Sinov xabari navbatga qo'yildi") } catch (e) { notify.error("Yuborib bo'lmadi", e) } }}>
          <Send /> Sinov xabari
        </Button>
        <Button size="sm" onClick={save} disabled={!dirty}>
          <Save /> Saqlash
        </Button>
      </div>
    </div>
  )
}

export function TelegramPage() {
  const title = useRouteTitle()
  const { data: st } = useQuery({ queryKey: ['tg-status'], queryFn: () => api.get<Status>('/telegram/status'), refetchInterval: 5000 })
  const { data: chats } = useQuery({ queryKey: ['tg-chats'], queryFn: () => api.get<Chat[]>('/telegram/chats'), refetchInterval: 10000 })
  const { data: outbox } = useQuery({ queryKey: ['tg-outbox'], queryFn: () => api.get<{ id: number; chat: string; type: string; status: string; attempts: number; error: string | null; created_at: string; text: string }[]>('/telegram/outbox', { query: { limit: 20 } }), refetchInterval: 5000 })
  const [sel, setSel] = useUrlState('chat', param.int, 0)
  const chat = useMemo(() => chats?.find((c) => c.id === sel) ?? chats?.[0], [chats, sel])

  return (
    <PageBody>
      <PageHeader title={title} description="Bot qo'shilgan chat va guruhlar avtomatik paydo bo'ladi. Har chat uchun kamera × xabar turi tanlanadi. Internet yo'q bo'lsa xabarlar navbatda kutadi." />
      <div className="space-y-4">
        <Card>
          <CardContent className="flex flex-wrap items-center gap-4 pt-4">
            {st ? (
              <>
                <StatusBadge status={STATE_KIND[st.state] ?? 'unknown'} label={st.label} />
                {st.username && <span className="text-sm">@{st.username}</span>}
                {st.error && st.state !== 'no_token' && <span className="text-sm text-danger">{st.error}</span>}
                <span className="ml-auto flex gap-3 text-sm">
                  <span>Kutmoqda: <b className="num">{st.outbox.pending ?? 0}</b></span>
                  <span>Yuborildi: <b className="num text-success">{st.outbox.sent ?? 0}</b></span>
                  <span>Xato: <b className={cn('num', (st.outbox.failed ?? 0) > 0 && 'text-danger')}>{st.outbox.failed ?? 0}</b></span>
                </span>
              </>
            ) : (
              <Loader2 className="size-4 animate-spin" />
            )}
          </CardContent>
          {st && <CardContent><TokenCard status={st} /></CardContent>}
        </Card>
        <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
          <Card className="h-fit">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base"><Users className="size-4" /> Chatlar</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1">
              {!chats?.length && <p className="text-sm text-muted-foreground">Botni guruhga qo'shing yoki shaxsiy chatda /start bosing — chat shu yerda paydo bo'ladi.</p>}
              {chats?.map((c) => (
                <button key={c.id} type="button" onClick={() => setSel(c.id)} className={cn('flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent', chat?.id === c.id && 'bg-accent')}>
                  <MessageSquare className="size-4 text-muted-foreground" />
                  <span className="flex-1 truncate">{c.title}</span>
                  {!c.active && <Badge variant="secondary">faol emas</Badge>}
                  <span className="num text-xs text-muted-foreground">{c.subscriptions}</span>
                </button>
              ))}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{chat ? `${chat.title} — obunalar` : 'Obunalar'}</CardTitle>
            </CardHeader>
            <CardContent>{chat && st ? <Matrix key={chat.id} chat={chat} types={st.types} /> : <EmptyState compact title="Chat tanlanmagan" />}</CardContent>
          </Card>
        </div>
        {outbox && outbox.length > 0 && (
          <Card>
            <CardHeader><CardTitle className="text-base">Oxirgi xabarlar</CardTitle></CardHeader>
            <CardContent className="overflow-x-auto">
              <Table>
                <TableHeader><TableRow><TableHead>Vaqt</TableHead><TableHead>Chat</TableHead><TableHead>Turi</TableHead><TableHead>Holat</TableHead><TableHead>Matn</TableHead></TableRow></TableHeader>
                <TableBody>
                  {outbox.map((m) => (
                    <TableRow key={m.id}>
                      <TableCell className="text-xs whitespace-nowrap">{fmtDateTime(m.created_at)}</TableCell>
                      <TableCell className="text-sm">{m.chat}</TableCell>
                      <TableCell className="text-xs">{m.type}</TableCell>
                      <TableCell><StatusBadge size="sm" status={m.status === 'sent' ? 'ok' : m.status === 'pending' ? 'connecting' : m.status === 'failed' ? 'error' : 'disabled'} label={{ sent: 'Yuborildi', pending: 'Kutmoqda', failed: 'Xato', cancelled: 'Bekor' }[m.status] ?? m.status} /></TableCell>
                      <TableCell className="max-w-96 truncate text-xs text-muted-foreground" title={m.error ?? undefined}>
                        {m.text.replace(/<[^>]+>/g, '')}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </div>
    </PageBody>
  )
}
