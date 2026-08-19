from datetime import UTC, date, datetime

from ai_observatory.domain import EvidenceTier, SourceMethod, SourceSpec, TargetKind, TargetSpec, TargetTier, ThemeSpec
from ai_observatory.ledger import EvidenceLedger
from ai_observatory.registry import Registry
from ai_observatory.runner import run_collection
from ai_observatory.sources.base import AdapterRegistry, CollectResult, SourceStatus


class MixedAdapter:
    method = None

    def collect(self, target, source, context):
        if source.id == "broken":
            raise TimeoutError("source timeout")
        return CollectResult(SourceStatus.HEALTHY, (), {"queried": True})


def registry_with_two_sources():
    sources = (
        SourceSpec("healthy", SourceMethod.RSS, "https://example.test/healthy", EvidenceTier.PRIMARY),
        SourceSpec("broken", SourceMethod.RSS, "https://example.test/broken", EvidenceTier.PRIMARY),
    )
    target = TargetSpec("openai", "OpenAI", TargetKind.COMPANY, TargetTier.CORE,
                        ("agent_runtime",), sources)
    return Registry((target,), (ThemeSpec("agent_runtime", "Agent Knowledge Runtime", 20),))


def test_one_source_failure_does_not_abort_run(tmp_path):
    registry = registry_with_two_sources()
    adapter = MixedAdapter()
    adapter.method = registry.targets[0].sources[0].method
    result = run_collection(
        registry=registry, adapters=AdapterRegistry([adapter]),
        ledger=EvidenceLedger(tmp_path / "evidence"), runs_root=tmp_path / "runs",
        run_date=date(2026, 8, 19), profile="core",
        now=datetime(2026, 8, 19, tzinfo=UTC),
    )
    assert result.status == "partial"
    assert {row.status for row in result.sources} == {"healthy", "unavailable"}
