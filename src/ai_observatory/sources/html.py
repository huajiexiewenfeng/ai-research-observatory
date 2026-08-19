from __future__ import annotations

from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from ..domain import SourceMethod, SourceSpec, TargetSpec
from ..evidence import Evidence
from .base import CollectContext, CollectResult, SourceStatus


def _html_date(item, fallback: datetime) -> tuple[datetime, bool]:
    time = item.select_one("time[datetime]")
    if time is None:
        return fallback, True
    try:
        return datetime.fromisoformat(time["datetime"].replace("Z", "+00:00")), False
    except ValueError:
        return fallback, True


class HtmlAdapter:
    method = SourceMethod.HTML

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()

    def collect(self, target: TargetSpec, source: SourceSpec, context: CollectContext) -> CollectResult:
        required = ("item_selector", "title_selector", "link_selector")
        if any(not source.config.get(key) for key in required):
            return CollectResult(SourceStatus.UNAVAILABLE, (), {"reason": "invalid_config"})
        response = self.session.get(source.url, timeout=context.timeout_seconds)
        if response.status_code != 200:
            return CollectResult(SourceStatus.UNAVAILABLE, (), {"reason": "http_error", "status_code": response.status_code})
        soup = BeautifulSoup(response.text, "html.parser")
        evidence: list[Evidence] = []
        inferred_dates = 0
        for item in soup.select(source.config["item_selector"])[:int(source.config.get("max_items", 20))]:
            title_node = item.select_one(source.config["title_selector"])
            link_node = item.select_one(source.config["link_selector"])
            if title_node is None or link_node is None or not link_node.get("href"):
                continue
            published_at, inferred = _html_date(item, context.collected_at)
            inferred_dates += int(inferred)
            title = title_node.get_text(" ", strip=True)
            evidence.append(Evidence.create(
                target_id=target.id, source_id=source.id, source_method=source.method,
                evidence_tier=source.evidence_tier, title=title,
                url=urljoin(source.url, link_node["href"]),
                content=item.get_text(" ", strip=True) or title,
                published_at=published_at, collected_at=context.collected_at, run_id=context.run_id,
            ))
        return CollectResult(SourceStatus.HEALTHY, tuple(evidence), {
            "queried": True, "record_count": len(evidence),
            "published_at_inferred_count": inferred_dates,
        })
