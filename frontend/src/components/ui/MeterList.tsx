export function MeterList({
  rows,
  empty,
}: {
  rows: { label: string; value: string; amount: number }[]
  empty: string
}) {
  if (rows.length === 0) return <p className="px-4 py-6 text-sm text-stone-500">{empty}</p>
  const max = Math.max(...rows.map((row) => row.amount), 0)
  return (
    <ul className="space-y-3 px-4 py-4">
      {rows.map((row) => (
        <li key={row.label}>
          <div className="mb-1 flex items-center justify-between gap-3 text-sm">
            <span className="min-w-0 truncate text-ink">{row.label}</span>
            <span className="shrink-0 font-medium text-ink">{row.value}</span>
          </div>
          <div className="h-1.5 rounded-full bg-stone-100">
            <div
              className="h-1.5 rounded-full bg-pine"
              style={{ width: max > 0 ? `${Math.max(6, (row.amount / max) * 100)}%` : "0%" }}
            />
          </div>
        </li>
      ))}
    </ul>
  )
}
