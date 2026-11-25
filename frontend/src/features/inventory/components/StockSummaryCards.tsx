import { StatCard, StatGrid } from "../../../components/ui"
import { formatPkr, formatQty } from "../logic"

export function StockSummaryCards({
  value,
  products,
  low,
  out,
}: {
  value: string
  products: number
  low: number
  out: number
}) {
  return (
    <StatGrid>
      <StatCard label="Inventory value" value={formatPkr(value)} />
      <StatCard label="Stocked products" value={formatQty(products)} />
      <StatCard label="Low stock" value={formatQty(low)} />
      <StatCard label="Out of stock" value={formatQty(out)} />
    </StatGrid>
  )
}
