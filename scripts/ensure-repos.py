#!/usr/bin/env -S uv run --script
# /// script
# dependencies=[
#     "requests",
# ]
# ///

import os
import sys
import requests

# ===== Config =====
ORG = "run-llama"

# Token from env
TOKEN = os.getenv("GITHUB_PAT") or os.getenv("GITHUB_TOKEN")
if not TOKEN:
    print(
        "ERROR: Set GITHUB_PAT or GITHUB_TOKEN env var to your GitHub Personal Access Token.",
        file=sys.stderr,
    )
    sys.exit(1)

# Build repo names (include org in each repo name)
repos = [
    "template-workflow-classify-extract-sec",
]

API = "https://api.github.com"


def repo_exists(org: str, name: str) -> bool:
    url = f"{API}/repos/{org}/{name}"
    r = requests.get(url, headers={"Authorization": f"token {TOKEN}"})
    return r.status_code == 200


def create_repo(org: str, name: str):
    if repo_exists(org, name):
        print(f"SKIP: {org}/{name} already exists.")
        return

    url = f"{API}/orgs/{org}/repos"
    payload = {
        "name": name,
        "description": "Llama Index Workflow Template",
        "private": False,
        "auto_init": True,
    }

    r = requests.post(
        url,
        headers={
            "Authorization": f"token {TOKEN}",
            "Accept": "application/vnd.github+json",
        },
        json=payload,
    )
    if r.status_code >= 300:
        print(
            f"ERROR: Failed to create {org}/{name}: {r.status_code} {r.text}",
            file=sys.stderr,
        )
    else:
        print(f"Created: https://github.com/{org}/{name}")


def main():
    for repo in repos:
        create_repo(ORG, repo)

    print("\nAll repo names:")
    for r in repos:
        print(f" - {r}")


if __name__ == "__main__":
    main()
