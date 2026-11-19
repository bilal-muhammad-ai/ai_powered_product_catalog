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
  const cards = [
    { label: "Inventory value", value: formatPkr(value) },
    { label: "Stocked products", value: formatQty(products) },
    { label: "Low stock", value: formatQty(low) },
    { label: "Out of stock", value: formatQty(out) },
  ]
  return (
    <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((card) => (
        <div key={card.label} className="rounded-lg border border-line bg-white px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">{card.label}</p>
          <p className="mt-1 font-display text-2xl text-ink">{card.value}</p>
        </div>
      ))}
    </div>
  )
}
