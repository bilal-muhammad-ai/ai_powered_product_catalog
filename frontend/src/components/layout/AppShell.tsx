import { useEffect, useState, type ReactNode } from "react"
import { useLocation } from "react-router-dom"
import { Sidebar } from "./Sidebar"
import { Topbar } from "./Topbar"

export function AppShell({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    setMobileOpen(false)
  }, [location.pathname])

  return (
    <div className="min-h-screen bg-paper text-ink">
      {mobileOpen ? (
        <button type="button" aria-label="Close navigation" className="app-backdrop fixed inset-0 z-30 bg-ink/40 md:hidden" onClick={() => setMobileOpen(false)} />
      ) : null}
      <Sidebar collapsed={collapsed} mobileOpen={mobileOpen} onNavigate={() => setMobileOpen(false)} />
      <div className={`app-frame flex min-h-screen flex-col transition-[padding] duration-200 ${collapsed ? "md:pl-[4.5rem]" : "md:pl-64"}`}>
        <Topbar collapsed={collapsed} onOpenMobile={() => setMobileOpen(true)} onToggleCollapsed={() => setCollapsed((value) => !value)} />
        <main className="min-w-0 flex-1 px-4 py-6 md:px-8 md:py-8">
          <div className="mx-auto w-full max-w-7xl">{children}</div>
        </main>
      </div>
    </div>
  )
}
