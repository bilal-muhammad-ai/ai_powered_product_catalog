import type { ReactNode } from "react"

export function PageHeader({ title, lede, action }: { title: string; lede?: string; action?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="font-display text-3xl text-ink">{title}</h1>
        {lede ? <p className="mt-1 max-w-2xl text-sm text-stone-600">{lede}</p> : null}
      </div>
      {action}
    </div>
  )
}

export function ErrorNote({ message }: { message: string | null }) {
  if (!message) {
    return null
  }
  return <p className="whitespace-pre-line rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{message}</p>
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      {children}
    </label>
  )
}
