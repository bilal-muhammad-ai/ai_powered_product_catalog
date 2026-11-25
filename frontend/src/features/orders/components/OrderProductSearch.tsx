import { Search } from "lucide-react"
import { useEffect, useState } from "react"
import { Field } from "../../../components/ui"
import { searchOrderCatalog, type OrderCatalogHit } from "../api"
import { formatPkr, formatQty } from "../logic"

export function OrderProductSearch({ onSelect }: { onSelect: (hit: OrderCatalogHit) => void }) {
  const [q, setQ] = useState("")
  const [hits, setHits] = useState<OrderCatalogHit[]>([])
  const [error, setError] = useState<string | null>(null)
  const [searched, setSearched] = useState(false)

  useEffect(() => {
    if (q.trim().length < 2) {
      setHits([])
      setSearched(false)
      return
    }
    const handle = window.setTimeout(() => {
      searchOrderCatalog(q.trim())
        .then((rows) => {
          setHits(rows)
          setSearched(true)
          setError(null)
        })
        .catch((reason: Error) => setError(reason.message))
    }, 250)
    return () => window.clearTimeout(handle)
  }, [q])

  return (
    <div>
      <Field label="Search product, SKU, or category">
        <span className="relative block">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" aria-hidden="true" />
          <input className="field pl-9" value={q} onChange={(event) => setQ(event.target.value)} placeholder="Cement, rod, SKU" />
        </span>
      </Field>
      {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
      {searched && hits.length === 0 ? <p className="mt-3 text-sm text-stone-500">No products found.</p> : null}
      {hits.length > 0 ? (
        <ul className="mt-3 overflow-hidden rounded-lg border border-line">
          {hits.map((hit) => (
            <li key={hit.product_id} className="border-t border-line first:border-t-0">
              <button
                type="button"
                className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left text-sm hover:bg-paper focus-visible:bg-paper focus-visible:outline-none"
                onClick={() => {
                  onSelect(hit)
                  setQ("")
                  setHits([])
                  setSearched(false)
                }}
              >
                <span className="min-w-0">
                  <span className="block font-medium text-ink">{hit.name}</span>
                  <span className="block text-xs text-stone-500">
                    {hit.sku} · {hit.category_name}
                  </span>
                </span>
                <span className="shrink-0 text-right text-stone-600">
                  <span className="block font-medium text-ink">{formatPkr(hit.selling_price)}</span>
                  <span className="block text-xs">
                    {formatQty(hit.quantity_on_hand)} {hit.unit_symbol}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
