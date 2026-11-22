import { useEffect, useState, type ReactNode } from "react"
import { Link, useParams } from "react-router-dom"
import { getInventory, getInventoryHistory, saveStockSettings, type InventoryDetail, type Movement } from "../../../api/inventory"
import { ErrorNote, Field, PageHeader } from "../../../components/ui"
import { InventoryStatusBadge, transactionTypeLabel } from "../components/InventoryStatusBadge"
import { formatPkr, formatQty } from "../logic"

export function InventoryDetailPage() {
  const { productId = "" } = useParams()
  const [detail, setDetail] = useState<InventoryDetail | null>(null)
  const [history, setHistory] = useState<Movement[]>([])
  const [kind, setKind] = useState("")
  const [minimum, setMinimum] = useState("")
  const [reorder, setReorder] = useState("")
  const [maximum, setMaximum] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([getInventory(productId), getInventoryHistory(productId)])
      .then(([stock, movements]) => {
        setDetail(stock)
        setHistory(movements)
        setMinimum(stock.minimum_stock_level ?? "")
        setReorder(stock.reorder_level ?? "")
        setMaximum(stock.maximum_stock_level ?? "")
      })
      .catch((reason: Error) => setError(reason.message))
  }, [productId])

  const visible = history.filter((row) => !kind || row.transaction_type === kind)

  async function saveThresholds() {
    setError(null)
    setSaved(null)
    try {
      await saveStockSettings(productId, {
        minimum_stock_level: minimum || null,
        reorder_level: reorder || null,
        maximum_stock_level: maximum || null,
      })
      const stock = await getInventory(productId)
      setDetail(stock)
      setSaved("Stock levels saved.")
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save stock levels")
    }
  }

  if (!detail && !error) return <p className="text-sm text-stone-500">Loading stock…</p>

  return (
    <div>
      <PageHeader
        title={detail?.product_name ?? "Stock"}
        lede={detail ? `${detail.sku} · ${detail.category_name}` : undefined}
        action={
          <div className="flex flex-wrap gap-2">
            <Link className="btn" to={`/inventory/receipts/new?product=${productId}`}>
              Receive
            </Link>
            <Link className="btn-ghost" to={`/inventory/issues/new?product=${productId}`}>
              Issue
            </Link>
            <Link className="btn-ghost" to={`/inventory/adjustments/new?product=${productId}`}>
              Adjust
            </Link>
          </div>
        }
      />
      <ErrorNote message={error} />
      {saved ? <p className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{saved}</p> : null}
      {detail ? (
        <>
          <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Fact label="On hand" value={`${formatQty(detail.quantity_on_hand)} ${detail.unit_symbol}`} />
            <Fact label="Average cost" value={formatPkr(detail.average_cost)} />
            <Fact label="Inventory value" value={formatPkr(detail.inventory_value)} />
            <Fact label="Status" value={<InventoryStatusBadge status={detail.stock_status} />} />
          </div>
          <p className="mb-6 text-sm text-stone-600">
            Catalogue cost {formatPkr(detail.cost_price)}
            {detail.brand ? ` · ${detail.brand}` : ""}
            {detail.net_quantity ? ` · ${formatQty(detail.net_quantity)} ${detail.net_quantity_unit_symbol ?? ""} per ${detail.unit_symbol}` : ""}
          </p>
          <form
            className="mb-8 grid gap-3 rounded-lg border border-line bg-white p-4 md:grid-cols-4"
            onSubmit={(event) => {
              event.preventDefault()
              void saveThresholds()
            }}
          >
            <Field label="Minimum">
              <input className="field" inputMode="decimal" value={minimum} onChange={(event) => setMinimum(event.target.value)} />
            </Field>
            <Field label="Reorder">
              <input className="field" inputMode="decimal" value={reorder} onChange={(event) => setReorder(event.target.value)} />
            </Field>
            <Field label="Maximum">
              <input className="field" inputMode="decimal" value={maximum} onChange={(event) => setMaximum(event.target.value)} />
            </Field>
            <div className="flex items-end">
              <button className="btn" type="submit">
                Save levels
              </button>
            </div>
          </form>
          <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
            <h2 className="font-display text-xl">Stock movement history</h2>
            <select className="field w-auto" value={kind} onChange={(event) => setKind(event.target.value)}>
              <option value="">All movements</option>
              <option value="OPENING_STOCK">Opening stock</option>
              <option value="STOCK_RECEIPT">Receipts</option>
              <option value="STOCK_ISSUE">Issues</option>
              <option value="STOCK_ADJUSTMENT">Adjustments</option>
              <option value="REVERSAL">Reversals</option>
            </select>
          </div>
          <div className="overflow-x-auto rounded-lg border border-line bg-white">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-stone-100 text-xs uppercase tracking-wide text-stone-500">
                <tr>
                  <th className="px-4 py-3">Number</th>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Movement</th>
                  <th className="px-4 py-3">Cost</th>
                </tr>
              </thead>
              <tbody>
                {visible.length === 0 ? (
                  <tr>
                    <td className="px-4 py-6 text-stone-500" colSpan={5}>
                      No movements of this kind yet.
                    </td>
                  </tr>
                ) : (
                  visible.map((row) => (
                    <tr key={`${row.transaction_id}-${row.quantity_delta}`} className="border-t border-line">
                      <td className="px-4 py-3">
                        <Link className="font-medium underline-offset-2 hover:underline" to={`/inventory/transactions/${row.transaction_id}`}>
                          {row.transaction_number}
                        </Link>
                      </td>
                      <td className="px-4 py-3">{row.transaction_date}</td>
                      <td className="px-4 py-3">{transactionTypeLabel(row.transaction_type)}</td>
                      <td className="px-4 py-3">
                        {Number(row.quantity_delta) > 0 ? "+" : ""}
                        {formatQty(row.quantity_delta)} {detail.unit_symbol}
                      </td>
                      <td className="px-4 py-3">{formatPkr(row.total_cost)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </div>
  )
}

function Fact({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-lg border border-line bg-white px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">{label}</p>
      <div className="mt-1 text-lg font-medium text-ink">{value}</div>
    </div>
  )
}
