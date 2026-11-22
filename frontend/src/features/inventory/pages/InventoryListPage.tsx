import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { listInventory, type BalanceItem } from "../../../api/inventory"
import { listCategories } from "../../../api/resources"
import type { CategoryNode } from "../../../api/types"
import { ErrorNote, Field, PageHeader } from "../../../components/ui"
import { flattenCategories } from "../../../lib/tree"
import { InventoryStatusBadge } from "../components/InventoryStatusBadge"
import { formatPkr, formatQty } from "../logic"

export function InventoryListPage() {
  const [items, setItems] = useState<BalanceItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [categories, setCategories] = useState<CategoryNode[]>([])
  const [q, setQ] = useState("")
  const [categoryId, setCategoryId] = useState("")
  const [brand, setBrand] = useState("")
  const [status, setStatus] = useState("")
  const [sort, setSort] = useState("name")
  const [direction, setDirection] = useState("asc")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  async function reload(nextPage = page) {
    setLoading(true)
    const result = await listInventory({
      q,
      category_id: categoryId,
      brand,
      status,
      sort,
      direction,
      page: String(nextPage),
      page_size: "20",
    })
    setItems(result.items)
    setTotal(result.total)
    setPage(result.page)
    setLoading(false)
  }

  useEffect(() => {
    Promise.all([reload(1), listCategories().then(setCategories)]).catch((reason: Error) => {
      setError(reason.message)
      setLoading(false)
    })
  }, [])

  const pages = Math.max(1, Math.ceil(total / 20))

  return (
    <div>
      <PageHeader
        title="Stock on hand"
        lede="One balance for each product that has been received, issued, or counted."
        action={
          <Link className="btn" to="/inventory/receipts/new">
            Receive stock
          </Link>
        }
      />
      <ErrorNote message={error} />
      <form
        className="mb-6 grid gap-3 rounded-lg border border-line bg-white p-4 md:grid-cols-3 xl:grid-cols-7"
        onSubmit={(event) => {
          event.preventDefault()
          reload(1).catch((reason: Error) => setError(reason.message))
        }}
      >
        <Field label="Search">
          <input className="field" value={q} onChange={(event) => setQ(event.target.value)} placeholder="Name or SKU" />
        </Field>
        <Field label="Category">
          <select className="field" value={categoryId} onChange={(event) => setCategoryId(event.target.value)}>
            <option value="">All</option>
            {flattenCategories(categories).map((category) => (
              <option key={category.id} value={category.id}>
                {"— ".repeat(category.depth)}
                {category.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Brand">
          <input className="field" value={brand} onChange={(event) => setBrand(event.target.value)} />
        </Field>
        <Field label="Stock status">
          <select className="field" value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">Any</option>
            <option value="in_stock">In stock</option>
            <option value="low_stock">Low stock</option>
            <option value="out_of_stock">Out of stock</option>
          </select>
        </Field>
        <Field label="Sort">
          <select className="field" value={sort} onChange={(event) => setSort(event.target.value)}>
            <option value="name">Product</option>
            <option value="sku">SKU</option>
            <option value="quantity">Quantity</option>
            <option value="average_cost">Average cost</option>
            <option value="value">Value</option>
          </select>
        </Field>
        <Field label="Direction">
          <select className="field" value={direction} onChange={(event) => setDirection(event.target.value)}>
            <option value="asc">Ascending</option>
            <option value="desc">Descending</option>
          </select>
        </Field>
        <div className="flex items-end">
          <button className="btn" type="submit">
            Apply filters
          </button>
        </div>
      </form>
      <div className="overflow-x-auto rounded-lg border border-line bg-white">
        <table className="w-full min-w-[960px] text-left text-sm">
          <thead className="bg-stone-100 text-xs uppercase tracking-wide text-stone-500">
            <tr>
              <th className="px-4 py-3">Product</th>
              <th className="px-4 py-3">SKU</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Brand</th>
              <th className="px-4 py-3">Quantity</th>
              <th className="px-4 py-3">Average cost</th>
              <th className="px-4 py-3">Value</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td className="px-4 py-6 text-stone-500" colSpan={8}>
                  Loading inventory…
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td className="px-4 py-6 text-stone-500" colSpan={8}>
                  No stock matches these filters.
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <tr key={item.product_id} className="border-t border-line">
                  <td className="px-4 py-3">
                    <Link className="font-medium underline-offset-2 hover:underline" to={`/inventory/stock/${item.product_id}`}>
                      {item.product_name}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{item.sku}</td>
                  <td className="px-4 py-3">{item.category_name}</td>
                  <td className="px-4 py-3">{item.brand ?? "—"}</td>
                  <td className="px-4 py-3">
                    {formatQty(item.quantity_on_hand)} {item.unit_symbol}
                  </td>
                  <td className="px-4 py-3">{formatPkr(item.average_cost)}</td>
                  <td className="px-4 py-3">{formatPkr(item.inventory_value)}</td>
                  <td className="px-4 py-3">
                    <InventoryStatusBadge status={item.stock_status} />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <div className="mt-4 flex items-center justify-between text-sm">
        <p className="text-stone-600">
          {total} products · page {page} of {pages}
        </p>
        <div className="flex gap-2">
          <button className="btn-ghost" type="button" disabled={page <= 1} onClick={() => reload(page - 1).catch((reason: Error) => setError(reason.message))}>
            Previous
          </button>
          <button className="btn-ghost" type="button" disabled={page >= pages} onClick={() => reload(page + 1).catch((reason: Error) => setError(reason.message))}>
            Next
          </button>
        </div>
      </div>
    </div>
  )
}
