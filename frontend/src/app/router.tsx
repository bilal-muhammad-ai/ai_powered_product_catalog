import { Route, Routes } from "react-router-dom"
import { AppShell } from "../components/layout/AppShell"
import { AttributesPage } from "../features/attributes/AttributesPage"
import { CategoriesPage } from "../features/categories/CategoriesPage"
import { ProductFormPage } from "../features/products/ProductFormPage"
import { ProductListPage } from "../features/products/ProductListPage"
import { UnitsPage } from "../features/units/UnitsPage"

export function AppRouter() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<ProductListPage />} />
        <Route path="/products" element={<ProductListPage />} />
        <Route path="/products/new" element={<ProductFormPage />} />
        <Route path="/products/:productId" element={<ProductFormPage />} />
        <Route path="/categories" element={<CategoriesPage />} />
        <Route path="/categories/:categoryId/attributes" element={<AttributesPage />} />
        <Route path="/units" element={<UnitsPage />} />
      </Routes>
    </AppShell>
  )
}
