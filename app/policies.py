from __future__ import annotations
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import httpx


class DomainPolicyEngine:
    def __init__(self, global_cfg, domain_policies):
        self.global_cfg = global_cfg
        self.policies = {p.domain.lower(): p for p in domain_policies}
        self.robots_cache = {}
        self.last_hit = {}

    def _policy_for(self, domain: str):
        return self.policies.get(domain.lower())

    async def _load_robots(self, base_url: str):
        if base_url in self.robots_cache:
            return self.robots_cache[base_url]
        robots_url = f"{base_url.rstrip('/')}/robots.txt"
        rp = RobotFileParser()
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                r = await client.get(robots_url)
                if r.status_code < 400:
                    rp.parse(r.text.splitlines())
                else:
                    rp = None
        except Exception:
            rp = None
        self.robots_cache[base_url] = rp
        return rp

    async def can_fetch(self, url: str, user_agent: str) -> bool:
        p = urlparse(url)
        domain = p.netloc.lower()
        policy = self._policy_for(domain)
        mode = policy.robots if policy else self.global_cfg.robots_default

        if mode == "ignore":
            return True

        base = f"{p.scheme}://{p.netloc}"
        rp = await self._load_robots(base)
        if rp is None:
            # fail-open for availability
            return True
        return rp.can_fetch(user_agent, url)

    async def apply_delay(self, url: str):
        p = urlparse(url)
        domain = p.netloc.lower()
        policy = self._policy_for(domain)
        delay_ms = policy.crawl_delay_ms if policy else 1000

        now = time.time() * 1000
        last = self.last_hit.get(domain, 0)
        wait = delay_ms - (now - last)
        if wait > 0:
            time.sleep(wait / 1000.0)
        self.last_hit[domain] = time.time() * 1000