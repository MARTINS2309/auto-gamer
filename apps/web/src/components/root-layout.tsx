import { Link, useRouterState } from "@tanstack/react-router"
import { LayoutDashboard, Gamepad2, Play, Settings, Moon, Sun, Monitor } from "lucide-react"
import { useTheme } from "next-themes"
import { Button } from "./ui/button"
import { cn } from "@/lib/utils"
import { useState, useEffect } from "react"

const navItems = [
  { path: "/", label: "Dashboard", icon: LayoutDashboard },
  { path: "/roms", label: "ROM Library", icon: Gamepad2 },
  { path: "/runs", label: "Runs", icon: Play },
  { path: "/config", label: "Config", icon: Settings },
]

function CRTOverlay() {
  return (
    <div className="crt-overlay">
      <div className="crt-scanlines" />
      <div className="crt-vignette" />
      <div className="crt-glow-bar" />
    </div>
  )
}

function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
    >
      <Sun className="size-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
      <Moon className="absolute size-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
      <span className="sr-only">Toggle theme</span>
    </Button>
  )
}

function CRTToggle() {
  const [enabled, setEnabled] = useState(false)

  useEffect(() => {
    if (enabled) {
      document.body.classList.add("crt-enabled")
    } else {
      document.body.classList.remove("crt-enabled")
    }
  }, [enabled])

  return (
    <Button
      variant={enabled ? "default" : "ghost"}
      size="icon"
      onClick={() => setEnabled(!enabled)}
      title="Toggle CRT effect"
    >
      <Monitor className="size-5" />
    </Button>
  )
}

export function RootLayout({ children }: { children: React.ReactNode }) {
  const router = useRouterState()
  const currentPath = router.location.pathname

  return (
    <div className="flex min-h-svh bg-background">
      {/* Sidebar */}
      <aside className="w-56 border-r border-border bg-sidebar flex flex-col">
        {/* Logo */}
        <div className="h-14 flex items-center px-4 border-b border-border">
          <Link to="/" className="flex items-center gap-2">
            <Gamepad2 className="size-6 text-primary" />
            <span className="font-semibold text-lg">Retro Runner</span>
          </Link>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-3 space-y-1">
          {navItems.map((item) => {
            const isActive = item.path === "/"
              ? currentPath === "/"
              : currentPath.startsWith(item.path)
            return (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <item.icon className="size-4" />
                {item.label}
              </Link>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="p-3 border-t border-border flex items-center gap-1">
          <ThemeToggle />
          <CRTToggle />
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>

      <CRTOverlay />
    </div>
  )
}
