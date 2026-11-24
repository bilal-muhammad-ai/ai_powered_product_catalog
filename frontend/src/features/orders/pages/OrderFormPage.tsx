import { useEffect, useState } from "react"
import { useLocation, useNavigate, useParams } from "react-router-dom"
import { ErrorNote, PageHeader } from "../../../components/ui"
import { confirmOrder, createOrder, readOrder, updateOrder, type OrderBody } from "../api"
import { OrderEditor, type EditorLine } from "../components/OrderEditor"

export function OrderFormPage() {
  const { orderId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const [lines, setLines] = useState<EditorLine[] | null>(orderId ? null : [])
  const [date, setDate] = useState<string>()
  const [notes, setNotes] = useState("")
  const [discountType, setDiscountType] = useState<"AMOUNT" | "PERCENT">("AMOUNT")
  const [discountValue, setDiscountValue] = useState("0")
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const state = location.state as { error?: string } | null
    if (state?.error) setError(state.error)
  }, [location.state])

  useEffect(() => {
    if (!orderId) return
    readOrder(orderId)
      .then((order) => {
        if (order.status !== "DRAFT") {
          navigate(`/orders/${order.id}`, { replace: true })
          return
        }
        setDate(order.order_date)
        setNotes(order.notes ?? "")
        setDiscountType(order.discount_type)
        setDiscountValue(order.discount_value)
        setLines(
          order.items.map((item) => ({
            key: item.id,
            productId: item.product_id,
            name: item.product_name_snapshot,
            sku: item.sku_snapshot,
            unitId: item.unit_id,
            quantity: item.quantity,
            unitPrice: item.unit_price,
            discountType: item.discount_type,
            discountValue: item.discount_value,
          })),
        )
      })
      .catch((reason: Error) => setError(reason.message))
  }, [orderId, navigate])

  async function save(body: OrderBody, confirm: boolean) {
    const saved = orderId ? await updateOrder(orderId, body) : await createOrder(body)
    if (!confirm) {
      navigate(`/orders/${saved.id}`)
      return
    }
    try {
      const posted = await confirmOrder(saved.id)
      navigate(`/orders/${posted.id}`)
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "Could not confirm the order"
      navigate(`/orders/${saved.id}/edit`, { replace: true, state: { error: message } })
    }
  }

  return (
    <div>
      <PageHeader
        title={orderId ? "Edit draft order" : "Create order"}
        lede="Choose products, set the price for this order, and save a draft or confirm it."
      />
      <ErrorNote message={error} />
      {lines ? (
        <OrderEditor
          initialLines={lines}
          initialDate={date}
          initialNotes={notes}
          initialDiscountType={discountType}
          initialDiscountValue={discountValue}
          assist={!orderId}
          onSubmit={save}
          onCancel={() => navigate("/orders")}
        />
      ) : (
        <p className="text-sm text-stone-500">Loading order…</p>
      )}
    </div>
  )
}
