# Anthropic 与 Meta AI 官网 HTML 来源设计

- 状态：对话设计已批准，待仓库规格复核
- 日期：2026-08-20
- 项目：`huajiexiewenfeng/ai-research-observatory`
- 阶段：Phase 1 Evidence radar 来源覆盖增强

## 1. 背景与根因

Phase 1 初始实现有意将 Anthropic Newsroom 和 Meta AI Blog 配置为 `enabled: false`，并记录 `selector_not_verified`。这是“选择器未验证前不猜测采集规则”的安全边界，不是运行回归。

2026-08-20 的真实扫描因此得到 14 个计划来源、10 个 `healthy` 和 4 个 `stale`；其中 Anthropic、Meta 是 HTML 选择器缺口，DeepSeek、Qwen 是 Phase 4 X host bridge 缺口。

当前一手页面验证结果：

- `https://www.anthropic.com/news` 返回服务端可见 HTML，正式 News 列表使用 `/news/` 链接，并提供文本型 `<time>` 日期。
- `https://ai.meta.com/blog/` 返回服务端可见 HTML，Blog Posts 首屏包含 10 张文章卡；可通过标题、文章链接和日期的结构关系定位，无需依赖 `_amd*`、`_8x*` 等不透明 class。
- 两个页面均未声明 RSS/Atom alternate link；常见官方 RSS 候选 URL 返回 404，因此本阶段继续使用 HTML Adapter。

## 2. 目标

1. 启用 Anthropic 和 Meta AI 两个核心公司官网来源。
2. 每次只读取官网首屏，最多输出 20 条去重 Evidence，不跟随分页。
3. 优先保存官网原始发布时间；无法解析时显式标记推断，不静默伪造日期。
4. 保持一个通用、配置驱动的 HTML Adapter，不增加公司专用 Python Adapter。
5. 当官网结构变化时 fail closed：Coverage 必须显示解析失败，不能误报“没有动态”。
6. 真实扫描成功后，核心来源 Coverage 目标从 `10/14 healthy` 提升到 `12/14 healthy`。

## 3. 非目标

- 不回填历史分页。
- 不处理 DeepSeek、Qwen 的 X MCP host bridge。
- 不抓取文章详情页，不为每张卡增加额外 HTTP 请求。
- 不引入 Playwright、浏览器渲染、站点专用 Adapter 或 LLM 解析。
- 不生成 Claim、Direction、研究卡或外部行动。
- 不承诺选择器永久稳定；系统通过诊断和 Fixture 让失效可见、可修复。

## 4. 方案选择

### 4.1 方案 A：只增加现有 CSS 配置

优点是改动最小。缺点是当前 Adapter 只能从 `time[datetime]` 读取日期，Meta 会把发布时间错误地推断为采集时间；零命中还会返回 `healthy`。不采用。

### 4.2 方案 B：增强通用 HTML Adapter，再启用两个来源

增加配置化日期解析、单次采集 URL 去重、零命中诊断和部分解析降级。站点差异仍留在 YAML，Python 只维护通用提取契约。采用此方案。

### 4.3 方案 C：Anthropic、Meta 专用 Adapter

站点控制力最高，但会把每个官网的 DOM 细节固化进代码，并形成“一家公司一个 Adapter”的扩张路径。当前页面不需要动态渲染或专用 API，不采用。

## 5. 数据流与职责边界

```text
Target Registry YAML
  → HtmlAdapter 校验配置
  → HTTP GET
  → item_selector 首屏卡片定位
  → 标题 / 链接 / 日期提取
  → URL 规范化与单次去重
  → Evidence.create
  → CollectResult + diagnostics
  → Runner / Evidence Ledger / Coverage / 日报
```

- Target Registry 负责站点选择器、日期格式、启用状态和数量上限。
- HtmlAdapter 负责通用提取、日期解析、去重和来源健康判断。
- Evidence Ledger 继续负责跨运行、跨日期的不可变全局去重。
- Runner、报告和 Ledger 不读取站点 DOM 细节。

## 6. HTML 来源配置契约

### 6.1 字段

| 字段 | 必需 | 语义 |
|---|---:|---|
| `item_selector` | 是 | 从整个页面选择候选卡片的 CSS selector |
| `title_selector` | 是 | 相对卡片选择标题节点 |
| `link_selector` | 是 | 相对卡片选择文章链接节点，默认读取 `href` |
| `date_selector` | 否 | 相对卡片选择一个或多个日期候选节点 |
| `date_formats` | 否 | 按顺序尝试的 `datetime.strptime` 格式列表 |
| `max_items` | 否 | 单次最多输出的去重 Evidence，默认 20 |

未知字段继续由 `SourceSpec.config` 保存，但 Adapter 只读取上述契约字段。配置缺少三个必需 selector 时返回 `invalid_config`。

### 6.2 Anthropic 配置

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

该规则只选择正式 News 列表项，不采集导航、Press Kit、分页按钮或 Featured 区的重复链接。

### 6.3 Meta AI 配置

```yaml
- id: meta_ai_blog_html
  method: html
  url: "https://ai.meta.com/blog/"
  evidence_tier: primary
  enabled: true
  item_selector: 'div:has(> div > div > h4):has(a[href*=blog])'
  title_selector: ':scope > div:first-child > div:nth-of-type(2) h4'
  link_selector: 'a[href*=blog]'
  date_selector: ':scope > div:nth-of-type(2) p'
  date_formats: ['%B %d, %Y', '%b %d, %Y']
  max_items: 20
```

该结构选择器已在 2026-08-20 官方首屏验证为 10 张 Blog Posts 卡片。它依赖语义结构、`h4` 和 blog 链接关系，不依赖不透明 class。日期选择器可以返回多个 `<p>`；解析器只接受完整文本能匹配允许格式的候选。

## 7. 提取和规范化规则

对 `item_selector` 返回的卡片按页面顺序处理，直到获得 `max_items` 个不同 URL，或候选耗尽：

1. `title_selector` 必须命中非空文本。
2. `link_selector` 必须命中带非空 `href` 的节点。
3. 链接使用 `urljoin(source.url, href)` 绝对化，并移除 fragment；不擅自删除有语义的 query。
4. 同一来源、同一运行中相同规范 URL 只保留第一条，计入 `duplicate_count`。
5. `date_selector` 的候选文本先 trim、折叠空白，再依次尝试 `date_formats`；必须整串匹配。
6. 解析出的无时区日期按 UTC 零点保存，与现有 Evidence 时间类型保持一致。
7. 没有日期或全部格式失败时使用 `collected_at`，并增加 `published_at_inferred_count`。
8. `content` 保存卡片的完整可见文本；标题、URL 和发布时间单独保存。
9. 缺少标题或链接的卡片跳过，并增加 `skipped_count`，不得创建半成品 Evidence。

数量上限作用于“成功提取且单次去重后的 Evidence”，而不是原始 DOM 节点切片，避免重复卡片挤占有效名额。

## 8. 来源健康与诊断语义

| 情况 | 状态 | `reason` / 诊断 |
|---|---|---|
| 缺少必需配置 | `unavailable` | `invalid_config` |
| HTTP 非 200 或请求失败 | `unavailable` | `http_error` / 请求异常类型 |
| CSS selector 语法错误 | `unavailable` | `invalid_selector` |
| `item_selector` 零命中 | `unavailable` | `selector_no_match` |
| 有候选但零条有效 Evidence | `unavailable` | `extraction_empty` |
| 有 Evidence，但存在跳过项或推断日期 | `degraded` | 通过计数字段说明质量损失 |
| 有 Evidence，标题、链接和日期全部按契约解析 | `healthy` | 无 `reason` |

每次结果至少包含：

```text
queried
item_match_count
record_count
duplicate_count
skipped_count
published_at_inferred_count
```

关键不变量：HTTP 200 不等于来源健康；只有成功解析至少一条 Evidence 才可能是 `healthy` 或 `degraded`。选择器失效不能被解释为“官网没有更新”。

## 9. 错误处理与安全

- 选择器错误、网络错误和解析错误只影响当前来源，其他来源继续扫描。
- 不执行页面脚本，不读取 Cookie，不进行登录，不跟随页面中的指令。
- 使用现有请求 timeout；本设计不增加重试和并发策略。
- 日志、manifest 和 Evidence 不写入 Token、Cookie、完整响应头或原始整页 HTML。
- 运行产物继续由 `.gitignore` 排除。

## 10. 测试设计

### 10.1 Fixture

新增两份最小、脱敏、手工构造的 HTML Fixture，只保留验证结构所需节点，不复制官网完整页面：

- `tests/fixtures/html/anthropic-news.html`
- `tests/fixtures/html/meta-ai-blog.html`

Meta Fixture 至少包含两个不同文章卡和一个重复 URL；Anthropic Fixture 至少包含两个列表项及文本型 `<time>`。

### 10.2 单元与契约测试

1. Anthropic Fixture 能提取标题、绝对 URL 和原始日期。
2. Meta Fixture 能提取 10 张结构中的代表卡，并解析长月份日期。
3. 短月份与长月份格式均可解析。
4. 同 URL 重复卡只输出一次，并记录 `duplicate_count`。
5. 缺少日期时回退 `collected_at`，状态为 `degraded`。
6. item 零命中时返回 `unavailable / selector_no_match`。
7. 有候选但标题或链接全部无效时返回 `unavailable / extraction_empty`。
8. 部分卡片无效时保留有效 Evidence，返回 `degraded` 并记录 `skipped_count`。
9. selector 语法错误时返回 `unavailable / invalid_selector`，不抛出导致整次扫描中止。
10. `max_items` 对去重后的 Evidence 生效。
11. Registry 加载后两个来源为 `enabled: true`，配置字段原样进入 `SourceSpec.config`。

测试必须先观察新增用例因现有行为失败，再实现最小改动使其通过。

## 11. 真实扫描验收

使用当前上海日期作为运行分组日期：

```powershell
ai-observatory validate-config --root .
ai-observatory scan --root . --date YYYY-MM-DD --profile core
ai-observatory render-daily --root . --date YYYY-MM-DD --run-id RUN_ID
```

验收条件：

1. 配置仍为 45 个观察对象、5 个研究主题。
2. Anthropic 和 Meta 请求成功时，各自产生 1–20 条去重 Evidence。
3. 两个来源的 `published_at_inferred_count` 都为 0；若官网临时缺失日期，则必须明确为 `degraded`，不能假装 `healthy`。
4. Anthropic Evidence URL 属于 `anthropic.com/news/`；Meta Evidence URL 属于 `ai.meta.com/blog/`。
5. 正常网络条件下 Coverage 达到 12/14 `healthy`；只剩两个 Phase 4 X 来源为 `stale`。
6. 同日立即重跑时 Ledger 不新增重复 Evidence；`appended_count` 可以为 0，但来源仍可根据本次查询和解析结果保持健康。
7. 日报 Coverage 显示实际状态、采集数、新增数和失败原因。
8. 完整测试套件通过，`git diff --check` 通过，运行产物不进入 Git 状态。

如果真实官网已改变，导致选择器零命中或日期无法解析，则验收不通过；不得为了得到 12/14 而降低健康判定或使用无来源日期。

## 12. 实施边界与顺序

后续实施计划应拆成两个可独立验证的任务：

1. 先以 TDD 增强通用 HtmlAdapter 的日期、去重、诊断和 fail-closed 契约。
2. 再以 TDD 加入两个站点 Fixture、启用 YAML 配置并执行真实扫描验收。

不在同一任务中顺手重构 Runner、Ledger、报告或其他 Adapter。若实现发现 Meta 结构无法由上述通用契约表达，应停止并回到设计评审，不得偷偷加入 Meta 专用分支。

## 13. 完成定义

只有以下证据同时存在，来源覆盖增强才算完成：

- 本规格已批准；
- 新增回归测试经历 RED → GREEN；
- 完整测试通过；
- 两个来源真实运行产生可追溯 Evidence；
- Coverage 和日期质量满足第 11 节；
- 同日重跑证明 Ledger 幂等；
- 仓库只包含预期源码、配置、Fixture 和文档变更。

