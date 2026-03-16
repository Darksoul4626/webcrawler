import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.fetchers import StaticFetcher, BrowserFetcher
from app.analyzer import KeywordAnalyzer
from app.archive import SnapshotArchiver
from app.state import StateStore
from app.discovery import SeedDiscovery
from app.policies import DomainPolicyEngine
from app.quality import ContentQualityScorer, ConfidenceScorer, FalsePositiveFilter
from app.dedup import Deduplicator
from app.crawler import CrawlEngine
from app.reporter import MarkdownReporter
from app.notifier import EmailNotifier, TeamsNotifier


async def run_topic(cfg, topic_cfg):
    static_fetcher = StaticFetcher(cfg.global_config.user_agent, cfg.global_config.request_timeout_sec)
    browser_fetcher = BrowserFetcher(cfg.global_config.state_dir, cfg.global_config.user_agent, cfg.global_config.request_timeout_sec)
    analyzer = KeywordAnalyzer()
    state = StateStore(cfg.global_config.state_dir)
    archiver = SnapshotArchiver(cfg.global_config.snapshot_dir) if cfg.global_config.enable_snapshots else None
    discovery = SeedDiscovery(cfg.global_config.user_agent, cfg.global_config.request_timeout_sec)
    policy_engine = DomainPolicyEngine(cfg.global_config, cfg.domain_policies)

    quality_scorer = ContentQualityScorer()
    confidence_scorer = ConfidenceScorer()
    fp_filter = FalsePositiveFilter(topic_cfg.alerting.suppress_if_contains)
    dedup = Deduplicator()

    engine = CrawlEngine(
        static_fetcher=static_fetcher,
        browser_fetcher=browser_fetcher,
        analyzer=analyzer,
        state_store=state,
        archiver=archiver,
        discovery=discovery,
        policy_engine=policy_engine,
        quality_scorer=quality_scorer,
        confidence_scorer=confidence_scorer,
        fp_filter=fp_filter,
        deduplicator=dedup,
        max_concurrency=cfg.global_config.max_concurrency,
        user_agent=cfg.global_config.user_agent,
    )

    reporter = MarkdownReporter(cfg.global_config.output_dir)
    email_notifier = EmailNotifier(cfg.email)
    teams_notifier = TeamsNotifier(cfg.teams)

    result = await engine.crawl_topic(topic_cfg)
    report_path = reporter.write_daily_topic_report(type("R", (), result))
    alert_findings = result.get("unique_findings") or result["findings"]

    if alert_findings:
        highlights = [f"{f.keyword} @ {f.url} (q={f.quality_score}, c={f.confidence:.2f})" for f in alert_findings]
        email_notifier.send(topic_cfg.name, len(alert_findings), report_path, highlights)
        teams_notifier.send(topic_cfg.name, len(alert_findings), report_path, highlights)

    return result, report_path


async def run_topic_once(cfg, topic_name: str):
    topic = next((t for t in cfg.topics if t.name == topic_name), None)
    if not topic:
        available = ", ".join(t.name for t in cfg.topics)
        raise SystemExit(f'Topic "{topic_name}" not found. Available topics: {available}')
    if not topic.enabled:
        raise SystemExit(f'Topic "{topic_name}" is disabled in config (topics[].enabled=false).')

    result, report_path = await run_topic(cfg, topic)
    unique_count = len(result.get("unique_findings") or [])
    print(f"[OK] Topic: {topic_name}")
    print(f"[OK] Pages scanned: {result['pages_scanned']}")
    print(f"[OK] Findings: {len(result['findings'])}")
    print(f"[OK] Unique URLs: {unique_count}")
    print(f"[OK] Errors: {len(result['errors'])}")
    print(f"[OK] Report: {report_path}")


async def run_scheduler(cfg):
    scheduler = AsyncIOScheduler(timezone=cfg.global_config.timezone)

    for topic in cfg.topics:
        if not topic.enabled:
            continue
        trigger = CronTrigger.from_crontab(topic.schedule, timezone=cfg.global_config.timezone)
        scheduler.add_job(run_topic, trigger=trigger, args=[cfg, topic], name=topic.name)

    scheduler.start()
    await asyncio.Event().wait()