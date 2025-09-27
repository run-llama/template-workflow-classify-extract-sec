import {
  ApiClients,
  cloudApiClient,
  createWorkflowsClient,
  createWorkflowsConfig,
} from "@llamaindex/ui";
import { AGENT_NAME } from "./config";

const platformToken = import.meta.env.VITE_LLAMA_CLOUD_API_KEY;
const apiBaseUrl = import.meta.env.VITE_LLAMA_CLOUD_BASE_URL;
const projectId = import.meta.env.VITE_LLAMA_DEPLOY_PROJECT_ID;

// Configure the platform client
cloudApiClient.setConfig({
  ...(apiBaseUrl && { baseUrl: apiBaseUrl }),
  headers: {
    // optionally use a backend API token scoped to a project. For local development,
    ...(platformToken && { authorization: `Bearer ${platformToken}` }),
    // This header is required for requests to correctly scope to the agent's project
    // when authenticating with a user cookie
    ...(projectId && { "Project-Id": projectId }),
  },
});

const workflowsClient = createWorkflowsClient(
  createWorkflowsConfig({
    baseUrl: `/deployments/${AGENT_NAME}/`,
    headers: {
      ...(platformToken && { authorization: `Bearer ${platformToken}` }),
    },
  }),
);

const clients: ApiClients = {
  workflowsClient: workflowsClient,
  cloudApiClient: cloudApiClient,
};

export { clients };
