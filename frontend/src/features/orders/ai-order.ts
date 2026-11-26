import type { AiOrder, AiProductMatch } from "./api"

export type AiItemStatus = "selected" | "pending" | "unavailable"

export type ResolvedAiItem = {
  index: number
  label: string
  quantity: string
  spokenUnit: string | null
  products: AiProductMatch[]
  status: AiItemStatus
  selectedProductId: string | null
}

export function quantityText(quantity: number | null): string {
  if (quantity === null || !Number.isFinite(quantity)) return "1"
  return String(quantity)
}

export function resolveAiOrder(order: AiOrder): ResolvedAiItem[] {
  return order.items.map((item, index) => {
    const products = item.products ?? []
    const status: AiItemStatus = products.length === 0 ? "unavailable" : products.length === 1 ? "selected" : "pending"
    return {
      index,
      label: item.product_name?.trim() || "Requested item",
      quantity: quantityText(item.quantity),
      spokenUnit: item.unit,
      products,
      status,
      selectedProductId: products.length === 1 ? products[0].product_id : null,
    }
  })
}

export function selectAiItem(items: ResolvedAiItem[], index: number, productId: string): ResolvedAiItem[] {
  return items.map((item) => (item.index === index ? { ...item, status: "selected", selectedProductId: productId } : item))
}

export function choiceIndexes(items: ResolvedAiItem[]): number[] {
  return items.filter((item) => item.products.length > 1).map((item) => item.index)
}

export function firstPendingChoice(items: ResolvedAiItem[]): number | null {
  const pending = items.find((item) => item.products.length > 1 && item.selectedProductId === null)
  return pending ? pending.index : null
}

export function hasPendingChoice(items: ResolvedAiItem[]): boolean {
  return firstPendingChoice(items) !== null
}

export function choicePosition(items: ResolvedAiItem[], index: number): { current: number; total: number } | null {
  const choices = choiceIndexes(items)
  const place = choices.indexOf(index)
  if (place === -1) return null
  return { current: place + 1, total: choices.length }
}

export function previousChoice(items: ResolvedAiItem[], index: number): number | null {
  const choices = choiceIndexes(items)
  const place = choices.indexOf(index)
  if (place <= 0) return null
  return choices[place - 1]
}

export function nextChoice(items: ResolvedAiItem[], index: number): number | null {
  const choices = choiceIndexes(items)
  const place = choices.indexOf(index)
  if (place === -1 || place >= choices.length - 1) return null
  return choices[place + 1]
}

export function lineKey(index: number): string {
  return `ai-${index}`
}

export function appendAiItems(existing: ResolvedAiItem[], incoming: ResolvedAiItem[]): ResolvedAiItem[] {
  const start = existing.reduce((max, item) => Math.max(max, item.index + 1), 0)
  return [...existing, ...incoming.map((item, offset) => ({ ...item, index: start + offset }))]
}
