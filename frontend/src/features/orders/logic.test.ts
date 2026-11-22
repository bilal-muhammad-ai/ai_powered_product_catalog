import { describe, expect, it } from "vitest"
import { discountError, orderAmounts, priceError, quantityError } from "./logic"

describe("order calculations", () => {
  it("applies line and order discounts", () => {
    const amounts = orderAmounts(
      [
        { quantity: 2, unitPrice: 1100, discountType: "AMOUNT", discountValue: 100 },
        { quantity: 1.5, unitPrice: 80, discountType: "PERCENT", discountValue: 10 },
      ],
      "PERCENT",
      5,
    )
    expect(amounts.lines[0].total).toBe(2100)
    expect(amounts.subtotal).toBe(2320)
    expect(amounts.itemDiscount).toBe(112)
    expect(amounts.orderDiscount).toBe(110.4)
    expect(amounts.grandTotal).toBe(2097.6)
  })

  it("rejects bad quantities, prices, and discounts", () => {
    expect(quantityError("0")).toMatch(/greater than zero/i)
    expect(priceError("-1")).toMatch(/negative/i)
    expect(discountError(100, "AMOUNT", "150")).toMatch(/exceed/i)
    expect(discountError(100, "AMOUNT", "10")).toBeNull()
  })
})
