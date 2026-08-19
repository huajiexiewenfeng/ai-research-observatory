from datetime import UTC, date, datetime
import json
from types import SimpleNamespace

from ai_observatory.domain import EvidenceTier, SourceMethod, SourceSpec, TargetKind, TargetSpec, TargetTier
from ai_observatory.sources.base import CollectContext, SourceStatus
from ai_observatory.sources.github import GitHubReleasesAdapter


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.last_kwargs = None

    def get(self, *args, **kwargs):
        self.last_kwargs = kwargs
        return self.response


def target_and_source():
    target = TargetSpec("vllm_project_vllm", "vLLM", TargetKind.PROJECT, TargetTier.CORE, ("inference",), ())
    source = SourceSpec("vllm_releases", SourceMethod.GITHUB_RELEASES,
                        "https://github.com/vllm-project/vllm", EvidenceTier.PRIMARY, True,
                        {"repo": "vllm-project/vllm", "max_items": 5})
    return target, source


def context():
    return CollectContext("run-1", date(2026, 8, 19), datetime(2026, 8, 19, tzinfo=UTC), 10)


def test_collects_release_as_primary_evidence():
    response = SimpleNamespace(status_code=200, headers={"X-RateLimit-Remaining": "4999"}, json=lambda: [{
        "name": "v0.9.0", "tag_name": "v0.9.0", "body": "release notes",
        "html_url": "https://github.com/vllm-project/vllm/releases/tag/v0.9.0",
        "published_at": "2026-08-19T00:00:00Z", "draft": False, "prerelease": False,
    }])
    result = GitHubReleasesAdapter(FakeSession(response)).collect(*target_and_source(), context())
    assert result.status is SourceStatus.HEALTHY
    assert result.evidence[0].title == "v0.9.0"
    assert result.diagnostics["rate_limit_remaining"] == 4999


def test_rate_limit_is_unavailable_not_empty():
    response = SimpleNamespace(status_code=403,
                               headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1787100000"},
                               json=lambda: {"message": "rate limit"})
    result = GitHubReleasesAdapter(FakeSession(response)).collect(*target_and_source(), context())
    assert result.status is SourceStatus.UNAVAILABLE
    assert result.evidence == ()
    assert result.diagnostics["reason"] == "rate_limited"


def test_optional_token_is_request_only(monkeypatch):
    response = SimpleNamespace(status_code=200, headers={"X-RateLimit-Remaining": "4999"}, json=lambda: [])
    session = FakeSession(response)
    monkeypatch.setenv("GITHUB_TOKEN", "test-secret-token")
    result = GitHubReleasesAdapter(session).collect(*target_and_source(), context())
    assert session.last_kwargs["headers"]["Authorization"] == "Bearer test-secret-token"
    assert "test-secret-token" not in json.dumps(result.diagnostics)
