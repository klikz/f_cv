const TZ = 'Asia/Tashkent'

/** 3725 → "1:02:05" */
export function fmtClock(sec: number | null | undefined) {
  if (sec == null || !Number.isFinite(sec)) return '—'
  const s = Math.max(0, Math.round(sec))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const ss = s % 60
  return h ? `${h}:${String(m).padStart(2, '0')}:${String(ss).padStart(2, '0')}` : `${m}:${String(ss).padStart(2, '0')}`
}

/** 3725 → "1 soat 2 daq" */
export function fmtDuration(sec: number | null | undefined) {
  if (sec == null || !Number.isFinite(sec)) return '—'
  const s = Math.max(0, Math.round(sec))
  if (s < 60) return `${s} s`
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  if (!h) return `${m} daq`
  return m ? `${h} soat ${m} daq` : `${h} soat`
}

export function fmtSec(sec: number | null | undefined, digits = 1) {
  if (sec == null || !Number.isFinite(sec)) return '—'
  return `${sec.toFixed(digits)} s`
}

export function fmtPct(v: number | null | undefined, digits = 0) {
  if (v == null || !Number.isFinite(v)) return '—'
  return `${v.toFixed(digits)}%`
}

export function fmtNum(v: number | null | undefined) {
  if (v == null) return '—'
  return new Intl.NumberFormat('uz-UZ').format(v)
}

const dtf = new Intl.DateTimeFormat('uz-UZ', { timeZone: TZ, dateStyle: 'short', timeStyle: 'medium', hour12: false })
const tf = new Intl.DateTimeFormat('uz-UZ', { timeZone: TZ, hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
const df = new Intl.DateTimeFormat('uz-UZ', { timeZone: TZ, day: '2-digit', month: '2-digit', year: 'numeric' })

export function fmtDateTime(v: string | number | Date | null | undefined) {
  if (v == null) return '—'
  return dtf.format(typeof v === 'number' && v < 1e12 ? new Date(v * 1000) : new Date(v))
}
export function fmtTime(v: string | number | Date | null | undefined) {
  if (v == null) return '—'
  return tf.format(typeof v === 'number' && v < 1e12 ? new Date(v * 1000) : new Date(v))
}
export function fmtDate(v: string | number | Date | null | undefined) {
  if (v == null) return '—'
  return df.format(typeof v === 'number' && v < 1e12 ? new Date(v * 1000) : new Date(v))
}

/** Toshkent vaqti bo'yicha bugungi sana: "2026-11-26" */
export function todayISO() {
  const p = new Intl.DateTimeFormat('en-CA', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
  return p
}

export function resolution(w?: number | null, h?: number | null) {
  return w && h ? `${w}×${h}` : '—'
}
