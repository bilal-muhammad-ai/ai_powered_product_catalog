import { api } from "./client"
import type { Page } from "./types"

export type StockStatus = "in_stock" | "low_stock" | "out_of_stock"
export type TransactionType = "OPENING_STOCK" | "STOCK_RECEIPT" | "STOCK_ISSUE" | "STOCK_ADJUSTMENT" | "REVERSAL"
export type TransactionStatus = "DRAFT" | "POSTED" | "CANCELLED" | "REVERSED"

export type BalanceItem = {
  product_id: string
  product_name: string
  sku: string
  category_id: string
  category_name: string
  brand: string | null
  quantity_on_hand: string
  unit_id: string
  unit_symbol: string
  average_cost: string
  inventory_value: string
  minimum_stock_level: string | null
  reorder_level: string | null
  maximum_stock_level: string | null
  stock_status: StockStatus
}

export type InventoryDetail = BalanceItem & {
  barcode: string | null
  net_quantity: string | null
  net_quantity_unit_symbol: string | null
}

export type TransactionItem = {
  id: string
  product_id: string
  product_name: string
  sku: string
  unit_id: string
  unit_symbol: string
  quantity: string
  unit_cost: string
  total_cost: string
  quantity_delta: string
}

export type Transaction = {
  id: string
  transaction_number: string
  transaction_type: TransactionType
  status: TransactionStatus
  reference_number: string | null
  reference_type: string | null
  reference_id: string | null
  transaction_date: string
  notes: string | null
  reason: string | null
  created_by: string | null
  created_at: string
  posted_at: string | null
  reversed_at: string | null
  reversal_of_id: string | null
  item_count: number
  total_quantity: string
  total_value: string
  items: TransactionItem[]
}

export type TransactionListItem = {
  id: string
  transaction_number: string
  transaction_type: TransactionType
  status: TransactionStatus
  transaction_date: string
  reference_number: string | null
  item_count: number
  total_quantity: string
  total_value: string
}

export type Movement = {
  transaction_id: string
  transaction_number: string
  transaction_type: TransactionType
  status: TransactionStatus
  transaction_date: string
  quantity: string
  quantity_delta: string
  unit_symbol: string
  unit_cost: string
  total_cost: string
  reference_number: string | null
}

export type InventorySummary = {
  product_count: number
  total_quantity: string
  total_value: string
  low_stock_count: number
  out_of_stock_count: number
  recent_transactions: TransactionListItem[]
  low_stock: BalanceItem[]
  out_of_stock: BalanceItem[]
  value_by_category: { category_name: string; inventory_value: string }[]
  movement_counts: { transaction_type: TransactionType; count: number }[]
}

export type CatalogHit = {
  product_id: string
  name: string
  sku: string
  category_name: string
  brand: string | null
  unit_id: string
  unit_symbol: string
  quantity_on_hand: string
  average_cost: string
  net_quantity: string | null
  net_quantity_unit_id: string | null
}

export type MovementItemInput = {
  product_id: string
  unit_id: string
  quantity?: string
  physical_quantity?: string
  unit_cost?: string
}

export type MovementBody = {
  transaction_date: string
  reference_number?: string | null
  notes?: string | null
  reason?: string | null
  post: boolean
  items: MovementItemInput[]
}

export type ReportTable = { header: string[]; rows: string[][] }

function query(params: Record<string, string | undefined>) {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value) search.set(key, value)
  }
  const text = search.toString()
  return text ? `?${text}` : ""
}

export function listInventory(params: Record<string, string | undefined>) {
  return api<Page<BalanceItem>>(`/api/v1/inventory${query(params)}`)
}

export function getInventorySummary() {
  return api<InventorySummary>("/api/v1/inventory/summary")
}

export function getInventory(productId: string) {
  return api<InventoryDetail>(`/api/v1/inventory/${productId}`)
}

export function getInventoryHistory(productId: string) {
  return api<Movement[]>(`/api/v1/inventory/${productId}/history`)
}

export function saveStockSettings(
  productId: string,
  body: { minimum_stock_level: string | null; reorder_level: string | null; maximum_stock_level: string | null },
) {
  return api<typeof body & { product_id: string }>(`/api/v1/inventory/${productId}/settings`, {
    method: "PUT",
    body: JSON.stringify(body),
  })
}

export function searchCatalog(q: string) {
  return api<CatalogHit[]>(`/api/v1/inventory/catalog${query({ q })}`)
}

export function listTransactions(params: Record<string, string | undefined>) {
  return api<Page<TransactionListItem>>(`/api/v1/inventory/transactions${query(params)}`)
}

export function getTransaction(id: string) {
  return api<Transaction>(`/api/v1/inventory/transactions/${id}`)
}

export function createMovement(path: "opening-stock" | "receipts" | "issues" | "adjustments", body: MovementBody) {
  return api<Transaction>(`/api/v1/inventory/${path}`, { method: "POST", body: JSON.stringify(body) })
}

export function postTransaction(id: string) {
  return api<Transaction>(`/api/v1/inventory/transactions/${id}/post`, { method: "POST" })
}

export function reverseTransaction(id: string) {
  return api<Transaction>(`/api/v1/inventory/transactions/${id}/reverse`, { method: "POST" })
}

export function getReport(path: string, params: Record<string, string | undefined>) {
  return api<ReportTable>(`/api/v1/inventory/reports/${path}${query(params)}`)
}

export function reportCsvPath(path: string, params: Record<string, string | undefined>) {
  return `/api/v1/inventory/reports/${path}${query({ ...params, format: "csv" })}`
}
