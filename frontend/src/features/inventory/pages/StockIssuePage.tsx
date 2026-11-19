import { useNavigate } from "react-router-dom"
import { createMovement } from "../../../api/inventory"
import { PageHeader } from "../../../components/ui"
import { StockDocumentForm } from "../components/StockDocumentForm"

export function StockIssuePage() {
  const navigate = useNavigate()
  return (
    <div>
      <PageHeader title="Stock issue" lede="Remove stock for use, damage, or any reason that is not a sale." />
      <StockDocumentForm
        mode="issue"
        onCancel={() => navigate("/inventory")}
        onSubmit={async (body) => {
          const saved = await createMovement("issues", body)
          navigate(`/inventory/transactions/${saved.id}`)
        }}
      />
    </div>
  )
}
