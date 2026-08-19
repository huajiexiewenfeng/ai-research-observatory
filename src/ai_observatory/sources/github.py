from __future__ import annotations

from datetime import datetime
import os

import requests

from ..domain import SourceMethod, SourceSpec, TargetSpec
from ..evidence import Evidence
from .base import CollectContext, CollectResult, SourceStatus


class GitHubReleasesAdapter:
    method = SourceMethod.GITHUB_RELEASES

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()

    def collect(self, target: TargetSpec, source: SourceSpec, context: CollectContext) -> CollectResult:
        repo = source.config["repo"]
        limit = int(source.config.get("max_items", 5))
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        response = self.session.get(
            f"https://api.github.com/repos/{repo}/releases",
            params={"per_page": limit}, headers=headers, timeout=context.timeout_seconds,
        )
        remaining = int(response.headers.get("X-RateLimit-Remaining", "-1"))
        if response.status_code == 403 and remaining == 0:
            return CollectResult(SourceStatus.UNAVAILABLE, (), {
                "reason": "rate_limited", "rate_limit_remaining": remaining,
                "rate_limit_reset": response.headers.get("X-RateLimit-Reset"),
            })
        if response.status_code != 200:
            return CollectResult(SourceStatus.UNAVAILABLE, (),
                                 {"reason": "http_error", "status_code": response.status_code})
        evidence = tuple(
            Evidence.create(
                target_id=target.id, source_id=source.id, source_method=source.method,
                evidence_tier=source.evidence_tier, title=row.get("name") or row["tag_name"],
                url=row["html_url"], content=row.get("body") or row["tag_name"],
                published_at=datetime.fromisoformat(row["published_at"].replace("Z", "+00:00")),
                collected_at=context.collected_at, run_id=context.run_id,
            )
            for row in response.json() if not row.get("draft") and not row.get("prerelease")
        )
        return CollectResult(SourceStatus.HEALTHY, evidence, {
            "queried": True, "rate_limit_remaining": remaining, "record_count": len(evidence),
        })
