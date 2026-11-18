import { useEffect, useState, type FormEvent } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { getProduct, listAttributes, listCategories, listUnits, saveProduct } from "../../api/resources"
import type { Attribute, CategoryNode, Unit } from "../../api/types"
import { DynamicAttributeFields } from "../../components/forms/DynamicAttributeFields"
import { ErrorNote, Field, PageHeader } from "../../components/ui"
import { VariantEditor, emptyVariant, type VariantDraft } from "../variants/VariantEditor"
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
  const [code, setCode] = useState("")
  const [description, setDescription] = useState("")
  const [status, setStatus] = useState("draft")
  const [baseUnitId, setBaseUnitId] = useState("")
  const [productValues, setProductValues] = useState<Record<string, unknown>>({})
  const [variants, setVariants] = useState<VariantDraft[]>([emptyVariant()])
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
        setCode(product.code ?? "")
        setDescription(product.description ?? "")
        setStatus(product.status)
        setBaseUnitId(product.base_unit_id ?? "")
        setProductValues(Object.fromEntries(product.attribute_values.map((item) => [item.attribute_id, item.value])))
        setVariants(
          product.variants.map((variant) => ({
            sku: variant.sku,
            barcode: variant.barcode ?? "",
            name: variant.name ?? "",
            selling_unit_id: variant.selling_unit_id,
            net_quantity: variant.net_quantity ?? "",
            net_quantity_unit_id: variant.net_quantity_unit_id ?? "",
            cost_price: variant.cost_price,
            selling_price: variant.selling_price,
            currency_code: variant.currency_code,
            is_active: variant.is_active,
            values: Object.fromEntries(variant.attribute_values.map((item) => [item.attribute_id, item.value])),
          })),
        )
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
      const productIds = new Set(attributes.filter((attribute) => attribute.scope === "product").map((attribute) => attribute.id))
      const variantIds = new Set(attributes.filter((attribute) => attribute.scope === "variant").map((attribute) => attribute.id))
      setProductValues((current) => pick(current, productIds))
      setVariants((current) => current.map((variant) => ({ ...variant, values: pick(variant.values, variantIds) })))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load category fields")
    }
  }

  const productAttributes = schema.filter((attribute) => attribute.scope === "product")
  const variantAttributes = schema.filter((attribute) => attribute.scope === "variant")
  const flat = flattenCategories(categories)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    if (!categoryId) {
      setError("Choose a category")
      return
    }
    setSaving(true)
    try {
      const saved = await saveProduct(
        {
          category_id: categoryId,
          name,
          code: code || null,
          description: description || null,
          status,
          base_unit_id: baseUnitId || null,
          attribute_values: toValueList(productAttributes, productValues),
          variants: variants.map((variant, index) => ({
            sku: variant.sku,
            barcode: variant.barcode || null,
            name: variant.name || null,
            selling_unit_id: variant.selling_unit_id,
            net_quantity: variant.net_quantity || null,
            net_quantity_unit_id: variant.net_quantity_unit_id || null,
            cost_price: variant.cost_price,
            selling_price: variant.selling_price,
            currency_code: variant.currency_code || "PKR",
            is_active: variant.is_active,
            sort_order: index,
            attribute_values: toValueList(variantAttributes, variant.values),
          })),
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
      <section className="mb-6 grid gap-4 rounded-lg border border-line bg-white p-4 md:grid-cols-2">
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
        <Field label="Code">
          <input className="field" value={code} onChange={(event) => setCode(event.target.value)} />
        </Field>
        <Field label="Status">
          <select className="field" value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="draft">Draft</option>
            <option value="active">Active</option>
            <option value="archived">Archived</option>
          </select>
        </Field>
        <Field label="Base unit">
          <select className="field" value={baseUnitId} onChange={(event) => setBaseUnitId(event.target.value)}>
            <option value="">None</option>
            {units.map((unit) => (
              <option key={unit.id} value={unit.id}>
                {unit.name} ({unit.symbol})
              </option>
            ))}
          </select>
        </Field>
        <div className="md:col-span-2">
          <Field label="Description">
            <textarea className="field min-h-24" value={description} onChange={(event) => setDescription(event.target.value)} />
          </Field>
        </div>
      </section>
      <section className="mb-6 rounded-lg border border-line bg-white p-4">
        <h2 className="mb-3 font-display text-xl">Specifications</h2>
        {categoryId ? (
          <DynamicAttributeFields
            attributes={productAttributes}
            values={productValues}
            onChange={(attributeId, value) => setProductValues((current) => ({ ...current, [attributeId]: value }))}
          />
        ) : (
          <p className="text-sm text-stone-500">Select a category to show its fields.</p>
        )}
      </section>
      <section className="mb-6">
        <h2 className="mb-3 font-display text-xl">Variants</h2>
        <VariantEditor variants={variants} units={units} attributes={variantAttributes} onChange={setVariants} />
      </section>
      <button className="btn" type="submit" disabled={saving}>
        {saving ? "Saving…" : "Save product"}
      </button>
    </form>
  )
}
