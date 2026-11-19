import { NavLink } from "react-router-dom"

const links = [
  { to: "/products", label: "Products" },
  { to: "/categories", label: "Categories" },
  { to: "/units", label: "Units" },
  { to: "/inventory", label: "Inventory" },
]

export function Sidebar() {
  return (
    <aside className="flex w-full shrink-0 flex-col border-b border-line bg-pine text-stone-100 md:w-60 md:border-b-0 md:border-r">
      <div className="px-5 py-4 md:py-6">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-300">Yard office</p>
        <p className="font-display mt-1 text-2xl leading-none">Catalogue</p>
      </div>
      <nav className="flex gap-1 overflow-x-auto px-3 pb-4 md:flex-col">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            className={({ isActive }) =>
              `whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium ${isActive ? "bg-white/15 text-white" : "text-stone-200 hover:bg-white/10"}`
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
