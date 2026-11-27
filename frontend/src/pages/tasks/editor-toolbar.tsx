import { Redo2, Undo2, ZoomIn } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Kbd } from '@/components/ui/kbd'

export function EditorToolbar({ canUndo, canRedo, onUndo, onRedo, hint }: { canUndo: boolean; canRedo: boolean; onUndo: () => void; onRedo: () => void; hint?: string }) {
  return (
    <div className="flex items-center gap-1 border-t px-2 py-1.5 text-xs text-muted-foreground">
      <Button variant="ghost" size="icon-sm" onClick={onUndo} disabled={!canUndo} aria-label="Bekor qilish (Ctrl+Z)" title="Bekor qilish (Ctrl+Z)">
        <Undo2 />
      </Button>
      <Button variant="ghost" size="icon-sm" onClick={onRedo} disabled={!canRedo} aria-label="Qaytarish (Ctrl+Y)" title="Qaytarish (Ctrl+Y)">
        <Redo2 />
      </Button>
      {hint ? (
        <span className="ml-2 truncate font-medium text-foreground">{hint}</span>
      ) : (
        <span className="ml-2 hidden items-center gap-1.5 truncate xl:flex">
          <ZoomIn className="size-3.5" /> zoom: g'ildirak · surish: <Kbd>Space</Kbd>+sudrash · <Kbd>0</Kbd> tiklash · nuqtani o'chirish: <Kbd>Delete</Kbd> / o'ng tugma ·
          qirraga 2× bosish — nuqta qo'shish
        </span>
      )}
    </div>
  )
}
