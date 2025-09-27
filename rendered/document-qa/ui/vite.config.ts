import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import dotenv from "dotenv";

dotenv.config({ path: '../.env' });

// https://vitejs.dev/config/
export default defineConfig(({}) => {
  const deploymentId = process.env.LLAMA_DEPLOY_DEPLOYMENT_URL_ID;
  const basePath = process.env.LLAMA_DEPLOY_DEPLOYMENT_BASE_PATH;
  const projectId = process.env.LLAMA_DEPLOY_PROJECT_ID;
  const port = process.env.PORT ? Number(process.env.PORT) : 3000;
  const baseUrl = process.env.LLAMA_CLOUD_BASE_URL;
  const apiKey = process.env.LLAMA_CLOUD_API_KEY;

  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      port: port,
      host: true,
    },
    build: {
      outDir: "dist",
      sourcemap: true,
    },
    base: basePath,
    define: {
      "import.meta.env.VITE_LLAMA_DEPLOY_DEPLOYMENT_NAME":
        JSON.stringify(deploymentId),
      "import.meta.env.VITE_LLAMA_DEPLOY_DEPLOYMENT_BASE_PATH": JSON.stringify(basePath),
      ...(projectId && {
        "import.meta.env.VITE_LLAMA_DEPLOY_PROJECT_ID":
          JSON.stringify(projectId),
      }),
      ...(baseUrl && {
        "import.meta.env.VITE_LLAMA_CLOUD_BASE_URL": JSON.stringify(baseUrl),
      }),
      ...(apiKey && {
        "import.meta.env.VITE_LLAMA_CLOUD_API_KEY": JSON.stringify(apiKey),
      }),
    },
  };
});
