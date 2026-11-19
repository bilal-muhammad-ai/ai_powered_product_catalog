import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { InventoryStatusBadge } from "./components/InventoryStatusBadge"
import { StockDocumentForm, type DocumentLine } from "./components/StockDocumentForm"
import { formatPkr } from "./logic"

vi.stubGlobal(
  "fetch",
  vi.fn(async () => new Response(JSON.stringify({ items: [], total: 0, page: 1, page_size: 100 }), { status: 200 })),
)

const cement: DocumentLine = {
  key: "cement",
  productId: "product-1",
  name: "Cement",
  sku: "CEM-50",
  available: 2,
  sellingUnitId: "bag",
  unitId: "bag",
  unitSymbol: "bag",
  quantity: "2",
  unitCost: "1200",
}

describe("inventory screens", () => {
  afterEach(() => cleanup())

  it("shows a stock status", () => {
    render(<InventoryStatusBadge status="low_stock" />)
    expect(screen.getByText("Low stock")).toBeTruthy()
  })

  it("shows a receipt line total", () => {
    render(<StockDocumentForm mode="receipt" initialLines={[cement]} onSubmit={vi.fn()} onCancel={() => undefined} />)
    expect(screen.getAllByText(/2,400\.00/).length).toBeGreaterThan(0)
    expect(formatPkr(2400)).toContain("2,400.00")
  })

  it("stops an issue that exceeds available stock", () => {
    const onSubmit = vi.fn()
    render(
      <StockDocumentForm
        mode="issue"
        initialLines={[{ ...cement, quantity: "5", available: 2 }]}
        onSubmit={onSubmit}
        onCancel={() => undefined}
      />,
    )
    fireEvent.click(screen.getByRole("button", { name: /post stock issue/i }))
    expect(screen.getByText(/more than the available stock/i)).toBeTruthy()
    expect(onSubmit).not.toHaveBeenCalled()
  })
})
