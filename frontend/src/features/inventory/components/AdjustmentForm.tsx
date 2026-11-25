import { useMemo, useState } from "react"
import type { CatalogHit, MovementBody } from "../../../api/inventory"
import { Field } from "../../../components/ui"
import { adjustmentDelta, formatQty, todayIso } from "../logic"
import { ProductSearch } from "./ProductSearch"

type Line = {
  key: string
  productId: string
  name: string
  sku: string
  systemStock: number
  unitId: string
  unitSymbol: string
  physical: string
}

export function AdjustmentForm({
  initialLines = [],
  onSubmit,
  onCancel,
}: {
  initialLines?: Line[]
  onSubmit: (body: MovementBody) => Promise<void>
  onCancel: () => void
}) {
  const [lines, setLines] = useState<Line[]>(initialLines)
  const [date, setDate] = useState(todayIso())
  const [reason, setReason] = useState("Physical count")
  const [notes, setNotes] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const summary = useMemo(
    () =>
      lines.map((line) => {
        const physical = Number(line.physical)
        const delta = Number.isFinite(physical) ? adjustmentDelta(line.systemStock, physical) : null
        return { key: line.key, delta, resulting: Number.isFinite(physical) ? physical : null }
      }),
    [lines],
  )

  function addHit(hit: CatalogHit) {
    if (lines.some((line) => line.productId === hit.product_id)) {
      setError("That product is already on this adjustment")
      return
    }
    setError(null)
    setLines((current) => [
      ...current,
      {
        key: hit.product_id,
        productId: hit.product_id,
        name: hit.name,
        sku: hit.sku,
        systemStock: Number(hit.quantity_on_hand),
        unitId: hit.unit_id,
        unitSymbol: hit.unit_symbol,
        physical: "",
      },
    ])
  }

  async function submit(post: boolean) {
    if (!reason.trim()) {
      setError("An adjustment reason is required")
      return
    }
    if (lines.length === 0) {
      setError("Add at least one product")
      return
    }
    for (const line of lines) {
      if (!line.physical.trim() || !Number.isFinite(Number(line.physical)) || Number(line.physical) < 0) {
        setError(`${line.name}: enter the physical stock`)
        return
      }
      const found = summary.find((item) => item.key === line.key)
      if (found?.delta === 0) {
        setError(`${line.name}: physical stock matches the system`)
        return
      }
    }
    setSaving(true)
    setError(null)
    try {
      await onSubmit({
        transaction_date: date,
        reason,
        notes: notes || null,
        post,
        items: lines.map((line) => ({
          product_id: line.productId,
          unit_id: line.unitId,
          physical_quantity: line.physical,
        })),
      })
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save the adjustment")
    } finally {
      setSaving(false)
    }
  }

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        void submit(true)
      }}
    >
      {error ? <p className="mb-4 whitespace-pre-line rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p> : null}
      <div className="mb-4 grid gap-3 rounded-xl border border-line bg-white p-4 shadow-card md:grid-cols-2">
        <Field label="Date">
          <input className="field" type="date" value={date} onChange={(event) => setDate(event.target.value)} />
        </Field>
        <Field label="Reason">
          <input className="field" value={reason} onChange={(event) => setReason(event.target.value)} />
        </Field>
      </div>
      <div className="mb-4 rounded-xl border border-line bg-white p-4 shadow-card">
        <ProductSearch onSelect={addHit} />
      </div>
      <div className="overflow-x-auto rounded-xl border border-line bg-white shadow-card">
        <table className="w-full min-w-[860px] text-left text-sm">
          <thead className="bg-stone-50 text-xs font-semibold uppercase tracking-wide text-stone-500">
            <tr>
              <th className="px-4 py-3">Product</th>
              <th className="px-4 py-3">System stock</th>
              <th className="px-4 py-3">Physical stock</th>
              <th className="px-4 py-3">Adjustment</th>
              <th className="px-4 py-3">Resulting stock</th>
              <th className="px-4 py-3">Unit</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {lines.length === 0 ? (
              <tr>
                <td className="px-4 py-6 text-stone-500" colSpan={7}>
                  Search for a product, then enter the counted quantity.
                </td>
              </tr>
            ) : (
              lines.map((line) => {
                const math = summary.find((item) => item.key === line.key)
                const delta = math?.delta
                return (
                  <tr key={line.key} className="border-t border-line">
                    <td className="px-4 py-3">
                      <div className="font-medium">{line.name}</div>
                      <div className="text-xs text-stone-500">{line.sku}</div>
                    </td>
                    <td className="px-4 py-3">{formatQty(line.systemStock)}</td>
                    <td className="px-4 py-3">
                      <input
                        className="field w-28"
                        inputMode="decimal"
                        value={line.physical}
                        onChange={(event) =>
                          setLines((current) => current.map((item) => (item.key === line.key ? { ...item, physical: event.target.value } : item)))
                        }
                      />
                    </td>
                    <td className={`px-4 py-3 font-semibold ${delta != null && delta < 0 ? "text-red-700" : "text-emerald-800"}`}>
                      {delta == null ? "—" : `${delta > 0 ? "+" : ""}${formatQty(delta)}`}
                    </td>
                    <td className="px-4 py-3">{math?.resulting === null || math?.resulting === undefined ? "—" : formatQty(math.resulting)}</td>
                    <td className="px-4 py-3">{line.unitSymbol}</td>
                    <td className="px-4 py-3 text-right">
                      <button type="button" className="btn-danger" onClick={() => setLines((current) => current.filter((item) => item.key !== line.key))}>
                        Remove
                      </button>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
      <Field label="Notes">
        <textarea className="field mt-3" rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} />
      </Field>
      <div className="mt-4 flex flex-wrap gap-2">
        <button className="btn" type="submit" disabled={saving}>
          {saving ? "Saving…" : "Post adjustment"}
        </button>
        <button className="btn-ghost" type="button" disabled={saving} onClick={() => void submit(false)}>
          Save draft
        </button>
        <button className="btn-ghost" type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  )
}
