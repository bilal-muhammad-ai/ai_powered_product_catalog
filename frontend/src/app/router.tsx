import { Route, Routes } from "react-router-dom"
import { AppShell } from "../components/layout/AppShell"
import { AttributesPage } from "../features/attributes/AttributesPage"
import { CategoriesPage } from "../features/categories/CategoriesPage"
import { InventoryDashboardPage } from "../features/inventory/pages/InventoryDashboardPage"
import { InventoryDetailPage } from "../features/inventory/pages/InventoryDetailPage"
import { InventoryListPage } from "../features/inventory/pages/InventoryListPage"
import { InventoryReportsPage } from "../features/inventory/pages/InventoryReportsPage"
import { InventoryTransactionDetailsPage } from "../features/inventory/pages/InventoryTransactionDetailsPage"
import { InventoryTransactionListPage } from "../features/inventory/pages/InventoryTransactionListPage"
import { OpeningStockPage } from "../features/inventory/pages/OpeningStockPage"
import { StockAdjustmentPage } from "../features/inventory/pages/StockAdjustmentPage"
import { StockIssuePage } from "../features/inventory/pages/StockIssuePage"
import { StockReceiptPage } from "../features/inventory/pages/StockReceiptPage"
import { OrderDetailsPage } from "../features/orders/pages/OrderDetailsPage"
import { OrderFormPage } from "../features/orders/pages/OrderFormPage"
import { OrderListPage } from "../features/orders/pages/OrderListPage"
import { OrderReceiptPage } from "../features/orders/pages/OrderReceiptPage"
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
        <Route path="/inventory" element={<InventoryDashboardPage />} />
        <Route path="/inventory/stock" element={<InventoryListPage />} />
        <Route path="/inventory/stock/:productId" element={<InventoryDetailPage />} />
        <Route path="/inventory/opening" element={<OpeningStockPage />} />
        <Route path="/inventory/receipts/new" element={<StockReceiptPage />} />
        <Route path="/inventory/issues/new" element={<StockIssuePage />} />
        <Route path="/inventory/adjustments/new" element={<StockAdjustmentPage />} />
        <Route path="/inventory/transactions" element={<InventoryTransactionListPage />} />
        <Route path="/inventory/transactions/:transactionId" element={<InventoryTransactionDetailsPage />} />
        <Route path="/inventory/reports" element={<InventoryReportsPage />} />
        <Route path="/orders" element={<OrderListPage />} />
        <Route path="/orders/new" element={<OrderFormPage />} />
        <Route path="/orders/:orderId/edit" element={<OrderFormPage />} />
        <Route path="/orders/:orderId/receipt" element={<OrderReceiptPage />} />
        <Route path="/orders/:orderId" element={<OrderDetailsPage />} />
      </Routes>
    </AppShell>
  )
}
