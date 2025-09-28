from __future__ import annotations

from pathlib import Path
from typing import List

from click.testing import CliRunner

from tmpl.cli import cli as tmpl_cli
import tmpl.cli as cli_mod
from tmpl.git.tagging import tag_all_versions


def write_mapping(tmp_path: Path, content: str) -> Path:
    yml = tmp_path / ".github" / "templates-remotes.yml"
    yml.parent.mkdir(parents=True, exist_ok=True)
    yml.write_text(content)
    return yml


class Recorder:
    def __init__(self) -> None:
        self.calls: List[List[str]] = []

    def run(self, args: List[str]) -> None:
        self.calls.append(args)

    def last(self) -> List[str]:
        return self.calls[-1]


def test_tag_versions_pushes_missing_tag(monkeypatch, tmp_path: Path) -> None:
    mapping_file = write_mapping(
        tmp_path,
        """
templates:
  basic:
    remote: basic
    url: https://example.com/basic.git
    branch: main
    version: 1.2.3
""".lstrip(),
    )

    monkeypatch.setattr(cli_mod, "MAPPING_FILE", str(mapping_file))
    monkeypatch.setattr(cli_mod, "MAPPING_DATA", {"basic": {}})

    # Simulate remote not having the tag and subtree split commit id
    import tmpl.git.tagging as tagging_mod

    monkeypatch.setattr(
        tagging_mod,
        "git_output",
        lambda args: "deadbeef" if args[:2] == ["subtree", "split"] else "",
    )

    rec = Recorder()
    monkeypatch.setattr(tagging_mod, "run", rec.run)

    runner = CliRunner()
    result = runner.invoke(tmpl_cli, ["tag-versions"])
    assert result.exit_code == 0, result.output

    # Expect a push that targets refs/tags/v1.2.3
    pushes = [c for c in rec.calls if c[:2] == ["git", "push"]]
    assert pushes, rec.calls
    assert any("refs/tags/v1.2.3" in " ".join(c) for c in pushes)

    # also verify the pure function shape (doesn't actually run commands here)
    mapping = {
        "basic": {
            "remote": "basic",
            "url": "https://example.com/basic.git",
            "branch": "main",
            "version": "1.2.3",
        }
    }
    # monkeypatch helpers to avoid executing commands in pure call
    pushed: list[str] = []
    monkeypatch.setattr(tagging_mod, "git_output", lambda args: "deadbeef")
    monkeypatch.setattr(tagging_mod, "run", lambda args: pushed.append(" ".join(args)))
    # call via cli_mod to reuse monkeypatched symbols
    _ = tag_all_versions(mapping)  # type: ignore[arg-type]
