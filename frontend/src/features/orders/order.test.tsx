import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import type { AiProductMatch } from "./api"
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

function json(body: unknown) {
  return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } })
}

function defaultFetch(input: RequestInfo) {
  const url = String(input)
  const body = url.includes("/catalog")
    ? [cement]
    : { items: [{ id: "bag", name: "Bag", symbol: "bag", unit_type: "packaging", is_active: true }], total: 1, page: 1, page_size: 100 }
  return json(body)
}

function aiMatch(id: string, name: string, category: string, unitId: string, symbol: string, unitName: string): AiProductMatch {
  return {
    product_id: id,
    name,
    category_id: category,
    category_name: category === "cement-cat" ? "Cement" : category === "brush-cat" ? "Brushes" : "Tiles",
    selling_unit_id: unitId,
    selling_unit_symbol: symbol,
    selling_unit_name: unitName,
    score: 1,
  }
}

describe("order screens", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(defaultFetch))
  })

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

  it("resolves an AI order one choice at a time and keeps manual products", async () => {
    const prices: Record<string, string> = {
      "cement-id": "1480.00",
      "brush-2": "80.00",
      "brush-3": "90.00",
      "tile-1": "500.00",
    }
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo) => {
        const url = String(input)
        if (url.includes("/ai/create_order")) return json({
          intent: "create_order",
          items: [
            {
              product_name: "DG cement",
              quantity: 2,
              unit: "bag",
              products: [aiMatch("cement-id", "DG Khan Cement PPC 43 — 50 kg bag", "cement-cat", "bag-id", "bag", "Bag")],
            },
            {
              product_name: "paintbrushes",
              quantity: 10,
              unit: null,
              products: [
                aiMatch("brush-2", "Wooden Paint Brush — 2 in", "brush-cat", "pc-id", "pc", "Piece"),
                aiMatch("brush-3", "Wooden Paint Brush — 3 in", "brush-cat", "pc-id", "pc", "Piece"),
              ],
            },
            { product_name: "toilet seat", quantity: 1, unit: null, products: [] },
            {
              product_name: "bathroom tiles",
              quantity: 4,
              unit: null,
              products: [
                aiMatch("tile-1", "White Bathroom Tile", "tile-cat", "pc-id", "pc", "Piece"),
                aiMatch("tile-2", "Grey Bathroom Tile", "tile-cat", "pc-id", "pc", "Piece"),
              ],
            },
          ],
        })
        if (url.includes("/products/")) {
          const id = url.split("/products/")[1]
          return json({ selling_price: prices[id] ?? "1.00" })
        }
        if (url.includes("/catalog")) return json([cement])
        return json({
          items: [
            { id: "bag", name: "Bag", symbol: "bag", unit_type: "packaging", is_active: true },
            { id: "bag-id", name: "Bag", symbol: "bag", unit_type: "packaging", is_active: true },
            { id: "pc-id", name: "Piece", symbol: "pc", unit_type: "piece", is_active: true },
          ],
          total: 3,
          page: 1,
          page_size: 100,
        })
      }),
    )
    const onSubmit = vi.fn()
    render(<OrderEditor assist onSubmit={onSubmit} onCancel={() => undefined} />)

    fireEvent.change(screen.getByPlaceholderText(/2 bags of DG cement/i), {
      target: { value: "I need 2 bags of DG cement, 10 paintbrushes, and one toilet seat." },
    })
    fireEvent.click(screen.getByRole("button", { name: "Find products" }))

    expect((await screen.findAllByText("DG Khan Cement PPC 43 — 50 kg bag")).length).toBeGreaterThan(0)
    expect(screen.getByText("No matching products available")).toBeTruthy()
    expect(screen.getByText(/Excluded from this order: toilet seat/i)).toBeTruthy()
    expect(screen.getByText("Selecting product 1 of 2")).toBeTruthy()
    expect(screen.queryByRole("radio", { name: /white bathroom tile/i })).toBeNull()
    expect((screen.getByRole("button", { name: "Confirm order" }) as HTMLButtonElement).disabled).toBe(true)

    fireEvent.click(screen.getByRole("radio", { name: /wooden paint brush — 3 in/i }))
    expect(await screen.findByText("Selecting product 2 of 2")).toBeTruthy()
    fireEvent.change(screen.getByDisplayValue("10"), { target: { value: "12" } })
    fireEvent.click(screen.getByRole("button", { name: "Back" }))
    expect((screen.getByRole("radio", { name: /wooden paint brush — 3 in/i }) as HTMLInputElement).checked).toBe(true)

    fireEvent.click(screen.getByRole("radio", { name: /wooden paint brush — 2 in/i }))
    expect(await screen.findByText("Selecting product 2 of 2")).toBeTruthy()
    expect(screen.getByDisplayValue("12")).toBeTruthy()
    fireEvent.click(screen.getByRole("radio", { name: /white bathroom tile/i }))
    await waitFor(() => expect((screen.getByRole("button", { name: "Confirm order" }) as HTMLButtonElement).disabled).toBe(false))

    fireEvent.change(screen.getByPlaceholderText("Cement, rod, SKU"), { target: { value: "maple" } })
    fireEvent.click(await screen.findByRole("button", { name: /maple leaf cement/i }))
    fireEvent.click(screen.getByRole("button", { name: "Confirm order" }))

    await waitFor(() => expect(onSubmit).toHaveBeenCalled())
    const body = onSubmit.mock.calls[0][0]
    expect(body.items.map((item: { product_id: string; quantity: string; unit_price: string }) => [item.product_id, item.quantity, item.unit_price])).toEqual([
      ["cement-id", "2", "1480.00"],
      ["brush-2", "12", "80.00"],
      ["tile-1", "4", "500.00"],
      ["product-1", "1", "1100.00"],
    ])
    const aiCall = vi.mocked(fetch).mock.calls.find((call) => String(call[0]).includes("/ai/create_order"))
    expect(String(aiCall?.[1] && typeof aiCall[1] === "object" ? (aiCall[1] as RequestInit).body : "")).toContain("DG cement")
  })
})
