import { stockStatusLabel, type StockState } from "../logic"

const tones: Record<StockState, string> = {
  in_stock: "bg-emerald-50 text-emerald-800",
  low_stock: "bg-amber-50 text-amber-800",
  out_of_stock: "bg-red-50 text-red-800",
}

export function InventoryStatusBadge({ status }: { status: StockState }) {
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${tones[status]}`}>
      {stockStatusLabel(status)}
    </span>
  )
}

const transactionTones: Record<string, string> = {
  DRAFT: "bg-stone-100 text-stone-700",
  POSTED: "bg-emerald-50 text-emerald-800",
  REVERSED: "bg-amber-50 text-amber-800",
  CANCELLED: "bg-red-50 text-red-800",
}

export function TransactionStatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${transactionTones[status] ?? transactionTones.DRAFT}`}>
      {status.charAt(0) + status.slice(1).toLowerCase()}
    </span>
  )
}

export function transactionTypeLabel(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ")
}
