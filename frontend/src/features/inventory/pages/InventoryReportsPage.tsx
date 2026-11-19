import { useEffect, useState } from "react"
import { getReport, reportCsvPath, type ReportTable } from "../../../api/inventory"
import { ErrorNote, Field, PageHeader } from "../../../components/ui"

const reports = [
  { id: "summary", label: "Stock summary" },
  { id: "movements", label: "Stock movements" },
  { id: "valuation", label: "Valuation" },
  { id: "low-stock", label: "Low stock" },
  { id: "out-of-stock", label: "Out of stock" },
]

export function InventoryReportsPage() {
  const [report, setReport] = useState("summary")
  const [q, setQ] = useState("")
  const [dateFrom, setDateFrom] = useState("")
  const [dateTo, setDateTo] = useState("")
  const [table, setTable] = useState<ReportTable | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const params = {
    q: report === "low-stock" || report === "out-of-stock" ? undefined : q,
    date_from: report === "movements" ? dateFrom : undefined,
    date_to: report === "movements" ? dateTo : undefined,
  }

  function load() {
    setLoading(true)
    return getReport(report, params)
      .then(setTable)
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load().catch((reason: Error) => {
      setError(reason.message)
      setLoading(false)
    })
  }, [report])

  return (
    <div>
      <PageHeader
        title="Inventory reports"
        lede="Summary, movements, valuation, and the products that need attention."
        action={
          <a className="btn-ghost" href={reportCsvPath(report, params)}>
            Download CSV
          </a>
        }
      />
      <ErrorNote message={error} />
      <form
        className="mb-6 grid gap-3 rounded-lg border border-line bg-white p-4 md:grid-cols-4"
        onSubmit={(event) => {
          event.preventDefault()
          load().catch((reason: Error) => setError(reason.message))
        }}
      >
        <Field label="Report">
          <select className="field" value={report} onChange={(event) => setReport(event.target.value)}>
            {reports.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Search">
          <input className="field" value={q} onChange={(event) => setQ(event.target.value)} />
        </Field>
        <Field label="From">
          <input className="field" type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} disabled={report !== "movements"} />
        </Field>
        <div className="flex items-end gap-2">
          <Field label="To">
            <input className="field" type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} disabled={report !== "movements"} />
          </Field>
          <button className="btn mb-0" type="submit">
            Apply
          </button>
        </div>
      </form>
      <div className="overflow-x-auto rounded-lg border border-line bg-white">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="bg-stone-100 text-xs uppercase tracking-wide text-stone-500">
            <tr>
              {table?.header.map((heading) => (
                <th key={heading} className="px-4 py-3">
                  {heading}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td className="px-4 py-6 text-stone-500">Loading report…</td>
              </tr>
            ) : !table || table.rows.length === 0 ? (
              <tr>
                <td className="px-4 py-6 text-stone-500">Nothing to report.</td>
              </tr>
            ) : (
              table.rows.map((row, index) => (
                <tr key={index} className="border-t border-line">
                  {row.map((cell, cellIndex) => (
                    <td key={cellIndex} className="px-4 py-3">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
