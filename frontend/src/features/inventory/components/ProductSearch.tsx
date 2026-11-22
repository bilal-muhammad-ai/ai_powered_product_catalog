import { useEffect, useState } from "react"
import { searchCatalog, type CatalogHit } from "../../../api/inventory"
import { Field } from "../../../components/ui"
import { formatQty } from "../logic"

export function ProductSearch({
  label = "Search product or SKU",
  onSelect,
}: {
  label?: string
  onSelect: (hit: CatalogHit) => void
}) {
  const [q, setQ] = useState("")
  const [hits, setHits] = useState<CatalogHit[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (q.trim().length < 2) {
      setHits([])
      return
    }
    const handle = window.setTimeout(() => {
      searchCatalog(q.trim())
        .then(setHits)
        .catch((reason: Error) => setError(reason.message))
    }, 250)
    return () => window.clearTimeout(handle)
  }, [q])

  return (
    <div>
      <Field label={label}>
        <input className="field" value={q} onChange={(event) => setQ(event.target.value)} placeholder="Cement, rod, SKU" />
      </Field>
      {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
      {hits.length > 0 ? (
        <ul className="mt-2 overflow-hidden rounded-md border border-line bg-white">
          {hits.map((hit) => (
            <li key={hit.product_id} className="border-t border-line first:border-t-0">
              <button
                type="button"
                className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm hover:bg-paper"
                onClick={() => {
                  onSelect(hit)
                  setQ("")
                  setHits([])
                }}
              >
                <span>
                  <span className="font-medium">{hit.name}</span>
                  <span className="ml-2 text-stone-500">{hit.sku}</span>
                </span>
                <span className="text-stone-600">
                  {formatQty(hit.quantity_on_hand)} {hit.unit_symbol}
                </span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
