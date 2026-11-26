import { describe, expect, it } from "vitest"
import type { AiOrder, AiProductMatch } from "./api"
import {
  appendAiItems,
  choicePosition,
  firstPendingChoice,
  hasPendingChoice,
  nextChoice,
  previousChoice,
  resolveAiOrder,
  selectAiItem,
} from "./ai-order"

function match(id: string, name: string): AiProductMatch {
  return {
    product_id: id,
    name,
    category_id: "cat",
    category_name: "Brushes",
    selling_unit_id: "pc",
    selling_unit_symbol: "pc",
    selling_unit_name: "Piece",
    sku: "SKU",
    selling_price: "10.00",
    score: 1,
  }
}

function order(): AiOrder {
  return {
    intent: "create_order",
    items: [
      {
        product_name: "DG cement",
        quantity: 2,
        unit: "bag",
        products: [match("cement", "DG Khan Cement PPC 43 — 50 kg bag")],
      },
      {
        product_name: "paintbrushes",
        quantity: 10,
        unit: null,
        products: [match("brush-2", "Wooden Paint Brush — 2 in"), match("brush-3", "Wooden Paint Brush — 3 in")],
      },
      { product_name: "toilet seat", quantity: 1, unit: null, products: [] },
      {
        product_name: "  ",
        quantity: null,
        unit: null,
        products: [match("tile-1", "Bathroom Tile — 1"), match("tile-2", "Bathroom Tile — 2")],
      },
    ],
  }
}

describe("resolveAiOrder", () => {
  it("selects one match, waits on several, and leaves none unavailable", () => {
    const items = resolveAiOrder(order())

    expect(items.map((item) => item.status)).toEqual(["selected", "pending", "unavailable", "pending"])
    expect(items[0].selectedProductId).toBe("cement")
    expect(items[0].quantity).toBe("2")
    expect(items[1].selectedProductId).toBeNull()
    expect(items[2].label).toBe("toilet seat")
    expect(items[3].label).toBe("Requested item")
    expect(items[3].quantity).toBe("1")
  })

  it("keeps an earlier choice when moving on and can move back", () => {
    const items = selectAiItem(resolveAiOrder(order()), 1, "brush-3")

    expect(items[1].selectedProductId).toBe("brush-3")
    expect(items[1].quantity).toBe("10")
    expect(firstPendingChoice(items)).toBe(3)
    expect(hasPendingChoice(items)).toBe(true)
    expect(choicePosition(items, 3)).toEqual({ current: 2, total: 2 })
    expect(previousChoice(items, 3)).toBe(1)
    expect(nextChoice(items, 1)).toBe(3)
    expect(hasPendingChoice(selectAiItem(items, 3, "tile-1"))).toBe(false)
  })

  it("continues indexes when another search is appended", () => {
    const existing = resolveAiOrder(order())
    const incoming = resolveAiOrder({
      intent: "create_order",
      items: [{ product_name: "sand", quantity: 3, unit: "bag", products: [match("sand", "River Sand")] }],
    })

    const combined = appendAiItems(existing, incoming)

    expect(combined.map((item) => item.index)).toEqual([0, 1, 2, 3, 4])
    expect(combined[4].label).toBe("sand")
    expect(combined[4].selectedProductId).toBe("sand")
    expect(appendAiItems(combined, incoming).map((item) => item.index)).toEqual([0, 1, 2, 3, 4, 5])
  })
})
