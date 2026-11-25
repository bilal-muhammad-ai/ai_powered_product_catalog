import type { ReactNode } from "react"

export function PageHeader({ title, lede, action }: { title: string; lede?: string; action?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="font-display text-3xl tracking-tight text-ink md:text-[2.15rem]">{title}</h1>
        {lede ? <p className="mt-2 max-w-2xl text-sm leading-6 text-stone-600">{lede}</p> : null}
      </div>
      {action ? <div className="flex shrink-0 flex-wrap items-center gap-2">{action}</div> : null}
    </div>
  )
}
