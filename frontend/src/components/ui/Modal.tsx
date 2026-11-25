import { useEffect, type ReactNode } from "react"

export function Modal({
  title,
  children,
  onClose,
}: {
  title: string
  children: ReactNode
  onClose: () => void
}) {
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose()
    }
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center">
      <button type="button" aria-label="Close dialog" className="absolute inset-0 bg-ink/40" onClick={onClose} />
      <div role="dialog" aria-modal="true" aria-labelledby="modal-title" className="relative w-full max-w-md rounded-xl border border-line bg-white p-5 shadow-card">
        <h2 id="modal-title" className="font-display text-xl text-ink">
          {title}
        </h2>
        <div className="mt-3 text-sm text-stone-700">{children}</div>
      </div>
    </div>
  )
}
