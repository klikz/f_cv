import type { FrameMeta, Point } from '@/lib/types'

export type Rect = { x: number; y: number; w: number; h: number }

type Palette = { roi: string; line: string; box: string; labelBg: string; success: string; danger: string; warning: string; neutral: string }

let palette: Palette | null = null
let paletteTheme = ''

/** AI qatlami ranglari — dizayn tokenlaridan (mavzu almashganda qayta o'qiladi). */
export function overlayPalette(): Palette {
  const theme = document.documentElement.dataset.theme ?? ''
  if (palette && paletteTheme === theme) return palette
  const cs = getComputedStyle(document.documentElement)
  const v = (n: string) => cs.getPropertyValue(n).trim()
  palette = {
    roi: v('--overlay-roi'),
    line: v('--overlay-line'),
    box: v('--overlay-box'),
    labelBg: v('--overlay-label-bg'),
    success: v('--success'),
    danger: v('--danger'),
    warning: v('--warning'),
    neutral: v('--neutral'),
  }
  paletteTheme = theme
  return palette
}

/** Chiziq qalinligi va shrift katak o'lchamiga moslashadi (kichik kataklarda yupqaroq). */
export function overlayScale(r: Rect) {
  const s = Math.max(0.55, Math.min(1.4, r.w / 960))
  return { line: Math.max(1, 2 * s), font: Math.round(Math.max(10, 13 * s)), compact: r.w < 420 }
}

const P = (r: Rect, p: Point) => [r.x + p[0] * r.w, r.y + p[1] * r.h] as const

export function drawPolygon(ctx: CanvasRenderingContext2D, r: Rect, pts: Point[], stroke: string, fillAlpha = 0.1, width = 2, dash: number[] = []) {
  if (pts.length < 2) return
  ctx.save()
  ctx.beginPath()
  pts.forEach((p, i) => {
    const [x, y] = P(r, p)
    if (i === 0) ctx.moveTo(x, y)
    else ctx.lineTo(x, y)
  })
  ctx.closePath()
  ctx.setLineDash(dash)
  ctx.lineWidth = width
  ctx.strokeStyle = stroke
  ctx.globalAlpha = fillAlpha
  ctx.fillStyle = stroke
  ctx.fill()
  ctx.globalAlpha = 1
  ctx.stroke()
  ctx.restore()
}

export function drawArrowLine(
  ctx: CanvasRenderingContext2D,
  r: Rect,
  a: Point,
  b: Point,
  direction: string,
  color: string,
  width: number,
  showLabels = true,
) {
  const [ax, ay] = P(r, a)
  const [bx, by] = P(r, b)
  ctx.save()
  ctx.strokeStyle = color
  ctx.fillStyle = color
  ctx.lineWidth = width * 1.5
  ctx.beginPath()
  ctx.moveTo(ax, ay)
  ctx.lineTo(bx, by)
  ctx.stroke()
  // uchlari
  for (const [x, y] of [[ax, ay], [bx, by]]) {
    ctx.beginPath()
    ctx.arc(x, y, width * 2.2, 0, Math.PI * 2)
    ctx.fill()
  }
  // yo'nalish strelkasi (chiziq normali bo'yicha). A→B: normal = (dy, -dx) — chapdan o'ngga o'tish
  const mx = (ax + bx) / 2
  const my = (ay + by) / 2
  const dx = bx - ax
  const dy = by - ay
  const len = Math.hypot(dx, dy) || 1
  const nx = -dy / len
  const ny = dx / len
  const L = Math.max(18, Math.min(60, len * 0.18))
  const arrows: number[] = direction === 'b_to_a' ? [-1] : direction === 'both' ? [1, -1] : [1]
  for (const sgn of arrows) {
    const tx = mx + nx * L * sgn
    const ty = my + ny * L * sgn
    ctx.beginPath()
    ctx.moveTo(mx, my)
    ctx.lineTo(tx, ty)
    ctx.stroke()
    const ang = Math.atan2(ty - my, tx - mx)
    const hs = Math.max(7, width * 4)
    ctx.beginPath()
    ctx.moveTo(tx, ty)
    ctx.lineTo(tx - hs * Math.cos(ang - 0.45), ty - hs * Math.sin(ang - 0.45))
    ctx.lineTo(tx - hs * Math.cos(ang + 0.45), ty - hs * Math.sin(ang + 0.45))
    ctx.closePath()
    ctx.fill()
  }
  if (showLabels) {
    label(ctx, 'A', ax + 6, ay - 6, color, Math.max(10, width * 6))
    label(ctx, 'B', bx + 6, by - 6, color, Math.max(10, width * 6))
  }
  ctx.restore()
}

export function label(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, color: string, size = 12, bg?: string) {
  ctx.save()
  ctx.font = `600 ${size}px "Inter Variable", sans-serif`
  const w = ctx.measureText(text).width
  const pad = Math.round(size * 0.35)
  ctx.fillStyle = bg ?? overlayPalette().labelBg
  ctx.beginPath()
  ctx.roundRect(x - pad, y - size - pad + 2, w + pad * 2, size + pad * 2 - 2, 3)
  ctx.fill()
  ctx.fillStyle = color
  ctx.textBaseline = 'alphabetic'
  ctx.fillText(text, x, y)
  ctx.restore()
}

/** Saqlangan geometriya va jonli metadata asosida AI qatlamini chizish. */
export function drawOverlay(ctx: CanvasRenderingContext2D, r: Rect, meta: FrameMeta | undefined, now = performance.now()) {
  if (!meta) return
  const pal = overlayPalette()
  const sc = overlayScale(r)
  const c = meta.counting
  if (c) {
    if (c.roi) drawPolygon(ctx, r, c.roi, pal.roi, 0.06, sc.line, [6, 4])
    if (c.line) {
      const flash = c.flash && Math.floor(now / 120) % 2 === 0
      drawArrowLine(ctx, r, c.line[0], c.line[1], c.direction, flash ? pal.success : pal.line, sc.line, !sc.compact)
    }
    for (const d of c.detections ?? []) {
      const [x1, y1, x2, y2] = d.bbox
      const color = d.counted ? pal.success : pal.warning
      ctx.save()
      ctx.strokeStyle = color
      ctx.lineWidth = sc.line
      ctx.strokeRect(r.x + x1 * r.w, r.y + y1 * r.h, (x2 - x1) * r.w, (y2 - y1) * r.h)
      ctx.restore()
      const txt = sc.compact ? d.label : `${d.label} ${Math.round(d.score * 100)}%${d.track_id != null ? ` #${d.track_id}` : ''}`
      label(ctx, txt, r.x + x1 * r.w + 3, r.y + y1 * r.h - 3, color, sc.font)
    }
  }
  const e = meta.equipment
  if (e) {
    const col = e.state === 'running' ? pal.success : e.state === 'stopped' ? pal.danger : pal.neutral
    for (const m of e.motion ?? []) drawPolygon(ctx, r, m, pal.warning, 0.35, 0)
    if (e.roi) drawPolygon(ctx, r, e.roi, col, 0.08, sc.line * 1.2)
    if (e.control_zone) drawPolygon(ctx, r, e.control_zone, pal.roi, 0.05, sc.line, [4, 4])
    for (const z of e.exclude_zones ?? []) drawPolygon(ctx, r, z, pal.neutral, 0.25, sc.line, [2, 3])
  }
}

/** Kadrni konteynerga sig'dirish (object-fit: contain). */
export function containRect(cw: number, ch: number, iw: number, ih: number): Rect {
  const s = Math.min(cw / iw, ch / ih)
  const w = iw * s
  const h = ih * s
  return { x: (cw - w) / 2, y: (ch - h) / 2, w, h }
}
