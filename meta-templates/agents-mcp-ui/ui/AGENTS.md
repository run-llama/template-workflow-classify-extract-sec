This is a vite built react project. It uses tailwindcss for styling, react-router, and is meant to be built into a static single page application (SPA).

When applicable, use the `@llamaindex/ui` library to build the UI. It provides a React component library for building UI components that interact with the workflow server.

`@llamaindex/ui` provides:
- react hooks for interacting with the workflow server, such as `useWorkflowRun`, `useWorkflowHandler`, `useWorkflowEvents`, etc. Search the llama-index-ui documentation via the MCP tool for more details.
- Document centric components, such as pdf viewers, as well as components specifically integrated with LlamaCloud, such as extracted data viewers.
- It provides ShadCN based primitive components, such as button, card, etc.
  
The components are currently undocumented. Explore its node_modules and LSP completions to find and use the components you need.

When passing files to the workflow server, first upload them to LlamaCloud, and pass the file reference to the workflow server in the StartEvent. See the `FileUpload` component. Make use of other patterns from other templates. Use the `tmpl` MCP tool to find examples.

Never use the workflow API directly. Always interact with it through the hooks.

### System Tools:
- Install missing dependencies. Use tools at your disposal to find correct dependencies.
- Use `pnpm` for js code dependencies.


### Linting:

Make sure to run lints, tests, etc, to validate that the code is correct and runnable

- `build` - runs the vite build process
- `lint` - runs the typescript compiler to check for errors
- `format` - runs the prettier formatter to format the code
- `format-check` - runs the prettier formatter to check the code for formatting errors
- `all-check` - runs the linting, formatting, and build processes
- `all-fix` - runs the linting, formatting, and build processes, and fixes any errors. Prefer using this over `all-check`, as it will just fix things, and tell you if there's anything additional that needs to be fixed.
