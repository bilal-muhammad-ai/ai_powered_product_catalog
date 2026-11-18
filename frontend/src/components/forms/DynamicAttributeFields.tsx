import type { Attribute } from "../../api/types"
import { AttributeValueInput } from "./AttributeValueInput"

type Props = {
  attributes: Attribute[]
  values: Record<string, unknown>
  onChange: (attributeId: string, value: unknown) => void
}

export function DynamicAttributeFields({ attributes, values, onChange }: Props) {
  if (attributes.length === 0) {
    return <p className="text-sm text-stone-500">This category has no extra fields.</p>
  }
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {attributes.map((attribute) => (
        <div key={attribute.id}>
          {attribute.data_type === "boolean" ? (
            <AttributeValueInput
              attribute={attribute}
              value={values[attribute.id]}
              onChange={(value) => onChange(attribute.id, value)}
            />
          ) : (
            <label className="block">
              <span className="label">
                {attribute.name}
                {attribute.is_required ? " *" : ""}
              </span>
              <AttributeValueInput
                attribute={attribute}
                value={values[attribute.id]}
                onChange={(value) => onChange(attribute.id, value)}
              />
            </label>
          )}
          {attribute.help_text ? <p className="mt-1 text-xs text-stone-500">{attribute.help_text}</p> : null}
        </div>
      ))}
    </div>
  )
}
