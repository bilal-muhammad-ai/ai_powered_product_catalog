import { useEffect, useState, type FormEvent } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { getProduct, listAttributes, listCategories, listUnits, saveProduct } from "../../api/resources"
import type { Attribute, CategoryNode, Unit } from "../../api/types"
import { DynamicAttributeFields } from "../../components/forms/DynamicAttributeFields"
import { Card, ErrorNote, Field, PageHeader } from "../../components/ui"
import { flattenCategories } from "../../lib/tree"

function pick(values: Record<string, unknown>, allowed: Set<string>) {
  return Object.fromEntries(Object.entries(values).filter(([key]) => allowed.has(key)))
}

function payloadValue(attribute: Attribute, raw: unknown) {
  if (attribute.data_type === "boolean") {
    return Boolean(raw)
  }
  if (attribute.data_type === "multi_select") {
    return Array.isArray(raw) ? raw : []
  }
  if (raw === undefined || raw === null || raw === "") {
    return null
  }
  return raw
}

function toValueList(attributes: Attribute[], values: Record<string, unknown>) {
  return attributes.flatMap((attribute) => {
    const value = payloadValue(attribute, values[attribute.id])
    const empty = value === null || (Array.isArray(value) && value.length === 0)
    if (empty && !attribute.is_required) {
      return []
    }
    return [{ attribute_id: attribute.id, value }]
  })
}

export function ProductFormPage() {
  const { productId } = useParams()
  const navigate = useNavigate()
  const [categories, setCategories] = useState<CategoryNode[]>([])
  const [units, setUnits] = useState<Unit[]>([])
  const [schema, setSchema] = useState<Attribute[]>([])
  const [categoryId, setCategoryId] = useState("")
  const [name, setName] = useState("")
  const [sku, setSku] = useState("")
  const [barcode, setBarcode] = useState("")
  const [code, setCode] = useState("")
  const [description, setDescription] = useState("")
  const [status, setStatus] = useState("draft")
  const [baseUnitId, setBaseUnitId] = useState("")
  const [sellingUnitId, setSellingUnitId] = useState("")
  const [netQuantity, setNetQuantity] = useState("")
  const [netQuantityUnitId, setNetQuantityUnitId] = useState("")
  const [costPrice, setCostPrice] = useState("")
  const [sellingPrice, setSellingPrice] = useState("")
  const [quantityUnitPrice, setQuantityUnitPrice] = useState("0")
  const [currencyCode, setCurrencyCode] = useState("PKR")
  const [productValues, setProductValues] = useState<Record<string, unknown>>({})
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    Promise.all([listCategories(), listUnits(false)])
      .then(async ([tree, unitPage]) => {
        setCategories(tree)
        setUnits(unitPage.items)
        if (!productId) {
          return
        }
        const product = await getProduct(productId)
        const attributes = await listAttributes(product.category_id, true)
        setSchema(attributes.filter((attribute) => attribute.is_active))
        setCategoryId(product.category_id)
        setName(product.name)
        setSku(product.sku)
        setBarcode(product.barcode ?? "")
        setCode(product.code ?? "")
        setDescription(product.description ?? "")
        setStatus(product.status)
        setBaseUnitId(product.base_unit_id ?? "")
        setSellingUnitId(product.selling_unit_id)
        setNetQuantity(product.net_quantity ?? "")
        setNetQuantityUnitId(product.net_quantity_unit_id ?? "")
        setCostPrice(product.cost_price)
        setSellingPrice(product.selling_price)
        setQuantityUnitPrice(product.quantity_unit_price)
        setCurrencyCode(product.currency_code)
        setProductValues(Object.fromEntries(product.attribute_values.map((item) => [item.attribute_id, item.value])))
      })
      .catch((reason: Error) => setError(reason.message))
  }, [productId])

  async function onCategoryChange(nextCategoryId: string) {
    setCategoryId(nextCategoryId)
    setError(null)
    if (!nextCategoryId) {
      setSchema([])
      return
    }
    try {
      const attributes = (await listAttributes(nextCategoryId, true)).filter((attribute) => attribute.is_active)
      setSchema(attributes)
      const attributeIds = new Set(attributes.map((attribute) => attribute.id))
      setProductValues((current) => pick(current, attributeIds))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load category fields")
    }
  }

  const flat = flattenCategories(categories)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    if (!categoryId) {
      setError("Choose a category")
      return
    }
    if (!sellingUnitId) {
      setError("Choose a selling unit")
      return
    }
    setSaving(true)
    try {
      const saved = await saveProduct(
        {
          category_id: categoryId,
          name,
          sku,
          barcode: barcode || null,
          code: code || null,
          description: description || null,
          status,
          base_unit_id: baseUnitId || null,
          selling_unit_id: sellingUnitId,
          net_quantity: netQuantity || null,
          net_quantity_unit_id: netQuantityUnitId || null,
          cost_price: costPrice,
          selling_price: sellingPrice,
          quantity_unit_price: quantityUnitPrice || "0",
          currency_code: currencyCode || "PKR",
          attribute_values: toValueList(schema, productValues),
        },
        productId,
      )
      navigate(`/products/${saved.id}`)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save the product")
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto max-w-5xl">
      <PageHeader
        title={productId ? "Edit product" : "New product"}
        lede="The category is part of this form. Selecting it shows that category's fields. Nothing is saved until you submit the product."
        action={
          <Link className="btn-ghost" to="/products">
            Back
          </Link>
        }
      />
      <ErrorNote message={error} />
      <Card className="mb-6 grid gap-4 p-4 md:grid-cols-2">
        <div className="md:col-span-2">
          <h2 className="font-display text-xl text-ink">Identity</h2>
        </div>
        <Field label="Category">
          <select className="field" value={categoryId} onChange={(event) => void onCategoryChange(event.target.value)}>
            <option value="">Select a category</option>
            {flat.map((category) => (
              <option key={category.id} value={category.id}>
                {"— ".repeat(category.depth)}
                {category.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Name">
          <input className="field" value={name} onChange={(event) => setName(event.target.value)} required />
        </Field>
        <Field label="SKU">
          <input className="field" value={sku} onChange={(event) => setSku(event.target.value)} required />
        </Field>
        <Field label="Code">
          <input className="field" value={code} onChange={(event) => setCode(event.target.value)} />
        </Field>
        <Field label="Barcode">
          <input className="field" value={barcode} onChange={(event) => setBarcode(event.target.value)} />
        </Field>
        <Field label="Status">
          <select className="field" value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="draft">Draft</option>
            <option value="active">Active</option>
            <option value="archived">Archived</option>
          </select>
        </Field>
        <div className="md:col-span-2 border-t border-line pt-4">
          <h2 className="font-display text-xl text-ink">Units and pricing</h2>
        </div>
        <Field label="Selling unit">
          <select className="field" value={sellingUnitId} onChange={(event) => setSellingUnitId(event.target.value)} required>
            <option value="">Select a unit</option>
            {units.map((unit) => (
              <option key={unit.id} value={unit.id}>
                {unit.name} ({unit.symbol})
              </option>
            ))}
          </select>
        </Field>
        <Field label="Selling price">
          <input className="field" value={sellingPrice} onChange={(event) => setSellingPrice(event.target.value)} required />
        </Field>
        <Field label="Quantity unit">
          <select className="field" value={netQuantityUnitId} onChange={(event) => setNetQuantityUnitId(event.target.value)}>
            <option value="">None</option>
            {units.map((unit) => (
              <option key={unit.id} value={unit.id}>
                {unit.name} ({unit.symbol})
              </option>
            ))}
          </select>
        </Field>
        <Field label="Quantity units in one selling unit">
          <input className="field" value={netQuantity} onChange={(event) => setNetQuantity(event.target.value)} />
        </Field>
        <Field label="Quantity unit price">
          <input className="field" value={quantityUnitPrice} onChange={(event) => setQuantityUnitPrice(event.target.value)} />
        </Field>
        <Field label="Cost price">
          <input className="field" value={costPrice} onChange={(event) => setCostPrice(event.target.value)} required />
        </Field>
        <Field label="Currency">
          <input className="field" value={currencyCode} onChange={(event) => setCurrencyCode(event.target.value)} required />
        </Field>
        <div className="md:col-span-2">
          <Field label="Description">
            <textarea className="field min-h-24" value={description} onChange={(event) => setDescription(event.target.value)} />
          </Field>
        </div>
      </Card>
      <Card className="mb-6 p-4">
        <h2 className="mb-3 font-display text-xl">Specifications</h2>
        {categoryId ? (
          <DynamicAttributeFields
            attributes={schema}
            values={productValues}
            onChange={(attributeId, value) => setProductValues((current) => ({ ...current, [attributeId]: value }))}
          />
        ) : (
          <p className="text-sm text-stone-500">Select a category to show its fields.</p>
        )}
      </Card>
      <button className="btn" type="submit" disabled={saving}>
        {saving ? "Saving…" : "Save product"}
      </button>
    </form>
  )
}
