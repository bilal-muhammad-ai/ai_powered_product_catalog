import { useMemo, useState, useEffect, type FormEvent } from "react"
import { Link } from "react-router-dom"
import { createCategory, deleteCategory, listCategories, updateCategory } from "../../api/resources"
import type { CategoryNode } from "../../api/types"
import { Badge, Button, Card, ConfirmationDialog, ErrorNote, Field, Modal, PageHeader, SearchInput } from "../../components/ui"

export function CategoriesPage() {
  const [tree, setTree] = useState<CategoryNode[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [name, setName] = useState("")
  const [parentId, setParentId] = useState("")
  const [description, setDescription] = useState("")
  const [query, setQuery] = useState("")
  const [editing, setEditing] = useState<{ id: string; name: string } | null>(null)
  const [pendingDelete, setPendingDelete] = useState<CategoryNode | null>(null)

  async function reload() {
    setTree(await listCategories())
    setLoading(false)
  }

  useEffect(() => {
    reload().catch((reason: Error) => {
      setError(reason.message)
      setLoading(false)
    })
  }, [])

  const flat = flattenAll(tree)
  const visible = useMemo(() => filterTree(tree, query), [tree, query])

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

  async function saveName() {
    if (!editing) return
    const next = editing.name.trim()
    if (!next) return
    setError(null)
    try {
      await updateCategory(editing.id, { name: next })
      setEditing(null)
      await reload()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not rename the category")
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return
    setError(null)
    try {
      await deleteCategory(pendingDelete.id)
      setPendingDelete(null)
      await reload()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not delete the category")
      setPendingDelete(null)
    }
  }

  return (
    <div>
      <PageHeader title="Categories" lede="Parent categories can pass their attributes down to children." />
      <ErrorNote message={error} />
      <form onSubmit={onCreate}>
        <Card className="mb-6 grid gap-3 p-4 md:grid-cols-4">
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
        </Card>
      </form>
      <Card className="mb-4 p-4">
        <SearchInput label="Find in this list" value={query} onChange={setQuery} placeholder="Category name" />
      </Card>
      {loading ? <p className="text-sm text-stone-500">Loading categories…</p> : null}
      {!loading && visible.length === 0 ? <p className="text-sm text-stone-500">No categories yet.</p> : null}
      <CategoryTree nodes={visible} onRename={setEditing} onDelete={setPendingDelete} />
      {editing ? (
        <Modal title="Rename category" onClose={() => setEditing(null)}>
          <form
            onSubmit={(event) => {
              event.preventDefault()
              void saveName()
            }}
          >
            <Field label="Name">
              <input className="field" value={editing.name} onChange={(event) => setEditing({ ...editing, name: event.target.value })} required />
            </Field>
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setEditing(null)}>
                Back
              </Button>
              <Button type="submit">Save</Button>
            </div>
          </form>
        </Modal>
      ) : null}
      {pendingDelete ? (
        <ConfirmationDialog
          title="Delete category"
          message={`Delete ${pendingDelete.name}? Child categories must be removed first if the catalogue requires it.`}
          confirmLabel="Delete"
          tone="danger"
          onClose={() => setPendingDelete(null)}
          onConfirm={() => void confirmDelete()}
        />
      ) : null}
    </div>
  )
}

function CategoryTree({
  nodes,
  depth = 0,
  onRename,
  onDelete,
}: {
  nodes: CategoryNode[]
  depth?: number
  onRename: (category: { id: string; name: string }) => void
  onDelete: (category: CategoryNode) => void
}) {
  if (nodes.length === 0) return null
  return (
    <ul className={depth === 0 ? "space-y-3" : "mt-3 space-y-3 border-l border-line pl-4"}>
      {nodes.map((node) => (
        <li key={node.id}>
          <Card className="px-4 py-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-medium text-ink">{node.name}</p>
                  <Badge tone={node.is_active ? "pine" : "neutral"}>{node.is_active ? "Active" : "Inactive"}</Badge>
                  <Badge>{node.children.length} children</Badge>
                </div>
                {node.description ? <p className="mt-1 text-sm text-stone-600">{node.description}</p> : null}
              </div>
              <div className="flex flex-wrap gap-2">
                <Link className="btn-ghost" to={`/categories/${node.id}/attributes`}>
                  Attributes
                </Link>
                <Button variant="ghost" onClick={() => onRename({ id: node.id, name: node.name })}>
                  Rename
                </Button>
                <Button variant="danger" onClick={() => onDelete(node)}>
                  Delete
                </Button>
              </div>
            </div>
          </Card>
          {node.children.length > 0 ? <CategoryTree nodes={node.children} depth={depth + 1} onRename={onRename} onDelete={onDelete} /> : null}
        </li>
      ))}
    </ul>
  )
}

function flattenAll(nodes: CategoryNode[], depth = 0): { id: string; name: string; depth: number }[] {
  return nodes.flatMap((node) => [{ id: node.id, name: node.name, depth }, ...flattenAll(node.children, depth + 1)])
}

function filterTree(nodes: CategoryNode[], query: string): CategoryNode[] {
  const text = query.trim().toLowerCase()
  if (!text) return nodes
  return nodes.flatMap((node) => {
    const children = filterTree(node.children, query)
    if (node.name.toLowerCase().includes(text)) return [{ ...node, children: node.children }]
    if (children.length > 0) return [{ ...node, children }]
    return []
  })
}
