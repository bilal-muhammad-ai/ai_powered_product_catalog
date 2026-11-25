import type { ReactNode } from "react"

export function DataTable({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className="overflow-hidden rounded-xl border border-line bg-white shadow-card">
      <div className="overflow-x-auto">
        <table className={`w-full text-left text-sm ${className}`.trim()}>{children}</table>
      </div>
    </div>
  )
}

export const tableHeadClass = "bg-stone-50 text-xs font-semibold uppercase tracking-wide text-stone-500"
export const tableCellClass = "px-4 py-3"
