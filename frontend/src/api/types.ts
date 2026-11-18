export type Page<T> = {
  items: T[]
  total: number
  page: number
  page_size: number
}

export type Unit = {
  id: string
  name: string
  symbol: string
  unit_type: string
  is_active: boolean
}

export type CategoryNode = {
  id: string
  parent_id: string | null
  name: string
  slug: string
  description: string | null
  sort_order: number
  is_active: boolean
  path: string
  children: CategoryNode[]
}

export type DataType = "text" | "number" | "boolean" | "date" | "single_select" | "multi_select"
export type AttributeScope = "product" | "variant"

export type AttributeOption = {
  id: string
  attribute_id: string
  label: string
  value: string
  sort_order: number
  is_active: boolean
}

export type Attribute = {
  id: string
  category_id: string
  owner_category_name: string
  code: string
  name: string
  data_type: DataType
  scope: AttributeScope
  unit_id: string | null
  is_required: boolean
  is_filterable: boolean
  is_active: boolean
  inherit_to_children: boolean
  sort_order: number
  help_text: string | null
  min_value: string | null
  max_value: string | null
  max_length: number | null
  inherited: boolean
  options: AttributeOption[]
}

export type AttributeValue = {
  attribute_id: string
  code: string
  name: string
  data_type: DataType
  value: unknown
}

export type Variant = {
  id: string
  sku: string
  barcode: string | null
  name: string | null
  selling_unit_id: string
  net_quantity: string | null
  net_quantity_unit_id: string | null
  cost_price: string
  selling_price: string
  currency_code: string
  is_active: boolean
  sort_order: number
  variant_key: string
  attribute_values: AttributeValue[]
}

export type ProductDetail = {
  id: string
  category_id: string
  category_name: string
  base_unit_id: string | null
  name: string
  slug: string
  code: string | null
  description: string | null
  status: "draft" | "active" | "archived"
  attribute_values: AttributeValue[]
  variants: Variant[]
  created_at: string
  updated_at: string
}

export type ProductListItem = {
  id: string
  name: string
  code: string | null
  slug: string
  status: ProductDetail["status"]
  category_id: string
  category_name: string
  variant_count: number
  selling_price_min: string | null
  selling_price_max: string | null
  updated_at: string
}
