# Llama Deploy

This application uses LlamaDeploy. For more information see [the docs](https://developers.llamaindex.ai/python/cloud/llamadeploy/getting-started)

# Getting Started

1. install `uv` if you haven't `brew install uv`
2. run `uvx llamactl serve`
3. Visit http://localhost:4501/


# Organization

- `src` contains python workflow sources. The name of the deployment here is defined as `research`
- `ui` contains a vite app powered by llama-ui. It calls the local workflow server via api requests. See http://localhost:4501/docs for openAPI docs
