import { useEffect, useState, type FormEvent } from "react"
import { Link, useParams } from "react-router-dom"
import {
  createAttribute,
  createOption,
  deleteAttribute,
  deleteOption,
  listAttributes,
  listCategories,
  updateAttribute,
} from "../../api/resources"
import type { Attribute, AttributeScope, DataType } from "../../api/types"
import { ErrorNote, Field, PageHeader } from "../../components/ui"
import { flattenCategories } from "../../lib/tree"

const DATA_TYPES: DataType[] = ["text", "number", "boolean", "date", "single_select", "multi_select"]

export function AttributesPage() {
  const { categoryId = "" } = useParams()
  const [attributes, setAttributes] = useState<Attribute[]>([])
  const [categoryName, setCategoryName] = useState("Category")
  const [error, setError] = useState<string | null>(null)
  const [name, setName] = useState("")
  const [code, setCode] = useState("")
  const [dataType, setDataType] = useState<DataType>("text")
  const [scope, setScope] = useState<AttributeScope>("product")
  const [required, setRequired] = useState(false)
  const [optionLabel, setOptionLabel] = useState<Record<string, string>>({})

  async function reload() {
    const [rows, tree] = await Promise.all([listAttributes(categoryId), listCategories()])
    setAttributes(rows)
    const match = flattenCategories(tree).find((category) => category.id === categoryId)
    setCategoryName(match?.name ?? "Category")
  }

  useEffect(() => {
    if (!categoryId) {
      return
    }
    reload().catch((reason: Error) => setError(reason.message))
  }, [categoryId])

  async function onCreate(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await createAttribute(categoryId, {
        name,
        code: code || null,
        data_type: dataType,
        scope,
        is_required: required,
        is_filterable: true,
        inherit_to_children: true,
      })
      setName("")
      setCode("")
      setRequired(false)
      await reload()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save the attribute")
    }
  }

  const own = attributes.filter((attribute) => !attribute.inherited)
  const inherited = attributes.filter((attribute) => attribute.inherited)

  return (
    <div>
      <PageHeader
        title={`${categoryName} attributes`}
        lede="Fields defined here appear on the product form when this category is selected."
        action={
          <Link className="btn-ghost" to="/categories">
            Back to categories
          </Link>
        }
      />
      <ErrorNote message={error} />
      <form onSubmit={onCreate} className="mb-6 grid gap-3 rounded-lg border border-line bg-white p-4 md:grid-cols-5">
        <Field label="Name">
          <input className="field" value={name} onChange={(event) => setName(event.target.value)} required />
        </Field>
        <Field label="Code">
          <input className="field" value={code} onChange={(event) => setCode(event.target.value)} placeholder="auto" />
        </Field>
        <Field label="Type">
          <select className="field" value={dataType} onChange={(event) => setDataType(event.target.value as DataType)}>
            {DATA_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Applies to">
          <select className="field" value={scope} onChange={(event) => setScope(event.target.value as AttributeScope)}>
            <option value="product">Product</option>
            <option value="variant">Variant</option>
          </select>
        </Field>
        <div className="flex items-end gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={required} onChange={(event) => setRequired(event.target.checked)} />
            Required
          </label>
          <button className="btn" type="submit">
            Add
          </button>
        </div>
      </form>
      <section className="mb-8">
        <h2 className="mb-3 font-display text-xl">On this category</h2>
        <AttributeList
          attributes={own}
          optionLabel={optionLabel}
          setOptionLabel={setOptionLabel}
          onChanged={reload}
          onError={setError}
        />
      </section>
      <section>
        <h2 className="mb-3 font-display text-xl">Inherited</h2>
        {inherited.length === 0 ? <p className="text-sm text-stone-500">No inherited attributes.</p> : null}
        <div className="space-y-2">
          {inherited.map((attribute) => (
            <article key={attribute.id} className="rounded-lg border border-dashed border-line bg-white px-4 py-3 text-sm">
              <p className="font-semibold">
                {attribute.name} <span className="font-mono text-xs text-stone-500">{attribute.code}</span>
              </p>
              <p className="text-stone-500">
                From {attribute.owner_category_name} · {attribute.scope} · {attribute.data_type}
                {attribute.is_active ? "" : " · inactive"}
              </p>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}

function AttributeList({
  attributes,
  optionLabel,
  setOptionLabel,
  onChanged,
  onError,
}: {
  attributes: Attribute[]
  optionLabel: Record<string, string>
  setOptionLabel: (value: Record<string, string>) => void
  onChanged: () => Promise<void>
  onError: (message: string) => void
}) {
  if (attributes.length === 0) {
    return <p className="text-sm text-stone-500">No attributes on this category yet.</p>
  }
  return (
    <div className="space-y-3">
      {attributes.map((attribute) => (
        <article key={attribute.id} className="rounded-lg border border-line bg-white p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="font-semibold">
                {attribute.name} <span className="font-mono text-xs text-stone-500">{attribute.code}</span>
              </p>
              <p className="text-sm text-stone-500">
                {attribute.scope} · {attribute.data_type}
                {attribute.is_required ? " · required" : ""}
                {attribute.is_active ? "" : " · inactive"}
              </p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                className="btn-ghost"
                onClick={() =>
                  updateAttribute(attribute.id, { is_active: !attribute.is_active })
                    .then(onChanged)
                    .catch((reason: Error) => onError(reason.message))
                }
              >
                {attribute.is_active ? "Deactivate" : "Activate"}
              </button>
              <button
                type="button"
                className="btn-danger"
                onClick={() =>
                  deleteAttribute(attribute.id)
                    .then(onChanged)
                    .catch((reason: Error) => onError(reason.message))
                }
              >
                Delete
              </button>
            </div>
          </div>
          {attribute.data_type === "single_select" || attribute.data_type === "multi_select" ? (
            <div className="mt-3">
              <ul className="mb-2 flex flex-wrap gap-2">
                {attribute.options.map((option) => (
                  <li key={option.id} className="flex items-center gap-2 rounded-full bg-paper px-3 py-1 text-sm">
                    {option.label}
                    <button
                      type="button"
                      className="text-stone-500"
                      onClick={() =>
                        deleteOption(option.id)
                          .then(onChanged)
                          .catch((reason: Error) => onError(reason.message))
                      }
                    >
                      ×
                    </button>
                  </li>
                ))}
              </ul>
              <form
                className="flex gap-2"
                onSubmit={(event) => {
                  event.preventDefault()
                  const label = optionLabel[attribute.id]?.trim()
                  if (!label) {
                    return
                  }
                  createOption(attribute.id, { label })
                    .then(async () => {
                      setOptionLabel({ ...optionLabel, [attribute.id]: "" })
                      await onChanged()
                    })
                    .catch((reason: Error) => onError(reason.message))
                }}
              >
                <input
                  className="field"
                  placeholder="New option"
                  value={optionLabel[attribute.id] ?? ""}
                  onChange={(event) => setOptionLabel({ ...optionLabel, [attribute.id]: event.target.value })}
                />
                <button className="btn-ghost" type="submit">
                  Add option
                </button>
              </form>
            </div>
          ) : null}
        </article>
      ))}
    </div>
  )
}
