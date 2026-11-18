import type { Attribute } from "../../api/types"

type Props = {
  attribute: Attribute
  value: unknown
  onChange: (value: unknown) => void
}

export function AttributeValueInput({ attribute, value, onChange }: Props) {
  const activeOptions = attribute.options.filter((option) => option.is_active)
  if (attribute.data_type === "boolean") {
    return (
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(event) => onChange(event.target.checked)}
        />
        {attribute.name}
      </label>
    )
  }
  if (attribute.data_type === "single_select") {
    return (
      <select className="field" value={typeof value === "string" ? value : ""} onChange={(event) => onChange(event.target.value)}>
        <option value="">Select</option>
        {activeOptions.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
    )
  }
  if (attribute.data_type === "multi_select") {
    const selected = Array.isArray(value) ? value.map(String) : []
    return (
      <div className="flex flex-col gap-1">
        {activeOptions.map((option) => (
          <label key={option.id} className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={selected.includes(option.id)}
              onChange={(event) => {
                const next = event.target.checked
                  ? [...selected, option.id]
                  : selected.filter((id) => id !== option.id)
                onChange(next)
              }}
            />
            {option.label}
          </label>
        ))}
      </div>
    )
  }
  if (attribute.data_type === "number") {
    return (
      <input
        className="field"
        type="number"
        step="any"
        value={value === undefined || value === null ? "" : String(value)}
        onChange={(event) => onChange(event.target.value)}
      />
    )
  }
  if (attribute.data_type === "date") {
    return (
      <input
        className="field"
        type="date"
        value={typeof value === "string" ? value.slice(0, 10) : ""}
        onChange={(event) => onChange(event.target.value)}
      />
    )
  }
  return (
    <input
      className="field"
      value={typeof value === "string" ? value : ""}
      onChange={(event) => onChange(event.target.value)}
    />
  )
}
