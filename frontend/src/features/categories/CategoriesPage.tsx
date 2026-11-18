import { useEffect, useState, type FormEvent } from "react"
import { Link } from "react-router-dom"
import { createCategory, deleteCategory, listCategories, updateCategory } from "../../api/resources"
import type { CategoryNode } from "../../api/types"
import { ErrorNote, Field, PageHeader } from "../../components/ui"
import { flattenCategories } from "../../lib/tree"

export function CategoriesPage() {
  const [tree, setTree] = useState<CategoryNode[]>([])
  const [error, setError] = useState<string | null>(null)
  const [name, setName] = useState("")
  const [parentId, setParentId] = useState("")
  const [description, setDescription] = useState("")

  async function reload() {
    setTree(await listCategories())
  }

  useEffect(() => {
    reload().catch((reason: Error) => setError(reason.message))
  }, [])

  const flat = flattenCategories(tree)

  async function onCreate(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await createCategory({
        name,
        parent_id: parentId || null,
        description: description || null,
      })
      setName("")
      setDescription("")
      await reload()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save the category")
    }
  }

  return (
    <div>
      <PageHeader title="Categories" lede="Parent categories can pass their attributes down to children." />
      <ErrorNote message={error} />
      <form onSubmit={onCreate} className="mb-6 grid gap-3 rounded-lg border border-line bg-white p-4 md:grid-cols-4">
        <Field label="Name">
          <input className="field" value={name} onChange={(event) => setName(event.target.value)} required />
        </Field>
        <Field label="Parent">
          <select className="field" value={parentId} onChange={(event) => setParentId(event.target.value)}>
            <option value="">None</option>
            {flat.map((category) => (
              <option key={category.id} value={category.id}>
                {"— ".repeat(category.depth)}
                {category.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Description">
          <input className="field" value={description} onChange={(event) => setDescription(event.target.value)} />
        </Field>
        <div className="flex items-end">
          <button className="btn" type="submit">
            Add category
          </button>
        </div>
      </form>
      <CategoryTree
        nodes={tree}
        onChanged={reload}
        onError={(message) => setError(message)}
      />
    </div>
  )
}

function CategoryTree({
  nodes,
  depth = 0,
  onChanged,
  onError,
}: {
  nodes: CategoryNode[]
  depth?: number
  onChanged: () => Promise<void>
  onError: (message: string) => void
}) {
  if (nodes.length === 0 && depth === 0) {
    return <p className="text-sm text-stone-500">No categories yet.</p>
  }
  return (
    <ul className={depth === 0 ? "space-y-2" : "mt-2 space-y-2 border-l border-line pl-4"}>
      {nodes.map((node) => (
        <li key={node.id} className="rounded-lg border border-line bg-white px-4 py-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-semibold">{node.name}</p>
              {/* <p className="font-mono text-xs text-stone-500">{node.path}</p> */}
            </div>
            <div className="flex gap-2">
              <Link className="btn-ghost" to={`/categories/${node.id}/attributes`}>
                Attributes
              </Link>
              <button
                type="button"
                className="btn-ghost"
                onClick={() => {
                  const next = window.prompt("Category name", node.name)
                  if (!next || next === node.name) {
                    return
                  }
                  updateCategory(node.id, { name: next })
                    .then(onChanged)
                    .catch((reason: Error) => onError(reason.message))
                }}
              >
                Rename
              </button>
              <button
                type="button"
                className="btn-danger"
                onClick={() =>
                  deleteCategory(node.id)
                    .then(onChanged)
                    .catch((reason: Error) => onError(reason.message))
                }
              >
                Delete
              </button>
            </div>
          </div>
          {node.children.length > 0 ? (
            <CategoryTree nodes={node.children} depth={depth + 1} onChanged={onChanged} onError={onError} />
          ) : null}
        </li>
      ))}
    </ul>
  )
}
