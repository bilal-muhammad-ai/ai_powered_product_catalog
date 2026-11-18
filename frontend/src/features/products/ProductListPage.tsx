import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { deleteProduct, listCategories, listProducts } from "../../api/resources"
import type { CategoryNode, ProductListItem } from "../../api/types"
import { ErrorNote, Field, PageHeader } from "../../components/ui"
import { flattenCategories } from "../../lib/tree"

export function ProductListPage() {
  const [items, setItems] = useState<ProductListItem[]>([])
  const [categories, setCategories] = useState<CategoryNode[]>([])
  const [error, setError] = useState<string | null>(null)
  const [q, setQ] = useState("")
  const [categoryId, setCategoryId] = useState("")
  const [status, setStatus] = useState("")
  const [attrCode, setAttrCode] = useState("")
  const [attrValue, setAttrValue] = useState("")

  async function reload(next?: { q?: string; categoryId?: string; status?: string; attrCode?: string; attrValue?: string }) {
    const params = new URLSearchParams()
    const query = next?.q ?? q
    const category = next?.categoryId ?? categoryId
    const productStatus = next?.status ?? status
    const code = next?.attrCode ?? attrCode
    const value = next?.attrValue ?? attrValue
    if (query) params.set("q", query)
    if (category) params.set("category_id", category)
    if (productStatus) params.set("status", productStatus)
    if (code && value) params.append("attr", `${code}:${value}`)
    const page = await listProducts(params)
    setItems(page.items)
  }

  useEffect(() => {
    Promise.all([reload(), listCategories().then(setCategories)]).catch((reason: Error) => setError(reason.message))
  }, [])

  const flat = flattenCategories(categories)

  return (
    <div>
      <PageHeader
        title="Products"
        lede="Choose a category on the product form and its fields appear on the same page."
        action={
          <Link className="btn" to="/products/new">
            New product
          </Link>
        }
      />
      <ErrorNote message={error} />
      <form
        className="mb-6 grid gap-3 rounded-lg border border-line bg-white p-4 md:grid-cols-5"
        onSubmit={(event) => {
          event.preventDefault()
          reload().catch((reason: Error) => setError(reason.message))
        }}
      >
        <Field label="Search">
          <input className="field" value={q} onChange={(event) => setQ(event.target.value)} />
        </Field>
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
        <div className="md:col-span-5">
          <button className="btn" type="submit">
            Apply filters
          </button>
        </div>
      </form>
      <div className="overflow-hidden rounded-lg border border-line bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-stone-100 text-xs uppercase tracking-wide text-stone-500">
            <tr>
              <th className="px-4 py-3">Product</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Variants</th>
              <th className="px-4 py-3">Price</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td className="px-4 py-6 text-stone-500" colSpan={6}>
                  No products match.
                </td>
              </tr>
            ) : null}
            {items.map((item) => (
              <tr key={item.id} className="border-t border-line">
                <td className="px-4 py-3">
                  <p className="font-semibold">{item.name}</p>
                  <p className="font-mono text-xs text-stone-500">{item.code || item.slug}</p>
                </td>
                <td className="px-4 py-3">{item.category_name}</td>
                <td className="px-4 py-3 capitalize">{item.status}</td>
                <td className="px-4 py-3">{item.variant_count}</td>
                <td className="px-4 py-3">{priceLabel(item)}</td>
                <td className="px-4 py-3 text-right">
                  <Link className="btn-ghost mr-2" to={`/products/${item.id}`}>
                    Edit
                  </Link>
                  <button
                    type="button"
                    className="btn-danger"
                    onClick={() =>
                      deleteProduct(item.id)
                        .then(() => reload())
                        .catch((reason: Error) => setError(reason.message))
                    }
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function priceLabel(item: ProductListItem) {
  if (!item.selling_price_min) {
    return "—"
  }
  if (item.selling_price_max && item.selling_price_max !== item.selling_price_min) {
    return `${item.selling_price_min} – ${item.selling_price_max}`
  }
  return item.selling_price_min
}
