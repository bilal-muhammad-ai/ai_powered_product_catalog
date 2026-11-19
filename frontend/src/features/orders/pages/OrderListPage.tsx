import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { ErrorNote, Field, PageHeader } from "../../../components/ui"
import { cancelOrder, confirmOrder, listOrders, type OrderListItem } from "../api"
import { OrderStatusBadge } from "../components/OrderStatusBadge"
import { formatPkr } from "../logic"

export function OrderListPage() {
  const [items, setItems] = useState<OrderListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [q, setQ] = useState("")
  const [status, setStatus] = useState("")
  const [dateFrom, setDateFrom] = useState("")
  const [dateTo, setDateTo] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [pending, setPending] = useState<{ id: string; action: "confirm" | "cancel"; number: string } | null>(null)

  async function reload(nextPage = page) {
    setLoading(true)
    const result = await listOrders({
      q,
      status,
      date_from: dateFrom,
      date_to: dateTo,
      page: String(nextPage),
      page_size: "20",
      sort: "order_date",
      direction: "desc",
    })
    setItems(result.items)
    setTotal(result.total)
    setPage(result.page)
    setLoading(false)
  }

  useEffect(() => {
    reload(1).catch((reason: Error) => {
      setError(reason.message)
      setLoading(false)
    })
  }, [])

  async function runPending() {
    if (!pending) return
    setError(null)
    try {
      if (pending.action === "confirm") await confirmOrder(pending.id)
      else await cancelOrder(pending.id)
      setPending(null)
      await reload(page)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not update the order")
      setPending(null)
    }
  }

  const pages = Math.max(1, Math.ceil(total / 20))

  return (
    <div>
      <PageHeader
        title="Orders"
        lede="Drafts can be changed. Confirming an order issues the stock."
        action={
          <Link className="btn" to="/orders/new">
            New order
          </Link>
        }
      />
      <ErrorNote message={error} />
      {pending ? (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-white p-4">
          <p className="text-sm">
            {pending.action === "confirm" ? "Confirm" : "Cancel"} {pending.number}? This updates stock.
          </p>
          <div className="flex gap-2">
            <button className="btn" type="button" onClick={() => void runPending()}>
              Confirm
            </button>
            <button className="btn-ghost" type="button" onClick={() => setPending(null)}>
              Back
            </button>
          </div>
        </div>
      ) : null}
      <form
        className="mb-6 grid gap-3 rounded-lg border border-line bg-white p-4 md:grid-cols-5"
        onSubmit={(event) => {
          event.preventDefault()
          reload(1).catch((reason: Error) => setError(reason.message))
        }}
      >
        <Field label="Order number">
          <input className="field" value={q} onChange={(event) => setQ(event.target.value)} placeholder="ORD-2026" />
        </Field>
        <Field label="Status">
          <select className="field" value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">Any</option>
            <option value="DRAFT">Draft</option>
            <option value="CONFIRMED">Confirmed</option>
            <option value="COMPLETED">Completed</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
        </Field>
        <Field label="From">
          <input className="field" type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
        </Field>
        <Field label="To">
          <input className="field" type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
        </Field>
        <div className="flex items-end">
          <button className="btn" type="submit">
            Apply filters
          </button>
        </div>
      </form>
      <div className="overflow-x-auto rounded-lg border border-line bg-white">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="bg-stone-100 text-xs uppercase tracking-wide text-stone-500">
            <tr>
              <th className="px-4 py-3">Number</th>
              <th className="px-4 py-3">Date</th>
              <th className="px-4 py-3">Items</th>
              <th className="px-4 py-3">Total</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td className="px-4 py-6 text-stone-500" colSpan={6}>
                  Loading orders…
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td className="px-4 py-6 text-stone-500" colSpan={6}>
                  No orders yet.
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <tr key={item.id} className="border-t border-line">
                  <td className="px-4 py-3">
                    <Link className="font-medium underline-offset-2 hover:underline" to={`/orders/${item.id}`}>
                      {item.order_number}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{item.order_date}</td>
                  <td className="px-4 py-3">{item.item_count}</td>
                  <td className="px-4 py-3">{formatPkr(item.grand_total)}</td>
                  <td className="px-4 py-3">
                    <OrderStatusBadge status={item.status} />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex flex-wrap justify-end gap-2">
                      <Link className="btn-ghost" to={`/orders/${item.id}`}>
                        View
                      </Link>
                      {item.status === "DRAFT" ? (
                        <Link className="btn-ghost" to={`/orders/${item.id}/edit`}>
                          Edit
                        </Link>
                      ) : null}
                      {item.status === "DRAFT" ? (
                        <button className="btn" type="button" onClick={() => setPending({ id: item.id, action: "confirm", number: item.order_number })}>
                          Confirm
                        </button>
                      ) : null}
                      {item.status === "CONFIRMED" ? (
                        <button className="btn-danger" type="button" onClick={() => setPending({ id: item.id, action: "cancel", number: item.order_number })}>
                          Cancel
                        </button>
                      ) : null}
                      <Link className="btn-ghost" to={`/orders/${item.id}/receipt`}>
                        Print
                      </Link>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <div className="mt-4 flex items-center justify-between text-sm text-stone-600">
        <span>
          {total} orders · page {page} of {pages}
        </span>
        <div className="flex gap-2">
          <button className="btn-ghost" type="button" disabled={page <= 1} onClick={() => reload(page - 1).catch((reason: Error) => setError(reason.message))}>
            Previous
          </button>
          <button className="btn-ghost" type="button" disabled={page >= pages} onClick={() => reload(page + 1).catch((reason: Error) => setError(reason.message))}>
            Next
          </button>
        </div>
      </div>
    </div>
  )
}
