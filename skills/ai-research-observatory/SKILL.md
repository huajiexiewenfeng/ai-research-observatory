---
name: ai-research-observatory
description: Use when working in the AI Research Observatory repository, invoking the ai-observatory CLI, or inspecting its Evidence Ledger, Coverage manifests, source health, or research-observation reports; not for AI Radar newsroom, dashboard, or article workflows.
---

# AI Research Observatory

## Purpose

Operate the independent, evidence-driven research observatory. Use its repository CLI and artifacts to track AI companies, researchers, projects, and research directions without switching into the AI Radar newsroom workflow.

## Routing Boundary

Use this Skill only when the current repository, explicit project name, path, artifact, or command identifies AI Research Observatory.

- Observatory markers: `ai-research-observatory`, `ai-observatory`, `evidence/ledger.jsonl`, run Coverage manifests, research-observation daily reports.
- Radar markers: `ai-radar`, `ai-radar-harness`, Newsroom Dashboard, publish selection, article generation.

If Radar markers identify the task, do not use this Skill. A bare “继续” or “continue” is not a project marker; resolve the active repository and most recent explicit project context first.

AI Radar may provide optional Evidence through a stable data contract. That does not transfer control to its Dashboard, Human Gate, or publishing workflow.

## Locate the Project

Prefer the current directory when its `pyproject.toml` declares `ai-research-observatory`. Otherwise use the known local clone only when it exists:

```text
D:\tmp\github\ai-research-observatory
```

Do not substitute an AI Radar directory.

## Phase 1 Commands

Validate configuration:

```powershell
ai-observatory validate-config --root .
```

Scan the core profile:

```powershell
ai-observatory scan --root . --date YYYY-MM-DD --profile core
```

`--date` groups the run and does not mean every remote item was published that day. Preserve both discovery time and original publication time.

Render the Chinese daily report with the returned run ID:

```powershell
ai-observatory render-daily --root . --date YYYY-MM-DD --run-id RUN_ID
```

## Evidence and Coverage Rules

- Treat `evidence/ledger.jsonl` as immutable, deduplicated Evidence.
- Inspect the run manifest before interpreting an empty report.
- `unavailable` means the source was not covered; it never proves that no update occurred.
- Phase 1 collects and reports Evidence. Do not present Claim, Direction, or contribution recommendations as implemented Phase 1 output.
- Never commit runtime Evidence, runs, reports, credentials, or private drafts.

## External Actions

Scanning and rendering are read-only. Do not create GitHub Issues, comments, PRs, X posts, or replies without a separate explicit approval for that exact external action.

## Output

Respond in Chinese by default. Report the run date, run ID, Evidence count, source-health summary, report path, and any unavailable or degraded sources. Keep Observatory and Radar artifact paths visibly distinct.

