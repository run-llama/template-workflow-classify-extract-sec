# Contributor Workflow

This project uses a "materialized" approach for template development. You make changes to a generated project (`test-proj/`) and then use a script to copy those changes back into the template source. This allows for a more interactive development experience.

The core script for this workflow is `copier/copy_utils.py`.

## Development Steps

### 1. Initial Setup

Ensure your repository is in a clean state (no uncommitted changes). Regenerate the `test-proj` directory to ensure it's synchronized with the latest version of the template.

```bash
# Regenerate test-proj from the template
uv run --script copier/copy_utils.py regenerate
```

### 2. Develop and Test in `test-proj`

Make all your desired code changes directly within the `test-proj/` directory. Treat it as a standard project: run development servers, add dependencies, and test your changes live.

```bash
# Example: Work on the UI
cd test-proj/ui
npm install
npm dev
```

Run validation checks to ensure your changes are correct before propagating them.

```bash
# From the project root directory
./copier/copy_utils.py check-python
# or within test-proj/, run `uv run hatch run all` or the individual script commands, such as `uv run hatch run format`
./copier/copy_utils.py check-javascript
# or within test-proj/ui/, run `npm run all`, or the individual script commands such as `npm run format`
```

### 3. Commit Your Development Work

Once you are satisfied with your changes in `test-proj`, it's a good idea to commit them so that you can revert back in case something goes wrong

```bash
git add .
git commit -m "WIP: Implement new feature in test-proj"
```

### 4. Propagate Changes to the Template

Use the `fix-template` command to automatically copy your changes from `test-proj` back into the template source files. It compares `test-proj` against what the current template would generate, showing only meaningful differences.

```bash
# Check what would change (recommended first step)
./copier/copy_utils.py check-template

# Apply changes automatically
./copier/copy_utils.py check-template --fix

# or "fix everything from the materialized
./copier/copy_utils.py check-template --fix-format
```

`fix-template` provides:

- **Automatic Jinja Resolution**: Resolves simple template variable changes (project names, versions, etc.)
- **Gitignore Respect**: Only considers files that would be tracked by git, ignoring build artifacts
- **Selective Copying**: Copies non-templated files and auto-resolved template files back to the template

### 5. Handle Remaining Manual Updates

For complex `.jinja` files that can't be auto-resolved, you'll need manual intervention:

1. Open the modified file in `test-proj` (e.g., `test-proj/pyproject.toml`)
2. Open the corresponding template file (e.g., `pyproject.toml.jinja`)
3. Carefully apply the changes, ensuring you retain or add the necessary Jinja templating logic

The tool will indicate which files need manual resolution.

### 6. Verify Template Integrity

After propagating all changes, verify that the template is consistent by running the `check-regeneration` command. This command regenerates `test-proj` and checks for any differences.

```bash
uv run --script copier/copy_utils.py check-regeneration
```

If this command reports any differences, it indicates that a change was not correctly propagated to the template. You will need to identify the discrepancy, fix the template file(s), and run the check again. A successful run will report no differences.
