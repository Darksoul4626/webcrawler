from __future__ import annotations
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class GlobalConfig(BaseModel):
    user_agent: str = "ResearchCrawler/2.0"
    max_concurrency: int = 8
    request_timeout_sec: int = 20
    enable_snapshots: bool = True
    obey_robots_txt: bool = True
    robots_default: str = "respect"  # respect | ignore
    output_dir: str = "./reports"
    state_dir: str = "./state"
    snapshot_dir: str = "./snapshots"
    timezone: str = "UTC"


class DomainPolicy(BaseModel):
    domain: str
    robots: str = "respect"  # respect | ignore
    crawl_delay_ms: int = 1000
    user_agent: Optional[str] = None


class EmailConfig(BaseModel):
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password_env: str = ""
    from_email: str = Field("", alias="from")
    to: List[str] = []
    subject_prefix: str = "[Crawler Alert]"


class TeamsConfig(BaseModel):
    enabled: bool = False
    webhook_url_env: str = "TEAMS_WEBHOOK_URL"


class KeywordConfig(BaseModel):
    include: List[str] = []
    exclude: List[str] = []
    regex: List[str] = []


class DiscoveryConfig(BaseModel):
    use_sitemap: bool = True
    sitemap_urls: List[str] = []
    use_rss: bool = False
    rss_urls: List[str] = []
    max_seed_urls: int = 5000


class AuthSelectors(BaseModel):
    username: str
    password: str
    submit: str
    success_indicator: str


class AuthConfig(BaseModel):
    mode: str = "none"
    login_url: Optional[str] = None
    username_env: Optional[str] = None
    password_env: Optional[str] = None
    selectors: Optional[AuthSelectors] = None


class CrawlConfig(BaseModel):
    max_depth: int = 1
    max_pages: int = 100
    allowed_domains: List[str] = []
    start_urls: List[str] = []
    include_url_patterns: List[str] = []
    exclude_url_patterns: List[str] = []
    render_js: bool = False
    auth: Optional[AuthConfig] = None
    session_persist: bool = True


class AlertingConfig(BaseModel):
    min_quality_score: int = 60
    min_confidence: float = 0.65
    suppress_if_contains: List[str] = []
    keyword_weights: Dict[str, float] = {}


class TopicConfig(BaseModel):
    enabled: bool = True
    name: str
    schedule: str
    keywords: KeywordConfig
    crawl: CrawlConfig
    discovery: DiscoveryConfig = DiscoveryConfig()
    alerting: AlertingConfig = AlertingConfig()


class AppConfig(BaseModel):
    global_config: GlobalConfig = Field(..., alias="global")
    domain_policies: List[DomainPolicy] = []
    email: EmailConfig
    teams: TeamsConfig = TeamsConfig()
    topics: List[TopicConfig]

    class Config:
        populate_by_name = True


class Finding(BaseModel):
    topic: str
    url: str
    title: str
    keyword: str
    snippet: str
    timestamp: str
    quality_score: int = 0
    confidence: float = 0.0
    canonical_url: str = ""
    content_hash: str = ""