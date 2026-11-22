export type StockState = "in_stock" | "low_stock" | "out_of_stock"

export function formatPkr(value: string | number): string {
  const amount = typeof value === "string" ? Number(value) : value
  if (!Number.isFinite(amount)) return "—"
  return new Intl.NumberFormat("en-PK", {
    style: "currency",
    currency: "PKR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

export function formatQty(value: string | number): string {
  const amount = typeof value === "string" ? Number(value) : value
  if (!Number.isFinite(amount)) return "—"
  return new Intl.NumberFormat("en-PK", { maximumFractionDigits: 4 }).format(amount)
}

export function stockStatus(quantity: number, minimum: number | null): StockState {
  if (quantity <= 0) return "out_of_stock"
  if (minimum !== null && quantity <= minimum) return "low_stock"
  return "in_stock"
}

export function stockStatusLabel(status: StockState): string {
  if (status === "low_stock") return "Low stock"
  if (status === "out_of_stock") return "Out of stock"
  return "In stock"
}

export function adjustmentDelta(systemStock: number, physicalStock: number): number {
  return physicalStock - systemStock
}

export function lineTotal(quantity: number, unitCost: number): number {
  return quantity * unitCost
}

export function quantityError(value: string): string | null {
  if (!value.trim()) return "Enter a quantity"
  const quantity = Number(value)
  if (!Number.isFinite(quantity)) return "Quantity must be a number"
  if (quantity <= 0) return "Quantity must be greater than zero"
  return null
}

export function issueQuantityError(value: string, available: number, sameUnit: boolean): string | null {
  const error = quantityError(value)
  if (error) return error
  if (sameUnit && Number(value) > available) return "Quantity is more than the available stock"
  return null
}

export function costError(value: string, required: boolean): string | null {
  if (!value.trim()) return required ? "Enter a unit cost" : null
  const cost = Number(value)
  if (!Number.isFinite(cost)) return "Unit cost must be a number"
  if (cost < 0) return "Unit cost cannot be negative"
  return null
}

export function todayIso(): string {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, "0")
  const day = String(now.getDate()).padStart(2, "0")
  return `${now.getFullYear()}-${month}-${day}`
}
