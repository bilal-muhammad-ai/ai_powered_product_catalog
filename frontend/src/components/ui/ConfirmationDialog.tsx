import { Button } from "./Button"
import { Modal } from "./Modal"

export function ConfirmationDialog({
  title,
  message,
  confirmLabel,
  tone = "primary",
  onConfirm,
  onClose,
}: {
  title: string
  message: string
  confirmLabel: string
  tone?: "primary" | "danger"
  onConfirm: () => void
  onClose: () => void
}) {
  return (
    <Modal title={title} onClose={onClose}>
      <p>{message}</p>
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>
          Back
        </Button>
        <Button variant={tone === "danger" ? "danger" : "primary"} onClick={onConfirm}>
          {confirmLabel}
        </Button>
      </div>
    </Modal>
  )
}
