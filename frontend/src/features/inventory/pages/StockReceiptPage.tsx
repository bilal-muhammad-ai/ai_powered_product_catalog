import { useNavigate } from "react-router-dom"
import { createMovement } from "../../../api/inventory"
import { PageHeader } from "../../../components/ui"
import { StockDocumentForm } from "../components/StockDocumentForm"

export function StockReceiptPage() {
  const navigate = useNavigate()
  return (
    <div>
      <PageHeader title="Stock receipt" lede="Record stock that arrived, without a purchase order." />
      <StockDocumentForm
        mode="receipt"
        onCancel={() => navigate("/inventory")}
        onSubmit={async (body) => {
          const saved = await createMovement("receipts", body)
          navigate(`/inventory/transactions/${saved.id}`)
        }}
      />
    </div>
  )
}
