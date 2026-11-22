import { describe, expect, it } from "vitest"
import {
  adjustmentDelta,
  costError,
  formatPkr,
  formatQty,
  issueQuantityError,
  lineTotal,
  quantityError,
  stockStatus,
} from "./logic"

describe("inventory calculations", () => {
  it("formats PKR and decimal quantities", () => {
    expect(formatPkr("1200")).toContain("1,200")
    expect(formatQty("10.5")).toBe("10.5")
  })

  it("marks low and out of stock", () => {
    expect(stockStatus(0, 5)).toBe("out_of_stock")
    expect(stockStatus(4, 5)).toBe("low_stock")
    expect(stockStatus(6, 5)).toBe("in_stock")
    expect(stockStatus(2, null)).toBe("in_stock")
  })

  it("calculates an adjustment from the physical count", () => {
    expect(adjustmentDelta(100, 95)).toBe(-5)
    expect(adjustmentDelta(100, 105)).toBe(5)
  })

  it("rejects empty, zero, and oversize quantities", () => {
    expect(quantityError("")).toMatch(/quantity/i)
    expect(quantityError("0")).toMatch(/greater than zero/i)
    expect(quantityError("3")).toBeNull()
    expect(issueQuantityError("5", 2, true)).toMatch(/available stock/i)
    expect(issueQuantityError("1", 2, true)).toBeNull()
    expect(costError("", true)).toMatch(/unit cost/i)
    expect(costError("-1", true)).toMatch(/negative/i)
  })

  it("totals a receipt line", () => {
    expect(lineTotal(2, 1200)).toBe(2400)
  })
})
