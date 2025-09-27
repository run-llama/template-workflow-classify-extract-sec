"""Auto-resolution algorithms for template synchronization."""

from __future__ import annotations

import difflib
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from ..templates import (
    parse_template_variables,
    render_jinja_string,
    run_copier_quietly,
)


def _line_has_jinja_markers(line: str) -> bool:
    """Return True if the line appears to contain Jinja syntax."""
    return ("{{" in line) or ("{%" in line) or ("{#" in line)


def _build_expected_to_template_index_map(
    template_lines: List[str], expected_lines: List[str]
) -> Dict[int, int]:
    """Build a best-effort map from expected line index to template line index."""
    matcher = difflib.SequenceMatcher(
        None, template_lines, expected_lines, autojunk=False
    )
    mapping: Dict[int, int] = {}
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            span = min(i2 - i1, j2 - j1)
            for k in range(span):
                mapping[j1 + k] = i1 + k
        else:
            for j in range(j1, j2):
                mapping.setdefault(j, i1)
    if expected_lines:
        mapping.setdefault(len(expected_lines), len(template_lines))
    return mapping


def attempt_chunk_based_jinja_resolution(
    template_dir: Path, template_file: Path, expected_content: str, actual_content: str
) -> Optional[str]:
    """Attempt a general chunk-based resolution using difflib hunks."""
    if not template_file.exists():
        return None

    with open(template_file, "r", encoding="utf-8") as f:
        template_content = f.read()

    template_lines = template_content.splitlines()
    expected_lines = expected_content.splitlines()
    actual_lines = actual_content.splitlines()

    exp_to_tpl = _build_expected_to_template_index_map(template_lines, expected_lines)

    matcher = difflib.SequenceMatcher(
        None, expected_lines, actual_lines, autojunk=False
    )

    new_template_lines = list(template_lines)
    delta_offset = 0

    def tpl_index_from_expected(exp_index: int) -> int:
        return exp_to_tpl.get(exp_index, len(new_template_lines)) + delta_offset

    def safe_region_has_jinja(t_start: int, t_end: int) -> bool:
        for t in range(max(0, t_start), min(len(new_template_lines), t_end)):
            if _line_has_jinja_markers(new_template_lines[t]):
                return True
        return False

    changes_made = False

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        tpl_start = tpl_index_from_expected(i1)
        tpl_end = tpl_index_from_expected(i2)

        if tag in ("replace", "delete"):
            if safe_region_has_jinja(tpl_start, tpl_end):
                continue

        if tag == "insert":
            insert_lines = actual_lines[j1:j2]
            left_ctx = max(0, tpl_start - 1)
            right_ctx = min(len(new_template_lines), tpl_start + 1)
            if any(
                _line_has_jinja_markers(new_template_lines[t])
                for t in range(left_ctx, right_ctx)
            ):
                continue
            new_template_lines[tpl_start:tpl_start] = insert_lines
            delta_offset += len(insert_lines)
            changes_made = True
        elif tag == "delete":
            del_count = max(0, tpl_end - tpl_start)
            if del_count > 0:
                del new_template_lines[tpl_start:tpl_end]
                delta_offset -= del_count
                changes_made = True
        elif tag == "replace":
            replacement_lines = actual_lines[j1:j2]
            del_count = max(0, tpl_end - tpl_start)
            new_template_lines[tpl_start:tpl_end] = replacement_lines
            delta_offset += len(replacement_lines) - del_count
            changes_made = True

    if not changes_made:
        return None

    proposed_content = "\n".join(new_template_lines)
    if not proposed_content.endswith("\n"):
        proposed_content += "\n"

    if validate_auto_resolved_template(
        template_dir, template_file, proposed_content, actual_content
    ):
        return proposed_content

    return None


def validate_auto_resolved_template(
    template_dir: Path,
    template_file: Path,
    resolved_content: str,
    expected_materialized_content: str,
) -> bool:
    """Validate that auto-resolved template produces expected output."""
    original_content: Optional[str] = None
    if template_file.exists():
        with open(template_file, "r", encoding="utf-8") as f:
            original_content = f.read()

    try:
        template_file.parent.mkdir(parents=True, exist_ok=True)
        with open(template_file, "w", encoding="utf-8") as f:
            f.write(resolved_content)

        with tempfile.TemporaryDirectory() as temp_dir:
            test_proj = Path(temp_dir) / "validation-proj"

            run_copier_quietly(
                str(template_dir),
                str(test_proj),
                parse_template_variables(template_dir),
            )

            relative_template_path = template_file.relative_to(template_dir)

            if relative_template_path.name.endswith(".jinja"):
                materialized_path_str = str(relative_template_path).removesuffix(
                    ".jinja"
                )
            else:
                materialized_path_str = str(relative_template_path)

            variables = parse_template_variables(template_dir)
            materialized_path_str = render_jinja_string(
                materialized_path_str, variables, template_dir
            )

            materialized_file = test_proj / materialized_path_str

            if not materialized_file.exists():
                return False

            with open(materialized_file, "r", encoding="utf-8") as f:
                validation_actual = f.read()

            expected_stripped = expected_materialized_content.strip()
            actual_stripped = validation_actual.strip()

            return actual_stripped == expected_stripped
    except Exception:
        return False
    finally:
        if original_content is not None:
            with open(template_file, "w", encoding="utf-8") as f:
                f.write(original_content)
