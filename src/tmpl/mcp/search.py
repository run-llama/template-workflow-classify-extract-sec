from __future__ import annotations

import math
import re
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Dict, Tuple, Optional
import fnmatch


# -----------------------------
# Search implementation (local)
# -----------------------------

TOKEN_RE = re.compile(r"\w+", re.UNICODE)
_include_ext = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".md",
    ".txt",
    ".yml",
    ".yaml",
    ".toml",
    ".css",
    ".html",
}
_exclude_dirs = {
    "node_modules",
    "dist",
    "build",
    ".git",
    ".venv",
    "venv",
    "env",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".cache",
    ".next",
    "out",
}

_exclude_patterns = {
    "*lock.json",
    "*lock.yaml",
    "*.lock",
}


def _iter_template_files(templates_dir: Path) -> Iterable[Path]:
    """Yield code/content files under templates directory, skipping heavy dirs."""

    max_size_bytes = 1_000_000  # 1 MB cap per file

    for root, dirnames, filenames in os.walk(templates_dir):
        # Prune heavy/irrelevant directories in-place
        dirnames[:] = [d for d in dirnames if d not in _exclude_dirs]

        # In the function:
        filenames[:] = [
            f
            for f in filenames
            if not any(fnmatch.fnmatch(f, pattern) for pattern in _exclude_patterns)
        ]
        for fname in filenames:
            path = Path(root) / fname
            if path.suffix.lower() not in _include_ext:
                continue
            try:
                if path.stat().st_size > max_size_bytes:
                    continue
            except OSError:
                continue
            yield path


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


@dataclass
class Match:
    line: int
    text: str
    before: List[str]
    after: List[str]


@dataclass
class SearchResult:
    path: str
    score: float
    matches: List[Match]


def _bm25_score(
    query_tokens: List[str],
    doc_tf: Dict[str, int],
    avgdl: float,
    doc_len: int,
    N: int,
    df: Dict[str, int],
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    score = 0.0
    for q in query_tokens:
        if q not in df or df[q] == 0:
            continue
        n_q = df[q]
        idf = math.log(1 + (N - n_q + 0.5) / (n_q + 0.5))
        f_q = doc_tf.get(q, 0)
        if f_q == 0:
            continue
        denom = f_q + k1 * (1 - b + b * (doc_len / (avgdl if avgdl > 0 else 1.0)))
        score += idf * (f_q * (k1 + 1)) / denom
    return score


def _find_snippets(
    lines: List[str],
    query_tokens: List[str],
    max_matches: int = 3,
    context_lines: int = 3,
) -> List[Match]:
    matches: List[Match] = []
    lowered_tokens = set(query_tokens)
    for idx, line in enumerate(lines, start=1):
        lower_line = line.lower()
        # Check if ANY query token appears as a substring in the line
        if any(tok in lower_line for tok in lowered_tokens):
            cleaned = line.rstrip("\n")
            # Skip if the cleaned line is empty or whitespace-only
            if not cleaned or not cleaned.strip():
                continue
            start = max(1, idx - context_lines)
            end = min(len(lines), idx + context_lines)
            before = [
                line_text.rstrip("\n") for line_text in lines[start - 1 : idx - 1]
            ]
            after = [line_text.rstrip("\n") for line_text in lines[idx:end]]
            matches.append(Match(line=idx, text=cleaned, before=before, after=after))
            if len(matches) >= max_matches:
                break
    return matches


def _find_repo_root(start: Path) -> Path:
    """Find the repo root by looking for a templates dir with actual template subdirs.

    To distinguish between src/tmpl/templates (just code) and the actual templates directory,
    we check that the templates directory contains subdirectories with pyproject.toml files.
    """
    for parent in [start, *start.parents]:
        templates_dir = parent / "templates"
        if not templates_dir.exists() or not templates_dir.is_dir():
            continue
        # Check if this templates dir has template subdirectories with pyproject.toml
        # (i.e., it's the actual templates dir, not just a code directory)
        has_template_projects = False
        try:
            for entry in templates_dir.iterdir():
                if entry.is_dir() and (entry / "pyproject.toml").exists():
                    has_template_projects = True
                    break
        except (OSError, PermissionError):
            continue
        if has_template_projects:
            return parent
    return start


def _detect_repo_root(explicit_root: Optional[Path]) -> Path:
    # Prefer explicit root if provided
    if explicit_root is not None:
        root = _find_repo_root(explicit_root)
        if (root / "templates").exists():
            return root
    # Next try current working directory
    cwd_root = _find_repo_root(Path.cwd())
    if (cwd_root / "templates").exists():
        return cwd_root
    # Fallback to module location
    return _find_repo_root(Path(__file__).resolve())


def get_template(
    relative_path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    max_lines: int = 1000,
) -> str:
    """Get a template file with line numbers.

    Args:
        relative_path: Path relative to templates directory
        start_line: Optional starting line number (1-indexed, inclusive)
        end_line: Optional ending line number (1-indexed, inclusive)
        max_lines: Maximum number of lines to return (default 1000)

    Returns:
        File contents with line numbers prefixed to each line
    """
    repo_root = _detect_repo_root(Path.cwd())
    templates_dir = repo_root / "templates"
    if not templates_dir.exists():
        raise ValueError(f"Templates directory not found at {templates_dir}")
    path = templates_dir / relative_path
    if not path.exists():
        raise ValueError(f"Template file not found at {path}")

    content = path.read_text(encoding="utf-8", errors="ignore")
    lines = content.splitlines()
    total_lines = len(lines)

    # Apply range filtering if specified
    if start_line is not None or end_line is not None:
        # Convert to 0-indexed
        start_idx = (start_line - 1) if start_line is not None else 0
        end_idx = end_line if end_line is not None else total_lines

        # Clamp to valid range
        start_idx = max(0, min(start_idx, total_lines))
        end_idx = max(start_idx, min(end_idx, total_lines))

        lines = lines[start_idx:end_idx]
        line_offset = start_idx
    else:
        line_offset = 0

    # Apply max_lines cap
    lines_to_show = lines[:max_lines]
    omitted_count = len(lines) - len(lines_to_show)

    # Format with line numbers
    result_lines = []
    for i, line in enumerate(lines_to_show, start=line_offset + 1):
        # Right-align line numbers to 6 characters for consistency
        result_lines.append(f"{i:6}| {line}")

    result = "\n".join(result_lines)

    # Add omission notice if needed
    if omitted_count > 0:
        result += f"\n// {omitted_count} more line(s) omitted"

    return result


def search_templates_impl(
    query: str,
    limit: int = 10,
    root: Optional[Path] = None,
    context_lines: int = 3,
) -> List[SearchResult]:
    """Search the repository templates directory for code matching the query.

    Uses a lightweight BM25-like ranking across files. Returns top results with
    a few matching line snippets.
    """
    repo_root = _detect_repo_root(root)
    templates_dir = repo_root / "templates"
    if not templates_dir.exists():
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    # First pass to gather term frequencies and document stats
    doc_tfs: Dict[Path, Dict[str, int]] = {}
    doc_lens: Dict[Path, int] = {}
    df: Dict[str, int] = {}
    files: List[Path] = []
    path_token_sets: Dict[Path, set[str]] = {}

    for path in _iter_template_files(templates_dir):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # Combine file content tokens with relative path tokens for better recall
        rel_path = path.relative_to(repo_root).as_posix()
        content_tokens = _tokenize(text)
        path_tokens = _tokenize(rel_path)
        tokens = content_tokens + path_tokens
        if not tokens:
            continue
        files.append(path)
        tf: Dict[str, int] = {}
        for tok in tokens:
            tf[tok] = tf.get(tok, 0) + 1
        doc_tfs[path] = tf
        doc_lens[path] = len(tokens)
        path_token_sets[path] = set(path_tokens)
        # Update document frequency only once per doc
        seen = set(tf.keys())
        for tok in seen:
            df[tok] = df.get(tok, 0) + 1

    if not files:
        return []

    N = len(files)
    avgdl = sum(doc_lens.values()) / float(N)

    # Score documents
    scored: List[Tuple[Path, float]] = []
    path_bonus = 2.0
    for path in files:
        score = _bm25_score(query_tokens, doc_tfs[path], avgdl, doc_lens[path], N, df)
        # Add bonus for matches in file path tokens
        if path in path_token_sets:
            bonus_hits = sum(1 for q in query_tokens if q in path_token_sets[path])
            if bonus_hits:
                score += path_bonus * bonus_hits
        if score > 0:
            scored.append((path, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[: max(1, limit)]

    results: List[SearchResult] = []
    for path, score in top:
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            lines = []
        matches = _find_snippets(lines, query_tokens, context_lines=context_lines)
        results.append(
            SearchResult(
                path=str(path.relative_to(repo_root)),
                score=round(score, 4),
                matches=matches,
            )
        )

    return results


# -----------------------------
# MCP tool wrappers
# -----------------------------


def _merge_line_entries(matches: List[Match]) -> Dict[int, Tuple[str, bool]]:
    """Merge overlapping contexts across matches.

    Returns mapping of line_number -> (text, is_match).
    """
    line_entries: Dict[int, Tuple[str, bool]] = {}
    for m in matches:
        # Before context
        start_before = m.line - len(m.before)
        for i, b in enumerate(m.before):
            ln = start_before + i
            if ln not in line_entries:
                line_entries[ln] = (b, False)
        # Matched line
        existing = line_entries.get(m.line)
        if existing is None or existing[1] is False:
            line_entries[m.line] = (m.text, True)
        # After context
        for i, a in enumerate(m.after):
            ln = m.line + 1 + i
            if ln not in line_entries:
                line_entries[ln] = (a, False)
    return line_entries


def format_results_pretty(results: List[SearchResult]) -> str:
    """Render search results into a pretty textual format.

    Uses '*' to mark matching lines and a blank space for context lines.
    """
    parts: List[str] = []
    for r in results:
        parts.append(f"{r.path} (score {r.score})")
        line_entries = _merge_line_entries(r.matches)
        for ln in sorted(line_entries.keys()):
            text, is_match = line_entries[ln]
            indicator = "*" if is_match else " "
            parts.append(f"  {ln:>5}{indicator} {text}")
    return "\n".join(parts)
