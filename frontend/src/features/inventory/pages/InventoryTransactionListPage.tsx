import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { listTransactions, postTransaction, reverseTransaction, type TransactionListItem } from "../../../api/inventory"
import { ErrorNote, Field, PageHeader } from "../../../components/ui"
import { TransactionStatusBadge, transactionTypeLabel } from "../components/InventoryStatusBadge"
import { formatPkr, formatQty } from "../logic"

export function InventoryTransactionListPage() {
  const [items, setItems] = useState<TransactionListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [type, setType] = useState("")
  const [status, setStatus] = useState("")
  const [q, setQ] = useState("")
  const [dateFrom, setDateFrom] = useState("")
  const [dateTo, setDateTo] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [pending, setPending] = useState<{ id: string; action: "post" | "reverse"; number: string } | null>(null)

  async function reload(nextPage = page) {
    setLoading(true)
    const result = await listTransactions({
      page: String(nextPage),
      page_size: "20",
      transaction_type: type,
      status,
      q,
      date_from: dateFrom,
      date_to: dateTo,
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

  async function confirm() {
    if (!pending) return
    setError(null)
    try {
      if (pending.action === "post") await postTransaction(pending.id)
      else await reverseTransaction(pending.id)
      setPending(null)
      await reload(page)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not update the transaction")
      setPending(null)
    }
  }

  const pages = Math.max(1, Math.ceil(total / 20))

  return (
    <div>
      <PageHeader title="Transactions" lede="Drafts can be posted. Posted documents are corrected by a reversal." />
      <ErrorNote message={error} />
      {pending ? (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-white p-4">
          <p className="text-sm">
            {pending.action === "post" ? "Post" : "Reverse"} {pending.number}? This updates stock.
          </p>
          <div className="flex gap-2">
            <button className="btn" type="button" onClick={() => void confirm()}>
              Confirm
            </button>
            <button className="btn-ghost" type="button" onClick={() => setPending(null)}>
              Cancel
            </button>
          </div>
        </div>
      ) : null}
      <form
        className="mb-6 grid gap-3 rounded-lg border border-line bg-white p-4 md:grid-cols-3 xl:grid-cols-6"
        onSubmit={(event) => {
          event.preventDefault()
          reload(1).catch((reason: Error) => setError(reason.message))
        }}
      >
        <Field label="Search">
          <input className="field" value={q} onChange={(event) => setQ(event.target.value)} placeholder="Number, product, SKU" />
        </Field>
        <Field label="Type">
          <select className="field" value={type} onChange={(event) => setType(event.target.value)}>
            <option value="">Any</option>
            <option value="OPENING_STOCK">Opening stock</option>
            <option value="STOCK_RECEIPT">Receipt</option>
            <option value="STOCK_ISSUE">Issue</option>
            <option value="STOCK_ADJUSTMENT">Adjustment</option>
            <option value="REVERSAL">Reversal</option>
          </select>
        </Field>
        <Field label="Status">
          <select className="field" value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">Any</option>
            <option value="DRAFT">Draft</option>
            <option value="POSTED">Posted</option>
            <option value="REVERSED">Reversed</option>
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
        <table className="w-full min-w-[980px] text-left text-sm">
          <thead className="bg-stone-100 text-xs uppercase tracking-wide text-stone-500">
            <tr>
              <th className="px-4 py-3">Number</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Date</th>
              <th className="px-4 py-3">Items</th>
              <th className="px-4 py-3">Quantity</th>
              <th className="px-4 py-3">Value</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Reference</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td className="px-4 py-6 text-stone-500" colSpan={9}>
                  Loading transactions…
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td className="px-4 py-6 text-stone-500" colSpan={9}>
                  No transactions match.
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <tr key={item.id} className="border-t border-line">
                  <td className="px-4 py-3 font-medium">{item.transaction_number}</td>
                  <td className="px-4 py-3">{transactionTypeLabel(item.transaction_type)}</td>
                  <td className="px-4 py-3">{item.transaction_date}</td>
                  <td className="px-4 py-3">{item.item_count}</td>
                  <td className="px-4 py-3">{formatQty(item.total_quantity)}</td>
                  <td className="px-4 py-3">{formatPkr(item.total_value)}</td>
                  <td className="px-4 py-3">
                    <TransactionStatusBadge status={item.status} />
                  </td>
                  <td className="px-4 py-3">{item.reference_number ?? "—"}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      <Link className="btn-ghost" to={`/inventory/transactions/${item.id}`}>
                        View
                      </Link>
                      {item.status === "DRAFT" ? (
                        <button className="btn" type="button" onClick={() => setPending({ id: item.id, action: "post", number: item.transaction_number })}>
                          Post
                        </button>
                      ) : null}
                      {item.status === "POSTED" && item.transaction_type !== "REVERSAL" ? (
                        <button
                          className="btn-danger"
                          type="button"
                          onClick={() => setPending({ id: item.id, action: "reverse", number: item.transaction_number })}
                        >
                          Reverse
                        </button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <div className="mt-4 flex items-center justify-between text-sm">
        <p className="text-stone-600">
          {total} transactions · page {page} of {pages}
        </p>
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
