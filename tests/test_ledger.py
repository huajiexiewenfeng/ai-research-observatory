from datetime import UTC, date, datetime

from ai_observatory.domain import EvidenceTier, SourceMethod
from ai_observatory.evidence import Evidence
from ai_observatory.ledger import EvidenceLedger


def sample_evidence() -> Evidence:
    return Evidence.create(
        target_id="vllm_project_vllm",
        source_id="vllm_releases",
        source_method=SourceMethod.GITHUB_RELEASES,
        evidence_tier=EvidenceTier.PRIMARY,
        title="v0.9.0",
        url="https://github.com/vllm-project/vllm/releases/tag/v0.9.0",
        content="release notes",
        published_at=datetime(2026, 8, 19, tzinfo=UTC),
        collected_at=datetime(2026, 8, 19, 1, tzinfo=UTC),
        run_id="run-1",
    )


def test_evidence_id_is_deterministic():
    assert sample_evidence().evidence_id == sample_evidence().evidence_id


def test_ledger_does_not_append_duplicate(tmp_path):
    ledger = EvidenceLedger(tmp_path)
    evidence = sample_evidence()
    assert ledger.append(date(2026, 8, 19), evidence) is True
    assert ledger.append(date(2026, 8, 19), evidence) is False
    assert ledger.read_date(date(2026, 8, 19)) == (evidence,)
