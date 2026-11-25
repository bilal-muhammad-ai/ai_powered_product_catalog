import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { readOrder, type Order } from "../api"
import { formatPkr, formatQty } from "../logic"

export function OrderReceiptPage() {
  const { orderId = "" } = useParams()
  const [order, setOrder] = useState<Order | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    async function load() {
      try {
        const row = await readOrder(orderId)
        if (active) setOrder(row)
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : "Could not load the receipt")
      }
    }
    void load()
    return () => {
      active = false
    }
  }, [orderId])

  if (error) return <p className="p-8 text-sm text-red-700">{error}</p>
  if (!order) return <p className="p-8 text-sm text-stone-500">Loading receipt…</p>

  return (
    <div className="mx-auto max-w-3xl bg-white px-6 py-8 text-ink">
      <div className="mb-6 flex items-start justify-between gap-4 print:hidden">
        <Link className="btn-ghost" to={`/orders/${order.id}`}>
          Back
        </Link>
        <button className="btn" type="button" onClick={() => window.print()}>
          Print
        </button>
      </div>
      <header className="border-b border-stone-300 pb-4">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">Rehan Cement</p>
        <h1 className="mt-1 font-display text-3xl">Order {order.order_number}</h1>
        <p className="mt-1 text-sm text-stone-600">{order.order_date}</p>
      </header>
      <table className="mt-6 w-full text-left text-sm">
        <thead>
          <tr className="border-b border-stone-300 text-xs uppercase tracking-wide text-stone-500">
            <th className="py-2">Item</th>
            <th className="py-2">Qty</th>
            <th className="py-2">Unit</th>
            <th className="py-2">Price</th>
            <th className="py-2 text-right">Total</th>
          </tr>
        </thead>
        <tbody>
          {order.items.map((item) => (
            <tr key={item.id} className="border-b border-stone-200">
              <td className="py-2">
                <div>{item.product_name_snapshot}</div>
                <div className="text-xs text-stone-500">{item.sku_snapshot}</div>
              </td>
              <td className="py-2">{formatQty(item.quantity)}</td>
              <td className="py-2">{item.unit_name_snapshot}</td>
              <td className="py-2">{formatPkr(item.unit_price)}</td>
              <td className="py-2 text-right">{formatPkr(item.total)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-4 space-y-1 text-sm">
        <p className="flex justify-between">
          <span>Subtotal</span>
          <span>{formatPkr(order.subtotal)}</span>
        </p>
        <p className="flex justify-between">
          <span>Item discounts</span>
          <span>{formatPkr(order.item_discount_total)}</span>
        </p>
        <p className="flex justify-between">
          <span>Order discount</span>
          <span>{formatPkr(order.order_discount_amount)}</span>
        </p>
        <p className="flex justify-between border-t border-stone-300 pt-2 text-base font-semibold">
          <span>Grand total</span>
          <span>{formatPkr(order.grand_total)}</span>
        </p>
      </div>
      {order.notes ? <p className="mt-6 text-sm text-stone-600">{order.notes}</p> : null}
    </div>
  )
}
