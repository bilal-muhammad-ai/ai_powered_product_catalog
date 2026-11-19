import { useNavigate } from "react-router-dom"
import { createMovement } from "../../../api/inventory"
import { PageHeader } from "../../../components/ui"
import { AdjustmentForm } from "../components/AdjustmentForm"

export function StockAdjustmentPage() {
  const navigate = useNavigate()
  return (
    <div>
      <PageHeader
        title="Stock adjustment"
        lede="Enter the physical count. The difference from the system stock is posted as the movement."
      />
      <AdjustmentForm
        onCancel={() => navigate("/inventory")}
        onSubmit={async (body) => {
          const saved = await createMovement("adjustments", body)
          navigate(`/inventory/transactions/${saved.id}`)
        }}
      />
    </div>
  )
}
