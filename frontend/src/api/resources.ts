import { api } from "./client"
import type {
  Attribute,
  AttributeOption,
  CategoryNode,
  Page,
  ProductDetail,
  ProductListItem,
  Unit,
} from "./types"

export function listUnits(includeInactive = true) {
  return api<Page<Unit>>(`/api/v1/units?include_inactive=${includeInactive}&page_size=100`)
}

export function createUnit(body: { name: string; symbol: string; unit_type: string; is_active: boolean }) {
  return api<Unit>("/api/v1/units", { method: "POST", body: JSON.stringify(body) })
}

export function updateUnit(id: string, body: Partial<{ name: string; symbol: string; unit_type: string; is_active: boolean }>) {
  return api<Unit>(`/api/v1/units/${id}`, { method: "PATCH", body: JSON.stringify(body) })
}

export function deleteUnit(id: string) {
  return api<void>(`/api/v1/units/${id}`, { method: "DELETE" })
}

export function listCategories() {
  return api<CategoryNode[]>("/api/v1/categories")
}

export function createCategory(body: {
  name: string
  parent_id?: string | null
  description?: string | null
  sort_order?: number
  is_active?: boolean
}) {
  return api<CategoryNode>("/api/v1/categories", { method: "POST", body: JSON.stringify(body) })
}

export function updateCategory(
  id: string,
  body: Partial<{ name: string; parent_id: string | null; description: string | null; sort_order: number; is_active: boolean }>,
) {
  return api<CategoryNode>(`/api/v1/categories/${id}`, { method: "PATCH", body: JSON.stringify(body) })
}

export function deleteCategory(id: string) {
  return api<void>(`/api/v1/categories/${id}`, { method: "DELETE" })
}

export function listAttributes(categoryId: string, activeOnly = false) {
  return api<Attribute[]>(
    `/api/v1/categories/${categoryId}/attributes?include_inherited=true&active_only=${activeOnly}`,
  )
}

export function createAttribute(categoryId: string, body: Record<string, unknown>) {
  return api<Attribute>(`/api/v1/categories/${categoryId}/attributes`, {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export function updateAttribute(id: string, body: Record<string, unknown>) {
  return api<Attribute>(`/api/v1/attributes/${id}`, { method: "PATCH", body: JSON.stringify(body) })
}

export function deleteAttribute(id: string) {
  return api<void>(`/api/v1/attributes/${id}`, { method: "DELETE" })
}

export function createOption(attributeId: string, body: { label: string; value?: string; sort_order?: number }) {
  return api<AttributeOption>(`/api/v1/attributes/${attributeId}/options`, {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export function deleteOption(optionId: string) {
  return api<void>(`/api/v1/attribute-options/${optionId}`, { method: "DELETE" })
}

export function listProducts(params: URLSearchParams) {
  return api<Page<ProductListItem>>(`/api/v1/products?${params.toString()}`)
}

export function getProduct(id: string) {
  return api<ProductDetail>(`/api/v1/products/${id}`)
}

export function saveProduct(body: unknown, id?: string) {
  return api<ProductDetail>(id ? `/api/v1/products/${id}` : "/api/v1/products", {
    method: id ? "PATCH" : "POST",
    body: JSON.stringify(body),
  })
}

export function deleteProduct(id: string) {
  return api<void>(`/api/v1/products/${id}`, { method: "DELETE" })
}
