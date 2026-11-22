import { formatPkr, formatQty } from "../inventory/logic"

export type DiscountType = "AMOUNT" | "PERCENT"

export { formatPkr, formatQty }

export function money(value: number): number {
  return Math.round((value + Number.EPSILON) * 100) / 100
}

export function lineAmounts(quantity: number, unitPrice: number, discountType: DiscountType, discountValue: number) {
  const subtotal = money(quantity * unitPrice)
  const discount = discountType === "PERCENT" ? money((subtotal * discountValue) / 100) : money(discountValue)
  return { subtotal, discount, total: money(subtotal - discount) }
}

export function orderAmounts(
  lines: { quantity: number; unitPrice: number; discountType: DiscountType; discountValue: number }[],
  discountType: DiscountType,
  discountValue: number,
) {
  const priced = lines.map((line) => lineAmounts(line.quantity, line.unitPrice, line.discountType, line.discountValue))
  const subtotal = money(priced.reduce((sum, line) => sum + line.subtotal, 0))
  const itemDiscount = money(priced.reduce((sum, line) => sum + line.discount, 0))
  const net = money(subtotal - itemDiscount)
  const orderDiscount = discountType === "PERCENT" ? money((net * discountValue) / 100) : money(discountValue)
  return {
    lines: priced,
    subtotal,
    itemDiscount,
    orderDiscount,
    grandTotal: money(net - orderDiscount),
    quantity: lines.reduce((sum, line) => sum + line.quantity, 0),
  }
}

export function quantityError(value: string): string | null {
  if (!value.trim()) return "Enter a quantity"
  const quantity = Number(value)
  if (!Number.isFinite(quantity)) return "Quantity must be a number"
  if (quantity <= 0) return "Quantity must be greater than zero"
  return null
}

export function priceError(value: string): string | null {
  if (!value.trim()) return "Enter a unit price"
  const price = Number(value)
  if (!Number.isFinite(price)) return "Unit price must be a number"
  if (price < 0) return "Unit price cannot be negative"
  return null
}

export function discountError(subtotal: number, discountType: DiscountType, value: string): string | null {
  if (!value.trim()) return null
  const discount = Number(value)
  if (!Number.isFinite(discount) || discount < 0) return "Discount cannot be negative"
  const amount = discountType === "PERCENT" ? (subtotal * discount) / 100 : discount
  if (amount > subtotal + 0.001) return "Discount cannot exceed the amount it applies to"
  return null
}

export function todayIso(): string {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, "0")
  const day = String(now.getDate()).padStart(2, "0")
  return `${now.getFullYear()}-${month}-${day}`
}

export function orderStatusLabel(status: string): string {
  if (status === "DRAFT") return "Draft"
  if (status === "CONFIRMED") return "Confirmed"
  if (status === "COMPLETED") return "Completed"
  return "Cancelled"
}
