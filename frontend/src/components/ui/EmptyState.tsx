import type { ReactNode } from "react"

export function EmptyState({ title, detail, action }: { title: string; detail?: string; action?: ReactNode }) {
  return (
    <div className="px-4 py-10 text-center">
      <p className="text-sm font-semibold text-ink">{title}</p>
      {detail ? <p className="mx-auto mt-1 max-w-md text-sm text-stone-500">{detail}</p> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  )
}
