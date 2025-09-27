"""Main diff generation and template comparison logic."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from ..templates import (
    map_materialized_to_template_path,
    parse_template_variables,
    run_copier_quietly,
)
from ..utils import console
from .comparator import compare_directories
from .resolver import attempt_chunk_based_jinja_resolution


def compare_with_expected_materialized(
    template_dir: Path, fix_mode: bool = False
) -> bool:
    """Compare current test directory with freshly generated template for a given template.

    Returns:
        - True if no differences found
        - True if --fix is enabled and all differences were auto-applied with no
          remaining manual fixes needed
        - False otherwise
    """
    with console.status(
        "[bold green]Generating expected materialized version from current template..."
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            expected_proj = Path(temp_dir) / "expected-proj"

            run_copier_quietly(
                str(template_dir),
                str(expected_proj),
                parse_template_variables(template_dir),
            )

            template_name = template_dir.name
            root = Path.cwd()
            test_proj_dir = root / "rendered" / template_name
            differences = compare_directories(expected_proj, test_proj_dir)

            if not differences:
                console.print(
                    "✅ test directory matches expected template output",
                    style="bold green",
                )
                return True

            console.print(
                f"\n❌ Found {len(differences)} differences between expected and actual:",
                style="bold red",
            )
            for diff in differences:
                console.print(f"  {diff}")

            files_to_copy: List[
                Tuple[str, str, Optional[Path], Path, Optional[str]]
            ] = []
            files_needing_manual_fix: List[Tuple[str, str]] = []

            console.print("\nDetailed differences:")
            for diff in differences:
                if diff.startswith("Content differs: "):
                    file_path_str = diff[len("Content differs: ") :]
                    file_path = Path(file_path_str)
                    expected_file = expected_proj / file_path
                    actual_file = test_proj_dir / file_path

                    template_file_path = map_materialized_to_template_path(
                        template_dir, str(file_path)
                    )
                    template_file = template_dir / template_file_path

                    try:
                        with open(expected_file, "r", encoding="utf-8") as f:
                            expected_content = f.read()
                        with open(actual_file, "r", encoding="utf-8") as f:
                            actual_content = f.read()
                    except (UnicodeDecodeError, PermissionError):
                        expected_content = None
                        actual_content = None

                    console.print(f"\n--- Expected (from template): {file_path}")
                    console.print(f"+++ Actual (in test): {file_path}")

                    try:
                        result = subprocess.run(
                            [
                                "git",
                                "diff",
                                "--no-index",
                                str(expected_file),
                                str(actual_file),
                            ],
                            capture_output=True,
                            text=True,
                            cwd=template_dir,
                        )
                        if result.stdout:
                            lines = result.stdout.split("\n")
                            for line in lines[4:]:
                                if line.strip():
                                    console.print(f"  {line}")
                    except subprocess.CalledProcessError:
                        console.print("  (Files differ)")

                    if template_file_path.endswith(".jinja"):
                        auto_resolved_content: Optional[str] = None
                        if expected_content is not None and actual_content is not None:
                            auto_resolved_content = (
                                attempt_chunk_based_jinja_resolution(
                                    template_dir,
                                    template_file,
                                    expected_content,
                                    actual_content,
                                )
                            )

                        if auto_resolved_content:
                            if fix_mode:
                                console.print(
                                    f"  ✓ Auto-resolved: {template_file_path}"
                                )
                            else:
                                console.print(
                                    f"  ✓ Would auto-resolve: {template_file_path}"
                                )
                            files_to_copy.append(
                                (
                                    str(file_path),
                                    template_file_path,
                                    None,
                                    template_file,
                                    auto_resolved_content,
                                )
                            )
                        else:
                            files_needing_manual_fix.append(
                                (str(file_path), template_file_path)
                            )
                    else:
                        files_to_copy.append(
                            (
                                str(file_path),
                                template_file_path,
                                actual_file,
                                template_file,
                                None,
                            )
                        )
                elif diff.startswith("Extra file: "):
                    file_path_str = diff[len("Extra file: ") :]
                    actual_file = test_proj_dir / file_path_str

                    template_file_path = map_materialized_to_template_path(
                        template_dir, file_path_str
                    )
                    template_file = template_dir / template_file_path

                    console.print(f"\nExtra file in test: {file_path_str}")

                    if template_file_path.endswith(".jinja"):
                        files_needing_manual_fix.append(
                            (file_path_str, template_file_path)
                        )
                    else:
                        files_to_copy.append(
                            (
                                file_path_str,
                                template_file_path,
                                actual_file,
                                template_file,
                                None,
                            )
                        )

    if fix_mode:
        if files_to_copy:
            console.print(f"\nCopying {len(files_to_copy)} files back to template:")
            for (
                _relative_path,
                _template_path,
                actual_file,
                template_file,
                auto_resolved_content,
            ) in files_to_copy:
                console.print(f"Copying {template_file}")
                template_file.parent.mkdir(parents=True, exist_ok=True)
                if auto_resolved_content:
                    with open(template_file, "w", encoding="utf-8") as f:
                        f.write(auto_resolved_content)
                else:
                    assert actual_file is not None
                    shutil.copy2(actual_file, template_file)

        if files_needing_manual_fix:
            console.print(
                f"\n⚠️  {len(files_needing_manual_fix)} templated files need manual resolution:"
            )
            for materialized_path, template_path in files_needing_manual_fix:
                console.print(f"  {materialized_path} → {template_path}")
            return False

        console.print("\n✓ Changes applied to template", style="bold green")
        return True
    else:
        if files_to_copy or files_needing_manual_fix:
            console.print("\nWould make the following changes:")
            if files_to_copy:
                console.print(f"  Copy {len(files_to_copy)} files back to template")
            if files_needing_manual_fix:
                console.print(
                    f"  {len(files_needing_manual_fix)} files need manual resolution"
                )
            console.print(
                "\nTo apply changes, run: template check-template <name> --fix"
            )
        return False
