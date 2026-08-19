# AI Research Observatory

一个 local-first、evidence-driven 的个人 AI 研究观测站。它持续观察 AI 公司、研究人员与开源项目，帮助我：

1. 学习并提升对 AI 领域的系统认知；
2. 支持 Agent Runtime、RAG 与 AI Infra 方向的研究；
3. 找到可验证、可持续的开源贡献与社区讨论机会。

## Phase 1 边界

Phase 1 是 Evidence radar，不是自动研究结论生成器。它只采集、去重、保存原始证据并展示来源覆盖情况；Claim、Direction、评分与行动队列属于后续阶段。

## 环境

需要 Python 3.11 或更高版本。

```powershell
python -m pip install -e ".[dev]"
```

## 校验配置

```powershell
ai-observatory validate-config --root .
```

## 扫描核心来源

扫描是只读操作，不会向 GitHub 或 X 写入内容。

```powershell
ai-observatory scan --root . --date YYYY-MM-DD --profile core
```

## 生成中文日报

使用扫描输出中的 `run_id`：

```powershell
ai-observatory render-daily --root . --date YYYY-MM-DD --run-id RUN_ID
```

## 运行时文件

- `evidence/`：按日期保存不可变 JSONL Evidence；
- `runs/`：保存每次扫描的来源健康与 Coverage 清单；
- `reports/`：保存生成的中文日报。

这些目录是本地运行产物，已由 `.gitignore` 排除，不提交到仓库。

## GitHub 认证

`GITHUB_TOKEN` 是可选环境变量。未设置时，GitHub Releases 适配器以较低限额匿名读取；设置时仅用于请求头，禁止写入 Evidence、运行清单、报告或日志。

## 来源健康语义

- `healthy / 正常`：本次成功查询并解析；
- `degraded / 降级`：获得部分结果或质量下降；
- `unavailable / 不可用`：本次无法完成查询；
- `stale / 陈旧`：来源停用或结果可能过期。

`unavailable` 绝不等于“没有动态”。日报无 Evidence 时必须先查看 Coverage。

## Human Gate

Phase 1 不会自动创建 GitHub Issue、评论、提交 PR，也不会自动在 X 发布或回复。任何外部写操作都必须经过人工确认，并在后续阶段单独设计。

## 测试

```powershell
python -m pytest -q
```

## 路线图

- [已批准的总体设计](docs/superpowers/specs/2026-08-18-ai-research-observatory-design.md)
- Phase 2：Research Intelligence（Signal、Claim、Direction、评分与周报）
- Phase 3：Personal Workbench（Human Gate、学习/研究/贡献/表达队列与本地 UI）
- Phase 4：X 与 AI Radar 集成、运行加固
