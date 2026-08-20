# AI Research Observatory 与 AI Radar Skill 路由边界设计

- 状态：已批准
- 日期：2026-08-20
- 涉及项目：`ai-research-observatory`、`ai-radar-harness`

## 问题

`ai-frontier-newsroom` 的已安装版本使用了“AI 资讯”和裸词“继续”等宽泛触发条件，而 AI Research Observatory 没有独立 Skill。结果是在 Observatory 上下文中继续工作时，Codex 可能错误加载 AI Radar 的 Newsroom 工作流。

此外，`ai-radar-harness` 中的 Skill 源码与本机已安装副本内容不一致，使修复无法只依赖单一文件。

## 目标

1. 为 AI Research Observatory 提供独立、可发现的 `ai-research-observatory` Skill。
2. 将 `ai-frontier-newsroom` 限定在 AI Radar / AI Radar Harness 的采集、Dashboard、Human Gate 和发布流水线。
3. 当前仓库、明确项目名和项目专属命令优先于“继续”等模糊自然语言。
4. 两个项目只允许通过稳定的 Evidence 数据契约集成，不共享或隐式切换工作流。

## 路由契约

| 当前上下文 | 应加载 | 不应加载 |
|---|---|---|
| `ai-research-observatory` 仓库、`ai-observatory` CLI、Evidence Ledger、Coverage、研究观测日报 | `ai-research-observatory` | `ai-frontier-newsroom` |
| `ai-radar` / `ai-radar-harness`、Dashboard、Newsroom Human Gate、文章流水线 | `ai-frontier-newsroom` | `ai-research-observatory` |
| 只有“继续”，没有可识别项目上下文 | 根据当前工作目录和最近明确项目判断；仍不明确则先检查本地上下文 | 不允许仅凭“继续”触发任一项目 Skill |

## 实现

Observatory 仓库新增 `skills/ai-research-observatory/`，包含简洁的 `SKILL.md` 与 `agents/openai.yaml`。Skill 负责定位仓库、调用现有 CLI、报告 Evidence/Coverage/日报产物，并保持所有外部写操作停在 Human Gate。

Radar Skill 删除宽泛触发词，增加明确排除条件和项目根目录验证。仓库源码是维护源；验证后将其同步到 Codex 本机 Skill 目录。

## 验证

使用路由场景矩阵验证两边：各自的明确正向请求必须命中；对方项目的请求必须拒绝；裸词“继续”不能单独构成触发条件。两个 Skill 分别通过 `quick_validate.py`，最后比较源码与安装副本哈希。

