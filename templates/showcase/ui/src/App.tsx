import { Routes, Route, Link, useLocation } from "react-router-dom";
import Home from "./pages/Home";
import FanOutPage from "./pages/fanout/page";
import SnapshotQueryPage from "./pages/state/query-page";
import { ApiProvider, ApiClients, createWorkflowsClient } from "@llamaindex/ui";
import SignalPage from "./pages/state/signal-page";
import StreamPage from "./pages/stream/page";
import PausePage from "./pages/pause/page";

const deploymentName =
  import.meta.env.VITE_LLAMA_DEPLOY_DEPLOYMENT_NAME || "default";
const api: ApiClients = {
  workflowsClient: createWorkflowsClient({
    baseUrl: `/deployments/${deploymentName}`,
  }),
};

function BackHomeButton() {
  const location = useLocation();
  const isHome = location.pathname === "/";
  if (isHome) return null;
  return (
    <div className="fixed top-3 left-3 z-50">
      <Link
        to="/"
        aria-label="Back to Home"
        className="inline-flex items-center gap-1 rounded-full border px-3 py-1.5 text-sm bg-white/70 dark:bg-zinc-900/60 hover:bg-white/90 dark:hover:bg-zinc-900/80 border-zinc-200/70 dark:border-zinc-800/70 backdrop-blur text-zinc-700 dark:text-zinc-200"
      >
        <span aria-hidden>←</span>
        <span>Home</span>
      </Link>
    </div>
  );
}

export default function App() {
  return (
    <ApiProvider clients={api}>
      <BackHomeButton />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/streaming" element={<StreamPage />} />
        <Route path="/stateful-query" element={<SnapshotQueryPage />} />
        <Route path="/stateful-signal" element={<SignalPage />} />
        <Route path="/fan-out" element={<FanOutPage />} />
        <Route path="/pause-for-input" element={<PausePage />} />
      </Routes>
    </ApiProvider>
  );
}
