# Anthropic 与 Meta AI HTML 来源实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增强配置驱动的通用 HTML Adapter，并启用 Anthropic Newsroom 与 Meta AI Blog，使真实 core 扫描在官网结构正常时达到 12/14 healthy。

**Architecture:** 站点差异全部保留在 `config/targets.yaml`；`HtmlAdapter` 统一负责选择器校验、日期解析、URL 规范化、单次去重、数量上限和 fail-closed 健康语义。Runner、Ledger 和报告接口保持不变，跨运行幂等继续由全局 Evidence Ledger 提供。

**Tech Stack:** Python 3.11+、Requests、BeautifulSoup 4 / SoupSieve、PyYAML、pytest 8+。

## Global Constraints

- 每个来源只请求配置 URL 一次，只处理首屏 HTML，不跟随分页或文章详情页。
- 每次最多输出 20 条成功提取且 URL 去重后的 Evidence。
- 优先保存官网发布时间；无法解析时使用 `collected_at` 并将来源标为 `degraded`。
- HTTP 200 但选择器零命中或零条有效 Evidence 必须 `unavailable`，不能误报“无动态”。
- 不增加站点专用 Python Adapter、Playwright、LLM 解析、重试或并发策略。
- 不修改 Runner、Ledger、报告、Feed/GitHub Adapter 或 X host bridge。
- 运行产物、凭据、完整页面 HTML 不进入 Git。
- 工作于当前 `main` 分支；用户已明确要求执行且其既定偏好是不新建分支、不使用子代理。

## File Structure

```text
src/ai_observatory/sources/html.py             # 通用 HTML 提取、日期、URL、去重与健康语义
tests/test_feed_html_adapters.py                # HtmlAdapter 单元与契约回归测试
tests/fixtures/html/anthropic-news.html         # Anthropic 最小结构 Fixture
tests/fixtures/html/meta-ai-blog.html           # Meta 最小结构 Fixture（含重复 URL）
tests/test_registry.py                          # 两个来源启用状态和配置透传测试
config/targets.yaml                             # Anthropic / Meta 结构化选择器配置
```

---

### Task 1: 以 TDD 增强通用 HtmlAdapter 契约

**Files:**
- Modify: `tests/test_feed_html_adapters.py`
- Modify: `src/ai_observatory/sources/html.py`

**Interfaces:**
- Consumes: `SourceSpec.config`, `CollectContext`, `Evidence.create()` 与现有 `requests.Session.get()`。
- Produces: `HtmlAdapter.collect(target, source, context) -> CollectResult`，所有返回均包含 `queried`、`item_match_count`、`record_count`、`duplicate_count`、`skipped_count`、`published_at_inferred_count`。
- Produces: `_html_date(item, date_selector, date_formats, fallback) -> tuple[datetime, bool]` 和 `_normalize_url(base_url, href) -> str`，仅供本模块内部使用。

- [ ] **Step 1: 扩展 FakeSession，并写入所有新契约的失败测试**

在 `tests/test_feed_html_adapters.py` 中保留 RSS 测试与现有 HTML happy-path，扩展测试桩并新增以下测试代码：

```python
class TextResponse:
    headers = {}

    def __init__(self, text, status_code=200):
        self.text = text
        self.content = text.encode("utf-8")
        self.status_code = status_code


class FakeSession:
    def __init__(self, text, status_code=200, error=None):
        self.text = text
        self.status_code = status_code
        self.error = error

    def get(self, *args, **kwargs):
        if self.error is not None:
            raise self.error
        return TextResponse(self.text, self.status_code)


def html_source(html_config):
    return SourceSpec(
        "site_html", SourceMethod.HTML, "https://example.test/news", EvidenceTier.PRIMARY,
        True, html_config,
    )


def assert_required_diagnostics(result):
    assert set(result.diagnostics) >= {
        "queried", "item_match_count", "record_count", "duplicate_count",
        "skipped_count", "published_at_inferred_count",
    }


def test_html_adapter_parses_text_dates_normalizes_urls_and_deduplicates():
    html = """
    <main>
      <article><h2>Short month</h2><a href="/a#top">A</a><time>Aug 14, 2026</time></article>
      <article><h2>Duplicate</h2><a href="/a#other">A2</a><time>Aug 14, 2026</time></article>
      <article><h2>Long month</h2><a href="/b?view=full#top">B</a><time>August 7, 2026</time></article>
    </main>
    """
    source = html_source({
        "item_selector": "article", "title_selector": "h2", "link_selector": "a",
        "date_selector": "time", "date_formats": ["%b %d, %Y", "%B %d, %Y"],
        "max_items": 20,
    })
    result = HtmlAdapter(FakeSession(html)).collect(TARGET, source, CONTEXT)
    assert result.status is SourceStatus.HEALTHY
    assert [item.url for item in result.evidence] == [
        "https://example.test/a", "https://example.test/b?view=full",
    ]
    assert [item.published_at for item in result.evidence] == [
        datetime(2026, 8, 14, tzinfo=UTC), datetime(2026, 8, 7, tzinfo=UTC),
    ]
    assert result.diagnostics["duplicate_count"] == 1
    assert result.diagnostics["published_at_inferred_count"] == 0
    assert_required_diagnostics(result)


def test_html_adapter_applies_max_items_after_url_deduplication():
    html = """
    <article><h2>A</h2><a href="/a">A</a><time>Aug 14, 2026</time></article>
    <article><h2>A duplicate</h2><a href="/a#copy">A</a><time>Aug 14, 2026</time></article>
    <article><h2>B</h2><a href="/b">B</a><time>Aug 13, 2026</time></article>
    <article><h2>C</h2><a href="/c">C</a><time>Aug 12, 2026</time></article>
    """
    source = html_source({
        "item_selector": "article", "title_selector": "h2", "link_selector": "a",
        "date_selector": "time", "date_formats": ["%b %d, %Y"], "max_items": 2,
    })
    result = HtmlAdapter(FakeSession(html)).collect(TARGET, source, CONTEXT)
    assert [item.title for item in result.evidence] == ["A", "B"]
    assert result.diagnostics["duplicate_count"] == 1


def test_html_adapter_marks_inferred_date_as_degraded():
    html = '<article><h2>A</h2><a href="/a">A</a></article>'
    source = html_source({
        "item_selector": "article", "title_selector": "h2", "link_selector": "a",
        "date_selector": "time", "date_formats": ["%b %d, %Y"],
    })
    result = HtmlAdapter(FakeSession(html)).collect(TARGET, source, CONTEXT)
    assert result.status is SourceStatus.DEGRADED
    assert result.evidence[0].published_at == CONTEXT.collected_at
    assert result.diagnostics["published_at_inferred_count"] == 1


def test_html_adapter_fails_closed_when_item_selector_matches_nothing():
    source = html_source({
        "item_selector": "article", "title_selector": "h2", "link_selector": "a",
    })
    result = HtmlAdapter(FakeSession("<main></main>")).collect(TARGET, source, CONTEXT)
    assert result.status is SourceStatus.UNAVAILABLE
    assert result.evidence == ()
    assert result.diagnostics["reason"] == "selector_no_match"
    assert result.diagnostics["item_match_count"] == 0
    assert_required_diagnostics(result)


def test_html_adapter_fails_closed_when_all_cards_are_invalid():
    source = html_source({
        "item_selector": "article", "title_selector": "h2", "link_selector": "a",
    })
    result = HtmlAdapter(FakeSession("<article><h2></h2><a>No href</a></article>")).collect(
        TARGET, source, CONTEXT,
    )
    assert result.status is SourceStatus.UNAVAILABLE
    assert result.diagnostics["reason"] == "extraction_empty"
    assert result.diagnostics["skipped_count"] == 1


def test_html_adapter_marks_partial_extraction_as_degraded():
    html = """
    <article><h2>A</h2><a href="/a">A</a><time datetime="2026-08-14T00:00:00Z"></time></article>
    <article><h2>Broken</h2><a>No href</a></article>
    """
    source = html_source({
        "item_selector": "article", "title_selector": "h2", "link_selector": "a",
    })
    result = HtmlAdapter(FakeSession(html)).collect(TARGET, source, CONTEXT)
    assert result.status is SourceStatus.DEGRADED
    assert len(result.evidence) == 1
    assert result.diagnostics["skipped_count"] == 1
    assert result.diagnostics["published_at_inferred_count"] == 0


def test_html_adapter_reports_invalid_selector_without_raising():
    source = html_source({
        "item_selector": "article[", "title_selector": "h2", "link_selector": "a",
    })
    result = HtmlAdapter(FakeSession("<article></article>")).collect(TARGET, source, CONTEXT)
    assert result.status is SourceStatus.UNAVAILABLE
    assert result.evidence == ()
    assert result.diagnostics["reason"] == "invalid_selector"
    assert_required_diagnostics(result)


def test_html_adapter_reports_invalid_config_with_complete_diagnostics():
    result = HtmlAdapter(FakeSession("<main></main>")).collect(
        TARGET, html_source({"item_selector": "article"}), CONTEXT,
    )
    assert result.status is SourceStatus.UNAVAILABLE
    assert result.diagnostics["reason"] == "invalid_config"
    assert result.diagnostics["queried"] is False
    assert_required_diagnostics(result)


def test_html_adapter_reports_http_and_request_errors():
    source = html_source({
        "item_selector": "article", "title_selector": "h2", "link_selector": "a",
    })
    http_result = HtmlAdapter(FakeSession("", status_code=503)).collect(TARGET, source, CONTEXT)
    request_result = HtmlAdapter(
        FakeSession("", error=requests.ConnectionError("offline")),
    ).collect(TARGET, source, CONTEXT)
    assert http_result.status is SourceStatus.UNAVAILABLE
    assert http_result.diagnostics["reason"] == "http_error"
    assert http_result.diagnostics["status_code"] == 503
    assert request_result.status is SourceStatus.UNAVAILABLE
    assert request_result.diagnostics["reason"] == "request_error"
    assert request_result.diagnostics["exception_type"] == "ConnectionError"
    assert http_result.diagnostics["queried"] is True
    assert request_result.diagnostics["queried"] is True
```

同时在测试文件顶部增加 `import requests`。现有 `test_html_adapter_requires_configured_selector` 继续验证 `time[datetime]` ISO 日期的向后兼容默认行为。

- [ ] **Step 2: 运行新契约测试并观察 RED**

Run:

```powershell
& 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest tests/test_feed_html_adapters.py -v
```

Expected: 新增测试因文本日期未解析、URL 未去重、零结果仍 healthy、无完整诊断和 selector/request 异常未转换而失败；现有 RSS 测试仍通过。

- [ ] **Step 3: 实现最小通用 HtmlAdapter 契约**

将 `src/ai_observatory/sources/html.py` 替换为下列实现：

```python
from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup
from soupsieve.util import SelectorSyntaxError

from ..domain import SourceMethod, SourceSpec, TargetSpec
from ..evidence import Evidence
from .base import CollectContext, CollectResult, SourceStatus


def _diagnostics(*, queried: bool) -> dict:
    return {
        "queried": queried,
        "item_match_count": 0,
        "record_count": 0,
        "duplicate_count": 0,
        "skipped_count": 0,
        "published_at_inferred_count": 0,
    }


def _normalize_text(value: str) -> str:
    return " ".join(value.split())


def _normalize_url(base_url: str, href: str) -> str:
    parsed = urlsplit(urljoin(base_url, href))
    return urlunsplit(parsed._replace(fragment=""))


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _html_date(
    item, date_selector: str | None, date_formats: tuple[str, ...], fallback: datetime,
) -> tuple[datetime, bool]:
    candidates = item.select(date_selector) if date_selector else item.select("time[datetime]")
    for candidate in candidates:
        datetime_value = candidate.get("datetime")
        if datetime_value:
            try:
                return _as_utc(datetime.fromisoformat(datetime_value.replace("Z", "+00:00"))), False
            except ValueError:
                pass
        text = _normalize_text(candidate.get_text(" ", strip=True))
        for date_format in date_formats:
            try:
                return datetime.strptime(text, date_format).replace(tzinfo=UTC), False
            except ValueError:
                continue
    return fallback, True


class HtmlAdapter:
    method = SourceMethod.HTML

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()

    def collect(self, target: TargetSpec, source: SourceSpec, context: CollectContext) -> CollectResult:
        diagnostics = _diagnostics(queried=False)
        required = ("item_selector", "title_selector", "link_selector")
        if any(not isinstance(source.config.get(key), str) or not source.config[key].strip() for key in required):
            return CollectResult(SourceStatus.UNAVAILABLE, (), {**diagnostics, "reason": "invalid_config"})
        try:
            max_items = int(source.config.get("max_items", 20))
        except (TypeError, ValueError):
            return CollectResult(SourceStatus.UNAVAILABLE, (), {**diagnostics, "reason": "invalid_config"})
        raw_formats = source.config.get("date_formats", ())
        date_selector = source.config.get("date_selector")
        if (
            max_items <= 0
            or (
                date_selector is not None
                and (not isinstance(date_selector, str) or not date_selector.strip())
            )
            or not isinstance(raw_formats, (list, tuple))
            or any(not isinstance(value, str) or not value for value in raw_formats)
        ):
            return CollectResult(SourceStatus.UNAVAILABLE, (), {**diagnostics, "reason": "invalid_config"})
        date_formats = tuple(raw_formats)

        diagnostics["queried"] = True
        try:
            response = self.session.get(source.url, timeout=context.timeout_seconds)
        except requests.RequestException as exc:
            return CollectResult(SourceStatus.UNAVAILABLE, (), {
                **diagnostics, "reason": "request_error", "exception_type": type(exc).__name__,
            })
        if response.status_code != 200:
            return CollectResult(SourceStatus.UNAVAILABLE, (), {
                **diagnostics, "reason": "http_error", "status_code": response.status_code,
            })

        soup = BeautifulSoup(response.text, "html.parser")
        evidence: list[Evidence] = []
        seen_urls: set[str] = set()
        try:
            items = soup.select(source.config["item_selector"])
            diagnostics["item_match_count"] = len(items)
            if not items:
                return CollectResult(SourceStatus.UNAVAILABLE, (), {
                    **diagnostics, "reason": "selector_no_match",
                })
            for item in items:
                title_node = item.select_one(source.config["title_selector"])
                link_node = item.select_one(source.config["link_selector"])
                title = _normalize_text(title_node.get_text(" ", strip=True)) if title_node else ""
                href = link_node.get("href", "").strip() if link_node else ""
                if not title or not href:
                    diagnostics["skipped_count"] += 1
                    continue
                url = _normalize_url(source.url, href)
                if url in seen_urls:
                    diagnostics["duplicate_count"] += 1
                    continue
                published_at, inferred = _html_date(item, date_selector, date_formats, context.collected_at)
                diagnostics["published_at_inferred_count"] += int(inferred)
                seen_urls.add(url)
                evidence.append(Evidence.create(
                    target_id=target.id,
                    source_id=source.id,
                    source_method=source.method,
                    evidence_tier=source.evidence_tier,
                    title=title,
                    url=url,
                    content=item.get_text(" ", strip=True) or title,
                    published_at=published_at,
                    collected_at=context.collected_at,
                    run_id=context.run_id,
                ))
                if len(evidence) >= max_items:
                    break
        except SelectorSyntaxError:
            return CollectResult(SourceStatus.UNAVAILABLE, (), {
                **diagnostics, "record_count": 0, "reason": "invalid_selector",
            })

        diagnostics["record_count"] = len(evidence)
        if not evidence:
            return CollectResult(SourceStatus.UNAVAILABLE, (), {
                **diagnostics, "reason": "extraction_empty",
            })
        status = (
            SourceStatus.DEGRADED
            if diagnostics["skipped_count"] or diagnostics["published_at_inferred_count"]
            else SourceStatus.HEALTHY
        )
        return CollectResult(status, tuple(evidence), diagnostics)
```

- [ ] **Step 4: 运行 focused tests 并确认 GREEN**

Run:

```powershell
& 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest tests/test_feed_html_adapters.py tests/test_runner.py -v
```

Expected: 所有 HTML/Feed Adapter 与 Runner 测试通过；无未捕获 selector/request 异常。

- [ ] **Step 5: 提交通用 Adapter 契约**

```powershell
git add src/ai_observatory/sources/html.py tests/test_feed_html_adapters.py
git commit -m "feat: harden html source collection"
```

---

### Task 2: 以 Fixture 验证并启用 Anthropic / Meta 来源，完成真实扫描

**Files:**
- Create: `tests/fixtures/html/anthropic-news.html`
- Create: `tests/fixtures/html/meta-ai-blog.html`
- Modify: `tests/test_feed_html_adapters.py`
- Modify: `tests/test_registry.py`
- Modify: `config/targets.yaml`
- Runtime only, untracked: `evidence/`, `runs/`, `reports/`

**Interfaces:**
- Consumes: Task 1 的 `HtmlAdapter.collect()` 契约和 `load_registry()` 的未知字段透传行为。
- Produces: `anthropic_news_html` 与 `meta_ai_blog_html` 两个 `enabled: true` 的 primary HTML 来源；各自配置 `item_selector`、`title_selector`、`link_selector`、`date_selector`、`date_formats`、`max_items`。

- [ ] **Step 1: 创建最小站点 Fixture**

创建 `tests/fixtures/html/anthropic-news.html`：

```html
<main>
  <ul>
    <li><a href="/news/text-watermark"><div><time>Aug 14, 2026</time></div><span>How Claude's text watermark works</span></a></li>
    <li><a href="/news/biology-safeguards"><div><time>August 7, 2026</time></div><span>Improving biology safeguards</span></a></li>
  </ul>
  <a href="/press">Press kit</a>
</main>
```

创建 `tests/fixtures/html/meta-ai-blog.html`：

```html
<main>
  <div>
    <div><div><h4>Research</h4></div><div><h4>Introducing Muse Spark 1.1</h4><p>Research update.</p></div></div>
    <div><p>July 09, 2026</p><a href="/blog/introducing-muse-spark-1-1/">Learn More</a></div>
  </div>
  <div>
    <div><div><h4>Open Source</h4></div><div><h4>Reimagining Independence</h4></div></div>
    <div><p>July 27, 2026</p><a href="/blog/reimagining-independence/">Learn More</a></div>
  </div>
  <div>
    <div><div><h4>Open Source</h4></div><div><h4>Duplicate card</h4></div></div>
    <div><p>July 27, 2026</p><a href="/blog/reimagining-independence/#duplicate">Learn More</a></div>
  </div>
</main>
```

- [ ] **Step 2: 写站点 Fixture 与 Registry 失败测试**

在 `tests/test_feed_html_adapters.py` 末尾增加：

```python
from ai_observatory.registry import load_registry


ROOT = Path(__file__).parents[1]


def configured_source(target_id, source_id):
    registry = load_registry(ROOT / "config/targets.yaml", ROOT / "config/themes.yaml")
    target = next(item for item in registry.targets if item.id == target_id)
    return target, next(item for item in target.sources if item.id == source_id)


def test_anthropic_fixture_matches_configured_contract():
    target, source = configured_source("anthropic", "anthropic_news_html")
    html = (FIXTURES / "html/anthropic-news.html").read_text(encoding="utf-8")
    result = HtmlAdapter(FakeSession(html)).collect(target, source, CONTEXT)
    assert result.status is SourceStatus.HEALTHY
    assert [item.title for item in result.evidence] == [
        "How Claude's text watermark works", "Improving biology safeguards",
    ]
    assert [item.url for item in result.evidence] == [
        "https://www.anthropic.com/news/text-watermark",
        "https://www.anthropic.com/news/biology-safeguards",
    ]
    assert result.diagnostics["published_at_inferred_count"] == 0


def test_meta_fixture_matches_configured_contract_and_deduplicates():
    target, source = configured_source("meta_ai", "meta_ai_blog_html")
    html = (FIXTURES / "html/meta-ai-blog.html").read_text(encoding="utf-8")
    result = HtmlAdapter(FakeSession(html)).collect(target, source, CONTEXT)
    assert result.status is SourceStatus.HEALTHY
    assert [item.title for item in result.evidence] == [
        "Introducing Muse Spark 1.1", "Reimagining Independence",
    ]
    assert [item.published_at for item in result.evidence] == [
        datetime(2026, 7, 9, tzinfo=UTC), datetime(2026, 7, 27, tzinfo=UTC),
    ]
    assert result.diagnostics["duplicate_count"] == 1
    assert result.diagnostics["published_at_inferred_count"] == 0
```

在 `tests/test_registry.py` 末尾增加：

```python
def test_registry_enables_official_html_sources_with_verified_contracts():
    registry = load_registry(ROOT / "config/targets.yaml", ROOT / "config/themes.yaml")
    sources = {
        source.id: source
        for target in registry.targets
        for source in target.sources
        if source.id in {"anthropic_news_html", "meta_ai_blog_html"}
    }
    assert set(sources) == {"anthropic_news_html", "meta_ai_blog_html"}
    for source in sources.values():
        assert source.enabled is True
        assert source.config["max_items"] == 20
        assert source.config["date_selector"]
        assert source.config["date_formats"]
        assert source.config["item_selector"]
        assert source.config["title_selector"]
        assert source.config["link_selector"]
    assert sources["anthropic_news_html"].config["date_formats"] == ["%b %d, %Y", "%B %d, %Y"]
    assert sources["meta_ai_blog_html"].config["date_formats"] == ["%B %d, %Y", "%b %d, %Y"]
```

- [ ] **Step 3: 运行站点测试并观察 RED**

Run:

```powershell
& 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest tests/test_feed_html_adapters.py::test_anthropic_fixture_matches_configured_contract tests/test_feed_html_adapters.py::test_meta_fixture_matches_configured_contract_and_deduplicates tests/test_registry.py::test_registry_enables_official_html_sources_with_verified_contracts -v
```

Expected: 三个测试因两个来源仍为 `enabled: false` 且没有 selector/date 配置而失败。

- [ ] **Step 4: 按批准规格启用两个来源**

将 `config/targets.yaml` 中 Anthropic 来源替换为：

```yaml
      - id: anthropic_news_html
        method: html
        url: "https://www.anthropic.com/news"
        evidence_tier: primary
        enabled: true
        item_selector: 'main li:has(> a[href^="/news/"])'
        title_selector: 'a[href^="/news/"] > span:last-child'
        link_selector: 'a[href^="/news/"]'
        date_selector: 'time'
        date_formats: ['%b %d, %Y', '%B %d, %Y']
        max_items: 20
```

将 Meta 来源替换为：

```yaml
      - id: meta_ai_blog_html
        method: html
        url: "https://ai.meta.com/blog/"
        evidence_tier: primary
        enabled: true
        item_selector: 'div:has(> div > div > h4):has(a[href*="blog"])'
        title_selector: ':scope > div:first-child > div:nth-of-type(2) h4'
        link_selector: 'a[href*="blog"]'
        date_selector: ':scope > div:nth-of-type(2) p'
        date_formats: ['%B %d, %Y', '%b %d, %Y']
        max_items: 20
```

- [ ] **Step 5: 运行站点、Registry 与完整离线测试并确认 GREEN**

Run:

```powershell
& 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest tests/test_feed_html_adapters.py tests/test_registry.py -v
& 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q
git diff --check
```

Expected: focused 与完整测试均零失败；`git diff --check` 无输出。

- [ ] **Step 6: 提交 Fixture、配置与契约测试**

```powershell
git add config/targets.yaml tests/fixtures/html/anthropic-news.html tests/fixtures/html/meta-ai-blog.html tests/test_feed_html_adapters.py tests/test_registry.py
git commit -m "feat: enable anthropic and meta html sources"
```

- [ ] **Step 7: 校验配置并执行 2026-08-21 第一次真实 core 扫描**

Run:

```powershell
$cli = 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Scripts\ai-observatory.exe'
& $cli validate-config --root .
& $cli scan --root . --date 2026-08-21 --profile core --timeout-seconds 15
$firstManifest = Get-ChildItem -LiteralPath 'runs\2026-08-21' -Filter '*.json' |
    Sort-Object LastWriteTimeUtc -Descending |
    Select-Object -First 1
$firstRun = Get-Content -LiteralPath $firstManifest.FullName -Raw | ConvertFrom-Json
$firstRun.sources |
    Where-Object { $_.source_id -in @('anthropic_news_html', 'meta_ai_blog_html') } |
    ConvertTo-Json -Depth 8
```

Expected:

- `validate-config` 输出 `45 个观察对象，5 个研究主题`。
- Anthropic 与 Meta 各 `collected_count` 为 1–20、`status` 为 `healthy`、`published_at_inferred_count` 为 0。
- 两个来源 Evidence URL 分别属于 `anthropic.com/news/` 与 `ai.meta.com/blog/`。
- core Coverage 为 12/14 healthy；DeepSeek、Qwen 仍为 `stale / phase4_host_bridge`。

- [ ] **Step 8: 渲染日报、同日重跑并验证 Ledger 幂等**

Run:

```powershell
$cli = 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Scripts\ai-observatory.exe'
$firstRunId = [System.IO.Path]::GetFileNameWithoutExtension($firstManifest.Name)
& $cli render-daily --root . --date 2026-08-21 --run-id $firstRunId --limit 20
& $cli scan --root . --date 2026-08-21 --profile core --timeout-seconds 15
$secondManifest = Get-ChildItem -LiteralPath 'runs\2026-08-21' -Filter '*.json' |
    Sort-Object LastWriteTimeUtc -Descending |
    Select-Object -First 1
$secondRun = Get-Content -LiteralPath $secondManifest.FullName -Raw | ConvertFrom-Json
$secondRun.sources |
    Where-Object { $_.source_id -in @('anthropic_news_html', 'meta_ai_blog_html') } |
    ConvertTo-Json -Depth 8
```

Expected: 日报存在于 `reports/daily/2026-08-21.md`；第二次运行两个来源仍 healthy，但 unchanged Evidence 的 `appended_count` 均为 0。

- [ ] **Step 9: 完成隐私、运行产物与最终状态审计**

Run:

```powershell
& 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q
git diff --check
git status --short
rg -n "Authorization|Bearer |gho_|github_pat_|BEGIN .*PRIVATE KEY" evidence runs reports
```

Expected: 完整测试零失败；diff check 无输出；运行目录不出现在 Git 状态；secret scan 无命中（`rg` exit code 1 为预期）。

---

## Completion Review

- HtmlAdapter 的所有结果包含六个必需诊断字段。
- 文本日期、ISO `time[datetime]`、URL fragment 移除、query 保留、单次去重和去重后限额均有测试。
- 缺配置、HTTP/request 异常、selector 错误、零命中、零有效记录、部分解析和推断日期均符合批准的状态语义。
- Anthropic 与 Meta 使用通用 Adapter 和 YAML 结构选择器，不存在公司专用 Python 分支。
- 两个来源 Fixture 与 Registry 契约通过，完整测试通过。
- 真实运行证明 12/14 healthy、两来源原始日期无推断、同日重跑 Ledger 不新增重复 Evidence。
- X 来源、Runner、Ledger、报告与其他 Adapter 未被越界修改。
- Runtime artifacts 和 secrets 未进入 Git。
