from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup
from soupsieve.util import SelectorSyntaxError

from ..domain import SourceMethod, SourceSpec, TargetSpec
from ..evidence import Evidence
from .base import CollectContext, CollectResult, SourceStatus


def _diagnostics(*, queried: bool) -> dict:
    return {
        "queried": queried,
        "item_match_count": 0,
        "record_count": 0,
        "duplicate_count": 0,
        "skipped_count": 0,
        "published_at_inferred_count": 0,
    }


def _normalize_text(value: str) -> str:
    return " ".join(value.split())


def _normalize_url(base_url: str, href: str) -> str:
    parsed = urlsplit(urljoin(base_url, href))
    return urlunsplit(parsed._replace(fragment=""))


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _html_date(
    item, date_selector: str | None, date_formats: tuple[str, ...], fallback: datetime,
) -> tuple[datetime, bool]:
    candidates = item.select(date_selector) if date_selector else item.select("time[datetime]")
    for candidate in candidates:
        datetime_value = candidate.get("datetime")
        if datetime_value:
            try:
                return _as_utc(datetime.fromisoformat(datetime_value.replace("Z", "+00:00"))), False
            except ValueError:
                pass
        text = _normalize_text(candidate.get_text(" ", strip=True))
        for date_format in date_formats:
            try:
                return datetime.strptime(text, date_format).replace(tzinfo=UTC), False
            except ValueError:
                continue
    return fallback, True


class HtmlAdapter:
    method = SourceMethod.HTML

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()

    def collect(self, target: TargetSpec, source: SourceSpec, context: CollectContext) -> CollectResult:
        diagnostics = _diagnostics(queried=False)
        required = ("item_selector", "title_selector", "link_selector")
        if any(
            not isinstance(source.config.get(key), str) or not source.config[key].strip()
            for key in required
        ):
            return CollectResult(SourceStatus.UNAVAILABLE, (), {**diagnostics, "reason": "invalid_config"})
        try:
            max_items = int(source.config.get("max_items", 20))
        except (TypeError, ValueError):
            return CollectResult(SourceStatus.UNAVAILABLE, (), {**diagnostics, "reason": "invalid_config"})
        raw_formats = source.config.get("date_formats", ())
        date_selector = source.config.get("date_selector")
        if (
            max_items <= 0
            or (
                date_selector is not None
                and (not isinstance(date_selector, str) or not date_selector.strip())
            )
            or not isinstance(raw_formats, (list, tuple))
            or any(not isinstance(value, str) or not value for value in raw_formats)
        ):
            return CollectResult(SourceStatus.UNAVAILABLE, (), {**diagnostics, "reason": "invalid_config"})
        date_formats = tuple(raw_formats)

        diagnostics["queried"] = True
        try:
            response = self.session.get(source.url, timeout=context.timeout_seconds)
        except requests.RequestException as exc:
            return CollectResult(SourceStatus.UNAVAILABLE, (), {
                **diagnostics,
                "reason": "request_error",
                "exception_type": type(exc).__name__,
            })
        if response.status_code != 200:
            return CollectResult(SourceStatus.UNAVAILABLE, (), {
                **diagnostics,
                "reason": "http_error",
                "status_code": response.status_code,
            })

        soup = BeautifulSoup(response.text, "html.parser")
        evidence: list[Evidence] = []
        seen_urls: set[str] = set()
        try:
            items = soup.select(source.config["item_selector"])
            diagnostics["item_match_count"] = len(items)
            if not items:
                return CollectResult(SourceStatus.UNAVAILABLE, (), {
                    **diagnostics,
                    "reason": "selector_no_match",
                })
            for item in items:
                title_node = item.select_one(source.config["title_selector"])
                link_node = item.select_one(source.config["link_selector"])
                title = _normalize_text(title_node.get_text(" ", strip=True)) if title_node else ""
                href = link_node.get("href", "").strip() if link_node else ""
                if not title or not href:
                    diagnostics["skipped_count"] += 1
                    continue
                url = _normalize_url(source.url, href)
                if url in seen_urls:
                    diagnostics["duplicate_count"] += 1
                    continue
                published_at, inferred = _html_date(
                    item, date_selector, date_formats, context.collected_at,
                )
                diagnostics["published_at_inferred_count"] += int(inferred)
                seen_urls.add(url)
                evidence.append(Evidence.create(
                    target_id=target.id,
                    source_id=source.id,
                    source_method=source.method,
                    evidence_tier=source.evidence_tier,
                    title=title,
                    url=url,
                    content=item.get_text(" ", strip=True) or title,
                    published_at=published_at,
                    collected_at=context.collected_at,
                    run_id=context.run_id,
                ))
                if len(evidence) >= max_items:
                    break
        except SelectorSyntaxError:
            return CollectResult(SourceStatus.UNAVAILABLE, (), {
                **diagnostics,
                "record_count": 0,
                "reason": "invalid_selector",
            })

        diagnostics["record_count"] = len(evidence)
        if not evidence:
            return CollectResult(SourceStatus.UNAVAILABLE, (), {
                **diagnostics,
                "reason": "extraction_empty",
            })
        status = (
            SourceStatus.DEGRADED
            if diagnostics["skipped_count"] or diagnostics["published_at_inferred_count"]
            else SourceStatus.HEALTHY
        )
        return CollectResult(status, tuple(evidence), diagnostics)
