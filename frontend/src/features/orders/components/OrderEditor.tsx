import { useEffect, useMemo, useState } from "react"
import { listUnits } from "../../../api/resources"
import type { Unit } from "../../../api/types"
import { Field } from "../../../components/ui"
import type { DiscountType, OrderBody, OrderCatalogHit } from "../api"
import { discountError, formatPkr, formatQty, orderAmounts, priceError, quantityError, todayIso } from "../logic"
import { OrderProductSearch } from "./OrderProductSearch"

export type EditorLine = {
  key: string
  productId: string
  name: string
  sku: string
  unitId: string
  quantity: string
  unitPrice: string
  discountType: DiscountType
  discountValue: string
}

export function OrderEditor({
  initialLines = [],
  initialDate,
  initialNotes = "",
  initialDiscountType = "AMOUNT",
  initialDiscountValue = "0",
  onSubmit,
  onCancel,
}: {
  initialLines?: EditorLine[]
  initialDate?: string
  initialNotes?: string
  initialDiscountType?: DiscountType
  initialDiscountValue?: string
  onSubmit: (body: OrderBody, confirm: boolean) => Promise<void>
  onCancel: () => void
}) {
  const [lines, setLines] = useState<EditorLine[]>(initialLines)
  const [units, setUnits] = useState<Unit[]>([])
  const [date, setDate] = useState(initialDate ?? todayIso())
  const [notes, setNotes] = useState(initialNotes)
  const [discountType, setDiscountType] = useState<DiscountType>(initialDiscountType)
  const [discountValue, setDiscountValue] = useState(initialDiscountValue)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    listUnits(false)
      .then((page) => setUnits(page.items))
      .catch((reason: Error) => setError(reason.message))
  }, [])

  const summary = useMemo(
    () =>
      orderAmounts(
        lines.map((line) => ({
          quantity: Number(line.quantity) || 0,
          unitPrice: Number(line.unitPrice) || 0,
          discountType: line.discountType,
          discountValue: Number(line.discountValue) || 0,
        })),
        discountType,
        Number(discountValue) || 0,
      ),
    [lines, discountType, discountValue],
  )

  function addHit(hit: OrderCatalogHit) {
    setError(null)
    setLines((current) => [
      ...current,
      {
        key: `${hit.product_id}-${current.length}`,
        productId: hit.product_id,
        name: hit.name,
        sku: hit.sku,
        unitId: hit.unit_id,
        quantity: "1",
        unitPrice: hit.selling_price,
        discountType: "AMOUNT",
        discountValue: "0",
      },
    ])
  }

  function validate(): string | null {
    if (lines.length === 0) return "Add at least one product"
    for (const line of lines) {
      const quantity = quantityError(line.quantity)
      if (quantity) return `${line.name}: ${quantity}`
      const price = priceError(line.unitPrice)
      if (price) return `${line.name}: ${price}`
      const subtotal = (Number(line.quantity) || 0) * (Number(line.unitPrice) || 0)
      const discount = discountError(subtotal, line.discountType, line.discountValue)
      if (discount) return `${line.name}: ${discount}`
    }
    const net = summary.subtotal - summary.itemDiscount
    const orderDiscount = discountError(net, discountType, discountValue)
    if (orderDiscount) return `Order discount: ${orderDiscount}`
    return null
  }

  async function submit(confirm: boolean) {
    const problem = validate()
    if (problem) {
      setError(problem)
      return
    }
    setSaving(true)
    setError(null)
    try {
      await onSubmit(
        {
          order_date: date,
          notes: notes || null,
          discount_type: discountType,
          discount_value: discountValue || "0",
          items: lines.map((line) => ({
            product_id: line.productId,
            unit_id: line.unitId,
            quantity: line.quantity,
            unit_price: line.unitPrice,
            discount_type: line.discountType,
            discount_value: line.discountValue || "0",
          })),
        },
        confirm,
      )
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save the order")
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
      <div className="mb-4 grid gap-3 rounded-lg border border-line bg-white p-4 md:grid-cols-2">
        <Field label="Date">
          <input className="field" type="date" value={date} onChange={(event) => setDate(event.target.value)} />
        </Field>
        <Field label="Order discount">
          <div className="flex gap-2">
            <select className="field" value={discountType} onChange={(event) => setDiscountType(event.target.value as DiscountType)}>
              <option value="AMOUNT">Amount</option>
              <option value="PERCENT">Percent</option>
            </select>
            <input className="field" inputMode="decimal" value={discountValue} onChange={(event) => setDiscountValue(event.target.value)} />
          </div>
        </Field>
      </div>
      <div className="mb-4 rounded-lg border border-line bg-white p-4">
        <OrderProductSearch onSelect={addHit} />
      </div>
      <div className="overflow-x-auto rounded-lg border border-line bg-white">
        <table className="w-full min-w-[860px] text-left text-sm">
          <thead className="bg-stone-100 text-xs uppercase tracking-wide text-stone-500">
            <tr>
              <th className="px-4 py-3">Product</th>
              <th className="px-4 py-3">Quantity</th>
              <th className="px-4 py-3">Unit</th>
              <th className="px-4 py-3">Price</th>
              <th className="px-4 py-3">Discount</th>
              <th className="px-4 py-3">Total</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {lines.length === 0 ? (
              <tr>
                <td className="px-4 py-6 text-stone-500" colSpan={7}>
                  Search for a product to add it.
                </td>
              </tr>
            ) : (
              lines.map((line, index) => {
                const amounts = summary.lines[index]
                return (
                  <tr key={line.key} className="border-t border-line">
                    <td className="px-4 py-3">
                      <div className="font-medium">{line.name}</div>
                      <div className="text-xs text-stone-500">{line.sku}</div>
                    </td>
                    <td className="px-4 py-3">
                      <input
                        className="field w-24"
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
                        onChange={(event) =>
                          setLines((current) => current.map((item) => (item.key === line.key ? { ...item, unitId: event.target.value } : item)))
                        }
                      >
                        {units.some((unit) => unit.id === line.unitId) ? null : <option value={line.unitId}>{line.unitId}</option>}
                        {units.map((unit) => (
                          <option key={unit.id} value={unit.id}>
                            {unit.symbol}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-3">
                      <input
                        className="field w-28"
                        inputMode="decimal"
                        value={line.unitPrice}
                        onChange={(event) =>
                          setLines((current) => current.map((item) => (item.key === line.key ? { ...item, unitPrice: event.target.value } : item)))
                        }
                      />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <select
                          className="field"
                          value={line.discountType}
                          onChange={(event) =>
                            setLines((current) =>
                              current.map((item) =>
                                item.key === line.key ? { ...item, discountType: event.target.value as DiscountType } : item,
                              ),
                            )
                          }
                        >
                          <option value="AMOUNT">Rs</option>
                          <option value="PERCENT">%</option>
                        </select>
                        <input
                          className="field w-20"
                          inputMode="decimal"
                          value={line.discountValue}
                          onChange={(event) =>
                            setLines((current) =>
                              current.map((item) => (item.key === line.key ? { ...item, discountValue: event.target.value } : item))
                            )
                          }
                        />
                      </div>
                    </td>
                    <td className="px-4 py-3">{formatPkr(amounts?.total ?? 0)}</td>
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
      <div className="mt-4 grid gap-2 rounded-lg border border-line bg-white p-4 text-sm md:grid-cols-2">
        <p>Items: {lines.length}</p>
        <p>Quantity: {formatQty(summary.quantity)}</p>
        <p>Subtotal: {formatPkr(summary.subtotal)}</p>
        <p>Item discounts: {formatPkr(summary.itemDiscount)}</p>
        <p>Order discount: {formatPkr(summary.orderDiscount)}</p>
        <p className="font-semibold text-ink">Grand total: {formatPkr(summary.grandTotal)}</p>
      </div>
      <Field label="Notes">
        <textarea className="field mt-3" rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} />
      </Field>
      <div className="mt-4 flex flex-wrap gap-2">
        <button className="btn" type="submit" disabled={saving}>
          {saving ? "Saving…" : "Confirm order"}
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
