import { Menu, PanelLeftClose, PanelLeftOpen } from "lucide-react"
import { useLocation } from "react-router-dom"

function sectionLabel(pathname: string) {
  if (pathname.startsWith("/products")) return "Products"
  if (pathname.startsWith("/categories")) return "Categories"
  if (pathname.startsWith("/units")) return "Units"
  if (pathname.startsWith("/inventory")) return "Inventory"
  if (pathname.startsWith("/orders")) return "Orders"
  return "Dashboard"
}

export function Topbar({
  collapsed,
  onOpenMobile,
  onToggleCollapsed,
}: {
  collapsed: boolean
  onOpenMobile: () => void
  onToggleCollapsed: () => void
}) {
  const { pathname } = useLocation()

  return (
    <header className="app-topbar sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-line bg-paper/95 px-4 backdrop-blur md:px-6">
      <button
        type="button"
        className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-line bg-white text-ink shadow-sm md:hidden"
        aria-label="Open navigation"
        onClick={onOpenMobile}
      >
        <Menu className="h-4 w-4" aria-hidden="true" />
      </button>
      <button
        type="button"
        className="hidden h-9 w-9 items-center justify-center rounded-lg border border-line bg-white text-ink shadow-sm md:inline-flex"
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        onClick={onToggleCollapsed}
      >
        {collapsed ? <PanelLeftOpen className="h-4 w-4" aria-hidden="true" /> : <PanelLeftClose className="h-4 w-4" aria-hidden="true" />}
      </button>
      <p className="truncate text-sm font-medium text-stone-600">{sectionLabel(pathname)}</p>
    </header>
  )
}
