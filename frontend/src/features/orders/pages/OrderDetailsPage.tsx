import { useEffect, useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { ErrorNote, PageHeader } from "../../../components/ui"
import { cancelOrder, completeOrder, confirmOrder, deleteOrder, readOrder, type Order } from "../api"
import { OrderStatusBadge } from "../components/OrderStatusBadge"
import { formatPkr, formatQty } from "../logic"

export function OrderDetailsPage() {
  const { orderId = "" } = useParams()
  const navigate = useNavigate()
  const [order, setOrder] = useState<Order | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState<"confirm" | "cancel" | "delete" | null>(null)

  useEffect(() => {
    let active = true
    async function load() {
      try {
        const row = await readOrder(orderId)
        if (active) {
          setOrder(row)
          setError(null)
        }
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : "Could not load the order")
      }
    }
    void load()
    return () => {
      active = false
    }
  }, [orderId])

  async function run() {
    if (!pending) return
    setError(null)
    try {
      if (pending === "delete") {
        await deleteOrder(orderId)
        navigate("/orders")
        return
      }
      const saved = pending === "confirm" ? await confirmOrder(orderId) : await cancelOrder(orderId)
      setOrder(saved)
      setPending(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not update the order")
      setPending(null)
    }
  }

  async function complete() {
    setError(null)
    try {
      setOrder(await completeOrder(orderId))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not complete the order")
    }
  }

  if (!order && !error) return <p className="text-sm text-stone-500">Loading order…</p>

  return (
    <div>
      <PageHeader
        title={order?.order_number ?? "Order"}
        lede={order ? order.order_date : undefined}
        action={
          order ? (
            <div className="flex flex-wrap gap-2">
              {order.status === "DRAFT" ? (
                <Link className="btn-ghost" to={`/orders/${order.id}/edit`}>
                  Edit
                </Link>
              ) : null}
              {order.status === "DRAFT" ? (
                <button className="btn" type="button" onClick={() => setPending("confirm")}>
                  Confirm
                </button>
              ) : null}
              {order.status === "DRAFT" ? (
                <button className="btn-danger" type="button" onClick={() => setPending("delete")}>
                  Delete
                </button>
              ) : null}
              {order.status === "CONFIRMED" ? (
                <button className="btn" type="button" onClick={() => void complete()}>
                  Complete
                </button>
              ) : null}
              {order.status === "CONFIRMED" ? (
                <button className="btn-danger" type="button" onClick={() => setPending("cancel")}>
                  Cancel
                </button>
              ) : null}
              <Link className="btn-ghost" to={`/orders/${order.id}/receipt`}>
                Print
              </Link>
            </div>
          ) : null
        }
      />
      <ErrorNote message={error} />
      {pending ? (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-white p-4">
          <p className="text-sm">
            {pending === "confirm" ? "Confirm this order and issue the stock?" : null}
            {pending === "cancel" ? "Cancel this order and return the stock?" : null}
            {pending === "delete" ? "Delete this draft?" : null}
          </p>
          <div className="flex gap-2">
            <button className="btn" type="button" onClick={() => void run()}>
              Confirm
            </button>
            <button className="btn-ghost" type="button" onClick={() => setPending(null)}>
              Back
            </button>
          </div>
        </div>
      ) : null}
      {order ? (
        <>
          <div className="mb-6 grid gap-3 rounded-lg border border-line bg-white p-4 text-sm md:grid-cols-4">
            <p>
              Status <OrderStatusBadge status={order.status} />
            </p>
            <p>Items {order.item_count}</p>
            <p>Quantity {formatQty(order.total_quantity)}</p>
            <p className="font-semibold">Grand total {formatPkr(order.grand_total)}</p>
            {order.inventory_transaction_id ? (
              <p>
                Stock issue{" "}
                <Link className="underline-offset-2 hover:underline" to={`/inventory/transactions/${order.inventory_transaction_id}`}>
                  {order.inventory_transaction_number}
                </Link>
              </p>
            ) : null}
          </div>
          {order.notes ? <p className="mb-4 text-sm text-stone-600">{order.notes}</p> : null}
          <div className="overflow-x-auto rounded-lg border border-line bg-white">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-stone-100 text-xs uppercase tracking-wide text-stone-500">
                <tr>
                  <th className="px-4 py-3">Product</th>
                  <th className="px-4 py-3">Quantity</th>
                  <th className="px-4 py-3">Unit</th>
                  <th className="px-4 py-3">Price</th>
                  <th className="px-4 py-3">Discount</th>
                  <th className="px-4 py-3">Total</th>
                </tr>
              </thead>
              <tbody>
                {order.items.map((item) => (
                  <tr key={item.id} className="border-t border-line">
                    <td className="px-4 py-3">
                      <div className="font-medium">{item.product_name_snapshot}</div>
                      <div className="text-xs text-stone-500">{item.sku_snapshot}</div>
                    </td>
                    <td className="px-4 py-3">{formatQty(item.quantity)}</td>
                    <td className="px-4 py-3">{item.unit_name_snapshot}</td>
                    <td className="px-4 py-3">{formatPkr(item.unit_price)}</td>
                    <td className="px-4 py-3">{formatPkr(item.discount_amount)}</td>
                    <td className="px-4 py-3">{formatPkr(item.total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 grid gap-1 text-sm">
            <p>Subtotal {formatPkr(order.subtotal)}</p>
            <p>Item discounts {formatPkr(order.item_discount_total)}</p>
            <p>Order discount {formatPkr(order.order_discount_amount)}</p>
            <p className="font-semibold">Grand total {formatPkr(order.grand_total)}</p>
          </div>
        </>
      ) : null}
    </div>
  )
}
