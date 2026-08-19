from datetime import UTC, date, datetime

from ai_observatory.domain import SourceMethod
from ai_observatory.sources.base import AdapterRegistry, CollectContext, CollectResult, SourceStatus


class EmptyAdapter:
    method = SourceMethod.RSS

    def collect(self, target, source, context):
        return CollectResult(SourceStatus.HEALTHY, (), {"queried": True})


def test_successful_zero_result_is_healthy():
    registry = AdapterRegistry([EmptyAdapter()])
    result = registry.get(SourceMethod.RSS).collect(
        None, None,
        CollectContext("run-1", date(2026, 8, 19), datetime(2026, 8, 19, tzinfo=UTC), 10),
    )
    assert result.status is SourceStatus.HEALTHY
    assert result.evidence == ()
    assert result.diagnostics["queried"] is True
