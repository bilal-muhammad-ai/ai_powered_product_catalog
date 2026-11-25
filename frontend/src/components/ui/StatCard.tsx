import type { ReactNode } from "react"
import { Card } from "./Card"

export function StatCard({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <Card className="px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">{label}</p>
      <div className="mt-1 font-display text-2xl tracking-tight text-ink">{value}</div>
      {hint ? <p className="mt-1 text-xs text-stone-500">{hint}</p> : null}
    </Card>
  )
}

export function StatGrid({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4 ${className}`.trim()}>{children}</div>
}
