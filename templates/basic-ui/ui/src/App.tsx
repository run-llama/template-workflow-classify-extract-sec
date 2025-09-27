import { Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import { ApiProvider, ApiClients, createWorkflowsClient } from "@llamaindex/ui";

const deploymentName =
  import.meta.env.VITE_LLAMA_DEPLOY_DEPLOYMENT_NAME || "default";
const api: ApiClients = {
  workflowsClient: createWorkflowsClient({
    baseUrl: `/deployments/${deploymentName}`,
  }),
};

export default function App() {
  return (
    <ApiProvider clients={api}>
      <Routes>
        <Route path="/" element={<Home />} />
      </Routes>
    </ApiProvider>
  );
}
