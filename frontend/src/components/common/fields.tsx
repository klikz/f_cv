import { ChevronDown } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'

export function NumberField({
  id,
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
  unit,
  hint,
  nullable,
}: {
  id: string
  label: ReactNode
  value: number | null
  onChange: (v: number | null) => void
  min?: number
  max?: number
  step?: number
  unit?: string
  hint?: ReactNode
  nullable?: boolean
}) {
  return (
    <div className="space-y-1">
      <Label htmlFor={id} className="text-sm">
        {label}
      </Label>
      <div className="flex items-center gap-2">
        <Input
          id={id}
          type="number"
          inputMode="decimal"
          className="num h-8"
          value={value ?? ''}
          min={min}
          max={max}
          step={step}
          placeholder={nullable ? 'avto' : undefined}
          onChange={(e) => {
            const raw = e.target.value
            if (raw === '' && nullable) return onChange(null)
            const v = Number(raw)
            if (Number.isFinite(v)) onChange(v)
          }}
        />
        {unit && <span className="shrink-0 text-xs text-muted-foreground">{unit}</span>}
      </div>
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  )
}

export function SelectField<T extends string>({
  id,
  label,
  value,
  onChange,
  options,
  hint,
}: {
  id: string
  label: ReactNode
  value: T
  onChange: (v: T) => void
  options: { value: T; label: string }[]
  hint?: ReactNode
}) {
  return (
    <div className="space-y-1">
      <Label htmlFor={id} className="text-sm">
        {label}
      </Label>
      <Select value={value} onValueChange={(v) => onChange(v as T)}>
        <SelectTrigger id={id} className="h-8 w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map((o) => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  )
}

/** "Qo'shimcha sozlamalar" — kamdan-kam ishlatiladigan parametrlar yig'iladi. */
export function Advanced({ children, title = "Qo'shimcha sozlamalar", defaultOpen = false }: { children: ReactNode; title?: string; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="rounded-lg border">
      <button type="button" className="flex w-full items-center justify-between px-3 py-2 text-sm font-medium" onClick={() => setOpen(!open)} aria-expanded={open}>
        {title}
        <ChevronDown className={cn('size-4 transition-transform', open && 'rotate-180')} />
      </button>
      {open && <div className="space-y-3 border-t p-3">{children}</div>}
    </div>
  )
}
