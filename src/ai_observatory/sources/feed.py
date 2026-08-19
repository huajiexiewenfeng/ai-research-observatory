from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin
from xml.etree import ElementTree

import requests

from ..domain import SourceMethod, SourceSpec, TargetSpec
from ..evidence import Evidence
from .base import CollectContext, CollectResult, SourceStatus


ATOM = "{http://www.w3.org/2005/Atom}"


def _parse_date(value: str | None, fallback: datetime) -> tuple[datetime, bool]:
    if not value:
        return fallback, True
    try:
        if "," in value:
            return parsedate_to_datetime(value), False
        return datetime.fromisoformat(value.replace("Z", "+00:00")), False
    except (TypeError, ValueError):
        return fallback, True


class FeedAdapter:
    method = SourceMethod.RSS

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()

    def collect(self, target: TargetSpec, source: SourceSpec, context: CollectContext) -> CollectResult:
        response = self.session.get(source.url, timeout=context.timeout_seconds)
        if response.status_code != 200:
            return CollectResult(SourceStatus.UNAVAILABLE, (), {"reason": "http_error", "status_code": response.status_code})
        try:
            root = ElementTree.fromstring(response.content)
        except ElementTree.ParseError as exc:
            return CollectResult(SourceStatus.UNAVAILABLE, (), {"reason": "parse_error", "message": str(exc)})
        rows: list[tuple[str, str, str, str | None]] = []
        for item in root.findall(".//item"):
            rows.append((item.findtext("title") or "Untitled", item.findtext("link") or source.url,
                         item.findtext("description") or "", item.findtext("pubDate")))
        for entry in root.findall(f".//{ATOM}entry"):
            link = entry.find(f"{ATOM}link")
            rows.append((entry.findtext(f"{ATOM}title") or "Untitled",
                         (link.get("href") if link is not None else None) or source.url,
                         entry.findtext(f"{ATOM}summary") or entry.findtext(f"{ATOM}content") or "",
                         entry.findtext(f"{ATOM}published") or entry.findtext(f"{ATOM}updated")))
        evidence: list[Evidence] = []
        inferred_dates = 0
        for title, link, content, published in rows[:int(source.config.get("max_items", 20))]:
            published_at, inferred = _parse_date(published, context.collected_at)
            inferred_dates += int(inferred)
            evidence.append(Evidence.create(
                target_id=target.id, source_id=source.id, source_method=source.method,
                evidence_tier=source.evidence_tier, title=title, url=urljoin(source.url, link),
                content=content or title, published_at=published_at,
                collected_at=context.collected_at, run_id=context.run_id,
            ))
        return CollectResult(SourceStatus.HEALTHY, tuple(evidence), {
            "queried": True, "record_count": len(evidence),
            "published_at_inferred_count": inferred_dates,
        })
