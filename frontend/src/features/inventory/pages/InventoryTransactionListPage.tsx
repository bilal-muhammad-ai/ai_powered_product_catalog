import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { listTransactions, postTransaction, reverseTransaction, type TransactionListItem } from "../../../api/inventory"
import { Card, ConfirmationDialog, DataTable, ErrorNote, Field, PageHeader, Pagination, SearchInput, tableCellClass, tableHeadClass } from "../../../components/ui"
import { TransactionStatusBadge, transactionTypeLabel } from "../components/InventoryStatusBadge"
import { formatPkr, formatQty } from "../logic"

type TransactionFilters = {
  q: string
  type: string
  status: string
  dateFrom: string
  dateTo: string
}

const emptyTransactionFilters: TransactionFilters = {
  q: "",
  type: "",
  status: "",
  dateFrom: "",
  dateTo: "",
}

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

  async function reload(nextPage = page, filters?: TransactionFilters) {
    const current = filters ?? { q, type, status, dateFrom, dateTo }
    setLoading(true)
    const result = await listTransactions({
      page: String(nextPage),
      page_size: "20",
      transaction_type: current.type,
      status: current.status,
      q: current.q,
      date_from: current.dateFrom,
      date_to: current.dateTo,
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

  function clearFilters() {
    setQ(emptyTransactionFilters.q)
    setType(emptyTransactionFilters.type)
    setStatus(emptyTransactionFilters.status)
    setDateFrom(emptyTransactionFilters.dateFrom)
    setDateTo(emptyTransactionFilters.dateTo)
    reload(1, emptyTransactionFilters).catch((reason: Error) => {
      setError(reason.message)
      setLoading(false)
    })
  }

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

  return (
    <div>
      <PageHeader title="Transactions" lede="Drafts can be posted. Posted documents are corrected by a reversal." />
      <ErrorNote message={error} />
      {pending ? (
        <ConfirmationDialog
          title={pending.action === "post" ? "Post transaction" : "Reverse transaction"}
          message={`${pending.action === "post" ? "Post" : "Reverse"} ${pending.number}? This updates stock.`}
          confirmLabel="Confirm"
          tone={pending.action === "reverse" ? "danger" : "primary"}
          onClose={() => setPending(null)}
          onConfirm={() => void confirm()}
        />
      ) : null}
      <form
        onSubmit={(event) => {
          event.preventDefault()
          reload(1).catch((reason: Error) => setError(reason.message))
        }}
      >
        <Card className="mb-6 grid gap-3 p-4 md:grid-cols-3 xl:grid-cols-6">
        <SearchInput label="Search" value={q} onChange={setQ} placeholder="Number, product, SKU" />
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
        <div className="flex items-end gap-2">
          <button className="btn" type="submit">
            Apply filters
          </button>
          <button className="btn-ghost" type="button" onClick={clearFilters}>
            Clear
          </button>
        </div>
        </Card>
      </form>
      <DataTable className="min-w-[980px]">
          <thead className={tableHeadClass}>
            <tr>
              <th className={tableCellClass}>Number</th>
              <th className={tableCellClass}>Type</th>
              <th className={tableCellClass}>Date</th>
              <th className={tableCellClass}>Items</th>
              <th className={tableCellClass}>Quantity</th>
              <th className={tableCellClass}>Value</th>
              <th className={tableCellClass}>Status</th>
              <th className={tableCellClass}>Reference</th>
              <th className={tableCellClass} />
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
      </DataTable>
      <Pagination
        page={page}
        pageSize={20}
        total={total}
        noun="transactions"
        onPage={(next) => reload(next).catch((reason: Error) => setError(reason.message))}
      />
    </div>
  )
}
