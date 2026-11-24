import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { getInventorySummary, type InventorySummary } from "../../api/inventory"
import { Badge, Card, EmptyState, ErrorNote, LoadingState, PageHeader } from "../../components/ui"
import { InventoryStatusBadge } from "../inventory/components/InventoryStatusBadge"
import { formatQty } from "../inventory/logic"
import { listOrders, type OrderListItem } from "../orders/api"
import { OrderStatusBadge } from "../orders/components/OrderStatusBadge"
import { formatPkr } from "../orders/logic"
import { StockSummaryCards } from "../inventory/components/StockSummaryCards"

const shortcuts = [
  { to: "/orders/new", label: "New order" },
  { to: "/products", label: "Products" },
  { to: "/inventory/stock", label: "Stock on hand" },
  { to: "/inventory/receipts/new", label: "Receive stock" },
]

export function DashboardPage() {
  const [summary, setSummary] = useState<InventorySummary | null>(null)
  const [orders, setOrders] = useState<OrderListItem[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.allSettled([
      getInventorySummary(),
      listOrders({ page: "1", page_size: "5", sort: "order_date", direction: "desc" }),
    ]).then(([stock, recent]) => {
      const messages: string[] = []
      if (stock.status === "fulfilled") setSummary(stock.value)
      else messages.push(stock.reason instanceof Error ? stock.reason.message : "Could not load inventory")
      if (recent.status === "fulfilled") setOrders(recent.value.items)
      else messages.push(recent.reason instanceof Error ? recent.reason.message : "Could not load orders")
      setError(messages.length ? messages.join("\n") : null)
      setLoading(false)
    })
  }, [])

  return (
    <div>
      <PageHeader
        title="Dashboard"
        lede="Stock position and the latest orders for the yard."
        action={
          <Link className="btn" to="/orders/new">
            New order
          </Link>
        }
      />
      {loading ? <LoadingState label="Loading the yard overview…" /> : null}
      <ErrorNote message={error} />
      {summary ? (
        <StockSummaryCards
          value={summary.total_value}
          products={summary.product_count}
          low={summary.low_stock_count}
          out={summary.out_of_stock_count}
        />
      ) : null}
      <div className="mb-6 flex flex-wrap gap-2">
        {shortcuts.map((item) => (
          <Link key={item.to} className="btn-ghost" to={item.to}>
            {item.label}
          </Link>
        ))}
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
                    <p className="text-xs text-stone-500">{order.order_date}</p>
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
        <Card>
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <h2 className="font-display text-xl text-ink">Needs attention</h2>
            <Link className="text-sm font-semibold text-copper hover:text-copper-bright" to="/inventory">
              Inventory
            </Link>
          </div>
          {summary && summary.low_stock.length === 0 && summary.out_of_stock.length === 0 ? (
            <EmptyState title="Stock levels look clear" detail="Low and out-of-stock products will show up here." />
          ) : null}
          {summary && (summary.low_stock.length > 0 || summary.out_of_stock.length > 0) ? (
            <ul>
              {[...summary.out_of_stock, ...summary.low_stock].slice(0, 6).map((item) => (
                <li key={item.product_id} className="flex items-center justify-between gap-3 border-t border-line px-4 py-3 text-sm first:border-t-0">
                  <div className="min-w-0">
                    <Link className="font-medium text-ink underline-offset-2 hover:underline" to={`/inventory/stock/${item.product_id}`}>
                      {item.product_name}
                    </Link>
                    <p className="text-xs text-stone-500">
                      {item.sku} · {formatQty(item.quantity_on_hand)} {item.unit_symbol}
                    </p>
                  </div>
                  <InventoryStatusBadge status={item.stock_status} />
                </li>
              ))}
            </ul>
          ) : null}
          {summary ? (
            <div className="flex flex-wrap gap-2 border-t border-line px-4 py-3">
              <Badge tone="warning">{summary.low_stock_count} low</Badge>
              <Badge tone="danger">{summary.out_of_stock_count} out</Badge>
            </div>
          ) : null}
        </Card>
      </div>
    </div>
  )
}
