import { orderStatusLabel } from "../logic"

const tones: Record<string, string> = {
  DRAFT: "bg-stone-100 text-stone-700",
  CONFIRMED: "bg-emerald-50 text-emerald-800",
  COMPLETED: "bg-sky-50 text-sky-800",
  CANCELLED: "bg-red-50 text-red-800",
}

export function OrderStatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${tones[status] ?? tones.DRAFT}`}>
      {orderStatusLabel(status)}
    </span>
  )
}
