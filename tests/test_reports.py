from datetime import date

from ai_observatory.reports import render_coverage
from ai_observatory.runner import RunResult, SourceRun


def test_coverage_never_calls_unavailable_source_no_updates():
    run = RunResult(
        "run-1", date(2026, 8, 19), "core", "partial",
        (SourceRun("openai", "openai_rss", "rss", "unavailable", 0, 0, {"reason": "timeout"}),),
    )
    report = render_coverage(run)
    assert "不可用" in report
    assert "没有动态" not in report
    assert "openai_rss" in report
