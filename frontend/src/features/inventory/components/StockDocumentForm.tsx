import { useEffect, useMemo, useState } from "react"
import type { MovementBody } from "../../../api/inventory"
import type { CatalogHit } from "../../../api/inventory"
import { listUnits } from "../../../api/resources"
import type { Unit } from "../../../api/types"
import { Field } from "../../../components/ui"
import { costError, formatPkr, formatQty, issueQuantityError, lineTotal, quantityError, todayIso } from "../logic"
import { ProductSearch } from "./ProductSearch"

export type DocumentMode = "opening" | "receipt" | "issue"

export type DocumentLine = {
  key: string
  productId: string
  name: string
  sku: string
  available: number
  sellingUnitId: string
  unitId: string
  unitSymbol: string
  quantity: string
  unitCost: string
}

const titles: Record<DocumentMode, string> = {
  opening: "Opening stock",
  receipt: "Stock receipt",
  issue: "Stock issue",
}

export function StockDocumentForm({
  mode,
  initialLines = [],
  onSubmit,
  onCancel,
}: {
  mode: DocumentMode
  initialLines?: DocumentLine[]
  onSubmit: (body: MovementBody) => Promise<void>
  onCancel: () => void
}) {
  const [lines, setLines] = useState<DocumentLine[]>(initialLines)
  const [units, setUnits] = useState<Unit[]>([])
  const [date, setDate] = useState(todayIso())
  const [reference, setReference] = useState("")
  const [reason, setReason] = useState(mode === "issue" ? "Internal usage" : "")
  const [notes, setNotes] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    listUnits(false)
      .then((page) => setUnits(page.items))
      .catch((reason: Error) => setError(reason.message))
  }, [])

  const totals = useMemo(() => {
    const quantity = lines.reduce((sum, line) => sum + (Number(line.quantity) || 0), 0)
    const value = lines.reduce((sum, line) => sum + lineTotal(Number(line.quantity) || 0, Number(line.unitCost) || 0), 0)
    return { quantity, value }
  }, [lines])

  function addHit(hit: CatalogHit) {
    if (lines.some((line) => line.productId === hit.product_id)) {
      setError("That product is already on this document")
      return
    }
    if (mode === "opening" && Number(hit.quantity_on_hand) > 0) {
      setError(`${hit.name} already has stock. Use a receipt for more.`)
      return
    }
    setError(null)
    setLines((current: DocumentLine[]) => [
      ...current,
      {
        key: hit.product_id,
        productId: hit.product_id,
        name: hit.name,
        sku: hit.sku,
        available: Number(hit.quantity_on_hand),
        sellingUnitId: hit.unit_id,
        unitId: hit.unit_id,
        unitSymbol: hit.unit_symbol,
        quantity: "",
        unitCost: mode === "issue" ? hit.average_cost : "",
      },
    ])
  }

  function validate(): string | null {
    if (lines.length === 0) return "Add at least one product"
    if (mode === "issue" && !reason.trim()) return "Choose a reason"
    for (const line of lines) {
      const quantity = mode === "issue" ? issueQuantityError(line.quantity, line.available, line.unitId === line.sellingUnitId) : quantityError(line.quantity)
      if (quantity) return `${line.name}: ${quantity}`
      const cost = costError(line.unitCost, mode !== "issue")
      if (cost) return `${line.name}: ${cost}`
    }
    return null
  }

  async function submit(post: boolean) {
    const message = validate()
    if (message) {
      setError(message)
      return
    }
    setSaving(true)
    setError(null)
    const body: MovementBody = {
      transaction_date: date,
      reference_number: reference || null,
      notes: notes || null,
      reason: reason || null,
      post,
      items: lines.map((line) => ({
        product_id: line.productId,
        unit_id: line.unitId,
        quantity: line.quantity,
        unit_cost: mode === "issue" ? undefined : line.unitCost,
      })),
    }
    try {
      await onSubmit(body)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save the transaction")
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
      <div className="mb-4 grid gap-3 rounded-lg border border-line bg-white p-4 md:grid-cols-3">
        <Field label="Date">
          <input className="field" type="date" value={date} onChange={(event) => setDate(event.target.value)} />
        </Field>
        <Field label="Reference number">
          <input className="field" value={reference} onChange={(event) => setReference(event.target.value)} />
        </Field>
        {mode === "issue" ? (
          <Field label="Reason">
            <select className="field" value={reason} onChange={(event) => setReason(event.target.value)}>
              <option>Internal usage</option>
              <option>Damaged</option>
              <option>Other</option>
            </select>
          </Field>
        ) : null}
      </div>
      <div className="mb-4 rounded-lg border border-line bg-white p-4">
        <ProductSearch onSelect={addHit} />
      </div>
      <div className="overflow-x-auto rounded-lg border border-line bg-white">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="bg-stone-100 text-xs uppercase tracking-wide text-stone-500">
            <tr>
              <th className="px-4 py-3">Product</th>
              {mode === "issue" ? <th className="px-4 py-3">Available</th> : null}
              <th className="px-4 py-3">Quantity</th>
              <th className="px-4 py-3">Unit</th>
              <th className="px-4 py-3">{mode === "issue" ? "Cost" : "Unit cost"}</th>
              {mode !== "issue" ? <th className="px-4 py-3">Total</th> : null}
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {lines.length === 0 ? (
              <tr>
                <td className="px-4 py-6 text-stone-500" colSpan={6}>
                  Search for a product to add it.
                </td>
              </tr>
            ) : (
              lines.map((line) => (
                <tr key={line.key} className="border-t border-line">
                  <td className="px-4 py-3">
                    <div className="font-medium">{line.name}</div>
                    <div className="text-xs text-stone-500">{line.sku}</div>
                  </td>
                  {mode === "issue" ? (
                    <td className="px-4 py-3">
                      {formatQty(line.available)} {line.unitSymbol}
                    </td>
                  ) : null}
                  <td className="px-4 py-3">
                    <input
                      className="field w-28"
                      inputMode="decimal"
                      value={line.quantity}
                      onChange={(event) =>
                        setLines((current) => current.map((item) => (item.key === line.key ? { ...item, quantity: event.target.value } : item)))
                      }
                    />
                  </td>
                  <td className="px-4 py-3">
                    <select
                      className="field"
                      value={line.unitId}
                      onChange={(event) => {
                        const unit = units.find((item) => item.id === event.target.value)
                        setLines((current) =>
                          current.map((item) =>
                            item.key === line.key ? { ...item, unitId: event.target.value, unitSymbol: unit?.symbol ?? item.unitSymbol } : item,
                          ),
                        )
                      }}
                    >
                      {units.map((unit) => (
                        <option key={unit.id} value={unit.id}>
                          {unit.symbol}
                        </option>
                      ))}
                      {units.some((unit) => unit.id === line.unitId) ? null : <option value={line.unitId}>{line.unitSymbol}</option>}
                    </select>
                  </td>
                  <td className="px-4 py-3">
                    {mode === "issue" ? (
                      formatPkr(line.unitCost)
                    ) : (
                      <input
                        className="field w-28"
                        inputMode="decimal"
                        value={line.unitCost}
                        onChange={(event) =>
                          setLines((current) => current.map((item) => (item.key === line.key ? { ...item, unitCost: event.target.value } : item)))
                        }
                      />
                    )}
                  </td>
                  {mode !== "issue" ? <td className="px-4 py-3">{formatPkr(lineTotal(Number(line.quantity) || 0, Number(line.unitCost) || 0))}</td> : null}
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      className="btn-danger"
                      onClick={() => setLines((current) => current.filter((item) => item.key !== line.key))}
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <p className="text-sm text-stone-600">Items: {lines.length}</p>
        <p className="text-sm text-stone-600">Quantity: {formatQty(totals.quantity)}</p>
        {mode !== "issue" ? <p className="text-sm font-semibold text-ink">Value: {formatPkr(totals.value)}</p> : null}
      </div>
      <Field label="Notes">
        <textarea className="field mt-3" rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} />
      </Field>
      <div className="mt-4 flex flex-wrap gap-2">
        <button className="btn" type="submit" disabled={saving}>
          {saving ? "Saving…" : `Post ${titles[mode].toLowerCase()}`}
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
