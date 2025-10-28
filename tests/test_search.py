from __future__ import annotations

import re
from pathlib import Path

import pytest

from tmpl.mcp.search import search_templates_impl, format_results_pretty, get_template


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


# ============================================================================
# get_template tests
# ============================================================================


def test_get_template_returns_file_with_line_numbers() -> None:
    """Test that get_template returns file content with line numbers."""
    result = get_template("basic/src/basic/workflow.py")
    lines = result.splitlines()

    # Should have line numbers
    assert len(lines) > 0
    # First line should be "     1| from workflows import ..."
    assert lines[0].startswith("     1|")
    assert "from workflows import" in lines[0]

    # Check that line numbers are formatted correctly (right-aligned to 6 chars)
    for i, line in enumerate(lines, start=1):
        if line.startswith("//"):  # Skip omission notice
            break
        assert line.startswith(f"{i:6}|")


def test_get_template_with_start_line() -> None:
    """Test that start_line parameter works correctly."""
    result = get_template("basic/src/basic/workflow.py", start_line=14)
    lines = result.splitlines()

    # Should start at line 14
    assert lines[0].startswith("    14|")
    assert "class BasicWorkflow" in lines[0]


def test_get_template_with_end_line() -> None:
    """Test that end_line parameter works correctly."""
    result = get_template("basic/src/basic/workflow.py", end_line=5)
    lines = result.splitlines()

    # Should end at line 5
    assert len(lines) == 5
    assert lines[-1].startswith("     5|")


def test_get_template_with_line_range() -> None:
    """Test that start_line and end_line work together."""
    result = get_template("basic/src/basic/workflow.py", start_line=14, end_line=21)
    lines = result.splitlines()

    # Should have exactly 8 lines (14-21 inclusive)
    assert len(lines) == 8
    assert lines[0].startswith("    14|")
    assert lines[-1].startswith("    21|")
    assert "class BasicWorkflow" in lines[0]
    assert "StopEvent" in lines[-1]


def test_get_template_max_lines_truncation() -> None:
    """Test that max_lines parameter truncates output."""
    result = get_template("basic/src/basic/workflow.py", max_lines=10)
    lines = result.splitlines()

    # Should have 10 content lines + 1 omission notice
    assert len(lines) == 11
    assert lines[-1].startswith("//")
    assert "more line(s) omitted" in lines[-1]

    # Should show exactly 10 lines of content
    assert lines[9].startswith("    10|")


def test_get_template_range_with_truncation() -> None:
    """Test that max_lines works with line range."""
    result = get_template(
        "basic/src/basic/workflow.py", start_line=10, end_line=25, max_lines=5
    )
    lines = result.splitlines()

    # Should have 5 content lines + omission notice
    assert len(lines) == 6
    assert lines[0].startswith("    10|")
    assert lines[4].startswith("    14|")
    assert "more line(s) omitted" in lines[-1]


def test_get_template_invalid_path() -> None:
    """Test that invalid path raises ValueError."""
    with pytest.raises(ValueError, match="Template file not found"):
        get_template("nonexistent/file.py")


def test_get_template_clamping_out_of_range() -> None:
    """Test that out-of-range line numbers are clamped."""
    # Request lines beyond end of file
    result = get_template("basic/src/basic/workflow.py", start_line=1, end_line=10000)
    lines = result.splitlines()

    # Should return all lines without error
    assert len(lines) > 0
    assert not any("omitted" in line for line in lines)


def test_get_template_start_greater_than_end() -> None:
    """Test that start > end is handled gracefully."""
    result = get_template("basic/src/basic/workflow.py", start_line=20, end_line=10)
    lines = result.splitlines()

    # Should return empty or clamped range
    assert len(lines) == 0


def test_get_template_no_truncation_for_small_files() -> None:
    """Test that small files don't show omission notice."""
    result = get_template("basic/src/basic/workflow.py")
    lines = result.splitlines()

    # Should not have omission notice for a file under 1000 lines
    assert not any("omitted" in line for line in lines)


def test_get_template_line_number_alignment() -> None:
    """Test that line numbers are properly right-aligned to 6 characters."""
    result = get_template("basic/src/basic/workflow.py")
    lines = result.splitlines()

    for line in lines:
        if line.startswith("//"):  # Skip omission notice
            continue
        # Line number should be exactly 6 chars before the pipe
        parts = line.split("|", 1)
        assert len(parts) == 2
        assert len(parts[0]) == 6
        assert parts[0].strip().isdigit()
