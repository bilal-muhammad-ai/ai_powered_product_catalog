import type { LucideIcon } from "lucide-react"
import { ClipboardList, LayoutDashboard, Package, Ruler, Tags, Warehouse, X } from "lucide-react"
import { NavLink } from "react-router-dom"

const links: { to: string; label: string; icon: LucideIcon; end?: boolean }[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/products", label: "Products", icon: Package },
  { to: "/categories", label: "Categories", icon: Tags },
  { to: "/units", label: "Units", icon: Ruler },
  { to: "/inventory", label: "Inventory", icon: Warehouse },
  { to: "/orders", label: "Orders", icon: ClipboardList },
]

export function Sidebar({
  collapsed,
  mobileOpen,
  onNavigate,
}: {
  collapsed: boolean
  mobileOpen: boolean
  onNavigate: () => void
}) {
  return (
    <aside
      className={`app-sidebar fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-pine text-stone-100 transition-[transform,width] duration-200 md:translate-x-0 ${
        mobileOpen ? "translate-x-0" : "-translate-x-full"
      } ${collapsed ? "md:w-[4.5rem]" : "md:w-64"}`}
    >
      <div className="flex items-center gap-3 px-4 py-5">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/10 font-display text-lg text-white">R</span>
        <span className={collapsed ? "min-w-0 md:sr-only" : "min-w-0"}>
          <span className="block text-[11px] font-semibold uppercase tracking-[0.18em] text-stone-300">Yard office</span>
          <span className="font-display block truncate text-xl leading-none text-white">Rehan Cement</span>
        </span>
        <button
          type="button"
          className="ml-auto inline-flex h-8 w-8 items-center justify-center rounded-lg text-stone-200 hover:bg-white/10 md:hidden"
          aria-label="Close navigation"
          onClick={onNavigate}
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
      <nav className="flex flex-1 flex-col gap-1 overflow-y-auto px-3 pb-6">
        {links.map((link) => {
          const Icon = link.icon
          return (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              title={collapsed ? link.label : undefined}
              onClick={onNavigate}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40 ${
                  collapsed ? "md:justify-center md:px-0" : ""
                } ${isActive ? "bg-white/10 text-white shadow-[inset_3px_0_0_0_#9c4221]" : "text-stone-200 hover:bg-white/10 hover:text-white"}`
              }
            >
              <Icon className="h-[1.15rem] w-[1.15rem] shrink-0" aria-hidden="true" />
              <span className={collapsed ? "md:sr-only" : ""}>{link.label}</span>
            </NavLink>
          )
        })}
      </nav>
    </aside>
  )
}
