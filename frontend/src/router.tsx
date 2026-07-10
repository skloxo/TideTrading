import { Suspense, lazy, type ComponentType } from "react";
import { createBrowserRouter } from "react-router-dom";
import { Layout } from "@/components/layout/Layout";

const Home = lazy(() => import("@/pages/Home").then((m) => ({ default: m.Home })));
const Agent = lazy(() => import("@/pages/Agent").then((m) => ({ default: m.Agent })));
const RunDetail = lazy(() =>
  import("@/pages/RunDetail").then((m) => ({ default: m.RunDetail })),
);
const Compare = lazy(() =>
  import("@/pages/Compare").then((m) => ({ default: m.Compare })),
);
const Settings = lazy(() =>
  import("@/pages/Settings").then((m) => ({ default: m.Settings })),
);
const Xueqiu = lazy(() =>
  import("@/pages/Xueqiu").then((m) => ({ default: m.Xueqiu })),
);
const XueqiuAuth = lazy(() =>
  import("@/pages/XueqiuAuth").then((m) => ({ default: m.XueqiuAuth })),
);
const Runtime = lazy(() =>
  import("@/pages/Runtime").then((m) => ({ default: m.Runtime })),
);
const Reports = lazy(() =>
  import("@/pages/Reports").then((m) => ({ default: m.Reports })),
);
const Correlation = lazy(() =>
  import("@/pages/Correlation").then((m) => ({ default: m.Correlation })),
);
const AlphaZoo = lazy(() =>
  import("@/pages/AlphaZoo").then((m) => ({ default: m.AlphaZoo })),
);
const Monitor = lazy(() =>
  import("@/pages/Monitor").then((m) => ({ default: m.Monitor })),
);
const Logs = lazy(() =>
  import("@/pages/Logs").then((m) => ({ default: m.Logs })),
);
const TenantManagement = lazy(() =>
  import("@/pages/TenantManagement").then((m) => ({ default: m.TenantManagement })),
);
const GlobalDashboard = lazy(() =>
  import("@/pages/GlobalDashboard").then((m) => ({ default: m.GlobalDashboard })),
);
const ProjectSettings = lazy(() =>
  import("@/pages/ProjectSettings").then((m) => ({ default: m.ProjectSettings })),
);
const TenantLogin = lazy(() =>
  import("@/pages/TenantLogin").then((m) => ({ default: m.TenantLogin })),
);
const TenantRegister = lazy(() =>
  import("@/pages/TenantRegister").then((m) => ({ default: m.TenantRegister })),
);

function PageLoader() {
  return (
    <div className="flex h-[60vh] items-center justify-center text-muted-foreground">
      Loading…
    </div>
  );
}

function wrap(Component: ComponentType) {
  return (
    <Suspense fallback={<PageLoader />}>
      <Component />
    </Suspense>
  );
}

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: wrap(Home) },
      { path: "/dashboard", element: wrap(GlobalDashboard) },
      { path: "/agent", element: wrap(Agent) },
      { path: "/runtime", element: wrap(Runtime) },
      { path: "/reports", element: wrap(Reports) },
      { path: "/settings", element: wrap(Settings) },
      { path: "/project-settings", element: wrap(ProjectSettings) },
      { path: "/xueqiu", element: wrap(Xueqiu) },
      { path: "/monitor", element: wrap(Monitor) },
      { path: "/logs", element: wrap(Logs) },
      { path: "/tenants", element: wrap(TenantManagement) },
      { path: "/runs/:runId", element: wrap(RunDetail) },
      { path: "/compare", element: wrap(Compare) },
      { path: "/correlation", element: wrap(Correlation) },
      { path: "/alpha-zoo", element: wrap(AlphaZoo) },
      { path: "/alpha-zoo/bench", element: wrap(AlphaZoo) },
      { path: "/alpha-zoo/compare", element: wrap(AlphaZoo) },
      { path: "/alpha-zoo/:alphaId", element: wrap(AlphaZoo) },
    ],
  },
  {
    path: "/xueqiu/auth",
    element: wrap(XueqiuAuth),
  },
  // Standalone pages — outside Layout, no auth required to render
  { path: "/login", element: wrap(TenantLogin) },
  { path: "/claim", element: wrap(TenantRegister) },
]);
