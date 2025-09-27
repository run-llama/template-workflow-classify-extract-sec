Getting Started
---------------

This project exclusively uses `uv` for package management.

To run commands, use the following format:

```bash
uv run <command>
```

or, source the .venv/bin/activate and run the command directly:

```bash
source .venv/bin/activate
<command>
```

The main entrypoint is `tmpl`.

To get started, run:

```bash
uv run tmpl --help
```

Validating CI:
-------------------

When editing a template. Make changes directly in the tests/<template-name> directory.

Then, to push changes to a template, run:

```bash
# format, typecheck, and lint before pushing to template
uv run tmpl check-python <template-name> --fix
uv run tmpl check-javascript <template-name> --fix
# push to the template. Occasionally, complex jinja templates may require manual fixes.
uv run tmpl check-template <template-name> --fix
```

When editing the src/tmpl code, make sure it passes it's own checks:

```bash
uv run hatch run all-fix
# this runs all of the following
uv run hatch run format
uv run hatch run lint
uv run hatch run typecheck
uv run hatch run test
```