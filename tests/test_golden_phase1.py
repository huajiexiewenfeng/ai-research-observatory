from datetime import UTC, date, datetime
from pathlib import Path

from ai_observatory.ledger import EvidenceLedger
from ai_observatory.registry import load_registry
from ai_observatory.reports import render_daily
from ai_observatory.runner import run_collection
from ai_observatory.sources.base import AdapterRegistry
from ai_observatory.sources.feed import FeedAdapter


FIXTURES = Path(__file__).parent / "fixtures"


class FakeResponse:
    status_code = 200

    def __init__(self, content: str):
        self.content = content.encode("utf-8")


class FakeSession:
    def __init__(self, content: str):
        self.response = FakeResponse(content)

    def get(self, *args, **kwargs):
        return self.response


def test_golden_phase1_is_globally_idempotent_and_secret_free(tmp_path):
    registry = load_registry(FIXTURES / "golden/targets.yaml", FIXTURES / "golden/themes.yaml")
    xml = (FIXTURES / "feed/sample-rss.xml").read_text(encoding="utf-8")
    adapters = AdapterRegistry([FeedAdapter(FakeSession(xml))])
    ledger = EvidenceLedger(tmp_path / "evidence")
    day_one = run_collection(
        registry, adapters, ledger, tmp_path / "runs", date(2026, 8, 20), "core",
        datetime(2026, 8, 20, tzinfo=UTC),
    )
    same_day = run_collection(
        registry, adapters, ledger, tmp_path / "runs", date(2026, 8, 20), "core",
        datetime(2026, 8, 20, 1, tzinfo=UTC),
    )
    day_two = run_collection(
        registry, adapters, ledger, tmp_path / "runs", date(2026, 8, 21), "core",
        datetime(2026, 8, 21, tzinfo=UTC),
    )
    xml_with_new_item = xml.replace(
        "</channel>",
        "<item><title>New Runtime Evidence</title>"
        "<link>https://example.test/research/new-runtime</link>"
        "<description>A newly discovered item.</description>"
        "<pubDate>Sat, 22 Aug 2026 00:00:00 GMT</pubDate></item></channel>",
    )
    day_three_adapters = AdapterRegistry([FeedAdapter(FakeSession(xml_with_new_item))])
    day_three = run_collection(
        registry, day_three_adapters, ledger, tmp_path / "runs", date(2026, 8, 22), "core",
        datetime(2026, 8, 22, tzinfo=UTC),
    )

    first_report = render_daily(
        date(2026, 8, 20), registry, ledger.read_date(date(2026, 8, 20)), same_day,
    )
    second_report = render_daily(
        date(2026, 8, 21), registry, ledger.read_date(date(2026, 8, 21)), day_two,
    )
    third_report = render_daily(
        date(2026, 8, 22), registry, ledger.read_date(date(2026, 8, 22)), day_three,
    )

    assert sum(row.appended_count for row in day_one.sources) == 1
    assert sum(row.appended_count for row in same_day.sources) == 0
    assert sum(row.appended_count for row in day_two.sources) == 0
    assert sum(row.appended_count for row in day_three.sources) == 1
    assert "Agent Runtime Update" in first_report
    assert "Agent Runtime Update" not in second_report
    assert "New Runtime Evidence" in third_report
    assert "Agent Runtime Update" not in third_report
    assert "尚未形成研究结论" in first_report
    serialized = "\n".join(path.read_text(encoding="utf-8") for path in tmp_path.rglob("*.*"))
    assert "Authorization" not in serialized
    assert "Bearer " not in serialized
