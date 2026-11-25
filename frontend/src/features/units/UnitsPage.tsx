import { useMemo, useState, useEffect, type FormEvent } from "react"
import { createUnit, deleteUnit, listUnits, updateUnit } from "../../api/resources"
import type { Unit } from "../../api/types"
import {
  Badge,
  Button,
  Card,
  ConfirmationDialog,
  DataTable,
  ErrorNote,
  Field,
  Modal,
  PageHeader,
  SearchInput,
  tableCellClass,
  tableHeadClass,
} from "../../components/ui"

const UNIT_TYPES = ["weight", "volume", "length", "area", "count", "packaging"]

export function UnitsPage() {
  const [units, setUnits] = useState<Unit[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState("")
  const [name, setName] = useState("")
  const [symbol, setSymbol] = useState("")
  const [unitType, setUnitType] = useState("count")
  const [editing, setEditing] = useState<Unit | null>(null)
  const [pendingDelete, setPendingDelete] = useState<Unit | null>(null)

  async function reload() {
    const page = await listUnits(true)
    setUnits(page.items)
    setLoading(false)
  }

  useEffect(() => {
    reload().catch((reason: Error) => {
      setError(reason.message)
      setLoading(false)
    })
  }, [])

  const visible = useMemo(() => {
    const text = query.trim().toLowerCase()
    if (!text) return units
    return units.filter((unit) => unit.name.toLowerCase().includes(text) || unit.symbol.toLowerCase().includes(text))
  }, [units, query])

  async function onCreate(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await createUnit({ name, symbol, unit_type: unitType, is_active: true })
      setName("")
      setSymbol("")
      await reload()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save the unit")
    }
  }

  async function saveEdit(event: FormEvent) {
    event.preventDefault()
    if (!editing) return
    setError(null)
    try {
      await updateUnit(editing.id, { name: editing.name, symbol: editing.symbol, unit_type: editing.unit_type })
      setEditing(null)
      await reload()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not update the unit")
    }
  }

  async function toggle(unit: Unit) {
    setError(null)
    try {
      await updateUnit(unit.id, { is_active: !unit.is_active })
      await reload()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not update the unit")
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return
    setError(null)
    try {
      await deleteUnit(pendingDelete.id)
      setPendingDelete(null)
      await reload()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not delete the unit")
      setPendingDelete(null)
    }
  }

  return (
    <div>
      <PageHeader title="Units" lede="Selling units and the units used by category attributes." />
      <ErrorNote message={error} />
      <form onSubmit={onCreate}>
        <Card className="mb-6 grid gap-3 p-4 md:grid-cols-4">
          <Field label="Name">
            <input className="field" value={name} onChange={(event) => setName(event.target.value)} required />
          </Field>
          <Field label="Symbol">
            <input className="field" value={symbol} onChange={(event) => setSymbol(event.target.value)} required />
          </Field>
          <Field label="Type">
            <select className="field" value={unitType} onChange={(event) => setUnitType(event.target.value)}>
              {UNIT_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </Field>
          <div className="flex items-end">
            <button className="btn" type="submit">
              Add unit
            </button>
          </div>
        </Card>
      </form>
      <Card className="mb-4 p-4">
        <SearchInput label="Find in this list" value={query} onChange={setQuery} placeholder="Name or symbol" />
      </Card>
      <DataTable>
        <thead className={tableHeadClass}>
          <tr>
            <th className={tableCellClass}>Name</th>
            <th className={tableCellClass}>Symbol</th>
            <th className={tableCellClass}>Type</th>
            <th className={tableCellClass}>Status</th>
            <th className={tableCellClass}>
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td className={`${tableCellClass} text-stone-500`} colSpan={5}>
                Loading units…
              </td>
            </tr>
          ) : visible.length === 0 ? (
            <tr>
              <td className={`${tableCellClass} text-stone-500`} colSpan={5}>
                No units match.
              </td>
            </tr>
          ) : (
            visible.map((unit) => (
              <tr key={unit.id} className="border-t border-line">
                <td className={tableCellClass}>{unit.name}</td>
                <td className={`${tableCellClass} font-mono`}>{unit.symbol}</td>
                <td className={`${tableCellClass} capitalize`}>{unit.unit_type}</td>
                <td className={tableCellClass}>
                  <Badge tone={unit.is_active ? "pine" : "neutral"}>{unit.is_active ? "Active" : "Inactive"}</Badge>
                </td>
                <td className={`${tableCellClass} text-right`}>
                  <Button variant="ghost" className="mr-2" onClick={() => setEditing(unit)}>
                    Edit
                  </Button>
                  <Button variant="ghost" className="mr-2" onClick={() => void toggle(unit)}>
                    {unit.is_active ? "Deactivate" : "Activate"}
                  </Button>
                  <Button variant="danger" onClick={() => setPendingDelete(unit)}>
                    Delete
                  </Button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </DataTable>
      {editing ? (
        <Modal title="Edit unit" onClose={() => setEditing(null)}>
          <form onSubmit={(event) => void saveEdit(event)}>
            <div className="grid gap-3">
              <Field label="Name">
                <input className="field" value={editing.name} onChange={(event) => setEditing({ ...editing, name: event.target.value })} required />
              </Field>
              <Field label="Symbol">
                <input className="field" value={editing.symbol} onChange={(event) => setEditing({ ...editing, symbol: event.target.value })} required />
              </Field>
              <Field label="Type">
                <select className="field" value={editing.unit_type} onChange={(event) => setEditing({ ...editing, unit_type: event.target.value })}>
                  {UNIT_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </Field>
            </div>
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
          title="Delete unit"
          message={`Delete ${pendingDelete.name}? Products already using it may keep the existing reference.`}
          confirmLabel="Delete"
          tone="danger"
          onClose={() => setPendingDelete(null)}
          onConfirm={() => void confirmDelete()}
        />
      ) : null}
    </div>
  )
}
