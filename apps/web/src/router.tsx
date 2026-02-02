import { createRouter, createRootRoute, createRoute, Outlet } from "@tanstack/react-router"
import { RootLayout } from "./components/root-layout"
import { DashboardPage } from "./pages/dashboard"
import { RomsPage } from "./pages/roms"
import { RunsPage } from "./pages/runs"
import { RunDetailPage } from "./pages/run-detail"
import { ConfigPage } from "./pages/config"

const rootRoute = createRootRoute({
  component: () => (
    <RootLayout>
      <Outlet />
    </RootLayout>
  ),
})

const dashboardRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: DashboardPage,
})

const romsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/roms",
  component: RomsPage,
})

const runsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/runs",
  component: RunsPage,
})

const runDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/runs/$runId",
  component: RunDetailPage,
})

const configRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/config",
  component: ConfigPage,
})

const routeTree = rootRoute.addChildren([
  dashboardRoute,
  romsRoute,
  runsRoute,
  runDetailRoute,
  configRoute,
])

export const router = createRouter({ routeTree })

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}
