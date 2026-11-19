import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { getTransaction, postTransaction, reverseTransaction, type Transaction } from "../../../api/inventory"
import { ApiError } from "../../../api/client"
import { ErrorNote, PageHeader } from "../../../components/ui"
import { TransactionStatusBadge, transactionTypeLabel } from "../components/InventoryStatusBadge"
import { formatPkr, formatQty } from "../logic"

async function readTransaction(transactionId: string): Promise<Transaction> {
  try {
    return await getTransaction(transactionId)
  } catch (reason) {
    if (!(reason instanceof ApiError) || reason.status !== 404) throw reason
    await new Promise((resolve) => window.setTimeout(resolve, 200))
    return getTransaction(transactionId)
  }
}

export function InventoryTransactionDetailsPage() {
  const { transactionId = "" } = useParams()
  const [transaction, setTransaction] = useState<Transaction | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [confirm, setConfirm] = useState<"post" | "reverse" | null>(null)

  useEffect(() => {
    let active = true
    async function load() {
      try {
        const row = await readTransaction(transactionId)
        if (active) setTransaction(row)
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : "Could not load the transaction")
      }
    }
    void load()
    return () => {
      active = false
    }
  }, [transactionId])

  async function run() {
    if (!confirm) return
    setError(null)
    try {
      const saved = confirm === "post" ? await postTransaction(transactionId) : await reverseTransaction(transactionId)
      if (confirm === "reverse") {
        setTransaction(saved)
      } else {
        setTransaction(saved)
      }
      setConfirm(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not update the transaction")
      setConfirm(null)
    }
  }

  if (!transaction && !error) return <p className="text-sm text-stone-500">Loading transaction…</p>

  return (
    <div>
      <PageHeader
        title={transaction?.transaction_number ?? "Transaction"}
        lede={transaction ? `${transactionTypeLabel(transaction.transaction_type)} · ${transaction.transaction_date}` : undefined}
        action={
          transaction ? (
            <div className="flex flex-wrap gap-2">
              {transaction.status === "DRAFT" ? (
                <button className="btn" type="button" onClick={() => setConfirm("post")}>
                  Post
                </button>
              ) : null}
              {transaction.status === "POSTED" && transaction.transaction_type !== "REVERSAL" ? (
                <button className="btn-danger" type="button" onClick={() => setConfirm("reverse")}>
                  Reverse
                </button>
              ) : null}
              <Link className="btn-ghost" to="/inventory/transactions">
                Back
              </Link>
            </div>
          ) : null
        }
      />
      <ErrorNote message={error} />
      {confirm ? (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-white p-4">
          <p className="text-sm">{confirm === "post" ? "Post this draft and update stock?" : "Reverse this posted transaction?"}</p>
          <div className="flex gap-2">
            <button className="btn" type="button" onClick={() => void run()}>
              Confirm
            </button>
            <button className="btn-ghost" type="button" onClick={() => setConfirm(null)}>
              Cancel
            </button>
          </div>
        </div>
      ) : null}
      {transaction ? (
        <>
          <div className="mb-6 flex flex-wrap gap-6 text-sm text-stone-700">
            <span>
              Status <TransactionStatusBadge status={transaction.status} />
            </span>
            <span>Items {transaction.item_count}</span>
            <span>Quantity {formatQty(transaction.total_quantity)}</span>
            <span>Value {formatPkr(transaction.total_value)}</span>
            {transaction.reason ? <span>Reason {transaction.reason}</span> : null}
            {transaction.reference_number ? <span>Reference {transaction.reference_number}</span> : null}
          </div>
          {transaction.notes ? <p className="mb-6 text-sm text-stone-600">{transaction.notes}</p> : null}
          <div className="overflow-x-auto rounded-lg border border-line bg-white">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-stone-100 text-xs uppercase tracking-wide text-stone-500">
                <tr>
                  <th className="px-4 py-3">Product</th>
                  <th className="px-4 py-3">SKU</th>
                  <th className="px-4 py-3">Quantity</th>
                  <th className="px-4 py-3">Unit</th>
                  <th className="px-4 py-3">Unit cost</th>
                  <th className="px-4 py-3">Total</th>
                  <th className="px-4 py-3">Movement</th>
                </tr>
              </thead>
              <tbody>
                {transaction.items.map((item) => (
                  <tr key={item.id} className="border-t border-line">
                    <td className="px-4 py-3">
                      <Link className="font-medium underline-offset-2 hover:underline" to={`/inventory/stock/${item.product_id}`}>
                        {item.product_name}
                      </Link>
                    </td>
                    <td className="px-4 py-3">{item.sku}</td>
                    <td className="px-4 py-3">{formatQty(item.quantity)}</td>
                    <td className="px-4 py-3">{item.unit_symbol}</td>
                    <td className="px-4 py-3">{formatPkr(item.unit_cost)}</td>
                    <td className="px-4 py-3">{formatPkr(item.total_cost)}</td>
                    <td className="px-4 py-3">
                      {Number(item.quantity_delta) > 0 ? "+" : ""}
                      {formatQty(item.quantity_delta)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </div>
  )
}
