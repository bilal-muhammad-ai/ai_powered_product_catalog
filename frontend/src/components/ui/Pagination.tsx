export function Pagination({
  page,
  pageSize,
  total,
  onPage,
  noun = "records",
}: {
  page: number
  pageSize: number
  total: number
  onPage: (page: number) => void
  noun?: string
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm">
      <p className="text-stone-600">
        {total} {noun} · page {page} of {pages}
      </p>
      <div className="flex gap-2">
        <button className="btn-ghost" type="button" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          Previous
        </button>
        <button className="btn-ghost" type="button" disabled={page >= pages} onClick={() => onPage(page + 1)}>
          Next
        </button>
      </div>
    </div>
  )
}
