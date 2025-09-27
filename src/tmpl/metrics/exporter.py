"""GitHub traffic metrics fetcher (clones) and PostHog exporter.

Collects repository traffic metrics (clones and unique cloners) for the last
14 days from the GitHub REST API and emits a single PostHog event per
repository. Designed to be used by the CLI command and from CI.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, TypedDict

import requests
import posthog


GITHUB_API_BASE = "https://api.github.com"


class CloneItem(TypedDict):
    timestamp: str
    count: int
    uniques: int


class ClonesResponse(TypedDict):
    count: int
    uniques: int
    clones: List[CloneItem]


@dataclass
class GitHubAuth:
    token: Optional[str]

    @classmethod
    def from_env(cls) -> "GitHubAuth":
        return cls(token=os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PAT"))


@dataclass
class PostHogEvent:
    """Represents a PostHog event with all necessary data."""

    event_name: str
    properties: Dict[str, Any]
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for backwards compatibility."""
        result = {
            "event_name": self.event_name,
            "properties": self.properties,
        }
        if self.timestamp is not None:
            result["timestamp"] = self.timestamp
        return result


def owner_repo_from_url(url: str) -> Tuple[str, str]:
    """Parse an owner/repo from a GitHub URL or SSH git URL.

    Examples:
      - https://github.com/run-llama/template-workflow-basic.git -> (run-llama, template-workflow-basic)
      - git@github.com:run-llama/template-workflow-basic.git -> (run-llama, template-workflow-basic)
    """
    # SSH form
    m = re.match(r"^git@github.com:(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$", url)
    if m:
        return m.group("owner"), m.group("repo")
    # HTTPS form
    m = re.match(
        r"^https?://github.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$", url
    )
    if m:
        return m.group("owner"), m.group("repo")
    raise ValueError(f"Unsupported GitHub URL format: {url}")


def _gh_get(
    path: str, auth: GitHubAuth, params: Optional[Dict[str, Any]] = None
) -> requests.Response:
    url = f"{GITHUB_API_BASE}{path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "tmpl-metrics-exporter",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if auth.token:
        headers["Authorization"] = f"token {auth.token}"
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    return resp


def _gh_get_json(
    path: str, auth: GitHubAuth, params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    resp = _gh_get(path, auth, params)
    if resp.status_code is None or resp.status_code >= 300:
        raise RuntimeError(
            f"GitHub API error {resp.status_code} for {path}: {resp.text[:200]}"
        )
    return resp.json()


def get_repo_clones(
    owner: str, repo: str, auth: GitHubAuth, per: str = "day"
) -> ClonesResponse:
    data = _gh_get_json(
        f"/repos/{owner}/{repo}/traffic/clones", auth, params={"per": per}
    )
    # Schema is stable per GitHub docs
    return ClonesResponse(
        count=int(data["count"]),
        uniques=int(data["uniques"]),
        clones=[
            CloneItem(
                timestamp=str(item["timestamp"]),
                count=int(item["count"]),
                uniques=int(item["uniques"]),
            )
            for item in data["clones"]
        ],
    )


def fetch_repo_metrics(
    owner: str, repo: str, auth: Optional[GitHubAuth] = None
) -> Dict[str, Any]:
    """Fetch traffic metrics for a repository: clones and unique cloners.

    Returns keys: owner, repo, clones_count, clones_uniques, clones (per day for last 14 days).
    """
    auth = auth or GitHubAuth.from_env()
    clones = get_repo_clones(owner, repo, auth, per="day")
    return {
        "owner": owner,
        "repo": repo,
        "clones_count": clones["count"],
        "clones_uniques": clones["uniques"],
        "clones": clones["clones"],
    }


def send_posthog_event(
    event: str,
    properties: Dict[str, Any],
    *,
    timestamp: Optional[datetime] = None,
    api_key: Optional[str] = None,
    host: Optional[str] = None,
    distinct_id: str = "tmpl-metrics",
) -> None:
    """Send a single event to PostHog, optionally with a specific timestamp.

    Reads POSTHOG_API_KEY and POSTHOG_HOST if not provided.
    """
    api_key = (
        api_key or os.getenv("POSTHOG_API_KEY") or os.getenv("POSTHOG_PROJECT_API_KEY")
    )
    host = host or os.getenv("POSTHOG_HOST") or "https://us.posthog.com"
    if not api_key:
        raise RuntimeError("POSTHOG_API_KEY is required to send metrics")

    posthog.api_key = api_key
    posthog.host = host
    posthog.capture(
        distinct_id=distinct_id, event=event, properties=properties, timestamp=timestamp
    )


def _parse_iso_utc(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def build_clone_events(
    template: str, owner: str, repo: str, clones: ClonesResponse, *, backfill: bool
) -> List[PostHogEvent]:
    """Build PostHog events for total and daily clones metrics.

    Returns a list of PostHogEvent objects.
    - Total event includes: clones_total, clones_unique_total, days_count, window_start, window_end.
    - Daily events include: day_timestamp, clones_day, uniques_day. When backfill is False, only last day is included.
    The timestamp will be set to the day's timestamp for daily events and to window_end for the total event.
    """
    items = clones["clones"]
    days_count = len(items)
    window_start = items[0]["timestamp"] if items else None
    window_end = items[-1]["timestamp"] if items else None

    events: List[PostHogEvent] = []

    # Total window event
    total_props: Dict[str, Any] = {
        "template": template,
        "owner": owner,
        "repo": repo,
        "clones_total": clones["count"],
        "clones_unique_total": clones["uniques"],
        "days_count": days_count,
        "window_start": window_start,
        "window_end": window_end,
        "dedupe_ts": window_end,
    }
    events.append(
        PostHogEvent(
            event_name="template_repo_clones_total",
            properties=total_props,
            timestamp=_parse_iso_utc(window_end) if window_end else None,
        )
    )

    # Daily events
    daily_items: List[CloneItem]
    if backfill:
        daily_items = items
    else:
        daily_items = items[-1:] if items else []

    for it in daily_items:
        ts = it["timestamp"]
        daily_props: Dict[str, Any] = {
            "template": template,
            "owner": owner,
            "repo": repo,
            "day": ts,
            "clones_day": it["count"],
            "clones_uniques_day": it["uniques"],
            "dedupe_ts": ts,
        }
        events.append(
            PostHogEvent(
                event_name="template_repo_clones_daily",
                properties=daily_props,
                timestamp=_parse_iso_utc(ts),
            )
        )

    return events


def export_all_from_mapping(
    mapping: Dict[str, Dict[str, Any]], *, github_auth: Optional[GitHubAuth] = None
) -> Dict[str, Dict[str, Any]]:
    """Fetch metrics for all templates defined in the mapping file.

    Returns a dict keyed by template name with metrics dict values.
    """
    github_auth = github_auth or GitHubAuth.from_env()
    results: Dict[str, Dict[str, Any]] = {}
    for template_name, cfg in mapping.items():
        try:
            owner, repo = owner_repo_from_url(
                cfg["url"]
            )  # cfg keys validated by loader
            metrics = fetch_repo_metrics(owner, repo, github_auth)
            results[template_name] = metrics
        except Exception as exc:  # capture error info per template
            results[template_name] = {
                "error": str(exc),
            }
    return results


def get_all_events_for_export(
    mapping: Dict[str, Dict[str, Any]],
    *,
    github_auth: Optional[GitHubAuth] = None,
    backfill: bool = False,
) -> Tuple[Dict[str, Dict[str, Any]], List[PostHogEvent]]:
    """Get metrics and PostHog events for all templates.

    Returns a tuple of (metrics_dict, events_list) where:
    - metrics_dict: keyed by template name with summary metrics
    - events_list: list of PostHogEvent objects ready for sending

    Each PostHogEvent contains: event_name, properties, timestamp (optional)
    """
    github_auth = github_auth or GitHubAuth.from_env()
    metrics: Dict[str, Dict[str, Any]] = {}
    all_events: List[PostHogEvent] = []

    for template_name, cfg in mapping.items():
        try:
            owner, repo = owner_repo_from_url(cfg["url"])
            clones = get_repo_clones(owner, repo, github_auth, per="day")

            # Build metrics summary
            metrics[template_name] = {
                "owner": owner,
                "repo": repo,
                "clones_count": clones["count"],
                "clones_uniques": clones["uniques"],
                "days_count": len(clones["clones"]),
                "window_start": clones["clones"][0]["timestamp"]
                if clones["clones"]
                else None,
                "window_end": clones["clones"][-1]["timestamp"]
                if clones["clones"]
                else None,
            }

            # Build events
            events = build_clone_events(
                template_name, owner, repo, clones, backfill=backfill
            )
            all_events.extend(events)

        except Exception as exc:
            metrics[template_name] = {"error": str(exc)}

    return metrics, all_events


__all__ = [
    "GitHubAuth",
    "PostHogEvent",
    "fetch_repo_metrics",
    "send_posthog_event",
    "export_all_from_mapping",
    "get_all_events_for_export",
    "owner_repo_from_url",
    "get_repo_clones",
    "build_clone_events",
]
