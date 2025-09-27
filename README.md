# tmpl

CLI for managing multi-template monorepo.

Usage examples:

- Detect changed templates:
  - `uv run tmpl changed --format lines`
- Clone templates per mapping:
  - `uv run tmpl clone`
- Ensure remotes exist:
  - `uv run tmpl ensure-remotes`
- Mirror a template subtree:
  - `uv run tmpl mirror --template workflow-data-extraction`
- Regenerate committed test project:
  - `uv run tmpl regenerate --template workflow-data-extraction`
- Check test project sync with template output:
  - `uv run tmpl check-template --template workflow-data-extraction`

