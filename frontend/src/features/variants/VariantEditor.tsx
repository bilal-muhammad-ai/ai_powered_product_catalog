import type { Attribute, Unit } from "../../api/types"
import { DynamicAttributeFields } from "../../components/forms/DynamicAttributeFields"
import { Field } from "../../components/ui"
import { variantSignature } from "../../lib/variantKey"

export type VariantDraft = {
  sku: string
  barcode: string
  name: string
  selling_unit_id: string
  net_quantity: string
  net_quantity_unit_id: string
  cost_price: string
  selling_price: string
  currency_code: string
  is_active: boolean
  values: Record<string, unknown>
}

type Props = {
  variants: VariantDraft[]
  units: Unit[]
  attributes: Attribute[]
  onChange: (variants: VariantDraft[]) => void
}

export function emptyVariant(sellingUnitId = ""): VariantDraft {
  return {
    sku: "",
    barcode: "",
    name: "",
    selling_unit_id: sellingUnitId,
    net_quantity: "",
    net_quantity_unit_id: "",
    cost_price: "",
    selling_price: "",
    currency_code: "PKR",
    is_active: true,
    values: {},
  }
}

export function VariantEditor({ variants, units, attributes, onChange }: Props) {
  const activeUnits = units.filter((unit) => unit.is_active)
  const axisIds = attributes.map((attribute) => attribute.id)
  const signatures = variants.map((variant) => variantSignature(axisIds, variant.values))

  function update(index: number, patch: Partial<VariantDraft>) {
    onChange(variants.map((variant, itemIndex) => (itemIndex === index ? { ...variant, ...patch } : variant)))
  }

  return (
    <div className="space-y-4">
      {variants.map((variant, index) => {
        const duplicate = signatures.filter((signature) => signature === signatures[index]).length > 1
        return (
          <section key={index} className="rounded-lg border border-line bg-white p-4">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-semibold">Variant {index + 1}</h3>
              {variants.length > 1 ? (
                <button
                  type="button"
                  className="btn-danger"
                  onClick={() => onChange(variants.filter((_, itemIndex) => itemIndex !== index))}
                >
                  Remove
                </button>
              ) : null}
            </div>
            <div className="grid gap-4 md:grid-cols-3">
              <Field label="SKU *">
                <input className="field" value={variant.sku} onChange={(event) => update(index, { sku: event.target.value })} />
              </Field>
              <Field label="Barcode">
                <input className="field" value={variant.barcode} onChange={(event) => update(index, { barcode: event.target.value })} />
              </Field>
              <Field label="Variant name">
                <input className="field" value={variant.name} onChange={(event) => update(index, { name: event.target.value })} />
              </Field>
              <Field label="Selling unit *">
                <select className="field" value={variant.selling_unit_id} onChange={(event) => update(index, { selling_unit_id: event.target.value })}>
                  <option value="">Select</option>
                  {activeUnits.map((unit) => (
                    <option key={unit.id} value={unit.id}>
                      {unit.name} ({unit.symbol})
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Net quantity">
                <input className="field" value={variant.net_quantity} onChange={(event) => update(index, { net_quantity: event.target.value })} />
              </Field>
              <Field label="Quantity unit">
                <select
                  className="field"
                  value={variant.net_quantity_unit_id}
                  onChange={(event) => update(index, { net_quantity_unit_id: event.target.value })}
                >
                  <option value="">None</option>
                  {activeUnits.map((unit) => (
                    <option key={unit.id} value={unit.id}>
                      {unit.symbol}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Cost price *">
                <input className="field" value={variant.cost_price} onChange={(event) => update(index, { cost_price: event.target.value })} />
              </Field>
              <Field label="Selling price *">
                <input className="field" value={variant.selling_price} onChange={(event) => update(index, { selling_price: event.target.value })} />
              </Field>
              <Field label="Currency">
                <input
                  className="field"
                  maxLength={3}
                  value={variant.currency_code}
                  onChange={(event) => update(index, { currency_code: event.target.value.toUpperCase() })}
                />
              </Field>
            </div>
            <label className="mt-3 flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={variant.is_active}
                onChange={(event) => update(index, { is_active: event.target.checked })}
              />
              Active SKU
            </label>
            {attributes.length > 0 ? (
              <div className="mt-4">
                <DynamicAttributeFields
                  attributes={attributes}
                  values={variant.values}
                  onChange={(attributeId, value) => update(index, { values: { ...variant.values, [attributeId]: value } })}
                />
              </div>
            ) : null}
            {duplicate && attributes.length > 0 ? (
              <p className="mt-3 text-sm text-red-700">This variant repeats another combination.</p>
            ) : null}
          </section>
        )
      })}
      <button type="button" className="btn-ghost" onClick={() => onChange([...variants, emptyVariant(variants[0]?.selling_unit_id ?? "")])}>
        Add variant
      </button>
    </div>
  )
}
