import { Search } from "lucide-react"
import { Field } from "./Field"

export function SearchInput({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
}) {
  return (
    <Field label={label}>
      <span className="relative block">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" aria-hidden="true" />
        <input className="field pl-9" value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
      </span>
    </Field>
  )
}
