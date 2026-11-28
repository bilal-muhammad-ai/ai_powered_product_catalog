import { useEffect, useState } from "react"
import { getReport, reportCsvPath, type ReportTable } from "../../../api/inventory"
import { Card, DataTable, ErrorNote, Field, PageHeader, SearchInput, tableCellClass, tableHeadClass } from "../../../components/ui"

const reports = [
  { id: "summary", label: "Stock summary" },
  { id: "movements", label: "Stock movements" },
  { id: "valuation", label: "Valuation" },
  { id: "low-stock", label: "Low stock" },
  { id: "out-of-stock", label: "Out of stock" },
]

type ReportFilters = {
  report: string
  q: string
  dateFrom: string
  dateTo: string
}

const defaultReportFilters: ReportFilters = {
  report: "summary",
  q: "",
  dateFrom: "",
  dateTo: "",
}

function reportQuery(filters: ReportFilters) {
  return {
    q: filters.report === "low-stock" || filters.report === "out-of-stock" ? undefined : filters.q,
    date_from: filters.report === "movements" ? filters.dateFrom : undefined,
    date_to: filters.report === "movements" ? filters.dateTo : undefined,
  }
}

export function InventoryReportsPage() {
  const [report, setReport] = useState("summary")
  const [q, setQ] = useState("")
  const [dateFrom, setDateFrom] = useState("")
  const [dateTo, setDateTo] = useState("")
  const [table, setTable] = useState<ReportTable | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const filters = { report, q, dateFrom, dateTo }
  const params = reportQuery(filters)

  function load(next: ReportFilters = filters) {
    setLoading(true)
    return getReport(next.report, reportQuery(next))
      .then(setTable)
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load().catch((reason: Error) => {
      setError(reason.message)
      setLoading(false)
    })
  }, [report])

  function clearFilters() {
    setReport(defaultReportFilters.report)
    setQ(defaultReportFilters.q)
    setDateFrom(defaultReportFilters.dateFrom)
    setDateTo(defaultReportFilters.dateTo)
    load(defaultReportFilters).catch((reason: Error) => {
      setError(reason.message)
      setLoading(false)
    })
  }

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
        onSubmit={(event) => {
          event.preventDefault()
          load().catch((reason: Error) => setError(reason.message))
        }}
      >
        <Card className="mb-6 grid gap-3 p-4 md:grid-cols-4">
        <Field label="Report">
          <select className="field" value={report} onChange={(event) => setReport(event.target.value)}>
            {reports.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </Field>
        <SearchInput label="Search" value={q} onChange={setQ} />
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
          <button className="btn-ghost mb-0" type="button" onClick={clearFilters}>
            Clear
          </button>
        </div>
        </Card>
      </form>
      <DataTable className="min-w-[720px]">
          <thead className={tableHeadClass}>
            <tr>
              {table?.header.map((heading) => (
                <th key={heading} className={tableCellClass}>
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
      </DataTable>
    </div>
  )
}
