import { useEffect, useState, type FormEvent } from "react"
import { createUnit, deleteUnit, listUnits, updateUnit } from "../../api/resources"
import type { Unit } from "../../api/types"
import { ErrorNote, Field, PageHeader } from "../../components/ui"

const UNIT_TYPES = ["weight", "volume", "length", "area", "count", "packaging"]

export function UnitsPage() {
  const [units, setUnits] = useState<Unit[]>([])
  const [error, setError] = useState<string | null>(null)
  const [name, setName] = useState("")
  const [symbol, setSymbol] = useState("")
  const [unitType, setUnitType] = useState("count")

  async function reload() {
    const page = await listUnits(true)
    setUnits(page.items)
  }

  useEffect(() => {
    reload().catch((reason: Error) => setError(reason.message))
  }, [])

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

  return (
    <div>
      <PageHeader title="Units" lede="Selling units and the units used by category attributes." />
      <ErrorNote message={error} />
      <form onSubmit={onCreate} className="mb-6 grid gap-3 rounded-lg border border-line bg-white p-4 md:grid-cols-4">
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
      </form>
      <div className="overflow-hidden rounded-lg border border-line bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-stone-100 text-xs uppercase tracking-wide text-stone-500">
            <tr>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Symbol</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {units.map((unit) => (
              <tr key={unit.id} className="border-t border-line">
                <td className="px-4 py-3">{unit.name}</td>
                <td className="px-4 py-3 font-mono">{unit.symbol}</td>
                <td className="px-4 py-3">{unit.unit_type}</td>
                <td className="px-4 py-3">{unit.is_active ? "Active" : "Inactive"}</td>
                <td className="px-4 py-3 text-right">
                  <button
                    type="button"
                    className="btn-ghost mr-2"
                    onClick={() =>
                      updateUnit(unit.id, { is_active: !unit.is_active })
                        .then(reload)
                        .catch((reason: Error) => setError(reason.message))
                    }
                  >
                    {unit.is_active ? "Deactivate" : "Activate"}
                  </button>
                  <button
                    type="button"
                    className="btn-danger"
                    onClick={() =>
                      deleteUnit(unit.id)
                        .then(reload)
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
