import { ApiError, api } from "../../api/client"
import type { Page } from "../../api/types"

export type OrderStatus = "DRAFT" | "CONFIRMED" | "COMPLETED" | "CANCELLED"
export type DiscountType = "AMOUNT" | "PERCENT"

export type OrderItem = {
  id: string
  product_id: string
  product_name_snapshot: string
  sku_snapshot: string
  unit_id: string
  unit_name_snapshot: string
  quantity: string
  unit_price: string
  discount_type: DiscountType
  discount_value: string
  discount_amount: string
  subtotal: string
  total: string
}

export type Order = {
  id: string
  order_number: string
  status: OrderStatus
  order_date: string
  notes: string | null
  discount_type: DiscountType
  discount_value: string
  subtotal: string
  item_discount_total: string
  order_discount_amount: string
  grand_total: string
  item_count: number
  total_quantity: string
  confirmed_at: string | null
  cancelled_at: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
  inventory_transaction_id: string | null
  inventory_transaction_number: string | null
  items: OrderItem[]
}

export type OrderListItem = {
  id: string
  order_number: string
  status: OrderStatus
  order_date: string
  item_count: number
  grand_total: string
  created_at: string
}

export type OrderCatalogHit = {
  product_id: string
  name: string
  sku: string
  category_id: string
  category_name: string
  unit_id: string
  unit_symbol: string
  selling_price: string
  quantity_on_hand: string
}

export type OrderItemInput = {
  product_id: string
  unit_id: string
  quantity: string
  unit_price: string
  discount_type: DiscountType
  discount_value: string
}

export type OrderBody = {
  order_date: string
  notes?: string | null
  discount_type: DiscountType
  discount_value: string
  items: OrderItemInput[]
}

function query(params: Record<string, string | undefined>) {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value) search.set(key, value)
  }
  const text = search.toString()
  return text ? `?${text}` : ""
}

export function listOrders(params: Record<string, string | undefined>) {
  return api<Page<OrderListItem>>(`/api/v1/orders${query(params)}`)
}

export function getOrder(orderId: string) {
  return api<Order>(`/api/v1/orders/${orderId}`)
}

export async function readOrder(orderId: string): Promise<Order> {
  try {
    return await getOrder(orderId)
  } catch (reason) {
    if (!(reason instanceof ApiError) || reason.status !== 404) throw reason
    await new Promise((resolve) => window.setTimeout(resolve, 200))
    return getOrder(orderId)
  }
}

export function createOrder(body: OrderBody) {
  return api<Order>("/api/v1/orders", { method: "POST", body: JSON.stringify(body) })
}

export function updateOrder(orderId: string, body: OrderBody) {
  return api<Order>(`/api/v1/orders/${orderId}`, { method: "PUT", body: JSON.stringify(body) })
}

export function deleteOrder(orderId: string) {
  return api<void>(`/api/v1/orders/${orderId}`, { method: "DELETE" })
}

export function confirmOrder(orderId: string) {
  return api<Order>(`/api/v1/orders/${orderId}/confirm`, { method: "POST" })
}

export function cancelOrder(orderId: string) {
  return api<Order>(`/api/v1/orders/${orderId}/cancel`, { method: "POST" })
}

export function completeOrder(orderId: string) {
  return api<Order>(`/api/v1/orders/${orderId}/complete`, { method: "POST" })
}

export function searchOrderCatalog(q: string) {
  return api<OrderCatalogHit[]>(`/api/v1/orders/catalog${query({ q })}`)
}

export type AiProductMatch = {
  product_id: string
  name: string
  category_id: string
  category_name: string
  selling_unit_id: string
  selling_unit_symbol: string
  selling_unit_name: string
  score: number
}

export type AiOrderItem = {
  product_name: string | null
  quantity: number | null
  unit: string | null
  products: AiProductMatch[]
}

export type AiOrder = {
  intent: "create_order"
  items: AiOrderItem[]
}

export function suggestOrder(text: string) {
  return api<AiOrder>("/api/v1/ai/create_order", { method: "POST", body: JSON.stringify({ text }) })
}
