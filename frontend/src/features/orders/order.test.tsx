import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { OrderStatusBadge } from "./components/OrderStatusBadge"
import { OrderEditor } from "./components/OrderEditor"

const cement = {
  product_id: "product-1",
  name: "Maple Leaf Cement",
  sku: "CEM-50",
  category_id: "cat",
  category_name: "Cement",
  unit_id: "bag",
  unit_symbol: "bag",
  selling_price: "1100.00",
  quantity_on_hand: "10.0000",
}

vi.stubGlobal(
  "fetch",
  vi.fn(async (input: RequestInfo) => {
    const url = String(input)
    const body = url.includes("/catalog")
      ? [cement]
      : { items: [{ id: "bag", name: "Bag", symbol: "bag", unit_type: "packaging", is_active: true }], total: 1, page: 1, page_size: 100 }
    return new Response(JSON.stringify(body), { status: 200 })
  }),
)

describe("order screens", () => {
  afterEach(() => cleanup())

  it("shows an order status", () => {
    render(<OrderStatusBadge status="CONFIRMED" />)
    expect(screen.getByText("Confirmed")).toBeTruthy()
  })

  it("adds a searched product and shows the line total", async () => {
    const onSubmit = vi.fn()
    render(<OrderEditor onSubmit={onSubmit} onCancel={() => undefined} />)
    fireEvent.change(screen.getByPlaceholderText("Cement, rod, SKU"), { target: { value: "maple" } })
    fireEvent.click(await screen.findByRole("button", { name: /maple leaf cement/i }))
    expect(screen.getAllByText(/1,100\.00/).length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole("button", { name: /confirm order/i }))
    await waitFor(() => expect(onSubmit).toHaveBeenCalled())
    const body = onSubmit.mock.calls[0][0]
    expect(body.items[0].product_id).toBe("product-1")
    expect(body.items[0].quantity).toBe("1")
    expect(body.items[0].unit_price).toBe("1100.00")
  })
})
