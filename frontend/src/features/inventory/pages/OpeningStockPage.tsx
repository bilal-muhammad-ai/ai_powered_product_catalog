import { useNavigate } from "react-router-dom"
import { createMovement } from "../../../api/inventory"
import { PageHeader } from "../../../components/ui"
import { StockDocumentForm } from "../components/StockDocumentForm"

export function OpeningStockPage() {
  const navigate = useNavigate()
  return (
    <div>
      <PageHeader
        title="Opening stock"
        lede="Use this once, when the yard is first counted. Later additions go through Receive stock."
      />
      <StockDocumentForm
        mode="opening"
        onCancel={() => navigate("/inventory")}
        onSubmit={async (body) => {
          const saved = await createMovement("opening-stock", body)
          navigate(`/inventory/transactions/${saved.id}`)
        }}
      />
    </div>
  )
}
