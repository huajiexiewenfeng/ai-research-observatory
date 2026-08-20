# Skill Routing Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 AI Research Observatory 建立独立 Skill，并阻止 AI Radar Newsroom Skill 在 Observatory 上下文中被误用。

**Architecture:** 两个仓库各自维护自己的 Skill 源码；Skill 通过项目路径、项目名和专属命令进行判别。安装副本只从对应源码同步，两个工作流仅通过 Evidence 协议集成。

**Tech Stack:** Markdown Skill、YAML UI metadata、PowerShell、Codex `quick_validate.py`、Git

## Global Constraints

- `ai-research-observatory` 与 `ai-frontier-newsroom` 不共享命令或隐式切换工作流。
- 裸词“继续”不得单独触发任一项目 Skill。
- 外部 GitHub/X 写操作继续受 Human Gate 约束。
- Skill 源码先验证，再同步到本机安装目录。

---

### Task 1: Observatory Skill

**Files:**
- Create: `skills/ai-research-observatory/SKILL.md`
- Create: `skills/ai-research-observatory/agents/openai.yaml`
- Test: `tests/test_skill_routing.py`

**Interfaces:**
- Consumes: `ai-observatory validate-config|scan|render-daily` CLI 与仓库运行产物约定。
- Produces: 独立的 `ai-research-observatory` Skill 入口和可验证的路由描述。

- [ ] **Step 1: 编写失败的路由测试**

测试断言 Observatory Skill 文件存在、描述包含项目专属标识，并且不包含 Radar Dashboard/文章流水线职责。当前应因文件不存在而失败。

- [ ] **Step 2: 运行 RED 测试**

Run: `python -m pytest tests/test_skill_routing.py -q`

Expected: FAIL，指出 `skills/ai-research-observatory/SKILL.md` 不存在。

- [ ] **Step 3: 创建最小 Skill**

写入项目定位、命令映射、产物语义、Evidence 边界和 Human Gate；创建与 Skill 名称一致的 UI metadata。

- [ ] **Step 4: 验证 GREEN**

Run: `python -m pytest tests/test_skill_routing.py -q`

Expected: PASS。

Run: `python C:/Users/admin/.codex-clean-20260710/skills/.system/skill-creator/scripts/quick_validate.py skills/ai-research-observatory`

Expected: `Skill is valid!`

- [ ] **Step 5: 提交 Observatory Skill**

```powershell
git add skills tests/test_skill_routing.py docs/superpowers/specs/2026-08-20-skill-routing-boundary-design.md docs/superpowers/plans/2026-08-20-skill-routing-boundary.md
git commit -m "feat: add observatory skill boundary"
```

### Task 2: Radar Skill Narrowing

**Files:**
- Modify: `D:/ai-discovery/ai-radar-harness/skills/ai-frontier-newsroom/SKILL.md`
- Preserve: `D:/ai-discovery/ai-radar-harness/skills/ai-frontier-newsroom/agents/openai.yaml`

**Interfaces:**
- Consumes: AI Radar `run_human_gated_workflow.py` 与 `run_publish_workflow.py`。
- Produces: 只在 AI Radar / Harness 上下文触发的 Newsroom Skill。

- [ ] **Step 1: 记录当前误路由基线**

验证现有安装版包含裸词“继续”和泛化“AI 资讯”，并记录 Observatory 缺少独立 Skill 的实际失败。

- [ ] **Step 2: 收窄 Skill**

描述只保留 AI Radar、AI Radar Harness、Newsroom Dashboard、Newsroom Human Gate、Radar 专属脚本等判别词；正文加入 Observatory 排除规则和仓库根目录验证。

- [ ] **Step 3: 验证 Radar Skill**

Run: `python C:/Users/admin/.codex-clean-20260710/skills/.system/skill-creator/scripts/quick_validate.py D:/ai-discovery/ai-radar-harness/skills/ai-frontier-newsroom`

Expected: `Skill is valid!`

- [ ] **Step 4: 提交 Radar Skill**

```powershell
git add skills/ai-frontier-newsroom/SKILL.md
git commit -m "fix: narrow newsroom skill routing"
```

### Task 3: Installation and Cross-Routing Verification

**Files:**
- Install: `C:/Users/admin/.codex-clean-20260710/skills/ai-research-observatory/`
- Sync: `C:/Users/admin/.codex-clean-20260710/skills/ai-frontier-newsroom/`

**Interfaces:**
- Consumes: 两个已验证的仓库 Skill 源码。
- Produces: 本机 Codex 可发现且互不串用的安装状态。

- [ ] **Step 1: 顺序同步两个 Skill**

先安装 Observatory，再用 Radar 仓库源码替换其已安装副本；不复制运行产物。

- [ ] **Step 2: 校验安装副本**

对两个安装目录分别运行 `quick_validate.py`，并比较源码与安装副本的 SHA256。

- [ ] **Step 3: 运行完整回归**

Run: `python -m pytest -q`

Expected: 全部测试通过。

- [ ] **Step 4: 检查仓库状态**

两个仓库运行 `git status --short` 和 `git diff --check`，确认没有凭据、Evidence、reports 或 runs 被提交。

