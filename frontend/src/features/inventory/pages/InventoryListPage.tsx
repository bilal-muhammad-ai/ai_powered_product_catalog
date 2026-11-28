import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { listInventory, type BalanceItem } from "../../../api/inventory"
import { listCategories } from "../../../api/resources"
import type { CategoryNode } from "../../../api/types"
import { Card, DataTable, ErrorNote, Field, PageHeader, Pagination, SearchInput, tableCellClass, tableHeadClass } from "../../../components/ui"
import { flattenCategories } from "../../../lib/tree"
import { InventoryStatusBadge } from "../components/InventoryStatusBadge"
import { formatPkr, formatQty } from "../logic"

type StockFilters = {
  q: string
  categoryId: string
  brand: string
  status: string
  sort: string
  direction: string
}

const defaultStockFilters: StockFilters = {
  q: "",
  categoryId: "",
  brand: "",
  status: "",
  sort: "name",
  direction: "asc",
}

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

  async function reload(nextPage = page, filters?: StockFilters) {
    const current = filters ?? { q, categoryId, brand, status, sort, direction }
    setLoading(true)
    const result = await listInventory({
      q: current.q,
      category_id: current.categoryId,
      brand: current.brand,
      status: current.status,
      sort: current.sort,
      direction: current.direction,
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

  function clearFilters() {
    setQ(defaultStockFilters.q)
    setCategoryId(defaultStockFilters.categoryId)
    setBrand(defaultStockFilters.brand)
    setStatus(defaultStockFilters.status)
    setSort(defaultStockFilters.sort)
    setDirection(defaultStockFilters.direction)
    reload(1, defaultStockFilters).catch((reason: Error) => setError(reason.message))
  }

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
        onSubmit={(event) => {
          event.preventDefault()
          reload(1).catch((reason: Error) => setError(reason.message))
        }}
      >
        <Card className="mb-6 grid gap-3 p-4 md:grid-cols-3 xl:grid-cols-4">
        <SearchInput label="Search" value={q} onChange={setQ} placeholder="Name or SKU" />
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
        <div className="flex items-end gap-2">
          <button className="btn" type="submit">
            Apply filters
          </button>
          <button className="btn-ghost" type="button" onClick={clearFilters}>
            Clear
          </button>
        </div>
        </Card>
      </form>
      <DataTable className="min-w-[960px]">
          <thead className={tableHeadClass}>
            <tr>
              <th className={tableCellClass}>Product</th>
              <th className={tableCellClass}>SKU</th>
              <th className={tableCellClass}>Category</th>
              <th className={tableCellClass}>Brand</th>
              <th className={tableCellClass}>Quantity</th>
              <th className={tableCellClass}>Average cost</th>
              <th className={tableCellClass}>Value</th>
              <th className={tableCellClass}>Status</th>
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
      </DataTable>
      <Pagination
        page={page}
        pageSize={20}
        total={total}
        noun="products"
        onPage={(next) => reload(next).catch((reason: Error) => setError(reason.message))}
      />
    </div>
  )
}
