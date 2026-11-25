import { Trash2 } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { listUnits } from "../../../api/resources"
import type { Unit } from "../../../api/types"
import { Button, Card, Field } from "../../../components/ui"
import { lineKey } from "../ai-order"
import type { AiProductMatch, DiscountType, OrderBody, OrderCatalogHit } from "../api"
import { discountError, formatPkr, formatQty, orderAmounts, priceError, quantityError, todayIso } from "../logic"
import { AiOrderQuery } from "./AiOrderQuery"
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
  assist = false,
  onSubmit,
  onCancel,
}: {
  initialLines?: EditorLine[]
  initialDate?: string
  initialNotes?: string
  initialDiscountType?: DiscountType
  initialDiscountValue?: string
  assist?: boolean
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
  const [choicePending, setChoicePending] = useState(false)
  const [excluded, setExcluded] = useState<string[]>([])

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

  function upsertAiLine(index: number, match: AiProductMatch, price: string, quantity: string) {
    const key = lineKey(index)
    setError(null)
    setLines((current) => {
      const existing = current.find((line) => line.key === key)
      const next: EditorLine = {
        key,
        productId: match.product_id,
        name: match.name,
        sku: "",
        unitId: match.selling_unit_id,
        quantity: existing?.quantity ?? quantity,
        unitPrice: price,
        discountType: existing?.discountType ?? "AMOUNT",
        discountValue: existing?.discountValue ?? "0",
      }
      if (!existing) return [...current, next]
      return current.map((line) => (line.key === key ? next : line))
    })
  }

  function clearAiLines() {
    setLines((current) => current.filter((line) => !line.key.startsWith("ai-")))
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
    if (choicePending) {
      setError("Choose a product for each requested item")
      return
    }
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
      <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="min-w-0 space-y-5 xl:col-start-1 xl:row-start-1">
          {error ? <p className="whitespace-pre-line rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p> : null}
          <Card className="grid gap-4 p-4 md:grid-cols-2">
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
          </Card>
          {assist ? <AiOrderQuery onUpsert={upsertAiLine} onClear={clearAiLines} onPendingChange={setChoicePending} onExcludedChange={setExcluded} /> : null}
          <Card className="p-4">
            <OrderProductSearch onSelect={addHit} />
          </Card>
          <Card className="overflow-hidden">
            <div className="border-b border-line px-4 py-3">
              <h2 className="font-display text-xl text-ink">Order items</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[860px] text-left text-sm">
                <thead className="bg-stone-50 text-xs uppercase tracking-wide text-stone-500">
                  <tr>
                    <th className="px-4 py-3 font-semibold">Product</th>
                    <th className="px-4 py-3 font-semibold">Quantity</th>
                    <th className="px-4 py-3 font-semibold">Unit</th>
                    <th className="px-4 py-3 font-semibold">Price</th>
                    <th className="px-4 py-3 font-semibold">Discount</th>
                    <th className="px-4 py-3 font-semibold">Total</th>
                    <th className="px-4 py-3 font-semibold">
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {lines.length === 0 ? (
                    <tr>
                      <td className="px-4 py-10 text-center text-stone-500" colSpan={7}>
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
                            {line.sku ? <div className="text-xs text-stone-500">{line.sku}</div> : null}
                          </td>
                          <td className="px-4 py-3">
                            <input
                              className="field w-24"
                              aria-label={`Quantity for ${line.name}`}
                              inputMode="decimal"
                              value={line.quantity}
                              onChange={(event) =>
                                setLines((current) => current.map((item) => (item.key === line.key ? { ...item, quantity: event.target.value } : item)))
                              }
                            />
                          </td>
                          <td className="px-4 py-3">
                            <select
                              className="field min-w-24"
                              aria-label={`Unit for ${line.name}`}
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
                              aria-label={`Price for ${line.name}`}
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
                                className="field w-20"
                                aria-label={`Discount type for ${line.name}`}
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
                                aria-label={`Discount for ${line.name}`}
                                inputMode="decimal"
                                value={line.discountValue}
                                onChange={(event) =>
                                  setLines((current) =>
                                    current.map((item) => (item.key === line.key ? { ...item, discountValue: event.target.value } : item)),
                                  )
                                }
                              />
                            </div>
                          </td>
                          <td className="px-4 py-3 font-medium">{formatPkr(amounts?.total ?? 0)}</td>
                          <td className="px-4 py-3 text-right">
                            <button
                              type="button"
                              className="btn-danger h-9 w-9 px-0"
                              aria-label={`Remove ${line.name}`}
                              onClick={() => setLines((current) => current.filter((item) => item.key !== line.key))}
                            >
                              <Trash2 className="h-4 w-4" aria-hidden="true" />
                            </button>
                          </td>
                        </tr>
                      )
                    })
                  )}
                </tbody>
              </table>
            </div>
          </Card>
          <Card className="p-4">
            <Field label="Notes">
              <textarea className="field" rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} />
            </Field>
          </Card>
          {excluded.length > 0 ? (
            <p className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-950">
              Excluded from this order: {excluded.join(", ")}. These items are not in the catalogue.
            </p>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={saving || choicePending}>
              {saving ? "Saving…" : "Confirm order"}
            </Button>
            <Button variant="ghost" disabled={saving || choicePending} onClick={() => void submit(false)}>
              Save draft
            </Button>
            <Button variant="ghost" onClick={onCancel}>
              Cancel
            </Button>
          </div>
        </div>
        <Card className="order-first border-pine/20 p-5 xl:sticky xl:top-20 xl:order-none xl:col-start-2 xl:row-start-1">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-stone-500">Order summary</p>
          <p className="mt-3 font-display text-4xl tracking-tight text-ink">{formatPkr(summary.grandTotal)}</p>
          <p className="mt-1 text-sm text-stone-500">Grand total</p>
          <dl className="mt-5 space-y-3 border-t border-line pt-4 text-sm">
            <div className="flex items-center justify-between gap-4">
              <dt className="text-stone-500">Items</dt>
              <dd className="font-medium text-ink">{lines.length}</dd>
            </div>
            <div className="flex items-center justify-between gap-4">
              <dt className="text-stone-500">Quantity</dt>
              <dd className="font-medium text-ink">{formatQty(summary.quantity)}</dd>
            </div>
            <div className="flex items-center justify-between gap-4">
              <dt className="text-stone-500">Subtotal</dt>
              <dd className="font-medium text-ink">{formatPkr(summary.subtotal)}</dd>
            </div>
            <div className="flex items-center justify-between gap-4">
              <dt className="text-stone-500">Item discounts</dt>
              <dd className="font-medium text-ink">{formatPkr(summary.itemDiscount)}</dd>
            </div>
            <div className="flex items-center justify-between gap-4">
              <dt className="text-stone-500">Order discount</dt>
              <dd className="font-medium text-ink">{formatPkr(summary.orderDiscount)}</dd>
            </div>
          </dl>
        </Card>
      </div>
    </form>
  )
}
