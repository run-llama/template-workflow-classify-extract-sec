Template Manager (tmpl)
-----------------------

This directory contains the template monorepo manager, exposed via the `tmpl` CLI. It helps you develop, validate, and publish individual templates under `templates/`, using a rendered test project under `rendered/`.

Use `uv` to run commands:

```bash
uv run tmpl --help
```

### CLI commands

- **list**: Show configured templates and (optionally) remotes/branches.
  - `uv run tmpl list`
  - `uv run tmpl list --detail`
- **changed**: Detect which templates changed between two refs (used by CI).
  - `uv run tmpl changed --base <ref> --head <ref> --format json`
- **clone**: Initial import of a template as a git subtree.
  - `uv run tmpl clone <template>`
- **merge**: Pull upstream changes from the template's remote (git subtree pull).
  - `uv run tmpl merge <template>`
- **mirror**: Push `templates/<template>` to its upstream remote (git subtree push).
  - `uv run tmpl mirror <template>`
- **regenerate**: Re-render the test project under `rendered/<template>` using Copier.
  - `uv run tmpl regenerate <template>`
- **check-regeneration**: Ensure `rendered/<template>` matches what the template would generate.
  - `uv run tmpl check-regeneration <template>`
- **check-python**: Run Python format/lint/type checks within `rendered/<template>`.
  - `uv run tmpl check-python <template> [--fix]`
- **check-javascript**: Run JS/TS formatting/lint checks within `rendered/<template>`.
  - `uv run tmpl check-javascript <template> [--fix]`
- **check-template**: Compare `rendered/<template>` with the expected template output; optionally copy changes back to `templates/<template>`.
  - `uv run tmpl check-template <template> [--fix] [--fix-format]`
- **init-scripts**: Add helpful dev scripts to the template (Python and JS/TS).
  - `uv run tmpl init-scripts <template>`
- **export-metrics**: Export GitHub repo traffic to PostHog (see Metrics section).
  - `uv run tmpl export-metrics [--dry-run] [--print] [--backfill]`
- **all**: Run any subcommand across all templates.
  - `uv run tmpl all check-python --fix`

### Development workflow

The intended loop is to work in the rendered project, validate, sync to the template, and then release:

1. **Render the test project**: create or refresh `rendered/<template>`
   - `uv run tmpl regenerate <template>`
2. **Develop in rendered**: make changes inside `rendered/<template>`
   - Python: `uv run tmpl check-python <template> --fix`
   - JS/TS (if present): `uv run tmpl check-javascript <template> --fix`
3. **Sync changes back to the template**: copy diffs from rendered into `templates/<template>`
   - `uv run tmpl check-template <template> --fix`
   - Optional: `--fix-format` runs Python and JS formatters before syncing
4. **Verify regeneration**: ensure a clean re-render produces the same result
   - `uv run tmpl check-regeneration <template>`
5. **Commit and open a PR**
6. **Release**: after merge to `main`, the mirror workflow pushes to the upstream template repo; or run manually:
   - `uv run tmpl mirror <template>`

Tip: See the root `AGENTS.md` for a quick-start and project-level checks.

### GitHub Actions

This repo includes workflows that use the CLI under the hood:

- **templates-ci** (`.github/workflows/ci.yml`)
  - Triggers on PRs and pushes that touch templates.
  - Steps:
    - Detect changed templates via `uv run tmpl changed --format json --github-output`.
    - For each changed template: run `check-python`, `check-javascript`, `check-template`, and `check-regeneration`.

- **mirror-templates** (`.github/workflows/mirror.yml`)
  - Triggers on push to `main` and via manual dispatch.
  - Uses `uv run tmpl changed` to detect changed templates on push; or a manual input.
  - Mirrors each changed template using `uv run tmpl mirror <template>` to its configured upstream. Requires `GH_PAT` with push permission.

- **export-template-metrics** (`.github/workflows/export-template-metrics.yml`)
  - Scheduled and manually runnable job to export metrics to PostHog.
  - Runs `uv run tmpl export-metrics` with `GH_PAT` and `POSTHOG_API_KEY`.

### PostHog metrics

The `export-metrics` command fetches 14-day GitHub traffic (clones and unique cloners) for each configured template repository and emits PostHog events.

- **Required environment**:
  - GitHub: `GITHUB_TOKEN` or `GITHUB_PAT`
  - PostHog: `POSTHOG_API_KEY` (or `POSTHOG_PROJECT_API_KEY`), optional `POSTHOG_HOST` (defaults to `https://us.posthog.com`)

- **Events emitted**:
  - `template_repo_clones_total`
    - properties: `template`, `owner`, `repo`, `clones_total`, `clones_unique_total`, `days_count`, `window_start`, `window_end`, `dedupe_ts`
    - timestamp: end of the window
  - `template_repo_clones_daily`
    - properties: `template`, `owner`, `repo`, `day`, `clones_day`, `clones_uniques_day`, `dedupe_ts`
    - timestamp: that day's timestamp; with `--backfill` it emits one per day in the window; otherwise only the most recent day

- **Examples**:
  - Dry run and print results locally: `uv run tmpl export-metrics --dry-run --print`
  - Backfill daily events for the entire 14-day window: `uv run tmpl export-metrics --backfill`

### Notes

- Remote URLs/branches for templates are configured via `.github/templates-remotes.yml` and loaded by the CLI.
- The CLI operates on two key locations: `templates/<template>` (source) and `rendered/<template>` (materialized output used for validation and development).

