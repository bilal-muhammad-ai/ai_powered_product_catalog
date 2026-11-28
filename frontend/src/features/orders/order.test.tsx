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
  quantity_unit_id: null,
  quantity_unit_symbol: null,
  quantity_unit_price: "0.00",
  net_quantity: null,
}

const pipe = {
  product_id: "pipe-1",
  name: "Soil Pipe",
  sku: "PIPE-1",
  category_id: "cat",
  category_name: "Pipes",
  unit_id: "pc",
  unit_symbol: "pc",
  selling_price: "500.00",
  quantity_on_hand: "10.0000",
  quantity_unit_id: "ft",
  quantity_unit_symbol: "ft",
  quantity_unit_price: "25.00",
  net_quantity: "20.0000",
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

function aiMatch(
  id: string,
  name: string,
  category: string,
  unitId: string,
  symbol: string,
  unitName: string,
  sku: string,
  price: string,
): AiProductMatch {
  return {
    product_id: id,
    name,
    sku,
    category_id: category,
    category_name: category === "cement-cat" ? "Cement" : category === "brush-cat" ? "Brushes" : "Tiles",
    selling_unit_id: unitId,
    selling_unit_symbol: symbol,
    selling_unit_name: unitName,
    selling_price: price,
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
    const result = await screen.findByRole("button", { name: /maple leaf cement/i })
    expect(result.textContent).toMatch(/10 bag/)
    expect(result.textContent).not.toMatch(/ft/)
    fireEvent.click(result)
    expect(screen.getAllByText(/1,100\.00/).length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole("button", { name: /confirm order/i }))
    await waitFor(() => expect(onSubmit).toHaveBeenCalled())
    const body = onSubmit.mock.calls[0][0]
    expect(body.items[0].product_id).toBe("product-1")
    expect(body.items[0].quantity).toBe("1")
    expect(body.items[0].unit_price).toBe("1100.00")
  })

  it("switches to the quantity unit price without changing quantity", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo) => json(String(input).includes("/catalog") ? [pipe] : { items: [], total: 0, page: 1, page_size: 100 })),
    )
    render(<OrderEditor onSubmit={vi.fn()} onCancel={() => undefined} />)
    fireEvent.change(screen.getByPlaceholderText("Cement, rod, SKU"), { target: { value: "soil" } })
    const result = await screen.findByRole("button", { name: /soil pipe/i })
    expect(result.textContent).toMatch(/10 pc/)
    expect(result.textContent).not.toMatch(/200/)
    fireEvent.click(result)
    const quantity = screen.getByLabelText("Quantity for Soil Pipe") as HTMLInputElement
    fireEvent.change(quantity, { target: { value: "2" } })
    fireEvent.change(screen.getByLabelText("Unit for Soil Pipe"), { target: { value: "ft" } })
    expect(quantity.value).toBe("2")
    expect((screen.getByLabelText("Price for Soil Pipe") as HTMLInputElement).value).toBe("25.00")
    expect(screen.getAllByText(/50\.00/).length).toBeGreaterThan(0)
    const unit = screen.getByLabelText("Unit for Soil Pipe") as HTMLSelectElement
    expect(Array.from(unit.options).map((option) => option.textContent)).toEqual(["pc", "ft"])
  })

  it("resolves an AI order one choice at a time and keeps manual products", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo, init?: RequestInit) => {
        const url = String(input)
        if (url.includes("/ai/create_order")) {
          const text = String(init?.body ?? "")
          if (text.includes("sand")) {
            return json({
              intent: "create_order",
              items: [
                {
                  product_name: "sand",
                  quantity: 3,
                  unit: "bag",
                  products: [aiMatch("sand-id", "River Sand", "cement-cat", "bag-id", "bag", "Bag", "SAND-1", "220.00")],
                },
              ],
            })
          }
          return json({
          intent: "create_order",
          items: [
            {
              product_name: "DG cement",
              quantity: 2,
              unit: "bag",
              products: [aiMatch("cement-id", "DG Khan Cement PPC 43 — 50 kg bag", "cement-cat", "bag-id", "bag", "Bag", "CEM-DG", "1480.00")],
            },
            {
              product_name: "paintbrushes",
              quantity: 10,
              unit: null,
              products: [
                aiMatch("brush-2", "Wooden Paint Brush — 2 in", "brush-cat", "pc-id", "pc", "Piece", "BR-2", "80.00"),
                aiMatch("brush-3", "Wooden Paint Brush — 3 in", "brush-cat", "pc-id", "pc", "Piece", "BR-3", "90.00"),
              ],
            },
            { product_name: "toilet seat", quantity: 1, unit: null, products: [] },
            {
              product_name: "bathroom tiles",
              quantity: 4,
              unit: null,
              products: [
                aiMatch("tile-1", "White Bathroom Tile", "tile-cat", "pc-id", "pc", "Piece", "TILE-1", "500.00"),
                aiMatch("tile-2", "Grey Bathroom Tile", "tile-cat", "pc-id", "pc", "Piece", "TILE-2", "450.00"),
              ],
            },
          ],
        })
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
    expect(screen.getByText("CEM-DG")).toBeTruthy()
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

    fireEvent.change(screen.getByPlaceholderText(/2 bags of DG cement/i), { target: { value: "3 bags of sand" } })
    fireEvent.click(screen.getByRole("button", { name: "Find products" }))
    expect((await screen.findAllByText("River Sand")).length).toBeGreaterThan(1)
    expect(screen.getByText("SAND-1")).toBeTruthy()
    expect(screen.getByText("CEM-DG")).toBeTruthy()

    fireEvent.change(screen.getByPlaceholderText("Cement, rod, SKU"), { target: { value: "maple" } })
    fireEvent.click(await screen.findByRole("button", { name: /maple leaf cement/i }))
    fireEvent.click(screen.getByRole("button", { name: "Confirm order" }))

    await waitFor(() => expect(onSubmit).toHaveBeenCalled())
    const body = onSubmit.mock.calls[0][0]
    expect(
      body.items.map((item: { product_id: string; quantity: string; unit_price: string; unit_id: string }) => [
        item.product_id,
        item.quantity,
        item.unit_price,
        item.unit_id,
      ]),
    ).toEqual([
      ["cement-id", "2", "1480.00", "bag-id"],
      ["brush-2", "12", "80.00", "pc-id"],
      ["tile-1", "4", "500.00", "pc-id"],
      ["sand-id", "3", "220.00", "bag-id"],
      ["product-1", "1", "1100.00", "bag"],
    ])
    expect(vi.mocked(fetch).mock.calls.some((call) => String(call[0]).includes("/products/"))).toBe(false)
    const aiCall = vi.mocked(fetch).mock.calls.find((call) => String(call[0]).includes("/ai/create_order"))
    expect(String(aiCall?.[1] && typeof aiCall[1] === "object" ? (aiCall[1] as RequestInit).body : "")).toContain("DG cement")
  })
})
