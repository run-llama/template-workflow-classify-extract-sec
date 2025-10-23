from __future__ import annotations

import re
from pathlib import Path

from tmpl.mcp.search import search_templates_impl, format_results_pretty


def test_search_finds_python_content() -> None:
    # basic template contains a recognizable string in workflow.py
    results = search_templates_impl("Hello from the basic template", limit=5)
    paths = [r.path for r in results]
    assert any("templates/basic/src/basic/workflow.py" in p for p in paths)


def test_search_finds_by_filename_tokens() -> None:
    # Should be able to find by file path token, e.g., App.tsx
    results = search_templates_impl("App.tsx", limit=5)
    paths = [r.path for r in results]
    assert any("templates/basic-ui/ui/src/App.tsx" in p for p in paths)


def test_search_returns_workflow_results() -> None:
    # Test that search returns proper result objects
    results = search_templates_impl("workflow.py", limit=5)
    assert len(results) > 0
    assert any(r.path.endswith("workflow.py") for r in results)
    # Check structure
    for r in results:
        assert hasattr(r, "path")
        assert hasattr(r, "score")
        assert hasattr(r, "matches")


def test_pretty_formatter_marks_only_match_lines() -> None:
    # Pick a file with multiple matches close together to test merging
    results = search_templates_impl("workflows", limit=3, context_lines=1)
    pretty = format_results_pretty(results)
    # No duplicated line numbers; every line number should occur once per file block
    blocks = pretty.splitlines()
    # Heuristic checks: ensure '*' exists and context lines use space
    assert any(re.match(r"\s+\d+\*\s", line) for line in blocks)
    assert any(re.match(r"\s+\d+\s\s", line) for line in blocks)


def test_pyproject_blank_line_not_starred(tmp_path: Path) -> None:
    # Create mock templates tree with a pyproject containing a blank line near a non-matching key
    mock_tmpl = tmp_path / "templates" / "mock"
    mock_tmpl.mkdir(parents=True, exist_ok=True)
    pyproj = mock_tmpl / "pyproject.toml"
    pyproj.write_text(
        """
[project]
requires-python = ">=3.10"
readme = "README.md"
dependencies = [
    "llama-index-workflows>=2.5.0,<3.0.0"
]

[tool.tmpl]
env_files = [".env"]


default = "mock.workflow:workflow"
""".lstrip(),
        encoding="utf-8",
    )

    results = search_templates_impl(
        "workflows", root=tmp_path, limit=5, context_lines=2
    )
    pretty = format_results_pretty(results)

    # Extract only the block for our mock file
    lines = pretty.splitlines()
    capturing = False
    block: list[str] = []
    for line in lines:
        if line.startswith("templates/mock/pyproject.toml "):
            capturing = True
            block = []
            continue
        if capturing and line and not line.startswith("  "):
            # Next file header reached
            break
        if capturing:
            block.append(line)

    # Ensure any starred line actually contains the query token
    for line in block:
        if line.strip() and "*" in line:
            # After the indicator, the text should contain 'workflows'
            text = line.split("*", 1)[1].strip()
            assert "workflows" in text.lower()
