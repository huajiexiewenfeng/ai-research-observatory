from datetime import UTC, date, datetime
from pathlib import Path

import requests

from ai_observatory.domain import EvidenceTier, SourceMethod, SourceSpec, TargetKind, TargetSpec, TargetTier
from ai_observatory.sources.base import CollectContext, SourceStatus
from ai_observatory.sources.feed import FeedAdapter
from ai_observatory.sources.html import HtmlAdapter


FIXTURES = Path(__file__).parent / "fixtures"


class TextResponse:
    headers = {}

    def __init__(self, text, status_code=200):
        self.text = text
        self.content = text.encode("utf-8")
        self.status_code = status_code


class FakeSession:
    def __init__(self, text, status_code=200, error=None):
        self.text = text
        self.status_code = status_code
        self.error = error

    def get(self, *args, **kwargs):
        if self.error is not None:
            raise self.error
        return TextResponse(self.text, self.status_code)


TARGET = TargetSpec("openai", "OpenAI", TargetKind.COMPANY, TargetTier.CORE, ("agent_runtime",), ())
CONTEXT = CollectContext("run-1", date(2026, 8, 19), datetime(2026, 8, 19, tzinfo=UTC), 10)


def html_source(html_config):
    return SourceSpec(
        "site_html", SourceMethod.HTML, "https://example.test/news", EvidenceTier.PRIMARY,
        True, html_config,
    )


def assert_required_diagnostics(result):
    assert set(result.diagnostics) >= {
        "queried", "item_match_count", "record_count", "duplicate_count",
        "skipped_count", "published_at_inferred_count",
    }


def test_rss_adapter_extracts_primary_evidence():
    xml = (FIXTURES / "feed/sample-rss.xml").read_text(encoding="utf-8")
    source = SourceSpec("openai_rss", SourceMethod.RSS, "https://example.test/rss", EvidenceTier.PRIMARY)
    result = FeedAdapter(FakeSession(xml)).collect(TARGET, source, CONTEXT)
    assert result.status is SourceStatus.HEALTHY
    assert result.evidence[0].title == "Agent Runtime Update"


def test_html_adapter_requires_configured_selector():
    html = (FIXTURES / "html/sample-news.html").read_text(encoding="utf-8")
    source = SourceSpec(
        "openai_html", SourceMethod.HTML, "https://example.test/news", EvidenceTier.PRIMARY,
        True, {"item_selector": "article", "title_selector": "h2", "link_selector": "a"},
    )
    result = HtmlAdapter(FakeSession(html)).collect(TARGET, source, CONTEXT)
    assert result.status is SourceStatus.HEALTHY
    assert result.evidence[0].url == "https://example.test/research/agent-runtime"


def test_html_adapter_parses_text_dates_normalizes_urls_and_deduplicates():
    html = """
    <main>
      <article><h2>Short month</h2><a href="/a#top">A</a><time>Aug 14, 2026</time></article>
      <article><h2>Duplicate</h2><a href="/a#other">A2</a><time>Aug 14, 2026</time></article>
      <article><h2>Long month</h2><a href="/b?view=full#top">B</a><time>August 7, 2026</time></article>
    </main>
    """
    source = html_source({
        "item_selector": "article", "title_selector": "h2", "link_selector": "a",
        "date_selector": "time", "date_formats": ["%b %d, %Y", "%B %d, %Y"],
        "max_items": 20,
    })
    result = HtmlAdapter(FakeSession(html)).collect(TARGET, source, CONTEXT)
    assert result.status is SourceStatus.HEALTHY
    assert [item.url for item in result.evidence] == [
        "https://example.test/a", "https://example.test/b?view=full",
    ]
    assert [item.published_at for item in result.evidence] == [
        datetime(2026, 8, 14, tzinfo=UTC), datetime(2026, 8, 7, tzinfo=UTC),
    ]
    assert result.diagnostics["duplicate_count"] == 1
    assert result.diagnostics["published_at_inferred_count"] == 0
    assert_required_diagnostics(result)


def test_html_adapter_applies_max_items_after_url_deduplication():
    html = """
    <article><h2>A</h2><a href="/a">A</a><time>Aug 14, 2026</time></article>
    <article><h2>A duplicate</h2><a href="/a#copy">A</a><time>Aug 14, 2026</time></article>
    <article><h2>B</h2><a href="/b">B</a><time>Aug 13, 2026</time></article>
    <article><h2>C</h2><a href="/c">C</a><time>Aug 12, 2026</time></article>
    """
    source = html_source({
        "item_selector": "article", "title_selector": "h2", "link_selector": "a",
        "date_selector": "time", "date_formats": ["%b %d, %Y"], "max_items": 2,
    })
    result = HtmlAdapter(FakeSession(html)).collect(TARGET, source, CONTEXT)
    assert [item.title for item in result.evidence] == ["A", "B"]
    assert result.diagnostics["duplicate_count"] == 1


def test_html_adapter_marks_inferred_date_as_degraded():
    html = '<article><h2>A</h2><a href="/a">A</a></article>'
    source = html_source({
        "item_selector": "article", "title_selector": "h2", "link_selector": "a",
        "date_selector": "time", "date_formats": ["%b %d, %Y"],
    })
    result = HtmlAdapter(FakeSession(html)).collect(TARGET, source, CONTEXT)
    assert result.status is SourceStatus.DEGRADED
    assert result.evidence[0].published_at == CONTEXT.collected_at
    assert result.diagnostics["published_at_inferred_count"] == 1


def test_html_adapter_fails_closed_when_item_selector_matches_nothing():
    source = html_source({
        "item_selector": "article", "title_selector": "h2", "link_selector": "a",
    })
    result = HtmlAdapter(FakeSession("<main></main>")).collect(TARGET, source, CONTEXT)
    assert result.status is SourceStatus.UNAVAILABLE
    assert result.evidence == ()
    assert result.diagnostics["reason"] == "selector_no_match"
    assert result.diagnostics["item_match_count"] == 0
    assert_required_diagnostics(result)


def test_html_adapter_fails_closed_when_all_cards_are_invalid():
    source = html_source({
        "item_selector": "article", "title_selector": "h2", "link_selector": "a",
    })
    result = HtmlAdapter(FakeSession("<article><h2></h2><a>No href</a></article>")).collect(
        TARGET, source, CONTEXT,
    )
    assert result.status is SourceStatus.UNAVAILABLE
    assert result.diagnostics["reason"] == "extraction_empty"
    assert result.diagnostics["skipped_count"] == 1


def test_html_adapter_marks_partial_extraction_as_degraded():
    html = """
    <article><h2>A</h2><a href="/a">A</a><time datetime="2026-08-14T00:00:00Z"></time></article>
    <article><h2>Broken</h2><a>No href</a></article>
    """
    source = html_source({
        "item_selector": "article", "title_selector": "h2", "link_selector": "a",
    })
    result = HtmlAdapter(FakeSession(html)).collect(TARGET, source, CONTEXT)
    assert result.status is SourceStatus.DEGRADED
    assert len(result.evidence) == 1
    assert result.diagnostics["skipped_count"] == 1
    assert result.diagnostics["published_at_inferred_count"] == 0


def test_html_adapter_reports_invalid_selector_without_raising():
    source = html_source({
        "item_selector": "article[", "title_selector": "h2", "link_selector": "a",
    })
    result = HtmlAdapter(FakeSession("<article></article>")).collect(TARGET, source, CONTEXT)
    assert result.status is SourceStatus.UNAVAILABLE
    assert result.evidence == ()
    assert result.diagnostics["reason"] == "invalid_selector"
    assert_required_diagnostics(result)


def test_html_adapter_reports_invalid_config_with_complete_diagnostics():
    result = HtmlAdapter(FakeSession("<main></main>")).collect(
        TARGET, html_source({"item_selector": "article"}), CONTEXT,
    )
    assert result.status is SourceStatus.UNAVAILABLE
    assert result.diagnostics["reason"] == "invalid_config"
    assert result.diagnostics["queried"] is False
    assert_required_diagnostics(result)


def test_html_adapter_reports_http_error_with_complete_diagnostics():
    source = html_source({
        "item_selector": "article", "title_selector": "h2", "link_selector": "a",
    })
    result = HtmlAdapter(FakeSession("", status_code=503)).collect(TARGET, source, CONTEXT)
    assert result.status is SourceStatus.UNAVAILABLE
    assert result.diagnostics["reason"] == "http_error"
    assert result.diagnostics["status_code"] == 503
    assert result.diagnostics["queried"] is True
    assert_required_diagnostics(result)


def test_html_adapter_reports_request_error_with_complete_diagnostics():
    source = html_source({
        "item_selector": "article", "title_selector": "h2", "link_selector": "a",
    })
    result = HtmlAdapter(
        FakeSession("", error=requests.ConnectionError("offline")),
    ).collect(TARGET, source, CONTEXT)
    assert result.status is SourceStatus.UNAVAILABLE
    assert result.diagnostics["reason"] == "request_error"
    assert result.diagnostics["exception_type"] == "ConnectionError"
    assert result.diagnostics["queried"] is True
    assert_required_diagnostics(result)
