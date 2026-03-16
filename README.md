# Automated Webcrawler (v3)

A configurable, automated crawler for monitoring websites (including authenticated pages), detecting keyword-based findings, archiving evidence, and sending alerts.

---

## What this crawler does

### Core capabilities
- **Config-first crawling** via `crawler.config.yaml`
- **Crawls websites + subpages** with depth/page limits
- **Parallel crawling** using `asyncio` + semaphore (`global.max_concurrency`)
- **Supports JS-rendered pages** via Playwright
- **Supports authenticated/login flows** (Playwright form login)
- **Sitemap + RSS seeding** for broader URL discovery
- **Keyword + regex matching**
- **Daily Markdown reports** per topic
- **HTML snapshot archiving** for audit trails
- **Notifications** via Email and Microsoft Teams
- **robots.txt policy engine** configurable per domain
- **Duplicate + near-duplicate suppression**
- **Content quality scoring + false-positive filtering**

---

## High-level workflow

1. Load config from YAML.
2. For each scheduled topic:
   - Build seeds from:
     - `crawl.start_urls`
     - optional sitemap URLs
     - optional RSS feeds
   - Enforce per-domain crawl policy (robots + delay).
   - Fetch pages (HTTP or Playwright).
   - Extract text/links and archive HTML snapshot.
   - Score content quality.
   - Detect keyword/regex matches.
   - Suppress duplicates and likely false positives.
   - Save findings + state.
3. Write report to:
   - `reports/YYYY-MM-DD/<topic-slug>.md`
4. Send alerts (Email/Teams) if findings exist.

---

## Project structure

```text
webcrawler/
├─ reports/
├─ snapshots/
├─ state/
├─ app/
│  ├─ main.py
│  ├─ scheduler.py
│  ├─ crawler.py
│  ├─ config.py
│  ├─ models.py
│  ├─ fetchers.py
│  ├─ discovery.py
│  ├─ policies.py
│  ├─ quality.py
│  ├─ dedup.py
│  ├─ analyzer.py
│  ├─ archive.py
│  ├─ reporter.py
│  ├─ notifier.py
│  └─ state.py
├─ crawler.config.yaml
├─ requirements.txt
├─ Dockerfile
├─ docker-compose.yml
└─ .env.example

```

---

## Installation

## Option A: Local Python run

1. Create environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   # .venv\Scripts\activate    # Windows PowerShell
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install Playwright browser:
   ```bash
   playwright install chromium
   ```

4. Prepare config + env:
   ```bash
   cp .env.example .env
   # edit .env and crawler.config.yaml
   ```

5. Start scheduler:
   ```bash
   python -m app.main
   ```

## Option B: Docker

```bash
docker compose up --build -d
docker logs -f webcrawler
```

---

## Running modes

### Scheduled mode (default)
Runs continuously and executes each topic by cron expression in config.

```bash
python -m app.main
```

### One-shot mode (recommended for testing)
Run a single topic once and exit:

```bash
python -m app.main --once --topic "Test Topic"
```

With explicit config path:

```bash
python -m app.main --config ./crawler.config.yaml --once --topic "Test Topic"
```

---

## Configuration guide (`crawler.config.yaml`)

## 1) Global settings

```yaml
global:
  user_agent: "ResearchCrawler/3.0 (+contact: ops@example.com)"
  max_concurrency: 8
  request_timeout_sec: 20
  obey_robots_txt: true
  robots_default: "respect"    # respect | ignore
  output_dir: "./reports"
  state_dir: "./state"
  snapshot_dir: "./snapshots"
  timezone: "UTC"
```

- `max_concurrency`: max parallel page tasks per topic run
- `robots_default`: default robots policy if no domain override

## 2) Domain policies (robots + delay)

```yaml
domain_policies:
  - domain: "vendor-a.com"
    robots: "respect"
    crawl_delay_ms: 1200
  - domain: "portal.example.org"
    robots: "ignore"
    crawl_delay_ms: 500
```

Use `robots: ignore` only for sites you are authorized to crawl.

## 3) Notifications

### Email
```yaml
email:
  enabled: true
  smtp_host: "smtp.example.com"
  smtp_port: 587
  smtp_user: "crawler@example.com"
  smtp_password_env: "CRAWLER_SMTP_PASSWORD"
  from: "crawler@example.com"
  to: ["alice@example.com", "bob@example.com"]
  subject_prefix: "[Crawler Alert]"
```

### Teams
```yaml
teams:
  enabled: true
  webhook_url_env: "TEAMS_WEBHOOK_URL"
```

## 4) Topic configuration

Each topic has:
- schedule (cron)
- keywords
- discovery (sitemap/rss)
- alerting thresholds
- crawl behavior

```yaml
topics:
  - name: "Cybersecurity Advisories"
    schedule: "0 */2 * * *"   # every 2 hours
    keywords:
      include: ["critical vulnerability", "CVE-"]
      exclude: ["advertisement"]
      regex: ["(?i)zero[- ]day"]
    discovery:
      use_sitemap: true
      sitemap_urls: []
      use_rss: true
      rss_urls:
        - "https://vendor-a.com/security/feed"
      max_seed_urls: 3000
    alerting:
      min_quality_score: 60
      min_confidence: 0.65
      suppress_if_contains: ["sponsored", "advertorial"]
      keyword_weights:
        "critical vulnerability": 1.0
        "CVE-": 0.9
    crawl:
      max_depth: 2
      max_pages: 150
      allowed_domains: ["vendor-a.com", "vendor-b.com"]
      start_urls:
        - "https://vendor-a.com/security"
      include_url_patterns: ["/security", "/advisories"]
      exclude_url_patterns: ["/tag/", "/author/"]
      render_js: false
```

---

## Authenticated/login crawling

For websites behind login/paywall (authorized access only), set:

```yaml
crawl:
  render_js: true
  auth:
    mode: "playwright_form"
    login_url: "https://portal.example.org/login"
    username_env: "PORTAL_USER"
    password_env: "PORTAL_PASS"
    selectors:
      username: "#email"
      password: "#password"
      submit: "button[type='submit']"
      success_indicator: "nav .account"
  session_persist: true
```

Then put credentials in `.env`:
```bash
PORTAL_USER=your-user
PORTAL_PASS=your-password
```

---

## Detailed Configuration Reference (Table)

The following overview documents all relevant fields in `crawler.config.yaml`.

### 1) Global (`global`)

| Config Name | Description | Possible Values |
|---|---|---|
| `global.user_agent` | User-Agent header used for HTTP requests and browser context. | Any string, e.g. `ResearchCrawler/3.0 (+contact: ops@example.com)` |
| `global.max_concurrency` | Maximum number of parallel fetch/processing tasks per topic run. | Integer `>= 1` |
| `global.request_timeout_sec` | Timeout for HTTP and browser navigation. | Integer `> 0` (seconds) |
| `global.enable_snapshots` | Enables/disables HTML snapshot archiving for crawled pages. | `true` / `false` |
| `global.obey_robots_txt` | Currently defined in the config model; runtime logic effectively uses `robots_default` and `domain_policies[*].robots`. | `true` / `false` |
| `global.robots_default` | Default robots strategy when no domain override exists. | `respect` \| `ignore` |
| `global.output_dir` | Output folder for reports. | Valid relative/absolute path |
| `global.state_dir` | Output folder for state files and optional login session state. | Valid relative/absolute path |
| `global.snapshot_dir` | Output folder for HTML snapshots. | Valid relative/absolute path |
| `global.timezone` | Scheduler timezone for cron execution. | IANA timezone, e.g. `UTC`, `Europe/Berlin` |

### 2) Domain Policies (`domain_policies[]`)

| Config Name | Description | Possible Values |
|---|---|---|
| `domain_policies[].domain` | Domain where this policy is applied. | Hostname, e.g. `www.heise.de` |
| `domain_policies[].robots` | Per-domain robots behavior. Overrides `global.robots_default`. | `respect` \| `ignore` |
| `domain_policies[].crawl_delay_ms` | Minimum delay between requests on the same domain. | Integer `>= 0` (milliseconds) |
| `domain_policies[].user_agent` | Present in model, currently not separately consumed in runtime policy logic. | String or empty |

### 3) Notifications (`email`, `teams`)

| Config Name | Description | Possible Values |
|---|---|---|
| `email.enabled` | Enable/disable email notifications. | `true` / `false` |
| `email.smtp_host` | SMTP server host. | Hostname/IP |
| `email.smtp_port` | SMTP port. | Integer, typically `25`, `465`, `587` |
| `email.smtp_user` | SMTP username. | String |
| `email.smtp_password_env` | Environment variable name for SMTP password. | String, e.g. `CRAWLER_SMTP_PASSWORD` |
| `email.from` | Sender address. | Valid email address |
| `email.to` | Recipient list. | List of email addresses |
| `email.subject_prefix` | Prefix for email subject lines. | String |
| `teams.enabled` | Enable/disable Teams notifications. | `true` / `false` |
| `teams.webhook_url_env` | Environment variable name with Teams webhook URL. | String, e.g. `TEAMS_WEBHOOK_URL` |

### 4) Topic Basics (`topics[]`)

| Config Name | Description | Possible Values |
|---|---|---|
| `topics[].enabled` | Enables/disables the topic. Disabled topics are skipped by scheduler and blocked in `--once`. | `true` / `false` |
| `topics[].name` | Display name of the topic (used by `--topic`). | Unique string |
| `topics[].schedule` | Cron expression for scheduled runs. | 5-field cron, e.g. `*/15 * * * *` |

### 5) Keywords (`topics[].keywords`)

| Config Name | Description | Possible Values |
|---|---|---|
| `topics[].keywords.include` | Keyword OR-matching against page text. | List of strings |
| `topics[].keywords.exclude` | Suppresses matches if an exclude token appears in the snippet. | List of strings |
| `topics[].keywords.regex` | Additional regex patterns (`re.search`). | List of valid regex strings |

### 6) Discovery (`topics[].discovery`)

| Config Name | Description | Possible Values |
|---|---|---|
| `topics[].discovery.use_sitemap` | Enables sitemap-based seed expansion. | `true` / `false` |
| `topics[].discovery.sitemap_urls` | Explicit sitemap URLs. If empty, `/sitemap.xml` is tried from `start_urls`. | List of URLs |
| `topics[].discovery.use_rss` | Enables RSS/Atom feed seed expansion. | `true` / `false` |
| `topics[].discovery.rss_urls` | RSS/Atom feed URLs for additional seeds. | List of URLs |
| `topics[].discovery.max_seed_urls` | Maximum number of seeds after deduplication. | Integer `>= 1` |

### 7) Alerting (`topics[].alerting`)

| Config Name | Description | Possible Values |
|---|---|---|
| `topics[].alerting.min_quality_score` | Minimum quality score required for a match. | Integer `0..100` |
| `topics[].alerting.min_confidence` | Minimum confidence required for a match. | Float `0.0..1.0` |
| `topics[].alerting.suppress_if_contains` | Suppresses matches if snippet contains one of these tokens. | List of strings |
| `topics[].alerting.keyword_weights` | Per-keyword/regex weight used in confidence scoring. | Mapping `"keyword": float`, typically `0.0..1.0` |

### 8) Crawl (`topics[].crawl`)

| Config Name | Description | Possible Values |
|---|---|---|
| `topics[].crawl.max_depth` | Link traversal depth from start URLs. | Integer `>= 0` |
| `topics[].crawl.max_pages` | Maximum pages per topic run. | Integer `>= 1` |
| `topics[].crawl.allowed_domains` | Domain filter (current behavior: substring match on URL). | List of domain strings |
| `topics[].crawl.start_urls` | Entry points for crawling. | List of URLs |
| `topics[].crawl.include_url_patterns` | Only URLs containing one of these patterns are crawled (substring match). | List of strings |
| `topics[].crawl.exclude_url_patterns` | URLs containing one of these patterns are excluded (substring match). | List of strings |
| `topics[].crawl.render_js` | Uses Playwright-based rendering instead of HTTP-only fetch. | `true` / `false` |
| `topics[].crawl.session_persist` | Stores/reuses login session state across runs. | `true` / `false` |
| `topics[].crawl.auth.mode` | Authentication mode. | `none` \| `playwright_form` |
| `topics[].crawl.auth.login_url` | Login URL for form-based authentication. | URL |
| `topics[].crawl.auth.username_env` | Environment variable name for login username. | String |
| `topics[].crawl.auth.password_env` | Environment variable name for login password. | String |
| `topics[].crawl.auth.selectors.username` | CSS selector for username input. | CSS selector string |
| `topics[].crawl.auth.selectors.password` | CSS selector for password input. | CSS selector string |
| `topics[].crawl.auth.selectors.submit` | CSS selector for submit button. | CSS selector string |
| `topics[].crawl.auth.selectors.success_indicator` | CSS selector that must appear after successful login. | CSS selector string |

### Practical Notes (Important)

- `include_url_patterns` and `exclude_url_patterns` are **not regex**; they are substring checks.
- `allowed_domains` is also a substring check on the full URL; use precise domain strings.
- `keywords.include` is OR logic; use lookahead regex if you need AND logic.
- Very low `min_confidence`/`min_quality_score` usually increases false positives.

### Best-Practice Example Configs

#### A) Minimal config (quick local smoke test)

```yaml
global:
  user_agent: "ResearchCrawler/3.0-test"
  max_concurrency: 2
  request_timeout_sec: 20
  obey_robots_txt: true
  robots_default: "respect"
  output_dir: "./reports"
  state_dir: "./state"
  snapshot_dir: "./snapshots"
  timezone: "UTC"

domain_policies: []

email:
  enabled: false
  smtp_host: ""
  smtp_port: 587
  smtp_user: ""
  smtp_password_env: "CRAWLER_SMTP_PASSWORD"
  from: ""
  to: []
  subject_prefix: "[Crawler Alert]"

teams:
  enabled: false
  webhook_url_env: "TEAMS_WEBHOOK_URL"

topics:
  - name: "AI Minimal"
    schedule: "*/30 * * * *"
    keywords:
      include: ["ai", "künstliche intelligenz"]
      exclude: []
      regex: ["(?i)\\bai\\b", "(?i)künstliche\\s+intelligenz"]
    discovery:
      use_sitemap: false
      sitemap_urls: []
      use_rss: false
      rss_urls: []
      max_seed_urls: 100
    alerting:
      min_quality_score: 20
      min_confidence: 0.25
      suppress_if_contains: []
      keyword_weights:
        "ai": 0.6
        "künstliche intelligenz": 0.9
    crawl:
      max_depth: 1
      max_pages: 20
      allowed_domains: ["heise.de"]
      start_urls: ["https://www.heise.de/news/"]
      include_url_patterns: ["/news/"]
      exclude_url_patterns: ["view=print", "/forum/"]
      render_js: false
```

#### B) Production-style config (lower noise, better coverage)

```yaml
global:
  user_agent: "ResearchCrawler/3.0 (+contact: ops@example.com)"
  max_concurrency: 6
  request_timeout_sec: 25
  obey_robots_txt: true
  robots_default: "respect"
  output_dir: "./reports"
  state_dir: "./state"
  snapshot_dir: "./snapshots"
  timezone: "Europe/Berlin"

domain_policies:
  - domain: "www.heise.de"
    robots: "respect"
    crawl_delay_ms: 1200
  - domain: "www.golem.de"
    robots: "respect"
    crawl_delay_ms: 1200

email:
  enabled: true
  smtp_host: "smtp.example.com"
  smtp_port: 587
  smtp_user: "crawler@example.com"
  smtp_password_env: "CRAWLER_SMTP_PASSWORD"
  from: "crawler@example.com"
  to: ["team@example.com"]
  subject_prefix: "[Crawler Alert]"

teams:
  enabled: true
  webhook_url_env: "TEAMS_WEBHOOK_URL"

topics:
  - name: "AI News"
    schedule: "*/15 * * * *"
    keywords:
      include: ["ki", "künstliche intelligenz", "machine learning", "openai", "llm"]
      exclude: ["stellenanzeige", "werbung"]
      regex:
        [
          "(?i)\\bki\\b",
          "(?i)künstliche\\s+intelligenz",
          "(?i)machine\\s+learning",
          "(?i)\\bllm(s)?\\b",
          "(?is)(?=.*künstliche\\s+intelligenz)(?=.*(gesetz|regulierung|compliance))",
        ]
    discovery:
      use_sitemap: true
      sitemap_urls:
        ["https://www.heise.de/sitemaps/news.xml", "https://www.golem.de/sitemap.xml"]
      use_rss: true
      rss_urls:
        ["https://www.heise.de/rss/heise-atom.xml", "https://rss.golem.de/rss.php?feed=RSS2.0"]
      max_seed_urls: 600
    alerting:
      min_quality_score: 45
      min_confidence: 0.5
      suppress_if_contains: ["cookie", "impressum", "agb"]
      keyword_weights:
        "ki": 0.65
        "künstliche intelligenz": 1.0
        "machine learning": 0.8
        "openai": 0.85
        "llm": 0.85
        "regex:(?i)\\bki\\b": 0.65
        "regex:(?i)künstliche\\s+intelligenz": 1.0
        "regex:(?i)machine\\s+learning": 0.8
        "regex:(?i)\\bllm(s)?\\b": 0.85
        "regex:(?is)(?=.*künstliche\\s+intelligenz)(?=.*(gesetz|regulierung|compliance))": 1.0
    crawl:
      max_depth: 2
      max_pages: 120
      allowed_domains: ["heise.de", "golem.de"]
      start_urls: ["https://www.heise.de/news/", "https://www.golem.de/news/"]
      include_url_patterns: ["/news/", "/thema/"]
      exclude_url_patterns: ["/forum/", "view=print", "/specials/"]
      render_js: false
```

---

## State, reports, and snapshots

- **Reports:** first run writes `reports/YYYY-MM-DD/<topic>.md`; additional runs on the same day write `reports/YYYY-MM-DD/<topic>-HHMMSS.md` (and `-HHMMSS-2`, ... on collision)
- **Snapshots:** `snapshots/YYYY-MM-DD/<topic>/*.html`
- **State:** `state/<topic>_state.json`

State includes:
- seen fingerprints
- canonical URL -> content hash
- simhash list for near-dup suppression
- feedback map (`true_positive` / `false_positive`)

---

## False-positive handling

Current mechanisms:
- Keyword `exclude`
- `alerting.suppress_if_contains`
- `min_quality_score`
- `min_confidence`
- Duplicate/near-duplicate suppression

Tip: start with lower thresholds for discovery, then tighten after observing noise.

---

## Troubleshooting

### No findings
- Broaden keywords
- Reduce `min_quality_score` / `min_confidence`
- Increase `max_pages` / `max_depth`
- Check include/exclude URL patterns

### Too many findings/noise
- Add `exclude` keywords
- Add `suppress_if_contains`
- Raise quality/confidence thresholds
- Restrict `allowed_domains`

### Login crawl fails
- Verify CSS selectors
- Verify credentials in env
- Ensure `render_js: true`
- Test login manually in browser first

### Teams/email not sent
- Ensure `enabled: true`
- Validate env var names and values
- Check SMTP/webhook connectivity

### Playwright errors
```bash
playwright install chromium
```

---

## Security + compliance notes

- Crawl only domains you are authorized to access.
- For paywalled/authenticated targets, ensure contractual permission.
- Avoid storing secrets in YAML; use env vars / secret manager.
- Use conservative crawl delays and domain restrictions.

---

## Quick smoke test

1. Create a `Test Topic` with one allowed domain.
2. Disable notifications (`email.enabled: false`, `teams.enabled: false`).
3. Run:
   ```bash
   python -m app.main --once --topic "Test Topic"
   ```
4. Confirm:
   - report file exists
   - snapshot files exist
   - state file exists

---

## Next recommended upgrades

- Per-domain concurrency pools (not only global)
- Retry/backoff (`tenacity`) around all network operations
- Structured JSON logs + metrics
- Postgres + OpenSearch backend
- Review UI for findings/feedback