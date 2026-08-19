from __future__ import annotations

from datetime import date

from .evidence import Evidence
from .registry import Registry
from .runner import RunResult


STATUS_LABELS = {"healthy": "正常", "degraded": "降级", "unavailable": "不可用", "stale": "陈旧"}


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_coverage(run: RunResult) -> str:
    lines = ["## Coverage", "", "| 目标 | 来源 | 方法 | 状态 | 获取 | 新增 | 原因 |",
             "| --- | --- | --- | --- | ---: | ---: | --- |"]
    for source in run.sources:
        lines.append("| " + " | ".join([
            _cell(source.target_id), _cell(source.source_id), _cell(source.method),
            _cell(STATUS_LABELS.get(source.status, source.status)), str(source.collected_count),
            str(source.appended_count), _cell(source.diagnostics.get("reason", "-")),
        ]) + " |")
    if not run.sources:
        lines.append("| - | - | - | 不可用 | 0 | 0 | zero_planned_sources |")
    return "\n".join(lines)


def render_daily(
    run_date: date, registry: Registry, evidence: tuple[Evidence, ...],
    run: RunResult, limit: int = 10,
) -> str:
    target_names = {target.id: target.name for target in registry.targets}
    selected = sorted(evidence, key=lambda item: (-item.published_at.timestamp(), item.evidence_id))[:limit]
    lines = [f"# AI Research Observatory 每日证据 - {run_date.isoformat()}", "",
             render_coverage(run), "", "## 原始证据候选（尚未形成研究结论）", ""]
    if not selected:
        lines.append("本次没有获得可展示 Evidence；请先检查 Coverage，不能据此判断目标没有动态。")
    for index, item in enumerate(selected, start=1):
        excerpt = " ".join(item.content.split())[:400]
        lines.extend([
            f"### {index}. {target_names.get(item.target_id, item.target_id)} — {item.title}", "",
            f"- 链接：{item.url}", f"- 来源方法：{item.source_method.value}",
            f"- 证据等级：{item.evidence_tier.value}", f"- 发布时间：{item.published_at.isoformat()}",
            f"- 摘要：{excerpt}", "",
        ])
    return "\n".join(lines).rstrip() + "\n"
