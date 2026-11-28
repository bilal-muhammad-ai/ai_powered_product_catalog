import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { getInventory, getInventoryHistory, saveStockSettings, type InventoryDetail, type Movement } from "../../../api/inventory"
import { Card, DataTable, ErrorNote, Field, LoadingState, PageHeader, StatCard, StatGrid, tableCellClass, tableHeadClass } from "../../../components/ui"
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

  if (!detail && !error) return <LoadingState label="Loading stock…" />

  return (
    <div>
      <PageHeader
        title={detail?.product_name ?? "Stock"}
        lede={detail ? [detail.sku, detail.category_name].filter(Boolean).join(" · ") : undefined}
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
          <StatGrid>
            <StatCard label="On hand" value={`${formatQty(detail.quantity_on_hand)} ${detail.unit_symbol}`} />
            <StatCard label="Average cost" value={formatPkr(detail.average_cost)} />
            <StatCard label="Inventory value" value={formatPkr(detail.inventory_value)} />
            <StatCard label="Status" value={<InventoryStatusBadge status={detail.stock_status} />} />
          </StatGrid>
          {detail.brand || detail.net_quantity ? (
            <p className="mb-6 text-sm text-stone-600">
              {[
                detail.brand,
                detail.net_quantity
                  ? `${formatQty(detail.net_quantity)} ${detail.net_quantity_unit_symbol ?? ""} per ${detail.unit_symbol}`
                  : null,
              ]
                .filter(Boolean)
                .join(" · ")}
            </p>
          ) : null}
          <form
            className="mb-8"
            onSubmit={(event) => {
              event.preventDefault()
              void saveThresholds()
            }}
          >
            <Card className="grid gap-3 p-4 md:grid-cols-4">
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
            </Card>
          </form>
          <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
            <h2 className="font-display text-xl">Stock movement history</h2>
            <div className="flex items-end gap-2">
              <select className="field w-auto" value={kind} onChange={(event) => setKind(event.target.value)}>
                <option value="">All movements</option>
                <option value="OPENING_STOCK">Opening stock</option>
                <option value="STOCK_RECEIPT">Receipts</option>
                <option value="STOCK_ISSUE">Issues</option>
                <option value="STOCK_ADJUSTMENT">Adjustments</option>
                <option value="REVERSAL">Reversals</option>
              </select>
              <button className="btn-ghost" type="button" onClick={() => setKind("")}>
                Clear
              </button>
            </div>
          </div>
          <DataTable className="min-w-[760px]">
              <thead className={tableHeadClass}>
                <tr>
                  <th className={tableCellClass}>Number</th>
                  <th className={tableCellClass}>Date</th>
                  <th className={tableCellClass}>Type</th>
                  <th className={tableCellClass}>Movement</th>
                  <th className={tableCellClass}>Cost</th>
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
          </DataTable>
        </>
      ) : null}
    </div>
  )
}
