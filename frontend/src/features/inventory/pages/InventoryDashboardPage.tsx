import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { getInventorySummary, type InventorySummary } from "../../../api/inventory"
import { ErrorNote, PageHeader } from "../../../components/ui"
import { InventoryStatusBadge, transactionTypeLabel } from "../components/InventoryStatusBadge"
import { StockSummaryCards } from "../components/StockSummaryCards"
import { formatPkr, formatQty } from "../logic"

const actions = [
  { to: "/inventory/stock", label: "View inventory" },
  { to: "/inventory/opening", label: "Opening stock" },
  { to: "/inventory/receipts/new", label: "Receive stock" },
  { to: "/inventory/issues/new", label: "Issue stock" },
  { to: "/inventory/adjustments/new", label: "Adjust stock" },
  { to: "/inventory/reports", label: "Reports" },
]

export function InventoryDashboardPage() {
  const [summary, setSummary] = useState<InventorySummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getInventorySummary()
      .then(setSummary)
      .catch((reason: Error) => setError(reason.message))
  }, [])

  return (
    <div>
      <PageHeader title="Inventory" lede="Stock on hand, value, and the latest movements for the yard." />
      <ErrorNote message={error} />
      {summary ? (
        <>
          <StockSummaryCards
            value={summary.total_value}
            products={summary.product_count}
            low={summary.low_stock_count}
            out={summary.out_of_stock_count}
          />
          <div className="mb-6 flex flex-wrap gap-2">
            {actions.map((action) => (
              <Link key={action.to} className="btn-ghost" to={action.to}>
                {action.label}
              </Link>
            ))}
          </div>
          <div className="grid gap-6 xl:grid-cols-2">
            <section>
              <h2 className="mb-3 font-display text-xl">Recent movements</h2>
              <div className="overflow-x-auto rounded-lg border border-line bg-white">
                <table className="w-full text-left text-sm">
                  <thead className="bg-stone-100 text-xs uppercase tracking-wide text-stone-500">
                    <tr>
                      <th className="px-4 py-3">Number</th>
                      <th className="px-4 py-3">Type</th>
                      <th className="px-4 py-3">Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.recent_transactions.length === 0 ? (
                      <tr>
                        <td className="px-4 py-6 text-stone-500" colSpan={3}>
                          No stock movements yet.
                        </td>
                      </tr>
                    ) : (
                      summary.recent_transactions.map((item) => (
                        <tr key={item.id} className="border-t border-line">
                          <td className="px-4 py-3">
                            <Link className="font-medium underline-offset-2 hover:underline" to={`/inventory/transactions/${item.id}`}>
                              {item.transaction_number}
                            </Link>
                          </td>
                          <td className="px-4 py-3">{transactionTypeLabel(item.transaction_type)}</td>
                          <td className="px-4 py-3">{formatPkr(item.total_value)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </section>
            <section>
              <h2 className="mb-3 font-display text-xl">Value by category</h2>
              <div className="rounded-lg border border-line bg-white">
                {summary.value_by_category.length === 0 ? (
                  <p className="px-4 py-6 text-sm text-stone-500">No inventory value yet.</p>
                ) : (
                  summary.value_by_category.map((row) => (
                    <div key={row.category_name} className="flex items-center justify-between border-t border-line px-4 py-3 text-sm first:border-t-0">
                      <span>{row.category_name}</span>
                      <span className="font-medium">{formatPkr(row.inventory_value)}</span>
                    </div>
                  ))
                )}
              </div>
              <h2 className="mb-3 mt-6 font-display text-xl">Movement summary</h2>
              <div className="rounded-lg border border-line bg-white">
                {summary.movement_counts.length === 0 ? (
                  <p className="px-4 py-6 text-sm text-stone-500">No posted movements yet.</p>
                ) : (
                  summary.movement_counts.map((row) => (
                    <div key={row.transaction_type} className="flex items-center justify-between border-t border-line px-4 py-3 text-sm first:border-t-0">
                      <span>{transactionTypeLabel(row.transaction_type)}</span>
                      <span className="font-medium">{row.count}</span>
                    </div>
                  ))
                )}
              </div>
            </section>
          </div>
          <div className="mt-6 grid gap-6 xl:grid-cols-2">
            <WatchList title="Low stock" rows={summary.low_stock} empty="Nothing is below its minimum." />
            <WatchList title="Out of stock" rows={summary.out_of_stock} empty="Nothing is out of stock." />
          </div>
        </>
      ) : error ? null : (
        <p className="text-sm text-stone-500">Loading inventory…</p>
      )}
    </div>
  )
}

function WatchList({
  title,
  rows,
  empty,
}: {
  title: string
  rows: InventorySummary["low_stock"]
  empty: string
}) {
  return (
    <section>
      <h2 className="mb-3 font-display text-xl">{title}</h2>
      <div className="overflow-hidden rounded-lg border border-line bg-white">
        {rows.length === 0 ? (
          <p className="px-4 py-6 text-sm text-stone-500">{empty}</p>
        ) : (
          rows.map((row) => (
            <Link
              key={row.product_id}
              to={`/inventory/stock/${row.product_id}`}
              className="flex items-center justify-between gap-3 border-t border-line px-4 py-3 text-sm first:border-t-0 hover:bg-paper"
            >
              <span>
                <span className="font-medium">{row.product_name}</span>
                <span className="ml-2 text-stone-500">{row.sku}</span>
              </span>
              <span className="flex items-center gap-3">
                <span>
                  {formatQty(row.quantity_on_hand)} {row.unit_symbol}
                </span>
                <InventoryStatusBadge status={row.stock_status} />
              </span>
            </Link>
          ))
        )}
      </div>
    </section>
  )
}
