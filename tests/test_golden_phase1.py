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


def test_golden_phase1_is_idempotent_and_secret_free(tmp_path):
    registry = load_registry(FIXTURES / "golden/targets.yaml", FIXTURES / "golden/themes.yaml")
    xml = (FIXTURES / "feed/sample-rss.xml").read_text(encoding="utf-8")
    adapters = AdapterRegistry([FeedAdapter(FakeSession(xml))])
    ledger = EvidenceLedger(tmp_path / "evidence")
    first = run_collection(registry, adapters, ledger, tmp_path / "runs", date(2026, 8, 19),
                           "core", datetime(2026, 8, 19, tzinfo=UTC))
    second = run_collection(registry, adapters, ledger, tmp_path / "runs", date(2026, 8, 19),
                            "core", datetime(2026, 8, 19, 1, tzinfo=UTC))
    report = render_daily(date(2026, 8, 19), registry,
                          ledger.read_date(date(2026, 8, 19)), second)
    assert sum(row.appended_count for row in first.sources) == 1
    assert sum(row.appended_count for row in second.sources) == 0
    assert "Agent Runtime Update" in report
    assert "尚未形成研究结论" in report
    serialized = "\n".join(path.read_text(encoding="utf-8") for path in tmp_path.rglob("*.*"))
    assert "Authorization" not in serialized
    assert "Bearer " not in serialized
