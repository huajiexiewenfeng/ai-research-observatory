from datetime import UTC, date, datetime
from pathlib import Path

from ai_observatory.domain import EvidenceTier, SourceMethod, SourceSpec, TargetKind, TargetSpec, TargetTier
from ai_observatory.sources.base import CollectContext, SourceStatus
from ai_observatory.sources.feed import FeedAdapter
from ai_observatory.sources.html import HtmlAdapter


FIXTURES = Path(__file__).parent / "fixtures"


class TextResponse:
    status_code = 200
    headers = {}

    def __init__(self, text):
        self.text = text
        self.content = text.encode("utf-8")


class FakeSession:
    def __init__(self, text):
        self.text = text

    def get(self, *args, **kwargs):
        return TextResponse(self.text)


TARGET = TargetSpec("openai", "OpenAI", TargetKind.COMPANY, TargetTier.CORE, ("agent_runtime",), ())
CONTEXT = CollectContext("run-1", date(2026, 8, 19), datetime(2026, 8, 19, tzinfo=UTC), 10)


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
