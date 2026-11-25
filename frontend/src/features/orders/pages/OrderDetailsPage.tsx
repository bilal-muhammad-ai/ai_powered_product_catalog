import { useEffect, useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { Card, ConfirmationDialog, DataTable, ErrorNote, LoadingState, PageHeader, StatCard, StatGrid, tableCellClass, tableHeadClass } from "../../../components/ui"
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

  if (!order && !error) return <LoadingState label="Loading order…" />

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
        <ConfirmationDialog
          title={pending === "delete" ? "Delete draft" : pending === "cancel" ? "Cancel order" : "Confirm order"}
          message={
            pending === "confirm"
              ? "Confirm this order and issue the stock?"
              : pending === "cancel"
                ? "Cancel this order and return the stock?"
                : "Delete this draft?"
          }
          confirmLabel={pending === "delete" ? "Delete" : "Confirm"}
          tone={pending === "confirm" ? "primary" : "danger"}
          onClose={() => setPending(null)}
          onConfirm={() => void run()}
        />
      ) : null}
      {order ? (
        <>
          <StatGrid>
            <StatCard label="Status" value={<OrderStatusBadge status={order.status} />} />
            <StatCard label="Items" value={order.item_count} />
            <StatCard label="Quantity" value={formatQty(order.total_quantity)} />
            <StatCard label="Grand total" value={formatPkr(order.grand_total)} />
          </StatGrid>
          {order.inventory_transaction_id ? (
            <p className="mb-4 text-sm text-stone-600">
              Stock issue{" "}
              <Link className="font-medium text-copper underline-offset-2 hover:underline" to={`/inventory/transactions/${order.inventory_transaction_id}`}>
                {order.inventory_transaction_number}
              </Link>
            </p>
          ) : null}
          {order.notes ? <p className="mb-4 text-sm text-stone-600">{order.notes}</p> : null}
          <DataTable className="min-w-[760px]">
              <thead className={tableHeadClass}>
                <tr>
                  <th className={tableCellClass}>Product</th>
                  <th className={tableCellClass}>Quantity</th>
                  <th className={tableCellClass}>Unit</th>
                  <th className={tableCellClass}>Price</th>
                  <th className={tableCellClass}>Discount</th>
                  <th className={tableCellClass}>Total</th>
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
          </DataTable>
          <Card className="mt-4 grid gap-2 p-4 text-sm sm:grid-cols-2">
            <p className="flex justify-between gap-4"><span className="text-stone-500">Subtotal</span><span>{formatPkr(order.subtotal)}</span></p>
            <p className="flex justify-between gap-4"><span className="text-stone-500">Item discounts</span><span>{formatPkr(order.item_discount_total)}</span></p>
            <p className="flex justify-between gap-4"><span className="text-stone-500">Order discount</span><span>{formatPkr(order.order_discount_amount)}</span></p>
            <p className="flex justify-between gap-4 font-semibold text-ink"><span>Grand total</span><span>{formatPkr(order.grand_total)}</span></p>
          </Card>
        </>
      ) : null}
    </div>
  )
}
