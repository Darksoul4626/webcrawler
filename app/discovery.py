from __future__ import annotations
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET
import feedparser
import httpx


class SeedDiscovery:
    def __init__(self, user_agent: str, timeout_sec: int):
        self.user_agent = user_agent
        self.timeout_sec = timeout_sec

    async def _get(self, url: str) -> str:
        async with httpx.AsyncClient(
            headers={"User-Agent": self.user_agent},
            timeout=self.timeout_sec,
            follow_redirects=True,
        ) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.text

    async def _parse_sitemap(self, url: str, limit: int) -> list[str]:
        xml = await self._get(url)
        root = ET.fromstring(xml)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        urls = []
        # urlset
        for loc in root.findall(".//sm:url/sm:loc", ns):
            if loc.text:
                urls.append(loc.text.strip())
                if len(urls) >= limit:
                    return urls

        # sitemapindex recursion (one level for simplicity)
        for loc in root.findall(".//sm:sitemap/sm:loc", ns):
            if len(urls) >= limit:
                break
            if loc.text:
                child = await self._parse_sitemap(loc.text.strip(), limit - len(urls))
                urls.extend(child)

        return urls[:limit]

    async def discover(self, topic_cfg) -> list[str]:
        seeds = list(topic_cfg.crawl.start_urls)
        limit = topic_cfg.discovery.max_seed_urls

        if topic_cfg.discovery.use_sitemap:
            sitemap_urls = list(topic_cfg.discovery.sitemap_urls)
            if not sitemap_urls:
                for u in topic_cfg.crawl.start_urls:
                    p = urlparse(u)
                    sitemap_urls.append(f"{p.scheme}://{p.netloc}/sitemap.xml")

            for sm in sitemap_urls:
                try:
                    seeds.extend(await self._parse_sitemap(sm, limit))
                except Exception:
                    pass

        if topic_cfg.discovery.use_rss:
            for ru in topic_cfg.discovery.rss_urls:
                try:
                    feed = feedparser.parse(ru)
                    for e in feed.entries:
                        link = getattr(e, "link", None)
                        if link:
                            seeds.append(link)
                except Exception:
                    pass

        # dedup, preserve order
        seen = set()
        out = []
        for s in seeds:
            if s not in seen:
                seen.add(s)
                out.append(s)
            if len(out) >= limit:
                break
        return out