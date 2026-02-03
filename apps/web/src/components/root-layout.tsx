import { Link, useRouterState } from "@tanstack/react-router"
import { LayoutDashboard, Gamepad2, Play, Settings } from "lucide-react"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
} from "@/components/ui/sidebar"
import { ModeToggle } from "./mode-toggle"
import { CRTToggle } from "./crt-toggle"
import { ButtonGroup } from "./ui/button-group"

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


export function RootLayout({ children }: { children: React.ReactNode }) {
  const router = useRouterState()
  const currentPath = router.location.pathname

  return (
    <SidebarProvider>
      <Sidebar collapsible="icon" className="border-r">
        <SidebarHeader>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton size="lg" asChild className="md:h-8 md:p-0">
                <Link to="/">
                  <div className="bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-8 items-center justify-center">
                    <Gamepad2 className="size-4" />
                  </div>
                  <div className="grid flex-1 text-left text-sm leading-tight">
                    <span className="truncate font-medium">Retro Runner</span>
                    <span className="truncate text-xs">AI Training</span>
                  </div>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarHeader>
        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupContent className="px-1.5 md:px-0">
              <SidebarMenu>
                {navItems.map((item) => {
                  const isActive = item.path === "/"
                    ? currentPath === "/"
                    : currentPath.startsWith(item.path)
                  return (
                    <SidebarMenuItem key={item.path}>
                      <SidebarMenuButton
                        tooltip={{ children: item.label, hidden: false }}
                        asChild
                        isActive={isActive}
                        className="px-2.5 md:px-2"
                      >
                        <Link to={item.path}>
                          <item.icon />
                          <span>{item.label}</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  )
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>
        <SidebarFooter>
          <ButtonGroup>
            <ButtonGroup>
              <ModeToggle />
            </ButtonGroup>
            <ButtonGroup>
              <CRTToggle />
            </ButtonGroup>
          </ButtonGroup>
        </SidebarFooter>
      </Sidebar>

      <SidebarInset>
        {children}
      </SidebarInset>

      <CRTOverlay />
    </SidebarProvider>
  )
}
