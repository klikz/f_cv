import type { FrameHeader } from '@/lib/types'

/** Ikkilik xabar: [4 bayt sarlavha uzunligi][JSON][JPEG] */
export function parseFrame(buf: ArrayBuffer): { header: FrameHeader; jpeg: Blob } | null {
  if (buf.byteLength < 4) return null
  const dv = new DataView(buf)
  const hl = dv.getUint32(0)
  if (4 + hl > buf.byteLength) return null
  const header = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 4, hl))) as FrameHeader
  const jpeg = new Blob([new Uint8Array(buf, 4 + hl)], { type: 'image/jpeg' })
  return { header, jpeg }
}

export type FrameData = { header: FrameHeader; bitmap: ImageBitmap; receivedAt: number }
type Listener = (f: FrameData) => void

/**
 * Kadrlar markazi: WS dan kelgan kadrlarni dekod qilib, kamera bo'yicha tinglovchilarga beradi.
 * Bir kamera uchun bir vaqtda faqat bitta dekod — eski kadrlar tashlab yuboriladi.
 */
export class FeedHub {
  private listeners = new Map<number, Set<Listener>>()
  private latest = new Map<number, FrameData>()
  private decoding = new Set<number>()
  private pending = new Map<number, ArrayBuffer>()

  push(buf: ArrayBuffer) {
    const dv = new DataView(buf)
    if (buf.byteLength < 4) return
    // kamera id ni tez olish uchun sarlavhani parse qilamiz
    const parsed = parseFrame(buf)
    if (!parsed) return
    const cam = parsed.header.cam
    if (this.decoding.has(cam)) {
      this.pending.set(cam, buf)
      return
    }
    void dv
    void this.decode(cam, parsed)
  }

  private async decode(cam: number, parsed: { header: FrameHeader; jpeg: Blob }) {
    this.decoding.add(cam)
    try {
      const bitmap = await createImageBitmap(parsed.jpeg)
      const prev = this.latest.get(cam)
      const f = { header: parsed.header, bitmap, receivedAt: performance.now() }
      this.latest.set(cam, f)
      this.listeners.get(cam)?.forEach((l) => l(f))
      prev?.bitmap.close()
    } catch {
      /* buzilgan kadr — e'tiborsiz */
    } finally {
      this.decoding.delete(cam)
      const next = this.pending.get(cam)
      if (next) {
        this.pending.delete(cam)
        const p = parseFrame(next)
        if (p) void this.decode(cam, p)
      }
    }
  }

  subscribe(cam: number, l: Listener) {
    let set = this.listeners.get(cam)
    if (!set) this.listeners.set(cam, (set = new Set()))
    set.add(l)
    const last = this.latest.get(cam)
    if (last) l(last)
    return () => {
      set!.delete(l)
    }
  }

  getLatest(cam: number) {
    return this.latest.get(cam)
  }

  clear() {
    this.latest.forEach((f) => f.bitmap.close())
    this.latest.clear()
  }
}
