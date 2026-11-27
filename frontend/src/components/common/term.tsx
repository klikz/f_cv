import { CircleHelp } from 'lucide-react'
import type { ReactNode } from 'react'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { glossary, type GlossaryId } from '@/lib/glossary'
import { cn } from '@/lib/utils'

/** (?) izoh belgisi — atamalar lug'atidan. */
export function HintIcon({ id, className }: { id: GlossaryId; className?: string }) {
  const g = glossary[id]
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          className={cn(
            'inline-flex size-4 items-center justify-center rounded-full text-muted-foreground hover:text-foreground',
            className,
          )}
          aria-label={`${g.term}: izoh`}
        >
          <CircleHelp className="size-3.5" />
        </button>
      </TooltipTrigger>
      <TooltipContent className="max-w-72 text-xs leading-relaxed">
        <div className="mb-0.5 font-semibold">{g.term}</div>
        {g.hint}
      </TooltipContent>
    </Tooltip>
  )
}

/** Atama matni + (?) izoh. Matn lug'atdan olinadi — butun tizimda bir xil. */
export function Term({ id, children, className }: { id: GlossaryId; children?: ReactNode; className?: string }) {
  return (
    <span className={cn('inline-flex items-center gap-1', className)}>
      {children ?? glossary[id].term}
      <HintIcon id={id} />
    </span>
  )
}
