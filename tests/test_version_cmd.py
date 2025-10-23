from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from tmpl.cli import cli as tmpl_cli
import tmpl.cli as cli_mod
import tmpl.config.mapping as mapping_mod
from tmpl.git.versioning import bump_version_string, apply_version_bumps


def write_mapping(tmp_path: Path, content: str) -> Path:
    yml = tmp_path / ".github" / "templates-remotes.yml"
    yml.parent.mkdir(parents=True, exist_ok=True)
    yml.write_text(content)
    return yml


def test_version_patch_bump_from_zero(monkeypatch, tmp_path: Path) -> None:
    # Prepare mapping with one template without version
    mapping_file = write_mapping(
        tmp_path,
        """
templates:
  basic:
    remote: basic
    url: https://example.com/basic.git
    branch: main
""".lstrip(),
    )

    # Point discovery to our temp mapping file and clear memoized cache
    monkeypatch.setattr(
        mapping_mod,
        "discover_repo_mapping_path",
        lambda: mapping_file,
    )
    mapping_mod.get_mapping_data.cache_clear()
    # Provide template list and changed detection
    monkeypatch.setattr(
        cli_mod,
        "MAPPING_DATA",
        {
            "basic": {
                "remote": "basic",
                "url": "https://example.com/basic.git",
                "branch": "main",
            }
        },
    )
    monkeypatch.setattr(cli_mod, "detect_base_ref", lambda head: "BASE")
    monkeypatch.setattr(
        cli_mod,
        "list_changed_files",
        lambda base, head, include_uncommitted=True: ["templates/basic/pyproject.toml"],
    )
    monkeypatch.setattr(cli_mod, "templates_from_files", lambda files, names: ["basic"])

    runner = CliRunner()
    # Choose patch in prompt
    result = runner.invoke(
        tmpl_cli, ["version", "--base", "BASE", "--head", "HEAD"], input="patch\n"
    )
    assert result.exit_code == 0, result.output

    # Verify mapping updated to 0.0.1
    saved = mapping_file.read_text()
    assert "version: 0.0.1" in saved

    # also validate the pure function
    assert bump_version_string(None, "patch") == "0.0.1"


def test_version_minor_and_ignore(monkeypatch, tmp_path: Path) -> None:
    mapping_file = write_mapping(
        tmp_path,
        """
templates:
  t1:
    remote: r1
    url: https://example.com/r1.git
    branch: main
    version: 1.2.3
  t2:
    remote: r2
    url: https://example.com/r2.git
    branch: main
    version: 0.0.9
""".lstrip(),
    )

    monkeypatch.setattr(
        mapping_mod,
        "discover_repo_mapping_path",
        lambda: mapping_file,
    )
    mapping_mod.get_mapping_data.cache_clear()
    monkeypatch.setattr(cli_mod, "MAPPING_DATA", {"t1": {}, "t2": {}})
    monkeypatch.setattr(cli_mod, "detect_base_ref", lambda head: "BASE")
    monkeypatch.setattr(
        cli_mod,
        "list_changed_files",
        lambda base, head, include_uncommitted=True: [
            "templates/t1/x",
            "templates/t2/y",
        ],
    )
    # Ensure deterministic order: sorted -> [t1, t2]
    monkeypatch.setattr(
        cli_mod, "templates_from_files", lambda files, names: sorted(["t1", "t2"])
    )

    runner = CliRunner()
    # First choose minor for t1, then ignore for t2
    result = runner.invoke(
        tmpl_cli,
        ["version", "--base", "BASE", "--head", "HEAD"],
        input="minor\nignore\n",
    )
    assert result.exit_code == 0, result.output

    saved = mapping_file.read_text()
    # t1: 1.2.3 -> 1.3.0, t2 unchanged at 0.0.9
    assert "t1:" in saved and "version: 1.3.0" in saved
    assert "t2:" in saved and "version: 0.0.9" in saved

    # pure function decisions
    mapping = {
        "t1": {"remote": "r1", "url": "x", "branch": "main", "version": "1.2.3"},
        "t2": {"remote": "r2", "url": "y", "branch": "main", "version": "0.0.9"},
    }
    out = apply_version_bumps(mapping, {"t1": "minor", "t2": "ignore"})
    assert out["t1"]["version"] == "1.3.0"
    assert out["t2"]["version"] == "0.0.9"
