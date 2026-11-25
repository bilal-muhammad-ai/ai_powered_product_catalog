import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { getTransaction, postTransaction, reverseTransaction, type Transaction } from "../../../api/inventory"
import { ApiError } from "../../../api/client"
import { ConfirmationDialog, DataTable, ErrorNote, LoadingState, PageHeader, tableCellClass, tableHeadClass } from "../../../components/ui"
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

  if (!transaction && !error) return <LoadingState label="Loading transaction…" />

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
        <ConfirmationDialog
          title={confirm === "post" ? "Post transaction" : "Reverse transaction"}
          message={confirm === "post" ? "Post this draft and update stock?" : "Reverse this posted transaction?"}
          confirmLabel="Confirm"
          tone={confirm === "reverse" ? "danger" : "primary"}
          onClose={() => setConfirm(null)}
          onConfirm={() => void run()}
        />
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
          <DataTable className="min-w-[760px]">
              <thead className={tableHeadClass}>
                <tr>
                  <th className={tableCellClass}>Product</th>
                  <th className={tableCellClass}>SKU</th>
                  <th className={tableCellClass}>Quantity</th>
                  <th className={tableCellClass}>Unit</th>
                  <th className={tableCellClass}>Unit cost</th>
                  <th className={tableCellClass}>Total</th>
                  <th className={tableCellClass}>Movement</th>
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
          </DataTable>
        </>
      ) : null}
    </div>
  )
}
