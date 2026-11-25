import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { deleteProduct, listCategories, listProducts } from "../../api/resources"
import type { CategoryNode, ProductListItem } from "../../api/types"
import {
  Badge,
  Card,
  ConfirmationDialog,
  DataTable,
  ErrorNote,
  Field,
  PageHeader,
  Pagination,
  SearchInput,
  tableCellClass,
  tableHeadClass,
} from "../../components/ui"
import { flattenCategories } from "../../lib/tree"
import { formatPkr } from "../orders/logic"

const pageSize = 20

export function ProductListPage() {
  const [items, setItems] = useState<ProductListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [categories, setCategories] = useState<CategoryNode[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState("")
  const [categoryId, setCategoryId] = useState("")
  const [status, setStatus] = useState("")
  const [attrCode, setAttrCode] = useState("")
  const [attrValue, setAttrValue] = useState("")
  const [pendingDelete, setPendingDelete] = useState<ProductListItem | null>(null)

  async function reload(nextPage = page) {
    const params = new URLSearchParams()
    params.set("page", String(nextPage))
    params.set("page_size", String(pageSize))
    if (q) params.set("q", q)
    if (categoryId) params.set("category_id", categoryId)
    if (status) params.set("status", status)
    if (attrCode && attrValue) params.append("attr", `${attrCode}:${attrValue}`)
    const result = await listProducts(params)
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

  const flat = flattenCategories(categories)

  async function confirmDelete() {
    if (!pendingDelete) return
    setError(null)
    try {
      await deleteProduct(pendingDelete.id)
      setPendingDelete(null)
      await reload(page)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not delete the product")
      setPendingDelete(null)
    }
  }

  return (
    <div>
      <PageHeader
        title="Products"
        lede="Search the catalogue, filter by category or status, and open a product to edit it."
        action={
          <Link className="btn" to="/products/new">
            Add product
          </Link>
        }
      />
      <ErrorNote message={error} />
      <form
        onSubmit={(event) => {
          event.preventDefault()
          setLoading(true)
          reload(1).catch((reason: Error) => {
            setError(reason.message)
            setLoading(false)
          })
        }}
      >
        <Card className="mb-6 grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-5">
          <SearchInput label="Search" value={q} onChange={setQ} placeholder="Name, SKU, or code" />
          <Field label="Category">
            <select className="field" value={categoryId} onChange={(event) => setCategoryId(event.target.value)}>
              <option value="">All</option>
              {flat.map((category) => (
                <option key={category.id} value={category.id}>
                  {"— ".repeat(category.depth)}
                  {category.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Status">
            <select className="field" value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="">Any</option>
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="archived">Archived</option>
            </select>
          </Field>
          <Field label="Attribute code">
            <input className="field" value={attrCode} onChange={(event) => setAttrCode(event.target.value)} placeholder="grade" />
          </Field>
          <Field label="Attribute value">
            <input className="field" value={attrValue} onChange={(event) => setAttrValue(event.target.value)} placeholder="53" />
          </Field>
          <div className="xl:col-span-5">
            <button className="btn" type="submit">
              Apply filters
            </button>
          </div>
        </Card>
      </form>
      <DataTable className="min-w-[760px]">
        <thead className={tableHeadClass}>
          <tr>
            <th className={tableCellClass}>Product</th>
            <th className={tableCellClass}>Category</th>
            <th className={tableCellClass}>Status</th>
            <th className={tableCellClass}>Price</th>
            <th className={tableCellClass}>
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td className={`${tableCellClass} text-stone-500`} colSpan={5}>
                Loading products…
              </td>
            </tr>
          ) : items.length === 0 ? (
            <tr>
              <td className={`${tableCellClass} text-stone-500`} colSpan={5}>
                No products match.
              </td>
            </tr>
          ) : (
            items.map((item) => (
              <tr key={item.id} className="border-t border-line">
                <td className={tableCellClass}>
                  <p className="font-medium text-ink">{item.name}</p>
                  <p className="font-mono text-xs text-stone-500">{item.sku}</p>
                </td>
                <td className={tableCellClass}>{item.category_name}</td>
                <td className={tableCellClass}>
                  <Badge tone={item.status === "active" ? "pine" : item.status === "archived" ? "neutral" : "warning"} className="capitalize">
                    {item.status}
                  </Badge>
                </td>
                <td className={tableCellClass}>{formatPkr(item.selling_price)}</td>
                <td className={`${tableCellClass} text-right`}>
                  <Link className="btn-ghost mr-2" to={`/products/${item.id}`}>
                    Edit
                  </Link>
                  <button type="button" className="btn-danger" onClick={() => setPendingDelete(item)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </DataTable>
      <Pagination page={page} pageSize={pageSize} total={total} noun="products" onPage={(next) => reload(next).catch((reason: Error) => setError(reason.message))} />
      {pendingDelete ? (
        <ConfirmationDialog
          title="Delete product"
          message={`Delete ${pendingDelete.name}? This cannot be undone.`}
          confirmLabel="Delete"
          tone="danger"
          onClose={() => setPendingDelete(null)}
          onConfirm={() => void confirmDelete()}
        />
      ) : null}
    </div>
  )
}
