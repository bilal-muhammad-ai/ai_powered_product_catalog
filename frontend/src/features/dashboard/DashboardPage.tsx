import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { getInventorySummary, type InventorySummary } from "../../api/inventory"
import { listCategories, listProducts } from "../../api/resources"
import {
  Card,
  EmptyState,
  ErrorNote,
  LoadingState,
  MeterList,
  PageHeader,
  StatCard,
  tableCellClass,
  tableHeadClass,
} from "../../components/ui"
import { InventoryStatusBadge, transactionTypeLabel } from "../inventory/components/InventoryStatusBadge"
import { formatQty } from "../inventory/logic"
import { flattenCategories } from "../../lib/tree"
import { listOrders, type OrderListItem } from "../orders/api"
import { OrderStatusBadge } from "../orders/components/OrderStatusBadge"
import { formatPkr } from "../orders/logic"

export function DashboardPage() {
  const [summary, setSummary] = useState<InventorySummary | null>(null)
  const [orders, setOrders] = useState<OrderListItem[] | null>(null)
  const [catalogTotal, setCatalogTotal] = useState<number | null>(null)
  const [categoryTotal, setCategoryTotal] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const params = new URLSearchParams({ page: "1", page_size: "1" })
    Promise.allSettled([
      getInventorySummary(),
      listOrders({ page: "1", page_size: "5", sort: "order_date", direction: "desc" }),
      listProducts(params),
      listCategories(),
    ]).then(([stock, recent, products, categories]) => {
      const messages: string[] = []
      if (stock.status === "fulfilled") setSummary(stock.value)
      else messages.push(stock.reason instanceof Error ? stock.reason.message : "Could not load inventory")
      if (recent.status === "fulfilled") setOrders(recent.value.items)
      else messages.push(recent.reason instanceof Error ? recent.reason.message : "Could not load orders")
      if (products.status === "fulfilled") setCatalogTotal(products.value.total)
      else messages.push(products.reason instanceof Error ? products.reason.message : "Could not load products")
      if (categories.status === "fulfilled") setCategoryTotal(flattenCategories(categories.value).length)
      else messages.push(categories.reason instanceof Error ? categories.reason.message : "Could not load categories")
      setError(messages.length ? messages.join("\n") : null)
      setLoading(false)
    })
  }, [])

  const attention = summary ? [...summary.out_of_stock, ...summary.low_stock].slice(0, 6) : []

  return (
    <div>
      <PageHeader
        title="Dashboard"
        lede="Catalogue size, stock position, and the latest orders for the yard."
        action={
          <Link className="btn" to="/orders/new">
            New order
          </Link>
        }
      />
      {loading ? <LoadingState label="Loading the yard overview…" /> : null}
      <ErrorNote message={error} />
      <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <StatCard label="Catalogue products" value={catalogTotal ?? "—"} hint="All products in the catalogue" />
        <StatCard label="Categories" value={categoryTotal ?? "—"} />
        <StatCard label="Stocked products" value={summary ? formatQty(summary.product_count) : "—"} hint="Products with a stock balance" />
        <StatCard label="Quantity on hand" value={summary ? formatQty(summary.total_quantity) : "—"} />
        <StatCard label="Inventory value" value={summary ? formatPkr(summary.total_value) : "—"} />
        <StatCard label="Low stock" value={summary ? formatQty(summary.low_stock_count) : "—"} hint={summary ? `${formatQty(summary.out_of_stock_count)} out of stock` : undefined} />
      </div>
      <div className="mb-6 flex flex-wrap gap-2">
        <Link className="btn-ghost" to="/products">
          Products
        </Link>
        <Link className="btn-ghost" to="/inventory/stock">
          Stock on hand
        </Link>
        <Link className="btn-ghost" to="/inventory/receipts/new">
          Receive stock
        </Link>
      </div>
      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <h2 className="font-display text-xl text-ink">Recent orders</h2>
            <Link className="text-sm font-semibold text-copper hover:text-copper-bright" to="/orders">
              View all
            </Link>
          </div>
          {orders && orders.length === 0 ? <EmptyState title="No orders yet" detail="Confirmed and draft orders will appear here." /> : null}
          {orders && orders.length > 0 ? (
            <ul>
              {orders.map((order) => (
                <li key={order.id} className="flex items-center justify-between gap-3 border-t border-line px-4 py-3 text-sm first:border-t-0">
                  <div className="min-w-0">
                    <Link className="font-medium text-ink underline-offset-2 hover:underline" to={`/orders/${order.id}`}>
                      {order.order_number}
                    </Link>
                    <p className="text-xs text-stone-500">
                      {order.order_date} · {order.item_count} items
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-3">
                    <OrderStatusBadge status={order.status} />
                    <span className="font-medium">{formatPkr(order.grand_total)}</span>
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
        </Card>
        <Card className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <h2 className="font-display text-xl text-ink">Recent movements</h2>
            <Link className="text-sm font-semibold text-copper hover:text-copper-bright" to="/inventory/transactions">
              View all
            </Link>
          </div>
          {summary && summary.recent_transactions.length === 0 ? <EmptyState title="No stock movements yet" /> : null}
          {summary && summary.recent_transactions.length > 0 ? (
            <table className="w-full text-left text-sm">
              <thead className={tableHeadClass}>
                <tr>
                  <th className={tableCellClass}>Number</th>
                  <th className={tableCellClass}>Type</th>
                  <th className={tableCellClass}>Value</th>
                </tr>
              </thead>
              <tbody>
                {summary.recent_transactions.slice(0, 5).map((item) => (
                  <tr key={item.id} className="border-t border-line">
                    <td className={tableCellClass}>
                      <Link className="font-medium underline-offset-2 hover:underline" to={`/inventory/transactions/${item.id}`}>
                        {item.transaction_number}
                      </Link>
                    </td>
                    <td className={tableCellClass}>{transactionTypeLabel(item.transaction_type)}</td>
                    <td className={tableCellClass}>{formatPkr(item.total_value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </Card>
        <Card>
          <div className="border-b border-line px-4 py-3">
            <h2 className="font-display text-xl text-ink">Value by category</h2>
          </div>
          <MeterList
            empty="No inventory value yet."
            rows={(summary?.value_by_category ?? []).map((row) => ({
              label: row.category_name,
              value: formatPkr(row.inventory_value),
              amount: Number(row.inventory_value) || 0,
            }))}
          />
        </Card>
        <Card>
          <div className="border-b border-line px-4 py-3">
            <h2 className="font-display text-xl text-ink">Movement summary</h2>
          </div>
          <MeterList
            empty="No posted movements yet."
            rows={(summary?.movement_counts ?? []).map((row) => ({
              label: transactionTypeLabel(row.transaction_type),
              value: String(row.count),
              amount: row.count,
            }))}
          />
        </Card>
        <Card className="xl:col-span-2">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <h2 className="font-display text-xl text-ink">Needs attention</h2>
            <Link className="text-sm font-semibold text-copper hover:text-copper-bright" to="/inventory/stock">
              Stock on hand
            </Link>
          </div>
          {summary && attention.length === 0 ? <EmptyState title="Stock levels look clear" detail="Low and out-of-stock products will show up here." /> : null}
          {attention.length > 0 ? (
            <ul>
              {attention.map((item) => (
                <li key={item.product_id} className="flex items-center justify-between gap-3 border-t border-line px-4 py-3 text-sm first:border-t-0">
                  <div className="min-w-0">
                    <Link className="font-medium text-ink underline-offset-2 hover:underline" to={`/inventory/stock/${item.product_id}`}>
                      {item.product_name}
                    </Link>
                    <p className="text-xs text-stone-500">
                      {[item.sku, `${formatQty(item.quantity_on_hand)} ${item.unit_symbol}`].filter(Boolean).join(" · ")}
                    </p>
                  </div>
                  <InventoryStatusBadge status={item.stock_status} />
                </li>
              ))}
            </ul>
          ) : null}
        </Card>
      </div>
    </div>
  )
}
